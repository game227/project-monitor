"""Captures a running project's stdout/stderr into an in-memory ring
buffer and forwards each line to a callback for real-time UI updates.

Reading happens on background threads so it never blocks the Qt event
loop; the callback is expected to be cheap (e.g. emit a Qt signal) since
it runs on the reader thread, not the UI thread.
"""
from __future__ import annotations

import subprocess
import threading
from collections import deque
from dataclasses import dataclass
from typing import Callable

LogCallback = Callable[[str, str], None]  # (line, stream) where stream is "stdout"/"stderr"

_MAX_LINES = 2000


@dataclass
class LogLine:
    stream: str
    text: str


class LogManager:
    def __init__(self, max_lines: int = _MAX_LINES) -> None:
        self._lines: deque[LogLine] = deque(maxlen=max_lines)
        self._lock = threading.Lock()
        self._threads: list[threading.Thread] = []
        self.last_error: str | None = None

    def attach(self, popen: subprocess.Popen, on_line: LogCallback | None = None) -> None:
        if popen.stdout is not None:
            self._threads.append(self._start_reader(popen.stdout, "stdout", on_line))
        if popen.stderr is not None:
            self._threads.append(self._start_reader(popen.stderr, "stderr", on_line))

    def _start_reader(self, stream, label: str, on_line: LogCallback | None) -> threading.Thread:
        def _reader() -> None:
            try:
                for raw_line in iter(stream.readline, ""):
                    if raw_line == "":
                        break
                    line = raw_line.rstrip("\n")
                    with self._lock:
                        self._lines.append(LogLine(stream=label, text=line))
                        if label == "stderr":
                            self.last_error = line
                    if on_line is not None:
                        on_line(line, label)
            except (ValueError, OSError):
                pass  # stream closed underneath us; nothing left to read

        thread = threading.Thread(target=_reader, daemon=True)
        thread.start()
        return thread

    def snapshot(self) -> list[LogLine]:
        with self._lock:
            return list(self._lines)

    def clear(self) -> None:
        with self._lock:
            self._lines.clear()
