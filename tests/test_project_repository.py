from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.services.project_repository import ProjectRepository


def _session():
    from app.models import project  # noqa: F401 - register table on Base.metadata

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_add_and_get_by_path() -> None:
    session = _session()
    repo = ProjectRepository(session)

    project = Project(name="Demo", path="/tmp/demo")
    repo.add(project)
    session.commit()

    found = repo.get_by_path("/tmp/demo")
    assert found is not None
    assert found.name == "Demo"
    assert found.status == ProjectStatus.DISCOVERED  # default


def test_get_by_path_missing_returns_none() -> None:
    session = _session()
    repo = ProjectRepository(session)
    assert repo.get_by_path("/does/not/exist") is None


def test_list_all_orders_by_name() -> None:
    session = _session()
    repo = ProjectRepository(session)
    repo.add(Project(name="Zeta", path="/tmp/z"))
    repo.add(Project(name="Alpha", path="/tmp/a"))
    session.commit()

    names = [p.name for p in repo.list_all()]
    assert names == ["Alpha", "Zeta"]


def test_path_must_be_unique() -> None:
    from sqlalchemy.exc import IntegrityError

    session = _session()
    repo = ProjectRepository(session)
    repo.add(Project(name="One", path="/tmp/dup"))
    session.commit()

    try:
        repo.add(Project(name="Two", path="/tmp/dup"))
    except IntegrityError:
        pass
    else:
        raise AssertionError("expected IntegrityError for duplicate path")
