#!/usr/bin/env python3
"""
doshie_gaming_monitor.py - Autonomous Watchdog & Auto-Repair Daemon for Doshie Gaming
Monitors:
  1. IPv4 Packet Forwarding (net.ipv4.ip_forward=1)
  2. NAT Gateway Masquerading (iptables POSTROUTING for LAN interface & tailscale0)
  3. Tailscale Mesh Connection & Daemon status
  4. Tailscale Dallas Exit Node routing (vultr exit node)
  5. Low-Latency Reachability & Ping to Dallas Gateway (155.138.241.159)
  6. Public egress IP and geolocation validation

If any subsystem degrades or drops, automatically executes self-healing repair actions,
writes real-time telemetry to /home/doshie/Doshie/data/doshie_gaming_status.json,
and maintains an audit log in /home/doshie/.doshie/doshie_gaming.log.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.request

DOSHIE_DIR = Path("/home/doshie/Doshie")
DATA_DIR = DOSHIE_DIR / "data"
STATUS_FILE = DATA_DIR / "doshie_gaming_status.json"
CONFIG_DIR = Path.home() / ".doshie"
LOG_FILE = CONFIG_DIR / "doshie_gaming.log"

DEFAULT_EXIT_NODE = os.environ.get("DOSHIE_GAMING_EXIT_NODE", "vultr")
DALLAS_IP = "155.138.241.159"
CHECK_INTERVAL_SECONDS = int(os.environ.get("DOSHIE_GAMING_CHECK_INTERVAL", "30"))


def log_event(message: str, level: str = "INFO"):
    """Appends an event to the persistent audit log."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] [{level}] {message}"
    print(entry, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception as e:
        print(f"Failed to write to log: {e}", file=sys.stderr)


def run_cmd(cmd_list: list[str], timeout: int = 5) -> tuple[bool, str]:
    """Run a command without sudo."""
    try:
        proc = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        out = proc.stdout.strip() if proc.returncode == 0 else (proc.stderr.strip() or proc.stdout.strip())
        return proc.returncode == 0, out
    except Exception as e:
        return False, str(e)


def run_sudo(cmd_list: list[str], timeout: int = 10) -> tuple[bool, str]:
    """Run a command using passwordless sudo (sudo -n)."""
    full_cmd = ["sudo", "-n"] + cmd_list
    try:
        proc = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        out = proc.stdout.strip() if proc.returncode == 0 else (proc.stderr.strip() or proc.stdout.strip())
        return proc.returncode == 0, out
    except Exception as e:
        return False, str(e)


def get_default_lan_interface() -> str:
    """Detects primary LAN network interface."""
    try:
        ok, out = run_cmd(["ip", "route", "show", "default"])
        if ok and out:
            parts = out.split()
            if "dev" in parts:
                return parts[parts.index("dev") + 1]
    except Exception:
        pass
    return "enp129s0"


def get_lan_ip() -> str:
    """Detects active host LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "192.168.1.167"


def check_ip_forward() -> bool:
    """Checks whether net.ipv4.ip_forward is 1."""
    try:
        p = Path("/proc/sys/net/ipv4/ip_forward")
        if p.exists():
            return p.read_text().strip() == "1"
    except Exception:
        pass
    ok, out = run_cmd(["sysctl", "-n", "net.ipv4.ip_forward"])
    return ok and out.strip() == "1"


def check_nat_rule(iface: str) -> bool:
    """Checks if iptables POSTROUTING contains MASQUERADE for the interface."""
    ok, _ = run_sudo(["iptables", "-t", "nat", "-C", "POSTROUTING", "-o", iface, "-j", "MASQUERADE"])
    return ok


def check_tailscale_status() -> tuple[bool, dict]:
    """Returns (is_running, status_dict)."""
    ok, out = run_cmd(["tailscale", "status", "--json"])
    if not ok or not out:
        return False, {}
    try:
        data = json.loads(out)
        return True, data
    except Exception:
        return False, {}


def check_exit_node(ts_data: dict, expected_node: str = DEFAULT_EXIT_NODE) -> tuple[bool, str | None]:
    """Checks if the expected exit node is currently active."""
    exit_status = ts_data.get("ExitNodeStatus")
    if not exit_status:
        return False, None
    
    online = exit_status.get("Online", False)
    exit_node_id = exit_status.get("ID", "")
    exit_ips = exit_status.get("TailscaleIPs", [])

    # Check peer details to match expected_node name
    peers = ts_data.get("Peer", {})
    active_name = None
    for peer_id, peer in peers.items():
        if peer.get("ExitNode"):
            active_name = peer.get("HostName") or peer.get("DNSName", "").split(".")[0]
            break

    if not active_name and exit_ips:
        for peer in peers.values():
            peer_ips = peer.get("TailscaleIPs", [])
            if any(ip.split("/")[0] in [x.split("/")[0] for x in exit_ips] for ip in peer_ips):
                active_name = peer.get("HostName")
                break

    is_expected = bool(online and (active_name == expected_node or expected_node in str(exit_ips)))
    return is_expected, active_name


def ping_dallas(target_ip: str = DALLAS_IP) -> tuple[bool, float | None, float]:
    """Pings Dallas server. Returns (success, avg_latency_ms, packet_loss_pct)."""
    ok, out = run_cmd(["ping", "-c", "2", "-W", "2", target_ip], timeout=6)
    if not ok:
        return False, None, 100.0
    
    loss = 0.0
    m_loss = re.search(r"(\d+(?:\.\d+)?)%\s+packet\s+loss", out)
    if m_loss:
        loss = float(m_loss.group(1))

    latency = None
    m_rtt = re.search(r"rtt\s+min/avg/max/mdev\s*=\s*[\d\.]+/([\d\.]+)/", out)
    if m_rtt:
        latency = round(float(m_rtt.group(1)), 2)

    return (loss == 0.0 and latency is not None), latency, loss


def query_public_ip() -> tuple[str, str]:
    """Queries public IP and geolocation."""
    try:
        req = urllib.request.Request(
            "https://ipinfo.io/json",
            headers={"User-Agent": "curl/7.68.0"}
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            ip = data.get("ip", "Unknown")
            city = data.get("city", "Unknown")
            region = data.get("region", "")
            org = data.get("org", "")
            return ip, f"{city}, {region} ({org})"
    except Exception:
        pass
    
    ok, out = run_cmd(["curl", "-s", "--max-time", "3", "https://ifconfig.me"])
    if ok and out:
        return out.strip(), "External Route"
    return "Unknown", "Unknown"


def inspect_gaming_status(exit_node_target: str = DEFAULT_EXIT_NODE) -> dict:
    """Runs a complete diagnostics scan of Doshie Gaming."""
    lan_iface = get_default_lan_interface()
    lan_ip = get_lan_ip()

    ip_fwd = check_ip_forward()
    nat_lan = check_nat_rule(lan_iface)
    nat_ts = check_nat_rule("tailscale0")

    ts_ok, ts_data = check_tailscale_status()
    exit_node_active, active_node_name = check_exit_node(ts_data, exit_node_target)

    ping_ok, latency_ms, packet_loss = ping_dallas()
    public_ip, location = query_public_ip()

    healthy = (
        ip_fwd
        and nat_lan
        and nat_ts
        and ts_ok
        and exit_node_active
        and ping_ok
    )

    status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "healthy": healthy,
        "lan_interface": lan_iface,
        "lan_ip": lan_ip,
        "gateway_status": {
            "ip_forward": ip_fwd,
            "nat_lan_rule": nat_lan,
            "nat_tailscale_rule": nat_ts,
            "active": ip_fwd and nat_lan and nat_ts
        },
        "tailscale_status": {
            "service_online": ts_ok,
            "target_exit_node": exit_node_target,
            "active_exit_node": active_node_name or ("None" if not exit_node_active else exit_node_target),
            "exit_node_active": exit_node_active
        },
        "network_metrics": {
            "dallas_server_ip": DALLAS_IP,
            "latency_ms": latency_ms,
            "packet_loss_pct": packet_loss,
            "ping_healthy": ping_ok,
            "public_ip": public_ip,
            "egress_location": location
        }
    }
    return status


def fix_gaming_stack(exit_node_target: str = DEFAULT_EXIT_NODE) -> dict:
    """
    Performs auto-remediation on any failing Doshie Gaming components.
    Uses passwordless sudo rules already authorized for doshie.
    """
    actions_taken = []
    lan_iface = get_default_lan_interface()

    # 1. IP Forwarding
    if not check_ip_forward():
        log_event("Auto-fix: Enabling IPv4 forwarding...", "WARN")
        ok, out = run_sudo(["sysctl", "-w", "net.ipv4.ip_forward=1"])
        if ok:
            actions_taken.append("Enabled net.ipv4.ip_forward=1")
            log_event("Successfully enabled IPv4 forwarding", "SUCCESS")
        else:
            actions_taken.append(f"Failed to enable ip_forward: {out}")
            log_event(f"Failed to enable IPv4 forwarding: {out}", "ERROR")

    # 2. LAN NAT Masquerade
    if not check_nat_rule(lan_iface):
        log_event(f"Auto-fix: Adding NAT MASQUERADE rule for {lan_iface}...", "WARN")
        ok, out = run_sudo(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", lan_iface, "-j", "MASQUERADE"])
        if ok:
            actions_taken.append(f"Added iptables MASQUERADE for {lan_iface}")
            log_event(f"Successfully added NAT MASQUERADE for {lan_iface}", "SUCCESS")
        else:
            actions_taken.append(f"Failed to add NAT for {lan_iface}: {out}")
            log_event(f"Failed to add NAT for {lan_iface}: {out}", "ERROR")

    # 3. Tailscale NAT Masquerade
    if not check_nat_rule("tailscale0"):
        log_event("Auto-fix: Adding NAT MASQUERADE rule for tailscale0...", "WARN")
        ok, out = run_sudo(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "tailscale0", "-j", "MASQUERADE"])
        if ok:
            actions_taken.append("Added iptables MASQUERADE for tailscale0")
            log_event("Successfully added NAT MASQUERADE for tailscale0", "SUCCESS")
        else:
            actions_taken.append(f"Failed to add NAT for tailscale0: {out}")
            log_event(f"Failed to add NAT for tailscale0: {out}", "ERROR")

    # 4. Tailscale Exit Node routing
    ts_ok, ts_data = check_tailscale_status()
    if not ts_ok:
        log_event("Auto-fix: Tailscale daemon unresponsive or restarting...", "WARN")
        run_sudo(["tailscale", "up", "--accept-routes"])
        time.sleep(2)
        ts_ok, ts_data = check_tailscale_status()

    exit_active, current_node = check_exit_node(ts_data, exit_node_target)
    if not exit_active:
        log_event(f"Auto-fix: Switching Tailscale exit node to {exit_node_target} (Dallas)...", "WARN")
        ok, out = run_sudo([
            "tailscale", "set",
            f"--exit-node={exit_node_target}",
            "--exit-node-allow-lan-access=true"
        ])
        if ok:
            actions_taken.append(f"Configured Tailscale exit node to {exit_node_target}")
            log_event(f"Successfully configured exit node to {exit_node_target}", "SUCCESS")
        else:
            actions_taken.append(f"Failed to configure exit node: {out}")
            log_event(f"Failed to configure exit node: {out}", "ERROR")

    # Re-inspect to confirm health after fixes
    time.sleep(1)
    status = inspect_gaming_status(exit_node_target)
    status["actions_taken"] = actions_taken
    save_status(status)
    return status


def save_status(status: dict):
    """Persists status dictionary to json file for Doshie web & agents."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = DATA_DIR / ".doshie_gaming_status.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, STATUS_FILE)
    except Exception as e:
        log_event(f"Error saving status json: {e}", "ERROR")


