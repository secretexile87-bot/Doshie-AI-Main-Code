"""Private Spotify Premium integration for Yoshi."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


ACCOUNTS_BASE = "https://accounts.spotify.com"
API_BASE = "https://api.spotify.com/v1"
DATA_DIR = Path(
    os.environ.get(
        "YOSHI_SPOTIFY_DIR",
        str(Path.home() / ".local/share/yoshi/spotify"),
    )
).expanduser()
SCOPES = (
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-modify-playback-state",
    "playlist-read-private",
    "playlist-read-collaborative",
)
FILE_LOCK = threading.RLock()
AUTH_LOCK = threading.Lock()
AUTH_STATES: dict[str, dict] = {}
AUTH_STATE_TTL = 10 * 60


class SpotifyError(RuntimeError):
    """A safe, user-facing Spotify integration error."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _prepare_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        DATA_DIR.chmod(0o700)
    except OSError:
        pass


def _config_path() -> Path:
    return DATA_DIR / "config.json"


def _profile_name(profile: object) -> str:
    value = " ".join(str(profile or "Hermes").split()).strip()
    return value[:80] or "Hermes"


def _token_path(profile: object) -> Path:
    name = _profile_name(profile)
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    digest = hashlib.sha256(name.casefold().encode("utf-8")).hexdigest()[:8]
    return DATA_DIR / f"token-{slug or 'profile'}-{digest}.json"


def _read_json(path: Path) -> dict:
    with FILE_LOCK:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return {}
    return payload if isinstance(payload, dict) else {}


def _write_private_json(path: Path, payload: dict) -> None:
    _prepare_directory()
    temporary = path.with_name(
        f".{path.name}.{secrets.token_hex(6)}.tmp"
    )
    descriptor = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            json.dump(payload, handle, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def get_client_id() -> str:
    environment = os.environ.get("YOSHI_SPOTIFY_CLIENT_ID", "").strip()
    if environment:
        return environment
    return str(_read_json(_config_path()).get("client_id") or "").strip()


def save_client_id(value: object) -> str:
    client_id = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", client_id):
        raise ValueError("Enter the Client ID from your Spotify developer app.")
    with FILE_LOCK:
        _write_private_json(_config_path(), {"client_id": client_id})
    return client_id


def configuration() -> dict:
    client_id = get_client_id()
    return {
        "configured": bool(client_id),
        "client_id": client_id,
        "scopes": list(SCOPES),
    }


def connected(profile: object = "Hermes") -> bool:
    token = _read_json(_token_path(profile))
    return bool(token.get("refresh_token") or token.get("access_token"))


def disconnect(profile: object = "Hermes") -> None:
    with FILE_LOCK:
        try:
            _token_path(profile).unlink()
        except FileNotFoundError:
            pass


def _friendly_error(status: int, payload: object) -> str:
    detail = ""
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            detail = str(error.get("message") or error.get("reason") or "")
        elif error:
            detail = str(error)
        detail = str(payload.get("error_description") or detail)
    if status == 401:
        return "Spotify needs to be connected again."
    if status == 403:
        return "Spotify did not grant permission for that action."
    if status == 404:
        return (
            "No active Spotify player was found. Open Spotify on a device, "
            "start any song once, and try again."
        )
    if status == 429:
        return "Spotify is receiving too many requests. Try again shortly."
    if status == 400 and detail:
        return f"Spotify rejected the request: {detail[:180]}"
    return "Spotify could not complete that request."


def _http_json(
    url: str,
    method: str = "GET",
    *,
    payload: dict | None = None,
    form: dict | None = None,
    headers: dict | None = None,
    timeout: float = 15.0,
):
    request_headers = dict(headers or {})
    body = None
    if form is not None:
        body = urlencode(form).encode("utf-8")
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(512 * 1024)
    except HTTPError as error:
        raw = error.read(64 * 1024)
        try:
            error_payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            error_payload = {}
        raise SpotifyError(
            _friendly_error(error.code, error_payload),
            status=error.code,
        ) from error
    except (OSError, URLError, TimeoutError) as error:
        raise SpotifyError("Spotify is unreachable right now.") from error

    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SpotifyError("Spotify returned an invalid response.") from error


def redirect_uri_supported(redirect_uri: object) -> bool:
    try:
        parsed = urlparse(str(redirect_uri or ""))
    except ValueError:
        return False
    if parsed.username or parsed.password:
        return False
    if parsed.scheme in {"http", "https"} and bool(parsed.hostname):
        return True
    return False


def begin_authorization(profile: object, redirect_uri: object) -> str:
    client_id = get_client_id()
    if not client_id:
        raise SpotifyError("Add your Spotify Client ID first.")

    redirect = str(redirect_uri or "").strip()
    if not redirect_uri_supported(redirect):
        raise SpotifyError(
            "Spotify setup must use HTTPS or the TECRA address "
            "http://127.0.0.1:5000."
        )

    verifier = secrets.token_urlsafe(64)[:128]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    state = secrets.token_urlsafe(32)
    now = time.time()

    with AUTH_LOCK:
        expired = [
            key
            for key, value in AUTH_STATES.items()
            if now - float(value.get("created_at", 0)) > AUTH_STATE_TTL
        ]
        for key in expired:
            AUTH_STATES.pop(key, None)
        AUTH_STATES[state] = {
            "profile": _profile_name(profile),
            "redirect_uri": redirect,
            "verifier": verifier,
            "created_at": now,
        }

    query = urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect,
        "state": state,
        "scope": " ".join(SCOPES),
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    })
    return f"{ACCOUNTS_BASE}/authorize?{query}"


