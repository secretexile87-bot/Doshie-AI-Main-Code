"""Persistent DiYoshi profile roles with private atomic storage."""
import json
import os
import re
import tempfile
import threading

BASE_DIR = os.path.expanduser(os.environ.get("YOSHI_DIR", "~/yoshi"))
ROLES_FILE = os.path.join(BASE_DIR, "profile_roles.json")
_LOCK = threading.RLock()
_ALLOWED = {"admin", "family", "child"}


class RoleError(RuntimeError):
    pass


def _key(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _default_role(legacy_role=""):
    if _key(legacy_role) in {"son", "daughter", "child", "kid"}:
        return "child"
    return "family"
def _load():
    if not os.path.exists(ROLES_FILE):
        return {"version": 1, "roles": {}}
    try:
        with open(ROLES_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        raise RoleError("Role settings could not be read.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("roles", {}), dict):
        raise RoleError("Role settings are invalid.")
    return data


def _save(data):
    os.makedirs(os.path.dirname(ROLES_FILE), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        prefix=".profile-roles-", dir=os.path.dirname(ROLES_FILE)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, ROLES_FILE)
        os.chmod(ROLES_FILE, 0o600)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def get_role(name, legacy_role=""):
    if _key(name) == "hermes":
        return "owner"
    with _LOCK:
        value = _load().get("roles", {}).get(_key(name))
    return value if value in _ALLOWED else _default_role(legacy_role)


def set_role(name, role):
    key = _key(name)
    clean_role = _key(role)
    if not key or key == "hermes":
        raise ValueError("The owner role cannot be changed.")
    if clean_role not in _ALLOWED:
        raise ValueError("Choose Admin, Family, or Child.")
    with _LOCK:
        data = _load()
        data.setdefault("roles", {})[key] = clean_role
        _save(data)
    return clean_role


def remove_role(name):
    key = _key(name)
    if not key or key == "hermes":
        return False
    with _LOCK:
        data = _load()
        removed = data.setdefault("roles", {}).pop(key, None)
        if removed is not None:
            _save(data)
    return removed is not None


def role_flags(name, legacy_role=""):
    role = get_role(name, legacy_role)
    return {
        "access_role": role,
        "is_admin": role in {"owner", "admin"},
        "is_child": role == "child",
    }


def state_valid():
    try:
        data = _load()
        return all(value in _ALLOWED for value in data.get("roles", {}).values())
    except RoleError:
        return False
