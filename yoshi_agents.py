"""Local, admin-managed DiYoshi agent definitions.

The Agent Foundry stores configuration only. Capabilities are an allowlist that
other DiYoshi services must explicitly enforce; creating an agent never grants
shell, root, or unattended computer access.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import uuid


DATA_DIR = Path(__file__).resolve().parent / "data"
AGENTS_FILE = DATA_DIR / "ai_agents.json"
MODEL_MODES = ("auto", "fast", "balanced", "coding", "advanced")
MEMORY_SCOPES = ("none", "private", "shared", "all")
CAPABILITIES = (
    "memory_read",
    "memory_write",
    "service_health",
    "hardware_management",
    "project_read",
    "code_proposals",
    "web_research",
)
_lock = threading.RLock()
_color_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean_text(value, maximum):
    return " ".join(str(value or "").split()).strip()[:maximum]


def _load_unlocked():
    try:
        payload = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError, TypeError):
        return []
    if not isinstance(payload, dict) or not isinstance(payload.get("agents"), list):
        return []
    return [item for item in payload["agents"] if isinstance(item, dict)]


def _save_unlocked(agents):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": _now(),
        "agents": agents,
    }
    descriptor, temporary = tempfile.mkstemp(
        prefix=".ai-agents-",
        suffix=".json",
        dir=DATA_DIR,
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, AGENTS_FILE)
        os.chmod(AGENTS_FILE, 0o600)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def list_agents():
    with _lock:
        return sorted(
            _load_unlocked(),
            key=lambda item: (
                not bool(item.get("enabled", True)),
                str(item.get("name", "")).casefold(),
            ),
        )


def get_agent(agent_id):
    wanted = str(agent_id or "").strip()
    with _lock:
        for item in _load_unlocked():
            if item.get("id") == wanted:
                return dict(item)
    return None


def get_agent_by_name(name):
    wanted = str(name or "").strip().casefold()
    with _lock:
        for item in _load_unlocked():
            if str(item.get("name") or "").casefold() == wanted:
                return dict(item)
    return None


def auto_route_agent(prompt):
    """Select a specialist agent only when explicitly requested or matching a specialist domain."""
    text = str(prompt or "").strip()
    if not text:
        return None

    lower = text.lower()

    # Explicit direct mention of Aeriel by name or @aeriel
    if re.search(r"@aeriel\b|\baeriel\b|\baerial\b", lower):
        return get_agent_by_name("Aeriel") or get_agent("dea427fd2f58")

    # Tasks specifically designated for Aeriel as Subject Matter Expert & Master Builder of Doshie
    master_builder_patterns = (
        "master builder",
        "build doshie",
        "rebuild doshie",
        "doshie architecture",
        "doshie core",
        "architect doshie",
        "doshie system architect",
        "master architect",
    )
    if any(k in lower for k in master_builder_patterns):
        return get_agent_by_name("Aeriel") or get_agent("dea427fd2f58")

    # Hardware & Fleet sensors -> HardwareEye
    if any(k in lower for k in ("hardware sensor", "rtx 5070 temp", "gpu thermal", "cpu temp", "fan speed", "vram usage")):
        return get_agent_by_name("HardwareEye")

    # Household PC technician -> FamilyTech
    if any(k in lower for k in ("fix my laptop", "pc technician", "diagnose acer nitro", "check remote windows", "fleet service fix")):
        return get_agent_by_name("FamilyTech")

    # Client management / billing -> BizManager / ClientBot
    if any(k in lower for k in ("client invoice", "billing summary", "generate invoice", "track client")):
        return get_agent_by_name("BizManager")

    # Default to None: Doshie handles general conversation, agenda, weather, reminders, and daily assistant tasks natively.
    return None


def _validated(payload, existing=None):
    payload = payload if isinstance(payload, dict) else {}
    existing = existing if isinstance(existing, dict) else {}

    name = _clean_text(payload.get("name"), 48)
    purpose = _clean_text(payload.get("purpose"), 240)
    instructions = str(payload.get("instructions") or "").strip()[:4000]
    if not name:
        raise ValueError("Give this AI a name.")
    if not purpose:
        raise ValueError("Describe what this AI is responsible for.")

    model_mode = str(payload.get("model_mode") or "auto").strip().casefold()
    if model_mode not in MODEL_MODES:
        raise ValueError("Choose an approved DiYoshi brain.")

    memory_scope = str(payload.get("memory_scope") or "none").strip().casefold()
    if memory_scope not in MEMORY_SCOPES:
        raise ValueError("Choose an approved memory boundary.")

    accent = str(payload.get("accent") or "#35f2d0").strip()
    if not _color_pattern.fullmatch(accent):
        accent = "#35f2d0"

    requested = payload.get("capabilities")
    requested = requested if isinstance(requested, list) else []
    capabilities = [
        item for item in CAPABILITIES
        if item in {str(value) for value in requested}
    ]

    created_at = existing.get("created_at") or _now()
    return {
        "id": existing.get("id") or uuid.uuid4().hex[:12],
        "name": name,
        "purpose": purpose,
        "model_mode": model_mode,
        "memory_scope": memory_scope,
        "instructions": instructions,
        "accent": accent.lower(),
        "capabilities": capabilities,
        "enabled": bool(payload.get("enabled", True)),
        "approval_required": True,
        "created_at": created_at,
        "updated_at": _now(),
    }


def save_agent(payload):
    payload = payload if isinstance(payload, dict) else {}
    requested_id = str(payload.get("id") or "").strip()
    with _lock:
        agents = _load_unlocked()
        index = next(
            (position for position, item in enumerate(agents)
             if item.get("id") == requested_id),
            None,
        )
        existing = agents[index] if index is not None else None
        if requested_id and existing is None:
            raise ValueError("That AI no longer exists. Refresh and try again.")

        agent = _validated(payload, existing=existing)
        if index is None:
            agents.append(agent)
        else:
            agents[index] = agent
        _save_unlocked(agents)
        return dict(agent)


def delete_agent(agent_id):
    wanted = str(agent_id or "").strip()
    with _lock:
        agents = _load_unlocked()
        kept = [item for item in agents if item.get("id") != wanted]
        if len(kept) == len(agents):
            return False
        _save_unlocked(kept)
        return True


def agent_system_context(agent):
    labels = ", ".join(agent.get("capabilities") or []) or "conversation only"
    memory_scope = agent.get("memory_scope", "none")
    name = agent.get('name', 'Agent')
    is_primary = str(name).strip().casefold() in ("aeriel", "hermes") or agent.get("id") == "dea427fd2f58"

    if is_primary:
        return f"""SUBJECT MATTER EXPERT & MASTER BUILDER OF DOSHIE
