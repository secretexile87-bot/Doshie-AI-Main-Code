"""Safe local proxy helpers for Yoshi's multi-engine voice service."""

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
            payload = json.loads(response.read(32 * 1024).decode("utf-8"))
    except HTTPError as error:
        try:
            payload = json.loads(error.read(32 * 1024).decode("utf-8"))
        except Exception:
            payload = {}
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        payload = {}

    return {
        "online": bool(payload.get("online")),
        "status": str(payload.get("status") or "offline"),
        "voice": str(payload.get("default_voice") or payload.get("voice") or "Hermes"),
        "engine": str(payload.get("default_engine") or payload.get("engine") or "edge"),
        "engines": payload.get("engines") or {},
        "verified_voices": payload.get("verified_voices") or {},
        "local": True,
    }


def list_voices(timeout: float = 2.0) -> dict:
    request = Request(f"{VOICE_URL}/api/voices", method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read(64 * 1024).decode("utf-8"))
    except Exception as error:
        return {"ok": False, "error": str(error), "default_voice": "hermes", "voices": {}}


def verify_voice(profile: str, verified: bool = True, timeout: float = 5.0) -> dict:
    body = json.dumps({"profile": profile, "verified": verified}).encode("utf-8")
    request = Request(
        f"{VOICE_URL}/api/voices/verify",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read(16 * 1024).decode("utf-8"))
    except Exception as error:
        return {"ok": False, "error": str(error)}


def upload_voice(profile: str, audio_base64: str, auto_verify: bool = True, timeout: float = 10.0) -> dict:
    body = json.dumps({
        "profile": profile,
        "audio": audio_base64,
        "verify": auto_verify,
    }).encode("utf-8")
    request = Request(
        f"{VOICE_URL}/api/voices/upload",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read(16 * 1024).decode("utf-8"))
    except Exception as error:
        return {"ok": False, "error": str(error)}


def synthesize(
    text: str,
    profile: str | None = None,
    engine: str | None = None,
    voice: str | None = None,
    timeout: float = 180.0,
) -> bytes:
    cleaned = " ".join(str(text or "").split()).strip()[:700]
    if not cleaned:
        raise ValueError("Text is required")

    req_data = {"text": cleaned}
    if profile:
        req_data["profile"] = str(profile).strip()
    if engine:
        req_data["engine"] = str(engine).strip()
    if voice:
        req_data["voice"] = str(voice).strip()

    body = json.dumps(req_data).encode("utf-8")
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
            raise VoiceUnavailable("Voice service is still warming up") from error
        raise VoiceUnavailable(f"Voice generation failed (HTTP {error.code})") from error
    except (OSError, URLError, TimeoutError) as error:
        raise VoiceUnavailable("Voice service is unavailable") from error

    if content_type != "audio/wav" or not audio.startswith(b"RIFF"):
        raise VoiceUnavailable("Voice service returned invalid audio")
    if len(audio) > MAX_AUDIO_BYTES:
        raise VoiceUnavailable("Voice response was too large")
    return audio
