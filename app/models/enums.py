from __future__ import annotations

import enum


class ProjectStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    CRASHED = "CRASHED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class ProjectType(str, enum.Enum):
    DJANGO = "django"
    FLASK = "flask"
    FASTAPI = "fastapi"
    PYTHON = "python"
    REACT = "react"
    VUE = "vue"
    NODE = "node"
    DOCKER = "docker"
    GIT_GENERIC = "git"
    GENERIC = "generic"
