#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Ensure local Doshie core backend is running via systemd
if ! curl -s --connect-timeout 1 http://127.0.0.1:5000 >/dev/null 2>&1; then
    echo "[Doshie Desktop] Starting Doshie local backend..."
    systemctl --user start doshie-web.service || nohup /home/doshie/Doshie/.venv/bin/python /home/doshie/Doshie/Doshie_web.py >/dev/null 2>&1 &
fi

# Ensure Doshie Universal Music Player is running
if ! curl -s --connect-timeout 1 http://127.0.0.1:5055/api/services >/dev/null 2>&1; then
    echo "[Doshie Desktop] Starting Doshie Music Player backend..."
    systemctl --user start doshie-music-player.service || nohup /home/doshie/.gemini/antigravity-cli/scratch/music-player/music-cli server >/dev/null 2>&1 &
fi

# Run Electron app with sandbox flag compatible with Ubuntu user namespaces
exec ./node_modules/.bin/electron --no-sandbox . "$@"
