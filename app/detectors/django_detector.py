from __future__ import annotations

from pathlib import Path

from app.detectors.base import BaseDetector
from app.detectors.result import DetectionResult
from app.detectors.utils import find_venv_python
from app.models.enums import ProjectType


class DjangoDetector(BaseDetector):
    """Django: manage.py plus a settings.py somewhere in a first-level
    package directory (the usual <project>/<project>/settings.py layout).
    """

    name = "django"

    def detect(self, project_path: Path) -> DetectionResult | None:
        manage_py = project_path / "manage.py"
        if not manage_py.is_file():
            return None

        content = self._read_text(manage_py) or ""
        if "django.core.management" not in content and "execute_from_command_line" not in content:
            return None

        has_settings = any(project_path.glob("*/settings.py")) or any(
            project_path.glob("*/settings/__init__.py")
        )

        port = 8000
        python_bin = find_venv_python(project_path) or "python"
        return DetectionResult(
            project_type=ProjectType.DJANGO,
            framework="Django",
            language="Python",
            confidence=60 if has_settings else 55,
            suggested_start_command=f"{python_bin} manage.py runserver 127.0.0.1:{port}",
            suggested_port=port,
        )
