#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Launch MySpace studio electron window
exec ./node_modules/.bin/electron --no-sandbox myspace-studio/main.js "$@"
