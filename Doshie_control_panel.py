"""
Doshie Robust Control Panel Backend Module
Provides:
- Real-time Hardware & Telemetry (RTX 5070 GPU, CPU, RAM, Disk, Uptime)
- AI Engine & Ollama Models inspection, model switching & low-latency ping
- Voice Engine (Hermes / chatterbox-nano) health & ping
- Service management (restart Doshie, restart voice, restart Ollama, flush cache)
- Real-time log streamer / tailer (Doshie, Voice, Ollama, Supervisor)
"""

import os
import gc
import time
import json
import signal
import platform
import threading
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, jsonify, request

try:
    import psutil
except ImportError:
    psutil = None

# Initialize CPU usage counter on load so next reading is valid
if psutil:
    try:
        psutil.cpu_percent(interval=None)
    except Exception:
        pass

control_panel_bp = Blueprint("control_panel", __name__)


def _run_cmd(args, timeout=4):
    """Run shell command safely and return trimmed stdout."""
    try:
        res = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return res.stdout.strip()
    except Exception as exc:
        return ""


def get_gpu_telemetry():
    """Query NVIDIA RTX 5070 GPU status via nvidia-smi."""
    fields = "name,temperature.gpu,memory.used,memory.total,utilization.gpu,power.draw,fan.speed"
    raw = _run_cmd(["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"], timeout=3)
    if not raw:
        return {
            "available": False,
            "name": "NVIDIA GPU Unavailable",
            "temperature_c": None,
            "memory_used_mb": 0,
            "memory_total_mb": 0,
            "memory_percent": 0.0,
            "utilization_percent": 0,
            "power_w": 0.0,
            "fan_percent": 0,
            "temp_state": "normal"
        }
    try:
        parts = [p.strip() for p in raw.split(",")]
        name = parts[0]
        temp = int(float(parts[1]))
        mem_used = int(float(parts[2]))
        mem_total = int(float(parts[3]))
        util = int(float(parts[4]))
        power = round(float(parts[5]), 1) if len(parts) > 5 and parts[5] != "[N/A]" else 0.0
        fan = int(float(parts[6])) if len(parts) > 6 and parts[6] != "[N/A]" else 0

        mem_pct = round((mem_used / mem_total * 100), 1) if mem_total > 0 else 0.0
        temp_state = "hot" if temp >= 78 else ("warm" if temp >= 58 else "cool")

        return {
            "available": True,
            "name": name,
            "temperature_c": temp,
            "memory_used_mb": mem_used,
            "memory_total_mb": mem_total,
            "memory_percent": mem_pct,
            "utilization_percent": util,
            "power_w": power,
            "fan_percent": fan,
            "temp_state": temp_state
        }
    except Exception as err:
        return {
            "available": False,
            "error": str(err),
            "name": "NVIDIA GPU (parse error)",
            "memory_percent": 0.0,
            "temperature_c": None
        }


def get_cpu_telemetry():
    """Query CPU utilization, load averages, and core count."""
    if not psutil:
        return {"percent": 0, "logical_cores": 1, "load_avg": []}
    try:
        cpu_pct = round(psutil.cpu_percent(interval=None), 1)
        logical = psutil.cpu_count(logical=True) or 1
        physical = psutil.cpu_count(logical=False) or 1
        load_avg = [round(x, 2) for x in os.getloadavg()] if hasattr(os, "getloadavg") else []
        return {
            "percent": cpu_pct,
            "logical_cores": logical,
            "physical_cores": physical,
            "load_avg": load_avg
        }
    except Exception as err:
        return {"percent": 0, "error": str(err)}


def get_memory_telemetry():
    """Query host RAM usage."""
    if not psutil:
        return {"percent": 0, "used_gb": 0, "total_gb": 0, "free_gb": 0}
    try:
        vm = psutil.virtual_memory()
        return {
            "percent": round(vm.percent, 1),
            "used_gb": round(vm.used / (1024 ** 3), 2),
            "total_gb": round(vm.total / (1024 ** 3), 2),
            "free_gb": round(vm.available / (1024 ** 3), 2)
        }
    except Exception as err:
        return {"percent": 0, "error": str(err)}


