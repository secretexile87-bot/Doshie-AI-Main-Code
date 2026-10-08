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

# Connect Tailscale when Doshie starts
echo "[Doshie Desktop] Connecting Tailscale..."
tailscale up 2>/dev/null || true

cleanup() {
    echo "[Doshie Desktop] Disconnecting Tailscale..."
    tailscale down 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Ensure audio input (microphone) source is active in PipeWire
if ! wpctl status 2>/dev/null | sed -n '/Audio/,/Video/p' | grep -A 5 "Sources:" | grep -q "\[vol:"; then
    echo "[Doshie Desktop] Initializing PipeWire audio input source..."
    DEV_LINE=$(wpctl status 2>/dev/null | sed -n "/Audio/,/Video/p" | grep -A 10 "Devices:" | grep -E "800 Series ACE|HDA Intel" | head -n 1 || true)
    DEV_ID=$(echo "$DEV_LINE" | grep -oE "[0-9]+\." | head -n 1 | tr -d "." || true)
    if [ -n "$DEV_ID" ]; then
        wpctl set-profile "$DEV_ID" 4 2>/dev/null || true
    fi
    SRC_LINE=$(wpctl status 2>/dev/null | sed -n "/Audio/,/Video/p" | grep -A 10 "Sources:" | grep -E "800 Series ACE|HDA Intel" | head -n 1 || true)
    SRC_ID=$(echo "$SRC_LINE" | grep -oE "[0-9]+\." | head -n 1 | tr -d "." || true)
    if [ -n "$SRC_ID" ]; then
        wpctl set-default "$SRC_ID" 2>/dev/null || true
    fi
fi

# Detect XAUTHORITY if in Wayland session
if [ -z "$XAUTHORITY" ]; then
    AUTH_FILE=$(ls -t /run/user/$(id -u)/.mutter-Xwaylandauth.* 2>/dev/null | head -n 1 || true)
    if [ -n "$AUTH_FILE" ]; then
        export XAUTHORITY="$AUTH_FILE"
    fi
fi

# Run Electron app with Wayland ozone platform support and sandbox flag
./node_modules/.bin/electron --no-sandbox --ozone-platform-hint=auto --enable-features=WaylandWindowDecorations . "$@"
