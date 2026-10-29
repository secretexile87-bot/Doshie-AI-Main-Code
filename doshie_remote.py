#!/usr/bin/env python3
"""
doshie_remote.py - Doshie Autonomous Fleet Technician Remote Engine

Empowers Doshie to act as a full remote systems engineer and technician across
Hermes's fleet of computers (Windows PCs, Linux servers, laptops).

Capabilities:
1. Host Discovery & Resolution via Tailscale mesh.
2. Remote Command Execution (Linux Bash / Windows PowerShell).
3. Remote Code & File Reading (with line numbering).
4. Remote Code Writing & Deployments (safe base64 transmission).
5. Remote Surgical Code Edits (find-and-replace on remote codebases).
6. Support for both SSH/Tailscale SSH and Doshie Node Agent HTTP protocols.
"""

import os
import re
import sys
import json
import time
import base64
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

DOSHIE_DIR = Path("/home/doshie/Doshie")
DEFAULT_SSH_KEY = Path.home() / ".ssh" / "id_ed25519"
DEFAULT_NODE_PORT = 5055


def resolve_fleet_host(target: str) -> Dict[str, Any]:
    """
    Resolve a host name or IP address within the Tailscale mesh fleet.
    Returns host metadata dictionary including IP, OS, online status, and reachability.
    """
    t = str(target or "").strip()
    if not t:
        return {"error": "No host specified.", "found": False}

    # Check for localhost
    if t.lower() in ("localhost", "127.0.0.1", "acer-nitro", "local", "nitro"):
        return {
            "name": "acer-nitro",
            "hostname": "acer-nitro",
            "ip": "127.0.0.1",
            "tailscale_ip": "100.109.79.35",
            "os": "linux",
            "is_local": True,
            "online": True,
            "found": True
        }

    # Query Tailscale
    try:
        res = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=4)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            peers = data.get("Peer", {})
            peer_list = peers.values() if isinstance(peers, dict) else peers

            for peer in peer_list:
                hostname = peer.get("HostName", "")
                ips = peer.get("TailscaleIPs", [])
                ipv4 = ips[0] if ips else ""
                os_type = str(peer.get("OS", "unknown")).lower()
                is_online = bool(peer.get("Online", False))

                # Match by hostname (case-insensitive substring or exact) or IP
                if (
                    t.lower() == hostname.lower()
                    or t.lower() in hostname.lower()
                    or (ipv4 and t == ipv4)
                ):
                    return {
                        "name": hostname,
                        "hostname": hostname,
                        "ip": ipv4,
                        "tailscale_ip": ipv4,
                        "os": os_type,
                        "is_local": False,
                        "online": is_online,
                        "last_seen": peer.get("LastSeen", ""),
                        "found": True
                    }
    except Exception:
        pass

    # If direct IP or unknown hostname was provided
    is_ip = bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", t))
    return {
        "name": t,
        "hostname": t,
        "ip": t if is_ip else "",
        "tailscale_ip": t if is_ip else "",
        "os": "unknown",
        "is_local": False,
        "online": None,
        "found": is_ip
    }


def _run_via_ssh(ip: str, cmd: str, os_type: str = "linux", timeout: int = 60, user: Optional[str] = None) -> Tuple[bool, int, str, str]:
    """Execute command over SSH or Tailscale SSH."""
    target_spec = f"{user}@{ip}" if user else ip
    
    # Base SSH command with fast timeouts and key forwarding
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=5",
    ]
    if DEFAULT_SSH_KEY.exists():
        ssh_cmd.extend(["-i", str(DEFAULT_SSH_KEY)])

    ssh_cmd.append(target_spec)

    if os_type == "windows":
        # Format for Windows PowerShell execution
        encoded_ps = base64.b64encode(cmd.encode("utf-16le")).decode("ascii")
        ssh_cmd.append(f"powershell.exe -NoProfile -EncodedCommand {encoded_ps}")
    else:
        ssh_cmd.append(cmd)

    try:
        proc = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        return True, proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return False, -1, "", f"Remote command timed out after {timeout} seconds."
    except Exception as exc:
        return False, -1, "", f"SSH execution error: {str(exc)}"


