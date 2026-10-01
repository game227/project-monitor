"""Runs MonitoringCoordinator on a background QThread so polling CPU/RAM,
git status, and process I/O never blocks the UI event loop. The UI talks
to this only through Qt signals/slots -- never by calling coordinator
methods directly from the main thread (see spec section 22).
"""
from __future__ import annotations

from PySide6.QtCore import QMetaObject, QObject, Qt, QThread, QTimer, Signal, Slot

from app.core.settings import Settings
from app.services.monitoring_service import MonitoringCoordinator


class MonitoringWorker(QObject):
    updated = Signal()

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings
        self._coordinator = MonitoringCoordinator(settings)
        self._timer: QTimer | None = None

    @Slot()
    def _on_thread_started(self) -> None:
        self._timer = QTimer(self)
        self._timer.setInterval(int(self._settings.cpu_ram_poll_interval_seconds * 1000))
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    @Slot()
    def _tick(self) -> None:
        self._coordinator.tick()
        self.updated.emit()

    @Slot(int)
    def start_project(self, project_id: int) -> None:
        self._coordinator.start_project(project_id)
        self.updated.emit()

    @Slot(int)
    def stop_project(self, project_id: int) -> None:
        self._coordinator.stop_project(project_id)
        self.updated.emit()

    @Slot(int)
    def restart_project(self, project_id: int) -> None:
        self._coordinator.restart_project(project_id)
        self.updated.emit()

    def get_runtime(self, project_id: int):
        return self._coordinator.get_runtime(project_id)

    @Slot()
    def _stop_timer(self) -> None:
        # Must run on this worker's own thread: a QTimer can only be
        # stopped by the thread that owns it, or Qt logs
        # "Timers cannot be stopped from another thread" on teardown.
        if self._timer is not None:
            self._timer.stop()


class MonitoringController:
    """Owns the worker's QThread and gives the UI a thread-safe handle.

    Construction does not start the thread: the caller must wire up
    signal connections first, then call start(). Starting immediately in
    __init__ is a race -- the worker can finish its first tick and emit
    `updated` before the UI has connected to it, and that first emission
    would simply be lost.
    """

    def __init__(self, settings: Settings) -> None:
        self.thread = QThread()
        self.worker = MonitoringWorker(settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker._on_thread_started)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        QMetaObject.invokeMethod(self.worker, "_stop_timer", Qt.ConnectionType.BlockingQueuedConnection)
        self.thread.quit()
        self.thread.wait(2000)
