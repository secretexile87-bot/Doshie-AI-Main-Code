import json
import os
import re
import threading
import urllib.parse
import urllib.request

try:
    import Doshie_agents as yoshi_agents
except ImportError:
    import yoshi_agents
import yoshi_code_tools
try:
    import Doshie_permissions as yoshi_permissions
except ImportError:
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
            "name": "web_search",
            "description": (
                "Search the web for up-to-date information to answer the user's questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on the web."
                    }
                },
                "required": ["query"]
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
    },
    {
        "type": "function",
        "function": {
            "name": "consult_agent",
            "description": (
                "Communicate or delegate a task/question to another specialist AI agent (e.g. 'Tutor', 'Researcher', 'Hermes', or any custom created agent). "
                "The target agent executes the request using their specialized domain instructions and returns the answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "The exact name of the specialist agent to communicate with."
                    },
                    "request": {
                        "type": "string",
                        "description": "The message, subtask, or question to send to the agent."
                    }
                },
                "required": ["agent_name", "request"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_service_health",
            "description": (
                "Check the live hardware status, system diagnostics, test the host PC, or inspect resource usage (CPU, RAM, GPU, storage, thermals), battery, and Doshie services."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "description": "Optional focus: 'all', 'system', 'services', or 'battery'.",
                        "enum": ["all", "system", "services", "battery"]
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_memories",
            "description": (
                "Search long-term memories and saved facts in Doshie for the current profile or shared knowledge."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword or topic to search for in memories."
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 25
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tasks_and_notes",
            "description": (
                "Retrieve active to-do tasks and saved notes recorded in Doshie."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "include_completed": {
                        "type": "boolean",
                        "description": "Whether to include completed tasks."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": (
                "Record a new persistent long-term memory or fact about preferences, family, or environment."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "The information or fact to remember."
                    },
                    "category": {
                        "type": "string",
                        "description": "Category (e.g. 'General', 'Preference', 'Fact', 'Health', 'Project')."
                    },
                    "scope": {
                        "type": "string",
                        "description": "'private' or 'shared'.",
                        "enum": ["private", "shared"]
                    }
                },
                "required": ["fact"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": (
                "Create a new actionable task / to-do item in Doshie."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Description of the task."
                    },
                    "priority": {
                        "type": "string",
                        "description": "Task priority: 'Normal', 'High', or 'Low'.",
                        "enum": ["Normal", "High", "Low"]
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Optional due date or deadline string."
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": (
                "Save a quick reference note in Doshie."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "note": {
                        "type": "string",
                        "description": "The note content to save."
                    }
                },
                "required": ["note"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_hardware",
            "description": (
                "Inspect any computer hardware subsystem (CPU, GPU, RAM, storage, thermals, motherboard, network, PCI, USB, or complete summary). "
                "Provides deep telemetry including temperatures, clock frequencies, governors, power limits, and device topology."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "description": "Subsystem to inspect: 'all', 'summary', 'cpu', 'gpu', 'ram', 'disk', 'thermals', 'motherboard', 'network', 'pci', or 'usb'.",
                        "enum": ["all", "summary", "cpu", "gpu", "ram", "disk", "thermals", "motherboard", "network", "pci", "usb"]
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propose_hardware_change",
            "description": (
                "Safely stage a hardware setting change (e.g. CPU governor, GPU power limit, hardware profile) with safety and thermal validation. "
                "In supervised mode, this generates an impact assessment and does NOT execute until confirmed by user command."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Hardware parameter: 'cpu_governor', 'gpu_power_limit', 'gpu_persistence_mode', or 'profile'.",
                        "enum": ["cpu_governor", "gpu_power_limit", "gpu_persistence_mode", "profile"]
                    },
                    "value": {
                        "type": "string",
                        "description": "New value or profile (e.g. 'performance', 'powersave', '220', 'gaming')."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Explanation or goal of the proposed change."
                    }
                },
                "required": ["target", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_hardware_change",
            "description": (
                "Execute a hardware setting change with explicit user command confirmation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Hardware parameter: 'cpu_governor', 'gpu_power_limit', 'gpu_persistence_mode', or 'profile'."
                    },
                    "value": {
                        "type": "string",
                        "description": "New value or profile to apply."
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "True indicating user explicitly issued command confirmation."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for applying change."
                    }
                },
                "required": ["target", "value", "confirmed"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hardware_governance",
            "description": (
                "Check Doshie's hardware governance state, including current mode (supervised vs self-reasoning), safety bounds, and confirmation requirement."
            ),
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "render_3d_model",
            "description": (
                "Render a 3D model (.obj, .glb, .gltf, .fbx, .ply) in native 4K UHD photorealistic resolution using Blender Cycles and the NVIDIA RTX 5070 GPU with OptiX hardware ray tracing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "input_path": {
                        "type": "string",
                        "description": "Path to the 3D model file."
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional output image path (.png). Defaults to model path with .png suffix."
                    },
                    "samples": {
                        "type": "integer",
                        "description": "Render quality sample count (default: 128)."
                    }
                },
                "required": ["input_path"]
            }
        }
    }
]

CAPABILITY_TOOL_MAP = {
    "web_research": ["web_search"],
    "project_read": ["list_code_files", "read_code_file", "search_code"],
    "code_proposals": ["propose_code_edit", "propose_new_file", "request_python_diagnostics"],
    "service_health": ["check_service_health", "request_python_diagnostics"],
    "hardware_management": ["inspect_hardware", "propose_hardware_change", "execute_hardware_change", "get_hardware_governance"],
    "memory_read": ["search_memories", "get_tasks_and_notes"],
    "memory_write": ["save_memory", "create_task", "add_note"],
    "3d_rendering": ["render_3d_model"],
}



def execute_tool(name, arguments, actor_profile="", can_propose_changes=False):
    if name == "web_search":
        import Doshie_search
        import Doshie_profile_preferences
        is_under_18 = Doshie_profile_preferences.is_profile_under_18(actor_profile)
        return Doshie_search.web_search(arguments.get("query"), is_under_18=is_under_18)

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

    if name == "consult_agent":
        target_name = str(arguments.get("agent_name") or "").strip()
        request_text = str(arguments.get("request") or "").strip()
        if not target_name or not request_text:
            raise ValueError("Both 'agent_name' and 'request' are required.")
        if len(request_text) > 4000:
            raise ValueError("Keep the consultation request under 4,000 characters.")
        agent = next(
            (
                item for item in yoshi_agents.list_agents()
                if item.get("name", "").casefold() == target_name.casefold()
                and item.get("enabled", True)
            ),
            None,
        )
        if not agent:
            available = [a.get("name") for a in yoshi_agents.list_agents() if a.get("enabled", True)]
            raise ValueError(f"Agent '{target_name}' not found or disabled. Available: {', '.join(available)}")
        if getattr(_AGENT_CALL, "active", False):
            raise ValueError("Specialist agents cannot recursively call each other beyond depth 1.")
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
            "consulted_agent": agent["name"],
            "reply": reply,
            "status": "success",
        }

    if name == "check_service_health":
        import socket
        try:
            import Doshie_memory
        except ImportError:
            import yoshi_memory as Doshie_memory

        device_status = Doshie_memory.get_device_status()
        battery = Doshie_memory.get_battery_status()

        def _is_port_open(port):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.4)
                    return sock.connect_ex(("127.0.0.1", port)) == 0
            except Exception:
                return False

        services = {
            "doshie_web": _is_port_open(5000),
            "ollama_ai": _is_port_open(11434),
            "voice_server": _is_port_open(5050),
            "music_player": _is_port_open(5055),
        }
        return {
            "device": device_status,
            "battery": battery,
            "services_online": services,
        }

    if name == "search_memories":
        try:
            import Doshie_memory
        except ImportError:
            import yoshi_memory as Doshie_memory

        mems = Doshie_memory.get_memories(profile=actor_profile or "Hermes", include_inactive=False)
        query = str(arguments.get("query") or "").strip().lower()
        if query:
            mems = [m for m in mems if query in str(m[1]).lower() or query in str(m[2]).lower()]
        limit = min(max(int(arguments.get("limit") or 10), 1), 25)
        return [
            {
                "id": m[0],
                "memory": m[1],
                "category": m[2],
                "importance": m[3],
                "created_at": m[4],
            }
            for m in mems[:limit]
        ]

    if name == "get_tasks_and_notes":
        try:
            import Doshie_memory
        except ImportError:
            import yoshi_memory as Doshie_memory

        include_completed = bool(arguments.get("include_completed", False))
        tasks = Doshie_memory.get_tasks()
        if not include_completed:
            tasks = [t for t in tasks if not t[2]]
        notes = Doshie_memory.get_notes()
        return {
            "tasks": [
                {
                    "id": t[0],
                    "task": t[1],
                    "done": bool(t[2]),
                    "priority": t[3],
                    "due_date": t[4],
                }
                for t in tasks
            ],
            "notes": [
                {
                    "id": n[0],
                    "note": n[1],
                }
                for n in notes
            ],
        }

    if name == "save_memory":
        try:
            import Doshie_memory
        except ImportError:
            import yoshi_memory as Doshie_memory

        fact = str(arguments.get("fact") or "").strip()
        if not fact:
            raise ValueError("Memory fact text cannot be empty.")
        category = str(arguments.get("category") or "General").strip()
        scope = str(arguments.get("scope") or "private").strip().lower()
        if scope not in ("private", "shared"):
            scope = "private"
        result = Doshie_memory.add_memory(fact, category=category, profile=actor_profile or "Hermes", scope=scope)
        return {"status": "saved", "detail": result}

    if name == "create_task":
        try:
            import Doshie_memory
        except ImportError:
            import yoshi_memory as Doshie_memory

        task_text = str(arguments.get("task") or "").strip()
        if not task_text:
            raise ValueError("Task description cannot be empty.")
        priority = str(arguments.get("priority") or "Normal").strip()
        due_date = str(arguments.get("due_date") or "").strip()
        result = Doshie_memory.add_task(task_text, priority=priority, due_date=due_date)
        return {"status": "created", "detail": result}

    if name == "add_note":
        try:
            import Doshie_memory
        except ImportError:
            import yoshi_memory as Doshie_memory

        note_text = str(arguments.get("note") or "").strip()
        if not note_text:
            raise ValueError("Note content cannot be empty.")
        result = Doshie_memory.add_note(note_text)
        return {"status": "added", "detail": result}

    if name == "inspect_hardware":
        import doshie_hardware
        comp = str(arguments.get("component") or "summary").lower()
        if comp in ("all", "full"):
            return doshie_hardware.inspect_all()
        elif comp == "cpu":
            return doshie_hardware.inspect_cpu()
        elif comp == "gpu":
            return doshie_hardware.inspect_gpu()
        elif comp in ("ram", "memory"):
            return doshie_hardware.inspect_memory()
        elif comp in ("disk", "storage"):
            return doshie_hardware.inspect_storage()
        elif comp in ("thermals", "temp", "thermal"):
            return doshie_hardware.inspect_thermals()
        elif comp in ("motherboard", "board", "dmi"):
            return doshie_hardware.inspect_motherboard()
        elif comp in ("net", "network"):
            return doshie_hardware.inspect_network()
        elif comp == "pci":
            return doshie_hardware.inspect_pci()
        elif comp == "usb":
            return doshie_hardware.inspect_usb()
        else:
            return doshie_hardware.inspect_all()

    if name == "propose_hardware_change":
        import doshie_hardware
        target = str(arguments.get("target") or "").strip()
        value = str(arguments.get("value") or "").strip()
        reason = str(arguments.get("reason") or "Agent proposal").strip()
        return doshie_hardware.propose_change(target, value, reason=reason)

    if name == "execute_hardware_change":
        import doshie_hardware
        target = str(arguments.get("target") or "").strip()
        value = str(arguments.get("value") or "").strip()
        confirmed = bool(arguments.get("confirmed", False))
        reason = str(arguments.get("reason") or "Agent request with confirmation").strip()
        return doshie_hardware.execute_change(target, value, confirmed=confirmed, actor="agent", reason=reason)

    if name == "get_hardware_governance":
        import doshie_hardware
        return doshie_hardware.load_governance()

    if name == "render_3d_model":
        import subprocess
        from pathlib import Path
        input_path = str(arguments.get("input_path") or "").strip()
        output_path = str(arguments.get("output_path") or "").strip()
        samples = int(arguments.get("samples") or 128)

        if not input_path or not os.path.isfile(input_path):
            return {"success": False, "error": f"3D model file not found: {input_path}"}

        blender_bin = "/home/doshie/.local/share/blender-4.3.2-linux-x64/blender"
        render_script = "/home/doshie/Doshie/doshie_render_4k.py"
        if not output_path:
            output_path = str(Path(input_path).with_suffix(".png"))

        cmd = [blender_bin, "-b", "-P", render_script, "--", "--input", input_path, "--output", output_path, "--samples", str(samples)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            return {
                "success": res.returncode == 0,
                "output_image": output_path,
                "message": f"Rendered 4K image saved to {output_path}" if res.returncode == 0 else f"Render failed: {res.stderr[-300:]}"
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

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
        "run python diagnostics",
        "hardware",
        "inspect hardware",
        "cpu governor",
        "gpu power",
        "thermals",
        "motherboard",
        "pcie",
        "change governor",
        "hardware setting",
        "doshie hw",
        "render 3d",
        "3d render",
        "render in 4k",
        "4k render",
        "render model",
        "render mesh",
    )

    return any(trigger in latest for trigger in triggers)

def _vision_chat(
    url, model, messages, images, timeout=180, request_id=""
):
    parts = urllib.parse.urlsplit(url)
    native_url = urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, "/api/chat", "", "")
    )
    tags_url = urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, "/api/tags", "", "")
    )

    # Extract user's clean prompt (omitting bulky system prompts that overflow small vision context windows)
    user_prompt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_prompt = str(m.get("content") or "").strip()
            break
    clean_user_prompt = re.sub(r"USER ATTACHMENTS:.*", "", user_prompt, flags=re.DOTALL).strip()
    if not clean_user_prompt:
        clean_user_prompt = "Describe what is shown in this image and answer any questions."

    # Discover which models are actually installed in Ollama and support vision
    installed_vision_models = []
    try:
        req_tags = urllib.request.Request(tags_url, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_tags, timeout=3) as resp:
            tags_data = json.loads(resp.read().decode("utf-8"))
            for m in tags_data.get("models", []):
                m_name = m.get("name", "")
                m_caps = m.get("capabilities", [])
                if "vision" in m_caps or any(k in m_name.lower() for k in ("moondream", "llava", "vision", "vl", "qwen3.5")):
                    installed_vision_models.append(m_name)
    except Exception:
        pass

    # Build prioritized candidate list:
    # 1. Requested model if it supports vision natively (e.g. qwen3.5:9b)
    # 2. Other installed vision models (excluding tiny OCR fallbacks)
    # 3. moondream as a fallback OCR model
    candidates = []
    if model:
        is_model_vision = (
            any(model == vm or model.split(":")[0] == vm.split(":")[0] for vm in installed_vision_models)
            or any(k in model.lower() for k in ("vision", "vl", "moondream", "llava", "minicpm", "qwen3.5"))
        )
        if is_model_vision and model not in candidates:
            candidates.append(model)

    for vmodel in installed_vision_models:
        if "moondream" not in vmodel.lower() and vmodel not in candidates:
            candidates.append(vmodel)

    for preferred in ("moondream", "moondream:latest"):
        if preferred in installed_vision_models and preferred not in candidates:
            candidates.append(preferred)

    if not candidates:
        candidates = ["moondream", "moondream:latest"]

    vision_description = None
    vision_timeout = max(min(timeout, 90), 45)
    used_ocr_fallback = False

    for candidate_model in candidates:
        is_moondream = "moondream" in candidate_model.lower()
        if is_moondream:
            used_ocr_fallback = True
            req_prompt = "Describe this image in detail and transcribe any visible text, handwriting, or problems."
        else:
            used_ocr_fallback = False
            req_prompt = clean_user_prompt

        req_messages = [
            {"role": "user", "content": req_prompt, "images": list(images)}
        ]

        payload = json.dumps({
            "model": candidate_model,
            "messages": req_messages,
            "stream": False,
            "think": False,
            "keep_alive": os.environ.get("YOSHI_KEEP_ALIVE", "5m"),
            "options": {
                "temperature": 0.2,
                "num_predict": 1000,
                "num_ctx": 4096,
            },
        }).encode("utf-8")
        request = urllib.request.Request(
            native_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            response = urllib.request.urlopen(request, timeout=vision_timeout)
        except Exception:
            continue

        key = str(request_id or "").strip()
        if key:
            with _ACTIVE_RESPONSES_LOCK:
                _ACTIVE_RESPONSES[key] = response
        try:
            data = json.loads(response.read().decode("utf-8"))
        except Exception:
            continue
        finally:
            if key:
                with _ACTIVE_RESPONSES_LOCK:
                    if _ACTIVE_RESPONSES.get(key) is response:
                        _ACTIVE_RESPONSES.pop(key, None)
            response.close()

        model_message = data.get("message") or {}
        visible = str(model_message.get("content") or "").strip()
        if visible:
            vision_description = visible
            break
        fallback = str(model_message.get("thinking") or "")
        fallback = re.sub(r"</?think>", "", fallback).strip()
        if fallback:
            vision_description = fallback
            break

    if not vision_description:
        return "I received the image, but the local vision model returned no description."

    # If we used a native vision model directly (e.g. qwen3.5:9b), it already answered
    # the user's question directly with full visual grounding.
    if not used_ocr_fallback:
        return vision_description

    # Only if we had to fall back to an OCR-only model (like moondream), synthesize
    # with the primary model if it's capable
    is_primary_agent = model and not any(k in model.lower() for k in ("moondream", "vision", "vl"))
    if is_primary_agent:
        try:
            synth_messages = [
                {
                    "role": "system",
                    "content": "You are Hermes AI (Doshie's specialist assistant). The user has shared an image/screenshot with you. Answer their question directly, thoroughly, and helpfully based on the visual context."
                },
                {
                    "role": "user",
                    "content": f"[Visual Inspection of User's Attachment: {vision_description}]\n\nUser Question: {clean_user_prompt}"
                }
            ]
            synth_payload = json.dumps({
                "model": model,
                "messages": synth_messages,
                "stream": False,
                "think": False,
                "keep_alive": os.environ.get("YOSHI_KEEP_ALIVE", "5m"),
                "options": {
                    "temperature": 0.35,
                    "num_predict": 800,
                },
            }).encode("utf-8")
            synth_req = urllib.request.Request(
                native_url,
                data=synth_payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(synth_req, timeout=60) as synth_resp:
                synth_data = json.loads(synth_resp.read().decode("utf-8"))
                synth_reply = str(synth_data.get("message", {}).get("content") or "").strip()
                if synth_reply:
                    return synth_reply
        except Exception:
            pass

    return vision_description


def chat(
    url, model, messages, timeout=180, request_id="",
    actor_profile="", can_propose_changes=False, images=None,
    agent_capabilities=None, brain_mode="auto"
):
    if images:
        return _vision_chat(
            url, model, messages, images,
            timeout=timeout, request_id=request_id
        )

    working_messages = list(messages)

    model_str = str(model or "").lower()
    is_reasoning_model = (
        any(k in model_str for k in ("r1", "deepseek", "think"))
        or str(brain_mode or "").lower() in ("advanced", "heavyweight", "genius")
    )

    accumulated_thoughts = []

    for _ in range(5):
        request_body = {
            "model": model,
            "messages": working_messages,
            "temperature": 0.6 if is_reasoning_model else 0.35,
            "max_tokens": 2048,
            "keep_alive": os.environ.get("YOSHI_KEEP_ALIVE", "5m")
        }

        if is_reasoning_model:
            request_body["think"] = True
        else:
            request_body["think"] = False
            request_body["reasoning_effort"] = "none"

        if agent_capabilities is not None:
            allowed_names = set()
            for cap in agent_capabilities:
                for tool_name in CAPABILITY_TOOL_MAP.get(cap, []):
                    allowed_names.add(tool_name)
            allowed_tools = [t for t in TOOLS if t["function"]["name"] in allowed_names]
        else:
            inside_hermes = any(
                message.get("role") == "system"
                and "You are Hermes AI in your dedicated workspace." in str(
                    message.get("content") or ""
                )
                for message in working_messages
            )

            project_tools_needed = inside_hermes or needs_project_tools(working_messages)
            
            allowed_tools = []
            for tool in TOOLS:
                name = tool["function"]["name"]
                if name == "web_search":
                    allowed_tools.append(tool)
                elif project_tools_needed:
                    if inside_hermes and name == "consult_hermes_ai":
                        continue
                    allowed_tools.append(tool)

        if allowed_tools:
            request_body["tools"] = allowed_tools

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

        reasoning = (
            message.get("reasoning_content")
            or message.get("reasoning")
            or message.get("thinking")
            or ""
        )
        if reasoning and reasoning.strip():
            accumulated_thoughts.append(reasoning.strip())

        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            final_content = str(message.get("content") or "").strip()
            if not final_content and accumulated_thoughts:
                final_content = accumulated_thoughts[-1]
            if accumulated_thoughts and "<think>" not in final_content:
                thoughts_text = "\n\n".join(accumulated_thoughts).strip()
                if thoughts_text:
                    final_content = f"<think>\n{thoughts_text}\n</think>\n\n{final_content}"
            return final_content

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


def helper_activity_snapshot():
    """Return a live snapshot of registered specialist helper agents."""
    try:
        import Doshie_agents
        agents = Doshie_agents.list_agents()
    except Exception:
        agents = []
    snapshot = {}
    for agent in agents:
        name = str(agent.get("name") or "").strip()
        if not name:
            continue
        snapshot[name] = {
            "name": name,
            "state": "idle",
            "category": str(agent.get("model_mode") or "auto"),
            "enabled": bool(agent.get("enabled", True)),
        }
    return snapshot

