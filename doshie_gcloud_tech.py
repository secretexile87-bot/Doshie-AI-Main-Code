#!/usr/bin/env python3
"""
doshie_gcloud_tech.py - Doshie Cloud Technician Toolbox

Provides AI-driven remote computer technician capabilities for Hermes's
family fleet (Hermes's PC, Mom's PC, Dad's PC) using:
  1. Doshie Node Agent (HTTP over Tailscale) — primary protocol
  2. SSH over Tailscale — fallback for any Linux machine
  3. gcloud CLI — authentication layer and optional IAP SSH tunnel

All functions return structured dicts so Aeriel can read and summarize
the results naturally in chat.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any, Dict, Optional

import doshie_remote

# ---------------------------------------------------------------------------
# Known family computers — add hostnames/IPs as they join Tailscale
# ---------------------------------------------------------------------------
FLEET_REGISTRY: Dict[str, Dict[str, Any]] = {
    "hermes": {
        "display_name": "Hermes's PC (Acer Nitro)",
        "hostname": "acer-nitro",
        "os": "linux",
        "tailscale_ip": "100.109.79.35",
        "node_port": 5055,
        "owner": "hermes",
    },
    "acer-nitro": {
        "display_name": "Hermes's PC (Acer Nitro)",
        "hostname": "acer-nitro",
        "os": "linux",
        "tailscale_ip": "100.109.79.35",
        "node_port": 5055,
        "owner": "hermes",
    },
}


def update_fleet_registry(hostname: str, **kwargs) -> Dict[str, Any]:
    """
    Update or add an entry in the in-memory fleet registry.
    Call this when a new family PC joins Tailscale.
    """
    key = str(hostname or "").strip().lower()
    if not key:
        return {"ok": False, "error": "No hostname provided."}
    existing = FLEET_REGISTRY.get(key, {})
    existing.update({"hostname": key, **kwargs})
    FLEET_REGISTRY[key] = existing
    return {"ok": True, "hostname": key, "entry": existing}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve(target: str) -> Dict[str, Any]:
    """
    Resolve a friendly target name (e.g. 'mom', 'dad', 'hermes') to
    a fleet host dict from the registry or via Tailscale discovery.
    """
    key = str(target or "").strip().lower()
    if key in FLEET_REGISTRY:
        reg = FLEET_REGISTRY[key]
        hostname = reg.get("hostname", key)
    else:
        hostname = key
    return doshie_remote.resolve_fleet_host(hostname)


def _run_remote(target: str, command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute a shell command on the target computer via doshie_remote.
    Returns a dict with 'ok', 'stdout', 'stderr', 'exit_code'.
    """
    return doshie_remote.remote_run_command(target, command, timeout=timeout)


def _friendly_name(target: str) -> str:
    key = str(target or "").strip().lower()
    reg = FLEET_REGISTRY.get(key, {})
    return reg.get("display_name") or target


# ---------------------------------------------------------------------------
# Technician Tools
# ---------------------------------------------------------------------------

def check_disk_space(target: str) -> Dict[str, Any]:
    """
    Check disk usage on the target computer.
    Returns per-partition usage with total, used, available, and % full.
    """
    name = _friendly_name(target)
    host = _resolve(target)
    if not host.get("found"):
        return {"ok": False, "target": name, "error": f"Cannot reach {name}. Is it online and on Tailscale?"}

    hostname = host.get("hostname", target)
    os_type = str(host.get("os", "unknown")).lower()

    if "win" in os_type:
        cmd = "powershell -Command \"Get-PSDrive -PSProvider FileSystem | Select-Object Name,@{N='Used(GB)';E={[math]::Round($_.Used/1GB,2)}},@{N='Free(GB)';E={[math]::Round($_.Free/1GB,2)}},@{N='Total(GB)';E={[math]::Round(($_.Used+$_.Free)/1GB,2)}} | Format-Table -AutoSize\""
    else:
        cmd = "df -h --output=source,size,used,avail,pcent,target | head -20"

    result = _run_remote(hostname, cmd)
    return {
        "ok": result.get("ok", False),
        "target": name,
        "disk_usage": result.get("stdout", "").strip(),
        "error": result.get("stderr", "").strip() if not result.get("ok") else None,
    }


