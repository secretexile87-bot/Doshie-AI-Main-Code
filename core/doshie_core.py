#!/usr/bin/env python3
"""Doshie Core: lightweight health/status layer for the permanent AI host."""
import json
import subprocess
import urllib.request
from datetime import datetime, timezone

OLLAMA_URL = "http://127.0.0.1:11434/api/tags"

def command(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception as exc:
        return f"error: {exc}"

def ollama_status():
    try:
        with urllib.request.urlopen(OLLAMA_URL, timeout=3) as response:
            data = json.load(response)
        return {"online": True, "models": [m.get("name") for m in data.get("models", [])]}
    except Exception as exc:
        return {"online": False, "error": str(exc)}

def gpu_status():
    query = "name,temperature.gpu,memory.used,memory.total,utilization.gpu"
    out = command(["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"])
    return out

def service_status(name):
    out = command(["systemctl", "is-active", name])
    return out == "active"

def snapshot():
    return {
        "name": "Doshie Core",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ollama": ollama_status(),
        "gpu": gpu_status(),
        "services": {
            "doshie": service_status("doshie.service"),
            "ollama": service_status("ollama.service"),
        },
    }

def main():
    print(json.dumps(snapshot(), indent=2))

if __name__ == "__main__":
    main()
