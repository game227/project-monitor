"""Scrollable list of ProjectCard widgets. Cards are created once per
project id and updated in place on every refresh so the UI never
flickers or loses scroll position while polling.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from app.models.project import Project
from app.ui.widgets.project_card import ProjectCard


class ProjectListWidget(QScrollArea):
    open_requested = Signal(int)
    start_requested = Signal(int)
    stop_requested = Signal(int)
    configure_requested = Signal(int)
    details_requested = Signal(int)

    def __init__(self, filter_fn: Callable[[Project], bool] | None = None) -> None:
        super().__init__()
        self._filter_fn = filter_fn or (lambda p: True)
        self._cards: dict[int, ProjectCard] = {}

        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setSpacing(10)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._empty_label = QLabel("No projects here yet.")
        self._empty_label.setObjectName("Muted")
        self._layout.addWidget(self._empty_label)

        self.setWidget(container)

    def refresh(self, projects: list[Project]) -> None:
        visible = [p for p in projects if self._filter_fn(p)]
        visible_ids = {p.id for p in visible}

        for project_id in list(self._cards):
            if project_id not in visible_ids:
                card = self._cards.pop(project_id)
                self._layout.removeWidget(card)
                card.deleteLater()

        for index, project in enumerate(visible):
            card = self._cards.get(project.id)
            if card is None:
                card = ProjectCard(project)
                self._cards[project.id] = card
                self._wire_card(card)
                self._layout.insertWidget(index, card)
            else:
                card.update_from_project(project)
                self._layout.removeWidget(card)
                self._layout.insertWidget(index, card)

        self._empty_label.setVisible(not visible)

    def _wire_card(self, card: ProjectCard) -> None:
        card.open_requested.connect(self.open_requested)
        card.start_requested.connect(self.start_requested)
        card.stop_requested.connect(self.stop_requested)
        card.configure_requested.connect(self.configure_requested)
        card.details_requested.connect(self.details_requested)
