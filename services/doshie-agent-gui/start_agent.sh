#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="/home/doshie/Doshie/.venv/bin/python"

if [ ! -f "$PYTHON_EXEC" ]; then
  PYTHON_EXEC="python3"
fi

echo "========================================================"
echo "⚡ Starting Doshie Autonomous Agent Console"
echo "========================================================"

# Check if Ollama is responding
if curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
  echo "✓ Ollama is online and ready."
else
  echo "⚠️ Warning: Ollama is not responding at http://127.0.0.1:11434"
  echo "  Run 'ollama serve' in another terminal if local models are needed."
fi

export AGENT_PORT=5070
echo "✓ Serving Agent GUI at: http://localhost:${AGENT_PORT}"
echo "✓ Press Ctrl+C to stop."
echo "========================================================"

exec "$PYTHON_EXEC" "$DIR/server.py"
