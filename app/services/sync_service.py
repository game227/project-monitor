"""Reconciles ProjectDiscoveryService results with the database.

Existing projects get their detected facts (type/framework/language, and
an auto-suggested start command) refreshed for as long as command_source
stays "auto-detected" -- the moment a user edits the command (Configure
dialog, Settings tab), command_source flips to "user" and this stops
touching it. Brand-new paths are either auto-added (when the user opted
into "Automatically add future projects") or handed back to the caller
so the UI can show a NEW PROJECT DETECTED prompt.
"""
from __future__ import annotations

from app.core.settings import Settings
from app.database.session import session_scope
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.services.discovery_service import DiscoveredProject, ProjectDiscoveryService
from app.services.project_repository import ProjectRepository


def _apply_detection(project: Project, discovered: DiscoveredProject) -> None:
    primary = discovered.detection.primary
    project.project_type = primary.project_type
    project.framework = primary.framework
    project.language = primary.language
    project.is_git_repo = discovered.detection.is_git_repo

    override = discovered.config_override
    if project.command_source == "auto-detected":
        if override and override.start_command:
            project.start_command = override.start_command
            project.stop_command = override.stop_command
            project.restart_command = override.restart_command
            project.working_directory = override.working_directory or discovered.path
            project.command_source = "project-file"
        elif primary.suggested_start_command:
            # Keep it in sync with current detection (e.g. a venv that
            # didn't exist on the first scan, or a detector fix) as long
            # as the user hasn't taken ownership of the command.
            project.start_command = primary.suggested_start_command
            project.working_directory = discovered.path

    if project.primary_port is None:
        if override and override.port:
            project.primary_port = override.port
        elif primary.suggested_port:
            project.primary_port = primary.suggested_port


def build_new_project(discovered: DiscoveredProject) -> Project:
    # command_source is set explicitly (not left to the column default):
    # SQLAlchemy's mapped_column(default=...) only materializes at flush
    # time, but _apply_detection's "auto-detected" check below runs on
    # this still-unflushed object.
    project = Project(
        name=discovered.name,
        path=discovered.path,
        working_directory=discovered.path,
        command_source="auto-detected",
    )
    _apply_detection(project, discovered)
    return project


def sync_discovered_projects(settings: Settings) -> list[DiscoveredProject]:
    """Runs a scan and updates the database. Returns the subset of
    discovered projects that are new AND were not auto-added, i.e. what
    the UI should prompt the user about.
    """
    discovery = ProjectDiscoveryService(settings)
    discovered_projects = discovery.scan()

    pending_prompt: list[DiscoveredProject] = []

    with session_scope() as session:
        repo = ProjectRepository(session)

        for discovered in discovered_projects:
            existing = repo.get_by_path(discovered.path)
            if existing is not None:
                _apply_detection(existing, discovered)
                continue

            if settings.auto_add_future_projects:
                repo.add(build_new_project(discovered))
            else:
                pending_prompt.append(discovered)

    return pending_prompt


def add_discovered_project(discovered: DiscoveredProject) -> Project:
    with session_scope() as session:
        repo = ProjectRepository(session)
        existing = repo.get_by_path(discovered.path)
        if existing is not None:
            return existing
        project = build_new_project(discovered)
        repo.add(project)
        session.refresh(project)
        session.expunge(project)
        return project


class ProjectAlreadyExistsError(ValueError):
    def __init__(self, path: str) -> None:
        super().__init__(f"'{path}' is already a monitored project")
        self.path = path


def add_manual_project(
    discovered: DiscoveredProject, *, name: str, start_command: str, primary_port: int | None
) -> Project:
    """Adds a project the user pointed at directly (Add Project page),
    with their name/start-command/port overrides layered on top of
    whatever auto-detection found.
    """
    with session_scope() as session:
        repo = ProjectRepository(session)
        if repo.get_by_path(discovered.path) is not None:
            raise ProjectAlreadyExistsError(discovered.path)

        project = build_new_project(discovered)
        if name:
            project.name = name
        if start_command:
            project.start_command = start_command
            project.command_source = "user"
        if primary_port:
            project.primary_port = primary_port

        repo.add(project)
        session.refresh(project)
        session.expunge(project)
        return project


def set_project_command(
    project_id: int, start_command: str, stop_command: str, working_directory: str
) -> None:
    """User-supplied command from the "Configure Start Command" dialog.
    Marked command_source="user" so future detection refreshes never
    overwrite it (see _apply_detection above).
    """
    with session_scope() as session:
        repo = ProjectRepository(session)
        project = repo.get_by_id(project_id)
        if project is None:
            return
        project.start_command = start_command
        project.stop_command = stop_command or None
        project.working_directory = working_directory
        project.command_source = "user"


def update_project_settings(
    project_id: int,
    *,
    start_command: str,
    stop_command: str,
    restart_command: str,
    working_directory: str,
    primary_port: int | None,
    env_vars: dict[str, str],
    ignore_patterns: list[str],
) -> None:
    """Persists the Project Detail page's Settings tab. Marked as a user
    edit (command_source="user") so a later discovery re-scan never
    silently overwrites what the user just typed in.
    """
    with session_scope() as session:
        repo = ProjectRepository(session)
        project = repo.get_by_id(project_id)
        if project is None:
            return
        project.start_command = start_command or None
        project.stop_command = stop_command or None
        project.restart_command = restart_command or None
        project.working_directory = working_directory or project.path
        project.primary_port = primary_port
        project.env_vars = env_vars
        project.ignore_patterns = ignore_patterns
        project.command_source = "user"


def ignore_discovered_project(discovered: DiscoveredProject) -> Project:
    with session_scope() as session:
        repo = ProjectRepository(session)
        project = build_new_project(discovered)
        project.is_ignored = True
        project.is_monitored = False
        project.status = ProjectStatus.DISCOVERED
        repo.add(project)
        session.refresh(project)
        session.expunge(project)
        return project
