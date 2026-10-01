from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.models.project import Project
from app.process.log_manager import LogLine

GetLogsFn = Callable[[int], list[LogLine]]
ClearLogsFn = Callable[[int], None]


class LogsPage(QWidget):
    def __init__(self, get_logs_fn: GetLogsFn, clear_logs_fn: ClearLogsFn) -> None:
        super().__init__()
        self._get_logs = get_logs_fn
        self._clear_logs = clear_logs_fn
        self._selected_project_id: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        splitter = QSplitter()

        self._project_list = QListWidget()
        self._project_list.setMaximumWidth(240)
        self._project_list.currentItemChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._project_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search logs...")
        self._search.textChanged.connect(self._render)
        clear_btn = QPushButton("Clear")
        copy_btn = QPushButton("Copy")
        export_btn = QPushButton("Export")
        clear_btn.clicked.connect(self._on_clear)
        copy_btn.clicked.connect(self._on_copy)
        export_btn.clicked.connect(self._on_export)
        toolbar.addWidget(self._search, stretch=1)
        toolbar.addWidget(clear_btn)
        toolbar.addWidget(copy_btn)
        toolbar.addWidget(export_btn)
        right_layout.addLayout(toolbar)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        right_layout.addWidget(self._text)

        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        self._lines: list[LogLine] = []

    def refresh(self, projects: list[Project]) -> None:
        monitored = [p for p in projects if not p.is_ignored]

        existing_ids = {
            self._project_list.item(i).data(1) for i in range(self._project_list.count())
        }
        wanted_ids = {p.id for p in monitored}

        if existing_ids != wanted_ids:
            current_id = self._selected_project_id
            self._project_list.clear()
            for project in monitored:
                item = QListWidgetItem(project.name)
                item.setData(1, project.id)
                self._project_list.addItem(item)
                if project.id == current_id:
                    self._project_list.setCurrentItem(item)

        if self._selected_project_id is not None:
            self._lines = self._get_logs(self._selected_project_id)
            self._render()

    def _on_selection_changed(self, current: QListWidgetItem | None, _previous) -> None:
        self._selected_project_id = current.data(1) if current else None
        self._lines = self._get_logs(self._selected_project_id) if self._selected_project_id else []
        self._render()

    def _render(self) -> None:
        query = self._search.text().strip().lower()
        text_lines = []
        for line in self._lines:
            tag = "ERROR" if line.stream == "stderr" else "INFO"
            formatted = f"[{tag}] {line.text}"
            if not query or query in formatted.lower():
                text_lines.append(formatted)

        scrollbar = self._text.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 4
        self._text.setPlainText("\n".join(text_lines))
        if was_at_bottom or not text_lines:
            scrollbar.setValue(scrollbar.maximum())

    def _on_clear(self) -> None:
        if self._selected_project_id is None:
            return
        self._clear_logs(self._selected_project_id)
        self._lines = []
        self._render()

    def _on_copy(self) -> None:
        self._text.selectAll()
        self._text.copy()
        cursor = self._text.textCursor()
        cursor.clearSelection()
        self._text.setTextCursor(cursor)

    def _on_export(self) -> None:
        if not self._lines:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export logs", "project-logs.txt", "Text files (*.txt)")
        if not path:
            return
        content = "\n".join(f"[{'ERROR' if l.stream == 'stderr' else 'INFO'}] {l.text}" for l in self._lines)
        with open(path, "w") as f:
            f.write(content)
