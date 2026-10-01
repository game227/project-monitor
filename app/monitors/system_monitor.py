"""Whole-machine CPU/RAM/disk/network stats for the System page."""
from __future__ import annotations

import time
from dataclasses import dataclass

import psutil


@dataclass
class SystemSnapshot:
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float
    disk_used_gb: float
    disk_total_gb: float
    network_down_mbps: float
    network_up_mbps: float


class SystemMonitor:
    def __init__(self, disk_path: str = "/") -> None:
        self._disk_path = disk_path
        self._last_net = psutil.net_io_counters()
        self._last_time = time.monotonic()
        psutil.cpu_percent(interval=None)  # prime the non-blocking counter

    def snapshot(self) -> SystemSnapshot:
        cpu = psutil.cpu_percent(interval=None)

        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(self._disk_path)

        now = time.monotonic()
        net = psutil.net_io_counters()
        elapsed = max(now - self._last_time, 1e-6)
        down_mbps = (net.bytes_recv - self._last_net.bytes_recv) / elapsed / (1024 * 1024)
        up_mbps = (net.bytes_sent - self._last_net.bytes_sent) / elapsed / (1024 * 1024)
        self._last_net = net
        self._last_time = now

        gb = 1024**3
        return SystemSnapshot(
            cpu_percent=cpu,
            ram_used_gb=mem.used / gb,
            ram_total_gb=mem.total / gb,
            disk_used_gb=disk.used / gb,
            disk_total_gb=disk.total / gb,
            network_down_mbps=max(down_mbps, 0.0),
            network_up_mbps=max(up_mbps, 0.0),
        )
