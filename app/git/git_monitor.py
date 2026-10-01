"""Read-only git status reporting.

Every git invocation here is a fixed argv list (never shell=True, never
string-interpolated), and every command is read-only: status, branch,
rev-list, log. Project Monitor never commits, pushes, or pulls on the
user's behalf (see spec section 8).
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

_GIT_TIMEOUT_SECONDS = 5


@dataclass
class GitStatus:
    branch: str | None = None
    modified_count: int = 0
    untracked_count: int = 0
    ahead: int = 0
    behind: int = 0
    last_commit: str | None = None


def _run_git(project_path: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_path), *args],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def is_git_repo(project_path: Path) -> bool:
    return (project_path / ".git").is_dir()


def get_git_status(project_path: Path) -> GitStatus | None:
    if not is_git_repo(project_path):
        return None

    status = GitStatus()

    branch_out = _run_git(project_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    if branch_out is not None:
        status.branch = branch_out.strip() or None

    porcelain = _run_git(project_path, ["status", "--porcelain"])
    if porcelain is not None:
        modified = 0
        untracked = 0
        for line in porcelain.splitlines():
            if not line:
                continue
            if line.startswith("??"):
                untracked += 1
            else:
                modified += 1
        status.modified_count = modified
        status.untracked_count = untracked

    ahead_behind = _run_git(
        project_path, ["rev-list", "--left-right", "--count", "HEAD...@{upstream}"]
    )
    if ahead_behind is not None:
        parts = ahead_behind.split()
        if len(parts) == 2:
            try:
                status.ahead = int(parts[0])
                status.behind = int(parts[1])
            except ValueError:
                pass

    last_commit = _run_git(project_path, ["log", "-1", "--pretty=%h %s"])
    if last_commit is not None:
        status.last_commit = last_commit.strip() or None

    return status
