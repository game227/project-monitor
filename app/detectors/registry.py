from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.detectors.base import BaseDetector
from app.detectors.django_detector import DjangoDetector
from app.detectors.docker_detector import DockerDetector
from app.detectors.fastapi_detector import FastAPIDetector
from app.detectors.flask_detector import FlaskDetector
from app.detectors.generic_detector import GenericDetector
from app.detectors.node_detector import NodeDetector
from app.detectors.python_detector import PythonDetector
from app.detectors.react_detector import ReactDetector
from app.detectors.result import DetectionResult
from app.detectors.vue_detector import VueDetector

# Registering a new project type/framework means: write a BaseDetector
# subclass and add an instance here. Nothing else needs to change for it
# to participate in discovery.
ALL_DETECTORS: list[BaseDetector] = [
    DjangoDetector(),
    FastAPIDetector(),
    FlaskDetector(),
    ReactDetector(),
    VueDetector(),
    NodeDetector(),
    PythonDetector(),
    DockerDetector(),
    GenericDetector(),
]


@dataclass
class ProjectDetectionSummary:
    primary: DetectionResult
    is_git_repo: bool
    has_docker: bool
    all_matches: list[DetectionResult]


def detect_project(project_path: Path) -> ProjectDetectionSummary:
    matches: list[DetectionResult] = []
    for detector in ALL_DETECTORS:
        try:
            result = detector.detect(project_path)
        except Exception:
            # One misbehaving detector must never break discovery for a
            # project, or for any other project in the same scan.
            result = None
        if result is not None:
            matches.append(result)

    matches.sort(key=lambda r: r.confidence, reverse=True)
    primary = matches[0] if matches else GenericDetector().detect(project_path)
    assert primary is not None

    return ProjectDetectionSummary(
        primary=primary,
        is_git_repo=(project_path / ".git").is_dir(),
        has_docker=any(m.framework and "docker" in m.framework.lower() for m in matches),
        all_matches=matches,
    )
