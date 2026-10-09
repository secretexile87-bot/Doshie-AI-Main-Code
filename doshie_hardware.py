#!/usr/bin/env python3
"""
doshie_hardware.py - Comprehensive Hardware Inspection and Command-Gated Control Module for Doshie
Designed for Acer Nitro / Linux systems.

Provides:
1. Deep hardware inspection across all hardware subsystems:
   - CPU, GPU, Memory, Storage/Disks, Thermals, Motherboard/BIOS, Network, PCI, USB.
2. Safe, command-gated hardware parameter modification:
   - CPU governors (powersave, performance, schedutil)
   - GPU power limits, persistence mode, compute mode (via nvidia-smi)
   - Pre-configured hardware profiles (powersave, balanced, performance, gaming)
3. Supervised-Until-Self-Reasoning Governance:
   - Enforces explicit user command confirmation while Doshie is in supervised mode.
   - Protects system with safety bounds (thermal thresholds, power wattage limits).
   - Keeps persistent audit log of all changes.
   - Provides a clean readiness transition path for future self-reasoning autonomy.
"""

import os
import sys
import glob
import json
import time
import shutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime, timezone

try:
    import psutil
except ImportError:
    psutil = None

# Base directories
DOSHIE_DIR = Path("/home/doshie/Doshie")
CONFIG_DIR = Path.home() / ".doshie"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
GOVERNANCE_FILE = CONFIG_DIR / "hardware_governance.json"
AUDIT_LOG_FILE = CONFIG_DIR / "hardware_audit.log"

DEFAULT_GOVERNANCE = {
    "version": "1.0.0",
    "mode": "supervised",  # "supervised" (current) or "self_reasoning" (future)
    "self_reasoning_capable": False,  # False until autonomous multi-step planning is validated
    "require_user_confirmation": True,
    "last_updated": datetime.now(timezone.utc).isoformat(),
    "safety_bounds": {
        "gpu_min_power_w": 100,
        "gpu_max_power_w": 250,
        "max_gpu_temp_c": 85,
        "max_cpu_temp_c": 90,
        "allowed_cpu_governors": ["powersave", "performance", "schedutil", "ondemand"],
        "allowed_profiles": ["powersave", "balanced", "performance", "gaming"]
    },
    "history_count": 0
}


def load_governance():
    """Load or initialize hardware governance configuration."""
    if not GOVERNANCE_FILE.exists():
        save_governance(DEFAULT_GOVERNANCE)
        return DEFAULT_GOVERNANCE
    try:
        with open(GOVERNANCE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure keys exist
            for k, v in DEFAULT_GOVERNANCE.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return DEFAULT_GOVERNANCE


def save_governance(data):
    """Save governance state to disk."""
    try:
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(GOVERNANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Warning] Failed to save governance config: {e}", file=sys.stderr)


def log_audit(action, target, value, status, actor="user", reason="", details=None):
    """Log hardware modification or command to persistent audit log."""
    gov = load_governance()
    gov["history_count"] = gov.get("history_count", 0) + 1
    save_governance(gov)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "target": target,
        "value": value,
        "status": status,
        "actor": actor,
        "reason": reason,
        "governance_mode": gov.get("mode", "supervised"),
        "self_reasoning_capable": gov.get("self_reasoning_capable", False),
        "details": details or {}
    }
    try:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[Warning] Failed to write audit log: {e}", file=sys.stderr)


# ==============================================================================
# 1. HARDWARE INSPECTION ENGINE
# ==============================================================================

