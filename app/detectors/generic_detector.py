from __future__ import annotations

from pathlib import Path

from app.detectors.base import BaseDetector
from app.detectors.result import DetectionResult
from app.models.enums import ProjectType


class GenericDetector(BaseDetector):
    """Fallback: matches any directory at all, so every discovered folder
    ends up with *some* classification instead of being dropped.
    """

    name = "generic"

    def detect(self, project_path: Path) -> DetectionResult | None:
        if not project_path.is_dir():
            return None
        return DetectionResult(
            project_type=ProjectType.GENERIC,
            framework=None,
            language=None,
            confidence=1,
        )
