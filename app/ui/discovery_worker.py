"""Background project discovery: an initial scan on startup, then
event-based re-scans whenever watchdog notices a new directory appear
under one of the configured project roots (spec section 16 -- creating
`~/Projects/new-project` must be picked up automatically, no polling).

A short debounce absorbs the burst of filesystem events a `git clone` or
`mkdir && cd && git init` produces, so one new project triggers one scan.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMetaObject, QObject, Qt, QThread, QTimer, Signal, Slot

from app.core.settings import Settings
from app.filesystem.file_watcher import DirectoryWatcher, FileChangeEvent
from app.services.sync_service import sync_discovered_projects

_DEBOUNCE_MS = 1500
_FALLBACK_SCAN_MS = 30_000


class DiscoveryWorker(QObject):
    # Signal(object), not Signal(list): a queued cross-thread emission
    # needs a registered Qt metatype for its argument, and arbitrary
    # Python objects (DiscoveredProject isn't a QVariant-convertible
    # type) only marshal reliably through the generic "object" type.
    pending_projects = Signal(object)  # list[DiscoveredProject]
    scan_completed = Signal()

    _fs_event = Signal()  # internal: marshals watchdog thread -> worker thread

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings
        self._watchers: list[DirectoryWatcher] = []
        self._debounce_timer: QTimer | None = None
        self._fallback_timer: QTimer | None = None
        self._fs_event.connect(self._on_fs_event)

    @Slot()
    def _on_thread_started(self) -> None:
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self.run_scan)

        if self._settings.scan_on_startup:
            self.run_scan()

        if self._settings.monitor_new_projects_automatically:
            self._setup_root_watchers()

        fallback = QTimer(self)
        fallback.setInterval(_FALLBACK_SCAN_MS)
        fallback.timeout.connect(self.run_scan)
        fallback.start()
        self._fallback_timer = fallback

    def _setup_root_watchers(self) -> None:
        for root in self._settings.project_roots:
            path = Path(root).expanduser()
            if not path.is_dir():
                continue
            watcher = DirectoryWatcher(
                str(path),
                callback=self._on_root_changed,
                ignore_names=self._settings.ignore_patterns,
                recursive=False,
            )
            watcher.start()
            self._watchers.append(watcher)

    def _on_root_changed(self, event: FileChangeEvent) -> None:
        # Called on watchdog's own thread: only emit a signal here, Qt
        # marshals it safely onto this worker's thread.
        self._fs_event.emit()

    @Slot()
    def _on_fs_event(self) -> None:
        if self._debounce_timer is not None:
            self._debounce_timer.start(_DEBOUNCE_MS)

    @Slot()
    def run_scan(self) -> None:
        try:
            pending = sync_discovered_projects(self._settings)
        except Exception:
            return
        self.scan_completed.emit()
        if pending:
            self.pending_projects.emit(pending)

    def stop_watchers(self) -> None:
        for watcher in self._watchers:
            watcher.stop()
        self._watchers.clear()

    @Slot()
    def _stop_timers(self) -> None:
        # Must run on this worker's own thread, same reason as
        # MonitoringWorker._stop_timer.
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
        if self._fallback_timer is not None:
            self._fallback_timer.stop()


class DiscoveryController:
    """See MonitoringController's docstring: construction does not start
    the thread, so the caller can wire signals before start() -- the
    initial scan's pending_projects/scan_completed signals would
    otherwise fire before anything is connected to receive them.
    """

    def __init__(self, settings: Settings) -> None:
        self.thread = QThread()
        self.worker = DiscoveryWorker(settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker._on_thread_started)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.worker.stop_watchers()
        QMetaObject.invokeMethod(self.worker, "_stop_timers", Qt.ConnectionType.BlockingQueuedConnection)
        self.thread.quit()
        self.thread.wait(2000)
