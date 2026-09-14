"""Portable, read-only equipment health for the DiYoshi control app."""

import os
import platform
import shutil
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None


def _percent_state(value, warning=80, critical=92):
    number = float(value or 0)
    if number >= critical:
        return "critical"
    if number >= warning:
        return "warning"
    return "healthy"


def _temperature():
    reader = getattr(psutil, "sensors_temperatures", None)
    if not callable(reader):
        return None
    try:
        readings = reader() or {}
    except Exception:
        return None
    values = []
    for entries in readings.values():
        for entry in entries or []:
            current = getattr(entry, "current", None)
            if isinstance(current, (int, float)) and 0 < current < 150:
                values.append(float(current))
    return round(max(values), 1) if values else None


def _battery():
    reader = getattr(psutil, "sensors_battery", None)
    if not callable(reader):
        return None
    try:
        battery = reader()
    except Exception:
        return None
    if battery is None:
        return None
    return {
        "percent": round(float(battery.percent), 1),
        "plugged_in": bool(battery.power_plugged),
        "seconds_left": int(battery.secsleft)
        if isinstance(battery.secsleft, (int, float)) and battery.secsleft >= 0
        else None,
    }
def snapshot():
    """Return portable host health without executing shell commands."""
    memory = psutil.virtual_memory()
    root = Path(os.path.abspath(os.sep))
    disk = psutil.disk_usage(str(root))
    cpu = psutil.cpu_percent(interval=0.2)
    temperature = _temperature()
    battery = _battery()
    alerts = []

    for label, value in (
        ("CPU load", cpu),
        ("Memory", memory.percent),
        ("Disk", disk.percent),
    ):
        state = _percent_state(value)
        if state != "healthy":
            alerts.append(f"{label} is {state} at {round(float(value), 1)}%.")

    if temperature is not None and temperature >= 85:
        alerts.append(f"Temperature is high at {temperature}°C.")
    if battery and battery["percent"] <= 15 and not battery["plugged_in"]:
        alerts.append(f"Battery is low at {battery['percent']}%.")

    return {
        "timestamp": int(time.time()),
        "hostname": platform.node(),
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor() or "Unknown processor",
        "cpu": {
            "percent": round(float(cpu), 1),
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "state": _percent_state(cpu),
        },
        "memory": {
            "percent": round(float(memory.percent), 1),
            "used_gb": round(memory.used / (1024 ** 3), 1),
            "total_gb": round(memory.total / (1024 ** 3), 1),
            "state": _percent_state(memory.percent),
        },
        "disk": {
            "percent": round(float(disk.percent), 1),
            "used_gb": round(disk.used / (1024 ** 3), 1),
            "total_gb": round(disk.total / (1024 ** 3), 1),
            "free_gb": round(disk.free / (1024 ** 3), 1),
            "state": _percent_state(disk.percent),
        },
        "temperature_c": temperature,
        "battery": battery,
        "uptime_seconds": max(0, int(time.time() - psutil.boot_time())),
        "network_interfaces": sorted(
            name for name, entries in psutil.net_if_addrs().items() if entries
        ),
        "alerts": alerts,
        "overall": "attention" if alerts else "healthy",
    }
