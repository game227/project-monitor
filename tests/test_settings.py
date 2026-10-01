from pathlib import Path

import app.core.settings as settings_module
from app.core.settings import Settings


def test_round_trip(tmp_path: Path, monkeypatch) -> None:
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "SETTINGS_PATH", settings_path)

    original = Settings(project_roots=["/tmp/a", "/tmp/b"], dark_mode=False)
    original.save()

    loaded = Settings.load()
    assert loaded.project_roots == ["/tmp/a", "/tmp/b"]
    assert loaded.dark_mode is False


def test_load_ignores_unknown_fields(tmp_path: Path, monkeypatch) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text('{"project_roots": ["/x"], "totally_made_up_field": 123}')
    monkeypatch.setattr(settings_module, "SETTINGS_PATH", settings_path)

    loaded = Settings.load()
    assert loaded.project_roots == ["/x"]


def test_load_recovers_from_corrupt_file(tmp_path: Path, monkeypatch) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{not json")
    monkeypatch.setattr(settings_module, "SETTINGS_PATH", settings_path)

    loaded = Settings.load()
    assert isinstance(loaded, Settings)
