"""Private, profile-aware DiYoshi messaging storage and protocol.

This module keeps peer messages separate from the AI conversation history.
It uses SQLite with short-lived connections so the existing Flask service can
serve the inbox safely without adding a new dependency.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import threading
import time
import uuid

DB_PATH = Path(__file__).with_name("messaging.db")
MAX_MESSAGE_LENGTH = 8000
MAX_GROUP_MEMBERS = 32
ONLINE_SECONDS = 90
_db_lock = threading.RLock()


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connect():
    """Yield one short-lived transaction and always release its file handle."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _db_lock, _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL CHECK (kind IN ('direct', 'group')),
                title TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversation_members (
                conversation_id TEXT NOT NULL,
                profile TEXT NOT NULL,
                joined_at TEXT NOT NULL,
                last_read_id INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (conversation_id, profile),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                    ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                sender_profile TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                edited_at TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                    ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS presence (
                profile TEXT PRIMARY KEY,
                last_seen REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS messages_conversation_idx
                ON messages(conversation_id, id);
            CREATE INDEX IF NOT EXISTS members_profile_idx
                ON conversation_members(profile, conversation_id);
            """
        )


def _clean_profile(value):
    return " ".join(str(value or "").split()).strip()


def _member_row(conn, conversation_id, profile):
    return conn.execute(
        """SELECT 1 FROM conversation_members
           WHERE conversation_id = ? AND lower(profile) = lower(?)""",
        (conversation_id, profile),
    ).fetchone()


def _require_member(conn, conversation_id, profile):
    if not _member_row(conn, conversation_id, profile):
        raise PermissionError("You are not a member of this conversation.")


def touch_presence(profile):
    profile = _clean_profile(profile)
    if not profile:
        return
    with _db_lock, _connect() as conn:
        conn.execute(
            """INSERT INTO presence(profile, last_seen) VALUES (?, ?)
               ON CONFLICT(profile) DO UPDATE SET last_seen=excluded.last_seen""",
            (profile, time.time()),
        )


def is_online(conn, profile):
    row = conn.execute(
        "SELECT last_seen FROM presence WHERE lower(profile) = lower(?)",
        (profile,),
    ).fetchone()
    return bool(row and time.time() - float(row["last_seen"]) <= ONLINE_SECONDS)


def people(profiles, active_profile):
    active_profile = _clean_profile(active_profile)
    with _db_lock, _connect() as conn:
        return [
            {
                "name": item["name"],
                "role": item.get("role", "Family"),
                "initials": item.get("initials", "Y"),
                "avatar_url": item.get("avatar_url"),
                "is_admin": bool(item.get("is_admin")),
                "online": is_online(conn, item["name"]),
                "self": item["name"].casefold() == active_profile.casefold(),
            }
            for item in profiles
        ]


def _direct_id(conn, members):
    wanted = {item.casefold() for item in members}
    rows = conn.execute(
        """SELECT c.id
           FROM conversations c
           JOIN conversation_members m ON m.conversation_id = c.id
           WHERE c.kind = 'direct'
           GROUP BY c.id
           HAVING COUNT(*) = 2""",
    ).fetchall()
    for row in rows:
        found = {
            item["profile"].casefold()
            for item in conn.execute(
                "SELECT profile FROM conversation_members WHERE conversation_id = ?",
                (row["id"],),
            ).fetchall()
        }
        if found == wanted:
            return row["id"]
    return None


def create_conversation(profile, members, title="", kind="direct"):
    profile = _clean_profile(profile)
    unique = []
    seen = set()
    for value in [profile] + list(members or []):
        clean = _clean_profile(value)
        if clean and clean.casefold() not in seen:
            seen.add(clean.casefold())
            unique.append(clean)
    kind = "group" if str(kind).casefold() == "group" else "direct"
    if kind == "direct" and len(unique) != 2:
        raise ValueError("A direct chat needs exactly two people.")
    if kind == "group" and len(unique) < 2:
        raise ValueError("A group chat needs at least two people.")
    if len(unique) > MAX_GROUP_MEMBERS:
        raise ValueError("That group is too large.")
    if profile.casefold() not in {item.casefold() for item in unique}:
        raise PermissionError("The creator must belong to the conversation.")

    with _db_lock, _connect() as conn:
        if kind == "direct":
            existing = _direct_id(conn, unique)
            if existing:
                return existing
        conversation_id = uuid.uuid4().hex
        now = _now()
        clean_title = _clean_profile(title)
        if kind == "group" and not clean_title:
            clean_title = "DiYoshi group"
        conn.execute(
            """INSERT INTO conversations
               (id, kind, title, created_by, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (conversation_id, kind, clean_title, profile, now, now),
        )
        conn.executemany(
            """INSERT INTO conversation_members
               (conversation_id, profile, joined_at) VALUES (?, ?, ?)""",
            [(conversation_id, item, now) for item in unique],
        )
        return conversation_id
def _conversation_payload(conn, row, profile):
    members = [
        item["profile"]
        for item in conn.execute(
            """SELECT profile FROM conversation_members
               WHERE conversation_id = ? ORDER BY lower(profile)""",
            (row["id"],),
        ).fetchall()
    ]
    last = conn.execute(
        """SELECT id, sender_profile, body, created_at
           FROM messages WHERE conversation_id = ?
           ORDER BY id DESC LIMIT 1""",
        (row["id"],),
    ).fetchone()
    read = conn.execute(
        """SELECT last_read_id FROM conversation_members
           WHERE conversation_id = ? AND lower(profile) = lower(?)""",
        (row["id"], profile),
    ).fetchone()
    last_read_id = int(read["last_read_id"]) if read else 0
    unread = conn.execute(
        """SELECT COUNT(*) AS count FROM messages
           WHERE conversation_id = ? AND id > ?
             AND lower(sender_profile) <> lower(?)""",
        (row["id"], last_read_id, profile),
    ).fetchone()["count"]
    title = row["title"]
    if row["kind"] == "direct":
        title = next(
            (item for item in members
             if item.casefold() != profile.casefold()),
            "Direct chat",
        )
    return {
        "id": row["id"],
        "kind": row["kind"],
        "title": title or "DiYoshi group",
        "members": members,
        "updated_at": row["updated_at"],
        "last_message": dict(last) if last else None,
        "unread_count": int(unread),
    }


def list_conversations(profile):
    profile = _clean_profile(profile)
    with _db_lock, _connect() as conn:
        rows = conn.execute(
            """SELECT c.* FROM conversations c
               JOIN conversation_members m ON m.conversation_id = c.id
               WHERE lower(m.profile) = lower(?)
               ORDER BY c.updated_at DESC""",
            (profile,),
        ).fetchall()
        return [_conversation_payload(conn, row, profile) for row in rows]


def get_messages(conversation_id, profile, after_id=0, limit=100):
    conversation_id = str(conversation_id or "").strip()
    profile = _clean_profile(profile)
    try:
        after_id = max(0, int(after_id or 0))
    except (TypeError, ValueError):
        after_id = 0
    try:
        limit = min(200, max(1, int(limit or 100)))
    except (TypeError, ValueError):
        limit = 100

    with _db_lock, _connect() as conn:
        _require_member(conn, conversation_id, profile)
        rows = conn.execute(
            """SELECT id, conversation_id, sender_profile, body,
                      created_at, edited_at
               FROM messages
               WHERE conversation_id = ? AND id > ?
               ORDER BY id ASC LIMIT ?""",
            (conversation_id, after_id, limit),
        ).fetchall()
        return [dict(item) for item in rows]


def send_message(conversation_id, profile, body):
    conversation_id = str(conversation_id or "").strip()
    profile = _clean_profile(profile)
    body = str(body or "").strip()
    if not body:
        raise ValueError("Message cannot be empty.")
    if len(body) > MAX_MESSAGE_LENGTH:
        raise ValueError("Message is too long.")
    with _db_lock, _connect() as conn:
        _require_member(conn, conversation_id, profile)
        now = _now()
        result = conn.execute(
            """INSERT INTO messages
               (conversation_id, sender_profile, body, created_at)
               VALUES (?, ?, ?, ?)""",
            (conversation_id, profile, body, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        conn.execute(
            """UPDATE conversation_members SET last_read_id = ?
               WHERE conversation_id = ? AND lower(profile) = lower(?)""",
            (result.lastrowid, conversation_id, profile),
        )
        row = conn.execute(
            """SELECT id, conversation_id, sender_profile, body,
                      created_at, edited_at
               FROM messages WHERE id = ?""",
            (result.lastrowid,),
        ).fetchone()
        return dict(row)
def mark_read(conversation_id, profile, message_id=None):
    conversation_id = str(conversation_id or "").strip()
    profile = _clean_profile(profile)
    with _db_lock, _connect() as conn:
        _require_member(conn, conversation_id, profile)
        if message_id is None:
            row = conn.execute(
                """SELECT COALESCE(MAX(id), 0) AS id FROM messages
                   WHERE conversation_id = ?""",
                (conversation_id,),
            ).fetchone()
            message_id = row["id"]
        try:
            message_id = max(0, int(message_id))
        except (TypeError, ValueError):
            message_id = 0
        conn.execute(
            """UPDATE conversation_members
               SET last_read_id = MAX(last_read_id, ?)
               WHERE conversation_id = ? AND lower(profile) = lower(?)""",
            (message_id, conversation_id, profile),
        )
        return {"conversation_id": conversation_id, "last_read_id": message_id}


def conversation_exists(conversation_id, profile):
    with _db_lock, _connect() as conn:
        return bool(_member_row(conn, conversation_id, profile))


init_db()


def _ensure_typing_table():
    with _db_lock, _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS typing (
                conversation_id TEXT NOT NULL,
                profile TEXT NOT NULL,
                last_seen REAL NOT NULL,
                PRIMARY KEY (conversation_id, profile),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                    ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS typing_conversation_idx
               ON typing(conversation_id, last_seen)"""
        )


def set_typing(conversation_id, profile, typing):
    conversation_id = str(conversation_id or "").strip()
    profile = _clean_profile(profile)
    with _db_lock, _connect() as conn:
        _require_member(conn, conversation_id, profile)
        if typing:
            conn.execute(
                """INSERT INTO typing(conversation_id, profile, last_seen)
                   VALUES (?, ?, ?)
                   ON CONFLICT(conversation_id, profile)
                   DO UPDATE SET last_seen=excluded.last_seen""",
                (conversation_id, profile, time.time()),
            )
        else:
            conn.execute(
                """DELETE FROM typing
                   WHERE conversation_id = ? AND lower(profile) = lower(?)""",
                (conversation_id, profile),
            )
        return typing_users_locked(conn, conversation_id, profile)
def typing_users_locked(conn, conversation_id, profile):
    cutoff = time.time() - 8
    conn.execute("DELETE FROM typing WHERE last_seen < ?", (cutoff,))
    rows = conn.execute(
        """SELECT t.profile FROM typing t
           JOIN conversation_members m
             ON m.conversation_id = t.conversation_id
            AND lower(m.profile) = lower(t.profile)
           WHERE t.conversation_id = ?
             AND lower(t.profile) <> lower(?)
             AND t.last_seen >= ?
           ORDER BY lower(t.profile)""",
        (conversation_id, profile, cutoff),
    ).fetchall()
    return [row["profile"] for row in rows]


def get_typing_users(conversation_id, profile):
    conversation_id = str(conversation_id or "").strip()
    profile = _clean_profile(profile)
    with _db_lock, _connect() as conn:
        _require_member(conn, conversation_id, profile)
        return typing_users_locked(conn, conversation_id, profile)


_ensure_typing_table()
