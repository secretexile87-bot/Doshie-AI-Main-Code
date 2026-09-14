import json
import os
import secrets
import tempfile
import threading
import time
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash


DATA_FILE = Path.home() / "yoshi" / "profile_locks.json"
SESSION_KEY_FILE = Path.home() / "yoshi" / "profile_session.key"
PIN_MIN_LENGTH = 4
PIN_MAX_LENGTH = 8
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64
AUTH_TYPES = {"pin", "password"}
_LOCK = threading.RLock()


class ProfileLockError(RuntimeError):
    pass


def normalize_profile(value):
    return " ".join(str(value or "").split()).strip()


def profile_key(profile):
    return normalize_profile(profile).casefold()


def validate_credential(credential, auth_type="pin"):
    kind = str(auth_type or "pin").strip().casefold()
    value = str(credential or "")
    if kind == "pin":
        value = value.strip()
        if (
            not value.isdigit()
            or len(value) < PIN_MIN_LENGTH
            or len(value) > PIN_MAX_LENGTH
        ):
            raise ValueError(
                f"PIN must be {PIN_MIN_LENGTH}-{PIN_MAX_LENGTH} digits."
            )
    elif kind == "password":
        if len(value) < PASSWORD_MIN_LENGTH or len(value) > PASSWORD_MAX_LENGTH:
            raise ValueError(
                f"Password must be {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} characters."
            )
    else:
        raise ValueError("Choose PIN or password protection.")
    return value


def validate_pin(pin):
    return validate_credential(pin, "pin")


def _load_entries():
    if not DATA_FILE.exists():
        return {}

    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        entries = payload.get("profiles", {})
        if not isinstance(entries, dict):
            raise ValueError("Profile locks must be an object.")

        clean = {}
        for key, entry in entries.items():
            if not isinstance(key, str) or not isinstance(entry, dict):
                raise ValueError("Invalid profile lock entry.")
            profile = normalize_profile(entry.get("profile"))
            password_hash = entry.get("hash")
            if not profile or not isinstance(password_hash, str):
                raise ValueError("Incomplete profile lock entry.")
            auth_type = str(entry.get("auth_type") or "pin").casefold()
            if auth_type not in AUTH_TYPES:
                raise ValueError("Invalid profile authentication type.")
            clean[key.casefold()] = {
                "profile": profile,
                "hash": password_hash,
                "auth_type": auth_type,
                "updated_at": int(entry.get("updated_at") or 0),
            }
        return clean
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ProfileLockError(
            "Yoshi's profile lock file needs repair."
        ) from error


def _save_entries(entries):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({
        "version": 1,
        "profiles": entries,
    }, indent=2) + "\n"
    temporary = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=DATA_FILE.parent,
            prefix=f".{DATA_FILE.name}.",
            suffix=".tmp",
            delete=False,
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


def data_file_valid():
    try:
        with _LOCK:
            _load_entries()
        return True
    except ProfileLockError:
        return False


def status(profile):
    name = normalize_profile(profile)
    with _LOCK:
        entry = _load_entries().get(profile_key(name))
    return {
        "profile": name,
        "locked": bool(entry),
        "auth_type": entry.get("auth_type") if entry else "none",
        "updated_at": entry.get("updated_at") if entry else None,
    }


def is_locked(profile):
    return status(profile)["locked"]


def verify_credential(profile, credential):
    with _LOCK:
        entry = _load_entries().get(profile_key(profile))
    if not entry:
        return False
    try:
        candidate = validate_credential(credential, entry["auth_type"])
    except ValueError:
        return False
    return check_password_hash(entry["hash"], candidate)


def verify_pin(profile, pin):
    return verify_credential(profile, pin)


def set_credential(profile, credential, auth_type="pin"):
    name = normalize_profile(profile)
    if not name:
        raise ValueError("Profile is required.")
    kind = str(auth_type or "pin").strip().casefold()
    candidate = validate_credential(credential, kind)

    with _LOCK:
        entries = _load_entries()
        entries[profile_key(name)] = {
            "profile": name,
            "hash": generate_password_hash(
                candidate,
                method="pbkdf2:sha256:600000",
                salt_length=16,
            ),
            "auth_type": kind,
            "updated_at": int(time.time()),
        }
        _save_entries(entries)
    return status(name)


def set_pin(profile, pin):
    return set_credential(profile, pin, "pin")


def remove_pin(profile):
    with _LOCK:
        entries = _load_entries()
        removed = entries.pop(profile_key(profile), None)
        if removed is not None:
            _save_entries(entries)
    return removed is not None


def get_session_secret():
    configured = os.environ.get("YOSHI_SESSION_SECRET", "").strip()
    if configured:
        if len(configured) < 32:
            raise ProfileLockError("YOSHI_SESSION_SECRET is too short.")
        return configured

    SESSION_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SESSION_KEY_FILE.exists():
        value = SESSION_KEY_FILE.read_text(encoding="utf-8").strip()
        if len(value) < 32:
            raise ProfileLockError("Yoshi's session key needs repair.")
        return value

    value = secrets.token_urlsafe(48)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=SESSION_KEY_FILE.parent,
            prefix=f".{SESSION_KEY_FILE.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(value + "\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary, 0o600)
        os.replace(temporary, SESSION_KEY_FILE)
        temporary = None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return value
