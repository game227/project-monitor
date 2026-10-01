"""Live, in-memory runtime state for one monitored project: its process,
captured logs, and cached git/port facts. One instance per project,
created on demand and kept for the app's lifetime so START/STOP/RESTART
and the Logs tab have somewhere to live between UI refreshes.

This is intentionally Qt-free -- app/ui wraps a collection of these in a
timer-driven worker (see app/ui/monitoring_worker.py) instead of this
module depending on Qt.
"""
from __future__ import annotations

from dataclasses import dataclass

from pathlib import Path

from app.git.git_monitor import GitStatus, get_git_status
from app.process.log_manager import LogLine, LogManager
from app.process.port_scanner import ports_for_pid
from app.process.process_manager import ProcessManager


@dataclass
class ProjectRuntimeSnapshot:
    is_running: bool
    pid: int | None
    cpu_percent: float
    ram_mb: float
    uptime_seconds: float | None
    ports: list[int]
    git: GitStatus | None
    last_error: str | None
    exited_unexpectedly: bool


class ProjectRuntime:
    def __init__(self, project_id: int) -> None:
        self.project_id = project_id
        self.process = ProcessManager()
        self.logs = LogManager()
        self._was_running = False

    def start(self, command: str, working_directory: str, env: dict[str, str] | None = None) -> None:
        popen = self.process.start(command, working_directory, env)
        self.logs.clear()
        self.logs.attach(popen)
        self._was_running = True

    def stop(self) -> None:
        self.process.stop()
        self._was_running = False

    def poll(self, project_path: str, git_scan_due: bool) -> ProjectRuntimeSnapshot:
        is_running = self.process.is_running
        exited_unexpectedly = self._was_running and not is_running
        self._was_running = is_running

        cpu = ram = 0.0
        uptime = None
        ports: list[int] = []
        pid = self.process.pid
        if is_running:
            usage = self.process.resource_usage()
            if usage is not None:
                cpu, ram = usage
            uptime = self.process.uptime_seconds()
            if pid is not None:
                ports = ports_for_pid(pid)

        git = get_git_status_safe(project_path) if git_scan_due else None

        return ProjectRuntimeSnapshot(
            is_running=is_running,
            pid=pid,
            cpu_percent=cpu,
            ram_mb=ram,
            uptime_seconds=uptime,
            ports=ports,
            git=git,
            last_error=self.logs.last_error,
            exited_unexpectedly=exited_unexpectedly,
        )

    def recent_logs(self) -> list[LogLine]:
        return self.logs.snapshot()


def get_git_status_safe(project_path: str) -> GitStatus | None:
    try:
        return get_git_status(Path(project_path))
    except Exception:
        return None
