"""Project Detail page (spec section 12): opens on DETAILS from a
project card. Tabs: Overview, Activity, Processes, Logs, Git, Backup,
Settings.

Non-modal so it can stay open and keep refreshing (Overview/Activity/
Processes/Git/Logs) while the user keeps working elsewhere in the app.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.paths import DEFAULT_IGNORE_PATTERNS
from app.filesystem.file_watcher import DirectoryWatcher, FileChangeEvent
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.process.log_manager import LogLine
from app.process.process_tree import list_process_tree
from app.services.backup_service import BackupError, BackupInfo, create_backup, delete_backup, list_backups, restore_backup
from app.services.sync_service import update_project_settings
from app.ui.format_utils import format_uptime, uptime_seconds_since
from app.ui.theme import GREEN, RED, status_color

GetLogsFn = Callable[[int], list[LogLine]]
ClearLogsFn = Callable[[int], None]


def _timestamp() -> str:
    return time.strftime("%H:%M:%S")


class OverviewTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        form = QFormLayout(self)
        self._status = QLabel()
        self._cpu = QLabel()
        self._ram = QLabel()
        self._pid = QLabel()
        self._port = QLabel()
        self._url = QLabel()
        self._uptime = QLabel()
        self._last_error = QLabel()
        self._last_error.setWordWrap(True)
        self._last_error.setObjectName("Muted")

        form.addRow("Status", self._status)
        form.addRow("CPU", self._cpu)
        form.addRow("RAM", self._ram)
        form.addRow("PID", self._pid)
        form.addRow("Port", self._port)
        form.addRow("URL", self._url)
        form.addRow("Uptime", self._uptime)
        form.addRow("Last error", self._last_error)

    def refresh(self, project: Project) -> None:
        status_value = project.status.value if hasattr(project.status, "value") else str(project.status)
        self._status.setText(status_value.capitalize())
        self._status.setStyleSheet(f"color: {status_color(status_value)}; font-weight: 600;")

        is_running = project.status == ProjectStatus.RUNNING
        self._cpu.setText(f"{project.cpu_percent:.0f}%" if is_running else "-")
        self._ram.setText(f"{project.ram_mb:.0f} MB" if is_running else "-")
        self._pid.setText(str(project.pid) if project.pid else "-")
        self._port.setText(str(project.primary_port) if project.primary_port else "-")
        self._url.setText(f"http://{project.host}:{project.primary_port}" if project.primary_port else "-")

        seconds = uptime_seconds_since(project.last_started_at) if is_running else None
        self._uptime.setText(format_uptime(seconds))
        self._last_error.setText(project.last_error or "-")


class ProcessesTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["PID", "CPU", "RAM", "Command"])
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

    def refresh(self, project: Project) -> None:
        infos = list_process_tree(project.pid) if project.pid else []
        self._table.setRowCount(len(infos))
        for row, info in enumerate(infos):
            values = [str(info.pid), f"{info.cpu_percent:.0f}%", f"{info.ram_mb:.0f} MB", info.command]
            for col, value in enumerate(values):
                self._table.setItem(row, col, QTableWidgetItem(value))


class SingleProjectLogsTab(QWidget):
    def __init__(self, project_id: int, get_logs_fn: GetLogsFn, clear_logs_fn: ClearLogsFn) -> None:
        super().__init__()
        self._project_id = project_id
        self._get_logs = get_logs_fn
        self._clear_logs = clear_logs_fn

        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search logs...")
        self._search.textChanged.connect(self._render)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._on_clear)
        toolbar.addWidget(self._search, stretch=1)
        toolbar.addWidget(clear_btn)
        layout.addLayout(toolbar)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        layout.addWidget(self._text)
        self._lines: list[LogLine] = []

    def refresh(self, _project: Project) -> None:
        self._lines = self._get_logs(self._project_id)
        self._render()

    def _render(self) -> None:
        query = self._search.text().strip().lower()
        rendered = []
        for line in self._lines:
            tag = "ERROR" if line.stream == "stderr" else "INFO"
            formatted = f"[{tag}] {line.text}"
            if not query or query in formatted.lower():
                rendered.append(formatted)
        scrollbar = self._text.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 4
        self._text.setPlainText("\n".join(rendered))
        if was_at_bottom or not rendered:
            scrollbar.setValue(scrollbar.maximum())

    def _on_clear(self) -> None:
        self._clear_logs(self._project_id)
        self._lines = []
        self._render()


class GitTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        form = QFormLayout(self)
        self._branch = QLabel()
        self._status = QLabel()
        self._ahead_behind = QLabel()
        self._last_commit = QLabel()
        self._last_commit.setWordWrap(True)

        form.addRow("Branch", self._branch)
        form.addRow("Status", self._status)
        form.addRow("Ahead / behind", self._ahead_behind)
        form.addRow("Last commit", self._last_commit)

    def refresh(self, project: Project) -> None:
        if not project.is_git_repo:
            self._branch.setText("Not a git repository")
            self._status.setText("-")
            self._ahead_behind.setText("-")
            self._last_commit.setText("-")
            return

        self._branch.setText(project.git_branch or "-")
        self._status.setText(f"{project.git_modified_count} modified, {project.git_untracked_count} untracked")
        self._ahead_behind.setText(f"↑ {project.git_ahead}   ↓ {project.git_behind}")
        self._last_commit.setText(project.git_last_commit or "-")


class ActivityTab(QWidget):
    """Everything happening in this project, merged into one live feed:
    file changes (instant, via watchdog), new log lines and status
    transitions (picked up on each refresh() -- the same ~2s cadence as
    the rest of the dialog). This is the "show me absolutely everything,
    live" view; Logs/Git/Files-specific detail still has its own tab for
    focused reading.
    """

    _file_event = Signal(object)  # FileChangeEvent

    def __init__(self, project_id: int, get_logs_fn: GetLogsFn) -> None:
        super().__init__()
        self._project_id = project_id
        self._get_logs = get_logs_fn
        self._watcher: DirectoryWatcher | None = None
        self._project_root: Path | None = None
        self._seen_log_lines = 0
        self._last_status: str | None = None

        layout = QVBoxLayout(self)
        self._list = QListWidget()
        layout.addWidget(self._list)
        self._file_event.connect(self._on_file_event)

    def start_watching(self, project: Project) -> None:
        self.stop_watching()
        self._project_root = Path(project.path)
        if not self._project_root.is_dir():
            self._prepend("This project's folder no longer exists on disk.")
            return
        ignore_names = project.ignore_patterns or list(DEFAULT_IGNORE_PATTERNS)
        self._watcher = DirectoryWatcher(
            project.path, callback=self._file_event.emit, ignore_names=ignore_names, recursive=True
        )
        self._watcher.start()

    def stop_watching(self) -> None:
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None

    def _on_file_event(self, event: FileChangeEvent) -> None:
        label = {"created": "CREATED", "modified": "MODIFIED", "deleted": "DELETED", "moved": "MOVED"}[event.kind]
        path = event.path
        if self._project_root is not None:
            try:
                path = str(Path(path).relative_to(self._project_root))
            except ValueError:
                pass
        self._prepend(f"FILE {label}: {path}")

    def refresh(self, project: Project) -> None:
        status_value = project.status.value if hasattr(project.status, "value") else str(project.status)
        if self._last_status is not None and status_value != self._last_status:
            self._prepend(f"STATUS: {self._last_status} -> {status_value}")
        self._last_status = status_value

        lines = self._get_logs(self._project_id)
        for line in lines[self._seen_log_lines :]:
            tag = "STDERR" if line.stream == "stderr" else "STDOUT"
            self._prepend(f"{tag}: {line.text}")
        self._seen_log_lines = len(lines)

    def _prepend(self, text: str) -> None:
        item = QListWidgetItem(f"[{_timestamp()}] {text}")
        self._list.insertItem(0, item)
        while self._list.count() > 300:
            self._list.takeItem(self._list.count() - 1)


class BackupTab(QWidget):
    """Create/restore/delete zip snapshots of the project (spec: backup
    capability). Backups live under Project Monitor's own state
    directory, never inside the project -- see backup_service.
    """

    def __init__(self, project: Project) -> None:
        super().__init__()
        self._project = project

        layout = QVBoxLayout(self)

        create_row = QHBoxLayout()
        self._create_btn = QPushButton("Create backup")
        self._create_btn.setObjectName("Primary")
        self._create_btn.clicked.connect(self._on_create)
        create_row.addWidget(self._create_btn)
        create_row.addStretch(1)
        layout.addLayout(create_row)

        self._status_label = QLabel()
        self._status_label.setObjectName("Muted")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Created", "Size"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._table)

        action_row = QHBoxLayout()
        self._restore_btn = QPushButton("Restore selected")
        self._delete_btn = QPushButton("Delete selected")
        self._delete_btn.setObjectName("Danger")
        self._restore_btn.clicked.connect(self._on_restore)
        self._delete_btn.clicked.connect(self._on_delete)
        action_row.addWidget(self._restore_btn)
        action_row.addWidget(self._delete_btn)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self._backups: list[BackupInfo] = []
        self.refresh_list()

    def refresh_list(self) -> None:
        self._backups = list_backups(self._project.id)
        self._table.setRowCount(len(self._backups))
        for row, info in enumerate(self._backups):
            self._table.setItem(row, 0, QTableWidgetItem(info.label))
            self._table.setItem(row, 1, QTableWidgetItem(f"{info.size_bytes / (1024 * 1024):.2f} MB"))

    def _selected_backup(self) -> BackupInfo | None:
        rows = {idx.row() for idx in self._table.selectedIndexes()}
        if len(rows) != 1:
            return None
        return self._backups[next(iter(rows))]

    def _on_create(self) -> None:
        self._create_btn.setEnabled(False)
        self._status_label.setStyleSheet("")
        self._status_label.setText("Creating backup...")
        try:
            info = create_backup(self._project)
        except BackupError as exc:
            self._status_label.setText(str(exc))
            self._status_label.setStyleSheet(f"color: {RED};")
        else:
            self._status_label.setText(f"Backup created: {info.label} ({info.size_bytes / (1024 * 1024):.2f} MB)")
            self._status_label.setStyleSheet(f"color: {GREEN};")
            self.refresh_list()
        finally:
            self._create_btn.setEnabled(True)

    def _on_restore(self) -> None:
        backup = self._selected_backup()
        if backup is None:
            self._status_label.setText("Select one backup to restore first.")
            return

        answer = QMessageBox.warning(
            self,
            "Restore backup",
            f"This will overwrite files in:\n{self._project.path}\n\n"
            f"with the contents of the backup from {backup.label}.\n\n"
            "Files changed since this backup was made will be lost. This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            restore_backup(self._project, backup.path)
        except BackupError as exc:
            self._status_label.setText(str(exc))
            self._status_label.setStyleSheet(f"color: {RED};")
        else:
            self._status_label.setText(f"Restored from {backup.label}.")
            self._status_label.setStyleSheet(f"color: {GREEN};")

    def _on_delete(self) -> None:
        backup = self._selected_backup()
        if backup is None:
            return
        answer = QMessageBox.question(self, "Delete backup", f"Delete the backup from {backup.label}?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_backup(backup.path)
        except BackupError as exc:
            self._status_label.setText(str(exc))
            self._status_label.setStyleSheet(f"color: {RED};")
        else:
            self.refresh_list()


class SettingsTab(QWidget):
    saved = Signal()

    def __init__(self, project: Project) -> None:
        super().__init__()
        self._project_id = project.id

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._start_edit = QLineEdit(project.start_command or "")
        self._stop_edit = QLineEdit(project.stop_command or "")
        self._restart_edit = QLineEdit(project.restart_command or "")
        self._dir_edit = QLineEdit(project.working_directory or project.path)
        dir_browse_btn = QPushButton("Browse...")
        dir_browse_btn.clicked.connect(self._on_browse_directory)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self._dir_edit)
        dir_row.addWidget(dir_browse_btn)

        self._port_spin = QSpinBox()
        self._port_spin.setRange(0, 65535)
        self._port_spin.setSpecialValueText("(none)")
        self._port_spin.setValue(project.primary_port or 0)

        form.addRow("Start command", self._start_edit)
        form.addRow("Stop command", self._stop_edit)
        form.addRow("Restart command", self._restart_edit)
        form.addRow("Working directory", dir_row)
        form.addRow("Port", self._port_spin)
        layout.addLayout(form)

        layout.addWidget(QLabel("Environment variables"))
        self._env_table = QTableWidget(0, 2)
        self._env_table.setHorizontalHeaderLabels(["Key", "Value"])
        self._env_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for key, value in (project.env_vars or {}).items():
            self._add_env_row(key, value)
        layout.addWidget(self._env_table)

        env_buttons = QHBoxLayout()
        add_env_btn = QPushButton("Add variable")
        remove_env_btn = QPushButton("Remove selected")
        add_env_btn.clicked.connect(lambda: self._add_env_row("", ""))
        remove_env_btn.clicked.connect(self._remove_selected_env_rows)
        env_buttons.addWidget(add_env_btn)
        env_buttons.addWidget(remove_env_btn)
        env_buttons.addStretch(1)
        layout.addLayout(env_buttons)

        layout.addWidget(QLabel("Ignore patterns (overrides global defaults when non-empty)"))
        self._ignore_list = QListWidget()
        self._ignore_list.addItems(project.ignore_patterns or [])
        layout.addWidget(self._ignore_list)

        ignore_buttons = QHBoxLayout()
        add_ignore_btn = QPushButton("Add pattern...")
        remove_ignore_btn = QPushButton("Remove selected")
        add_ignore_btn.clicked.connect(self._on_add_ignore)
        remove_ignore_btn.clicked.connect(self._remove_selected_ignore_rows)
        ignore_buttons.addWidget(add_ignore_btn)
        ignore_buttons.addWidget(remove_ignore_btn)
        ignore_buttons.addStretch(1)
        layout.addLayout(ignore_buttons)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._on_save)
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)

    def _on_browse_directory(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose working directory", self._dir_edit.text())
        if path:
            self._dir_edit.setText(path)

    def _add_env_row(self, key: str, value: str) -> None:
        row = self._env_table.rowCount()
        self._env_table.insertRow(row)
        self._env_table.setItem(row, 0, QTableWidgetItem(key))
        self._env_table.setItem(row, 1, QTableWidgetItem(value))

    def _remove_selected_env_rows(self) -> None:
        for row in sorted({idx.row() for idx in self._env_table.selectedIndexes()}, reverse=True):
            self._env_table.removeRow(row)

    def _on_add_ignore(self) -> None:
        text, ok = QInputDialog.getText(self, "Add ignore pattern", "Pattern (e.g. *.log):")
        if ok and text.strip():
            self._ignore_list.addItem(text.strip())

    def _remove_selected_ignore_rows(self) -> None:
        for item in self._ignore_list.selectedItems():
            self._ignore_list.takeItem(self._ignore_list.row(item))

    def _on_save(self) -> None:
        env_vars = {}
        for row in range(self._env_table.rowCount()):
            key_item = self._env_table.item(row, 0)
            value_item = self._env_table.item(row, 1)
            key = key_item.text().strip() if key_item else ""
            if key:
                env_vars[key] = value_item.text() if value_item else ""

        ignore_patterns = [self._ignore_list.item(i).text() for i in range(self._ignore_list.count())]
        port = self._port_spin.value() or None

        update_project_settings(
            self._project_id,
            start_command=self._start_edit.text().strip(),
            stop_command=self._stop_edit.text().strip(),
            restart_command=self._restart_edit.text().strip(),
            working_directory=self._dir_edit.text().strip(),
            primary_port=port,
            env_vars=env_vars,
            ignore_patterns=ignore_patterns,
        )
        self.saved.emit()


class ProjectDetailDialog(QDialog):
    start_requested = Signal(int)
    stop_requested = Signal(int)
    restart_requested = Signal(int)
    settings_saved = Signal()

    def __init__(self, project: Project, get_logs_fn: GetLogsFn, clear_logs_fn: ClearLogsFn, parent=None) -> None:
        super().__init__(parent)
        self.project_id = project.id
        self.setWindowTitle(project.name)
        self.setMinimumSize(640, 520)
        self.setModal(False)

        layout = QVBoxLayout(self)

        title = QLabel(project.name)
        title.setObjectName("ProjectName")
        layout.addWidget(title)

        actions = QHBoxLayout()
        self._start_btn = QPushButton("Start")
        self._stop_btn = QPushButton("Stop")
        self._restart_btn = QPushButton("Restart")
        self._start_btn.clicked.connect(lambda: self.start_requested.emit(self.project_id))
        self._stop_btn.clicked.connect(lambda: self.stop_requested.emit(self.project_id))
        self._restart_btn.clicked.connect(lambda: self.restart_requested.emit(self.project_id))
        actions.addWidget(self._start_btn)
        actions.addWidget(self._stop_btn)
        actions.addWidget(self._restart_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        self._tabs = QTabWidget()
        self._overview_tab = OverviewTab()
        self._activity_tab = ActivityTab(project.id, get_logs_fn)
        self._processes_tab = ProcessesTab()
        self._logs_tab = SingleProjectLogsTab(project.id, get_logs_fn, clear_logs_fn)
        self._git_tab = GitTab()
        self._backup_tab = BackupTab(project)
        self._settings_tab = SettingsTab(project)
        self._settings_tab.saved.connect(self.settings_saved)

        self._tabs.addTab(self._overview_tab, "Overview")
        self._tabs.addTab(self._activity_tab, "Activity")
        self._tabs.addTab(self._processes_tab, "Processes")
        self._tabs.addTab(self._logs_tab, "Logs")
        self._tabs.addTab(self._git_tab, "Git")
        self._tabs.addTab(self._backup_tab, "Backup")
        self._tabs.addTab(self._settings_tab, "Settings")
        layout.addWidget(self._tabs)

        self._activity_tab.start_watching(project)
        self.refresh(project)

    def refresh(self, project: Project) -> None:
        is_running = project.status == ProjectStatus.RUNNING
        is_busy = project.status in (ProjectStatus.STARTING, ProjectStatus.STOPPING)
        self._start_btn.setEnabled(not is_running and not is_busy)
        self._stop_btn.setEnabled(is_running)
        self._restart_btn.setEnabled(is_running)

        self._overview_tab.refresh(project)
        self._activity_tab.refresh(project)
        self._processes_tab.refresh(project)
        self._logs_tab.refresh(project)
        self._git_tab.refresh(project)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._activity_tab.stop_watching()
        super().closeEvent(event)
