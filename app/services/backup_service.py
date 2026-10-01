"""Project backups: zip snapshots of a project's working directory.

Backups are stored under Project Monitor's own state directory
(~/.config/project-monitor/backups/<project-id>/...), never inside the
monitored project itself -- consistent with "never write into a
monitored project" (spec section 18). Creating a backup only reads the
project; restoring is the one operation here that writes into it, and it
is never triggered automatically -- only from an explicit user action
the UI confirms first.
"""
from __future__ import annotations

import fnmatch
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.core.paths import CONFIG_DIR, DEFAULT_IGNORE_PATTERNS
from app.models.project import Project

BACKUPS_DIR = CONFIG_DIR / "backups"


@dataclass
class BackupInfo:
    path: Path
    created_at: float
    size_bytes: int

    @property
    def label(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at))


class BackupError(RuntimeError):
    pass


def _project_backup_dir(project_id: int) -> Path:
    backup_dir = BACKUPS_DIR / str(project_id)
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def _is_ignored(rel_parts: tuple[str, ...], patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(part, pattern) for part in rel_parts for pattern in patterns)


def create_backup(project: Project) -> BackupInfo:
    source = Path(project.path)
    if not source.is_dir():
        raise BackupError(f"Project folder not found: {project.path}")

    patterns = project.ignore_patterns or list(DEFAULT_IGNORE_PATTERNS)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    dest_path = _project_backup_dir(project.id) / f"backup_{timestamp}.zip"

    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in source.rglob("*"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(source)
            if _is_ignored(rel.parts, patterns):
                continue
            try:
                archive.write(file_path, arcname=str(rel))
            except OSError:
                continue  # unreadable file (permissions, broken symlink): skip, don't fail the whole backup

    stat = dest_path.stat()
    return BackupInfo(path=dest_path, created_at=stat.st_mtime, size_bytes=stat.st_size)


def list_backups(project_id: int) -> list[BackupInfo]:
    backup_dir = _project_backup_dir(project_id)
    infos = []
    for backup_file in backup_dir.glob("backup_*.zip"):
        stat = backup_file.stat()
        infos.append(BackupInfo(path=backup_file, created_at=stat.st_mtime, size_bytes=stat.st_size))
    return sorted(infos, key=lambda info: info.created_at, reverse=True)


def delete_backup(backup_path: Path) -> None:
    # Refuse to delete anything outside our own backups directory --
    # this function must never become a generic "delete this file" tool.
    if BACKUPS_DIR not in backup_path.resolve().parents:
        raise BackupError("Refusing to delete a path outside the backups directory")
    backup_path.unlink(missing_ok=True)


def restore_backup(project: Project, backup_path: Path) -> None:
    """Extracts a backup over the project's working directory. This is
    destructive (overwrites files) -- the caller (UI) must get explicit
    user confirmation before calling this.
    """
    if BACKUPS_DIR not in backup_path.resolve().parents:
        raise BackupError("Refusing to restore from a path outside the backups directory")
    if not backup_path.is_file():
        raise BackupError(f"Backup not found: {backup_path}")

    target = Path(project.path)
    target.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(backup_path, "r") as archive:
        for member in archive.infolist():
            member_path = (target / member.filename).resolve()
            if target.resolve() not in member_path.parents and member_path != target.resolve():
                # A malicious/corrupt archive entry trying to escape the
                # target directory (e.g. "../../etc/passwd"). Our own
                # create_backup() never produces these, but restore()
                # should not trust the zip blindly either.
                raise BackupError(f"Unsafe path in backup archive: {member.filename}")
        archive.extractall(target)
