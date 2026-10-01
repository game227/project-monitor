"""Thin data-access layer around the `projects` table. UI and services
go through this instead of touching SQLAlchemy sessions directly.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_path(self, path: str) -> Project | None:
        stmt = select(Project).where(Project.path == path)
        return self._session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, project_id: int) -> Project | None:
        return self._session.get(Project, project_id)

    def list_all(self) -> list[Project]:
        stmt = select(Project).order_by(Project.name)
        return list(self._session.execute(stmt).scalars().all())

    def add(self, project: Project) -> Project:
        self._session.add(project)
        self._session.flush()
        return project

    def delete(self, project: Project) -> None:
        self._session.delete(project)
