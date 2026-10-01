"""Loads the optional per-project `.project-monitor.json` override file.

Entirely optional: if a project has no such file, auto-detection is used
instead (see app/detectors). This file is only ever read, never written
by Project Monitor -- it is the user's own hand-authored config.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.paths import PROJECT_CONFIG_FILENAME


@dataclass
class ProjectConfigFile:
    name: str | None = None
    type: str | None = None
    working_directory: str | None = None
    start_command: str | None = None
    stop_command: str | None = None
    restart_command: str | None = None
    port: int | None = None
    auto_monitor: bool = True


def load_project_config(project_path: Path) -> ProjectConfigFile | None:
    config_path = project_path / PROJECT_CONFIG_FILENAME
    if not config_path.is_file():
        return None
    try:
        raw = json.loads(config_path.read_text(errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, dict):
        return None

    known_fields = set(ProjectConfigFile.__dataclass_fields__)
    filtered = {k: v for k, v in raw.items() if k in known_fields}
    return ProjectConfigFile(**filtered)