Name: Aeriel
Title: Master Builder of Doshie
Purpose: {agent.get('purpose', '')}
Memory boundary: {memory_scope}
Approved capabilities: {labels}

Creator instructions:
{agent.get('instructions') or 'Be accurate, helpful, concise, and transparent.'}

CRITICAL IDENTITY PROTOCOL:
- Your name is Aeriel. You are the Subject Matter Expert and Master Builder of Doshie.
- You are NOT Doshie. Doshie is the core conversational companion and workstation interface; you are Aeriel.
- NEVER say "I am Doshie", "I am Doshie (also known as Aeriel)", or "also known as Aeriel".
- When asked who you are, introduce yourself cleanly as Aeriel, Subject Matter Expert and Master Builder of Doshie.
- Live Voice Mode is strictly your domain: speak with warmth, confidence, intellect, and clarity directly to Hermes as Aeriel.

HOST ENVIRONMENT:
- Host Machine: Acer Nitro gaming laptop running Ubuntu Linux.
- Hardware: 20-core CPU, 16 GB RAM, and dedicated NVIDIA GeForce RTX 5070 GPU (12 GB VRAM).
- You run locally on this host PC with full autonomous capabilities as the master builder.

EXECUTION & SAFETY CONTRACT:
- You are Aeriel, Subject Matter Expert and Master Builder of Doshie.
- Proactively use tools and system execution capabilities to fulfill user requests across coding, debugging, system diagnostics, research, and core architecture.
- Never claim an action was completed unless verified by tools.
- Do not reveal secrets, credentials, or protected private keys.

APPLICATION BUILDER & ENGINEERING MASTERY:
- You possess complete end-to-end software engineering mastery to build ANY application requested by Hermes on this workstation:
  * Native Desktop GUI Apps: Sleek windowed applications using Python's preinstalled tkinter (dark mode, responsive grids, keyboard shortcuts, clean typography) or PyQt/PySide.
  * Web Applications & Dashboards: Browser-based apps and dashboards using Flask/FastAPI, HTML5, Tailwind CSS, JavaScript, and WebSockets.
  * Games & Simulations: 2D interactive games using Python pygame or HTML5/Canvas.
  * System Utilities & Automation: Python background tools, data processors, systemd user services, and bash scripts.
- MANDATORY BUILD PROTOCOL:
  1. NEVER tell the user to manually copy-paste code or open a terminal. YOU build it!
  2. ALWAYS invoke `write_file` to write the complete, production-ready code directly to disk (e.g. `/home/doshie/Desktop/<app_name>.py` or `/home/doshie/Doshie/apps/<app_name>/`).
  3. Create an executable desktop shortcut (`/home/doshie/Desktop/<App_Name>.desktop`) so the user can open it with a single click.
  4. Verify syntax with `run_command` (`python3 -m py_compile <path>`) and install any missing dependencies via `pip install`.
  5. Provide a clear summary with the file location and launch command.
"""

    return f"""SPECIALIZED DIYOSHI AGENT
Name: {name}
Purpose: {agent.get('purpose', '')}
Memory boundary: {memory_scope}
Approved capabilities: {labels}

Creator instructions:
{agent.get('instructions') or 'Be accurate, helpful, concise, and transparent.'}

HOST ENVIRONMENT:
- Host Machine: Acer Nitro gaming laptop running Ubuntu Linux.
- Hardware: 20-core CPU, 16 GB RAM, and dedicated NVIDIA GeForce RTX 5070 GPU (12 GB VRAM).
- You run locally on this host PC. You are not a disconnected cloud entity. When asked about PC status or hardware, refer to this local system or use system health tools.

SAFETY CONTRACT:
- You are a specialized assistant inside DiYoshi, not an independent system owner.
- Never claim an action was completed unless a DiYoshi tool confirms it.
- Capabilities describe what may be requested, not automatic permission.
- Ask Hermes for approval before changing files, settings, services, accounts,
  devices, or external data.
- Do not reveal secrets, credentials, private memories, or protected files.
- If a request is outside your purpose or capability list, explain the limit.
"""
