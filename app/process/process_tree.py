"""Lists a running project's process tree (main process + children) for
the Project Detail page's Processes tab.
"""
from __future__ import annotations

from dataclasses import dataclass

import psutil


@dataclass
class ProcessInfo:
    pid: int
    cpu_percent: float
    ram_mb: float
    command: str


def list_process_tree(root_pid: int) -> list[ProcessInfo]:
    try:
        root = psutil.Process(root_pid)
    except psutil.NoSuchProcess:
        return []

    procs = [root] + root.children(recursive=True)
    infos: list[ProcessInfo] = []
    for proc in procs:
        try:
            cpu = proc.cpu_percent(interval=None)
            ram_mb = proc.memory_info().rss / (1024 * 1024)
            command = " ".join(proc.cmdline()) or proc.name()
            infos.append(ProcessInfo(pid=proc.pid, cpu_percent=cpu, ram_mb=ram_mb, command=command))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return infos
