import base64
import json
import mimetypes
import os
import re
import secrets
import tempfile
from pathlib import Path

import yoshi_profile_lock

ROOT = Path.home() / "yoshi" / "private" / "chat-attachments"
MAX_BYTES = 8 * 1024 * 1024
MAX_TEXT_PREVIEW = 12000
ALLOWED_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif",
    ".pdf", ".txt", ".md", ".csv", ".json",
    ".py", ".js", ".css", ".html",
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


class AttachmentError(ValueError):
    pass


def _profile_directory(profile):
    key = yoshi_profile_lock.profile_key(profile)
    if not key:
        raise AttachmentError("A profile is required.")
    directory = ROOT / key
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(ROOT, 0o700)
    os.chmod(directory, 0o700)
    return directory


def _clean_name(value):
    name = Path(str(value or "attachment")).name
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return (name or "attachment")[:120]


def _validate_signature(suffix, data):
    if suffix == ".png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AttachmentError("That PNG file is invalid.")
    if suffix in {".jpg", ".jpeg"} and not data.startswith(b"\xff\xd8\xff"):
        raise AttachmentError("That JPEG file is invalid.")
    if suffix == ".gif" and not data.startswith((b"GIF87a", b"GIF89a")):
        raise AttachmentError("That GIF file is invalid.")
    if suffix == ".webp" and not (
        data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    ):
        raise AttachmentError("That WebP file is invalid.")
    if suffix == ".pdf" and not data.startswith(b"%PDF-"):
        raise AttachmentError("That PDF file is invalid.")


def save_attachment(profile, filename, data):
    clean_name = _clean_name(filename)
    suffix = Path(clean_name).suffix.casefold()
    if suffix not in ALLOWED_SUFFIXES:
        raise AttachmentError("That file type is not supported.")
    if not data:
        raise AttachmentError("The selected file is empty.")
    if len(data) > MAX_BYTES:
        raise AttachmentError("Attachments must be 8 MB or smaller.")
    _validate_signature(suffix, data)

    directory = _profile_directory(profile)
    attachment_id = secrets.token_hex(16)
    path = directory / f"{attachment_id}{suffix}"
    mime = mimetypes.types_map.get(suffix, "application/octet-stream")
    metadata = {
        "id": attachment_id,
        "name": clean_name,
        "size": len(data),
        "mime": mime,
        "kind": "image" if suffix in IMAGE_SUFFIXES else "file",
    }

    with tempfile.NamedTemporaryFile(dir=directory, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    meta_path = directory / f"{attachment_id}.json"
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")
    os.chmod(meta_path, 0o600)
    return metadata
def get_attachment(profile, attachment_id):
    if not ID_PATTERN.fullmatch(str(attachment_id or "")):
        raise AttachmentError("Unknown attachment.")
    directory = _profile_directory(profile)
    meta_path = directory / f"{attachment_id}.json"
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise AttachmentError("Unknown attachment.") from error
    matches = [
        path for path in directory.glob(f"{attachment_id}.*")
        if path.suffix != ".json"
    ]
    if len(matches) != 1 or not matches[0].is_file():
        raise AttachmentError("Unknown attachment.")
    return metadata, matches[0]


def image_payloads(profile, attachment_ids):
    images = []
    total_bytes = 0
    for attachment_id in list(attachment_ids or [])[:5]:
        metadata, path = get_attachment(profile, attachment_id)
        if metadata["kind"] != "image":
            continue
        data = path.read_bytes()
        total_bytes += len(data)
        if total_bytes > 16 * 1024 * 1024:
            raise AttachmentError(
                "Attached photos must total 16 MB or less."
            )
        images.append(base64.b64encode(data).decode("ascii"))
    return images


def prompt_context(profile, attachment_ids):
    descriptions = []
    public_items = []
    for attachment_id in list(attachment_ids or [])[:5]:
        metadata, path = get_attachment(profile, attachment_id)
        public_items.append(metadata)
        line = f"Attached {metadata['kind']}: {metadata['name']}"
        if metadata["kind"] == "file" and path.suffix in {
            ".txt", ".md", ".csv", ".json", ".py", ".js", ".css", ".html"
        }:
            preview = path.read_text(
                encoding="utf-8", errors="replace"
            )[:MAX_TEXT_PREVIEW]
            line += "\n--- file text ---\n" + preview + "\n--- end file ---"
        elif metadata["kind"] == "image":
            line += (
                " (stored for display/download; do not claim visual inspection "
                "unless vision input is available)"
            )
        descriptions.append(line)
    return "\n\n".join(descriptions), public_items
