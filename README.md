# Project Monitor

A standalone desktop dashboard for monitoring, starting, stopping, and
restarting your local development projects on Linux. It lives in its own
folder, separate from every project it watches, and never modifies a
watched project's source code.

## Running

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Project Monitor's own state (SQLite database, settings.json, logs) lives
under `~/.config/project-monitor/` — never inside a monitored project.

## How discovery works

On startup, and whenever a new folder appears under a configured project
root, Project Monitor scans that folder for markers (`manage.py`,
`package.json`, `Dockerfile`, `.git`, ...) and classifies it automatically
— no code changes required when you start a new project. Configure roots
under Settings -> Project roots (defaults to `~/Projects` if it exists,
otherwise falls back to `~/Desktop`).

Adding a new project type/framework detector is a matter of subclassing
`app/detectors/base.py::BaseDetector` and registering it in
`app/detectors/registry.py` — nothing else needs to change.

## Per-project configuration

Drop an optional `.project-monitor.json` in a project's root to override
auto-detection:

```json
{
  "name": "DTM Platform",
  "type": "django",
  "start_command": "python manage.py runserver 127.0.0.1:8000",
  "port": 8000
}
```

## Testing

```bash
source .venv/bin/activate
pip install pytest
pytest
```

## Building a standalone executable

```bash
./scripts/build.sh
```

Produces `dist/ProjectMonitor/ProjectMonitor`.

## Architecture

```
app/
  core/          paths, persistent Settings
  database/      SQLAlchemy engine/session
  models/        Project ORM model, status/type enums
  detectors/     one class per project type (Django, React, Docker, ...)
  services/      discovery, detection sync, config loading, monitoring coordination
  process/       process lifecycle, log capture, port scanning
  git/           read-only git status via subprocess
  filesystem/    watchdog-based directory watching
  monitors/      per-project runtime state, system-wide CPU/RAM/disk/net
  notifications/ desktop notifications (notify-send)
  ui/            PySide6 windows, pages, widgets, background QThread workers
```

Commands are never run through a shell (`shlex.split` + fixed argv), git
is invoked read-only, and one project's monitoring error never affects
another's.
