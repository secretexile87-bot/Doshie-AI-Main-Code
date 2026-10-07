"""Web server and REST API for the Doshie Dedicated Agent GUI.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import urllib.request

from flask import Flask, jsonify, render_template, request, send_from_directory

from agent import session_manager, OLLAMA_BASE_URL
from tools import APPROVAL_REQUIRED_TOOLS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("doshie_agent_server")

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static")
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/models", methods=["GET"])
def get_models():
    """Fetch installed Ollama models and server status."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [
                {
                    "name": m.get("name"),
                    "size": round(m.get("size", 0) / (1024**3), 1),
                    "parameter_size": m.get("details", {}).get("parameter_size", "unknown"),
                    "capabilities": m.get("capabilities", [])
                }
                for m in data.get("models", [])
            ]
            return jsonify({"ok": True, "provider": "ollama", "models": models})
    except Exception as e:
        return jsonify({
            "ok": False,
            "provider": "ollama",
            "error": f"Ollama not reachable: {e}",
            "models": [
                {"name": "qwen2.5-coder:7b", "parameter_size": "7B"},
                {"name": "qwen2.5:14b", "parameter_size": "14B"}
            ]
        })


@app.route("/api/chat", methods=["POST"])
def chat():
    """Receive user message and execute agent turn."""
    data = request.get_json(force=True, silent=True) or {}
    session_id = data.get("session_id")
    user_message = data.get("message", "").strip()
    model = data.get("model", "qwen2.5-coder:7b")
    require_all = bool(data.get("require_all_approval", False))
    api_key = data.get("api_key", "").strip()
    custom_endpoint = data.get("custom_endpoint", "").strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    session = session_manager.get_or_create(session_id, model=model, require_all=require_all)
    if api_key:
        session.api_key = api_key
    if custom_endpoint:
        session.custom_endpoint = custom_endpoint

    result = session.step(user_input=user_message)
    return jsonify({
        "ok": True,
        "session_id": session.session_id,
        "status": result.get("status"),
        "approval": result.get("approval"),
        "reply": result.get("reply"),
        "error": result.get("error"),
        "history": session.history_log
    })


@app.route("/api/approve", methods=["POST"])
def approve():
    """Handle user approval or rejection of an action."""
    data = request.get_json(force=True, silent=True) or {}
    session_id = data.get("session_id")
    approval_id = data.get("approval_id")
    approved = bool(data.get("approved", False))
    feedback = data.get("feedback", "").strip()

    if not session_id or not approval_id:
        return jsonify({"error": "session_id and approval_id are required"}), 400

    session = session_manager.get_or_create(session_id)
    result = session.resolve_approval(approval_id, approved=approved, user_feedback=feedback)

    return jsonify({
        "ok": True,
        "session_id": session.session_id,
        "status": result.get("status"),
        "approval": result.get("approval"),
        "reply": result.get("reply"),
        "error": result.get("error"),
        "history": session.history_log
    })


@app.route("/api/session/<session_id>", methods=["GET"])
def get_session(session_id):
    """Retrieve full conversation history."""
    session = session_manager.get_or_create(session_id)
    return jsonify({
        "ok": True,
        "session_id": session.session_id,
        "model": session.model,
        "pending_approval": session.pending_approval,
        "history": session.history_log
    })


@app.route("/api/session/<session_id>/reset", methods=["POST"])
def reset_session(session_id):
    """Start fresh session."""
    data = request.get_json(force=True, silent=True) or {}
    model = data.get("model", "qwen2.5-coder:7b")
    require_all = bool(data.get("require_all_approval", False))
    session = session_manager.reset_session(session_id, model=model, require_all=require_all)
    return jsonify({"ok": True, "session_id": session.session_id})


if __name__ == "__main__":
    port = int(os.environ.get("AGENT_PORT", 5070))
    logger.info(f"Starting Doshie Dedicated Agent GUI on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
