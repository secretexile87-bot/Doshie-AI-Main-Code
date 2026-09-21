import json
import os
import tempfile
import time
from pathlib import Path

SETTINGS_FILE = Path.home() / "yoshi" / "settings.json"

DEFAULTS = {
    "auto_memory": True,
    "speak_replies": False,
    "persona_tone": "humble_kind",
    "custom_system_prompt": "Always be humble, deeply kind, gentle, empathetic, patient, and encouraging in every response.",
    "voice_identity": "hermes",
    "voice_engine": "clone",
    "voice_rate": 1.0,
    "voice_pitch": 1.0,
    "voice_preset": "gentle",
    "mode": "family",
    "voice_language": "en",
    "voice_region": "US",
    "default_weather_location": "El Paso"
}


def _quarantine_invalid_settings():
    if not SETTINGS_FILE.exists():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    quarantine = SETTINGS_FILE.with_name(
        f".{SETTINGS_FILE.name}.corrupt-{stamp}-{os.getpid()}"
    )
    os.replace(SETTINGS_FILE, quarantine)
    os.chmod(quarantine, 0o600)


def settings_file_valid():
    if not SETTINGS_FILE.exists():
        return True
    try:
        return isinstance(
            json.loads(SETTINGS_FILE.read_text(encoding="utf-8")),
            dict
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def load_settings():
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULTS.copy())
        return DEFAULTS.copy()

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))

        if not isinstance(data, dict):
            raise ValueError("Settings must be an object")

        settings = DEFAULTS.copy()
        settings.update(data)

        return settings

    except Exception:
        try:
            _quarantine_invalid_settings()
            save_settings(DEFAULTS.copy())
        except OSError:
            pass
        return DEFAULTS.copy()


def save_settings(settings):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(settings, indent=2) + "\n"
    temporary = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=SETTINGS_FILE.parent,
            prefix=f".{SETTINGS_FILE.name}.",
            suffix=".tmp",
            delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary, 0o600)
        os.replace(temporary, SETTINGS_FILE)
        temporary = None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def get_setting(name):
    return load_settings().get(name)


def set_setting(name, value):
    settings = load_settings()
    settings[name] = value
    save_settings(settings)
    return settings
