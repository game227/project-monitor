from __future__ import annotations

from pathlib import Path

from app.detectors.base import BaseDetector
from app.detectors.result import DetectionResult
from app.detectors.utils import package_json_has_dependency, read_package_json
from app.models.enums import ProjectType


class VueDetector(BaseDetector):
    name = "vue"

    def detect(self, project_path: Path) -> DetectionResult | None:
        package_json = read_package_json(project_path)
        if package_json is None or not package_json_has_dependency(package_json, "vue"):
            return None

        scripts = package_json.get("scripts", {})
        vite_present = package_json_has_dependency(package_json, "vite")

        start_command = None
        for script_name in ("dev", "serve", "start"):
            if script_name in scripts:
                start_command = f"npm run {script_name}"
                break

        port = 5173 if vite_present else 8080
        return DetectionResult(
            project_type=ProjectType.VUE,
            framework="Vue",
            language="JavaScript",
            confidence=45,
            suggested_start_command=start_command,
            suggested_port=port,
        )
