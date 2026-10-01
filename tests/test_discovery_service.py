from pathlib import Path

from app.core.settings import Settings
from app.models.enums import ProjectType
from app.services.discovery_service import ProjectDiscoveryService, inspect_path


def _settings_for(root: Path, **overrides) -> Settings:
    settings = Settings(project_roots=[str(root)])
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


def test_scan_finds_direct_subdirectories(tmp_path: Path) -> None:
    (tmp_path / "project-a").mkdir()
    (tmp_path / "project-b").mkdir()
    (tmp_path / "not-a-dir.txt").write_text("x")

    discovered = ProjectDiscoveryService(_settings_for(tmp_path)).scan()

    names = {d.name for d in discovered}
    assert names == {"project-a", "project-b"}


def test_scan_ignores_hidden_and_pattern_matched_dirs(tmp_path: Path) -> None:
    (tmp_path / "project-a").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "node_modules").mkdir()

    settings = _settings_for(tmp_path, ignore_patterns=["node_modules"])
    discovered = ProjectDiscoveryService(settings).scan()

    names = {d.name for d in discovered}
    assert names == {"project-a"}


def test_scan_skips_missing_root(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    discovered = ProjectDiscoveryService(_settings_for(missing)).scan()
    assert discovered == []


def test_scan_deduplicates_across_overlapping_roots(tmp_path: Path) -> None:
    (tmp_path / "project-a").mkdir()
    settings = Settings(project_roots=[str(tmp_path), str(tmp_path)])
    discovered = ProjectDiscoveryService(settings).scan()
    assert len(discovered) == 1


def test_inspect_path_detects_an_arbitrary_directory(tmp_path: Path) -> None:
    project_dir = tmp_path / "somewhere-else"
    project_dir.mkdir()
    (project_dir / "package.json").write_text('{"dependencies": {"vue": "^3.0.0"}}')

    result = inspect_path(str(project_dir))

    assert result.name == "somewhere-else"
    assert result.detection.primary.project_type == ProjectType.VUE
