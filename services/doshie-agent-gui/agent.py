"""Autonomous Agent Session Engine with Interactive Human-in-the-Loop Approval.
Supports local Ollama models (Qwen2.5-Coder, Qwen3.5, etc.) and OpenAI/Gemini compatible APIs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import threading
import time
import urllib.request
import uuid

from tools import TOOL_DEFINITIONS, APPROVAL_REQUIRED_TOOLS, execute_tool

logger = logging.getLogger("doshie_agent")

SYSTEM_PROMPT = """You are Doshie's Autonomous AI Agent — an expert pair-programmer, DevOps engineer, and system assistant for Hermes / Doshie.

Your mission is to help Doshie complete tasks thoroughly, safely, and cleanly.
You have access to powerful tools to interact directly with the local system:
- `run_command`: Execute shell commands (e.g. bash scripts, package management, service controls, git).
- `view_file`: Read existing files with exact line numbers.
- `write_file`: Create or write new files.
- `replace_file_content`: Surgically replace a block of code in an existing file.
- `list_dir`: Inspect directory structure.
- `web_search`: Search the live web for errors, docs, or solutions.

DOSHIE ENVIRONMENT & SERVICES:
- Main Project Root: `/home/doshie/Doshie`
- Real System Services:
  - User Services: `doshie-web.service`, `doshie-agent-console.service`, `doshie-voice.service`, `doshie-voice-studio.service`, `doshie-music-player.service`
    (Check with: `systemctl --user status <service>` or `systemctl --user is-active <service>`)
  - Host Services: `ollama.service`
  - Core Health Diagnostic: run `/home/doshie/Doshie/.venv/bin/python /home/doshie/Doshie/core/doshie_core.py`
- IMPORTANT: When asked to check Doshie health or status, inspect the real Doshie services above or run the health diagnostic script. NEVER guess or check fake services like 'game-server.service' or search the web for video game servers unless the user explicitly asks about games.

OPERATIONAL RULES:
1. Always inspect files (`view_file`) before proposing edits to ensure accurate context.
2. When performing multi-step tasks, explain your reasoning before proposing high-impact tools.
3. Every terminal command and file modification will be presented to Doshie for interactive approval before running.
4. Keep explanations concise, professional, and clear.
5. When a tool finishes, examine its stdout/stderr or output carefully. If an error occurs, analyze it and propose a fix.
6. When the goal is completed, summarize what was achieved with clarity.

