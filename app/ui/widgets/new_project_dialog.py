from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from app.services.discovery_service import DiscoveredProject


class NewProjectDialog(QDialog):
    """The "NEW PROJECT DETECTED" prompt from spec section 16."""

    def __init__(self, discovered: DiscoveredProject, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New project detected")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        title = QLabel(f"<b>{discovered.name}</b>")
        layout.addWidget(title)

        primary = discovered.detection.primary
        kind = primary.framework or primary.project_type.value.title()
        layout.addWidget(QLabel(f"{kind} project detected."))
        layout.addWidget(QLabel(discovered.path))

        self._auto_add_checkbox = QCheckBox("Automatically add future projects")
        layout.addWidget(self._auto_add_checkbox)

        buttons = QDialogButtonBox()
        add_btn = buttons.addButton("ADD", QDialogButtonBox.ButtonRole.AcceptRole)
        ignore_btn = buttons.addButton("IGNORE", QDialogButtonBox.ButtonRole.RejectRole)
        add_btn.clicked.connect(self.accept)
        ignore_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def auto_add_future_projects(self) -> bool:
        return self._auto_add_checkbox.isChecked()
