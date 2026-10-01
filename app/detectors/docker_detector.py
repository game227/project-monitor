from __future__ import annotations

from pathlib import Path

from app.detectors.base import BaseDetector
from app.detectors.result import DetectionResult
from app.models.enums import ProjectType

_COMPOSE_FILES = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")


class DockerDetector(BaseDetector):
    """Docker is treated as a project type only when nothing more specific
    (a language/framework detector) also matches; otherwise it just means
    "this project also has a Dockerfile", which the discovery service can
    still surface as a fact even though it isn't the primary type.
    """

    name = "docker"

    def detect(self, project_path: Path) -> DetectionResult | None:
        has_dockerfile = (project_path / "Dockerfile").is_file()
        compose_file = next(
            (f for f in _COMPOSE_FILES if (project_path / f).is_file()), None
        )
        if not has_dockerfile and not compose_file:
            return None

        start_command = "docker compose up" if compose_file else "docker build -t app . && docker run app"

        return DetectionResult(
            project_type=ProjectType.DOCKER,
            framework="Docker Compose" if compose_file else "Docker",
            language=None,
            confidence=15,
            suggested_start_command=start_command,
        )