TOOL CALL INSTRUCTIONS:
To run a command or tool, always output the tool call or emit a JSON object:
```json
{"name": "<tool_name>", "arguments": {<arguments>}}
```
For example, to run a command:
```json
{"name": "run_command", "arguments": {"command": "python3 /home/doshie/Doshie/core/doshie_core.py", "cwd": "/home/doshie/Doshie"}}
```
Do not ask the user to manually copy and paste commands; always issue the tool call directly so the user can click Approve in the UI.
"""

OLLAMA_BASE_URL = "http://127.0.0.1:11434"


class AgentSession:
    def __init__(self, session_id: str = None, model: str = "qwen2.5-coder:7b", require_all_approval: bool = False):
        self.session_id = session_id or uuid.uuid4().hex[:10]
        self.model = model
        self.require_all_approval = require_all_approval
        self.lock = threading.RLock()
        self.messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.pending_approval: dict | None = None
        self.history_log: list[dict] = []
        self.created_at = time.time()
        self.api_key: str = ""
        self.custom_endpoint: str = ""

    def _call_llm(self, include_tools: bool = True) -> dict:
        """Call Ollama / OpenAI compatible endpoint with tools."""
        endpoint = (self.custom_endpoint or f"{OLLAMA_BASE_URL}/v1/chat/completions").rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint = f"{endpoint}/chat/completions"

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {
            "model": self.model,
            "messages": self.messages,
            "temperature": 0.2,
            "max_tokens": 1500,
        }
        if include_tools:
            body["tools"] = TOOL_DEFINITIONS

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        choice = data.get("choices", [{}])[0]
        return choice.get("message", {})

    def _extract_tool_calls(self, assistant_msg: dict) -> tuple[list[dict], str]:
        calls = assistant_msg.get("tool_calls") or []
        content = (assistant_msg.get("content") or "").strip()
        if calls:
            for c in calls:
                fn = c.get("function") or {}
                args = fn.get("arguments")
                if isinstance(args, dict):
                    fn["arguments"] = json.dumps(args)
                elif args is None:
                    fn["arguments"] = "{}"
            return calls, content

        if not content:
            return [], ""

        tool_calls = []
        clean_text = content

        def _format_args_str(val):
            if isinstance(val, dict):
                return json.dumps(val)
            if isinstance(val, str):
                try:
                    # Validate it parses as JSON or re-dump
                    parsed = json.loads(val)
                    return json.dumps(parsed)
                except Exception:
                    return json.dumps({"raw": val})
            return "{}"

        # 1. Check for <tool_call>...</tool_call> tags
        tc_matches = list(re.finditer(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", clean_text, re.DOTALL))
        for m in reversed(tc_matches):
            try:
                parsed = json.loads(m.group(1))
                t_name = parsed.get("name") or parsed.get("tool") or parsed.get("function")
                t_args = parsed.get("arguments") or parsed.get("parameters") or parsed.get("args") or {}
                if t_name:
                    tool_calls.append({
                        "id": uuid.uuid4().hex[:8],
                        "type": "function",
                        "function": {
                            "name": t_name,
                            "arguments": _format_args_str(t_args)
                        }
                    })
                    clean_text = clean_text[:m.start()] + clean_text[m.end():]
            except Exception:
                pass

        # 2. Check for markdown code blocks: ```(?:json)?\s*(\{.*?\})\s*```
        code_matches = list(re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", clean_text, re.DOTALL))
        for m in reversed(code_matches):
            try:
                parsed = json.loads(m.group(1))
                t_name = parsed.get("name") or parsed.get("tool") or parsed.get("function")
                t_args = parsed.get("arguments") or parsed.get("parameters") or parsed.get("args") or {}
                if t_name:
                    tool_calls.append({
                        "id": uuid.uuid4().hex[:8],
                        "type": "function",
                        "function": {
                            "name": t_name,
                            "arguments": _format_args_str(t_args)
                        }
                    })
                    clean_text = clean_text[:m.start()] + clean_text[m.end():]
            except Exception:
                pass

        # 3. Check for raw embedded JSON objects: scan for '{'
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(clean_text):
            if clean_text[idx] == "{":
                try:
                    obj, end_pos = decoder.raw_decode(clean_text[idx:])
                    if isinstance(obj, dict):
                        t_name = obj.get("name") or obj.get("tool") or obj.get("function")
                        t_args = obj.get("arguments") or obj.get("parameters") or obj.get("args")
                        if t_name and t_args is not None:
                            tool_calls.append({
                                "id": uuid.uuid4().hex[:8],
                                "type": "function",
                                "function": {
                                    "name": t_name,
                                    "arguments": _format_args_str(t_args)
                                }
                            })
                            clean_text = clean_text[:idx] + clean_text[idx + end_pos:]
                            continue
                except Exception:
                    pass
            idx += 1

        clean_text = clean_text.strip()
        return tool_calls, clean_text

    def step(self, user_input: str | None = None) -> dict:
        """Advance agent turn. Either starts from user message or continues after tool run."""
        with self.lock:
            if self.pending_approval:
                # Support conversational affirmative approvals typed into chat
                lower_in = (user_input or "").strip().lower().rstrip(".! ")
                if lower_in in [
                    "yes", "y", "run", "run it", "approve", "go ahead",
                    "okay go ahead", "ok go ahead", "sure", "do it",
                    "proceed", "execute", "how do we run", "run command",
                    "please do", "yes please", "sure go ahead"
                ]:
                    return self.resolve_approval(self.pending_approval["id"], approved=True)
                elif lower_in in ["no", "n", "stop", "cancel", "decline", "don't", "dont"]:
                    return self.resolve_approval(self.pending_approval["id"], approved=False, user_feedback=user_input or "")
                else:
                    return {
                        "status": "awaiting_approval",
                        "approval": self.pending_approval,
                        "reply": "I have an action waiting for your approval above. Tap [Approve & Execute] or reply 'go ahead' to run it."
                    }

            if user_input:
                self.messages.append({"role": "user", "content": user_input})
                self.history_log.append({
                    "id": uuid.uuid4().hex[:8],
                    "role": "user",
                    "content": user_input,
                    "timestamp": time.time()
                })

            # Loop for auto-executable tools (e.g. view_file if not requiring approval)
            max_auto_steps = 5
            for _ in range(max_auto_steps):
                try:
                    assistant_msg = self._call_llm()
                except Exception as e:
                    logger.exception("LLM call failed")
                    err_text = f"⚠️ Model communication error: {str(e)}"
                    return {
                        "status": "error",
                        "error": err_text
                    }

                raw_content = assistant_msg.get("content") or ""
                tool_calls, clean_content = self._extract_tool_calls(assistant_msg)
                if tool_calls and "tool_calls" not in assistant_msg:
                    assistant_msg["tool_calls"] = tool_calls

                msg_entry = {
                    "id": uuid.uuid4().hex[:8],
                    "role": "assistant",
                    "content": clean_content if tool_calls else raw_content,
                    "tool_calls": tool_calls,
                    "timestamp": time.time()
                }
                self.messages.append(assistant_msg)
                self.history_log.append(msg_entry)

                if not tool_calls:
                    return {
                        "status": "completed",
                        "reply": raw_content,
                        "turn": msg_entry
                    }

                # Evaluate first tool call
                call = tool_calls[0]
                call_id = call.get("id") or uuid.uuid4().hex[:8]
                func = call.get("function") or {}
                tool_name = func.get("name", "")
                raw_args = func.get("arguments") or {}

                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {"raw": raw_args}
                else:
                    args = raw_args

                requires_approval = self.require_all_approval or (tool_name in APPROVAL_REQUIRED_TOOLS)

                if requires_approval:
                    # Halt and create approval request
                    clean_thought = clean_content.strip()
                    if not clean_thought:
                        clean_thought = f"I would like permission to run `{tool_name}` on your system."

                    approval_obj = {
                        "id": uuid.uuid4().hex[:8],
                        "call_id": call_id,
                        "tool": tool_name,
                        "args": args,
                        "thought": clean_thought,
                        "timestamp": time.time(),
                        "status": "pending"
                    }
                    self.pending_approval = approval_obj
                    return {
                        "status": "awaiting_approval",
                        "approval": approval_obj,
                        "reply": clean_thought
                    }
                else:
                    # Auto-execute safe read-only tool
                    tool_result = execute_tool(tool_name, args)
                    tool_resp_str = json.dumps(tool_result, ensure_ascii=False)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": tool_resp_str
                    })
                    self.history_log.append({
                        "id": uuid.uuid4().hex[:8],
                        "role": "tool_executed",
                        "tool": tool_name,
                        "args": args,
                        "result": tool_result,
                        "timestamp": time.time()
                    })
                    # Continue loop to let model react to read-only tool output

            # If auto-steps completed, synthesize findings for user
            self.messages.append({
                "role": "user",
                "content": "Please synthesize and summarize your findings and actions for the user based on the tool outputs above."
            })
            try:
                summary_msg = self._call_llm(include_tools=False)
                summary_content = (summary_msg.get("content") or "").strip()
                if summary_content:
                    self.messages.append(summary_msg)
                    msg_entry = {
                        "id": uuid.uuid4().hex[:8],
                        "role": "assistant",
                        "content": summary_content,
                        "timestamp": time.time()
                    }
                    self.history_log.append(msg_entry)
                    return {
                        "status": "completed",
                        "reply": summary_content,
                        "turn": msg_entry
                    }
            except Exception as e:
                logger.warning(f"Summary call error: {e}")

            return {
                "status": "completed",
                "reply": "Inspection completed. See the tool results above for details.",
            }

    def resolve_approval(self, approval_id: str, approved: bool, user_feedback: str = "") -> dict:
        """Handles user approval or rejection of a pending tool call."""
        with self.lock:
            if not self.pending_approval or self.pending_approval["id"] != approval_id:
                return {"status": "error", "error": "No matching pending approval found"}

            current_approval = self.pending_approval
            self.pending_approval = None

            tool_name = current_approval["tool"]
            args = current_approval["args"]
            call_id = current_approval["call_id"]

            if approved:
                # Execute tool on host
                result = execute_tool(tool_name, args)
                tool_msg_content = json.dumps(result, ensure_ascii=False)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": tool_msg_content
                })
                self.history_log.append({
                    "id": uuid.uuid4().hex[:8],
                    "role": "tool_executed",
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                    "timestamp": time.time()
                })
            else:
                # User declined
                feedback = user_feedback.strip() or "User declined this action."
                decline_result = {"ok": False, "status": "declined_by_user", "message": feedback}
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(decline_result)
                })
                self.history_log.append({
                    "id": uuid.uuid4().hex[:8],
                    "role": "tool_declined",
                    "tool": tool_name,
                    "args": args,
                    "feedback": feedback,
                    "timestamp": time.time()
                })

            # Resume agent to process the outcome
            return self.step()


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, AgentSession] = {}
        self._lock = threading.RLock()

    def get_or_create(self, session_id: str | None = None, model: str = "qwen2.5-coder:7b", require_all: bool = False) -> AgentSession:
        with self._lock:
            if session_id and session_id in self._sessions:
                sess = self._sessions[session_id]
                sess.model = model
                sess.require_all_approval = require_all
                return sess

            new_id = session_id or uuid.uuid4().hex[:10]
            sess = AgentSession(session_id=new_id, model=model, require_all_approval=require_all)
            self._sessions[new_id] = sess
            return sess

    def reset_session(self, session_id: str, model: str = "qwen2.5-coder:7b", require_all: bool = False) -> AgentSession:
        with self._lock:
            sess = AgentSession(session_id=session_id, model=model, require_all_approval=require_all)
            self._sessions[session_id] = sess
            return sess

    def list_sessions(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "id": sid,
                    "model": s.model,
                    "turn_count": len([m for m in s.messages if m.get("role") == "user"]),
                    "created_at": s.created_at
                }
                for sid, s in self._sessions.items()
            ]


session_manager = SessionManager()
