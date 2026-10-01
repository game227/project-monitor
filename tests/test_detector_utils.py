from pathlib import Path

from app.detectors.utils import find_venv_python


def test_no_venv_returns_none(tmp_path: Path) -> None:
    assert find_venv_python(tmp_path) is None


def test_finds_dot_venv(tmp_path: Path) -> None:
    python_bin = tmp_path / ".venv" / "bin" / "python"
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("")
    assert find_venv_python(tmp_path) == str(python_bin)


def test_finds_plain_venv_dir(tmp_path: Path) -> None:
    python_bin = tmp_path / "venv" / "bin" / "python"
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("")
    assert find_venv_python(tmp_path) == str(python_bin)


def test_prefers_dot_venv_over_venv(tmp_path: Path) -> None:
    dot_venv = tmp_path / ".venv" / "bin" / "python"
    dot_venv.parent.mkdir(parents=True)
    dot_venv.write_text("")
    plain_venv = tmp_path / "venv" / "bin" / "python"
    plain_venv.parent.mkdir(parents=True)
    plain_venv.write_text("")
    assert find_venv_python(tmp_path) == str(dot_venv)


def test_ignores_directory_named_python(tmp_path: Path) -> None:
    (tmp_path / ".venv" / "bin" / "python").mkdir(parents=True)
    assert find_venv_python(tmp_path) is None
