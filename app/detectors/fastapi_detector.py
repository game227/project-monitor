from __future__ import annotations

from pathlib import Path

from app.detectors.base import BaseDetector
from app.detectors.result import DetectionResult
from app.detectors.utils import find_venv_python, read_python_dependencies
from app.models.enums import ProjectType


class FastAPIDetector(BaseDetector):
    name = "fastapi"

    def detect(self, project_path: Path) -> DetectionResult | None:
        deps = read_python_dependencies(project_path)
        if "fastapi" not in deps:
            return None

        module = "main:app"
        for candidate, mod in (("main.py", "main:app"), ("app.py", "app:app")):
            if (project_path / candidate).is_file():
                module = mod
                break

        port = 8000
        venv_python = find_venv_python(project_path)
        # uvicorn as a bare command only works if it's on PATH; running
        # it as a module of the project's own interpreter is what
        # actually finds a venv-installed uvicorn + fastapi.
        start_command = f"{venv_python} -m uvicorn {module} --reload --port {port}" if venv_python else f"uvicorn {module} --reload --port {port}"
        return DetectionResult(
            project_type=ProjectType.FASTAPI,
            framework="FastAPI",
            language="Python",
            confidence=40,
            suggested_start_command=start_command,
            suggested_port=port,
        )
