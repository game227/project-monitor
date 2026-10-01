from __future__ import annotations

from pathlib import Path

from app.detectors.base import BaseDetector
from app.detectors.result import DetectionResult
from app.detectors.utils import read_package_json
from app.models.enums import ProjectType


class NodeDetector(BaseDetector):
    """Generic Node.js project. Overridden by React/Vue when their
    dependency is present, since those report higher confidence.
    """

    name = "node"

    def detect(self, project_path: Path) -> DetectionResult | None:
        package_json = read_package_json(project_path)
        if package_json is None:
            return None

        scripts = package_json.get("scripts", {})
        start_command = None
        for script_name in ("dev", "start"):
            if script_name in scripts:
                start_command = f"npm run {script_name}"
                break

        return DetectionResult(
            project_type=ProjectType.NODE,
            framework=None,
            language="JavaScript",
            confidence=20,
            suggested_start_command=start_command,
        )
