from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

_REQ_LINE_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")


def read_python_dependencies(project_path: Path) -> set[str]:
    """Best-effort set of lowercased dependency names declared by the
    project, gathered from requirements.txt and pyproject.toml.
    """
    names: set[str] = set()

    req_file = project_path / "requirements.txt"
    if req_file.is_file():
        try:
            for line in req_file.read_text(errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                match = _REQ_LINE_RE.match(line)
                if match:
                    names.add(match.group(1).lower())
        except OSError:
            pass

    pyproject = project_path / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(errors="ignore"))
        except (tomllib.TOMLDecodeError, OSError):
            data = {}

        for dep in data.get("project", {}).get("dependencies", []):
            match = _REQ_LINE_RE.match(dep)
            if match:
                names.add(match.group(1).lower())

        poetry_deps = (
            data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        )
        for dep_name in poetry_deps:
            names.add(dep_name.lower())

    return names


def read_package_json(project_path: Path) -> dict | None:
    pkg_file = project_path / "package.json"
    if not pkg_file.is_file():
        return None
    try:
        return json.loads(pkg_file.read_text(errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return None


def package_json_has_dependency(package_json: dict, name: str) -> bool:
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        if name in package_json.get(key, {}):
            return True
    return False


_VENV_DIR_NAMES = (".venv", "venv", "env")


def find_venv_python(project_path: Path) -> str | None:
    """Path to the project's own virtualenv interpreter, if it has one.

    A suggested start command that just runs "python" picks up whatever
    interpreter happens to be on Project Monitor's own PATH -- not the
    project's dependencies. Since the app doesn't activate a shell (see
    process_manager: no shell, fixed argv), a Django/Flask/FastAPI
    project with its own .venv needs its OWN python explicitly, or
    "import django" fails even though the project is set up correctly.
    """
    for name in _VENV_DIR_NAMES:
        candidate = project_path / name / "bin" / "python"
        if candidate.is_file():
            return str(candidate)
    return None