def load_status() -> dict | None:
    """Reads latest saved status."""
    try:
        if STATUS_FILE.exists():
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def run_daemon_loop(interval: int = CHECK_INTERVAL_SECONDS, exit_node_target: str = DEFAULT_EXIT_NODE):
    """Continuous monitoring and auto-fix loop."""
    log_event(f"Doshie Gaming Monitor Daemon started. Polling every {interval}s. Target exit node: {exit_node_target}")
    while True:
        try:
            status = inspect_gaming_status(exit_node_target)
            save_status(status)

            if not status["healthy"]:
                log_event("Health check FAILED. Initiating auto-repair...", "WARN")
                fixed_status = fix_gaming_stack(exit_node_target)
                if fixed_status["healthy"]:
                    log_event("Auto-repair completed: All Doshie Gaming systems restored to optimal state.", "SUCCESS")
                else:
                    log_event(f"Auto-repair partial. Current status: healthy={fixed_status['healthy']}", "WARN")
            else:
                gw = status["gateway_status"]
                ts = status["tailscale_status"]
                net = status["network_metrics"]
                log_event(
                    f"Health OK | Gateway NAT: {gw['active']} | Exit Node: {ts['active_exit_node']} | "
                    f"Dallas Ping: {net['latency_ms']}ms | IP: {net['public_ip']}"
                )
        except Exception as e:
            log_event(f"Unexpected error in monitor loop: {e}", "ERROR")

        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Doshie Gaming Status Monitor & Auto-Repair Daemon")
    parser.add_argument("action", choices=["status", "fix", "daemon"], default="status", nargs="?",
                        help="Action to perform: status (check), fix (repair now), daemon (run monitor service)")
    parser.add_argument("--json", action="store_true", help="Output status in JSON format")
    parser.add_argument("--exit-node", default=DEFAULT_EXIT_NODE, help="Target Tailscale exit node (default: vultr)")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL_SECONDS, help="Check interval in seconds for daemon")

    args = parser.parse_args()

    if args.action == "status":
        status = inspect_gaming_status(args.exit_node)
        save_status(status)
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            gw = status["gateway_status"]
            ts = status["tailscale_status"]
            net = status["network_metrics"]
            health_badge = "🟢 OPTIMAL / HEALTHY" if status["healthy"] else "🔴 DEGRADED / ATTENTION NEEDED"
            print("=" * 60)
            print(f"🎮 DOSHIE GAMING STATUS: {health_badge}")
            print("=" * 60)
            print(f"LAN Interface:      {status['lan_interface']} (IP: {status['lan_ip']})")
            print(f"IP Forwarding:      {'Active' if gw['ip_forward'] else 'Inactive'}")
            print(f"LAN NAT Masquerade: {'Active' if gw['nat_lan_rule'] else 'Inactive'}")
            print(f"Tailscale NAT:      {'Active' if gw['nat_tailscale_rule'] else 'Inactive'}")
            print("-" * 60)
            print(f"Tailscale Online:   {'Yes' if ts['service_online'] else 'No'}")
            print(f"Active Exit Node:   {ts['active_exit_node']} (Target: {ts['target_exit_node']})")
            print(f"Exit Node Active:   {'Yes' if ts['exit_node_active'] else 'No'}")
            print("-" * 60)
            print(f"Dallas Server Ping: {net['latency_ms']} ms ({net['packet_loss_pct']}% loss)")
            print(f"Public Egress IP:   {net['public_ip']}")
            print(f"Egress Location:    {net['egress_location']}")
            print("=" * 60)

    elif args.action == "fix":
        print("🛠️ Initiating Doshie Gaming self-healing repair pipeline...")
        status = fix_gaming_stack(args.exit_node)
        actions = status.get("actions_taken", [])
        if actions:
            print("Actions executed:")
            for a in actions:
                print(f" • {a}")
        else:
            print("No repair actions required; system is already optimal.")
        print(f"Result: {'🟢 Healthy' if status['healthy'] else '⚠️ Some checks still failing'}")
        if args.json:
            print(json.dumps(status, indent=2))

    elif args.action == "daemon":
        run_daemon_loop(args.interval, args.exit_node)


if __name__ == "__main__":
    main()
