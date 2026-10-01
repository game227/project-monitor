from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.ui.widgets.project_list import ProjectListWidget

_ACTIVE = {ProjectStatus.RUNNING, ProjectStatus.STARTING, ProjectStatus.STOPPING}


class RunningPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        self.project_list = ProjectListWidget(filter_fn=lambda p: p.status in _ACTIVE)
        layout.addWidget(self.project_list)

    def refresh(self, projects: list[Project]) -> None:
        self.project_list.refresh(projects)
