from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from app.models.project import Project
from app.ui.widgets.project_list import ProjectListWidget


class ProjectsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search projects...")
        self._search.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search)

        self.project_list = ProjectListWidget(filter_fn=self._matches_search)
        layout.addWidget(self.project_list, stretch=1)

        self._projects: list[Project] = []
        self._query = ""

    def _matches_search(self, project: Project) -> bool:
        if project.is_ignored:
            return False
        if not self._query:
            return True
        return self._query in project.name.lower()

    def _on_search_changed(self, text: str) -> None:
        self._query = text.strip().lower()
        self.project_list.refresh(self._projects)

    def refresh(self, projects: list[Project]) -> None:
        self._projects = projects
        self.project_list.refresh(projects)
