import subprocess
from pathlib import Path

import pytest

from app.git.git_monitor import get_git_status, is_git_repo


def _run(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    _run(["init", "-q"], tmp_path)
    _run(["config", "user.email", "test@example.com"], tmp_path)
    _run(["config", "user.name", "Test"], tmp_path)
    (tmp_path / "README.md").write_text("hello\n")
    _run(["add", "README.md"], tmp_path)
    _run(["commit", "-q", "-m", "initial commit"], tmp_path)
    return tmp_path


def test_non_git_directory(tmp_path: Path) -> None:
    assert is_git_repo(tmp_path) is False
    assert get_git_status(tmp_path) is None


def test_clean_repo_status(git_repo: Path) -> None:
    status = get_git_status(git_repo)
    assert status is not None
    assert status.modified_count == 0
    assert status.untracked_count == 0
    assert status.last_commit is not None
    assert "initial commit" in status.last_commit


def test_modified_and_untracked_files_are_counted(git_repo: Path) -> None:
    (git_repo / "README.md").write_text("changed\n")
    (git_repo / "new_file.py").write_text("print(1)\n")

    status = get_git_status(git_repo)

    assert status.modified_count == 1
    assert status.untracked_count == 1
