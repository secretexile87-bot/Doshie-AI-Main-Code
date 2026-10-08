import base64
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
PIN_MIN_LENGTH = 3
PIN_MAX_LENGTH = 16
PASSWORD_MIN_LENGTH = 3
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
    value = str(credential or "").strip()
    if not value:
        raise ValueError("Password or PIN code cannot be empty.")

    if kind == "pin":
        if not value.isdigit() or len(value) < PIN_MIN_LENGTH or len(value) > PIN_MAX_LENGTH:
            # If user entered text password for a pin, accept as password
            if len(value) >= PASSWORD_MIN_LENGTH and len(value) <= PASSWORD_MAX_LENGTH:
                return value
            raise ValueError(
                f"PIN must be {PIN_MIN_LENGTH}-{PIN_MAX_LENGTH} digits or characters."
            )
    elif kind == "password":
        if len(value) < PASSWORD_MIN_LENGTH or len(value) > PASSWORD_MAX_LENGTH:
            raise ValueError(
                f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
            )
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
                "biometrics": entry.get("biometrics") if isinstance(entry.get("biometrics"), list) else [],
                "mfa_enabled": bool(entry.get("mfa_enabled", False)),
                "biometrics_quick_unlock": bool(entry.get("biometrics_quick_unlock", True)),
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
        "has_biometrics": bool(entry and entry.get("biometrics")),
        "biometrics_count": len(entry.get("biometrics", [])) if entry else 0,
        "mfa_enabled": bool(entry and entry.get("mfa_enabled")),
        "biometrics_quick_unlock": bool(entry and entry.get("biometrics_quick_unlock", True)),
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
        key = profile_key(name)
        old_entry = entries.get(key, {})
        entries[key] = {
            "profile": name,
            "hash": generate_password_hash(
                candidate,
                method="pbkdf2:sha256:600000",
                salt_length=16,
            ),
            "auth_type": kind,
            "updated_at": int(time.time()),
            "biometrics": old_entry.get("biometrics", []),
            "mfa_enabled": old_entry.get("mfa_enabled", False),
            "biometrics_quick_unlock": old_entry.get("biometrics_quick_unlock", True),
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


_CHALLENGES = {}
_MFA_TOKENS = {}


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def b64url_decode(s: str) -> bytes:
    pad = len(s) % 4
    if pad:
        s += "=" * (4 - pad)
    return base64.urlsafe_b64decode(s)


def create_challenge(profile, challenge_type="login", ttl=300):
    clean_profile = normalize_profile(profile)
    token = b64url_encode(secrets.token_bytes(32))
    now = time.time()
    with _LOCK:
        expired = [k for k, v in _CHALLENGES.items() if v.get("expires_at", 0) < now]
        for k in expired:
            _CHALLENGES.pop(k, None)
        _CHALLENGES[token] = {
            "profile": clean_profile.casefold(),
            "type": challenge_type,
            "expires_at": now + ttl,
        }
    return token


def verify_and_consume_challenge(profile, challenge_token, challenge_type="login"):
    if not challenge_token:
        return False
    clean_profile = normalize_profile(profile).casefold()
    now = time.time()
    with _LOCK:
        rec = _CHALLENGES.pop(str(challenge_token).strip(), None)
        if not rec:
            return False
        if rec.get("expires_at", 0) < now:
            return False
        if rec.get("profile") != clean_profile:
            return False
        if rec.get("type") != challenge_type:
            return False
    return True


def create_mfa_token(profile, ttl=300):
    clean_profile = normalize_profile(profile)
    token = secrets.token_urlsafe(32)
    now = time.time()
    with _LOCK:
        expired = [k for k, v in _MFA_TOKENS.items() if v.get("expires_at", 0) < now]
        for k in expired:
            _MFA_TOKENS.pop(k, None)
        _MFA_TOKENS[token] = {
            "profile": clean_profile.casefold(),
            "expires_at": now + ttl,
        }
    return token


def verify_and_consume_mfa_token(profile, token):
    if not token:
        return False
    clean_profile = normalize_profile(profile).casefold()
    now = time.time()
    with _LOCK:
        rec = _MFA_TOKENS.pop(str(token).strip(), None)
        if not rec:
            return False
        if rec.get("expires_at", 0) < now:
            return False
        if rec.get("profile") != clean_profile:
            return False
    return True


def get_biometrics(profile):
    name = normalize_profile(profile)
    with _LOCK:
        entry = _load_entries().get(profile_key(name))
        if not entry:
            return []
        items = entry.get("biometrics") or []
        return [
            {
                "id": b.get("id"),
                "name": b.get("name") or "Biometric Key",
                "created_at": b.get("created_at") or 0,
            }
            for b in items
            if isinstance(b, dict) and b.get("id")
        ]


def has_biometrics(profile):
    return len(get_biometrics(profile)) > 0


def add_biometric(profile, credential_id, name="Biometric Device", raw_id=None):
    clean_name = normalize_profile(profile)
    if not clean_name:
        raise ValueError("Profile is required.")
    cred_id = str(credential_id or "").strip()
    if not cred_id:
        raise ValueError("Credential ID is required.")

    with _LOCK:
        entries = _load_entries()
        key = profile_key(clean_name)
        entry = entries.get(key)
        if not entry:
            entry = {
                "profile": clean_name,
                "hash": "",
                "auth_type": "pin",
                "updated_at": int(time.time()),
                "biometrics": [],
                "mfa_enabled": False,
                "biometrics_quick_unlock": True,
            }

        bios = entry.get("biometrics") or []
        for b in bios:
            if b.get("id") == cred_id:
                b["name"] = str(name or "Biometric Device").strip()[:80]
                b["updated_at"] = int(time.time())
                _save_entries(entries)
                return entry

        bios.append({
            "id": cred_id,
            "raw_id": str(raw_id or cred_id),
            "name": str(name or "Biometric Device").strip()[:80],
            "created_at": int(time.time()),
        })
        entry["biometrics"] = bios
        entries[key] = entry
        _save_entries(entries)
    return entry


def remove_biometric(profile, credential_id):
    clean_name = normalize_profile(profile)
    cred_id = str(credential_id or "").strip()
    with _LOCK:
        entries = _load_entries()
        key = profile_key(clean_name)
        entry = entries.get(key)
        if not entry or not entry.get("biometrics"):
            return False

        orig_len = len(entry["biometrics"])
        entry["biometrics"] = [
            b for b in entry["biometrics"] if b.get("id") != cred_id
        ]
        if len(entry["biometrics"]) < orig_len:
            _save_entries(entries)
            return True
    return False


def set_mfa_settings(profile, mfa_enabled=None, biometrics_quick_unlock=None):
    clean_name = normalize_profile(profile)
    with _LOCK:
        entries = _load_entries()
        key = profile_key(clean_name)
        entry = entries.get(key)
        if not entry:
            raise ValueError(f"Profile {clean_name} does not have security configured.")
        if mfa_enabled is not None:
            entry["mfa_enabled"] = bool(mfa_enabled)
        if biometrics_quick_unlock is not None:
            entry["biometrics_quick_unlock"] = bool(biometrics_quick_unlock)
        _save_entries(entries)
    return status(clean_name)


def verify_biometric_credential(profile, credential_id):
    clean_name = normalize_profile(profile)
    cred_id = str(credential_id or "").strip()
    if not cred_id:
        return False
    with _LOCK:
        entry = _load_entries().get(profile_key(clean_name))
        if not entry or not entry.get("biometrics"):
            return False
        return any(b.get("id") == cred_id for b in entry["biometrics"])



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
