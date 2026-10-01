from pathlib import Path

import app.database.session as session_module
from app.core.settings import Settings
from app.database.session import init_db, session_scope
from app.models.enums import ProjectStatus
from app.services.discovery_service import ProjectDiscoveryService, inspect_path
from app.services.project_repository import ProjectRepository
from app.services.sync_service import (
    ProjectAlreadyExistsError,
    add_discovered_project,
    add_manual_project,
    ignore_discovered_project,
    sync_discovered_projects,
)


def _fresh_db(tmp_path: Path) -> None:
    # Each test gets its own SQLite file: reset the module-level
    # engine/session-factory singletons so init_db() rebuilds them here
    # instead of reusing whatever an earlier test connected to.
    session_module._engine = None
    session_module._SessionFactory = None
    init_db(str(tmp_path / "test.db"))


def test_sync_prompts_for_new_projects_by_default(tmp_path: Path) -> None:
    _fresh_db(tmp_path)
    root = tmp_path / "roots"
    root.mkdir()
    (root / "my-django-app").mkdir()
    (root / "my-django-app" / "manage.py").write_text(
        "from django.core.management import execute_from_command_line\n"
    )

    settings = Settings(project_roots=[str(root)], auto_add_future_projects=False)
    pending = sync_discovered_projects(settings)

    assert len(pending) == 1
    assert pending[0].name == "my-django-app"

    with session_scope() as session:
        assert ProjectRepository(session).list_all() == []


def test_sync_auto_adds_when_enabled(tmp_path: Path) -> None:
    _fresh_db(tmp_path)
    root = tmp_path / "roots"
    root.mkdir()
    (root / "some-app").mkdir()

    settings = Settings(project_roots=[str(root)], auto_add_future_projects=True)
    pending = sync_discovered_projects(settings)

    assert pending == []
    with session_scope() as session:
        projects = ProjectRepository(session).list_all()
        assert [p.name for p in projects] == ["some-app"]


def test_add_and_ignore_discovered_project(tmp_path: Path) -> None:
    _fresh_db(tmp_path)
    root = tmp_path / "roots"
    root.mkdir()
    (root / "app-a").mkdir()
    (root / "app-b").mkdir()

    settings = Settings(project_roots=[str(root)])
    discovered = ProjectDiscoveryService(settings).scan()
    by_name = {d.name: d for d in discovered}

    add_discovered_project(by_name["app-a"])
    ignore_discovered_project(by_name["app-b"])

    with session_scope() as session:
        projects = {p.name: p for p in ProjectRepository(session).list_all()}
        assert projects["app-a"].is_ignored is False
        assert projects["app-a"].status == ProjectStatus.DISCOVERED
        assert projects["app-b"].is_ignored is True
        assert projects["app-b"].is_monitored is False


def test_second_scan_refreshes_existing_project_without_duplicating(tmp_path: Path) -> None:
    _fresh_db(tmp_path)
    root = tmp_path / "roots"
    root.mkdir()
    project_dir = root / "app"
    project_dir.mkdir()

    settings = Settings(project_roots=[str(root)], auto_add_future_projects=True)
    sync_discovered_projects(settings)

    (project_dir / "package.json").write_text('{"dependencies": {}}')
    sync_discovered_projects(settings)

    with session_scope() as session:
        projects = ProjectRepository(session).list_all()
        assert len(projects) == 1
        assert projects[0].project_type.value == "node"


def test_auto_detected_command_self_heals_when_detection_improves(tmp_path: Path) -> None:
    """A project scanned before it had a venv (or before a detector fix)
    should pick up the corrected command on a later scan, as long as the
    user never edited the command themselves (command_source stays
    "auto-detected"). This is what fixes an already-added Django project
    that crashed with "Couldn't import Django" because the first scan
    suggested bare "python" instead of the project's own .venv python.
    """
    _fresh_db(tmp_path)
    root = tmp_path / "roots"
    root.mkdir()
    project_dir = root / "app"
    project_dir.mkdir()
    (project_dir / "manage.py").write_text(
        "from django.core.management import execute_from_command_line\n"
    )

    settings = Settings(project_roots=[str(root)], auto_add_future_projects=True)
    sync_discovered_projects(settings)

    with session_scope() as session:
        before = ProjectRepository(session).list_all()[0]
        assert before.start_command == "python manage.py runserver 127.0.0.1:8000"

    venv_python = project_dir / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("")

    sync_discovered_projects(settings)

    with session_scope() as session:
        after = ProjectRepository(session).list_all()[0]
        assert after.start_command == f"{venv_python} manage.py runserver 127.0.0.1:8000"


def test_user_edited_command_is_never_overwritten_by_rescan(tmp_path: Path) -> None:
    _fresh_db(tmp_path)
    root = tmp_path / "roots"
    root.mkdir()
    project_dir = root / "app"
    project_dir.mkdir()
    (project_dir / "manage.py").write_text(
        "from django.core.management import execute_from_command_line\n"
    )

    settings = Settings(project_roots=[str(root)], auto_add_future_projects=True)
    sync_discovered_projects(settings)

    with session_scope() as session:
        project = ProjectRepository(session).list_all()[0]
        project.start_command = "python manage.py runserver 0.0.0.0:9999"
        project.command_source = "user"

    venv_python = project_dir / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("")
    sync_discovered_projects(settings)

    with session_scope() as session:
        after = ProjectRepository(session).list_all()[0]
        assert after.start_command == "python manage.py runserver 0.0.0.0:9999"


def test_add_manual_project_applies_user_overrides(tmp_path: Path) -> None:
    _fresh_db(tmp_path)
    project_dir = tmp_path / "my-app"
    project_dir.mkdir()

    discovered = inspect_path(str(project_dir))
    added = add_manual_project(
        discovered, name="Custom Name", start_command="python run.py", primary_port=9000
    )

    assert added.name == "Custom Name"
    assert added.start_command == "python run.py"
    assert added.command_source == "user"
    assert added.primary_port == 9000

    with session_scope() as session:
        projects = ProjectRepository(session).list_all()
        assert len(projects) == 1


def test_add_manual_project_rejects_duplicate_path(tmp_path: Path) -> None:
    _fresh_db(tmp_path)
    project_dir = tmp_path / "my-app"
    project_dir.mkdir()

    discovered = inspect_path(str(project_dir))
    add_manual_project(discovered, name="", start_command="", primary_port=None)

    try:
        add_manual_project(discovered, name="", start_command="", primary_port=None)
    except ProjectAlreadyExistsError:
        pass
    else:
        raise AssertionError("expected ProjectAlreadyExistsError")
