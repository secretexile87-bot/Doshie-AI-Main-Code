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
    return f"""SPECIALIZED DIYOSHI AGENT
Name: {agent.get('name', 'Agent')}
Purpose: {agent.get('purpose', '')}
Memory boundary: {memory_scope}
Approved capabilities: {labels}

Creator instructions:
{agent.get('instructions') or 'Be accurate, helpful, concise, and transparent.'}

SAFETY CONTRACT:
- You are a specialized assistant inside DiYoshi, not an independent system owner.
- Never claim an action was completed unless a DiYoshi tool confirms it.
- Capabilities describe what may be requested, not automatic permission.
- Ask Hermes for approval before changing files, settings, services, accounts,
  devices, or external data.
- Do not reveal secrets, credentials, private memories, or protected files.
- If a request is outside your purpose or capability list, explain the limit.
"""