def inspect_cpu():
    """Detailed CPU telemetry, core topology, governors, and frequencies."""
    info = {
        "model": "Unknown CPU",
        "architecture": platform.machine(),
        "logical_cores": os.cpu_count() or 1,
        "physical_cores": None,
        "current_governor": None,
        "available_governors": [],
        "min_freq_mhz": None,
        "max_freq_mhz": None,
        "current_freq_mhz": None,
        "utilization_percent": None,
        "per_core_utilization": []
    }

    if psutil:
        try:
            info["physical_cores"] = psutil.cpu_count(logical=False)
            freq = psutil.cpu_freq()
            if freq:
                info["current_freq_mhz"] = round(freq.current, 1)
                info["min_freq_mhz"] = round(freq.min, 1)
                info["max_freq_mhz"] = round(freq.max, 1)
            info["utilization_percent"] = round(psutil.cpu_percent(interval=0.1), 1)
            info["per_core_utilization"] = [round(x, 1) for x in psutil.cpu_percent(interval=None, percpu=True)]
        except Exception:
            pass

    # Read from /sys/devices/system/cpu/cpu0/cpufreq
    gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    if os.path.exists(gov_file):
        try:
            with open(gov_file) as f:
                info["current_governor"] = f.read().strip()
        except Exception:
            pass

    avail_gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors"
    if os.path.exists(avail_gov_file):
        try:
            with open(avail_gov_file) as f:
                info["available_governors"] = f.read().strip().split()
        except Exception:
            pass

    # lscpu fallback for exact model
    try:
        p = subprocess.run(["lscpu", "-J"], capture_output=True, text=True, timeout=2)
        if p.returncode == 0:
            data = json.loads(p.stdout)
            for item in data.get("lscpu", []):
                field = item.get("field", "").rstrip(":")
                val = item.get("data", "")
                if field == "Model name":
                    info["model"] = val
                elif field == "CPU max MHz" and not info["max_freq_mhz"]:
                    try:
                        info["max_freq_mhz"] = round(float(val), 1)
                    except ValueError:
                        pass
                elif field == "CPU min MHz" and not info["min_freq_mhz"]:
                    try:
                        info["min_freq_mhz"] = round(float(val), 1)
                    except ValueError:
                        pass
    except Exception:
        pass

    return info