def check_cpu_ram(target: str) -> Dict[str, Any]:
    """
    Check CPU and RAM usage on the target computer.
    Returns CPU %, RAM used/total/%, and top memory consumers.
    """
    name = _friendly_name(target)
    host = _resolve(target)
    if not host.get("found"):
        return {"ok": False, "target": name, "error": f"Cannot reach {name}. Is it online and on Tailscale?"}

    hostname = host.get("hostname", target)
    os_type = str(host.get("os", "unknown")).lower()

    if "win" in os_type:
        cmd = (
            "powershell -Command \""
            "$cpu = (Get-WmiObject -Class Win32_Processor | Measure-Object LoadPercentage -Average).Average; "
            "$ram = Get-WmiObject Win32_OperatingSystem; "
            "$used = [math]::Round(($ram.TotalVisibleMemorySize - $ram.FreePhysicalMemory)/1MB, 2); "
            "$total = [math]::Round($ram.TotalVisibleMemorySize/1MB, 2); "
            "Write-Output \"CPU: $cpu%  RAM: $used GB / $total GB\"\""
        )
    else:
        cmd = (
            "echo '=== CPU ===' && top -bn1 | grep 'Cpu(s)' | awk '{print $2\"%\"}' && "
            "echo '=== RAM ===' && free -h && "
            "echo '=== Top 5 Memory Processes ===' && ps aux --sort=-%mem | head -6"
        )

    result = _run_remote(hostname, cmd)
    return {
        "ok": result.get("ok", False),
        "target": name,
        "cpu_ram": result.get("stdout", "").strip(),
        "error": result.get("stderr", "").strip() if not result.get("ok") else None,
    }


def list_running_services(target: str) -> Dict[str, Any]:
    """
    List running (and crashed/failed) services on the target computer.
    On Linux: systemctl. On Windows: Get-Service.
    """
    name = _friendly_name(target)
    host = _resolve(target)
    if not host.get("found"):
        return {"ok": False, "target": name, "error": f"Cannot reach {name}. Is it online and on Tailscale?"}

    hostname = host.get("hostname", target)
    os_type = str(host.get("os", "unknown")).lower()

    if "win" in os_type:
        cmd = "powershell -Command \"Get-Service | Where-Object {$_.Status -ne 'Running'} | Select-Object Name,Status | Format-Table -AutoSize\""
    else:
        cmd = (
            "echo '=== Failed Services ===' && systemctl --failed --no-pager 2>/dev/null && "
            "echo '=== Active Services (top 20) ===' && systemctl list-units --type=service --state=active --no-pager 2>/dev/null | head -25"
        )

    result = _run_remote(hostname, cmd)
    return {
        "ok": result.get("ok", False),
        "target": name,
        "services": result.get("stdout", "").strip(),
        "error": result.get("stderr", "").strip() if not result.get("ok") else None,
    }


def tail_system_logs(target: str, lines: int = 50) -> Dict[str, Any]:
    """
    Retrieve the last N lines of system error logs from the target computer.
    Linux: journalctl errors. Windows: System Event Log errors.
    """
    name = _friendly_name(target)
    host = _resolve(target)
    if not host.get("found"):
        return {"ok": False, "target": name, "error": f"Cannot reach {name}. Is it online and on Tailscale?"}

    hostname = host.get("hostname", target)
    os_type = str(host.get("os", "unknown")).lower()
    n = max(10, min(int(lines), 200))

    if "win" in os_type:
        cmd = (
            f"powershell -Command \""
            f"Get-EventLog -LogName System -EntryType Error,Warning -Newest {n} | "
            f"Select-Object TimeGenerated,Source,Message | Format-Table -AutoSize\""
        )
    else:
        cmd = f"journalctl -p err -n {n} --no-pager 2>/dev/null || tail -n {n} /var/log/syslog 2>/dev/null"

    result = _run_remote(hostname, cmd)
    return {
        "ok": result.get("ok", False),
        "target": name,
        "logs": result.get("stdout", "").strip(),
        "error": result.get("stderr", "").strip() if not result.get("ok") else None,
    }