def _store_token(profile: object, payload: dict, existing: dict | None = None) -> dict:
    current = dict(existing or {})
    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise SpotifyError("Spotify did not return an access token.")

    current.update({
        "profile": _profile_name(profile),
        "access_token": access_token,
        "token_type": str(payload.get("token_type") or "Bearer"),
        "scope": str(payload.get("scope") or current.get("scope") or ""),
        "expires_at": time.time() + int(payload.get("expires_in") or 3600),
        "updated_at": time.time(),
    })
    refresh_token = payload.get("refresh_token")
    if refresh_token:
        current["refresh_token"] = str(refresh_token)
    _write_private_json(_token_path(profile), current)

    # Mirror token to Music Player service cache
    try:
        mp_cache = Path("/home/doshie/.gemini/antigravity-cli/scratch/music-player/cache/.spotify_cache")
        mp_cache.parent.mkdir(parents=True, exist_ok=True)
        mp_data = {
            "access_token": current["access_token"],
            "token_type": current.get("token_type", "Bearer"),
            "expires_in": int(payload.get("expires_in") or 3600),
            "refresh_token": current.get("refresh_token", ""),
            "scope": current.get("scope", ""),
            "expires_at": int(current.get("expires_at", time.time() + 3600))
        }
        mp_cache.write_text(json.dumps(mp_data), encoding="utf-8")
        mp_cache.chmod(0o600)
    except Exception:
        pass

    return current


def complete_authorization(state: object, code: object) -> str:
    state_value = str(state or "")
    with AUTH_LOCK:
        pending = AUTH_STATES.pop(state_value, None)
    if not pending:
        raise SpotifyError("Spotify authorization expired. Start again.")
    if time.time() - pending["created_at"] > AUTH_STATE_TTL:
        raise SpotifyError("Spotify authorization expired. Start again.")

    payload = _http_json(
        f"{ACCOUNTS_BASE}/api/token",
        method="POST",
        form={
            "client_id": get_client_id(),
            "grant_type": "authorization_code",
            "code": str(code or ""),
            "redirect_uri": pending["redirect_uri"],
            "code_verifier": pending["verifier"],
        },
    )
    profile = pending["profile"]
    token = _store_token(profile, payload or {})
    try:
        account = current_account(profile)
        token["account"] = account
        _write_private_json(_token_path(profile), token)
    except SpotifyError:
        pass
    return profile


