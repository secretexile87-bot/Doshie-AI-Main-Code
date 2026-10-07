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
./gradlew bundleRelease

APK_SRC="$DIR/android/app/build/outputs/apk/debug/app-debug.apk"
AAB_SRC="$DIR/android/app/build/outputs/bundle/release/app-release.aab"

if [ ! -f "$APK_SRC" ]; then
    echo "❌ Error: APK build failed to produce $APK_SRC"
    exit 1
fi

echo "[3/4] Copying fresh APK and AAB to downloads & desktop..."
mkdir -p "$DIR/static/downloads"
cp -f "$APK_SRC" "$DIR/static/downloads/Doshie-latest.apk"
cp -f "$APK_SRC" "/home/doshie/Desktop/Doshie-latest.apk"

if [ -f "$AAB_SRC" ]; then
    cp -f "$AAB_SRC" "$DIR/static/downloads/Doshie-latest.aab"
    cp -f "$AAB_SRC" "/home/doshie/Desktop/Doshie-latest.aab"
fi

TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
SIZE=$(du -h "$APK_SRC" | cut -f1)

echo "[4/4] Updating latest download metadata..."
cat <<EOF2 > "$DIR/static/downloads/latest.json"
{
  "version": "0.9.9",
  "updated": "$TIMESTAMP",
  "android": {
    "file": "Doshie-latest.apk",
    "name": "Doshie Assistant for Android",
    "version": "0.9.9",
    "size": "$SIZE",
    "url": "/static/downloads/Doshie-latest.apk"
  }
}
EOF2

echo "==========================================="
echo "✅ SUCCESS! Android APK/AAB built and published."
echo "==========================================="
