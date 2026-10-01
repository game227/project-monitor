from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QWidget

from app.monitors.system_monitor import SystemMonitor
from app.ui.widgets.stat_tile import StatTile


class SystemPage(QWidget):
    def __init__(self, poll_interval_ms: int = 2000) -> None:
        super().__init__()
        self._monitor = SystemMonitor()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        grid = QGridLayout()
        grid.setSpacing(14)
        self._cpu_tile = StatTile("CPU")
        self._ram_tile = StatTile("RAM")
        self._disk_tile = StatTile("Disk")
        self._net_tile = StatTile("Network")
        grid.addWidget(self._cpu_tile, 0, 0)
        grid.addWidget(self._ram_tile, 0, 1)
        grid.addWidget(self._disk_tile, 1, 0)
        grid.addWidget(self._net_tile, 1, 1)
        layout.addLayout(grid)
        layout.addStretch(1)

        self._timer = QTimer(self)
        self._timer.setInterval(poll_interval_ms)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._tick()

    def _tick(self) -> None:
        snap = self._monitor.snapshot()
        self._cpu_tile.set_value(f"{snap.cpu_percent:.0f}%")
        self._ram_tile.set_value(f"{snap.ram_used_gb:.1f} / {snap.ram_total_gb:.1f} GB")
        self._disk_tile.set_value(f"{snap.disk_used_gb:.0f} / {snap.disk_total_gb:.0f} GB")
        self._net_tile.set_value(f"↓ {snap.network_down_mbps:.1f}  ↑ {snap.network_up_mbps:.1f} MB/s")