def inspect_gpu():
    """Inspect NVIDIA GPU (RTX 5070 / GeForce) telemetry and power limits."""
    res = {
        "available": False,
        "name": "NVIDIA GPU Unavailable",
        "driver_version": None,
        "temperature_c": None,
        "memory_used_mb": 0,
        "memory_total_mb": 0,
        "memory_free_mb": 0,
        "memory_percent": 0.0,
        "utilization_gpu_percent": 0,
        "power_draw_w": 0.0,
        "power_limit_w": 0.0,
        "power_min_limit_w": None,
        "power_max_limit_w": None,
        "fan_speed_percent": 0,
        "persistence_mode": None,
        "compute_mode": None
    }

    if not shutil.which("nvidia-smi"):
        return res

    fields = "name,driver_version,temperature.gpu,memory.used,memory.total,memory.free,utilization.gpu,power.draw,power.limit,fan.speed,persistence_mode,compute_mode"
    try:
        cmd = ["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if p.returncode == 0 and p.stdout.strip():
            parts = [x.strip() for x in p.stdout.strip().split(",")]
            res["available"] = True
            res["name"] = parts[0]
            res["driver_version"] = parts[1]
            res["temperature_c"] = int(float(parts[2])) if parts[2] != "[N/A]" else None
            res["memory_used_mb"] = int(float(parts[3])) if parts[3] != "[N/A]" else 0
            res["memory_total_mb"] = int(float(parts[4])) if parts[4] != "[N/A]" else 0
            res["memory_free_mb"] = int(float(parts[5])) if parts[5] != "[N/A]" else 0
            if res["memory_total_mb"] > 0:
                res["memory_percent"] = round((res["memory_used_mb"] / res["memory_total_mb"]) * 100, 1)
            res["utilization_gpu_percent"] = int(float(parts[6])) if parts[6] != "[N/A]" else 0
            res["power_draw_w"] = round(float(parts[7]), 1) if parts[7] != "[N/A]" else 0.0
            res["power_limit_w"] = round(float(parts[8]), 1) if parts[8] != "[N/A]" else 0.0
            res["fan_speed_percent"] = int(float(parts[9])) if parts[9] != "[N/A]" else 0
            res["persistence_mode"] = parts[10] if len(parts) > 10 and parts[10] != "[N/A]" else None
            res["compute_mode"] = parts[11] if len(parts) > 11 and parts[11] != "[N/A]" else None
    except Exception as e:
        res["error"] = str(e)

    # Attempt to query min/max power limit bounds
    try:
        p_bounds = subprocess.run(["nvidia-smi", "-q", "-d", "POWER"], capture_output=True, text=True, timeout=3)
        if p_bounds.returncode == 0:
            for line in p_bounds.stdout.splitlines():
                line = line.strip()
                if "Min Power Limit" in line:
                    res["power_min_limit_w"] = float(line.split(":")[1].replace("W", "").strip())
                elif "Max Power Limit" in line:
                    res["power_max_limit_w"] = float(line.split(":")[1].replace("W", "").strip())
    except Exception:
        pass

    return res


def inspect_memory():
    """Inspect Host RAM, Caching, and Swap space."""
    data = {
        "ram_total_gb": 0.0,
        "ram_used_gb": 0.0,
        "ram_available_gb": 0.0,
        "ram_percent": 0.0,
        "swap_total_gb": 0.0,
        "swap_used_gb": 0.0,
        "swap_percent": 0.0,
        "cached_gb": 0.0,
        "buffers_gb": 0.0
    }
    if psutil:
        try:
            vm = psutil.virtual_memory()
            sw = psutil.swap_memory()
            data["ram_total_gb"] = round(vm.total / (1024 ** 3), 2)
            data["ram_used_gb"] = round(vm.used / (1024 ** 3), 2)
            data["ram_available_gb"] = round(vm.available / (1024 ** 3), 2)
            data["ram_percent"] = round(vm.percent, 1)
            data["cached_gb"] = round(getattr(vm, "cached", 0) / (1024 ** 3), 2)
            data["buffers_gb"] = round(getattr(vm, "buffers", 0) / (1024 ** 3), 2)
            data["swap_total_gb"] = round(sw.total / (1024 ** 3), 2)
            data["swap_used_gb"] = round(sw.used / (1024 ** 3), 2)
            data["swap_percent"] = round(sw.percent, 1)
            return data
        except Exception:
            pass

    # /proc/meminfo fallback
    try:
        with open("/proc/meminfo") as f:
            mem = dict(line.split(":", 1) for line in f if ":" in line)
            total_kb = float(mem.get("MemTotal", "0 kB").split()[0])
            avail_kb = float(mem.get("MemAvailable", "0 kB").split()[0])
            cached_kb = float(mem.get("Cached", "0 kB").split()[0])
            swap_total_kb = float(mem.get("SwapTotal", "0 kB").split()[0])
            swap_free_kb = float(mem.get("SwapFree", "0 kB").split()[0])

            data["ram_total_gb"] = round(total_kb / (1024 ** 2), 2)
            data["ram_available_gb"] = round(avail_kb / (1024 ** 2), 2)
            data["ram_used_gb"] = round((total_kb - avail_kb) / (1024 ** 2), 2)
            data["ram_percent"] = round(((total_kb - avail_kb) / total_kb) * 100, 1) if total_kb else 0.0
            data["cached_gb"] = round(cached_kb / (1024 ** 2), 2)
            data["swap_total_gb"] = round(swap_total_kb / (1024 ** 2), 2)
            data["swap_used_gb"] = round((swap_total_kb - swap_free_kb) / (1024 ** 2), 2)
            data["swap_percent"] = round(((swap_total_kb - swap_free_kb) / swap_total_kb) * 100, 1) if swap_total_kb else 0.0
    except Exception:
        pass

    return data


def inspect_storage():
    """Inspect block storage devices, NVMe, USB disks, and partition mount points."""
    result = {
        "root_disk": {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0.0},
        "devices": []
    }

    if psutil:
        try:
            r = psutil.disk_usage("/")
            result["root_disk"] = {
                "total_gb": round(r.total / (1024 ** 3), 1),
                "used_gb": round(r.used / (1024 ** 3), 1),
                "free_gb": round(r.free / (1024 ** 3), 1),
                "percent": round(r.percent, 1)
            }
        except Exception:
            pass

    try:
        p = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL,TRAN,ROTA"],
            capture_output=True, text=True, timeout=3
        )
        if p.returncode == 0:
            raw = json.loads(p.stdout).get("blockdevices", [])
            for d in raw:
                # filter out loop devices
                if d.get("type") == "loop":
                    continue
                dev_info = {
                    "name": d.get("name"),
                    "size": d.get("size"),
                    "type": d.get("type"),
                    "model": d.get("model"),
                    "transport": d.get("tran"),
                    "rotational": bool(d.get("rota")),
                    "partitions": []
                }
                for c in d.get("children", []):
                    dev_info["partitions"].append({
                        "name": c.get("name"),
                        "size": c.get("size"),
                        "mountpoint": c.get("mountpoint"),
                        "fstype": c.get("fstype")
                    })
                result["devices"].append(dev_info)
    except Exception as e:
        result["error"] = str(e)

    return result


