from pathlib import Path

import pytest

import app.services.backup_service as backup_service
from app.models.project import Project


@pytest.fixture(autouse=True)
def _isolated_backups_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_service, "BACKUPS_DIR", tmp_path / "backups")


def _project(path: Path, project_id: int = 1) -> Project:
    project = Project(name="demo", path=str(path))
    project.id = project_id
    project.ignore_patterns = []
    return project


def test_create_backup_includes_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.py").write_text("print('hi')\n")
    (source / "sub").mkdir()
    (source / "sub" / "util.py").write_text("x = 1\n")

    info = backup_service.create_backup(_project(source))

    assert info.path.is_file()
    assert info.size_bytes > 0

    import zipfile

    with zipfile.ZipFile(info.path) as archive:
        names = set(archive.namelist())
    assert "main.py" in names
    assert "sub/util.py" in names


def test_create_backup_respects_ignore_patterns(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.py").write_text("print('hi')\n")
    (source / "node_modules").mkdir()
    (source / "node_modules" / "big.js").write_text("junk\n")

    project = _project(source)
    project.ignore_patterns = ["node_modules"]
    info = backup_service.create_backup(project)

    import zipfile

    with zipfile.ZipFile(info.path) as archive:
        names = archive.namelist()
    assert "main.py" in names
    assert not any("node_modules" in n for n in names)


def test_create_backup_missing_project_dir_raises(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(backup_service.BackupError):
        backup_service.create_backup(_project(missing))


def test_list_backups_returns_newest_first(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.txt").write_text("a")

    project = _project(source)
    first = backup_service.create_backup(project)
    import time

    time.sleep(1.01)  # backup filenames have 1-second resolution
    second = backup_service.create_backup(project)

    backups = backup_service.list_backups(project.id)
    assert [b.path for b in backups] == [second.path, first.path]


def test_restore_backup_writes_files_back(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "keep.txt").write_text("original")

    project = _project(source)
    backup_service.create_backup(project)

    (source / "keep.txt").write_text("modified")
    (source / "extra.txt").write_text("should remain, restore does not delete")

    [info] = backup_service.list_backups(project.id)
    backup_service.restore_backup(project, info.path)

    assert (source / "keep.txt").read_text() == "original"
    assert (source / "extra.txt").is_file()


def test_delete_backup_refuses_paths_outside_backups_dir(tmp_path: Path) -> None:
    outside = tmp_path / "not_a_backup.zip"
    outside.write_text("x")
    with pytest.raises(backup_service.BackupError):
        backup_service.delete_backup(outside)
    assert outside.is_file()


def test_delete_backup_removes_the_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.txt").write_text("a")
    project = _project(source)
    info = backup_service.create_backup(project)

    backup_service.delete_backup(info.path)

    assert not info.path.exists()
