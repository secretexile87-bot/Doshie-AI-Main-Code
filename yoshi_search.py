import html
import os
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
from html.parser import HTMLParser
from pathlib import Path

WEB_TIMEOUT_SECONDS = 7
WEB_RESPONSE_LIMIT = 1_000_000
WEB_CACHE_SECONDS = 5 * 60
MAX_DEVICE_RESULTS = 60
MAX_DEVICE_SCAN = 6000
MAX_DEVICE_DEPTH = 5

APPROVED_ROOTS = {
    "Desktop": Path.home() / "Desktop",
    "Documents": Path.home() / "Documents",
    "Downloads": Path.home() / "Downloads",
    "Pictures": Path.home() / "Pictures",
    "Music": Path.home() / "Music",
    "Videos": Path.home() / "Videos",
}
SENSITIVE_SUFFIXES = {
    ".key", ".pem", ".p12", ".pfx", ".crt", ".db", ".sqlite",
    ".sqlite3", ".kdbx", ".env", ".secret",
}
_WEB_CACHE = {}
_CACHE_LOCK = threading.RLock()


def _clean_query(value, maximum=180):
    query = " ".join(str(value or "").split()).strip()
    if len(query) < 2:
        raise ValueError("Search for at least two characters.")
    if len(query) > maximum:
        raise ValueError(f"Search must be {maximum} characters or fewer.")
    return query


def _safe_external_url(value):
    candidate = html.unescape(str(value or "").strip())
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    parsed = urllib.parse.urlparse(candidate)
    if parsed.hostname in {"duckduckgo.com", "www.duckduckgo.com"}:
        redirected = urllib.parse.parse_qs(parsed.query).get("uddg", [""])[0]
        if redirected:
            candidate = urllib.parse.unquote(redirected)
            parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    if parsed.username or parsed.password:
        return ""
    return urllib.parse.urlunparse(parsed._replace(fragment=""))


def _provider_urls(query):
    encoded = urllib.parse.quote_plus(query)
    return {
        "google": f"https://www.google.com/search?q={encoded}",
        "duckduckgo": f"https://duckduckgo.com/?q={encoded}",
        "bing": f"https://www.bing.com/search?q={encoded}",
    }


class _DuckDuckGoParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results = []
        self._anchor = None
        self._title_parts = []
        self._snippet_index = None
        self._snippet_parts = []

    @staticmethod
    def _classes(attributes):
        values = dict(attributes).get("class", "")
        return set(values.split())
    def handle_starttag(self, tag, attributes):
        classes = self._classes(attributes)
        values = dict(attributes)
        if tag == "a" and "result__a" in classes:
            url = _safe_external_url(values.get("href"))
            if url:
                self._anchor = url
                self._title_parts = []
        elif "result__snippet" in classes and self.results:
            self._snippet_index = len(self.results) - 1
            self._snippet_parts = []

    def handle_data(self, data):
        if self._anchor:
            self._title_parts.append(data)
        elif self._snippet_index is not None:
            self._snippet_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._anchor:
            title = " ".join("".join(self._title_parts).split())
            if title and len(self.results) < 10:
                parsed = urllib.parse.urlparse(self._anchor)
                self.results.append({
                    "title": title[:220],
                    "url": self._anchor,
                    "domain": parsed.hostname or "",
                    "snippet": "",
                })
            self._anchor = None
            self._title_parts = []
        elif self._snippet_index is not None and tag in {"a", "div"}:
            snippet = " ".join("".join(self._snippet_parts).split())
            if 0 <= self._snippet_index < len(self.results):
                self.results[self._snippet_index]["snippet"] = snippet[:360]
            self._snippet_index = None
            self._snippet_parts = []


