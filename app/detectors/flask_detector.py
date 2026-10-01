from __future__ import annotations

from pathlib import Path

from app.detectors.base import BaseDetector
from app.detectors.result import DetectionResult
from app.detectors.utils import find_venv_python, read_python_dependencies
from app.models.enums import ProjectType


class FlaskDetector(BaseDetector):
    name = "flask"

    def detect(self, project_path: Path) -> DetectionResult | None:
        deps = read_python_dependencies(project_path)
        if "flask" not in deps:
            return None

        python_bin = find_venv_python(project_path) or "python"
        start_command = None
        for candidate in ("app.py", "main.py", "wsgi.py"):
            if (project_path / candidate).is_file():
                start_command = f"{python_bin} {candidate}"
                break

        port = 5000
        return DetectionResult(
            project_type=ProjectType.FLASK,
            framework="Flask",
            language="Python",
            confidence=40,
            suggested_start_command=start_command,
            suggested_port=port,
        )