def inspect_thermals():
    """Inspect thermal zones (CPU package, ACPI, PCI) and fan sensors."""
    zones = []
    for tz in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
        try:
            type_f = os.path.join(tz, "type")
            temp_f = os.path.join(tz, "temp")
            tz_type = open(type_f).read().strip() if os.path.exists(type_f) else "unknown"
            tz_val = int(open(temp_f).read().strip()) if os.path.exists(temp_f) else 0
            temp_c = round(tz_val / 1000.0, 1)
            zones.append({
                "zone": os.path.basename(tz),
                "type": tz_type,
                "temperature_c": temp_c,
                "status": "critical" if temp_c >= 85 else ("warning" if temp_c >= 75 else "normal")
            })
        except Exception:
            pass

    gpu_telemetry = inspect_gpu()
    gpu_temp = gpu_telemetry.get("temperature_c") if gpu_telemetry.get("available") else None

    return {
        "thermal_zones": zones,
        "gpu_temperature_c": gpu_temp,
        "gpu_status": "critical" if (gpu_temp and gpu_temp >= 85) else ("warning" if (gpu_temp and gpu_temp >= 75) else "normal")
    }


def inspect_motherboard():
    """Inspect DMI/SMBIOS information: Vendor, Product, Board, BIOS version."""
    dmi = {
        "system_vendor": None,
        "product_name": None,
        "product_family": None,
        "sku": None,
        "board_vendor": None,
        "board_name": None,
        "bios_vendor": None,
        "bios_version": None,
        "bios_date": None
    }
    dmi_path = "/sys/class/dmi/id"
    if os.path.exists(dmi_path):
        fields = {
            "sys_vendor": "system_vendor",
            "product_name": "product_name",
            "product_family": "product_family",
            "product_sku": "sku",
            "board_vendor": "board_vendor",
            "board_name": "board_name",
            "bios_vendor": "bios_vendor",
            "bios_version": "bios_version",
            "bios_date": "bios_date"
        }
        for file_key, dmi_key in fields.items():
            fpath = os.path.join(dmi_path, file_key)
            if os.path.isfile(fpath):
                try:
                    dmi[dmi_key] = open(fpath).read().strip()
                except Exception:
                    pass
    return dmi


def inspect_network():
    """Inspect network interfaces, states, and addresses."""
    interfaces = []
    try:
        p = subprocess.run(["ip", "-j", "addr"], capture_output=True, text=True, timeout=3)
        if p.returncode == 0:
            for iface in json.loads(p.stdout):
                name = iface.get("ifname")
                state = iface.get("operstate")
                addrs = [a.get("local") for a in iface.get("addr_info", []) if a.get("local")]
                mac = iface.get("address")
                interfaces.append({
                    "name": name,
                    "state": state,
                    "mac": mac,
                    "addresses": addrs,
                    "is_up": state == "UP"
                })
    except Exception:
        pass
    return interfaces


def inspect_pci():
    """Inspect PCI devices (GPUs, controllers, bridges)."""
    devices = []
    if shutil.which("lspci"):
        try:
            p = subprocess.run(["lspci"], capture_output=True, text=True, timeout=3)
            if p.returncode == 0:
                for line in p.stdout.splitlines():
                    if line.strip():
                        parts = line.strip().split(" ", 1)
                        devices.append({
                            "slot": parts[0],
                            "description": parts[1] if len(parts) > 1 else ""
                        })
        except Exception:
            pass
    return devices


def inspect_usb():
    """Inspect connected USB peripherals."""
    devices = []
    if shutil.which("lsusb"):
        try:
            p = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=3)
            if p.returncode == 0:
                for line in p.stdout.splitlines():
                    if line.strip():
                        devices.append(line.strip())
        except Exception:
            pass
    return devices