def get_disk_telemetry():
    """Query primary filesystem storage."""
    if not psutil:
        return {"percent": 0, "used_gb": 0, "total_gb": 0, "free_gb": 0}
    try:
        usage = psutil.disk_usage("/")
        return {
            "percent": round(usage.percent, 1),
            "used_gb": round(usage.used / (1024 ** 3), 1),
            "total_gb": round(usage.total / (1024 ** 3), 1),
            "free_gb": round(usage.free / (1024 ** 3), 1)
        }
    except Exception as err:
        return {"percent": 0, "error": str(err)}


def get_ollama_info():
    """Fetch Ollama model inventory and engine health."""
    url = "http://127.0.0.1:11434/api/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DoshieControlPanel/1.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            running = set()
            try:
                with urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=2.5) as ps_resp:
                    ps_data = json.loads(ps_resp.read().decode("utf-8"))
                    running = {model.get("name") for model in ps_data.get("models", []) if model.get("name")}
            except Exception:
                pass
            models = []
            for m in data.get("models", []):
                size_b = m.get("size", 0)
                size_gb = round(size_b / (1024 ** 3), 2)
                details = m.get("details", {})
                models.append({
                    "name": m.get("name"),
                    "active": m.get("name") in running,
                    "size_gb": size_gb,
                    "parameter_size": details.get("parameter_size", ""),
                    "quantization": details.get("quantization_level", ""),
                    "family": details.get("family", ""),
                    "modified": m.get("modified_at", "")[:19].replace("T", " ")
                })
            return {
                "online": True,
                "count": len(models),
                "models": models
            }
    except Exception as exc:
        return {
            "online": False,
            "count": 0,
            "models": [],
            "error": str(exc)
        }


def get_voice_info():
    """Fetch Hermes voice server status from port 5051."""
    url = "http://127.0.0.1:5051/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DoshieControlPanel/1.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "online": bool(data.get("online", True)),
                "status": data.get("status", "ready"),
                "voice": data.get("voice", "Hermes"),
                "engine": data.get("engine", "chatterbox-nano"),
                "local": data.get("local", True),
                "port": 5051
            }
    except Exception as exc:
        return {
            "online": False,
            "status": "offline",
            "port": 5051,
            "error": str(exc)
        }


def get_services_status():
    """Check systemd unit and background process statuses."""
    doshie_active = _run_cmd(["systemctl", "is-active", "doshie"]) == "active"
    ollama_active = _run_cmd(["systemctl", "is-active", "ollama"]) == "active"
    tailscale_active = _run_cmd(["systemctl", "is-active", "tailscaled"]) == "active"

    # Check voice server process
    voice_proc = _run_cmd(["pgrep", "-f", "yoshi_voice_server.py"]) != ""

    return {
        "doshie_service": {
            "name": "Doshie Web Server",
            "active": doshie_active,
            "port": 5000
        },
        "voice_server": {
            "name": "Hermes Voice Engine",
            "active": voice_proc,
            "port": 5051
        },
        "ollama_service": {
            "name": "Ollama LLM Engine",
            "active": ollama_active,
            "port": 11434
        },
        "tailscale": {
            "name": "Tailscale Mesh VPN",
            "active": tailscale_active
        }
    }


def get_full_telemetry():
    """Assemble complete telemetry dictionary for the control panel."""
    boot = psutil.boot_time() if psutil else time.time()
    uptime_sec = int(time.time() - boot)
    days = uptime_sec // 86400
    hours = (uptime_sec % 86400) // 3600
    mins = (uptime_sec % 3600) // 60
    uptime_str = f"{days}d {hours}h {mins}m" if days > 0 else f"{hours}h {mins}m"

    gpu = get_gpu_telemetry()
    cpu = get_cpu_telemetry()
    mem = get_memory_telemetry()
    disk = get_disk_telemetry()
    ollama = get_ollama_info()
    voice = get_voice_info()
    services = get_services_status()

    # Overall system health score
    health = "optimal"
    if not ollama["online"] or not voice["online"]:
        health = "attention"
    if gpu.get("temp_state") == "hot" or mem.get("percent", 0) > 90:
        health = "warning"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "health": health,
        "host": {
            "hostname": platform.node(),
            "os": platform.system(),
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "uptime": uptime_str,
            "uptime_seconds": uptime_sec
        },
        "gpu": gpu,
        "cpu": cpu,
        "memory": mem,
        "disk": disk,
        "ollama": ollama,
        "voice": voice,
        "services": services
    }


