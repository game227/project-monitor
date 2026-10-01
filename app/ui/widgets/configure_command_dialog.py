from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit


class ConfigureCommandDialog(QDialog):
    """Shown when a project's start command couldn't be confidently
    auto-detected. The user sets it once; it is then saved and reused
    automatically (spec section 6).
    """

    def __init__(self, project_name: str, working_directory: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Configure start command - {project_name}")
        self.setMinimumWidth(420)

        layout = QFormLayout(self)

        self._start_edit = QLineEdit()
        self._start_edit.setPlaceholderText("e.g. python manage.py runserver 127.0.0.1:8000")
        layout.addRow("Start command", self._start_edit)

        self._stop_edit = QLineEdit()
        self._stop_edit.setPlaceholderText("Leave empty to just terminate the process")
        layout.addRow("Stop command (optional)", self._stop_edit)

        self._dir_edit = QLineEdit(working_directory)
        layout.addRow("Working directory", self._dir_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def start_command(self) -> str:
        return self._start_edit.text().strip()

    def stop_command(self) -> str:
        return self._stop_edit.text().strip()

    def working_directory(self) -> str:
        return self._dir_edit.text().strip()