def _call_node_agent(ip: str, endpoint: str, payload: Dict[str, Any], timeout: int = 30) -> Optional[Dict[str, Any]]:
    """Try communicating with Doshie Node Agent if active on port 5055."""
    url = f"http://{ip}:{DEFAULT_NODE_PORT}/api/{endpoint.lstrip('/')}"
    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    return None


def remote_run_command(
    host: str,
    command: str,
    user: Optional[str] = None,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Execute a shell or PowerShell command remotely on any computer in the fleet.
    """
    cmd = str(command or "").strip()
    if not cmd:
        return {"ok": False, "error": "No command provided."}

    node = resolve_fleet_host(host)
    if node.get("is_local"):
        # Local execution fallback
        try:
            p = subprocess.run(cmd, shell=True, cwd="/home/doshie/Doshie", capture_output=True, text=True, timeout=timeout)
            return {
                "ok": p.returncode == 0,
                "exit_code": p.returncode,
                "stdout": p.stdout,
                "stderr": p.stderr,
                "host": "localhost",
                "protocol": "local"
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "host": "localhost"}

    target_ip = node.get("ip") or host
    os_type = node.get("os", "linux")

    # 1. Try Doshie Node Agent HTTP first if available
    node_res = _call_node_agent(target_ip, "exec", {"command": cmd, "timeout": timeout}, timeout=timeout + 2)
    if node_res and "exit_code" in node_res:
        return {
            "ok": node_res.get("exit_code") == 0,
            "exit_code": node_res.get("exit_code"),
            "stdout": node_res.get("stdout", ""),
            "stderr": node_res.get("stderr", ""),
            "host": node.get("name", host),
            "os": os_type,
            "protocol": "doshie_node_agent"
        }

    # 2. Try SSH / Tailscale SSH
    connected, code, stdout, stderr = _run_via_ssh(target_ip, cmd, os_type=os_type, timeout=timeout, user=user)
    if connected:
        return {
            "ok": code == 0,
            "exit_code": code,
            "stdout": stdout,
            "stderr": stderr,
            "host": node.get("name", host),
            "os": os_type,
            "protocol": "ssh"
        }

    return {
        "ok": False,
        "exit_code": -1,
        "error": (
            f"Could not connect to remote host '{host}' ({target_ip}). "
            f"Details: {stderr or 'Connection refused or host offline.'}. "
            f"Ensure Tailscale SSH or Doshie Node Agent is running on the target machine."
        ),
        "host": node.get("name", host),
        "os": os_type
    }


def remote_view_file(
    host: str,
    path: str,
    start_line: int = 1,
    line_count: int = 150,
    user: Optional[str] = None
) -> Dict[str, Any]:
    """
    Read code or file contents remotely with line numbers from any machine in the fleet.
    """
    path_str = str(path or "").strip()
    if not path_str:
        return {"ok": False, "error": "No file path provided."}

    node = resolve_fleet_host(host)
    if node.get("is_local"):
        p = Path(path_str).expanduser().resolve()
        if not p.exists() or not p.is_file():
            return {"ok": False, "error": f"Local file not found: {p}"}
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        end_line = min(start_line + line_count - 1, len(lines))
        slice_lines = lines[start_line - 1:end_line]
        numbered = "".join(f"{i + start_line}: {line}" for i, line in enumerate(slice_lines))
        return {
            "ok": True,
            "host": "localhost",
            "path": str(p),
            "start_line": start_line,
            "end_line": end_line,
            "total_lines": len(lines),
            "content": numbered
        }

    target_ip = node.get("ip") or host
    os_type = node.get("os", "linux")

    # 1. Try Doshie Node Agent HTTP
    agent_res = _call_node_agent(target_ip, "file/read", {
        "path": path_str,
        "start_line": start_line,
        "line_count": line_count
    })
    if agent_res and agent_res.get("ok"):
        return agent_res

    # 2. SSH Python snippet (works uniformly on Linux & Windows if python is present)
    py_reader = (
        f"python3 -c \""
        f"import pathlib, sys;"
        f"p = pathlib.Path(r'{path_str}');"
        f"sys.exit(1) if not p.exists() else None;"
        f"lines = p.read_text(encoding='utf-8', errors='replace').splitlines(True);"
        f"s = max({start_line}, 1);"
        f"e = min(s + {line_count} - 1, len(lines));"
        f"print(f'TOTAL_LINES:{{len(lines)}}');"
        f"print(''.join(f'{{i + s}}: {{l}}' for i, l in enumerate(lines[s - 1:e])))"
        f"\""
    )

    if os_type == "windows":
        # PowerShell native fallback for Windows
        cmd = (
            f"$p = '{path_str}'; "
            f"if (!(Test-Path $p)) {{ Write-Error 'FileNotFound'; exit 1 }}; "
            f"$lines = Get-Content $p; "
            f"$total = $lines.Count; "
            f"Write-Output \"TOTAL_LINES:$total\"; "
            f"$start = [Math]::Max(1, {start_line}) - 1; "
            f"$count = {line_count}; "
            f"$idx = $start + 1; "
            f"$lines | Select-Object -Skip $start -First $count | ForEach-Object {{ \"$idx`: $_\"; $idx++ }}"
        )
    else:
        cmd = py_reader

    ok, code, stdout, stderr = _run_via_ssh(target_ip, cmd, os_type=os_type, user=user)
    if not ok or code != 0:
        return {
            "ok": False,
            "error": f"Failed to read remote file: {stderr or stdout or 'File not found or unreachable'}",
            "host": node.get("name", host),
            "path": path_str
        }

    total_lines = 0
    content_lines = []
    for line in stdout.splitlines(True):
        if line.startswith("TOTAL_LINES:"):
            try:
                total_lines = int(line.split(":", 1)[1].strip())
            except Exception:
                pass
        else:
            content_lines.append(line)

    return {
        "ok": True,
        "host": node.get("name", host),
        "path": path_str,
        "start_line": start_line,
        "end_line": start_line + len(content_lines) - 1,
        "total_lines": total_lines or len(content_lines),
        "content": "".join(content_lines)
    }


def remote_write_file(
    host: str,
    path: str,
    content: str,
    overwrite: bool = True,
    user: Optional[str] = None
) -> Dict[str, Any]:
    """
    Write or deploy a complete file or script to any remote computer in the fleet.
    Transmits content via base64 for 100% binary/string safety.
    """
    path_str = str(path or "").strip()
    if not path_str:
        return {"ok": False, "error": "No file path provided."}

    node = resolve_fleet_host(host)
    if node.get("is_local"):
        p = Path(path_str).expanduser().resolve()
        if p.exists() and not overwrite:
            return {"ok": False, "error": f"File exists and overwrite is False: {p}"}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"ok": True, "host": "localhost", "path": str(p), "bytes_written": len(content.encode("utf-8"))}

    target_ip = node.get("ip") or host
    os_type = node.get("os", "linux")

    # 1. Try Doshie Node Agent HTTP
    agent_res = _call_node_agent(target_ip, "file/write", {
        "path": path_str,
        "content": content,
        "overwrite": overwrite
    })
    if agent_res and agent_res.get("ok"):
        return agent_res

    # 2. Transmit via safe Base64 over SSH
    b64_content = base64.b64encode(content.encode("utf-8")).decode("ascii")

    if os_type == "windows":
        cmd = (
            f"$dest = '{path_str}'; "
            f"$dir = [System.IO.Path]::GetDirectoryName($dest); "
            f"if ($dir -and !(Test-Path $dir)) {{ [System.IO.Directory]::CreateDirectory($dir) | Out-Null }}; "
            f"if ((Test-Path $dest) -and (-not ${str(overwrite).lower()})) {{ Write-Error 'FileExists'; exit 1 }}; "
            f"$bytes = [System.Convert]::FromBase64String('{b64_content}'); "
            f"[System.IO.File]::WriteAllBytes($dest, $bytes); "
            f"Write-Output \"SUCCESS: $($bytes.Length) bytes written.\""
        )
    else:
        cmd = (
            f"python3 -c \""
            f"import base64, pathlib;"
            f"p = pathlib.Path(r'{path_str}');"
            f"p.parent.mkdir(parents=True, exist_ok=True);"
            f"p.write_bytes(base64.b64decode('{b64_content}'));"
            f"print(f'SUCCESS: {{p.stat().st_size}} bytes written.')\" 2>/dev/null || "
            f"(mkdir -p \"$(dirname '{path_str}')\" && echo '{b64_content}' | base64 -d > '{path_str}' && echo 'SUCCESS')"
        )

    ok, code, stdout, stderr = _run_via_ssh(target_ip, cmd, os_type=os_type, user=user)
    if not ok or code != 0:
        return {
            "ok": False,
            "error": f"Failed to write remote file: {stderr or stdout}",
            "host": node.get("name", host),
            "path": path_str
        }

    return {
        "ok": True,
        "host": node.get("name", host),
        "path": path_str,
        "bytes_written": len(content.encode("utf-8")),
        "message": f"Successfully wrote {len(content.encode('utf-8'))} bytes to {node.get('name', host)}:{path_str}"
    }


def remote_replace_file_content(
    host: str,
    path: str,
    target_content: str,
    replacement_content: str,
    user: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform a surgical find-and-replace modification in an existing file on a remote PC.
    """
    path_str = str(path or "").strip()
    if not path_str:
        return {"ok": False, "error": "No file path provided."}
    if not target_content:
        return {"ok": False, "error": "No target content provided to replace."}

    node = resolve_fleet_host(host)
    if node.get("is_local"):
        p = Path(path_str).expanduser().resolve()
        if not p.exists() or not p.is_file():
            return {"ok": False, "error": f"File not found: {p}"}
        content = p.read_text(encoding="utf-8")
        cnt = content.count(target_content)
        if cnt == 0:
            return {"ok": False, "error": "Target content not found in local file."}
        if cnt > 1:
            return {"ok": False, "error": f"Target content occurs {cnt} times. Provide a more unique target chunk."}
        p.write_text(content.replace(target_content, replacement_content, 1), encoding="utf-8")
        return {"ok": True, "host": "localhost", "path": str(p), "message": "Successfully modified local file."}

    target_ip = node.get("ip") or host
    os_type = node.get("os", "linux")

    # 1. Try Doshie Node Agent HTTP
    agent_res = _call_node_agent(target_ip, "file/replace", {
        "path": path_str,
        "target_content": target_content,
        "replacement_content": replacement_content
    })
    if agent_res and agent_res.get("ok"):
        return agent_res

    # 2. Base64 encoded payload for safe remote execution
    b64_target = base64.b64encode(target_content.encode("utf-8")).decode("ascii")
    b64_replace = base64.b64encode(replacement_content.encode("utf-8")).decode("ascii")

    if os_type == "windows":
        cmd = (
            f"$dest = '{path_str}'; "
            f"if (!(Test-Path $dest)) {{ Write-Error 'FileNotFound'; exit 1 }}; "
            f"$target = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_target}')); "
            f"$repl = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_replace}')); "
            f"$content = [System.IO.File]::ReadAllText($dest, [System.Text.Encoding]::UTF8); "
            f"$idx = $content.IndexOf($target); "
            f"if ($idx -lt 0) {{ Write-Error 'TargetNotFound'; exit 2 }}; "
            f"$lastIdx = $content.LastIndexOf($target); "
            f"if ($idx -ne $lastIdx) {{ Write-Error 'TargetNotUnique'; exit 3 }}; "
            f"$newContent = $content.Remove($idx, $target.Length).Insert($idx, $repl); "
            f"[System.IO.File]::WriteAllText($dest, $newContent, [System.Text.Encoding]::UTF8); "
            f"Write-Output 'REPLACE_SUCCESS'"
        )
    else:
        cmd = (
            f"python3 -c \""
            f"import base64, pathlib, sys;"
            f"p = pathlib.Path(r'{path_str}');"
            f"sys.exit(1) if not p.exists() else None;"
            f"target = base64.b64decode('{b64_target}').decode('utf-8');"
            f"repl = base64.b64decode('{b64_replace}').decode('utf-8');"
            f"content = p.read_text(encoding='utf-8');"
            f"cnt = content.count(target);"
            f"sys.exit(2) if cnt == 0 else None;"
            f"sys.exit(3) if cnt > 1 else None;"
            f"p.write_text(content.replace(target, repl, 1), encoding='utf-8');"
            f"print('REPLACE_SUCCESS')\""
        )

    ok, code, stdout, stderr = _run_via_ssh(target_ip, cmd, os_type=os_type, user=user)
    if "REPLACE_SUCCESS" in stdout:
        return {
            "ok": True,
            "host": node.get("name", host),
            "path": path_str,
            "message": f"Successfully replaced target content in {node.get('name', host)}:{path_str}."
        }

    err_msg = stderr or stdout
    if code == 1:
        err_msg = f"Remote file '{path_str}' was not found on {node.get('name', host)}."
    elif code == 2:
        err_msg = f"Target content was not found in remote file '{path_str}'."
    elif code == 3:
        err_msg = f"Target content occurs multiple times in '{path_str}'. Provide a larger, unique code chunk."

    return {
        "ok": False,
        "error": f"Remote edit failed: {err_msg}",
        "host": node.get("name", host),
        "path": path_str
    }


def remote_delete_file(
    host: str,
    path: str,
    user: Optional[str] = None
) -> Dict[str, Any]:
    """
    Delete a file locally or on any remote fleet computer.
    """
    path_str = str(path or "").strip()
    if not path_str:
        return {"ok": False, "error": "No file path provided."}

    node = resolve_fleet_host(host)
    if node.get("is_local"):
        p = Path(path_str).expanduser().resolve()
        if not p.exists():
            return {"ok": True, "host": "localhost", "path": str(p), "message": f"File {p} already does not exist."}
        if p.is_dir():
            p.rmdir()
        else:
            p.unlink()
        return {"ok": True, "host": "localhost", "path": str(p), "message": f"Successfully deleted {p}."}

    target_ip = node.get("ip") or host
    os_type = node.get("os", "linux")
    if os_type == "windows":
        cmd = f'powershell -Command "Remove-Item -Path \'{path_str}\' -Force -ErrorAction SilentlyContinue; if (Test-Path \'{path_str}\') {{ exit 1 }} else {{ Write-Output \'DELETE_SUCCESS\' }}"'
    else:
        cmd = f"rm -f '{path_str}' && echo 'DELETE_SUCCESS'"

    ok, code, stdout, stderr = _run_via_ssh(target_ip, cmd, os_type=os_type, user=user)
    if ok and "DELETE_SUCCESS" in stdout:
        return {
            "ok": True,
            "host": node.get("name", host),
            "path": path_str,
            "message": f"Successfully deleted {path_str} on {node.get('name', host)}."
        }
    return {
        "ok": False,
        "error": f"Remote delete failed: {stderr or stdout}",
        "host": node.get("name", host),
        "path": path_str
    }

