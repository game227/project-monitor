"""One project card. Deliberately few buttons -- at most two actions
plus Details, chosen by state, rather than a fixed row of six (direct
feedback: too many buttons/colors was confusing). Restart and Logs live
inside the Details dialog instead of getting their own always-visible
buttons here.

    DTM Platform                    RUNNING
    Django · Python · Git
    127.0.0.1:8000
    CPU 8%   RAM 420MB   Uptime 01:24:32
    [OPEN] [STOP] [DETAILS]
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.ui.format_utils import format_uptime, uptime_seconds_since
from app.ui.theme import status_color

_BUSY_STATUSES = {"STARTING", "STOPPING"}


class ProjectCard(QFrame):
    open_requested = Signal(int)
    start_requested = Signal(int)
    stop_requested = Signal(int)
    configure_requested = Signal(int)
    details_requested = Signal(int)

    def __init__(self, project: Project) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.project_id = project.id

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(8)

        header = QHBoxLayout()
        self._name_label = QLabel()
        self._name_label.setObjectName("ProjectName")
        self._status_label = QLabel()
        header.addWidget(self._name_label)
        header.addStretch(1)
        header.addWidget(self._status_label)
        root.addLayout(header)

        self._meta_label = QLabel()
        self._meta_label.setObjectName("Muted")
        root.addWidget(self._meta_label)

        self._url_label = QLabel()
        self._url_label.setObjectName("Muted")
        root.addWidget(self._url_label)

        self._stats_label = QLabel()
        self._stats_label.setObjectName("Muted")
        root.addWidget(self._stats_label)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self._open_btn = QPushButton("Open")
        self._start_btn = QPushButton("Start")
        self._stop_btn = QPushButton("Stop")
        self._configure_btn = QPushButton("Set up")
        self._details_btn = QPushButton("Details")

        self._open_btn.setObjectName("Primary")
        self._open_btn.clicked.connect(lambda: self.open_requested.emit(self.project_id))
        self._start_btn.clicked.connect(lambda: self.start_requested.emit(self.project_id))
        self._stop_btn.setObjectName("Danger")
        self._stop_btn.clicked.connect(lambda: self.stop_requested.emit(self.project_id))
        self._configure_btn.clicked.connect(lambda: self.configure_requested.emit(self.project_id))
        self._details_btn.clicked.connect(lambda: self.details_requested.emit(self.project_id))

        for btn in (self._open_btn, self._start_btn, self._stop_btn, self._configure_btn, self._details_btn):
            actions.addWidget(btn)
        actions.addStretch(1)
        root.addLayout(actions)

        self.update_from_project(project)

    def update_from_project(self, project: Project) -> None:
        self._name_label.setText(project.name)

        status = project.status
        status_value = status.value if hasattr(status, "value") else str(status)
        self._status_label.setText(status_value.capitalize())
        self._status_label.setStyleSheet(f"color: {status_color(status_value)}; font-weight: 600;")

        type_label = str(project.project_type.value if hasattr(project.project_type, "value") else project.project_type)
        tags = [project.framework] if project.framework else [type_label.capitalize()]
        if project.language and project.language.lower() not in (t.lower() for t in tags):
            tags.append(project.language)
        if project.is_git_repo:
            tags.append("Git")
        self._meta_label.setText(" · ".join(tags))

        if project.primary_port:
            self._url_label.setText(f"{project.host}:{project.primary_port}")
            self._url_label.show()
        else:
            self._url_label.hide()

        is_running = status_value == "RUNNING"
        is_busy = status_value in _BUSY_STATUSES

        seconds = uptime_seconds_since(project.last_started_at) if is_running else None
        uptime = format_uptime(seconds)
        self._stats_label.setText(
            f"CPU {project.cpu_percent:.0f}%   RAM {project.ram_mb:.0f}MB   Uptime {uptime}"
            if is_running
            else "Not running"
        )

        # Show only what applies right now: needs setup, running, or
        # stopped -- never all six actions at once.
        needs_setup = not project.start_command
        self._configure_btn.setVisible(needs_setup)
        self._start_btn.setVisible(not needs_setup and not is_running and not is_busy)
        self._open_btn.setVisible(is_running and bool(project.primary_port))
        self._stop_btn.setVisible(is_running or is_busy)
        self._stop_btn.setEnabled(not is_busy)
