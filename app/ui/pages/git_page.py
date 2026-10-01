from __future__ import annotations

from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.models.project import Project

_COLUMNS = ["Project", "Branch", "Modified", "Untracked", "Ahead", "Behind", "Last commit"]


class GitPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

    def refresh(self, projects: list[Project]) -> None:
        git_projects = [p for p in projects if p.is_git_repo and not p.is_ignored]
        self._table.setRowCount(len(git_projects))
        for row, project in enumerate(git_projects):
            values = [
                project.name,
                project.git_branch or "-",
                str(project.git_modified_count),
                str(project.git_untracked_count),
                f"↑ {project.git_ahead}" if project.git_ahead else "-",
                f"↓ {project.git_behind}" if project.git_behind else "-",
                project.git_last_commit or "-",
            ]
            for col, value in enumerate(values):
                self._table.setItem(row, col, QTableWidgetItem(value))
