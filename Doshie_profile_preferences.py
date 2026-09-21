import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import yoshi_profile_lock


DATA_FILE = Path.home() / "yoshi" / "profile_preferences.json"
THEMES = {
    "forest", "midnight", "jungle", "sunset", "stars", "tron",
    "emerald", "cyberpunk", "oled", "amber", "crimson", "terminal", "nord", "dracula"
}
FONTS = {"system", "tech", "mono", "compact", "classic"}
FONT_SIZES = {85, 100, 115, 130}
ACCENTS = {
    "mint": "#83d69b",
    "forest": "#5f9d76",
    "teal": "#62b9ad",
    "blue": "#6f9ed6",
    "purple": "#9b78c6",
    "rose": "#ce7893",
    "orange": "#dc8b61",
    "amber": "#dfb45f",
}
AUTO_LOCK_MINUTES = {0, 5, 15, 30, 60}
NEWS_TOPICS = {"local", "national", "tech", "gaming", "family"}
ACCESS_ROLES = {"family", "child", "admin"}
_LOCK = threading.RLock()

DEFAULTS = {
    "status": "",
    "about_me": "",
    "interests": "",
    "profile_music_url": "",
    "custom_css": "",
    "accent": "mint",
    "theme": "forest",
    "custom_color": "#31f6ff",
    "font_family": "tech",
    "font_size": 100,
    "auto_lock_minutes": 5,
    "lock_on_close": True,
    "news_topic": "local",
    "news_visible": True,
    "access_role": "family",
    "gui_customization": {},
    "auto_web_search": True,
    "safe_search": True,
    "age": 18,
}


class ProfilePreferencesError(RuntimeError):
    pass


def _profile_key(profile):
    key = yoshi_profile_lock.profile_key(profile)
    if not key:
        raise ValueError("Profile is required.")
    return key


def _clean_status(value):
    clean = " ".join(str(value or "").split()).strip()
    if len(clean) > 80:
        raise ValueError("Status must be 80 characters or fewer.")
    return clean


def _clean_about(value):
    clean = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(clean) > 240:
        raise ValueError("About Me must be 240 characters or fewer.")
    return clean


def _clean_interests(value):
    clean = " ".join(str(value or "").split()).strip()
    if len(clean) > 240:
        raise ValueError("Interests must be 240 characters or fewer.")
    return clean


def _clean_music_url(value):
    clean = str(value or "").strip()
    if not clean:
        return ""
    parsed = urlparse(clean)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Profile music must use a valid HTTPS link.")
    if len(clean) > 500:
        raise ValueError("Profile music link is too long.")
    return clean


def _clean_custom_css(value):
    clean = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(clean) > 12000:
        raise ValueError("Custom CSS must be 12,000 characters or fewer.")
    return clean


def _validated(values):
    data = dict(DEFAULTS)
    if not isinstance(values, dict):
        raise ValueError("Profile preferences must be an object.")

    if "status" in values:
        data["status"] = _clean_status(values["status"])
    if "about_me" in values:
        data["about_me"] = _clean_about(values["about_me"])
    if "interests" in values:
        data["interests"] = _clean_interests(values["interests"])
    if "profile_music_url" in values:
        data["profile_music_url"] = _clean_music_url(
            values["profile_music_url"]
        )
    if "custom_css" in values:
        data["custom_css"] = _clean_custom_css(values["custom_css"])

    if "gui_customization" in values and isinstance(values["gui_customization"], dict):
        data["gui_customization"] = dict(values["gui_customization"])

    raw_accent = str(values.get("accent", data["accent"])).strip().casefold()
    if raw_accent in ACCENTS:
        data["accent"] = raw_accent

    raw_theme = str(values.get("theme", data["theme"])).strip().casefold()
    if raw_theme in THEMES:
        data["theme"] = raw_theme
    elif "gui_customization" in values:
        data["theme"] = raw_theme

    color = str(values.get("custom_color", data["custom_color"])).strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        data["custom_color"] = color.lower()

    font = str(values.get("font_family", data["font_family"])).strip().casefold()
    if font in FONTS:
        data["font_family"] = font

    font_size = values.get("font_size", data["font_size"])
    if not isinstance(font_size, bool) and isinstance(font_size, (int, float)):
        data["font_size"] = int(font_size)

    minutes = values.get("auto_lock_minutes", data["auto_lock_minutes"])
    if not isinstance(minutes, bool) and isinstance(minutes, (int, float)):
        data["auto_lock_minutes"] = int(minutes)

    for field in ("lock_on_close", "news_visible"):
        value = values.get(field, data[field])
        if isinstance(value, bool):
            data[field] = value

    topic = str(values.get("news_topic", data["news_topic"])).strip().casefold()
    if topic in NEWS_TOPICS:
        data["news_topic"] = topic

    access_role = str(
        values.get("access_role", data["access_role"])
    ).strip().casefold()
    if access_role in ACCESS_ROLES:
        data["access_role"] = access_role
    return data


