"""Manual "Add Project" section (separate from auto-discovery): the user
points at a folder directly -- anywhere on disk, not just under a
configured project root -- previews what gets auto-detected, adjusts the
name/start command/port, and adds it.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.services.discovery_service import DiscoveredProject, inspect_path
from app.services.sync_service import ProjectAlreadyExistsError, add_manual_project
from app.ui.theme import GREEN, RED


class AddProjectPage(QWidget):
    project_added = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._discovered: DiscoveredProject | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        heading = QLabel("Add a project")
        heading.setObjectName("ProjectName")
        outer.addWidget(heading)
        sub = QLabel("Point at any folder on disk. Project Monitor detects its type; you can adjust anything before adding it.")
        sub.setObjectName("Muted")
        sub.setWordWrap(True)
        outer.addWidget(sub)

        path_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("/home/you/Projects/my-app")
        self._path_edit.editingFinished.connect(self._on_path_changed)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(self._path_edit, stretch=1)
        path_row.addWidget(browse_btn)
        outer.addLayout(path_row)

        preview = QFrame()
        preview.setObjectName("Card")
        form = QFormLayout(preview)

        self._name_edit = QLineEdit()
        self._type_label = QLabel("-")
        self._git_label = QLabel("-")
        self._start_command_edit = QLineEdit()
        self._start_command_edit.setPlaceholderText("Auto-detected if left empty")
        self._port_spin = QSpinBox()
        self._port_spin.setRange(0, 65535)
        self._port_spin.setSpecialValueText("(none)")

        form.addRow("Name", self._name_edit)
        form.addRow("Detected type", self._type_label)
        form.addRow("Git repository", self._git_label)
        form.addRow("Start command", self._start_command_edit)
        form.addRow("Port", self._port_spin)
        outer.addWidget(preview)

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        outer.addWidget(self._status_label)

        add_row = QHBoxLayout()
        add_row.addStretch(1)
        self._add_btn = QPushButton("Add project")
        self._add_btn.setObjectName("Primary")
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add)
        add_row.addWidget(self._add_btn)
        outer.addLayout(add_row)

        outer.addStretch(1)

    def _on_browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose a project folder")
        if path:
            self._path_edit.setText(path)
            self._on_path_changed()

    def _on_path_changed(self) -> None:
        path = self._path_edit.text().strip()
        self._discovered = None
        self._add_btn.setEnabled(False)
        self._status_label.setText("")

        if not path:
            self._reset_preview()
            return

        if not Path(path).expanduser().is_dir():
            self._reset_preview()
            self._status_label.setText("That folder doesn't exist.")
            self._status_label.setStyleSheet(f"color: {RED};")
            return

        discovered = inspect_path(path)
        self._discovered = discovered
        primary = discovered.detection.primary

        self._name_edit.setText(discovered.name)
        kind = primary.framework or primary.project_type.value.title()
        self._type_label.setText(f"{kind}" + (f" · {primary.language}" if primary.language else ""))
        self._git_label.setText("Yes" if discovered.detection.is_git_repo else "No")
        self._start_command_edit.setText(primary.suggested_start_command or "")
        self._port_spin.setValue(primary.suggested_port or 0)
        self._add_btn.setEnabled(True)

    def _reset_preview(self) -> None:
        self._name_edit.clear()
        self._type_label.setText("-")
        self._git_label.setText("-")
        self._start_command_edit.clear()
        self._port_spin.setValue(0)

    def _on_add(self) -> None:
        if self._discovered is None:
            return
        try:
            add_manual_project(
                self._discovered,
                name=self._name_edit.text().strip(),
                start_command=self._start_command_edit.text().strip(),
                primary_port=self._port_spin.value() or None,
            )
        except ProjectAlreadyExistsError as exc:
            self._status_label.setText(str(exc))
            self._status_label.setStyleSheet(f"color: {RED};")
            return

        self._status_label.setText(f"Added \"{self._name_edit.text().strip()}\".")
        self._status_label.setStyleSheet(f"color: {GREEN};")
        self._path_edit.clear()
        self._reset_preview()
        self._add_btn.setEnabled(False)
        self._discovered = None
        self.project_added.emit()
