"""Safe local proxy helpers for Yoshi's private voice service."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


VOICE_URL = os.environ.get("YOSHI_VOICE_URL", "http://127.0.0.1:5051").rstrip("/")
MAX_AUDIO_BYTES = 24 * 1024 * 1024


class VoiceUnavailable(RuntimeError):
    """Raised when the optional local voice service cannot answer."""


def status(timeout: float = 2.0) -> dict:
    request = Request(f"{VOICE_URL}/health", method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(16 * 1024).decode("utf-8"))
    except HTTPError as error:
        try:
            payload = json.loads(error.read(16 * 1024).decode("utf-8"))
        except Exception:
            payload = {}
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        payload = {}

    return {
        "online": bool(payload.get("online")),
        "status": str(payload.get("status") or "offline"),
        "voice": str(payload.get("voice") or "Hermes"),
        "engine": str(payload.get("engine") or "chatterbox-nano"),
        "local": True,
    }


def synthesize(text: str, timeout: float = 180.0) -> bytes:
    cleaned = " ".join(str(text or "").split()).strip()[:700]
    if not cleaned:
        raise ValueError("Text is required")

    body = json.dumps({"text": cleaned}).encode("utf-8")
    request = Request(
        f"{VOICE_URL}/synthesize",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            audio = response.read(MAX_AUDIO_BYTES + 1)
    except HTTPError as error:
        if error.code == 503:
            raise VoiceUnavailable("Cloned voice is still warming up") from error
        raise VoiceUnavailable("Cloned voice generation failed") from error
    except (OSError, URLError, TimeoutError) as error:
        raise VoiceUnavailable("Cloned voice service is unavailable") from error

    if content_type != "audio/wav" or not audio.startswith(b"RIFF"):
        raise VoiceUnavailable("Cloned voice returned invalid audio")
    if len(audio) > MAX_AUDIO_BYTES:
        raise VoiceUnavailable("Cloned voice response was too large")
    return audio
