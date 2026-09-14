import json
import re
import threading
import urllib.parse
import urllib.request

import yoshi_agents
import yoshi_code_tools
import yoshi_permissions


_ACTIVE_RESPONSES = {}
_ACTIVE_RESPONSES_LOCK = threading.RLock()
_AGENT_CALL = threading.local()


def cancel_request(request_id):
    """Close one active Ollama response by its unguessable request ID."""
    key = str(request_id or "").strip()
    if not key:
        return False
    with _ACTIVE_RESPONSES_LOCK:
        response = _ACTIVE_RESPONSES.pop(key, None)
    if response is None:
        return False
    try:
        response.close()
    except Exception:
        pass
    return True


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_code_files",
            "description": (
                "List approved source-code files in the Yoshi project. "
                "Private files and backups are excluded."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 200
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_code_file",
            "description": (
                "Read numbered lines from one approved project source file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string"},
                    "start_line": {
                        "type": "integer",
                        "minimum": 1
                    },
                    "line_count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 300
                    }
                },
                "required": ["relative_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": (
                "Search approved Yoshi source files for literal text."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propose_code_edit",
            "description": (
                "Create a pending exact source-code edit for administrator approval. "
                "This never applies the edit directly."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "relative_path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                    "run_tests": {"type": "boolean"}
                },
                "required": ["summary", "relative_path", "old_text", "new_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propose_new_file",
            "description": (
                "Create a pending new Builder project file for administrator approval. "
                "The path must stay inside projects/ and is never written automatically."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "relative_path": {"type": "string"},
                    "content": {"type": "string"},
                    "run_tests": {"type": "boolean"}
                },
                "required": ["summary", "relative_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_python_diagnostics",
            "description": (
                "Create a pending Python regression-test request for administrator approval. "
                "The diagnostics never run until the administrator approves them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_hermes_ai",
            "description": (
                "Delegate a focused request to the enabled custom Hermes AI. "
                "Hermes can analyze and propose approved changes but cannot bypass approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request": {"type": "string"}
                },
                "required": ["request"]
            }
        }
    }
]


def execute_tool(name, arguments, actor_profile="", can_propose_changes=False):
    if name == "list_code_files":
        return yoshi_code_tools.list_code_files(
            arguments.get("limit", 100)
        )

    if name == "read_code_file":
        return yoshi_code_tools.read_code_file(
            arguments.get("relative_path"),
            arguments.get("start_line", 1),
            arguments.get("line_count", 200)
        )

    if name == "search_code":
        return yoshi_code_tools.search_code(
            arguments.get("query"),
            arguments.get("limit", 30)
        )

    if name == "propose_code_edit":
        if not can_propose_changes:
            raise ValueError("Only an administrator can propose project changes.")
        return yoshi_permissions.create_code_edit(
            actor_profile,
            arguments.get("summary"),
            arguments.get("relative_path"),
            arguments.get("old_text"),
            arguments.get("new_text"),
            arguments.get("run_tests", True)
        )

    if name == "propose_new_file":
        if not can_propose_changes:
            raise ValueError("Only an administrator can propose new project files.")
        return yoshi_permissions.create_file_request(
            actor_profile,
            arguments.get("summary"),
            arguments.get("relative_path"),
            arguments.get("content"),
            arguments.get("run_tests", False),
        )

    if name == "request_python_diagnostics":
        if not can_propose_changes:
            raise ValueError("Only an administrator can request Python diagnostics.")
        return yoshi_permissions.create_regression_request(
            actor_profile,
            arguments.get("summary") or "Run shared DiYoshi and Hermes Python diagnostics"
        )

    if name == "consult_hermes_ai":
        if not can_propose_changes:
            raise ValueError("The Hermes AI tool is administrator-only.")
        if getattr(_AGENT_CALL, "active", False):
            raise ValueError("Hermes AI cannot recursively call itself.")
        request_text = str(arguments.get("request") or "").strip()
        if not request_text:
            raise ValueError("Give Hermes AI a focused request.")
        if len(request_text) > 4000:
            raise ValueError("Keep the Hermes AI request under 4,000 characters.")
        agent = next(
            (
                item for item in yoshi_agents.list_agents()
                if item.get("name", "").casefold() == "hermes"
                and item.get("enabled", True)
            ),
            None,
        )
        if not agent:
            raise ValueError("The Hermes AI tool is unavailable or disabled.")
        import yoshi_memory
        _AGENT_CALL.active = True
        try:
            reply = yoshi_memory.ask_yoshi(
                [],
                request_text,
                raise_on_error=True,
                profile=actor_profile or "Hermes",
                conversation_profile="Agent " + agent["id"],
                system_context=yoshi_agents.agent_system_context(agent),
                brain_mode=agent.get("model_mode", "auto"),
                memory_scope=agent.get("memory_scope", "none"),
            )
        finally:
            _AGENT_CALL.active = False
        return {
            "agent": agent["name"],
            "reply": reply,
            "approval_required": True,
        }

    raise ValueError("Unknown or unauthorized tool.")



def needs_project_tools(messages):
    latest = ""

    for message in reversed(messages):
        if message.get("role") == "user":
            latest = str(message.get("content") or "").lower()
            break

    triggers = (
        "use your project tools",
        "project file",
        "source code",
        "codebase",
        "inspect the project",
        "search the code",
        "read the file",
        "line number",
        "yoshi_web.py",
        "yoshi_memory.py",
        "yoshi_router.py",
        "coding builder mode",
        "approval queue",
        "ask hermes ai",
        "consult hermes",
        "use hermes ai",
        "hermes ai tool",
        "python error",
        "python problem",
        "self repair",
        "fix yourself",
        "diagnose your code",
        "run python diagnostics"
    )

    return any(trigger in latest for trigger in triggers)

def _vision_chat(
    url, model, messages, images, timeout=180, request_id=""
):
    parts = urllib.parse.urlsplit(url)
    native_url = urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, "/api/chat", "", "")
    )
    vision_messages = [
        {
            "role": str(message.get("role") or "user"),
            "content": str(message.get("content") or ""),
        }
        for message in messages
        if message.get("role") in {"system", "user", "assistant"}
    ]
    for message in reversed(vision_messages):
        if message["role"] == "user":
            message["images"] = list(images)
            break

    payload = json.dumps({
        "model": model,
        "messages": vision_messages,
        "stream": False,
        "think": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.25,
            "num_predict": 300,
        },
    }).encode("utf-8")
    request = urllib.request.Request(
        native_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    response = urllib.request.urlopen(request, timeout=timeout)
    key = str(request_id or "").strip()
    if key:
        with _ACTIVE_RESPONSES_LOCK:
            _ACTIVE_RESPONSES[key] = response
    try:
        data = json.loads(response.read().decode("utf-8"))
    finally:
        if key:
            with _ACTIVE_RESPONSES_LOCK:
                if _ACTIVE_RESPONSES.get(key) is response:
                    _ACTIVE_RESPONSES.pop(key, None)
        response.close()
    model_message = data.get("message") or {}
    visible = str(model_message.get("content") or "").strip()
    if visible:
        return visible
    # Some local Qwen builds place vision descriptions in reasoning even when
    # thinking is disabled. Surface that text rather than returning blank.
    fallback = str(model_message.get("thinking") or "")
    fallback = re.sub(r"</?think>", "", fallback).strip()
    sentences = re.findall(r"[^.!?]+[.!?]", fallback)
    if sentences:
        return " ".join(sentences[-2:]).strip()
    return "I received the image, but the local vision model returned no description."


def chat(
    url, model, messages, timeout=180, request_id="",
    actor_profile="", can_propose_changes=False, images=None
):
    if images:
        return _vision_chat(
            url, model, messages, images,
            timeout=timeout, request_id=request_id
        )

    working_messages = list(messages)

    for _ in range(3):
        request_body = {
            "model": model,
            "messages": working_messages,
            "temperature": 0.35,
            "max_tokens": 300,
            "reasoning_effort": "none",
            "think": False,
            "keep_alive": "10m"
        }

        inside_hermes = any(
            message.get("role") == "system"
            and "You are Hermes AI in your dedicated workspace." in str(
                message.get("content") or ""
            )
            for message in working_messages
        )

        if inside_hermes or needs_project_tools(working_messages):
            request_body["tools"] = [
                tool for tool in TOOLS
                if not (
                    inside_hermes
                    and tool["function"]["name"] == "consult_hermes_ai"
                )
            ]

        payload = json.dumps(request_body).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        response = urllib.request.urlopen(request, timeout=timeout)
        key = str(request_id or "").strip()
        if key:
            with _ACTIVE_RESPONSES_LOCK:
                _ACTIVE_RESPONSES[key] = response
        try:
            data = json.loads(response.read().decode("utf-8"))
        finally:
            if key:
                with _ACTIVE_RESPONSES_LOCK:
                    if _ACTIVE_RESPONSES.get(key) is response:
                        _ACTIVE_RESPONSES.pop(key, None)
            close_response = getattr(response, "close", None)
            if callable(close_response):
                close_response()

        message = data["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            return str(message.get("content") or "").strip()

        working_messages.append(message)

        for call in tool_calls:
            function = call.get("function") or {}
            name = str(function.get("name") or "")
            raw_arguments = function.get("arguments") or {}

            try:
                if isinstance(raw_arguments, str):
                    arguments = json.loads(raw_arguments)
                elif isinstance(raw_arguments, dict):
                    arguments = raw_arguments
                else:
                    arguments = {}

                result = execute_tool(
                    name,
                    arguments,
                    actor_profile=actor_profile,
                    can_propose_changes=can_propose_changes
                )
                content = json.dumps(
                    {"ok": True, "result": result},
                    ensure_ascii=False
                )
            except Exception as error:
                content = json.dumps({
                    "ok": False,
                    "error": str(error)
                })

            working_messages.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "content": content
            })

    return "I could not finish inspecting the project within the safe tool limit."
