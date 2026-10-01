"""Coordinates process lifecycle + periodic polling for every monitored
project, and persists the results to the database.

Each project's poll/start/stop runs in its own try/except: a crash or
bug while handling one project is recorded as that project's ERROR
status and never stops the others from being monitored (spec section 24).
"""
from __future__ import annotations

import time

from app.core.settings import Settings
from app.database.session import session_scope
from app.git.git_monitor import GitStatus
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.monitors.project_runtime import ProjectRuntime
from app.notifications import notifier
from app.process.port_scanner import find_pid_using_port, is_port_in_use
from app.services.project_repository import ProjectRepository

_ACTIVE_STATUSES = {ProjectStatus.STARTING, ProjectStatus.RUNNING, ProjectStatus.STOPPING}


class MonitoringCoordinator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._runtimes: dict[int, ProjectRuntime] = {}
        self._last_git_scan: dict[int, float] = {}

    def _runtime(self, project_id: int) -> ProjectRuntime:
        if project_id not in self._runtimes:
            self._runtimes[project_id] = ProjectRuntime(project_id)
        return self._runtimes[project_id]

    def get_runtime(self, project_id: int) -> ProjectRuntime | None:
        """Read-only lookup for the UI's Logs page. Safe to call from any
        thread: it only returns a reference to state a lock already
        protects (ProjectRuntime.logs), never mutates anything here.
        """
        return self._runtimes.get(project_id)

    # -- lifecycle -----------------------------------------------------

    def start_project(self, project_id: int) -> None:
        # The outer try/except guards session_scope itself (e.g. a
        # transient SQLite commit failure), not just runtime.start(): an
        # unhandled exception here would otherwise escape into the Qt
        # slot that calls this and print a raw traceback instead of
        # landing on this project as an ERROR status.
        try:
            with session_scope() as session:
                repo = ProjectRepository(session)
                project = repo.get_by_id(project_id)
                if project is None:
                    return
                if not project.start_command:
                    project.status = ProjectStatus.ERROR
                    project.last_error = "No start command configured"
                    return

                if project.primary_port and is_port_in_use(project.primary_port):
                    owner_pid = find_pid_using_port(project.primary_port)
                    if owner_pid != project.pid:
                        project.status = ProjectStatus.ERROR
                        project.last_error = f"Port conflict: {project.primary_port} already in use"
                        notifier.notify_port_conflict(project.name, project.primary_port)
                        return

                project.status = ProjectStatus.STARTING
                try:
                    runtime = self._runtime(project.id)
                    runtime.start(
                        project.start_command,
                        project.working_directory or project.path,
                        project.env_vars or None,
                    )
                except Exception as exc:  # noqa: BLE001 - isolate this project's failure
                    project.status = ProjectStatus.ERROR
                    project.last_error = str(exc)
                    notifier.notify_project_error(project.name, str(exc))
                    return

                project.status = ProjectStatus.RUNNING
                project.pid = runtime.process.pid
                project.last_started_at = _now()
                project.last_error = None
                url = f"http://{project.host}:{project.primary_port}" if project.primary_port else None
                notifier.notify_project_started(project.name, url)
        except Exception:  # noqa: BLE001 - see comment above
            pass

    def stop_project(self, project_id: int) -> None:
        try:
            with session_scope() as session:
                repo = ProjectRepository(session)
                project = repo.get_by_id(project_id)
                if project is None:
                    return

                project.status = ProjectStatus.STOPPING
                try:
                    self._runtime(project.id).stop()
                except Exception as exc:  # noqa: BLE001
                    project.status = ProjectStatus.ERROR
                    project.last_error = str(exc)
                    notifier.notify_project_error(project.name, str(exc))
                    return

                project.status = ProjectStatus.STOPPED
                project.pid = None
                project.cpu_percent = 0.0
                project.ram_mb = 0.0
                project.last_stopped_at = _now()
                notifier.notify_project_stopped(project.name)
        except Exception:  # noqa: BLE001 - see start_project's comment
            pass

    def restart_project(self, project_id: int) -> None:
        self.stop_project(project_id)
        self.start_project(project_id)

    # -- polling ---------------------------------------------------------

    def tick(self) -> None:
        try:
            with session_scope() as session:
                repo = ProjectRepository(session)
                for project in repo.list_all():
                    if not project.is_monitored or project.is_ignored:
                        continue
                    try:
                        self._poll_one(project)
                    except Exception as exc:  # noqa: BLE001 - one bad project can't break the tick
                        project.status = ProjectStatus.ERROR
                        project.last_error = f"Monitoring error: {exc}"
        except Exception:  # noqa: BLE001 - a transient DB failure must not kill the timer loop
            pass

    def _poll_one(self, project: Project) -> None:
        if project.id not in self._runtimes and project.status not in _ACTIVE_STATUSES:
            # Never started this session and not marked active: nothing to poll.
            return

        runtime = self._runtime(project.id)
        now = time.monotonic()
        git_due = now - self._last_git_scan.get(project.id, 0.0) >= self._settings.git_scan_interval_seconds

        snapshot = runtime.poll(project.path, git_due)

        if git_due:
            self._last_git_scan[project.id] = now
        if snapshot.git is not None:
            _apply_git_status(project, snapshot.git)

        if snapshot.exited_unexpectedly:
            project.status = ProjectStatus.CRASHED
            project.pid = None
            project.cpu_percent = 0.0
            project.ram_mb = 0.0
            project.last_stopped_at = _now()
            project.last_error = snapshot.last_error
            notifier.notify_project_crashed(project.name)
            return

        if snapshot.is_running:
            project.status = ProjectStatus.RUNNING
            project.pid = snapshot.pid
            project.cpu_percent = round(snapshot.cpu_percent, 1)
            project.ram_mb = round(snapshot.ram_mb, 1)
            if snapshot.ports:
                project.detected_ports = snapshot.ports
                if project.primary_port is None:
                    project.primary_port = snapshot.ports[0]


def _apply_git_status(project: Project, git: GitStatus) -> None:
    project.git_branch = git.branch
    project.git_modified_count = git.modified_count
    project.git_untracked_count = git.untracked_count
    project.git_ahead = git.ahead
    project.git_behind = git.behind
    project.git_last_commit = git.last_commit


def _now():
    import datetime as dt

    return dt.datetime.now(dt.timezone.utc)