def check_internet(target: str) -> Dict[str, Any]:
    """
    Run an internet connectivity test on the target computer.
    Pings Google DNS, tests DNS resolution, and checks HTTP reachability.
    """
    name = _friendly_name(target)
    host = _resolve(target)
    if not host.get("found"):
        return {"ok": False, "target": name, "error": f"Cannot reach {name}. Is it online and on Tailscale?"}

    hostname = host.get("hostname", target)
    os_type = str(host.get("os", "unknown")).lower()

    if "win" in os_type:
        cmd = (
            "powershell -Command \""
            "Test-NetConnection 8.8.8.8 -InformationLevel Quiet; "
            "Resolve-DnsName google.com -ErrorAction SilentlyContinue | Select-Object -First 1 Name,IPAddress; "
            "Test-NetConnection google.com -Port 443 -InformationLevel Quiet\""
        )
    else:
        cmd = (
            "echo '=== Ping Google DNS ===' && ping -c 3 8.8.8.8 2>&1 | tail -3 && "
            "echo '=== DNS Lookup ===' && nslookup google.com 2>&1 | head -6 && "
            "echo '=== HTTP Check ===' && curl -s -o /dev/null -w 'HTTP status: %{http_code}  Time: %{time_total}s' https://google.com --max-time 5"
        )

    result = _run_remote(hostname, cmd)
    return {
        "ok": result.get("ok", False),
        "target": name,
        "internet_test": result.get("stdout", "").strip(),
        "error": result.get("stderr", "").strip() if not result.get("ok") else None,
    }


def list_pending_updates(target: str) -> Dict[str, Any]:
    """
    List pending OS updates on the target computer.
    Linux: apt list --upgradable. Windows: Get-WindowsUpdate.
    """
    name = _friendly_name(target)
    host = _resolve(target)
    if not host.get("found"):
        return {"ok": False, "target": name, "error": f"Cannot reach {name}. Is it online and on Tailscale?"}

    hostname = host.get("hostname", target)
    os_type = str(host.get("os", "unknown")).lower()

    if "win" in os_type:
        cmd = (
            "powershell -Command \""
            "if (Get-Command Get-WindowsUpdate -ErrorAction SilentlyContinue) { "
            "  Get-WindowsUpdate | Select-Object KB,Title,Size | Format-Table -AutoSize "
            "} else { "
            "  Write-Output 'PSWindowsUpdate module not installed. Run: Install-Module PSWindowsUpdate' "
            "}\""
        )
    else:
        cmd = "apt list --upgradable 2>/dev/null | head -40 || echo 'apt not available'"

    result = _run_remote(hostname, cmd)
    return {
        "ok": result.get("ok", False),
        "target": name,
        "pending_updates": result.get("stdout", "").strip(),
        "error": result.get("stderr", "").strip() if not result.get("ok") else None,
    }


def restart_service(target: str, service_name: str) -> Dict[str, Any]:
    """
    Restart a specific service on the target computer.
    Linux: systemctl restart. Windows: Restart-Service.
    Requires user confirmation before calling — Aeriel must ask first.
    """
    name = _friendly_name(target)
    svc = str(service_name or "").strip()
    if not svc:
        return {"ok": False, "target": name, "error": "No service name provided."}

    host = _resolve(target)
    if not host.get("found"):
        return {"ok": False, "target": name, "error": f"Cannot reach {name}. Is it online and on Tailscale?"}

    hostname = host.get("hostname", target)
    os_type = str(host.get("os", "unknown")).lower()

    if "win" in os_type:
        cmd = f"powershell -Command \"Restart-Service -Name '{svc}' -Force; Get-Service -Name '{svc}'\""
    else:
        cmd = f"sudo systemctl restart {svc} && systemctl status {svc} --no-pager | head -20"

    result = _run_remote(hostname, cmd, timeout=30)
    return {
        "ok": result.get("ok", False),
        "target": name,
        "service": svc,
        "result": result.get("stdout", "").strip(),
        "error": result.get("stderr", "").strip() if not result.get("ok") else None,
    }


