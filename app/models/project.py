from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import ProjectStatus, ProjectType


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True, index=True)

    # Detection
    project_type: Mapped[str] = mapped_column(
        Enum(ProjectType, native_enum=False, length=32), default=ProjectType.GENERIC
    )
    framework: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Git
    is_git_repo: Mapped[bool] = mapped_column(default=False)
    git_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    git_ahead: Mapped[int] = mapped_column(Integer, default=0)
    git_behind: Mapped[int] = mapped_column(Integer, default=0)
    git_modified_count: Mapped[int] = mapped_column(Integer, default=0)
    git_untracked_count: Mapped[int] = mapped_column(Integer, default=0)
    git_last_commit: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Networking
    detected_ports: Mapped[list] = mapped_column(JSON, default=list)
    primary_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    host: Mapped[str] = mapped_column(String(128), default="127.0.0.1")

    # Process / runtime state
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(ProjectStatus, native_enum=False, length=32), default=ProjectStatus.DISCOVERED
    )
    cpu_percent: Mapped[float] = mapped_column(default=0.0)
    ram_mb: Mapped[float] = mapped_column(default=0.0)

    # Commands
    start_command: Mapped[str | None] = mapped_column(Text, nullable=True)
    stop_command: Mapped[str | None] = mapped_column(Text, nullable=True)
    restart_command: Mapped[str | None] = mapped_column(Text, nullable=True)
    working_directory: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    env_vars: Mapped[dict] = mapped_column(JSON, default=dict)

    # Config provenance: "auto-detected" | "user" | "project-file"
    command_source: Mapped[str] = mapped_column(String(32), default="auto-detected")

    # Ignore patterns override (falls back to global settings if empty)
    ignore_patterns: Mapped[list] = mapped_column(JSON, default=list)

    # Lifecycle timestamps
    last_started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_stopped_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # User controls
    is_monitored: Mapped[bool] = mapped_column(default=True)
    is_ignored: Mapped[bool] = mapped_column(default=False)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Project id={self.id} name={self.name!r} status={self.status}>"