def _refresh_token(profile: object, existing: dict) -> dict:
    refresh_token = str(existing.get("refresh_token") or "")
    if not refresh_token:
        raise SpotifyError("Spotify needs to be connected again.", status=401)
    payload = _http_json(
        f"{ACCOUNTS_BASE}/api/token",
        method="POST",
        form={
            "client_id": get_client_id(),
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    return _store_token(profile, payload or {}, existing=existing)


def _valid_token(profile: object, force_refresh: bool = False) -> dict:
    token = _read_json(_token_path(profile))
    if not token:
        raise SpotifyError("Connect Spotify for this Yoshi profile first.")
    expires_at = float(token.get("expires_at") or 0)
    if force_refresh or expires_at <= time.time() + 30:
        token = _refresh_token(profile, token)
    return token


def _api(
    profile: object,
    method: str,
    path: str,
    *,
    query: dict | None = None,
    payload: dict | None = None,
    retry: bool = True,
):
    token = _valid_token(profile)
    url = f"{API_BASE}{path}"
    if query:
        url += "?" + urlencode(query, doseq=True)
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    try:
        return _http_json(
            url,
            method=method,
            payload=payload,
            headers=headers,
        )
    except SpotifyError as error:
        if error.status != 401 or not retry:
            raise
    token = _valid_token(profile, force_refresh=True)
    headers["Authorization"] = f"Bearer {token['access_token']}"
    return _http_json(
        url,
        method=method,
        payload=payload,
        headers=headers,
    )


def current_account(profile: object = "Hermes") -> dict:
    payload = _api(profile, "GET", "/me") or {}
    images = payload.get("images") or []
    return {
        "id": str(payload.get("id") or ""),
        "name": str(payload.get("display_name") or payload.get("id") or ""),
        "image": str(images[0].get("url") or "") if images else "",
    }


def status(profile: object = "Hermes") -> dict:
    config = configuration()
    token = _read_json(_token_path(profile))
    return {
        **config,
        "profile": _profile_name(profile),
        "connected": bool(
            token.get("refresh_token") or token.get("access_token")
        ),
        "account": token.get("account") or {},
    }


def _track(item: object) -> dict:
    item = item if isinstance(item, dict) else {}
    artists = item.get("artists") or []
    album = item.get("album") or {}
    images = album.get("images") or item.get("images") or []
    external = item.get("external_urls") or {}
    return {
        "name": str(item.get("name") or "Unknown"),
        "artists": ", ".join(
            str(artist.get("name") or "")
            for artist in artists
            if isinstance(artist, dict)
        ),
        "album": str(album.get("name") or ""),
        "uri": str(item.get("uri") or ""),
        "url": str(external.get("spotify") or ""),
        "image": str(images[0].get("url") or "") if images else "",
        "duration_ms": int(item.get("duration_ms") or 0),
    }


def search_tracks(
    profile: object,
    query_text: object,
    limit: int = 5,
) -> list[dict]:
    query_value = " ".join(str(query_text or "").split()).strip()
    if not query_value:
        raise SpotifyError("Tell me what song or artist to search for.")
    payload = _api(
        profile,
        "GET",
        "/search",
        query={
            "q": query_value[:200],
            "type": "track",
            "limit": max(1, min(10, int(limit))),
        },
    ) or {}
    items = (payload.get("tracks") or {}).get("items") or []
    return [_track(item) for item in items if isinstance(item, dict)]


def playlists(profile: object, limit: int = 10) -> list[dict]:
    payload = _api(
        profile,
        "GET",
        "/me/playlists",
        query={"limit": max(1, min(10, int(limit)))},
    ) or {}
    results = []
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        images = item.get("images") or []
        owner = item.get("owner") or {}
        collection = item.get("items") or item.get("tracks") or {}
        results.append({
            "name": str(item.get("name") or "Untitled playlist"),
            "uri": str(item.get("uri") or ""),
            "url": str((item.get("external_urls") or {}).get("spotify") or ""),
            "image": str(images[0].get("url") or "") if images else "",
            "owner": str(owner.get("display_name") or owner.get("id") or ""),
            "total": int(collection.get("total") or 0),
        })
    return results


def now_playing(profile: object) -> dict:
    payload = _api(profile, "GET", "/me/player")
    if not payload:
        return {"active": False, "is_playing": False}
    item = _track(payload.get("item"))
    device = payload.get("device") or {}
    return {
        "active": bool(payload.get("item")),
        "is_playing": bool(payload.get("is_playing")),
        "progress_ms": int(payload.get("progress_ms") or 0),
        "track": item,
        "device": {
            "id": str(device.get("id") or ""),
            "name": str(device.get("name") or ""),
            "type": str(device.get("type") or ""),
            "volume_percent": device.get("volume_percent"),
        },
    }


def control(
    profile: object,
    action: object,
    *,
    uri: object = "",
    context_uri: object = "",
    device_id: object = "",
) -> None:
    action_value = str(action or "").casefold().strip()
    device = str(device_id or "").strip()
    query = {"device_id": device} if device else None

    if action_value in {"play", "resume"}:
        body: dict = {}
        track_uri = str(uri or "").strip()
        playlist_uri = str(context_uri or "").strip()
        if track_uri:
            body["uris"] = [track_uri]
        if playlist_uri:
            body["context_uri"] = playlist_uri
        _api(profile, "PUT", "/me/player/play", query=query, payload=body)
        return
    if action_value == "pause":
        _api(profile, "PUT", "/me/player/pause", query=query)
        return
    if action_value == "next":
        _api(profile, "POST", "/me/player/next", query=query)
        return
    if action_value in {"previous", "back"}:
        _api(profile, "POST", "/me/player/previous", query=query)
        return
    raise SpotifyError("Unknown Spotify playback action.")


def search_and_play(profile: object, query_text: object) -> dict:
    results = search_tracks(profile, query_text, limit=5)
    if not results:
        raise SpotifyError(f"I couldn't find {str(query_text).strip()} on Spotify.")
    selected = results[0]
    control(profile, "play", uri=selected["uri"])
    return selected


def play_playlist(profile: object, context_uri: object) -> None:
    playlist_uri = str(context_uri or "").strip()
    if not playlist_uri.startswith("spotify:playlist:"):
        raise SpotifyError("Choose a valid Spotify playlist.")
    control(profile, "play", context_uri=playlist_uri)
