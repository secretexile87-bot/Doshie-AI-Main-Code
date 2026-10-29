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
                "Inspect computer hardware subsystems (CPU, GPU, RAM, storage, thermals, motherboard, network, PCI, USB, or complete summary). "
                "Can inspect the local Acer Nitro or query specific remote machines in Hermes's fleet."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "description": "Subsystem to inspect: 'all', 'summary', 'cpu', 'gpu', 'ram', 'disk', 'thermals', 'motherboard', 'network', 'pci', or 'usb'.",
                        "enum": ["all", "summary", "cpu", "gpu", "ram", "disk", "thermals", "motherboard", "network", "pci", "usb"]
                    },
                    "host": {
                        "type": "string",
                        "description": "Target computer to inspect: 'localhost' (default, Acer Nitro), 'fleet' (all computers), or a specific host name (e.g., 'DuranCyberPwrPC', 'vultr')."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_fleet",
            "description": (
                "Inspect all computers and devices across Hermes's personal mesh network (Tailscale fleet). "
                "Discovers online Windows PCs, Linux servers, laptops, and mobile devices with IP addresses, OS, and network latency."
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
    },
    {
        "type": "function",
        "function": {
            "name": "python_calculator",
            "description": (
                "Execute verified Python code or mathematical expressions for exact calculations, statistics, date math, or data processing. "
                "Always use this when precise numbers, complex arithmetic, formulas, unit conversions, or algorithmic steps are needed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python expression (e.g. 'math.sqrt(54321)') or script to execute."
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wikipedia_search",
            "description": (
                "Search and retrieve authoritative summaries and verified knowledge from Wikipedia about history, geography, people, biology, and culture. "
                "CRITICAL: NEVER use this tool when the user asks you to make, build, create, or code an application, script, tool, or calculator; write the code directly with write_file instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Topic, entity, concept, or search term to look up on Wikipedia."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Execute a shell / bash command directly on the host Linux workstation (e.g. systemctl status, journalctl, git, python, inspect files, check network or services). "
                "Use this to inspect, diagnose, fix, test, and control the PC and services."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact shell command to execute."
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Optional working directory (defaults to /home/doshie/Doshie)."
                    },
                    "host": {
                        "type": "string",
                        "description": "Target host: 'localhost' (default, Acer Nitro) or any remote fleet computer (e.g. 'vultr', 'DuranCyberPwrPC', or IP)."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "view_file",
            "description": "View lines from any file on the local filesystem or on any remote fleet computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file."
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "1-based starting line number (default: 1)."
                    },
                    "line_count": {
                        "type": "integer",
                        "description": "Number of lines to read (default: 150)."
                    },
                    "host": {
                        "type": "string",
                        "description": "Optional target host: 'localhost' (default) or any remote fleet machine (e.g. 'vultr', 'DuranCyberPwrPC')."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_file_content",
            "description": "Perform an exact surgical find-and-replace edit in an existing file locally or on any remote fleet computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit."
                    },
                    "target_content": {
                        "type": "string",
                        "description": "The exact existing text chunk to find and replace."
                    },
                    "replacement_content": {
                        "type": "string",
                        "description": "The replacement text to put in place."
                    },
                    "host": {
                        "type": "string",
                        "description": "Optional target host: 'localhost' (default) or any remote fleet machine (e.g. 'vultr', 'DuranCyberPwrPC')."
                    }
                },
                "required": ["path", "target_content", "replacement_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write complete files or source code directly to disk locally or to any remote fleet computer. "
                "CRITICAL: ALWAYS use this tool immediately when asked to make, build, create, or code any application, GUI app, script, program, calculator, tool, or game."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to create or overwrite."
                    },
                    "content": {
                        "type": "string",
                        "description": "The full code or text content to write."
                    },
                    "host": {
                        "type": "string",
                        "description": "Optional target host: 'localhost' (default) or any remote fleet machine (e.g. 'vultr', 'DuranCyberPwrPC')."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": (
                "Delete a file or script directly from disk locally or on any remote fleet computer. "
                "CRITICAL: ALWAYS use this tool immediately when asked to delete, remove, or clean up an existing file or script."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to delete (e.g. '/home/doshie/Desktop/calculator.py')."
                    },
                    "host": {
                        "type": "string",
                        "description": "Optional target host: 'localhost' (default) or any remote fleet machine (e.g. 'vultr', 'DuranCyberPwrPC')."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remote_run_command",
            "description": "Execute shell or PowerShell commands remotely on any machine in Hermes's fleet (e.g. 'vultr', 'DuranCyberPwrPC').",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Target computer name or IP (e.g. 'vultr', 'DuranCyberPwrPC', '100.104.3.15')."
                    },
                    "command": {
                        "type": "string",
                        "description": "The command or script to execute on the remote machine."
                    }
                },
                "required": ["host", "command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remote_view_file",
            "description": "Read file contents or source code lines from any remote computer in the fleet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Target computer name or IP (e.g. 'vultr', 'DuranCyberPwrPC')."
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to the file on the remote machine."
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "1-based starting line number (default: 1)."
                    },
                    "line_count": {
                        "type": "integer",
                        "description": "Number of lines to read (default: 150)."
                    }
                },
                "required": ["host", "path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remote_write_file",
            "description": "Write or deploy source code / files directly to any remote computer in the fleet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Target computer name or IP (e.g. 'vultr', 'DuranCyberPwrPC')."
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to the file on the remote computer."
                    },
                    "content": {
                        "type": "string",
                        "description": "The full code or text content to deploy."
                    }
                },
                "required": ["host", "path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remote_replace_file_content",
            "description": "Perform an exact surgical code edit in an existing file on a remote computer in the fleet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Target computer name or IP (e.g. 'vultr', 'DuranCyberPwrPC')."
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to the file on the remote machine."
                    },
                    "target_content": {
                        "type": "string",
                        "description": "The exact existing code block to find and replace."
                    },
                    "replacement_content": {
                        "type": "string",
                        "description": "The replacement code to put in place."
                    }
                },
                "required": ["host", "path", "target_content", "replacement_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remote_delete_file",
            "description": "Delete a file or script directly on any remote computer in the fleet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Target computer name or IP (e.g. 'vultr', 'DuranCyberPwrPC')."
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to the file to delete on the remote machine."
                    }
                },
                "required": ["host", "path"]
            }
        }
    },
    # -----------------------------------------------------------------------
    # Remote Technician Tools
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "tech_health_report",
            "description": (
                "Run a full remote health diagnostic on any computer in the fleet — "
                "family (Mom, Dad, Hermes) or a client PC. Checks disk, CPU/RAM, services, "
                "internet, and recent error logs in one call."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target computer: 'mom', 'dad', 'hermes', a Tailscale hostname, or IP."
                    }
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tech_check_disk",
            "description": "Check disk space usage on a remote computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target computer name or alias."}
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tech_check_cpu_ram",
            "description": "Check CPU and RAM usage on a remote computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target computer name or alias."}
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tech_check_internet",
            "description": "Test internet connectivity (ping, DNS, HTTP) on a remote computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target computer name or alias."}
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tech_list_services",
            "description": "List running and failed services on a remote computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target computer name or alias."}
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tech_tail_logs",
            "description": "Retrieve recent system error log entries from a remote computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target computer name or alias."},
                    "lines": {"type": "integer", "description": "Number of log lines to fetch (default 50)."}
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tech_restart_service",
            "description": "Restart a specific service on a remote computer. Always confirm with user before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target computer name or alias."},
                    "service_name": {"type": "string", "description": "Service name to restart (e.g. 'nginx', 'Spooler')."}
                },
                "required": ["target", "service_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tech_run_command",
            "description": "Run a custom shell or PowerShell command on a remote computer for technician tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target computer name or alias."},
                    "command": {"type": "string", "description": "The command to execute."},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)."}
                },
                "required": ["target", "command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tech_list_fleet",
            "description": "List all known computers in the Doshie fleet (family + clients) with their online status.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tech_list_updates",
            "description": "Check for pending OS updates on a remote computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target computer name or alias."}
                },
                "required": ["target"]
            }
        }
    },
    # -----------------------------------------------------------------------
    # Business / Client Management Tools
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "biz_add_client",
            "description": "Add a new paying client to the business database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Client full name."},
                    "phone": {"type": "string", "description": "Client phone number."},
                    "email": {"type": "string", "description": "Client email address."},
                    "address": {"type": "string", "description": "Client address."},
                    "notes": {"type": "string", "description": "Any additional notes about the client."},
                    "consent": {"type": "boolean", "description": "Whether the client has given consent for remote access."},
                    "consent_method": {"type": "string", "description": "How consent was given: 'verbal', 'text', 'email', 'written'."}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "biz_search_clients",
            "description": "Search for clients in the business database by name, phone, or email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term (name, phone, or email)."},
                    "limit": {"type": "integer", "description": "Max results to return (default 20)."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "biz_check_consent",
            "description": "Verify that a client has given authorization before connecting to their computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_id": {"type": "string", "description": "Client ID to check consent for."}
                },
                "required": ["client_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "biz_add_device",
            "description": "Register a client's computer/device in the business database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_id": {"type": "string", "description": "Client ID to add the device to."},
                    "label": {"type": "string", "description": "Device label (e.g. 'Living room PC', 'Work laptop')."},
                    "os": {"type": "string", "description": "Operating system: 'windows', 'linux', 'mac'."},
                    "hostname": {"type": "string", "description": "Tailscale hostname or network name."},
                    "tailscale_ip": {"type": "string", "description": "Tailscale IP address if known."},
                    "node_installed": {"type": "boolean", "description": "Whether doshie_node.py is installed on this device."}
                },
                "required": ["client_id", "label"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "biz_open_job",
            "description": "Open a new job ticket for a client tech support session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_id": {"type": "string", "description": "Client ID for this job."},
                    "title": {"type": "string", "description": "Short job title (e.g. 'Virus removal', 'Slow PC cleanup')."},
                    "description": {"type": "string", "description": "Detailed description of the problem."},
                    "hourly_rate": {"type": "number", "description": "Hourly rate in USD (default $60)."},
                    "flat_fee": {"type": "number", "description": "Flat fee instead of/in addition to hourly rate."}
                },
                "required": ["client_id", "title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "biz_log_job_action",
            "description": "Add a log entry to a job ticket describing what was done.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID to log the action against."},
                    "entry": {"type": "string", "description": "Description of the action taken."}
                },
                "required": ["job_id", "entry"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "biz_close_job",
            "description": "Close a job ticket and calculate the final invoice total.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID to close."},
                    "hours": {"type": "number", "description": "Total hours worked."},
                    "parts_cost": {"type": "number", "description": "Cost of any parts or materials used."},
                    "notes": {"type": "string", "description": "Final notes about the completed work."}
                },
                "required": ["job_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "biz_generate_invoice",
            "description": "Generate a professional HTML invoice for a completed job.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID to invoice."}
                },
                "required": ["job_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "biz_mark_paid",
            "description": "Mark a job as paid.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID to mark as paid."}
                },
                "required": ["job_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "biz_list_jobs",
            "description": "List job tickets, optionally filtered by client or status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_id": {"type": "string", "description": "Filter by client ID (optional)."},
                    "status": {"type": "string", "description": "Filter by status: 'open', 'in_progress', 'closed'."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "biz_revenue_report",
            "description": "Generate a revenue report summarizing income and jobs for a time period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "Time period: 'week', 'month', 'year', or 'all'.",
                        "enum": ["week", "month", "year", "all"]
                    }
                }
            }
        }
    },
    # -----------------------------------------------------------------------
    # WhatsApp Tools
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "whatsapp_send",
            "description": "Send a WhatsApp message to a contact or phone number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Phone number with country code (e.g. '19155551234') or contact name/ID."},
                    "message": {"type": "string", "description": "The text message to send."}
                },
                "required": ["to", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "whatsapp_status",
            "description": "Check whether Doshie's WhatsApp bridge is connected, scanning QR, or disconnected.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "whatsapp_messages",
            "description": "Read recent incoming WhatsApp messages received by Doshie.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of recent messages to fetch (default 20)."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "whatsapp_contacts",
            "description": "List WhatsApp contacts available on the connected account.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

CAPABILITY_TOOL_MAP = {
    "web_research": ["web_search", "wikipedia_search"],
    "math_calculation": ["python_calculator"],
    "encyclopedia": ["wikipedia_search"],
    "project_read": ["view_file", "list_code_files", "read_code_file", "search_code", "remote_view_file"],
    "code_proposals": [
        "run_command", "view_file", "replace_file_content", "write_file", "delete_file",
        "remote_run_command", "remote_view_file", "remote_write_file", "remote_replace_file_content", "remote_delete_file",
        "propose_code_edit", "propose_new_file", "request_python_diagnostics"
    ],
    "service_health": ["check_service_health", "inspect_hardware", "inspect_fleet", "run_command", "remote_run_command"],
    "hardware_management": ["inspect_hardware", "inspect_fleet", "propose_hardware_change", "execute_hardware_change", "get_hardware_governance", "run_command", "remote_run_command"],
    "memory_read": ["search_memories", "get_tasks_and_notes"],
    "memory_write": ["save_memory", "create_task", "add_note"],
    "3d_rendering": ["render_3d_model"],
    "remote_tech": [
        "tech_health_report", "tech_check_disk", "tech_check_cpu_ram",
        "tech_check_internet", "tech_list_services", "tech_tail_logs",
        "tech_restart_service", "tech_run_command", "tech_list_fleet", "tech_list_updates",
        "inspect_fleet", "remote_run_command"
    ],
    "client_management": [
        "biz_add_client", "biz_search_clients", "biz_check_consent",
        "biz_add_device", "biz_list_jobs"
    ],
    "billing": [
        "biz_open_job", "biz_log_job_action", "biz_close_job",
        "biz_generate_invoice", "biz_mark_paid", "biz_list_jobs", "biz_revenue_report"
    ],
    "whatsapp": [
        "whatsapp_send", "whatsapp_status", "whatsapp_messages", "whatsapp_contacts"
    ],
}



def execute_tool(name, arguments, actor_profile="", can_propose_changes=False):
    if name == "web_search":
        import Doshie_search
        import Doshie_profile_preferences
        is_under_18 = Doshie_profile_preferences.is_profile_under_18(actor_profile)
        return Doshie_search.web_search(arguments.get("query"), is_under_18=is_under_18)

    if name == "python_calculator":
        import subprocess
        import sys
        code = str(arguments.get("code") or arguments.get("expression") or "").strip()
        if not code:
            raise ValueError("No calculation code provided.")
        wrapped = (
            "import math, sys, json, datetime, statistics, random\n"
            "code_str = " + repr(code) + "\n"
            "try:\n"
            "    res = eval(code_str)\n"
            "    if res is not None:\n"
            "        print(res)\n"
            "except SyntaxError:\n"
            "    exec(code_str)\n"
        )
        try:
            proc = subprocess.run(
                [sys.executable, "-c", wrapped],
                capture_output=True,
                text=True,
                timeout=5
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": proc.returncode,
                "result": stdout if stdout else (stderr if proc.returncode != 0 else "Execution completed.")
            }
        except subprocess.TimeoutExpired:
            return {"error": "Execution timed out after 5 seconds."}
        except Exception as exc:
            return {"error": str(exc)}

    if name == "wikipedia_search":
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("No search query provided.")
        headers = {"User-Agent": "DoshieAssistant/1.0 (contact@doshie.local)"}
        try:
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&srlimit=3"
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                sdata = json.loads(resp.read().decode("utf-8"))
            results = sdata.get("query", {}).get("search", [])
            if not results:
                return {"found": False, "message": f"No Wikipedia article found for '{query}'."}
            best_title = results[0]["title"]
            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(best_title)}"
            req_sum = urllib.request.Request(summary_url, headers=headers)
            with urllib.request.urlopen(req_sum, timeout=5) as resp:
                sum_data = json.loads(resp.read().decode("utf-8"))
            return {
                "found": True,
                "title": sum_data.get("title", best_title),
                "description": sum_data.get("description", ""),
                "summary": sum_data.get("extract", ""),
                "url": sum_data.get("content_urls", {}).get("desktop", {}).get("page", "")
            }
        except Exception as exc:
            return {"found": False, "error": str(exc)}

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
        target_host = str(arguments.get("host") or "").strip()
        if target_host and target_host.lower() not in ("localhost", "127.0.0.1", "acer-nitro", "local", "nitro"):
            return doshie_hardware.inspect_host(target_host)

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
        elif comp in ("fleet", "network_fleet", "nodes"):
            return doshie_hardware.inspect_fleet()
        else:
            return doshie_hardware.inspect_all()

    if name == "inspect_fleet":
        import doshie_hardware
        return doshie_hardware.inspect_fleet()

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

    if name in ("run_command", "remote_run_command"):
        import subprocess
        import time
        from pathlib import Path
        import doshie_remote

        cmd = str(arguments.get("command") or arguments.get("cmd") or "").strip()
        if not cmd:
            raise ValueError("No command provided.")
        host = str(arguments.get("host") or "").strip()
        if host and host.lower() not in ("localhost", "127.0.0.1", "acer-nitro", "local", "nitro"):
            return doshie_remote.remote_run_command(host, cmd)

        cwd = str(arguments.get("cwd") or "").strip()
        work_dir = Path(cwd).expanduser().resolve() if cwd else Path("/home/doshie/Doshie")
        if not work_dir.exists():
            work_dir = Path("/home/doshie/Doshie")
        destructive = [
            "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev/zero",
            ":(){ :|:& };:", "chmod -R 777 /", "> /dev/sda"
        ]
        if any(d in cmd for d in destructive):
            raise ValueError("Command blocked by safety guardrails.")
        start_time = time.time()
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=60
            )
            duration = round(time.time() - start_time, 2)
            stdout = proc.stdout[-15000:] if len(proc.stdout) > 15000 else proc.stdout
            stderr = proc.stderr[-15000:] if len(proc.stderr) > 15000 else proc.stderr
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "duration_seconds": duration,
                "cwd": str(work_dir),
                "command": cmd,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "exit_code": -1,
                "error": "Command timed out after 60 seconds.",
                "command": cmd,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "command": cmd}

    if name in ("view_file", "remote_view_file"):
        from pathlib import Path
        import doshie_remote

        path_str = str(arguments.get("path") or arguments.get("file_path") or "").strip()
        if not path_str:
            raise ValueError("No file path provided.")
        host = str(arguments.get("host") or "").strip()
        start_line = max(int(arguments.get("start_line") or 1), 1)
        line_count = min(max(int(arguments.get("line_count") or 150), 1), 500)
        if host and host.lower() not in ("localhost", "127.0.0.1", "acer-nitro", "local", "nitro"):
            return doshie_remote.remote_view_file(host, path_str, start_line, line_count)

        file_path = Path(path_str).expanduser().resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a regular file: {file_path}")
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        total_lines = len(lines)
        end_line = min(start_line + line_count - 1, total_lines)
        slice_lines = lines[start_line - 1:end_line]
        numbered_lines = "".join(f"{i + start_line}: {line}" for i, line in enumerate(slice_lines))
        return {
            "path": str(file_path),
            "start_line": start_line,
            "end_line": end_line,
            "total_lines": total_lines,
            "content": numbered_lines,
        }

    if name in ("replace_file_content", "remote_replace_file_content"):
        from pathlib import Path
        import doshie_remote

        path_str = str(arguments.get("path") or arguments.get("file_path") or "").strip()
        target_content = str(arguments.get("target_content") or "")
        replacement_content = str(arguments.get("replacement_content") or "")
        if not path_str:
            raise ValueError("No file path provided.")
        if not target_content:
            raise ValueError("No target content provided to replace.")
        host = str(arguments.get("host") or "").strip()
        if host and host.lower() not in ("localhost", "127.0.0.1", "acer-nitro", "local", "nitro"):
            return doshie_remote.remote_replace_file_content(host, path_str, target_content, replacement_content)

        file_path = Path(path_str).expanduser().resolve()
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        occurrences = content.count(target_content)
        if occurrences == 0:
            raise ValueError(f"Target content not found in {file_path}.")
        if occurrences > 1:
            raise ValueError(f"Target content occurs {occurrences} times in {file_path}. Please provide a more unique target chunk.")
        new_content = content.replace(target_content, replacement_content, 1)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return {
            "ok": True,
            "path": str(file_path),
            "message": f"Successfully replaced target content in {file_path}.",
        }

    if name in ("write_file", "remote_write_file"):
        from pathlib import Path
        import doshie_remote

        path_str = str(arguments.get("path") or arguments.get("file_path") or "").strip()
        content = str(arguments.get("content") or "")
        overwrite = bool(arguments.get("overwrite", True))
        if not path_str:
            raise ValueError("No file path provided.")
        host = str(arguments.get("host") or "").strip()
        if host and host.lower() not in ("localhost", "127.0.0.1", "acer-nitro", "local", "nitro"):
            return doshie_remote.remote_write_file(host, path_str, content, overwrite)

        file_path = Path(path_str).expanduser().resolve()
        if file_path.exists() and not overwrite:
            raise FileExistsError(f"File already exists and overwrite is False: {file_path}")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {
            "ok": True,
            "path": str(file_path),
            "bytes_written": len(content.encode("utf-8")),
            "message": f"Successfully wrote {len(content.encode('utf-8'))} bytes to {file_path}."
        }

    if name in ("delete_file", "remote_delete_file"):
        from pathlib import Path
        import doshie_remote

        path_str = str(arguments.get("path") or arguments.get("file_path") or "").strip()
        if not path_str:
            raise ValueError("No file path provided.")
        host = str(arguments.get("host") or "").strip()
        if host and host.lower() not in ("localhost", "127.0.0.1", "acer-nitro", "local", "nitro"):
            return doshie_remote.remote_delete_file(host, path_str)

        file_path = Path(path_str).expanduser().resolve()
        if not file_path.exists():
            return {
                "ok": True,
                "path": str(file_path),
                "message": f"File {file_path} already does not exist."
            }
        if file_path.is_dir():
            file_path.rmdir()
        else:
            file_path.unlink()
        return {
            "ok": True,
            "path": str(file_path),
            "message": f"Successfully deleted {file_path}."
        }

    # -----------------------------------------------------------------------
    # Remote Technician Tool Handlers
    # -----------------------------------------------------------------------
    if name == "tech_health_report":
        import doshie_gcloud_tech
        return doshie_gcloud_tech.full_health_report(arguments.get("target", ""))

    if name == "tech_check_disk":
        import doshie_gcloud_tech
        return doshie_gcloud_tech.check_disk_space(arguments.get("target", ""))

    if name == "tech_check_cpu_ram":
        import doshie_gcloud_tech
        return doshie_gcloud_tech.check_cpu_ram(arguments.get("target", ""))

    if name == "tech_check_internet":
        import doshie_gcloud_tech
        return doshie_gcloud_tech.check_internet(arguments.get("target", ""))

    if name == "tech_list_services":
        import doshie_gcloud_tech
        return doshie_gcloud_tech.list_running_services(arguments.get("target", ""))

    if name == "tech_tail_logs":
        import doshie_gcloud_tech
        return doshie_gcloud_tech.tail_system_logs(
            arguments.get("target", ""),
            lines=int(arguments.get("lines") or 50),
        )

    if name == "tech_restart_service":
        import doshie_gcloud_tech
        return doshie_gcloud_tech.restart_service(
            arguments.get("target", ""),
            arguments.get("service_name", ""),
        )

    if name == "tech_run_command":
        import doshie_gcloud_tech
        return doshie_gcloud_tech.run_tech_command(
            arguments.get("target", ""),
            arguments.get("command", ""),
            timeout=int(arguments.get("timeout") or 30),
        )

    if name == "tech_list_fleet":
        import doshie_gcloud_tech
        return doshie_gcloud_tech.list_fleet()

    if name == "tech_list_updates":
        import doshie_gcloud_tech
        return doshie_gcloud_tech.list_pending_updates(arguments.get("target", ""))

    # -----------------------------------------------------------------------
    # Business / Client Management Tool Handlers
    # -----------------------------------------------------------------------
    if name == "biz_add_client":
        import doshie_clients
        return doshie_clients.add_client(
            name=arguments.get("name", ""),
            phone=arguments.get("phone", ""),
            email=arguments.get("email", ""),
            address=arguments.get("address", ""),
            notes=arguments.get("notes", ""),
            consent=bool(arguments.get("consent", False)),
            consent_method=arguments.get("consent_method", "verbal"),
        )

    if name == "biz_search_clients":
        import doshie_clients
        return doshie_clients.search_clients(
            query=arguments.get("query", ""),
            limit=int(arguments.get("limit") or 20),
        )

    if name == "biz_check_consent":
        import doshie_clients
        return doshie_clients.check_client_consent(arguments.get("client_id", ""))

    if name == "biz_add_device":
        import doshie_clients
        return doshie_clients.add_device(
            client_id=arguments.get("client_id", ""),
            label=arguments.get("label", ""),
            os=arguments.get("os", "windows"),
            hostname=arguments.get("hostname", ""),
            tailscale_ip=arguments.get("tailscale_ip", ""),
            node_installed=bool(arguments.get("node_installed", False)),
        )

    if name == "biz_open_job":
        import doshie_clients
        return doshie_clients.open_job(
            client_id=arguments.get("client_id", ""),
            title=arguments.get("title", ""),
            description=arguments.get("description", ""),
            hourly_rate=float(arguments.get("hourly_rate") or 60),
            flat_fee=float(arguments.get("flat_fee") or 0),
        )

    if name == "biz_log_job_action":
        import doshie_clients
        return doshie_clients.log_job_action(
            job_id=arguments.get("job_id", ""),
            entry=arguments.get("entry", ""),
        )

    if name == "biz_close_job":
        import doshie_clients
        return doshie_clients.close_job(
            job_id=arguments.get("job_id", ""),
            hours=float(arguments.get("hours") or 0),
            parts_cost=float(arguments.get("parts_cost") or 0),
            notes=arguments.get("notes", ""),
        )

    if name == "biz_generate_invoice":
        import doshie_clients
        return doshie_clients.generate_invoice(arguments.get("job_id", ""))

    if name == "biz_mark_paid":
        import doshie_clients
        return doshie_clients.mark_job_paid(arguments.get("job_id", ""))

    if name == "biz_list_jobs":
        import doshie_clients
        return doshie_clients.list_jobs(
            client_id=arguments.get("client_id", ""),
            status=arguments.get("status", ""),
        )

    if name == "biz_revenue_report":
        import doshie_clients
        return doshie_clients.revenue_report(
            period=arguments.get("period", "month")
        )

    # -----------------------------------------------------------------------
    # WhatsApp Tool Handlers
    # -----------------------------------------------------------------------
    if name == "whatsapp_send":
        import doshie_whatsapp
        return doshie_whatsapp.send_message(
            to=arguments.get("to", ""),
            message=arguments.get("message", ""),
        )

    if name == "whatsapp_status":
        import doshie_whatsapp
        return doshie_whatsapp.get_status()

    if name == "whatsapp_messages":
        import doshie_whatsapp
        return doshie_whatsapp.get_messages(limit=int(arguments.get("limit") or 20))

    if name == "whatsapp_contacts":
        import doshie_whatsapp
        return doshie_whatsapp.get_contacts()

    raise ValueError(f"Unknown or unauthorized tool: {name}")




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
        "check doshie",
        "check",
        "status",
        "service",
        "services",
        "systemctl",
        "terminal",
        "command",
        "bash",
        "shell",
        "diagnose",
        "fix",
        "view file",
        "edit file",
        "write file",
        "create file",
        "save file",
        "make",
        "create",
        "build",
        "calculator",
        "app",
        "program",
        "script",
        "write a",
        "code",
        "develop",
        "generate",
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


