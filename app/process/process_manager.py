"""Starts, stops, and restarts a project's process.

Commands are never run through a shell: they are split with shlex and
executed as a fixed argv list, which rules out shell-injection via a
project's configured start command. Each process runs in its own session
(start_new_session=True) so STOP can terminate the whole process tree
(e.g. `npm run dev` spawning a node child) instead of leaking orphans.
"""
from __future__ import annotations

import os
import shlex
import signal
import subprocess
import threading
import time
from dataclasses import dataclass

import psutil

_STOP_GRACE_SECONDS = 5


class InvalidCommandError(ValueError):
    pass


@dataclass
class RunningProcess:
    pid: int
    popen: subprocess.Popen
    started_at: float


class ProcessManager:
    """Owns the OS-level lifecycle of one project's process.

    One instance per monitored project; ProjectMonitor (app/monitors) is
    responsible for creating/holding these and reflecting state into the
    database.
    """

    def __init__(self) -> None:
        self._running: RunningProcess | None = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running is not None and self._running.popen.poll() is None

    @property
    def pid(self) -> int | None:
        with self._lock:
            return self._running.pid if self._running else None

    def uptime_seconds(self) -> float | None:
        with self._lock:
            if self._running is None:
                return None
            return time.monotonic() - self._running.started_at

    def start(
        self,
        command: str,
        working_directory: str,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.Popen:
        if self.is_running:
            raise RuntimeError("Process is already running")

        try:
            argv = shlex.split(command)
        except ValueError as exc:
            raise InvalidCommandError(f"Could not parse start command: {exc}") from exc
        if not argv:
            raise InvalidCommandError("Start command is empty")

        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)

        popen = subprocess.Popen(
            argv,
            cwd=working_directory,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )

        with self._lock:
            self._running = RunningProcess(pid=popen.pid, popen=popen, started_at=time.monotonic())

        return popen

    def stop(self) -> None:
        with self._lock:
            running = self._running
        if running is None:
            return

        try:
            pgid = os.getpgid(running.pid)
        except ProcessLookupError:
            pgid = None

        if pgid is not None:
            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                pgid = None

        if pgid is not None:
            try:
                running.popen.wait(timeout=_STOP_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                pass

            # popen.wait() only confirms the one process we spawned
            # exited. A dev-server reloader (Django's runserver, Flask's
            # debug reloader, nodemon, ...) runs the actual server as a
            # child of that process, in the same group: if the reloader
            # exits cleanly on SIGTERM but never forwarded it to its own
            # child, that child is left running and the project reports
            # STOPPED while its server keeps serving. Force anything
            # still in the group, every time, not just on a timeout.
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        with self._lock:
            self._running = None

    def poll_exit_code(self) -> int | None:
        with self._lock:
            if self._running is None:
                return None
            return self._running.popen.poll()

    def resource_usage(self) -> tuple[float, float] | None:
        """Returns (cpu_percent, ram_megabytes) summed across the process
        tree, or None if the process is not running / already gone.
        """
        pid = self.pid
        if pid is None:
            return None
        try:
            proc = psutil.Process(pid)
            procs = [proc] + proc.children(recursive=True)
            cpu = sum(p.cpu_percent(interval=None) for p in procs)
            ram_bytes = sum(p.memory_info().rss for p in procs)
            return cpu, ram_bytes / (1024 * 1024)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