def inspect_all():
    """Aggregate complete hardware snapshot."""
    gov = load_governance()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "governance": {
            "mode": gov.get("mode", "supervised"),
            "self_reasoning_capable": gov.get("self_reasoning_capable", False),
            "require_user_confirmation": gov.get("require_user_confirmation", True)
        },
        "motherboard": inspect_motherboard(),
        "cpu": inspect_cpu(),
        "gpu": inspect_gpu(),
        "memory": inspect_memory(),
        "storage": inspect_storage(),
        "thermals": inspect_thermals(),
        "network": inspect_network(),
        "pci_count": len(inspect_pci()),
        "usb_count": len(inspect_usb())
    }


# ==============================================================================
# 2. COMMAND-GATED HARDWARE MODIFICATION ENGINE
# ==============================================================================

def _check_thermal_safety():
    """Verify that current system temperatures allow safe tuning."""
    thermals = inspect_thermals()
    gov = load_governance()
    max_gpu = gov["safety_bounds"]["max_gpu_temp_c"]
    max_cpu = gov["safety_bounds"]["max_cpu_temp_c"]

    gpu_temp = thermals.get("gpu_temperature_c")
    if gpu_temp and gpu_temp > max_gpu:
        return False, f"GPU temperature ({gpu_temp}°C) exceeds safety limit ({max_gpu}°C). Tuning aborted."

    for z in thermals.get("thermal_zones", []):
        if z.get("temperature_c", 0) > max_cpu:
            return False, f"CPU thermal zone '{z.get('type')}' ({z.get('temperature_c')}°C) exceeds safety limit ({max_cpu}°C). Tuning aborted."

    return True, "Thermal levels normal."


def propose_change(target, value, reason="User command"):
    """
    Generate a staged hardware change proposal with impact assessment and safety validation.
    Returns impact proposal without executing until confirmed by user command.
    """
    gov = load_governance()
    safe, thermal_msg = _check_thermal_safety()
    if not safe:
        return {
            "success": False,
            "status": "rejected_unsafe_thermals",
            "error": thermal_msg
        }

    target = target.lower().strip()
    proposal = {
        "target": target,
        "requested_value": value,
        "reason": reason,
        "governance_mode": gov.get("mode", "supervised"),
        "self_reasoning_capable": gov.get("self_reasoning_capable", False),
        "requires_user_confirmation": True,
        "command_to_run": None,
        "current_value": None,
        "impact_analysis": "",
        "safety_verified": True
    }

    if target in ("cpu_governor", "governor"):
        allowed = gov["safety_bounds"]["allowed_cpu_governors"]
        val = str(value).lower().strip()
        if val not in allowed:
            return {"success": False, "error": f"Governor '{val}' not in allowed list: {allowed}"}

        cpu_info = inspect_cpu()
        proposal["current_value"] = cpu_info.get("current_governor")
        proposal["command_to_run"] = f"sudo cpupower frequency-set -g {val}"
        proposal["impact_analysis"] = (
            f"Changes CPU scaling governor from '{proposal['current_value']}' to '{val}'. "
            f"If 'performance', locks CPU at maximum clock frequencies (higher power/thermals). "
            f"If 'powersave', lowers base clock when idle."
        )

    elif target in ("gpu_power_limit", "gpu_power"):
        try:
            watts = int(float(value))
        except ValueError:
            return {"success": False, "error": f"Invalid GPU power wattage: {value}"}

        bounds = gov["safety_bounds"]
        if watts < bounds["gpu_min_power_w"] or watts > bounds["gpu_max_power_w"]:
            return {
                "success": False,
                "error": f"Wattage {watts}W is outside safe boundary ({bounds['gpu_min_power_w']}W - {bounds['gpu_max_power_w']}W)."
            }

        gpu_info = inspect_gpu()
        proposal["current_value"] = f"{gpu_info.get('power_limit_w')}W"
        proposal["command_to_run"] = f"sudo nvidia-smi -pl {watts}"
        proposal["impact_analysis"] = (
            f"Adjusts NVIDIA RTX 5070 power ceiling to {watts}W. "
            f"Higher limit allows sustained boost clocks during AI inference/gaming."
        )

    elif target in ("gpu_persistence_mode", "gpu_persistence"):
        flag = "1" if str(value).lower() in ("1", "true", "on", "enable") else "0"
        gpu_info = inspect_gpu()
        proposal["current_value"] = gpu_info.get("persistence_mode")
        proposal["command_to_run"] = f"sudo nvidia-smi -pm {flag}"
        proposal["impact_analysis"] = f"Sets GPU persistence mode to {flag} (keeps NVIDIA driver loaded for low-latency AI inference)."

    elif target in ("profile", "system_profile"):
        profile = str(value).lower().strip()
        allowed = gov["safety_bounds"]["allowed_profiles"]
        if profile not in allowed:
            return {"success": False, "error": f"Profile '{profile}' not recognized. Allowed: {allowed}"}

        if profile == "performance":
            proposal["command_to_run"] = "sudo cpupower frequency-set -g performance && sudo nvidia-smi -pm 1 && sudo nvidia-smi -pl 250"
            proposal["impact_analysis"] = "Max performance preset: CPU performance governor, GPU persistence ON, GPU power limit 250W."
        elif profile == "powersave":
            proposal["command_to_run"] = "sudo cpupower frequency-set -g powersave && sudo nvidia-smi -pl 180"
            proposal["impact_analysis"] = "Eco/Quiet preset: CPU powersave governor, reduced GPU power limit (180W)."
        elif profile == "balanced":
            proposal["command_to_run"] = "sudo cpupower frequency-set -g powersave && sudo nvidia-smi -pl 220"
            proposal["impact_analysis"] = "Balanced preset: CPU powersave governor, standard GPU power (220W)."
        elif profile == "gaming":
            proposal["command_to_run"] = "sudo cpupower frequency-set -g performance && sudo nvidia-smi -pm 1 && sudo nvidia-smi -pl 250"
            proposal["impact_analysis"] = "High frame rate gaming preset: CPU performance governor, full GPU power limit (250W)."

    else:
        return {"success": False, "error": f"Unsupported hardware target: '{target}'."}

    return {"success": True, "proposal": proposal}