TOOL_TITLES = {
    "run_command": "Terminal Command Execution",
    "view_file": "Inspect Source File",
    "replace_file_content": "Surgical Code Replacement",
    "write_file": "Write File",
    "delete_file": "Delete File",
    "remote_delete_file": "Remote File Deletion",
    "python_calculator": "Python Calculator",
    "wikipedia_search": "Wikipedia Lookup",
    "web_search": "Web Search",
    "list_code_files": "List Project Files",
    "read_code_file": "Read Source Code",
    "search_code": "Search Codebase",
    "propose_code_edit": "Propose Code Edit",
    "propose_new_file": "Propose New File",
    "request_python_diagnostics": "Python Diagnostics",
    "consult_hermes_ai": "Consult Hermes AI",
    "consult_agent": "Consult Specialist Agent",
    "check_service_health": "Check Service Health",
    "search_memories": "Search Memories",
    "get_tasks_and_notes": "Tasks & Notes",
    "save_memory": "Save Memory",
    "create_task": "Create Task",
    "add_note": "Add Note",
    "inspect_hardware": "Inspect Hardware",
    "inspect_fleet": "Inspect Fleet Network",
    "remote_run_command": "Remote Terminal Execution",
    "remote_view_file": "Remote File Inspection",
    "remote_write_file": "Remote File Deployment",
    "remote_replace_file_content": "Remote Surgical Code Edit",
    "propose_hardware_change": "Propose Hardware Change",
    "execute_hardware_change": "Execute Hardware Change",
    "get_hardware_governance": "Hardware Governance",
    "render_3d_model": "Render 3D Model",
    # Remote Technician
    "tech_health_report": "Fleet Health Report",
    "tech_check_disk": "Remote Disk Check",
    "tech_check_cpu_ram": "Remote CPU & RAM",
    "tech_check_internet": "Remote Internet Test",
    "tech_list_services": "Remote Services List",
    "tech_tail_logs": "Remote Log Inspection",
    "tech_restart_service": "Restart Remote Service",
    "tech_run_command": "Run Remote Command",
    "tech_list_fleet": "Fleet Computers List",
    "tech_list_updates": "Check Remote Updates",
    # Business & Clients
    "biz_add_client": "Add Client",
    "biz_search_clients": "Search Clients",
    "biz_check_consent": "Verify Client Consent",
    "biz_add_device": "Add Client Device",
    "biz_open_job": "Open Service Job",
    "biz_log_job_action": "Log Job Progress",
    "biz_close_job": "Complete Job",
    "biz_generate_invoice": "Generate Invoice",
    "biz_mark_paid": "Mark Job Paid",
    "biz_list_jobs": "List Service Jobs",
    "biz_revenue_report": "Revenue Report",
    # WhatsApp
    "whatsapp_send": "Send WhatsApp Message",
    "whatsapp_status": "WhatsApp Status",
    "whatsapp_messages": "Read WhatsApp Messages",
    "whatsapp_contacts": "WhatsApp Contacts",
}


