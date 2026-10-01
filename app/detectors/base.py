from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.detectors.result import DetectionResult


class BaseDetector(ABC):
    """One detector recognizes one project type/framework.

    Adding a new detector means: subclass this, implement detect(), and
    register the instance in app.detectors.registry.ALL_DETECTORS. Nothing
    else in the codebase needs to change.
    """

    name: str = "base"

    @abstractmethod
    def detect(self, project_path: Path) -> DetectionResult | None:
        """Return a DetectionResult if this detector's markers are present,
        otherwise None. Must not raise for a merely-absent marker; only
        genuine bugs should propagate.
        """
        raise NotImplementedError

    @staticmethod
    def _read_text(path: Path, max_bytes: int = 2_000_000) -> str | None:
        try:
            if not path.is_file() or path.stat().st_size > max_bytes:
                return None
            return path.read_text(errors="ignore")
        except OSError:
            return None
