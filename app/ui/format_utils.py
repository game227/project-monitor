"""Small display-formatting helpers shared across UI widgets."""
from __future__ import annotations

import datetime as dt


def format_uptime(seconds: float | None) -> str:
    if not seconds or seconds < 0:
        return "--:--:--"
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def uptime_seconds_since(started_at: dt.datetime | None) -> float | None:
    if started_at is None:
        return None
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=dt.timezone.utc)
    return (dt.datetime.now(dt.timezone.utc) - started_at).total_seconds()
