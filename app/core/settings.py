"""Persistent user settings, stored as JSON under ~/.config/project-monitor.

Kept separate from the SQLite database: settings are small, human-editable
configuration; the database is monitoring/state data.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.core.paths import DEFAULT_IGNORE_PATTERNS, SETTINGS_PATH, ensure_app_dirs

# Project Monitor's own install directory. Never scanned as a "monitored
# project" even if it happens to live under a configured project root.
_SELF_DIR = Path(__file__).resolve().parents[2]

_CANDIDATE_ROOTS = (
    "~/Projects",
    "~/Development",
    "~/Desktop/Projects",
    "~/GitHub",
)


def _default_project_roots() -> list[str]:
    """Pick sensible default roots on first run.

    Prefers dedicated project directories (~/Projects, ~/Development, ...).
    Falls back to ~/Desktop when none of those exist, since that is where
    this user's real project folders currently live.
    """
    found = [p for p in _CANDIDATE_ROOTS if Path(p).expanduser().is_dir()]
    if found:
        return found

    desktop = Path("~/Desktop").expanduser()
    if desktop.is_dir():
        return [str(desktop)]

    return []


@dataclass
class Settings:
    project_roots: list[str] = field(default_factory=_default_project_roots)
    ignore_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE_PATTERNS))

    scan_on_startup: bool = True
    monitor_new_projects_automatically: bool = True
    auto_detect_project_type: bool = True
    show_desktop_notifications: bool = True
    start_monitoring_automatically: bool = True
    auto_add_future_projects: bool = False

    cpu_ram_poll_interval_seconds: float = 2.0
    git_scan_interval_seconds: float = 7.0

    dark_mode: bool = True

    def excluded_paths(self) -> set[str]:
        """Paths that must never be treated as monitored projects."""
        return {str(_SELF_DIR)}

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def load(cls) -> "Settings":
        ensure_app_dirs()
        if not SETTINGS_PATH.exists():
            settings = cls()
            settings.save()
            return settings
        try:
            raw = json.loads(SETTINGS_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return cls()
        known_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in raw.items() if k in known_fields}
        return cls(**filtered)

    def save(self) -> None:
        ensure_app_dirs()
        SETTINGS_PATH.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
