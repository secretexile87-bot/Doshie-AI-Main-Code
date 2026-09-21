#!/usr/bin/env python3
"""Unified Multi-Engine Multi-Profile Voice Service for Doshie / Yoshi.

Engines:
  1. "kokoro" (Default Option 1) - Blazing-fast GPU neural TTS on RTX 5070 (~150ms-2s)
  2. "edge"                     - Ultra-realistic neural streaming voice (~300-800ms)
  3. "piper"                    - Fast 100% offline local neural TTS (~1s)
  4. "clone"                    - Zero-shot neural voice cloning from reference WAV files
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import re
import threading
import time
import urllib.request
import wave
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch

# Ensure CUDA library search paths are present in process environment
_extra_lib_paths = [
    str(Path(__file__).resolve().parent / ".venv/lib/python3.14/site-packages/nvidia/cu13/lib"),
    str(Path(__file__).resolve().parent / ".venv/lib/python3.14/site-packages/nvidia/cudnn/lib"),
]
_current_ld = os.environ.get("LD_LIBRARY_PATH", "")
_new_ld = ":".join([p for p in _extra_lib_paths if os.path.isdir(p)] + ([_current_ld] if _current_ld else []))
if _new_ld:
    os.environ["LD_LIBRARY_PATH"] = _new_ld

# Auto-load .env file from project root if present
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.is_file():
    try:
        with open(_env_path, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))
    except Exception:
        pass

HOST = os.environ.get("YOSHI_VOICE_HOST", "127.0.0.1")
PORT = int(os.environ.get("YOSHI_VOICE_PORT", "5051"))
DEFAULT_ENGINE = os.environ.get("YOSHI_VOICE_ENGINE", "kokoro").lower().strip()
KOKORO_DEFAULT_VOICE = os.environ.get("YOSHI_KOKORO_VOICE", "am_adam")
EDGE_DEFAULT_VOICE = os.environ.get("YOSHI_EDGE_VOICE", "en-US-GuyNeural")

VOICES_DIR = Path(
    os.environ.get("YOSHI_VOICES_DIR", str(Path.home() / ".local/share/yoshi/voices"))
).expanduser()
VOICES_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_FILE = VOICES_DIR / "verified_voices.json"
HERMES_REFERENCE = VOICES_DIR / "hermes-reference.wav"
HERMES_SHORT_REFERENCE = VOICES_DIR / "hermes-ref-short.wav"

MAX_TEXT_LENGTH = 700
MAX_REQUEST_BYTES = 16 * 1024 * 1024

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("yoshi-voice")

torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))
try:
    torch.set_num_interop_threads(1)
except RuntimeError:
    pass

STATE_LOCK = threading.Lock()
SYNTHESIS_LOCK = threading.Lock()
REGISTRY_LOCK = threading.Lock()

# Engine instances
KOKORO_INSTANCE = None
PIPER_VOICE = None
CHATTERBOX_MODEL = None
ENGINES_READY = {
    "kokoro": False,
    "edge": True,
    "piper": False,
    "clone": False,
}
LOAD_ERRORS: dict[str, str] = {}
CACHED_CONDITIONALS: dict[str, Any] = {}


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _clean_text(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"https?://\S+", " link ", text)
    text = re.sub(r"[*_#>|`]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_TEXT_LENGTH]


def _normalize_name(name: str | None) -> str:
    return " ".join(str(name or "").split()).strip().casefold()


# --- Verified Voice Registry Helpers ---

def _load_registry() -> dict:
    default_registry = {
        "version": 1,
        "default_voice": "hermes",
        "voices": {
            "hermes": {
                "id": "hermes",
                "name": "Hermes",
                "file": "hermes-reference.wav",
                "backup_file": "hermes-ref-short.wav",
                "kokoro_voice": "am_adam",
                "edge_voice": "en-US-GuyNeural",
                "piper_voice": "en_US-bryce-medium",
                "verified": True,
                "is_default": True,
                "description": "Hermes Master Overall Voice (Kokoro Neural & Cloned Reference)",
                "updated_at": int(time.time()),
            }
        },
    }

    if not REGISTRY_FILE.exists():
        return default_registry

    try:
        data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "voices" not in data:
            return default_registry
        if "hermes" not in data["voices"]:
            data["voices"]["hermes"] = default_registry["voices"]["hermes"]
        return data
    except Exception as err:
        LOGGER.warning("Could not read voice registry (%s); using default", err)
        return default_registry


def _save_registry(registry: dict) -> None:
    try:
        REGISTRY_FILE.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        alt = Path.home() / "yoshi" / "verified_voices.json"
        alt.parent.mkdir(parents=True, exist_ok=True)
        alt.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    except Exception as err:
        LOGGER.error("Failed to save voice registry: %s", err)


def resolve_voice_profile(profile_or_voice: str | None) -> dict:
    """Resolves voice metadata. If profile is unverified or missing audio, falls back to Hermes."""
    norm = _normalize_name(profile_or_voice)
    with REGISTRY_LOCK:
        reg = _load_registry()
        voices = reg.get("voices", {})

    # Check direct match
    entry = None
    if norm:
        for k, v in voices.items():
            if k == norm or _normalize_name(v.get("name")) == norm or _normalize_name(v.get("id")) == norm:
                entry = v
                break

    # If matching entry exists, check if verified
    if entry and entry.get("verified", False):
        ref_file = VOICES_DIR / entry.get("file", "")
        return {
            "id": entry.get("id", norm),
            "name": entry.get("name", norm.title()),
            "file_path": ref_file if ref_file.is_file() else None,
            "kokoro_voice": entry.get("kokoro_voice", KOKORO_DEFAULT_VOICE),
            "edge_voice": entry.get("edge_voice", "en-US-GuyNeural"),
            "piper_voice": entry.get("piper_voice", "en_US-bryce-medium"),
            "verified": True,
            "is_fallback": False,
        }

    # Fallback to Master Overall Voice (Hermes)
    hermes_entry = voices.get("hermes", {})
    primary_ref = VOICES_DIR / hermes_entry.get("file", "hermes-reference.wav")
    if not primary_ref.is_file():
        primary_ref = HERMES_REFERENCE if HERMES_REFERENCE.is_file() else HERMES_SHORT_REFERENCE

    return {
        "id": "hermes",
        "name": "Hermes",
        "file_path": primary_ref,
        "kokoro_voice": hermes_entry.get("kokoro_voice", KOKORO_DEFAULT_VOICE),
        "edge_voice": hermes_entry.get("edge_voice", EDGE_DEFAULT_VOICE),
        "piper_voice": hermes_entry.get("piper_voice", "en_US-bryce-medium"),
        "verified": True,
        "is_fallback": (norm != "" and norm != "hermes"),
    }


# --- Engine Initialization ---

def _init_kokoro() -> None:
    global KOKORO_INSTANCE
    try:
        model_path = VOICES_DIR / "kokoro" / "kokoro-v1.0.onnx"
        voices_path = VOICES_DIR / "kokoro" / "voices-v1.0.bin"
        if not model_path.is_file() or not voices_path.is_file():
            LOGGER.warning("Kokoro model files not found: %s", model_path)
            return

        import ctypes
        nvidia_base = Path(__file__).resolve().parent / ".venv/lib/python3.14/site-packages/nvidia"
        for lib_sub in [
            "cu13/lib/libcublasLt.so.13",
            "cu13/lib/libcublas.so.13",
            "cudnn/lib/libcudnn.so.9",
            "cusparselt/lib/libcusparseLt.so.0",
        ]:
            p = nvidia_base / lib_sub
            if p.is_file():
                try:
                    ctypes.CDLL(str(p), mode=ctypes.RTLD_GLOBAL)
                except Exception:
                    pass

        import onnxruntime as rt
        from kokoro_onnx import Kokoro

        opts = rt.SessionOptions()
        opts.graph_optimization_level = rt.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = max(1, min(4, os.cpu_count() or 1))
        opts.execution_mode = rt.ExecutionMode.ORT_SEQUENTIAL

        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        session = rt.InferenceSession(str(model_path), sess_options=opts, providers=providers)
        instance = Kokoro.from_session(session, str(voices_path))

        # Warmup GPU kernels so first request is sub-second
        try:
            instance.create("Ready.", voice=KOKORO_DEFAULT_VOICE, speed=1.0, lang="en-us")
        except Exception:
            pass

        with STATE_LOCK:
            KOKORO_INSTANCE = instance
            ENGINES_READY["kokoro"] = True
            if "kokoro" in LOAD_ERRORS:
                del LOAD_ERRORS["kokoro"]
        LOGGER.info("Kokoro neural voice engine is ready on %s", session.get_providers()[0])
    except Exception as e:
        LOGGER.warning("Could not initialize Kokoro engine: %s", e)
        with STATE_LOCK:
            LOAD_ERRORS["kokoro"] = str(e)


def _init_piper() -> None:
    global PIPER_VOICE
    try:
        from piper import PiperVoice
        cache_dir = Path.home() / ".cache/piper"
        cache_dir.mkdir(parents=True, exist_ok=True)
        onnx_path = cache_dir / "en_US-bryce-medium.onnx"
        json_path = cache_dir / "en_US-bryce-medium.onnx.json"

        if not onnx_path.exists() or not json_path.exists():
            LOGGER.info("Downloading Piper voice model (en_US-bryce-medium)...")
            base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/bryce/medium"
            urllib.request.urlretrieve(f"{base_url}/en_US-bryce-medium.onnx", str(onnx_path))
            urllib.request.urlretrieve(f"{base_url}/en_US-bryce-medium.onnx.json", str(json_path))

        voice = PiperVoice.load(str(onnx_path), config_path=str(json_path))
        with STATE_LOCK:
            PIPER_VOICE = voice
            ENGINES_READY["piper"] = True
        LOGGER.info("Piper fast TTS engine is ready")
    except Exception as e:
        LOGGER.warning("Could not initialize Piper engine: %s", e)
        with STATE_LOCK:
            LOAD_ERRORS["piper"] = str(e)


def _init_chatterbox() -> None:
    global CHATTERBOX_MODEL
    try:
        ref_path = HERMES_REFERENCE if HERMES_REFERENCE.is_file() else HERMES_SHORT_REFERENCE
        if not ref_path.is_file():
            LOGGER.warning("Voice reference not found: %s", ref_path)
            return

        import perth
        if not callable(getattr(perth, "PerthImplicitWatermarker", None)):
            perth.PerthImplicitWatermarker = perth.DummyWatermarker

        from chatterbox.models.voice_encoder.voice_encoder import VoiceEncoder
        orig_ve_forward = VoiceEncoder.forward
        def compatible_ve_forward(self, mels):
            if torch.is_tensor(mels):
                mels = mels.to(dtype=torch.float32)
            return orig_ve_forward(self, mels)
        VoiceEncoder.forward = compatible_ve_forward

        orig_ve_inference = VoiceEncoder.inference
        def compatible_ve_inference(self, mels, *args, **kwargs):
            if torch.is_tensor(mels):
                mels = mels.to(dtype=torch.float32)
            return orig_ve_inference(self, mels, *args, **kwargs)
        VoiceEncoder.inference = compatible_ve_inference

        from chatterbox.tts_turbo import ChatterboxTurboTTS
        model = ChatterboxTurboTTS.from_pretrained(device="cpu")

        tokenizer = getattr(getattr(model, "s3gen", None), "tokenizer", None)
        mel_filters = getattr(tokenizer, "_mel_filters", None)
        if tokenizer is not None and torch.is_tensor(mel_filters):
            tokenizer._mel_filters = mel_filters.to(dtype=torch.float32)
        original_log_mel = getattr(tokenizer, "log_mel_spectrogram", None)
        if tokenizer is not None and callable(original_log_mel):
            def compatible_log_mel(audio, padding=0):
                tokenizer._mel_filters = tokenizer._mel_filters.to(dtype=torch.float32)
                if torch.is_tensor(audio):
                    audio = audio.to(dtype=torch.float32)
                else:
                    audio = np.asarray(audio, dtype=np.float32)
                return original_log_mel(audio, padding)
            tokenizer.log_mel_spectrogram = compatible_log_mel

        with torch.inference_mode():
            model.prepare_conditionals(str(ref_path))
            CACHED_CONDITIONALS[str(ref_path.resolve())] = model.conds

        with STATE_LOCK:
            CHATTERBOX_MODEL = model
            ENGINES_READY["clone"] = True
            if "clone" in LOAD_ERRORS:
                del LOAD_ERRORS["clone"]
        LOGGER.info("Chatterbox clone engine is ready with default voice: Hermes")
    except Exception as e:
        LOGGER.warning("Could not initialize Chatterbox clone engine: %s", e)
        with STATE_LOCK:
            LOAD_ERRORS["clone"] = str(e)


def _init_background_models() -> None:
    _init_kokoro()
    _init_piper()
    _init_chatterbox()


# --- Synthesis Handlers ---

def _synthesize_kokoro(text: str, voice_name: str | None = None, speed: float = 1.0) -> bytes:
    with STATE_LOCK:
        instance = KOKORO_INSTANCE
    if instance is None:
        raise RuntimeError("Kokoro engine is not loaded")

    chosen_voice = voice_name or KOKORO_DEFAULT_VOICE
    samples, sample_rate = instance.create(
        text,
        voice=chosen_voice,
        speed=speed,
        lang="en-us"
    )
    wav_io = io.BytesIO()
    sf.write(wav_io, samples, sample_rate, format="WAV")
    return wav_io.getvalue()


async def _synthesize_edge(text: str, edge_voice_name: str | None = None) -> bytes:
    import edge_tts
    chosen_voice = edge_voice_name or EDGE_DEFAULT_VOICE
    communicate = edge_tts.Communicate(text, chosen_voice)
    mp3_data = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_data.extend(chunk["data"])

    if not mp3_data:
        raise RuntimeError("No audio data received from Edge TTS")

    data, sr = sf.read(io.BytesIO(mp3_data))
    wav_io = io.BytesIO()
    sf.write(wav_io, data, sr, format="WAV")
    return wav_io.getvalue()


def _synthesize_piper(text: str) -> bytes:
    with STATE_LOCK:
        voice = PIPER_VOICE
    if voice is None:
        raise RuntimeError("Piper engine is not loaded")

    raw_bytes = bytearray()
    for chunk in voice.synthesize(text):
        raw_bytes.extend(chunk.audio_int16_bytes)

    sr = 22050
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(raw_bytes)
    return wav_io.getvalue()


def _synthesize_clone(text: str, reference_path: Path) -> bytes:
    with STATE_LOCK:
        model = CHATTERBOX_MODEL
    if model is None:
        raise RuntimeError("Chatterbox clone engine is not loaded")

    resolved_path = str(reference_path.resolve())
    if resolved_path not in CACHED_CONDITIONALS:
        LOGGER.info("Preparing conditionals for voice reference: %s", resolved_path)
        with torch.inference_mode():
            model.prepare_conditionals(resolved_path)
            CACHED_CONDITIONALS[resolved_path] = model.conds
    else:
        model.conds = CACHED_CONDITIONALS[resolved_path]

    with torch.inference_mode():
        generated = model.generate(text)

    audio = generated.detach().to(device="cpu", dtype=torch.float32)
    if audio.ndim > 1:
        audio = audio[0]
    audio = torch.clamp(audio, -1.0, 1.0)
    pcm = (audio.numpy() * 32767.0).astype(np.int16).tobytes()

    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(model.sr))
        handle.writeframes(pcm)
    return wav_io.getvalue()


def _synthesize_auto(
    text: str,
    requested_engine: str | None = None,
    profile: str | None = None,
    voice: str | None = None,
) -> bytes:
    engine = (requested_engine or DEFAULT_ENGINE).lower().strip()
    voice_meta = resolve_voice_profile(profile or voice)

    # 1. Kokoro Neural Engine (Option 1)
    if engine in ("kokoro", "option1", "fast-neural", "auto", "default"):
        try:
            return _synthesize_kokoro(text, voice_meta.get("kokoro_voice"))
        except Exception as err:
            LOGGER.warning("Kokoro TTS failed (%s); falling back to Edge", err)
            engine = "edge"

    # 2. Edge Streaming Neural
    if engine in ("edge", "neural", "online"):
        try:
            return asyncio.run(_synthesize_edge(text, voice_meta.get("edge_voice")))
        except Exception as err:
            LOGGER.warning("Edge TTS failed (%s); falling back to Piper", err)
            engine = "piper"

    # 3. Piper Offline Neural
    if engine in ("piper", "fast", "local", "offline"):
        try:
            return _synthesize_piper(text)
        except Exception as err:
            LOGGER.warning("Piper TTS failed (%s); falling back to Edge/Kokoro", err)
            try:
                return _synthesize_kokoro(text, voice_meta.get("kokoro_voice"))
            except Exception:
                return asyncio.run(_synthesize_edge(text, voice_meta.get("edge_voice")))

    # 4. Clone Engine
    if engine in ("clone", "chatterbox", "hermes"):
        try:
            if voice_meta.get("file_path") and voice_meta["file_path"].is_file():
                return _synthesize_clone(text, voice_meta["file_path"])
        except Exception as err:
            LOGGER.warning("Clone engine failed (%s); falling back to Kokoro", err)

    # Default fallback: Kokoro -> Edge
    try:
        return _synthesize_kokoro(text, voice_meta.get("kokoro_voice"))
    except Exception:
        return asyncio.run(_synthesize_edge(text, voice_meta.get("edge_voice")))


def _voice_status() -> dict:
    with STATE_LOCK:
        engines = {
            "kokoro": {"ready": ENGINES_READY["kokoro"], "desc": "Kokoro neural TTS on RTX 5070 GPU (~150ms)"},
            "edge": {"ready": ENGINES_READY["edge"], "desc": "Ultra-realistic neural streaming (~300ms)"},
            "piper": {"ready": ENGINES_READY["piper"], "desc": "Fast 100% offline local neural TTS (~1s)"},
            "clone": {"ready": ENGINES_READY["clone"], "desc": "Custom cloned Hermes voice (Master overall voice)"},
        }
        online = any(ENGINES_READY.values())

    with REGISTRY_LOCK:
        reg = _load_registry()

    return {
        "online": online,
        "status": "ready",
        "default_voice": "Hermes",
        "default_engine": DEFAULT_ENGINE,
        "engines": engines,
        "verified_voices": reg.get("voices", {}),
        "errors": LOAD_ERRORS,
    }


class VoiceHandler(BaseHTTPRequestHandler):
    server_version = "YoshiVoice/2.2"

    def log_message(self, format_string: str, *args: object) -> None:
        LOGGER.info("%s - %s", self.client_address[0], format_string % args)

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        self._send(status, _json_bytes(payload), "application/json")

    def do_OPTIONS(self) -> None:
        self._send(HTTPStatus.NO_CONTENT, b"", "text/plain")

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path in ("/health", "/status"):
            status = _voice_status()
            code = HTTPStatus.OK if status["online"] else HTTPStatus.SERVICE_UNAVAILABLE
            self._send_json(code, status)
            return

        if path in ("/api/voices", "/voices"):
            with REGISTRY_LOCK:
                reg = _load_registry()
            self._send_json(HTTPStatus.OK, {
                "ok": True,
                "default_voice": reg.get("default_voice", "hermes"),
                "default_engine": DEFAULT_ENGINE,
                "voices": reg.get("voices", {}),
            })
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:
        path = self.path.split("?")[0]

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0

        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid request size"})
            return

        try:
            raw_body = self.rfile.read(length)
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return

        # 1. Voice Synthesis endpoint
        if path in ("/synthesize", "/speak"):
            text = _clean_text(payload.get("text"))
            if not text:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Text is required"})
                return

            engine = payload.get("engine")
            profile = payload.get("profile")
            voice = payload.get("voice")

            try:
                resolved_voice = resolve_voice_profile(profile or voice)
                LOGGER.info(
                    "Synthesizing %d chars using engine='%s', voice='%s' (is_fallback=%s)",
                    len(text),
                    engine or DEFAULT_ENGINE,
                    resolved_voice["name"],
                    resolved_voice.get("is_fallback", False),
                )
                with SYNTHESIS_LOCK:
                    wav_body = _synthesize_auto(
                        text,
                        requested_engine=engine,
                        profile=profile,
                        voice=voice,
                    )
                self._send(HTTPStatus.OK, wav_body, "audio/wav")
            except Exception as error:
                LOGGER.exception("Voice generation failed")
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": f"Voice generation failed: {error}"},
                )
            return

        # 2. Voice Verification endpoint
        if path in ("/api/voices/verify", "/voices/verify"):
            profile_name = str(payload.get("profile") or payload.get("name") or "").strip()
            verified = bool(payload.get("verified", True))
            if not profile_name:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Profile name is required"})
                return

            key = _normalize_name(profile_name)
            with REGISTRY_LOCK:
                reg = _load_registry()
                if key not in reg.get("voices", {}):
                    reg["voices"][key] = {
                        "id": key,
                        "name": profile_name,
                        "file": f"{key}-reference.wav",
                        "kokoro_voice": "af_heart" if "aeriel" in key else "am_adam",
                        "verified": verified,
                        "updated_at": int(time.time()),
                    }
                else:
                    reg["voices"][key]["verified"] = verified
                    reg["voices"][key]["updated_at"] = int(time.time())
                _save_registry(reg)

            self._send_json(HTTPStatus.OK, {
                "ok": True,
                "profile": profile_name,
                "verified": verified,
                "voice": reg["voices"][key],
            })
            return

        # 3. Voice Upload / Input endpoint
        if path in ("/api/voices/upload", "/voices/upload"):
            profile_name = str(payload.get("profile") or "").strip()
            audio_base64 = str(payload.get("audio") or "").strip()
            auto_verify = bool(payload.get("verify", True))

            if not profile_name or not audio_base64:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Profile name and audio data are required"})
                return

            try:
                if "," in audio_base64:
                    audio_base64 = audio_base64.split(",", 1)[1]
                audio_bytes = base64.b64decode(audio_base64)
            except Exception as err:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"Invalid audio base64: {err}"})
                return

            key = _normalize_name(profile_name)
            dest_filename = f"{key}-reference.wav"
            dest_path = VOICES_DIR / dest_filename

            try:
                data, sr = sf.read(io.BytesIO(audio_bytes))
                sf.write(str(dest_path), data, sr, format="WAV")
                LOGGER.info("Saved new voice sample for '%s' to %s", profile_name, dest_path)

                CACHED_CONDITIONALS.pop(str(dest_path.resolve()), None)

                with REGISTRY_LOCK:
                    reg = _load_registry()
                    reg["voices"][key] = {
                        "id": key,
                        "name": profile_name,
                        "file": dest_filename,
                        "kokoro_voice": "af_heart" if "aeriel" in key else "am_adam",
                        "verified": auto_verify,
                        "updated_at": int(time.time()),
                    }
                    _save_registry(reg)

                self._send_json(HTTPStatus.OK, {
                    "ok": True,
                    "profile": profile_name,
                    "file": dest_filename,
                    "verified": auto_verify,
                    "message": f"Voice for {profile_name} saved and {'verified' if auto_verify else 'pending verification'}.",
                })
            except Exception as err:
                LOGGER.exception("Failed to save audio file")
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Failed to save audio: {err}"})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})


def main() -> None:
    loader = threading.Thread(target=_init_background_models, name="engine-loader", daemon=True)
    loader.start()
    server = ThreadingHTTPServer((HOST, PORT), VoiceHandler)
    LOGGER.info("Yoshi voice service listening on http://%s:%s (Default Engine: %s)", HOST, PORT, DEFAULT_ENGINE)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
