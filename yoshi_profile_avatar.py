import hashlib
import os
import struct
import tempfile
import threading
import zlib
from pathlib import Path

import yoshi_profile_lock


DATA_DIR = Path.home() / "yoshi" / "profile_avatars"
AVATAR_SIZE = 256
MAX_AVATAR_BYTES = 2 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_LOCK = threading.RLock()


class ProfileAvatarError(ValueError):
    pass


def _avatar_name(profile):
    key = yoshi_profile_lock.profile_key(profile)
    if not key:
        raise ProfileAvatarError("Profile is required.")
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"{digest}.png"
def _read_png(data):
    if not isinstance(data, bytes) or not data.startswith(PNG_SIGNATURE):
        raise ProfileAvatarError("Choose a valid photo.")
    if len(data) > MAX_AVATAR_BYTES:
        raise ProfileAvatarError("Profile photo must be under 2 MB.")

    position = len(PNG_SIGNATURE)
    header = None
    compressed = bytearray()
    finished = False

    while position + 12 <= len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        kind = data[position + 4:position + 8]
        end = position + 12 + length
        if end > len(data) or length > MAX_AVATAR_BYTES:
            raise ProfileAvatarError("The profile photo is damaged.")
        payload = data[position + 8:position + 8 + length]
        checksum = struct.unpack(">I", data[end - 4:end])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != checksum:
            raise ProfileAvatarError("The profile photo is damaged.")

        if kind == b"IHDR":
            if header is not None or len(payload) != 13:
                raise ProfileAvatarError("The profile photo is damaged.")
            header = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            if header is None:
                raise ProfileAvatarError("The profile photo is damaged.")
            compressed.extend(payload)
        elif kind == b"IEND":
            if length or end != len(data):
                raise ProfileAvatarError("The profile photo is damaged.")
            finished = True
            break
        position = end

    if not finished or header is None or not compressed:
        raise ProfileAvatarError("The profile photo is incomplete.")

    width, height, depth, color, compression, filtering, interlace = header
    if width != AVATAR_SIZE or height != AVATAR_SIZE:
        raise ProfileAvatarError("Profile photo must be 256 × 256 pixels.")
    if depth != 8 or color not in {2, 6}:
        raise ProfileAvatarError("Choose a standard color photo.")
    if compression or filtering or interlace:
        raise ProfileAvatarError("Choose a non-interlaced photo.")

    channels = 3 if color == 2 else 4
    row_bytes = 1 + width * channels
    expected = row_bytes * height
    inflater = zlib.decompressobj()
    raw = inflater.decompress(bytes(compressed), expected + 1)
    if len(raw) <= expected:
        raw += inflater.flush(expected + 1 - len(raw))
    if (
        len(raw) != expected
        or not inflater.eof
        or inflater.unused_data
        or inflater.unconsumed_tail
    ):
        raise ProfileAvatarError("The profile photo pixels are invalid.")
    if any(raw[row * row_bytes] > 4 for row in range(height)):
        raise ProfileAvatarError("The profile photo pixels are invalid.")
    return data


def avatar_path(profile):
    path = DATA_DIR / _avatar_name(profile)
    return path if path.is_file() else None


def avatar_version(profile):
    path = avatar_path(profile)
    return path.stat().st_mtime_ns if path else None


def save_avatar(profile, data):
    clean = _read_png(data)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(DATA_DIR, 0o700)
    destination = DATA_DIR / _avatar_name(profile)
    temporary = None
    with _LOCK:
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=DATA_DIR,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(clean)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, destination)
            temporary = None
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
    return destination


def remove_avatar(profile):
    with _LOCK:
        path = avatar_path(profile)
        if not path:
            return False
        path.unlink()
        return True


def data_directory_valid():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(DATA_DIR, 0o700)
        return DATA_DIR.is_dir() and os.access(DATA_DIR, os.R_OK | os.W_OK)
    except OSError:
        return False
