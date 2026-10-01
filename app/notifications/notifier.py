"""Desktop notifications via `notify-send` (standard on Ubuntu/GNOME).

Uses a fixed argv list, never a shell, so a project name or error message
containing shell metacharacters cannot do anything but appear as text.
"""
from __future__ import annotations

import shutil
import subprocess

_APP_NAME = "Project Monitor"
_notify_send_path = shutil.which("notify-send")
_enabled = True


def is_available() -> bool:
    return _notify_send_path is not None


def set_enabled(enabled: bool) -> None:
    global _enabled
    _enabled = enabled


def notify(title: str, message: str, urgency: str = "normal") -> None:
    if _notify_send_path is None or not _enabled:
        return
    try:
        subprocess.run(
            [_notify_send_path, "--app-name", _APP_NAME, "--urgency", urgency, title, message],
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def notify_project_started(name: str, url: str | None = None) -> None:
    message = f'"{name}" started.' + (f" Running at {url}" if url else "")
    notify(_APP_NAME, message)


def notify_project_stopped(name: str) -> None:
    notify(_APP_NAME, f'"{name}" stopped.')


def notify_project_crashed(name: str) -> None:
    notify(_APP_NAME, f'"{name}" crashed.', urgency="critical")


def notify_port_conflict(name: str, port: int) -> None:
    notify(_APP_NAME, f'"{name}": port {port} is already in use.', urgency="critical")


def notify_project_error(name: str, error: str) -> None:
    notify(_APP_NAME, f'"{name}" error: {error}', urgency="critical")
