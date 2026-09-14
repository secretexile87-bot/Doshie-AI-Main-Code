import json
import os
import re
import tempfile
import time
from pathlib import Path

HISTORY_FILE = Path.home() / "yoshi" / "chat_history.json"
MAX_MESSAGES = 12


def _history_path(profile=None):
    profile = (profile or "Hermes").strip()
    if profile.casefold() == "hermes":
        return HISTORY_FILE
    slug = re.sub(r"[^a-z0-9]+", "-", profile.casefold()).strip("-")
    return HISTORY_FILE.with_name(f"chat_history-{slug or 'guest'}.json")


def _quarantine_invalid_history(profile=None):
    path = _history_path(profile)
    if not path.exists():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    quarantine = path.with_name(
        f".{path.name}.corrupt-{stamp}-{os.getpid()}"
    )
    os.replace(path, quarantine)
    os.chmod(quarantine, 0o600)


def _validated_messages(data):
    if not isinstance(data, list):
        raise ValueError("History must be a list")

    messages = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("History entry must be an object")
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            raise ValueError("History entry has an invalid role or content")
        messages.append({"role": role, "content": content})
    return messages[-MAX_MESSAGES:]


def history_file_valid(profile=None):
    path = _history_path(profile)
    if not path.exists():
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        _validated_messages(data)
        return True
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def load_history(profile=None):
    path = _history_path(profile)
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        return _validated_messages(data)

    except Exception:
        try:
            _quarantine_invalid_history(profile)
        except OSError:
            pass

    return []


def save_history(history, profile=None):
    path = _history_path(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(history[-MAX_MESSAGES:], indent=2) + "\n"
    temporary = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def clear_history(profile=None):
    path = _history_path(profile)
    if path.exists():
        path.unlink()
