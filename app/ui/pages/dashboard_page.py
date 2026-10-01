from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.ui.widgets.project_list import ProjectListWidget
from app.ui.widgets.stat_tile import StatTile


class DashboardPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        tiles = QHBoxLayout()
        tiles.setSpacing(14)
        self._total_tile = StatTile("Total projects")
        self._running_tile = StatTile("Running")
        self._stopped_tile = StatTile("Stopped")
        self._errors_tile = StatTile("Errors")
        for tile in (self._total_tile, self._running_tile, self._stopped_tile, self._errors_tile):
            tiles.addWidget(tile)
        layout.addLayout(tiles)

        self.project_list = ProjectListWidget()
        layout.addWidget(self.project_list, stretch=1)

    def refresh(self, projects: list[Project]) -> None:
        monitored = [p for p in projects if not p.is_ignored]
        running = sum(1 for p in monitored if p.status == ProjectStatus.RUNNING)
        errors = sum(1 for p in monitored if p.status in (ProjectStatus.ERROR, ProjectStatus.CRASHED))
        stopped = sum(1 for p in monitored if p.status in (ProjectStatus.STOPPED, ProjectStatus.DISCOVERED))

        self._total_tile.set_value(str(len(monitored)))
        self._running_tile.set_value(str(running))
        self._stopped_tile.set_value(str(stopped))
        self._errors_tile.set_value(str(errors))

        self.project_list.refresh(monitored)
