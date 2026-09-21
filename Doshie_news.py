import html
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime


CACHE_SECONDS = 10 * 60
FORCE_REFRESH_SECONDS = 30
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
USER_AGENT = "DiYoshiHome/1.0 (private family news reader)"
TOPICS = {
    "local": ("LOCAL · EL PASO", "El Paso Texas local news"),
    "national": ("NATIONAL", "United States national news"),
    "tech": ("TECH", "technology AI cybersecurity news"),
    "gaming": ("GAMING", "video games PC gaming news"),
    "family": ("FAMILY", "El Paso family community events"),
}
EL_PASO_MATTERS = "https://elpasomatters.org/feed/"
_CACHE = {}
_CACHE_LOCK = threading.RLock()


class NewsError(RuntimeError):
    pass
def _google_feed(query):
    encoded = urllib.parse.quote_plus(query)
    return (
        "https://news.google.com/rss/search?q=" + encoded
        + "&hl=en-US&gl=US&ceid=US:en"
    )


def _clean_text(value, limit=240):
    clean = html.unescape(str(value or ""))
    clean = " ".join(clean.split()).strip()
    return clean[:limit]


def _safe_url(value):
    clean = html.unescape(str(value or "")).strip()
    try:
        parsed = urllib.parse.urlparse(clean)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return clean


def _fetch_feed(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
    except Exception as error:
        raise NewsError("News feed is unavailable.") from error
    if len(data) > MAX_RESPONSE_BYTES:
        raise NewsError("News feed was too large.")
    return data


def _published_timestamp(value):
    try:
        parsed = parsedate_to_datetime(str(value or ""))
        return int(parsed.timestamp())
    except (TypeError, ValueError, OverflowError):
        return 0


def _feed_source(root, item, fallback):
    source = item.findtext("source")
    if source:
        return _clean_text(source, 80)
    channel = root.find("./channel/title")
    return _clean_text(channel.text if channel is not None else fallback, 80)


def _parse_feed(payload, fallback_source):
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise NewsError("News feed could not be read.") from error
    results = []
    for item in root.findall(".//item"):
        title = _clean_text(item.findtext("title"), 220)
        url = _safe_url(item.findtext("link"))
        if not title or not url:
            continue
        results.append({
            "title": title,
            "url": url,
            "source": _feed_source(root, item, fallback_source),
            "published_at": _published_timestamp(item.findtext("pubDate")),
        })
        if len(results) >= 24:
            break
    return results


def _dedupe(items):
    seen = set()
    clean = []
    for item in items:
        key = " ".join(item["title"].casefold().split())
        if not key or key in seen:
            continue
        seen.add(key)
        clean.append(item)
    clean.sort(key=lambda item: item.get("published_at", 0), reverse=True)
    return clean


def _fetch_topic(topic):
    _label, query = TOPICS[topic]
    items = []
    errors = []
    feeds = []
    if topic == "local":
        feeds.append((EL_PASO_MATTERS, "El Paso Matters"))
    feeds.append((_google_feed(query), "Google News"))

    for url, source in feeds:
        try:
            items.extend(_parse_feed(_fetch_feed(url), source))
        except NewsError as error:
            errors.append(str(error))

    items = _dedupe(items)
    if not items:
        raise NewsError(errors[0] if errors else "No news is available.")
    return items[:16]


def get_headlines(topic="local", force=False, limit=12):
    topic = str(topic or "local").strip().casefold()
    if topic not in TOPICS:
        raise ValueError("Choose a supported news topic.")
    try:
        limit = max(1, min(int(limit), 16))
    except (TypeError, ValueError):
        limit = 12

    now = time.time()
    with _CACHE_LOCK:
        cached = _CACHE.get(topic)
        age = now - cached["fetched_at"] if cached else None

    should_fetch = (
        cached is None
        or age >= CACHE_SECONDS
        or (force and age >= FORCE_REFRESH_SECONDS)
    )
    stale = False
    error_message = ""
    if should_fetch:
        try:
            fresh_items = _fetch_topic(topic)
            cached = {
                "items": fresh_items,
                "fetched_at": int(now),
            }
            with _CACHE_LOCK:
                _CACHE[topic] = cached
            age = 0
        except NewsError as error:
            error_message = str(error)
            if cached is None:
                cached = {"items": [], "fetched_at": 0}
            else:
                stale = True

    label = TOPICS[topic][0]
    return {
        "topic": topic,
        "label": label,
        "items": list(cached["items"][:limit]),
        "fetched_at": cached["fetched_at"],
        "cached": not should_fetch or stale,
        "stale": stale,
        "error": error_message,
    }


def search_news(query, limit=6):
    clean = _clean_text(query, 120)
    if not clean:
        return get_headlines("local", limit=limit)
    try:
        url = _google_feed(clean)
        items = _parse_feed(_fetch_feed(url), "Google News")
        items = _dedupe(items)
        if not items:
            return get_headlines("local", limit=limit)
        return {
            "topic": "search",
            "label": f"NEWS · {clean.upper()}",
            "items": items[:limit],
            "fetched_at": int(time.time()),
        }
    except Exception:
        return get_headlines("local", limit=limit)


def service_ready():
    return (
        set(TOPICS) == {"local", "national", "tech", "gaming", "family"}
        and callable(get_headlines)
        and callable(_safe_url)
    )


def clear_cache():
    with _CACHE_LOCK:
        _CACHE.clear()