def execute_change(target, value, confirmed=False, actor="user", reason="User command"):
    """
    Execute hardware setting change.
    In 'supervised' mode, requires confirmed=True (explicit user command confirmation).
    """
    gov = load_governance()
    prep = propose_change(target, value, reason=reason)
    if not prep.get("success"):
        log_audit("modify", target, value, "failed", actor=actor, reason=reason, details={"error": prep.get("error")})
        return prep

    proposal = prep["proposal"]

    # Supervised Guardrail check:
    # If self_reasoning_capable is False, Doshie is strictly supervised and requires user confirmation
    if not gov.get("self_reasoning_capable", False):
        if not confirmed:
            log_audit("modify_proposed", target, value, "awaiting_user_confirmation", actor=actor, reason=reason, details=proposal)
            return {
                "success": False,
                "status": "awaiting_confirmation",
                "message": (
                    "Doshie is operating in SUPERVISED MODE (self-reasoning autonomy disabled). "
                    "Hardware modification requires your explicit command confirmation."
                ),
                "proposal": proposal
            }

    # Execute approved command
    cmd = proposal["command_to_run"]
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            log_audit("modify", target, value, "applied", actor=actor, reason=reason, details={"output": res.stdout.strip()})
            return {
                "success": True,
                "status": "applied",
                "target": target,
                "applied_value": value,
                "stdout": res.stdout.strip(),
                "governance": "supervised_command_confirmed"
            }
        else:
            err = res.stderr.strip() or res.stdout.strip()
            log_audit("modify", target, value, "command_error", actor=actor, reason=reason, details={"error": err})
            return {
                "success": False,
                "status": "command_failed",
                "error": err,
                "note": "Root/sudo privileges required to modify hardware registers."
            }
    except Exception as exc:
        log_audit("modify", target, value, "exception", actor=actor, reason=reason, details={"exception": str(exc)})
        return {"success": False, "error": str(exc)}


def set_governance_mode(mode=None, self_reasoning_capable=None):
    """Update supervisory or reasoning mode settings."""
    gov = load_governance()
    if mode in ("supervised", "self_reasoning"):
        gov["mode"] = mode
    if self_reasoning_capable is not None:
        gov["self_reasoning_capable"] = bool(self_reasoning_capable)
    save_governance(gov)
    return gov


# ==============================================================================
# 3. CLI INTERFACE FOR DOSHIE
# ==============================================================================

