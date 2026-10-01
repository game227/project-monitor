"""Project Monitor entry point.

Initializes the local SQLite database under ~/.config/project-monitor,
loads user settings, and opens the main window. All project scanning and
process monitoring happens on background QThreads started by MainWindow.
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.core.settings import Settings
from app.database.session import init_db
from app.ui.main_window import MainWindow
from app.ui.theme import DARK_STYLESHEET


def main() -> int:
    init_db()
    settings = Settings.load()

    app = QApplication(sys.argv)
    app.setApplicationName("Project Monitor")
    if settings.dark_mode:
        app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow(settings)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
