from __future__ import annotations

import socket

import psutil


def ports_for_pid(pid: int) -> list[int]:
    """Ports a process (or any of its children) is listening on."""
    ports: set[int] = set()
    try:
        proc = psutil.Process(pid)
        pids = [proc.pid] + [c.pid for c in proc.children(recursive=True)]
    except psutil.NoSuchProcess:
        return []

    for p in pids:
        try:
            connections = psutil.Process(p).net_connections(kind="inet")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        for conn in connections:
            if conn.status == psutil.CONN_LISTEN and conn.laddr:
                ports.add(conn.laddr.port)

    return sorted(ports)


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def find_pid_using_port(port: int) -> int | None:
    """Best-effort lookup of which PID is listening on a port, for the
    PORT CONFLICT UI. Requires no elevated privileges beyond what psutil
    already has for the current user's own processes.
    """
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError):
        return None
    for conn in connections:
        if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port == port:
            return conn.pid
    return None
