import os
import re
import tempfile
from pathlib import Path

SUMMARY_PATH = Path.home() / "yoshi" / "conversation_summary.txt"

MAX_SUMMARY_CHARS = 1800
MAX_MESSAGE_CHARS = 260


def _summary_path(profile=None):
    profile = (profile or "Hermes").strip()
    if profile.casefold() == "hermes":
        return SUMMARY_PATH
    slug = re.sub(r"[^a-z0-9]+", "-", profile.casefold()).strip("-")
    return SUMMARY_PATH.with_name(
        f"conversation_summary-{slug or 'guest'}.txt"
    )


def load_summary(profile=None):
    path = _summary_path(profile)
    try:
        text = path.read_text(
            encoding="utf-8"
        ).strip()
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return text
    except FileNotFoundError:
        return ""


def save_summary(text, profile=None):
    text = (text or "").strip()

    if len(text) > MAX_SUMMARY_CHARS:
        text = text[-MAX_SUMMARY_CHARS:]

    path = _summary_path(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
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
            handle.write(text + ("\n" if text else ""))
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def clear_summary(profile=None):
    try:
        _summary_path(profile).unlink()
    except FileNotFoundError:
        pass


def append_entries(entries, profile=None):
    lines = []

    for item in entries or []:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content", "")

        if role not in {"user", "assistant"}:
            continue

        if not isinstance(content, str):
            continue

        content = " ".join(content.split()).strip()

        if not content:
            continue

        if len(content) > MAX_MESSAGE_CHARS:
            content = content[:MAX_MESSAGE_CHARS].rstrip() + "…"

        speaker = (profile or "Hermes") if role == "user" else "DiYoshi"
        lines.append(f"{speaker}: {content}")

    if not lines:
        return load_summary(profile)

    old = load_summary(profile)

    combined = "\n".join(
        part for part in (
            old,
            "\n".join(lines)
        )
        if part
    )

    save_summary(combined, profile)
    return load_summary(profile)
