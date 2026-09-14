from pathlib import Path
import hashlib
import json
import os
import secrets
import tempfile
import threading
import time

DATA_FILE = Path.home() / "yoshi" / "family_invites.json"
_LOCK = threading.RLock()
DEFAULT_LIFETIME_SECONDS = 7 * 24 * 60 * 60


class InviteError(RuntimeError):
    pass


def _load():
    if not DATA_FILE.exists():
        return {"version": 1, "invites": []}
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InviteError("Family invitation data needs repair.") from error
    if not isinstance(data, dict) or not isinstance(data.get("invites"), list):
        raise InviteError("Family invitation data needs repair.")
    return data


def _save(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".family_invites-",
        suffix=".tmp",
        dir=DATA_FILE.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, DATA_FILE)
        os.chmod(DATA_FILE, 0o600)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _digest(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def create(profile, created_by, lifetime_seconds=DEFAULT_LIFETIME_SECONDS):
    profile = " ".join(str(profile or "").split()).strip()
    created_by = " ".join(str(created_by or "").split()).strip()
    if not profile or not created_by:
        raise ValueError("Choose a valid family profile.")
    lifetime = max(600, min(int(lifetime_seconds), 30 * 24 * 60 * 60))
    token = secrets.token_urlsafe(24)
    now = int(time.time())
    record = {
        "id": secrets.token_hex(8),
        "profile": profile,
        "created_by": created_by,
        "created_at": now,
        "expires_at": now + lifetime,
        "token_hash": _digest(token),
        "claimed_at": None,
        "revoked": False,
    }
    with _LOCK:
        data = _load()
        data["invites"].append(record)
        _save(data)
    return token, public_record(record)


def public_record(record):
    now = int(time.time())
    return {
        "id": record["id"],
        "profile": record["profile"],
        "created_by": record["created_by"],
        "created_at": record["created_at"],
        "expires_at": record["expires_at"],
        "claimed": bool(record.get("claimed_at")),
        "revoked": bool(record.get("revoked")),
        "active": (
            not record.get("revoked")
            and not record.get("claimed_at")
            and int(record.get("expires_at") or 0) > now
        ),
    }


def list_records():
    with _LOCK:
        return [public_record(item) for item in reversed(_load()["invites"])]


def claim(token):
    digest = _digest(str(token or "").strip())
    now = int(time.time())
    with _LOCK:
        data = _load()
        for record in data["invites"]:
            if not secrets.compare_digest(record.get("token_hash", ""), digest):
                continue
            if record.get("revoked"):
                raise ValueError("This invitation was revoked.")
            if record.get("claimed_at"):
                raise ValueError("This invitation was already used.")
            if int(record.get("expires_at") or 0) <= now:
                raise ValueError("This invitation expired.")
            record["claimed_at"] = now
            _save(data)
            return record["profile"]
    raise ValueError("That invitation code is invalid.")


def revoke_profile(profile):
    key = " ".join(str(profile or "").split()).strip().casefold()
    if not key:
        return 0
    changed = 0
    with _LOCK:
        data = _load()
        for record in data["invites"]:
            if str(record.get("profile") or "").strip().casefold() != key:
                continue
            if not record.get("revoked"):
                record["revoked"] = True
                changed += 1
        if changed:
            _save(data)
    return changed


def revoke(invite_id):
    with _LOCK:
        data = _load()
        for record in data["invites"]:
            if secrets.compare_digest(str(record.get("id")), str(invite_id)):
                record["revoked"] = True
                _save(data)
                return public_record(record)
    raise ValueError("Invitation not found.")