def chat(
    url, model, messages, timeout=180, request_id="",
    actor_profile="", can_propose_changes=False, images=None,
    agent_capabilities=None, brain_mode="auto", return_details=False
):
    if images:
        v_reply = _vision_chat(
            url, model, messages, images,
            timeout=timeout, request_id=request_id
        )
        if return_details:
            return {
                "reply": v_reply,
                "thinking": None,
                "steps": [],
            }
        return v_reply

    working_messages = list(messages)

    model_str = str(model or "").lower()
    is_reasoning_model = (
        any(k in model_str for k in ("r1", "deepseek", "think"))
        or str(brain_mode or "").lower() in ("advanced", "heavyweight", "genius")
    )

    accumulated_thoughts = []
    executed_steps = []
    seen_tool_calls = set()
    disabled_tool_names = set()

    # Detect if user prompt is a build / creation / coding request
    user_prompt_text = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_prompt_text = str(m.get("content") or "").lower()
            break

    is_build_request = any(
        kw in user_prompt_text for kw in (
            "make a", "build a", "create a", "code a", "write a",
            "make an", "build an", "create an", "code an",
            "calculator", "app", "application", "script", "game",
            "program", "desktop app", "gui"
        )
    ) and not any(
        kw in user_prompt_text for kw in (
            "search wikipedia", "look up on wikipedia", "search the web", "google", "search for"
        )
    )
    if is_build_request:
        disabled_tool_names.add("wikipedia_search")
        disabled_tool_names.add("web_search")

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
                if name in (
                    "web_search", "python_calculator", "wikipedia_search",
                    "check_service_health", "inspect_hardware", "inspect_fleet",
                    "run_command", "view_file", "write_file", "replace_file_content", "delete_file",
                    "remote_run_command", "remote_view_file", "remote_write_file", "remote_replace_file_content", "remote_delete_file"
                ):
                    allowed_tools.append(tool)
                elif project_tools_needed:
                    if inside_hermes and name == "consult_hermes_ai":
                        continue
                    allowed_tools.append(tool)

        active_tools = [t for t in allowed_tools if t["function"]["name"] not in disabled_tool_names]
        if active_tools:
            request_body["tools"] = active_tools

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
            raw_c = str(message.get("content") or "").strip()
            clean_c = re.sub(r"^```(?:json)?\s*", "", raw_c)
            clean_c = re.sub(r"\s*```$", "", clean_c).strip()

            extracted_calls = []
            decoder = json.JSONDecoder()
            idx = 0
            while idx < len(clean_c):
                start = clean_c.find("{", idx)
                if start == -1:
                    break
                try:
                    obj, end_pos = decoder.raw_decode(clean_c[start:])
                    if isinstance(obj, dict) and ("name" in obj or "tool" in obj or "function" in obj):
                        fn_obj = obj.get("function") if isinstance(obj.get("function"), dict) else obj
                        t_name = str(fn_obj.get("name") or fn_obj.get("tool") or "").strip()
                        t_args = fn_obj.get("arguments") or fn_obj.get("parameters") or {}
                        if any(t["function"]["name"] == t_name for t in allowed_tools):
                            extracted_calls.append({
                                "id": f"call_inline_fallback_{len(extracted_calls)}",
                                "function": {
                                    "name": t_name,
                                    "arguments": t_args
                                }
                            })
                    idx = start + max(end_pos, 1)
                except Exception:
                    idx = start + 1

            if extracted_calls:
                tool_calls = extracted_calls
                message["tool_calls"] = tool_calls
                message["content"] = ""

        if not tool_calls:
            final_content = str(message.get("content") or "").strip()
            if not final_content and accumulated_thoughts:
                final_content = accumulated_thoughts[-1]
            thoughts_text = "\n\n".join(accumulated_thoughts).strip() if accumulated_thoughts else None
            if thoughts_text and "<think>" not in final_content:
                final_content = f"<think>\n{thoughts_text}\n</think>\n\n{final_content}"
            if return_details:
                return {
                    "reply": final_content,
                    "thinking": thoughts_text,
                    "steps": executed_steps,
                }
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
            except Exception:
                arguments = {}

            # Deduplication & anti-loop guardrail
            call_key = (name, json.dumps(arguments, sort_keys=True))
            if call_key in seen_tool_calls:
                disabled_tool_names.add(name)
                content = json.dumps({
                    "ok": True,
                    "notice": (
                        f"Notice: Tool '{name}' was already executed previously with these exact parameters. "
                        "Redundant calls are suppressed. You already possess all necessary information. "
                        "Do not call this tool again. Now proceed immediately to write the file using write_file "
                        "or provide your complete response to the user."
                    )
                })
                working_messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "content": content
                })
                continue

            seen_tool_calls.add(call_key)

            import time
            step_start = time.time()
            step_ok = True
            try:
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
                step_ok = False
                result = {"error": str(error)}
                content = json.dumps({
                    "ok": False,
                    "error": str(error)
                })

            if name == "write_file" and step_ok:
                disabled_tool_names.add("wikipedia_search")
                disabled_tool_names.add("web_search")

            duration_ms = max(int((time.time() - step_start) * 1000), 1)
            executed_steps.append({
                "tool": name,
                "title": TOOL_TITLES.get(name, name.replace("_", " ").title()),
                "arguments": arguments,
                "result": result,
                "ok": step_ok,
                "duration_ms": duration_ms,
            })

            working_messages.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "content": content
            })

    # If tools were executed but the model hit the iteration limit without generating text,
    # invoke one final completion pass without tools so the user receives a helpful final answer.
    if executed_steps:
        try:
            final_messages = list(working_messages)
            final_messages.append({
                "role": "system",
                "content": (
                    "All tool actions have completed. Summarize what you have built or performed, "
                    "and provide the final helpful response with instructions to the user now. Do not call any tools."
                )
            })
            final_payload = json.dumps({
                "model": model,
                "messages": final_messages,
                "temperature": 0.35,
                "max_tokens": 1500,
                "keep_alive": os.environ.get("YOSHI_KEEP_ALIVE", "5m"),
            }).encode("utf-8")
            req_final = urllib.request.Request(
                url,
                data=final_payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req_final, timeout=max(timeout, 30)) as resp_final:
                data_final = json.loads(resp_final.read().decode("utf-8"))
                choice_msg = data_final.get("choices", [{}])[0].get("message", {})
                final_content = str(choice_msg.get("content") or "").strip()
                if final_content:
                    thoughts_text = "\n\n".join(accumulated_thoughts).strip() if accumulated_thoughts else None
                    if return_details:
                        return {
                            "reply": final_content,
                            "thinking": thoughts_text,
                            "steps": executed_steps,
                        }
                    return final_content
        except Exception:
            pass

    fallback_text = "I executed the necessary tool actions, but reached the iteration limit before finalizing the response. Please review the step outputs above."
    if return_details:
        return {
            "reply": fallback_text,
            "thinking": "\n\n".join(accumulated_thoughts).strip() if accumulated_thoughts else None,
            "steps": executed_steps,
        }
    return fallback_text


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

