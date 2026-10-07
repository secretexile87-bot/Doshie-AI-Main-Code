"""Execution tools for Doshie Autonomous Agent.

Provides safe command execution, file editing, directory inspection,
and web search. Tool definitions match the OpenAI function calling schema.
"""

from __future__ import annotations

import difflib
import json
import os
from pathlib import Path
import subprocess
import time

try:
    import sys
    sys.path.insert(0, "/home/doshie/Doshie")
    import Doshie_search
except Exception:
    Doshie_search = None


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell / bash command directly on the host system to run scripts, inspect status, install packages, or manage services.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact shell command line to execute (e.g. 'git status', 'python3 script.py', 'ls -la')."
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Optional working directory for the command. Defaults to the user home directory."
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
            "description": "View the contents of a local file with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to inspect."
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Starting line number (1-indexed). Defaults to 1."
                    },
                    "line_count": {
                        "type": "integer",
                        "description": "Number of lines to read. Defaults to 100."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or completely overwrite an existing file with the specified content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path of the file to create or write."
                    },
                    "content": {
                        "type": "string",
                        "description": "The full code or text content to write."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_file_content",
            "description": "Replace a specific contiguous block of text in an existing file with updated text (surgical edit).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Target file path to edit."
                    },
                    "target_content": {
                        "type": "string",
                        "description": "The exact existing text chunk to replace."
                    },
                    "replacement_content": {
                        "type": "string",
                        "description": "The new replacement text."
                    }
                },
                "required": ["path", "target_content", "replacement_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and subdirectories within a given folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list. Defaults to current workspace / home."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for documentation, solutions, error messages, or current data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string."
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# Set of tools that modify system state or run code, strictly requiring user approval
APPROVAL_REQUIRED_TOOLS = {"run_command", "write_file", "replace_file_content"}


def resolve_path(raw_path: str) -> Path:
    p = Path(raw_path.strip()).expanduser()
    if not p.is_absolute():
        p = Path.home() / p
    return p.resolve()


def execute_tool(name: str, args: dict) -> dict:
    """Executes a tool and returns a structured output dict."""
    args = args or {}
    start_time = time.time()

    try:
        if name == "run_command":
            cmd = args.get("command", "").strip()
            if not cmd:
                return {"ok": False, "error": "No command provided"}
            cwd = args.get("cwd")
            working_dir = resolve_path(cwd) if cwd else Path.home()
            if not working_dir.exists():
                working_dir = Path.home()

            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=str(working_dir),
                capture_output=True,
                text=True,
                timeout=120
            )
            duration = round(time.time() - start_time, 2)
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": proc.stdout[-8000:] if len(proc.stdout) > 8000 else proc.stdout,
                "stderr": proc.stderr[-8000:] if len(proc.stderr) > 8000 else proc.stderr,
                "duration_seconds": duration,
                "cwd": str(working_dir)
            }

        elif name == "view_file":
            raw_target = str(args.get("path", "")).strip()
            target = resolve_path(raw_target)
            if not target.exists():
                # Smart fallbacks for common project search paths
                candidates = [
                    Path("/home/doshie/Doshie") / target.name,
                    Path("/home/doshie/Doshie") / raw_target.lstrip("/"),
                    target.parent.parent / target.name if target.parent != target.parent.parent else None,
                    Path.home() / target.name,
                ]
                found = None
                for c in candidates:
                    if c and c.exists() and c.is_file():
                        found = c
                        break
                if found:
                    target = found
                else:
                    return {"ok": False, "error": f"File not found: {target}"}
            if target.is_dir():
                return {"ok": False, "error": f"Target is a directory, use list_dir instead: {target}"}

            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
            try:
                start_line = int(args.get("start_line", 1))
            except Exception:
                start_line = 1
            try:
                line_count = min(300, max(1, int(args.get("line_count", 100))))
            except Exception:
                line_count = 100

            # Support tail reading from end
            if start_line < 0 or bool(args.get("tail")):
                count = abs(start_line) if start_line < 0 else line_count
                selected = lines[-count:]
                start_line = max(1, len(lines) - len(selected) + 1)
            else:
                start_line = max(1, start_line)
                selected = lines[start_line - 1 : start_line - 1 + line_count]

            numbered = [
                f"{start_line + i:4d} | {line}"
                for i, line in enumerate(selected)
            ]
            return {
                "ok": True,
                "path": str(target),
                "total_lines": len(lines),
                "showing_range": f"{start_line}-{start_line + len(selected) - 1}",
                "content": "\n".join(numbered)
            }

        elif name == "write_file":
            target = resolve_path(args.get("path", ""))
            content = args.get("content", "")
            target.parent.mkdir(parents=True, exist_ok=True)
            existed = target.exists()
            target.write_text(content, encoding="utf-8")
            return {
                "ok": True,
                "path": str(target),
                "action": "overwritten" if existed else "created",
                "bytes_written": len(content.encode("utf-8")),
                "line_count": len(content.splitlines())
            }

        elif name == "replace_file_content":
            target = resolve_path(args.get("path", ""))
            if not target.exists():
                return {"ok": False, "error": f"File does not exist: {target}"}

            original = target.read_text(encoding="utf-8", errors="replace")
            find_str = args.get("target_content", "")
            replace_str = args.get("replacement_content", "")

            if find_str not in original:
                return {
                    "ok": False,
                    "error": "The target_content to replace was not found in the file. Check exact spacing and indentation."
                }

            updated = original.replace(find_str, replace_str, 1)
            target.write_text(updated, encoding="utf-8")

            # Generate diff preview
            diff = "".join(difflib.unified_diff(
                original.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=f"a/{target.name}",
                tofile=f"b/{target.name}",
                n=3
            ))

            return {
                "ok": True,
                "path": str(target),
                "diff": diff,
                "action": "replaced"
            }

        elif name == "list_dir":
            target = resolve_path(args.get("path") or ".")
            if not target.exists() or not target.is_dir():
                return {"ok": False, "error": f"Directory not found: {target}"}

            entries = []
            for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if item.name.startswith(".") and item.name not in {".env", ".gitignore"}:
                    continue
                entries.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None
                })
            return {
                "ok": True,
                "directory": str(target),
                "count": len(entries),
                "items": entries[:100]
            }

        elif name == "web_search":
            query = args.get("query", "").strip()
            if not query:
                return {"ok": False, "error": "Query required"}
            if Doshie_search:
                results = Doshie_search.web_search(query)
                return {"ok": True, "results": results.get("results", [])[:5]}
            else:
                return {"ok": False, "error": "Search service not available"}

        else:
            return {"ok": False, "error": f"Unknown tool: {name}"}

    except Exception as e:
        return {"ok": False, "error": str(e)}
