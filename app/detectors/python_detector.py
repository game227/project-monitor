from __future__ import annotations

from pathlib import Path

from app.detectors.base import BaseDetector
from app.detectors.result import DetectionResult
from app.detectors.utils import find_venv_python
from app.models.enums import ProjectType

_MARKERS = ("requirements.txt", "pyproject.toml", "setup.py", "manage.py")


class PythonDetector(BaseDetector):
    """Generic Python project: any recognizable Python packaging marker.

    More specific detectors (Django, Flask, FastAPI) override this when
    they also match, because they report higher confidence.
    """

    name = "python"

    def detect(self, project_path: Path) -> DetectionResult | None:
        if not any((project_path / marker).exists() for marker in _MARKERS):
            return None

        python_bin = find_venv_python(project_path) or "python"
        start_command = None
        if (project_path / "manage.py").is_file():
            start_command = None  # left to DjangoDetector
        elif (project_path / "main.py").is_file():
            start_command = f"{python_bin} main.py"
        elif (project_path / "app.py").is_file():
            start_command = f"{python_bin} app.py"

        return DetectionResult(
            project_type=ProjectType.PYTHON,
            framework=None,
            language="Python",
            confidence=20,
            suggested_start_command=start_command,
        )
