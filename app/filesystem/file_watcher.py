"""Event-based filesystem watching (watchdog), used for two things:

1. Watching each configured project root (non-recursive-ish, one level)
   to notice brand-new project directories as soon as they're created.
2. Watching inside a single monitored project for file changes to show
   in its "Files" tab.

Both share the same ignore-pattern logic so noisy directories (.git,
node_modules, __pycache__, .venv, ...) never generate events.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

FileChangeCallback = Callable[["FileChangeEvent"], None]


@dataclass
class FileChangeEvent:
    kind: str  # "created" | "modified" | "deleted" | "moved"
    path: str


def _ignore_glob_patterns(ignore_names: list[str]) -> list[str]:
    patterns: list[str] = []
    for name in ignore_names:
        patterns.append(f"*/{name}")
        patterns.append(f"*/{name}/*")
    return patterns


class _Handler(PatternMatchingEventHandler):
    def __init__(self, callback: FileChangeCallback, ignore_names: list[str]) -> None:
        super().__init__(
            ignore_patterns=_ignore_glob_patterns(ignore_names),
            ignore_directories=False,
        )
        self._callback = callback

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._callback(FileChangeEvent(kind="created", path=event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._callback(FileChangeEvent(kind="modified", path=event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._callback(FileChangeEvent(kind="deleted", path=event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._callback(FileChangeEvent(kind="moved", path=event.dest_path))


class DirectoryWatcher:
    """Watches one directory tree and forwards filtered change events."""

    def __init__(self, path: str, callback: FileChangeCallback, ignore_names: list[str], recursive: bool = True) -> None:
        self._observer = Observer()
        handler = _Handler(callback, ignore_names)
        self._observer.schedule(handler, path, recursive=recursive)

    def start(self) -> None:
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join(timeout=2)