# --- API Routes ---

@control_panel_bp.route("/api/control-panel/telemetry", methods=["GET"])
def api_telemetry():
    return jsonify(get_full_telemetry())


@control_panel_bp.route("/api/control-panel/ping-brain", methods=["GET", "POST"])
def api_ping_brain():
    """Measure inference latency on Ollama with a compact prompt."""
    req_data = request.get_json(silent=True) or {}
    model = req_data.get("model") or "qwen3.5:4b"
    t0 = time.perf_counter()
    url = "http://127.0.0.1:11434/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": "Say pong",
        "stream": False,
        "options": {
            "num_predict": 2,
            "temperature": 0.0
        }
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            reply = data.get("response", "").strip() or "pong"
            return jsonify({
                "ok": True,
                "latency_ms": elapsed_ms,
                "model": model,
                "reply": reply
            })
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        return jsonify({
            "ok": False,
            "latency_ms": elapsed_ms,
            "model": model,
            "error": str(exc)
        }), 502


@control_panel_bp.route("/api/control-panel/ping-voice", methods=["GET"])
def api_ping_voice():
    """Measure latency to the Hermes voice server."""
    t0 = time.perf_counter()
    url = "http://127.0.0.1:5051/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DoshieControlPanel/1.0"})
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            return jsonify({
                "ok": True,
                "latency_ms": elapsed_ms,
                "status": data.get("status", "ready"),
                "voice": data.get("voice", "Hermes")
            })
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        return jsonify({
            "ok": False,
            "latency_ms": elapsed_ms,
            "error": str(exc)
        }), 502