def web_search(value):
    query = _clean_query(value)
    key = query.casefold()
    now = time.time()
    with _CACHE_LOCK:
        cached = _WEB_CACHE.get(key)
        if cached and now - cached["saved_at"] < WEB_CACHE_SECONDS:
            payload = dict(cached["payload"])
            payload["cached"] = True
            return payload

    endpoint = (
        "https://www.bing.com/search?format=rss&q=" +
        urllib.parse.quote_plus(query)
    )
    web_request = urllib.request.Request(
        endpoint,
        headers={
            "User-Agent": "Mozilla/5.0 DiYoshi/1.0",
            "Accept": "application/rss+xml,application/xml,text/xml",
        },
    )
    try:
        with urllib.request.urlopen(
            web_request,
            timeout=WEB_TIMEOUT_SECONDS,
        ) as response:
            content_type = response.headers.get("Content-Type", "")
            if "xml" not in content_type.casefold():
                raise RuntimeError("Unexpected search response.")
            raw = response.read(WEB_RESPONSE_LIMIT + 1)
            if len(raw) > WEB_RESPONSE_LIMIT:
                raise RuntimeError("Search response was too large.")
        root = ElementTree.fromstring(raw)
    except Exception as error:
        raise RuntimeError("Web search is temporarily unavailable.") from error

    results = []
    for item in root.findall(".//item")[:8]:
        title = " ".join((item.findtext("title") or "").split())
        url = _safe_external_url(item.findtext("link"))
        snippet = " ".join(
            html.unescape(item.findtext("description") or "").split()
        )
        if not title or not url:
            continue
        results.append({
            "title": title[:220],
            "url": url,
            "domain": urllib.parse.urlparse(url).hostname or "",
            "snippet": snippet[:360],
        })

    payload = {
        "query": query,
        "results": results,
        "providers": _provider_urls(query),
        "source": "Bing",
        "cached": False,
    }
    with _CACHE_LOCK:
        _WEB_CACHE[key] = {
            "saved_at": now,
            "payload": payload,
        }
    return dict(payload)


def approved_locations():
    locations = []
    for label, root in APPROVED_ROOTS.items():
        try:
            available = root.exists() and root.is_dir()
        except OSError:
            available = False
        locations.append({"name": label, "available": available})
    return locations


def _safe_relative_path(root, path):
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except (OSError, ValueError):
        return ""


def device_search(value):
    original_query = _clean_query(value, maximum=100)
    query = original_query.casefold()
    results = []
    scanned = 0

    for root_name, root in APPROVED_ROOTS.items():
        if not root.exists() or not root.is_dir():
            continue

        for current, directories, files in os.walk(root, followlinks=False):
            current_path = Path(current)
            try:
                depth = len(current_path.relative_to(root).parts)
            except ValueError:
                directories[:] = []
                continue

            directories[:] = [
                name for name in directories
                if not name.startswith(".") and depth < MAX_DEVICE_DEPTH
            ]
            names = [(name, True) for name in directories]
            names.extend(
                (name, False) for name in files
                if not name.startswith(".")
            )

            for name, is_directory in names:
                scanned += 1
                if scanned > MAX_DEVICE_SCAN:
                    break
                if query not in name.casefold():
                    continue

                path = current_path / name
                if path.is_symlink():
                    continue
                if (
                    not is_directory and
                    path.suffix.casefold() in SENSITIVE_SUFFIXES
                ):
                    continue
                relative = _safe_relative_path(root, path)
                if not relative:
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                results.append({
                    "name": name[:240],
                    "type": "folder" if is_directory else "file",
                    "location": root_name,
                    "relative_path": relative,
                    "size": 0 if is_directory else int(stat.st_size),
                    "modified": int(stat.st_mtime),
                })
                if len(results) >= MAX_DEVICE_RESULTS:
                    break

            if (
                scanned > MAX_DEVICE_SCAN or
                len(results) >= MAX_DEVICE_RESULTS
            ):
                break
        if scanned > MAX_DEVICE_SCAN or len(results) >= MAX_DEVICE_RESULTS:
            break

    results.sort(key=lambda item: (
        item["type"] != "folder",
        item["name"].casefold(),
        item["location"],
    ))
    return {
        "query": original_query,
        "results": results,
        "locations": approved_locations(),
        "scanned": scanned,
        "limited": scanned > MAX_DEVICE_SCAN,
    }


def service_ready():
    return (
        callable(web_search)
        and callable(device_search)
        and bool(APPROVED_ROOTS)
    )