def run_tech_command(target: str, command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Run a custom technician shell command on any fleet computer.
    Aeriel should describe what the command does before executing it.
    """
    name = _friendly_name(target)
    cmd = str(command or "").strip()
    if not cmd:
        return {"ok": False, "target": name, "error": "No command provided."}

    host = _resolve(target)
    if not host.get("found"):
        return {"ok": False, "target": name, "error": f"Cannot reach {name}. Is it online and on Tailscale?"}

    hostname = host.get("hostname", target)
    result = _run_remote(hostname, cmd, timeout=timeout)
    return {
        "ok": result.get("ok", False),
        "target": name,
        "command": cmd,
        "stdout": result.get("stdout", "").strip(),
        "stderr": result.get("stderr", "").strip(),
        "exit_code": result.get("exit_code"),
    }


def full_health_report(target: str) -> Dict[str, Any]:
    """
    Run a full technician health diagnostic on the target computer.
    Gathers disk, CPU/RAM, failed services, and connectivity in one report.
    Returns a structured dict Aeriel can format into a readable summary.
    """
    name = _friendly_name(target)
    host = _resolve(target)
    if not host.get("found"):
        return {
            "ok": False,
            "target": name,
            "error": (
                f"Cannot reach {name}. "
                "Make sure the computer is powered on and connected to Tailscale. "
                "If it's a new PC, install doshie_node.py on it first."
            ),
        }

    hostname = host.get("hostname", target)
    os_type = str(host.get("os", "unknown")).lower()
    report: Dict[str, Any] = {"ok": True, "target": name, "os": os_type}

    # 1. Disk
    try:
        disk = check_disk_space(target)
        report["disk"] = disk.get("disk_usage") or disk.get("error")
    except Exception as exc:
        report["disk"] = f"Error: {exc}"

    # 2. CPU / RAM
    try:
        cpu = check_cpu_ram(target)
        report["cpu_ram"] = cpu.get("cpu_ram") or cpu.get("error")
    except Exception as exc:
        report["cpu_ram"] = f"Error: {exc}"

    # 3. Failed services
    try:
        svcs = list_running_services(target)
        report["services"] = svcs.get("services") or svcs.get("error")
    except Exception as exc:
        report["services"] = f"Error: {exc}"

    # 4. Internet
    try:
        net = check_internet(target)
        report["internet"] = net.get("internet_test") or net.get("error")
    except Exception as exc:
        report["internet"] = f"Error: {exc}"

    # 5. Recent errors from logs
    try:
        logs = tail_system_logs(target, lines=20)
        report["recent_errors"] = logs.get("logs") or logs.get("error")
    except Exception as exc:
        report["recent_errors"] = f"Error: {exc}"

    return report


def list_fleet() -> Dict[str, Any]:
    """
    List all known family computers in the tech fleet with their status.
    """
    computers = []
    for key, info in FLEET_REGISTRY.items():
        # Skip duplicate alias keys
        if key != info.get("hostname", key) and key in ("mom", "dad", "hermes"):
            continue
        hostname = info.get("hostname", key)
        # Quick ping via Tailscale
        host = doshie_remote.resolve_fleet_host(hostname)
        computers.append({
            "name": info.get("display_name", hostname),
            "hostname": hostname,
            "owner": info.get("owner", "unknown"),
            "os": info.get("os", "unknown"),
            "online": host.get("online", False),
            "tailscale_ip": host.get("ip") or info.get("tailscale_ip"),
        })
    return {"ok": True, "fleet": computers}


def gcloud_ssh_fallback(target: str, command: str) -> Dict[str, Any]:
    """
    SSH into a remote computer via gcloud IAP tunnel as a fallback when
    Tailscale or doshie_node is not available.
    Requires the target to be a GCP Compute Engine instance.
    Only available if user has a GCP project configured.
    """
    hostname = str(target or "").strip()
    cmd = str(command or "").strip()
    if not hostname or not cmd:
        return {"ok": False, "error": "host and command required."}

    try:
        proc = subprocess.run(
            ["gcloud", "compute", "ssh", hostname, "--command", cmd, "--quiet"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "exit_code": proc.returncode,
            "method": "gcloud-ssh",
        }
    except FileNotFoundError:
        return {"ok": False, "error": "gcloud CLI not found."}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "gcloud SSH timed out."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