@control_panel_bp.route("/api/control-panel/logs", methods=["GET"])
def api_logs():
    """Retrieve the latest log lines for a designated service."""
    service = request.args.get("service", "doshie")
    try:
        lines_count = min(max(int(request.args.get("lines", 50)), 10), 200)
    except (TypeError, ValueError):
        lines_count = 50

    log_lines = []
    if service == "doshie":
        out = _run_cmd(["journalctl", "-u", "doshie", "-n", str(lines_count), "--no-pager"], timeout=3)
        log_lines = out.splitlines() if out else ["No Doshie journal logs available."]
    elif service == "ollama":
        out = _run_cmd(["journalctl", "-u", "ollama", "-n", str(lines_count), "--no-pager"], timeout=3)
        log_lines = out.splitlines() if out else ["No Ollama journal logs available."]
    elif service == "voice":
        voice_path = Path("/tmp/doshie-voice.log")
        if voice_path.exists():
            try:
                with open(voice_path, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                    log_lines = [line.rstrip() for line in all_lines[-lines_count:]]
            except Exception as exc:
                log_lines = [f"Could not read voice log: {exc}"]
        else:
            log_lines = ["Voice log /tmp/doshie-voice.log does not exist."]
    elif service == "supervisor":
        sup_path = Path("/home/doshie/Doshie/doshie-supervisor.log")
        if sup_path.exists():
            try:
                with open(sup_path, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                    log_lines = [line.rstrip() for line in all_lines[-lines_count:]]
            except Exception as exc:
                log_lines = [f"Could not read supervisor log: {exc}"]
        else:
            log_lines = ["Supervisor log does not exist."]
    else:
        return jsonify({"ok": False, "error": f"Unknown service '{service}'"}), 400

    return jsonify({
        "ok": True,
        "service": service,
        "count": len(log_lines),
        "lines": log_lines
    })


@control_panel_bp.route("/api/control-panel/action", methods=["POST"])
def api_action():
    """Execute operational and maintenance actions."""
    data = request.get_json(silent=True) or {}
    action = data.get("action")

    if action == "restart_voice":
        try:
            # Kill existing instance
            _run_cmd(["pkill", "-f", "yoshi_voice_server.py"], timeout=3)
            time.sleep(0.5)

            # Start background instance
            python_bin = "/home/doshie/Doshie/.venv/bin/python"
            script_path = "/home/doshie/Doshie/yoshi_voice_server.py"
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            log_file = open("/tmp/doshie-voice.log", "a")

            subprocess.Popen(
                [python_bin, script_path],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True
            )
            return jsonify({
                "ok": True,
                "action": "restart_voice",
                "message": "Hermes voice server restart initiated (port 5051)."
            })
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    elif action == "flush_cache":
        try:
            collected = gc.collect()
            return jsonify({
                "ok": True,
                "action": "flush_cache",
                "message": f"Memory cache flushed ({collected} objects collected)."
            })
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    elif action == "restart_ollama":
        try:
            # Try restarting systemd unit
            res = subprocess.run(["systemctl", "restart", "ollama"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return jsonify({
                    "ok": True,
                    "action": "restart_ollama",
                    "message": "Ollama service successfully restarted."
                })
            return jsonify({
                "ok": False,
                "action": "restart_ollama",
                "message": f"Ollama restart requires elevated privileges: {res.stderr.strip()}"
            }), 403
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    elif action == "restart_doshie":
        # Graceful restart helper matching /system/restart
        def _terminate():
            os.kill(os.getpid(), signal.SIGTERM)

        timer = threading.Timer(0.75, _terminate)
        timer.daemon = True
        timer.start()
        return jsonify({
            "ok": True,
            "action": "restart_doshie",
            "message": "Doshie web server is restarting in 1 second..."
        })

    return jsonify({"ok": False, "error": f"Unsupported action '{action}'"}), 400


# =========================================================================
# Antigravity Conversations & Transcripts API
# =========================================================================

ANTIGRAVITY_BRAIN_DIR = Path.home() / ".gemini" / "antigravity-cli" / "brain"
DOSHIE_SESSIONS_FILE = Path.home() / "yoshi" / "chat_sessions.json"


def _clean_user_prompt(content: str) -> str:
    """Strip XML tags like <USER_REQUEST> from raw prompt for clean UI display."""
    if not content:
        return "(Empty prompt)"
    import re
    match = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", content, re.DOTALL)
    if match:
        text = match.group(1).strip()
        if text:
            return text
    # Clean any remaining tags if partially matched
    cleaned = re.sub(r"<[A-Z_]+>.*?</[A-Z_]+>", "", content, flags=re.DOTALL).strip()
    return cleaned or content.strip() or "(Empty prompt)"


def _parse_transcript_file(transcript_path: Path):
    """Parse a transcript.jsonl file into structured turns."""
    turns = []
    current_turn = None
    last_tool = None
    step_count = 0
    tool_call_count = 0

    if not transcript_path.exists():
        return turns, 0, 0

    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                step_count += 1
                try:
                    step = json.loads(line)
                except Exception:
                    continue

                stype = step.get("type")
                source = step.get("source")
                content = step.get("content", "")
                created_at = step.get("created_at", "")

                if stype == "USER_INPUT" or (source == "USER_EXPLICIT" and stype != "PLANNER_RESPONSE"):
                    if current_turn:
                        turns.append(current_turn)

                    clean_text = _clean_user_prompt(content)
                    current_turn = {
                        "turn_index": len(turns) + 1,
                        "user": {
                            "text": clean_text,
                            "raw": content,
                            "created_at": created_at,
                        },
                        "thoughts": [],
                        "tool_calls": [],
                        "assistant_replies": [],
                        "created_at": created_at,
                    }
                    last_tool = None
                elif current_turn is not None:
                    thinking = step.get("thinking")
                    if thinking:
                        current_turn["thoughts"].append({
                            "text": thinking.strip(),
                            "created_at": created_at,
                        })

                    tool_calls = step.get("tool_calls")
                    if tool_calls and isinstance(tool_calls, list):
                        for tc in tool_calls:
                            tool_call_count += 1
                            tc_item = {
                                "name": tc.get("name", "tool"),
                                "args": tc.get("args", {}),
                                "action": tc.get("args", {}).get("toolAction", "") if isinstance(tc.get("args"), dict) else "",
                                "summary": tc.get("args", {}).get("toolSummary", "") if isinstance(tc.get("args"), dict) else "",
                                "result": None,
                                "created_at": created_at,
                            }
                            current_turn["tool_calls"].append(tc_item)
                            last_tool = tc_item

                    if stype == "GENERIC" and last_tool is not None:
                        last_tool["result"] = content
                        last_tool = None

                    if stype == "PLANNER_RESPONSE" and content:
                        current_turn["assistant_replies"].append({
                            "text": content,
                            "created_at": created_at,
                        })

        if current_turn:
            turns.append(current_turn)
    except Exception as exc:
        print(f"Error parsing transcript {transcript_path}: {exc}")

    return turns, step_count, tool_call_count


@control_panel_bp.route("/api/antigravity/conversations", methods=["GET"])
def api_antigravity_conversations():
    """List all available Antigravity assistant conversation sessions."""
    conversations = []
    if ANTIGRAVITY_BRAIN_DIR.exists():
        for conv_dir in ANTIGRAVITY_BRAIN_DIR.iterdir():
            if not conv_dir.is_dir():
                continue
            transcript_file = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"
            if transcript_file.exists():
                try:
                    stat = transcript_file.stat()
                    # Read first line for title
                    title = "Conversation " + conv_dir.name[:8]
                    first_prompt = ""
                    with open(transcript_file, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            if line.strip():
                                try:
                                    first_step = json.loads(line)
                                    raw_c = first_step.get("content", "")
                                    first_prompt = _clean_user_prompt(raw_c)
                                    if first_prompt and first_prompt != "(Empty prompt)":
                                        title = first_prompt[:70] + ("..." if len(first_prompt) > 70 else "")
                                    break
                                except Exception:
                                    pass

                    conversations.append({
                        "id": conv_dir.name,
                        "title": title,
                        "preview": first_prompt[:120],
                        "updated_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "created_at": datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat(),
                        "file_size": stat.st_size,
                    })
                except Exception as exc:
                    print(f"Error reading conv {conv_dir.name}: {exc}")

    # Sort newest first
    conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return jsonify({
        "ok": True,
        "count": len(conversations),
        "conversations": conversations,
    })


@control_panel_bp.route("/api/antigravity/conversations/<conv_id>", methods=["GET"])
def api_antigravity_conversation_detail(conv_id):
    """Retrieve full structured turns for a specific Antigravity conversation."""
    safe_id = Path(conv_id).name
    conv_dir = ANTIGRAVITY_BRAIN_DIR / safe_id
    transcript_file = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"

    if not transcript_file.exists():
        return jsonify({"ok": False, "error": f"Conversation {safe_id} not found"}), 404

    turns, step_count, tool_count = _parse_transcript_file(transcript_file)
    stat = transcript_file.stat()

    title = f"Conversation {safe_id[:8]}"
    if turns and turns[0].get("user", {}).get("text"):
        p = turns[0]["user"]["text"]
        if p and p != "(Empty prompt)":
            title = p[:70] + ("..." if len(p) > 70 else "")

    return jsonify({
        "ok": True,
        "id": safe_id,
        "title": title,
        "turns": turns,
        "turn_count": len(turns),
        "step_count": step_count,
        "tool_call_count": tool_count,
        "updated_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    })


@control_panel_bp.route("/api/antigravity/conversations/<conv_id>/export", methods=["GET"])
def api_antigravity_conversation_export(conv_id):
    """Export conversation as formatted Markdown or JSON."""
    safe_id = Path(conv_id).name
    conv_dir = ANTIGRAVITY_BRAIN_DIR / safe_id
    transcript_file = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"

    if not transcript_file.exists():
        return jsonify({"ok": False, "error": "Not found"}), 404

    fmt = request.args.get("format", "md").lower()
    turns, _, _ = _parse_transcript_file(transcript_file)

    if fmt == "json":
        from flask import Response
        return Response(
            json.dumps({"id": safe_id, "turns": turns}, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename=conversation-{safe_id[:8]}.json"}
        )

    # Markdown export
    lines = [f"# Antigravity Session: {safe_id}", ""]
    for turn in turns:
        lines.append(f"## 👤 User (Turn {turn['turn_index']})")
        lines.append(turn.get("user", {}).get("text", ""))
        lines.append("")

        if turn.get("thoughts"):
            lines.append("<details><summary>🧠 Thought Process</summary>")
            lines.append("")
            for t in turn["thoughts"]:
                lines.append(f"> {t.get('text', '')}")
            lines.append("</details>")
            lines.append("")

        if turn.get("tool_calls"):
            lines.append("<details><summary>⚡ Tool Calls (" + str(len(turn['tool_calls'])) + ")</summary>")
            lines.append("")
            for tc in turn["tool_calls"]:
                lines.append(f"- **`{tc.get('name')}`**")
                if tc.get('result'):
                    lines.append(f"  ```\n  {str(tc['result'])[:300]}\n  ```")
            lines.append("</details>")
            lines.append("")

        for reply in turn.get("assistant_replies", []):
            lines.append("## 🤖 Assistant")
            lines.append(reply.get("text", ""))
            lines.append("")
        lines.append("---")
        lines.append("")

    from flask import Response
    return Response(
        "\n".join(lines),
        mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=session-{safe_id[:8]}.md"}
    )


# =========================================================================
# Doshie Multi-Session Chat Manager API
# =========================================================================

def _load_doshie_sessions():
    if not DOSHIE_SESSIONS_FILE.exists():
        return {}
    try:
        with open(DOSHIE_SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_doshie_sessions(sessions_dict):
    DOSHIE_SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DOSHIE_SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions_dict, f, indent=2)


def _is_requester_admin(requester_name: str) -> bool:
    if not requester_name:
        return False
    try:
        import Doshie_roles
        flags = Doshie_roles.role_flags(requester_name)
        return flags.get("is_admin", False)
    except Exception:
        return requester_name.strip().casefold() in {"hermes", "admin", "owner"}


@control_panel_bp.route("/api/chat/sessions", methods=["GET"])
def api_get_chat_sessions():
    """Get all saved chat sessions for a profile with strict privacy boundaries."""
    profile = (request.args.get("profile") or "Hermes").strip()
    requester = (request.args.get("requester") or profile).strip()

    is_admin = _is_requester_admin(requester)
    # Non-admin users are strictly isolated to their own sessions only
    if not is_admin and requester.casefold() != profile.casefold():
        return jsonify({
            "ok": False,
            "error": "Forbidden: You cannot access other users' chat sessions.",
            "sessions": []
        }), 403

    all_sessions = _load_doshie_sessions()
    profile_sessions = all_sessions.get(profile, [])
    # Sort newest updated first
    profile_sessions.sort(key=lambda s: s.get("updated_at", 0), reverse=True)
    return jsonify({
        "ok": True,
        "profile": profile,
        "is_admin_view": is_admin and (requester.casefold() != profile.casefold()),
        "sessions": profile_sessions,
    })


@control_panel_bp.route("/api/chat/sessions", methods=["POST"])
def api_save_chat_session():
    """Create or update a chat session."""
    data = request.get_json(silent=True) or {}
    profile = (data.get("profile") or "Hermes").strip()
    session_id = data.get("id") or str(int(time.time() * 1000))
    title = data.get("title") or "New Chat"
    messages = data.get("messages") or []

    all_sessions = _load_doshie_sessions()
    profile_sessions = all_sessions.get(profile, [])

    # Find existing session or append new
    idx = next((i for i, s in enumerate(profile_sessions) if s.get("id") == session_id), None)
    now_ts = int(time.time() * 1000)

    session_obj = {
        "id": session_id,
        "title": title,
        "messages": messages,
        "created_at": profile_sessions[idx].get("created_at", now_ts) if idx is not None else now_ts,
        "updated_at": now_ts,
    }

    if idx is not None:
        profile_sessions[idx] = session_obj
    else:
        profile_sessions.insert(0, session_obj)

    all_sessions[profile] = profile_sessions
    _save_doshie_sessions(all_sessions)

    return jsonify({"ok": True, "session": session_obj})


@control_panel_bp.route("/api/chat/sessions/<session_id>", methods=["DELETE"])
def api_delete_chat_session(session_id):
    """Delete a chat session."""
    profile = (request.args.get("profile") or "Hermes").strip()
    all_sessions = _load_doshie_sessions()
    profile_sessions = all_sessions.get(profile, [])

    filtered = [s for s in profile_sessions if s.get("id") != session_id]
    all_sessions[profile] = filtered
    _save_doshie_sessions(all_sessions)

    return jsonify({"ok": True, "deleted_id": session_id})


@control_panel_bp.route("/api/admin/oversight", methods=["GET"])
def api_admin_oversight():
    """Admin-only overview of all guest and family profiles, their chats, and memories."""
    requester = (request.args.get("requester") or "Hermes").strip()
    if not _is_requester_admin(requester):
        return jsonify({"ok": False, "error": "Admin privileges required"}), 403

    try:
        import Doshie_memory
        import Doshie_roles
    except ImportError:
        import yoshi_memory as Doshie_memory
        import yoshi_roles as Doshie_roles

    all_sessions = _load_doshie_sessions()
    
    # Load all members
    members = []
    # Always include Owner Hermes
    members.append({
        "id": "owner",
        "name": "Hermes",
        "role": "Owner Administrator",
        "is_admin": True,
        "is_child": False,
    })
    
    seen = {"hermes"}
    for member_id, name, role, _notes in Doshie_memory.get_family_members():
        clean = " ".join((name or "").split()).strip()
        if not clean or clean.casefold() in seen:
            continue
        seen.add(clean.casefold())
        flags = Doshie_roles.role_flags(clean, role)
        members.append({
            "id": f"family-{member_id}",
            "name": clean,
            "role": role or "Guest / Family",
            **flags,
        })

    # Enrich each profile with chat count, memory count, and latest activity
    results = []
    for m in members:
        p_name = m["name"]
        p_sessions = all_sessions.get(p_name, [])
        p_memories = Doshie_memory.get_memories(profile=p_name, include_inactive=True)
        
        last_chat_ts = max([s.get("updated_at", 0) for s in p_sessions], default=0)
        
        results.append({
            "name": p_name,
            "role": m.get("role", "Family"),
            "is_admin": m.get("is_admin", False),
            "is_child": m.get("is_child", False),
            "chat_count": len(p_sessions),
            "memory_count": len(p_memories),
            "last_active": last_chat_ts,
            "recent_memories": [
                {
                    "id": mem[0],
                    "memory": mem[1],
                    "category": mem[2],
                    "importance": mem[3],
                    "created_at": mem[4],
                }
                for mem in p_memories[:5]
            ],
        })

    return jsonify({
        "ok": True,
        "profiles": results,
    })


@control_panel_bp.route("/api/admin/guest-memories", methods=["GET"])
def api_admin_guest_memories():
    """Admin-only inspection of specific guest memories."""
    requester = (request.args.get("requester") or "Hermes").strip()
    if not _is_requester_admin(requester):
        return jsonify({"ok": False, "error": "Admin privileges required"}), 403

    profile = (request.args.get("profile") or "").strip()
    if not profile:
        return jsonify({"ok": False, "error": "Profile name is required"}), 400

    try:
        import Doshie_memory
    except ImportError:
        import yoshi_memory as Doshie_memory

    memories = Doshie_memory.memory_center_records(profile=profile, include_inactive=True)
    return jsonify({
        "ok": True,
        "profile": profile,
        "count": len(memories),
        "memories": [
            {
                "id": m[0],
                "memory": m[1],
                "category": m[2],
                "importance": m[3],
                "created_at": m[4],
                "updated_at": m[5],
                "active": bool(m[6]),
                "profile": m[7] if len(m) > 7 else profile,
                "scope": m[8] if len(m) > 8 else "private",
            }
            for m in memories
        ]
    })


def register_control_panel(app):
    """Register the control panel blueprint on the main Flask app."""
    app.register_blueprint(control_panel_bp)

