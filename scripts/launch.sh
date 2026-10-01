#!/usr/bin/env bash
# Launches Project Monitor using its own virtual environment.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
    echo "Project Monitor's virtual environment is missing." >&2
    echo "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
    exit 1
fi

exec .venv/bin/python main.py
