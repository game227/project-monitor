from __future__ import annotations

import webbrowser

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.settings import Settings
from app.database.session import session_scope
from app.models.project import Project
from app.notifications import notifier
from app.services.discovery_service import DiscoveredProject
from app.services.project_repository import ProjectRepository
from app.services.sync_service import add_discovered_project, ignore_discovered_project, set_project_command
from app.ui.discovery_worker import DiscoveryController
from app.ui.monitoring_worker import MonitoringController
from app.ui.pages.add_project_page import AddProjectPage
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.git_page import GitPage
from app.ui.pages.logs_page import LogsPage
from app.ui.pages.projects_page import ProjectsPage
from app.ui.pages.running_page import RunningPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.system_page import SystemPage
from app.ui.widgets.configure_command_dialog import ConfigureCommandDialog
from app.ui.widgets.new_project_dialog import NewProjectDialog
from app.ui.widgets.project_detail_dialog import ProjectDetailDialog

_NAV_ITEMS = ["Dashboard", "Projects", "Add Project", "Running", "Git", "Logs", "System", "Settings"]


class MainWindow(QMainWindow):
    request_start = Signal(int)
    request_stop = Signal(int)
    request_restart = Signal(int)
    request_rescan = Signal()

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings
        self._projects: dict[int, Project] = {}
        self._detail_dialogs: dict[int, ProjectDetailDialog] = {}

        self.setWindowTitle("Project Monitor")
        self.resize(1180, 760)

        notifier.set_enabled(settings.show_desktop_notifications)

        self.monitoring = MonitoringController(settings)
        self.discovery = DiscoveryController(settings)

        self._build_ui()
        self._wire_workers()

        # Only start the worker threads once every signal above is
        # connected -- otherwise the very first scan/tick can complete
        # and emit before anything is listening (see MonitoringController).
        self.monitoring.start()
        self.discovery.start()

    # -- UI construction --------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        root.addWidget(self._build_sidebar())

        self.pages = QStackedWidget()
        self.dashboard_page = DashboardPage()
        self.projects_page = ProjectsPage()
        self.add_project_page = AddProjectPage()
        self.add_project_page.project_added.connect(self._on_project_added)
        self.running_page = RunningPage()
        self.git_page = GitPage()
        self.logs_page = LogsPage(self._get_logs, self._clear_logs)
        self.system_page = SystemPage(int(self._settings.cpu_ram_poll_interval_seconds * 1000))
        self.settings_page = SettingsPage(self._settings)
        self.settings_page.settings_changed.connect(self._on_settings_changed)

        for page in (
            self.dashboard_page,
            self.projects_page,
            self.add_project_page,
            self.running_page,
            self.git_page,
            self.logs_page,
            self.system_page,
            self.settings_page,
        ):
            self.pages.addWidget(page)

        root.addWidget(self.pages, stretch=1)

        for page in (self.dashboard_page, self.projects_page, self.running_page):
            page.project_list.open_requested.connect(self._on_open_requested)
            page.project_list.start_requested.connect(self._on_start_requested)
            page.project_list.stop_requested.connect(self.request_stop)
            page.project_list.configure_requested.connect(self._on_configure_requested)
            page.project_list.details_requested.connect(self._on_details_requested)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(2)

        title = QLabel("Project Monitor")
        title.setObjectName("SidebarTitle")
        layout.addWidget(title)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for index, name in enumerate(_NAV_ITEMS):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked, i=index: self.pages.setCurrentIndex(i))
            self._nav_group.addButton(btn, index)
            layout.addWidget(btn)
        self._nav_group.button(0).setChecked(True)

        layout.addStretch(1)

        rescan_btn = QPushButton("Rescan")
        rescan_btn.clicked.connect(self.request_rescan)
        layout.addWidget(rescan_btn)

        return sidebar

    # -- worker wiring ------------------------------------------------------

    def _wire_workers(self) -> None:
        self.request_start.connect(self.monitoring.worker.start_project)
        self.request_stop.connect(self.monitoring.worker.stop_project)
        self.request_restart.connect(self.monitoring.worker.restart_project)
        self.request_rescan.connect(self.discovery.worker.run_scan)

        self.monitoring.worker.updated.connect(self._poll_db)
        self.discovery.worker.scan_completed.connect(self._poll_db)
        self.discovery.worker.pending_projects.connect(self._handle_pending_projects)

        self._poll_db()

    # -- data refresh ------------------------------------------------------

    def _poll_db(self) -> None:
        with session_scope() as session:
            repo = ProjectRepository(session)
            projects = repo.list_all()
            session.expunge_all()

        self._projects = {p.id: p for p in projects}

        self.dashboard_page.refresh(projects)
        self.projects_page.refresh(projects)
        self.running_page.refresh(projects)
        self.git_page.refresh(projects)
        self.logs_page.refresh(projects)

        for project_id, dialog in list(self._detail_dialogs.items()):
            project = self._projects.get(project_id)
            if project is not None:
                dialog.refresh(project)

    # -- actions ------------------------------------------------------------

    def _on_open_requested(self, project_id: int) -> None:
        project = self._projects.get(project_id)
        if project and project.primary_port:
            webbrowser.open(f"http://{project.host}:{project.primary_port}")

    def _on_start_requested(self, project_id: int) -> None:
        project = self._projects.get(project_id)
        if project is None:
            return
        if not project.start_command:
            self._prompt_configure_then_start(project)
            return
        self.request_start.emit(project_id)

    def _on_configure_requested(self, project_id: int) -> None:
        project = self._projects.get(project_id)
        if project is not None:
            self._prompt_configure_then_start(project)

    def _prompt_configure_then_start(self, project: Project) -> None:
        dialog = ConfigureCommandDialog(project.name, project.working_directory or project.path, self)
        if dialog.exec() != ConfigureCommandDialog.DialogCode.Accepted:
            return
        start_command = dialog.start_command()
        if not start_command:
            return
        set_project_command(project.id, start_command, dialog.stop_command(), dialog.working_directory())
        self.request_start.emit(project.id)

    def _on_project_added(self) -> None:
        self._poll_db()

    def _on_details_requested(self, project_id: int) -> None:
        existing = self._detail_dialogs.get(project_id)
        if existing is not None:
            existing.show()
            existing.raise_()
            existing.activateWindow()
            return

        project = self._projects.get(project_id)
        if project is None:
            return

        dialog = ProjectDetailDialog(project, self._get_logs, self._clear_logs, self)
        dialog.start_requested.connect(self._on_start_requested)
        dialog.stop_requested.connect(self.request_stop)
        dialog.restart_requested.connect(self.request_restart)
        dialog.settings_saved.connect(self._poll_db)
        dialog.finished.connect(lambda _result, pid=project_id: self._detail_dialogs.pop(pid, None))
        self._detail_dialogs[project_id] = dialog
        dialog.show()

    def _get_logs(self, project_id: int):
        runtime = self.monitoring.worker.get_runtime(project_id)
        return runtime.recent_logs() if runtime else []

    def _clear_logs(self, project_id: int) -> None:
        runtime = self.monitoring.worker.get_runtime(project_id)
        if runtime:
            runtime.logs.clear()

    def _handle_pending_projects(self, pending: list[DiscoveredProject]) -> None:
        for discovered in pending:
            dialog = NewProjectDialog(discovered, self)
            if dialog.exec() == NewProjectDialog.DialogCode.Accepted:
                add_discovered_project(discovered)
                if dialog.auto_add_future_projects():
                    self._settings.auto_add_future_projects = True
                    self._settings.save()
            else:
                ignore_discovered_project(discovered)
        self._poll_db()

    def _on_settings_changed(self) -> None:
        notifier.set_enabled(self._settings.show_desktop_notifications)
        QMessageBox.information(
            self,
            "Settings saved",
            "Settings saved. Restart Project Monitor for project-root and interval changes to take effect.",
        )

    # -- shutdown -------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.discovery.stop()
        self.monitoring.stop()
        super().closeEvent(event)
