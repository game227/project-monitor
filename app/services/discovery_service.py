"""Finds candidate project directories under the user's configured
project roots. Read-only: it only lists directories and reads marker
files (package.json, requirements.txt, ...) to classify them -- it never
writes into a scanned project.
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from app.core.settings import Settings
from app.detectors.registry import ProjectDetectionSummary, detect_project
from app.services.project_config_service import load_project_config


@dataclass
class DiscoveredProject:
    name: str
    path: str
    detection: ProjectDetectionSummary
    config_override: object | None  # ProjectConfigFile | None, kept loosely typed to avoid import cycle


def _matches_any_pattern(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def inspect_path(path: str) -> DiscoveredProject:
    """Runs detection on a single, explicitly-chosen directory -- used by
    the "Add Project" page, where the user points at a folder directly
    instead of waiting for it to turn up under a configured root.
    """
    resolved = Path(path).expanduser().resolve()
    detection = detect_project(resolved)
    config_override = load_project_config(resolved)
    name = config_override.name if config_override and config_override.name else resolved.name
    return DiscoveredProject(name=name, path=str(resolved), detection=detection, config_override=config_override)


class ProjectDiscoveryService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def scan(self) -> list[DiscoveredProject]:
        discovered: list[DiscoveredProject] = []
        seen_paths: set[str] = set()
        excluded = self._settings.excluded_paths()

        for root_str in self._settings.project_roots:
            root = Path(root_str).expanduser()
            if not root.is_dir():
                continue

            try:
                children = sorted(root.iterdir())
            except OSError:
                continue

            for child in children:
                try:
                    if not child.is_dir():
                        continue
                except OSError:
                    continue

                resolved = str(child.resolve())
                if resolved in seen_paths or resolved in excluded:
                    continue
                if _matches_any_pattern(child.name, self._settings.ignore_patterns):
                    continue
                if child.name.startswith("."):
                    continue

                seen_paths.add(resolved)
                detection = detect_project(child)
                config_override = load_project_config(child)

                discovered.append(
                    DiscoveredProject(
                        name=(config_override.name if config_override and config_override.name else child.name),
                        path=resolved,
                        detection=detection,
                        config_override=config_override,
                    )
                )

        return discovered