def cli_main():
    """Entrypoint for `doshie hardware` CLI commands."""
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print("==================================================")
        print("  ⚡ DOSHIE HARDWARE INSPECTOR & COMMAND CONTROL")
        print("==================================================")
        print("Usage:")
        print("  doshie hw inspect [all|cpu|gpu|ram|disk|thermals|motherboard|network|pci|usb]")
        print("  doshie hw set <target> <value> [--confirm]")
        print("  doshie hw profile <performance|powersave|balanced|gaming> [--confirm]")
        print("  doshie hw governance [status|set-reasoning]")
        print("  doshie hw audit [limit]")
        print("")
        print("Supervisory Safety Notice:")
        print("  Doshie operates under supervised command governance.")
        print("  Hardware changes only execute upon your explicit command confirmation,")
        print("  preserving safety until autonomous self-reasoning is achieved.")
        print("==================================================")
        return

    subcmd = args[0].lower()

    if subcmd in ("inspect", "status", "info"):
        comp = args[1].lower() if len(args) > 1 else "summary"
        if comp in ("all", "full"):
            print(json.dumps(inspect_all(), indent=2))
        elif comp == "cpu":
            print(json.dumps(inspect_cpu(), indent=2))
        elif comp == "gpu":
            print(json.dumps(inspect_gpu(), indent=2))
        elif comp in ("ram", "memory"):
            print(json.dumps(inspect_memory(), indent=2))
        elif comp in ("disk", "storage"):
            print(json.dumps(inspect_storage(), indent=2))
        elif comp in ("thermals", "temp", "thermal"):
            print(json.dumps(inspect_thermals(), indent=2))
        elif comp in ("motherboard", "board", "dmi"):
            print(json.dumps(inspect_motherboard(), indent=2))
        elif comp in ("net", "network"):
            print(json.dumps(inspect_network(), indent=2))
        elif comp == "pci":
            print(json.dumps(inspect_pci(), indent=2))
        elif comp == "usb":
            print(json.dumps(inspect_usb(), indent=2))
        else:
            # Default rich summary
            snap = inspect_all()
            print("==================================================")
            print("  💻 DOSHIE HARDWARE DASHBOARD — ACER NITRO")
            print("==================================================")
            print(f"System:        {snap['motherboard']['system_vendor']} {snap['motherboard']['product_name']} ({snap['motherboard']['board_name']})")
            print(f"BIOS:          {snap['motherboard']['bios_version']} ({snap['motherboard']['bios_date']})")
            print(f"CPU:           {snap['cpu']['model']}")
            print(f"  - Cores:     {snap['cpu']['logical_cores']} threads | Load: {snap['cpu']['utilization_percent']}%")
            print(f"  - Governor:  {snap['cpu']['current_governor']} (avail: {', '.join(snap['cpu']['available_governors'])})")
            print(f"GPU:           {snap['gpu']['name']}")
            print(f"  - Driver:    {snap['gpu']['driver_version']} | VRAM: {snap['gpu']['memory_used_mb']}/{snap['gpu']['memory_total_mb']} MB ({snap['gpu']['memory_percent']}%)")
            print(f"  - Power:     {snap['gpu']['power_draw_w']}W / {snap['gpu']['power_limit_w']}W | Temp: {snap['gpu']['temperature_c']}°C")
            print(f"Memory:        {snap['memory']['ram_used_gb']} GB / {snap['memory']['ram_total_gb']} GB ({snap['memory']['ram_percent']}%) | Free: {snap['memory']['ram_available_gb']} GB")
            print(f"Root Disk:     {snap['storage']['root_disk']['used_gb']} GB / {snap['storage']['root_disk']['total_gb']} GB ({snap['storage']['root_disk']['percent']}%)")
            print(f"Thermals:      GPU {snap['thermals']['gpu_temperature_c']}°C | Zones: {len(snap['thermals']['thermal_zones'])}")
            print(f"Governance:    Mode: {snap['governance']['mode'].upper()} | Self-Reasoning: {'ENABLED' if snap['governance']['self_reasoning_capable'] else 'PENDING (Supervised)'}")
            print("==================================================")

    elif subcmd == "set":
        if len(args) < 3:
            print("Error: Missing target or value. Usage: doshie hw set <target> <value> [--confirm]")
            sys.exit(1)
        target = args[1]
        value = args[2]
        confirmed = "--confirm" in args or "-y" in args or "--yes" in args

        if not confirmed:
            prep = propose_change(target, value)
            if not prep.get("success"):
                print(f"❌ Safety check failed: {prep.get('error')}")
                sys.exit(1)
            p = prep["proposal"]
            print("==================================================")
            print("  ⚠️  STAGED HARDWARE CHANGE (SUPERVISED MODE)")
            print("==================================================")
            print(f"Target:          {p['target']}")
            print(f"Current Value:   {p['current_value']}")
            print(f"Requested Value: {p['requested_value']}")
            print(f"Impact:          {p['impact_analysis']}")
            print(f"Command:         {p['command_to_run']}")
            print("--------------------------------------------------")
            ans = input("Execute this change with your command? [y/N]: ").strip().lower()
            if ans in ("y", "yes"):
                confirmed = True
            else:
                print("Aborted by user.")
                sys.exit(0)

        result = execute_change(target, value, confirmed=True)
        if result.get("success"):
            print(f"✅ Success! Applied {target} = {value}.")
        else:
            print(f"❌ Failed: {result.get('error') or result.get('message')}")

    elif subcmd == "profile":
        if len(args) < 2:
            print("Error: Specify profile (performance, powersave, balanced, gaming).")
            sys.exit(1)
        profile_name = args[1]
        confirmed = "--confirm" in args or "-y" in args or "--yes" in args
        if not confirmed:
            prep = propose_change("profile", profile_name)
            if not prep.get("success"):
                print(f"❌ Safety check failed: {prep.get('error')}")
                sys.exit(1)
            p = prep["proposal"]
            print("==================================================")
            print(f"  ⚡ SWITCH SYSTEM HARDWARE PROFILE: {profile_name.upper()}")
            print("==================================================")
            print(f"Impact:  {p['impact_analysis']}")
            print(f"Command: {p['command_to_run']}")
            ans = input("Confirm profile activation? [y/N]: ").strip().lower()
            if ans in ("y", "yes"):
                confirmed = True
            else:
                print("Aborted.")
                sys.exit(0)
        res = execute_change("profile", profile_name, confirmed=True)
        if res.get("success"):
            print(f"✅ Successfully activated '{profile_name}' hardware profile!")
        else:
            print(f"❌ Failed: {res.get('error') or res.get('message')}")

    elif subcmd == "governance":
        action = args[1] if len(args) > 1 else "status"
        if action == "status":
            gov = load_governance()
            print("==================================================")
            print("  🛡️  DOSHIE HARDWARE GOVERNANCE STATE")
            print("==================================================")
            print(f"Mode:                   {gov.get('mode')}")
            print(f"Self-Reasoning Capable: {gov.get('self_reasoning_capable')}")
            print(f"User Confirmation Req:  {gov.get('require_user_confirmation')}")
            print(f"Audit Entries Logged:   {gov.get('history_count', 0)}")
            print("Safety Thresholds:")
            print(f"  - Max GPU Temp:       {gov['safety_bounds']['max_gpu_temp_c']}°C")
            print(f"  - Max CPU Temp:       {gov['safety_bounds']['max_cpu_temp_c']}°C")
            print(f"  - Safe GPU Power:     {gov['safety_bounds']['gpu_min_power_w']}W - {gov['safety_bounds']['gpu_max_power_w']}W")
            print("==================================================")
        elif action == "set-reasoning":
            flag = args[2].lower() in ("1", "true", "yes", "on") if len(args) > 2 else False
            gov = set_governance_mode(self_reasoning_capable=flag)
            print(f"Updated: self_reasoning_capable is now {gov['self_reasoning_capable']}")

    elif subcmd == "audit":
        limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        print(f"=== Last {limit} Hardware Audit Log Entries ===")
        if AUDIT_LOG_FILE.exists():
            with open(AUDIT_LOG_FILE) as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        e = json.loads(line)
                        print(f"[{e.get('timestamp')[:19]}] {e.get('action').upper()} {e.get('target')}={e.get('value')} -> {e.get('status')} (by {e.get('actor')})")
                    except Exception:
                        print(line.strip())
        else:
            print("No audit log entries yet.")
    else:
        print(f"Unknown hardware subcommand: {subcmd}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
