from pathlib import Path

from app.detectors.registry import detect_project
from app.models.enums import ProjectType


def test_generic_detector_matches_empty_dir(tmp_path: Path) -> None:
    summary = detect_project(tmp_path)
    assert summary.primary.project_type == ProjectType.GENERIC
    assert summary.is_git_repo is False


def test_git_repo_flag(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    summary = detect_project(tmp_path)
    assert summary.is_git_repo is True


def test_python_detector(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
    summary = detect_project(tmp_path)
    assert summary.primary.project_type == ProjectType.PYTHON


_MANAGE_PY = (
    "#!/usr/bin/env python\n"
    "import os\nimport sys\n\n"
    "def main():\n"
    "    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')\n"
    "    from django.core.management import execute_from_command_line\n"
    "    execute_from_command_line(sys.argv)\n"
)


def test_django_detector(tmp_path: Path) -> None:
    (tmp_path / "manage.py").write_text(_MANAGE_PY)
    pkg_dir = tmp_path / "mysite"
    pkg_dir.mkdir()
    (pkg_dir / "settings.py").write_text("DEBUG = True\n")

    summary = detect_project(tmp_path)
    assert summary.primary.project_type == ProjectType.DJANGO
    assert summary.primary.suggested_start_command.startswith("python manage.py runserver")


def test_django_detector_uses_project_venv_python(tmp_path: Path) -> None:
    (tmp_path / "manage.py").write_text(_MANAGE_PY)
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("")

    summary = detect_project(tmp_path)

    assert summary.primary.suggested_start_command.startswith(f"{venv_python} manage.py runserver")


def test_django_detector_ignores_non_django_manage_py(tmp_path: Path) -> None:
    (tmp_path / "manage.py").write_text("print('not django')\n")
    summary = detect_project(tmp_path)
    assert summary.primary.project_type != ProjectType.DJANGO


def test_flask_detector(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("Flask==3.0.0\n")
    (tmp_path / "app.py").write_text("app = None\n")
    summary = detect_project(tmp_path)
    assert summary.primary.project_type == ProjectType.FLASK
    assert summary.primary.suggested_start_command == "python app.py"


def test_fastapi_detector(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("fastapi==0.110.0\nuvicorn==0.29.0\n")
    (tmp_path / "main.py").write_text("app = None\n")
    summary = detect_project(tmp_path)
    assert summary.primary.project_type == ProjectType.FASTAPI


def test_node_detector(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "x", "dependencies": {}}')
    summary = detect_project(tmp_path)
    assert summary.primary.project_type == ProjectType.NODE


def test_react_detector_wins_over_node(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"name": "x", "dependencies": {"react": "^18.0.0"}, "scripts": {"dev": "vite"}}'
    )
    summary = detect_project(tmp_path)
    assert summary.primary.project_type == ProjectType.REACT
    assert summary.primary.suggested_start_command == "npm run dev"


def test_vue_detector(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"name": "x", "dependencies": {"vue": "^3.0.0"}, "scripts": {"serve": "vue-cli-service serve"}}'
    )
    summary = detect_project(tmp_path)
    assert summary.primary.project_type == ProjectType.VUE


def test_docker_detected_as_secondary_fact(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("django\n")
    (tmp_path / "manage.py").write_text(_MANAGE_PY)
    (tmp_path / "Dockerfile").write_text("FROM python:3.12\n")
    summary = detect_project(tmp_path)
    assert summary.primary.project_type == ProjectType.DJANGO
    assert summary.has_docker is True


def test_docker_is_primary_when_nothing_else_matches(tmp_path: Path) -> None:
    (tmp_path / "docker-compose.yml").write_text("services: {}\n")
    summary = detect_project(tmp_path)
    assert summary.primary.project_type == ProjectType.DOCKER
    assert summary.primary.suggested_start_command == "docker compose up"


def test_bad_json_does_not_crash_detection(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{not valid json")
    summary = detect_project(tmp_path)
    assert summary.primary.project_type == ProjectType.GENERIC
