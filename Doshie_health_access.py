import json
import os
import tempfile
import threading
import time
from pathlib import Path

DATA_FILE = Path.home() / "yoshi" / "health_access.json"
AUDIT_FILE = Path.home() / "yoshi" / "health_access_audit.jsonl"
_LOCK = threading.RLock()

PERMISSIONS = (
    "activity",
    "heart",
    "sleep",
    "workouts",
    "body",
    "nutrition",
    "medications",
)


def _profile_key(profile):
    return " ".join(str(profile or "").split()).strip().casefold()


def _default_policy(profile):
    return {
        "profile": " ".join(str(profile or "").split()).strip(),
        "enabled": False,
        "permissions": [],
        "online_required": True,
        "updated_at": None,
    }

def _load_policies():
    if not DATA_FILE.exists():
        return {}
    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        profiles = payload.get("profiles", {})
        return profiles if isinstance(profiles, dict) else {}
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _save_policies(profiles):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"version": 1, "profiles": profiles}, indent=2) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=DATA_FILE.parent,
            prefix=f".{DATA_FILE.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, DATA_FILE)
        temporary = None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()

def _audit(profile, event, **details):
    record = {
        "time": int(time.time()),
        "profile": " ".join(str(profile or "").split()).strip(),
        "event": event,
        "details": details,
    }
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    try:
        os.chmod(AUDIT_FILE, 0o600)
    except OSError:
        pass


def get_policy(profile):
    key = _profile_key(profile)
    with _LOCK:
        saved = _load_policies().get(key)
    policy = _default_policy(profile)
    if isinstance(saved, dict):
        policy["enabled"] = bool(saved.get("enabled", False))
        policy["permissions"] = [
            item for item in saved.get("permissions", [])
            if item in PERMISSIONS
        ]
        policy["updated_at"] = saved.get("updated_at")
    return policy

def set_policy(profile, enabled, permissions=None):
    name = " ".join(str(profile or "").split()).strip()
    if not name:
        raise ValueError("Profile is required.")
    requested = permissions or []
    if not isinstance(requested, list):
        raise ValueError("Permissions must be a list.")
    clean = []
    for item in requested:
        value = str(item).strip().casefold()
        if value not in PERMISSIONS:
            raise ValueError(f"Unknown health permission: {value}")
        if value not in clean:
            clean.append(value)
    policy = {
        "profile": name,
        "enabled": bool(enabled),
        "permissions": clean if enabled else [],
        "online_required": True,
        "updated_at": int(time.time()),
    }
    key = _profile_key(name)
    with _LOCK:
        profiles = _load_policies()
        profiles[key] = policy
        _save_policies(profiles)
        _audit(name, "policy_updated", enabled=policy["enabled"], permissions=clean)
    return policy

def authorize(profile, online, unlocked):
    policy = get_policy(profile)
    reasons = []
    if not policy["enabled"]:
        reasons.append("consent_disabled")
    if policy["online_required"] and not bool(online):
        reasons.append("offline")
    if not bool(unlocked):
        reasons.append("profile_locked")
    return {
        **policy,
        "allowed": not reasons,
        "reasons": reasons,
    }


def record_sync_access(profile, categories, allowed):
    clean = [
        str(item).strip().casefold() for item in (categories or [])
        if str(item).strip().casefold() in PERMISSIONS
    ]
    with _LOCK:
        _audit(
            profile,
            "sync_access",
            allowed=bool(allowed),
            categories=sorted(set(clean)),
        )
