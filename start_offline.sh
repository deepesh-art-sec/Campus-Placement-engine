#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "======================================================================"
echo "Starting Campus Placement Engine in 100% Offline Standalone Mode..."
echo "(No internet, Wi-Fi, Ethernet, or network connection required)"
echo "======================================================================"

export HOST=127.0.0.1
export PORT=8000
export AUTO_OPEN_BROWSER=1

if [ -f ".venv/bin/python" ]; then
    .venv/bin/python scripts/lan_launcher.py
else
    python3 scripts/lan_launcher.py
fi
