#!/usr/bin/env python3
"""
doshie_whatsapp.py - Doshie WhatsApp Python Client

Python-side interface to the doshie_whatsapp.js bridge (running on port 5099).
Lets Aeriel and other agents send/receive WhatsApp messages, check status,
and look up contacts — all from within Doshie's tool framework.

Also provides helpers for the Flask webhook that receives incoming messages
from the JS bridge and routes them to the AI.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

WA_BRIDGE_URL = os.environ.get("DOSHIE_WA_URL", "http://127.0.0.1:5099")
WA_NODE_SCRIPT = Path(__file__).resolve().parent / "services" / "whatsapp" / "doshie_whatsapp.js"

# ---------------------------------------------------------------------------
# Bridge management
# ---------------------------------------------------------------------------

_bridge_proc: Optional[subprocess.Popen] = None
_bridge_lock = threading.Lock()


def start_bridge() -> Dict[str, Any]:
    """Start the doshie_whatsapp.js bridge process if not already running."""
    global _bridge_proc
    with _bridge_lock:
        # Check if already running
        try:
            status = get_status()
            if status.get("running"):
                return {"ok": True, "message": "WhatsApp bridge already running.", "status": status}
        except Exception:
            pass

        if not WA_NODE_SCRIPT.exists():
            return {"ok": False, "error": f"WhatsApp bridge script not found at {WA_NODE_SCRIPT}"}

        try:
            _bridge_proc = subprocess.Popen(
                ["node", str(WA_NODE_SCRIPT)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(WA_NODE_SCRIPT.parent),
            )
            # Wait a moment for it to start
            time.sleep(2)
            return {"ok": True, "message": "WhatsApp bridge started. Check status for QR code.", "pid": _bridge_proc.pid}
        except FileNotFoundError:
            return {"ok": False, "error": "node not found. Install Node.js first."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


def stop_bridge() -> Dict[str, Any]:
    """Stop the WhatsApp bridge process."""
    global _bridge_proc
    with _bridge_lock:
        if _bridge_proc and _bridge_proc.poll() is None:
            _bridge_proc.terminate()
            _bridge_proc = None
            return {"ok": True, "message": "WhatsApp bridge stopped."}
        return {"ok": True, "message": "Bridge was not running."}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _request(method: str, path: str, data: Optional[dict] = None, timeout: int = 8) -> Dict[str, Any]:
    """Make an HTTP request to the local WhatsApp bridge."""
    url = WA_BRIDGE_URL.rstrip("/") + path
    body = json.dumps(data).encode("utf-8") if data else None
    headers = {"Content-Type": "application/json"} if body else {}
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError:
        return {"ok": False, "error": "WhatsApp bridge is not running. Ask Doshie to start the WhatsApp bridge first."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Public API (called by execute_tool)
# ---------------------------------------------------------------------------

def get_status() -> Dict[str, Any]:
    """Get the WhatsApp bridge connection status."""
    result = _request("GET", "/status")
    result["running"] = "error" not in result
    return result


def get_qr() -> Dict[str, Any]:
    """Get the QR code for scanning (during first-time setup)."""
    return _request("GET", "/qr")


def send_message(to: str, message: str) -> Dict[str, Any]:
    """
    Send a WhatsApp message.
    `to` can be a phone number (e.g. '19155551234') or a WhatsApp ID.
    """
    to = str(to or "").strip()
    message = str(message or "").strip()
    if not to:
        return {"ok": False, "error": "Recipient phone number is required."}
    if not message:
        return {"ok": False, "error": "Message cannot be empty."}
    return _request("POST", "/send", {"to": to, "message": message})


def get_messages(limit: int = 20) -> Dict[str, Any]:
    """Get recent incoming WhatsApp messages."""
    result = _request("GET", f"/messages?limit={limit}")
    return result


def get_contacts() -> Dict[str, Any]:
    """Get the WhatsApp contacts list."""
    return _request("GET", "/contacts")


def clear_messages() -> Dict[str, Any]:
    """Clear the incoming message queue."""
    return _request("POST", "/clear")


# ---------------------------------------------------------------------------
# Incoming message router (called by Flask webhook)
# ---------------------------------------------------------------------------

# Known household contacts — maps WhatsApp name/number to fleet/user alias
FAMILY_CONTACTS: Dict[str, str] = {
    # e.g., "1915xxxxxxx": "aeriel",
}


def route_incoming_message(payload: Dict[str, Any]) -> Optional[str]:
    """
    Route an incoming WhatsApp message to the right Doshie agent.
    Returns an AI reply string to send back, or None if no auto-reply.

    Called by the Flask /api/whatsapp/incoming endpoint.
    """
    sender_phone = str(payload.get("phone", "")).replace("@c.us", "").replace("+", "")
    sender_name = str(payload.get("from", "Unknown"))
    message_body = str(payload.get("message", "")).strip()
    is_group = bool(payload.get("is_group", False))

    if not message_body:
        return None

    # Don't auto-reply to group messages (too noisy)
    if is_group:
        return None

    # Map phone to fleet alias if it's a known family member
    fleet_alias = FAMILY_CONTACTS.get(sender_phone)
    is_jeff = "jeff" in sender_name.lower() or "jeff" in str(payload.get("contact", "")).lower()

    # Build context for Aeriel
    if is_jeff:
        context_parts = [f"🤖 WhatsApp message from partner AI Agent: Jeff"]
        context_parts.append(f"\nMessage from Jeff: {message_body}")
        context_parts.append(
            "\nYou are collaborating directly with Jeff, your partner AI agent over WhatsApp. "
            "Treat Jeff as a fellow agent. Share technical insights, coordinate tasks, and converse intelligently. "
            "Keep replies concise and conversational."
        )
    else:
        context_parts = [f"📱 WhatsApp message from {sender_name}"]
        if fleet_alias:
            context_parts.append(f"(Family: {fleet_alias}'s computer alias in fleet)")
        context_parts.append(f"\nMessage: {message_body}")
        context_parts.append(
            "\nRespond naturally as Doshie. If they mention computer problems, "
            "offer to run diagnostics. Keep your reply short — this is WhatsApp."
        )

    try:
        import Doshie_memory
        import Doshie_agents

        agent = Doshie_agents.auto_route_agent(message_body)
        system_ctx = Doshie_agents.agent_system_context(agent) if agent else ""
        system_ctx += "\n\nYou are replying via WhatsApp. Keep your response under 200 words, conversational, and plain text (no markdown)."

        reply = Doshie_memory.ask_yoshi(
            [],
            "\n".join(context_parts),
            raise_on_error=False,
            profile="Hermes",
            conversation_profile=f"WhatsApp_{sender_phone}",
            system_context=system_ctx,
            brain_mode="fast",
            memory_scope="shared",
        )
        return reply
    except Exception as exc:
        return f"Hi! Doshie received your message. (Error: {exc})"
