#!/usr/bin/env bash
# Builds a standalone Linux executable with PyInstaller.
# Run from the project root: ./scripts/build.sh
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
    echo "No .venv found. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
    exit 1
fi

source .venv/bin/activate

if ! python -c "import PyInstaller" 2>/dev/null; then
    pip install pyinstaller
fi

rm -rf build dist

pyinstaller \
    --name "ProjectMonitor" \
    --windowed \
    --onedir \
    --noconfirm \
    main.py

echo "Build complete: dist/ProjectMonitor/ProjectMonitor"
