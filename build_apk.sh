#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "==========================================="
echo "  🚀 DOSHIE ANDROID APK BUILD SYSTEM"
echo "==========================================="

echo "[1/4] Syncing frontend web assets to Android project..."
if [ -f "node_modules/.bin/cap" ]; then
    ./node_modules/.bin/cap sync android || true
fi

echo "[2/4] Assembling APK with Gradle..."
cd "$DIR/android"
./gradlew assembleDebug

APK_SRC="$DIR/android/app/build/outputs/apk/debug/app-debug.apk"

if [ ! -f "$APK_SRC" ]; then
    echo "❌ Error: APK build failed to produce $APK_SRC"
    exit 1
fi

echo "[3/4] Copying fresh APK to downloads & desktop..."
mkdir -p "$DIR/static/downloads"
cp -f "$APK_SRC" "$DIR/static/downloads/Doshie-latest.apk"
cp -f "$APK_SRC" "/home/doshie/Desktop/Doshie-latest.apk"

TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
SIZE=$(du -h "$APK_SRC" | cut -f1)

echo "[4/4] Updating latest download metadata..."
cat <<EOF > "$DIR/static/downloads/latest.json"
{
  "version": "0.9.2-dev",
  "updated": "$TIMESTAMP",
  "android": {
    "file": "Doshie-latest.apk",
    "name": "Doshie Assistant for Android",
    "version": "0.9.2-dev",
    "size": "$SIZE"
  }
}
EOF

echo "==========================================="
echo "✅ SUCCESS! Android APK built and published."
echo "📱 Local Download URL: http://localhost:5000/download"
echo "🌐 Network Download URL: http://100.109.79.35:5000/download"
echo "📁 Desktop File: /home/doshie/Desktop/Doshie-latest.apk ($SIZE)"
echo "==========================================="