def _load_entries():
    if not DATA_FILE.exists():
        return {}
    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        entries = payload.get("profiles", {})
        if not isinstance(entries, dict):
            raise ValueError("Profile preferences must be an object.")

        clean = {}
        for key, entry in entries.items():
            if not isinstance(key, str) or not isinstance(entry, dict):
                raise ValueError("Invalid profile preferences entry.")
            profile = yoshi_profile_lock.normalize_profile(entry.get("profile"))
            if not profile:
                raise ValueError("Profile preferences are incomplete.")
            preferences = _validated(entry.get("preferences", {}))
            clean[key.casefold()] = {
                "profile": profile,
                "preferences": preferences,
                "updated_at": int(entry.get("updated_at") or 0),
            }
        return clean
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ProfilePreferencesError(
            "Yoshi's profile preferences need repair."
        ) from error


def _save_entries(entries):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({
        "version": 1,
        "profiles": entries,
    }, indent=2, ensure_ascii=False) + "\n"
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


def get_preferences(profile):
    name = yoshi_profile_lock.normalize_profile(profile)
    with _LOCK:
        entry = _load_entries().get(_profile_key(name))
    preferences = dict(DEFAULTS)
    if entry:
        preferences.update(entry["preferences"])
    preferences["accent_hex"] = (
        preferences["custom_color"]
        if preferences["theme"] == "tron"
        else ACCENTS[preferences["accent"]]
    )
    return preferences


def save_preferences(profile, updates):
    name = yoshi_profile_lock.normalize_profile(profile)
    if not name:
        raise ValueError("Profile is required.")

    with _LOCK:
        entries = _load_entries()
        existing = entries.get(_profile_key(name), {})
        merged = dict(DEFAULTS)
        merged.update(existing.get("preferences", {}))
        if not isinstance(updates, dict):
            raise ValueError("Profile preferences must be an object.")
        merged.update(updates)
        preferences = _validated(merged)
        entries[_profile_key(name)] = {
            "profile": name,
            "preferences": preferences,
            "updated_at": int(time.time()),
        }
        _save_entries(entries)
    return get_preferences(name)


def remove_preferences(profile):
    with _LOCK:
        entries = _load_entries()
        removed = entries.pop(_profile_key(profile), None)
        if removed is not None:
            _save_entries(entries)
    return removed is not None


def data_file_valid():
    try:
        with _LOCK:
            _load_entries()
        return True
    except ProfilePreferencesError:
        return False


def is_profile_under_18(profile):
    try:
        import Doshie_roles
        role_info = Doshie_roles.role_flags(profile)
        if role_info.get("is_child"):
            return True
    except Exception:
        pass

    prefs = get_preferences(profile)
    access_role = str(prefs.get("access_role", "")).casefold()
    if access_role == "child":
        return True

    age = prefs.get("age", 18)
    try:
        if int(age) < 18:
            return True
    except (ValueError, TypeError):
        pass

    return False

