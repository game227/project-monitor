from pathlib import Path

from app.services.project_config_service import load_project_config


def test_missing_config_returns_none(tmp_path: Path) -> None:
    assert load_project_config(tmp_path) is None


def test_valid_config_is_loaded(tmp_path: Path) -> None:
    (tmp_path / ".project-monitor.json").write_text(
        """
        {
            "name": "DTM Platform",
            "type": "django",
            "start_command": "python manage.py runserver 127.0.0.1:8000",
            "port": 8000
        }
        """
    )
    config = load_project_config(tmp_path)
    assert config is not None
    assert config.name == "DTM Platform"
    assert config.port == 8000


def test_invalid_json_is_ignored(tmp_path: Path) -> None:
    (tmp_path / ".project-monitor.json").write_text("{not valid")
    assert load_project_config(tmp_path) is None


def test_unknown_fields_are_dropped(tmp_path: Path) -> None:
    (tmp_path / ".project-monitor.json").write_text('{"name": "X", "made_up": true}')
    config = load_project_config(tmp_path)
    assert config is not None
    assert config.name == "X"
