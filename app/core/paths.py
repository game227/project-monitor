"""Filesystem locations used by Project Monitor itself.

Project Monitor keeps all of its own state under ~/.config/project-monitor.
It never writes into a monitored project's directory.
"""
from __future__ import annotations

from pathlib import Path

APP_NAME = "project-monitor"

CONFIG_DIR = Path.home() / ".config" / APP_NAME
DATA_DIR = CONFIG_DIR
LOG_DIR = CONFIG_DIR / "logs"
DATABASE_PATH = DATA_DIR / "project_monitor.db"
SETTINGS_PATH = CONFIG_DIR / "settings.json"

PROJECT_CONFIG_FILENAME = ".project-monitor.json"

# Directory names ignored by default during discovery and file monitoring.
DEFAULT_IGNORE_PATTERNS: tuple[str, ...] = (
    ".git",
    "venv",
    ".venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "*.egg-info",
    ".env",
    ".DS_Store",
)


def ensure_app_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
