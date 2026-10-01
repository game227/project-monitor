from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import ProjectType


@dataclass
class DetectionResult:
    """What a single detector found about a project directory."""

    project_type: ProjectType
    framework: str | None = None
    language: str | None = None
    # Higher confidence wins when several detectors match the same project.
    confidence: int = 0
    suggested_start_command: str | None = None
    suggested_port: int | None = None
