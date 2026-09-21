from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import urllib.request
import yoshi_settings
import yoshi_summary
import yoshi_tool_agent
import urllib.error
import json
import time
import os
import sys
import re

HOME = os.path.expanduser("~")
YOSHI_DIR = os.path.join(HOME, "yoshi")
DB_PATH = os.path.join(YOSHI_DIR, "memory.db")
IDENTITY_PATH = os.environ.get(
    "YOSHI_IDENTITY_PATH",
    os.path.join(YOSHI_DIR, "identity.txt")
)
PROFILE = os.environ.get("YOSHI_PROFILE", "companion").strip().lower()
FORCE_MODE = os.environ.get("YOSHI_FORCE_MODE", "").strip().lower()
MODEL_PID_PATH = os.path.join(YOSHI_DIR, ".yoshi_model.pid")
MODEL_LOG_PATH = os.path.join(YOSHI_DIR, "yoshi_model.log")
SERVER = os.environ.get(
    "YOSHI_LLAMA_SERVER",
    os.path.join(HOME, "llama.cpp", "build", "bin", "llama-server")
)


def _environment_int(name, default, minimum=1):
    try:
        return max(minimum, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


def _environment_float(name, default, minimum=0.0, maximum=2.0):
    try:
        value = float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


MODEL = os.environ.get(
    "YOSHI_MODEL",
    "qwen2.5:14b"
)
CODING_MODEL = os.environ.get(
    "YOSHI_CODING_MODEL",
    "qwen2.5-coder:7b"
)
FAST_MODEL = os.environ.get(
    "YOSHI_FAST_MODEL",
    "qwen3.5:4b"
)
ADVANCED_MODEL = os.environ.get(
    "YOSHI_ADVANCED_MODEL",
    "deepseek-r1:14b"
)
HEAVYWEIGHT_MODEL = os.environ.get(
    "YOSHI_HEAVYWEIGHT_MODEL",
    "deepseek-r1:32b"
)
VISION_MODEL = os.environ.get(
    "YOSHI_VISION_MODEL",
    "moondream"
)
FALLBACK_VISION_MODEL = os.environ.get(
    "YOSHI_FALLBACK_VISION_MODEL",
    "moondream"
)
BRAIN_MODELS = {
    "fast": FAST_MODEL,
    "balanced": MODEL,
    "coding": CODING_MODEL,
    "advanced": ADVANCED_MODEL,
    "heavyweight": HEAVYWEIGHT_MODEL,
    "vision": VISION_MODEL,
}
PORT = _environment_int("YOSHI_MODEL_PORT", 11434, minimum=1024)
FALLBACK_MODEL_PORT = _environment_int(
    "YOSHI_FALLBACK_MODEL_PORT", 11434, minimum=1024
)
CONTEXT_SIZE = _environment_int("YOSHI_CONTEXT_SIZE", 2048, minimum=512)
MODEL_THREADS = _environment_int("YOSHI_MODEL_THREADS", 4)
MAX_RESPONSE_TOKENS = _environment_int(
    "YOSHI_MAX_RESPONSE_TOKENS",
    500,
    minimum=64
)
MODEL_TEMPERATURE = _environment_float(
    "YOSHI_MODEL_TEMPERATURE",
    0.35
)
MODEL_TIMEOUT_SECONDS = _environment_int(
    "YOSHI_MODEL_TIMEOUT_SECONDS",
    180,
    minimum=10
)
MODEL_URLS = tuple(dict.fromkeys((
    f"http://127.0.0.1:{PORT}/v1/chat/completions",
    f"http://127.0.0.1:{FALLBACK_MODEL_PORT}/v1/chat/completions",
)))
URL = MODEL_URLS[0]


def _model_request_urls():
    return (URL,) + tuple(
        value for value in MODEL_URLS if value != URL
    )


os.makedirs(YOSHI_DIR, exist_ok=True)

AUTO_MEMORY = True
VOICE_MODE = False
SCHEMA_VERSION = 2


class YoshiModelError(RuntimeError):
    """Raised when the local model cannot complete a request."""


class ClosingConnection(sqlite3.Connection):
    """Commit or roll back a with block, then always close the connection."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect_db():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=5,
        factory=ClosingConnection,
    )
    try:
        os.chmod(DB_PATH, 0o600)
    except OSError:
        pass
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS yoshi_schema (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL
        )
    """)
    schema_row = conn.execute(
        "SELECT version FROM yoshi_schema WHERE id = 1"
    ).fetchone()
    if schema_row and schema_row[0] > SCHEMA_VERSION:
        conn.close()
        raise RuntimeError(
            "This memory database was created by a newer Yoshi version."
        )
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    memory_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(memories)")
    }

    memory_upgrades = {
        "category": "TEXT DEFAULT 'General'",
        "importance": "TEXT DEFAULT 'Normal'",
        "updated_at": "TIMESTAMP",
        "active": "INTEGER DEFAULT 1",
        "recall_count": "INTEGER DEFAULT 0",
        "last_recalled_at": "TIMESTAMP",
        "profile": "TEXT NOT NULL DEFAULT 'Hermes'",
        "scope": "TEXT NOT NULL DEFAULT 'private'",
    }

    for name, definition in memory_upgrades.items():
        if name not in memory_columns:
            conn.execute(
                f"ALTER TABLE memories ADD COLUMN {name} {definition}"
            )

    memory_table_sql = conn.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table' AND name = 'memories'
        """
    ).fetchone()[0]

    # Version 2 replaces the old global UNIQUE(memory) rule with a
    # profile-aware index so two people can safely remember the same fact.
    if "UNIQUE" in (memory_table_sql or "").upper():
        conn.execute("DROP TABLE IF EXISTS memories_profiled")
        conn.execute("""
            CREATE TABLE memories_profiled (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category TEXT DEFAULT 'General',
                importance TEXT DEFAULT 'Normal',
                updated_at TIMESTAMP,
                active INTEGER DEFAULT 1,
                recall_count INTEGER DEFAULT 0,
                last_recalled_at TIMESTAMP,
                profile TEXT NOT NULL DEFAULT 'Hermes',
                scope TEXT NOT NULL DEFAULT 'private'
            )
        """)
        conn.execute("""
            INSERT INTO memories_profiled (
                id, memory, created_at, category, importance,
                updated_at, active, recall_count, last_recalled_at,
                profile, scope
            )
            SELECT
                id, memory, created_at, category, importance,
                updated_at, active, recall_count, last_recalled_at,
                COALESCE(NULLIF(TRIM(profile), ''), 'Hermes'),
                CASE WHEN LOWER(scope) = 'shared'
                     THEN 'shared' ELSE 'private' END
            FROM memories
        """)
        conn.execute("DROP TABLE memories")
        conn.execute("ALTER TABLE memories_profiled RENAME TO memories")

    conn.execute("""
        UPDATE memories
        SET updated_at = created_at
        WHERE updated_at IS NULL
    """)
    conn.execute("""
        UPDATE memories
        SET profile = COALESCE(NULLIF(TRIM(profile), ''), 'Hermes'),
            scope = CASE WHEN LOWER(scope) = 'shared'
                         THEN 'shared' ELSE 'private' END
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            priority TEXT DEFAULT 'Normal',
            due_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    task_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(tasks)")
    }

    if "priority" not in task_columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'Normal'"
        )

    if "due_date" not in task_columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN due_date TEXT"
        )

    if "tag" not in task_columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN tag TEXT DEFAULT 'General'"
        )

    if "assigned_to" not in task_columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN assigned_to INTEGER"
        )

    # Create every base table before inspecting it for upgrade columns. This
    # keeps first-run installs working as well as older upgraded databases.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shopping_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            quantity TEXT,
            bought INTEGER DEFAULT 0,
            added_by TEXT,
            category TEXT DEFAULT 'Other',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    shopping_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(shopping_items)"
        )
    }

    if "category" not in shopping_columns:
        conn.execute(
            "ALTER TABLE shopping_items "
            "ADD COLUMN category TEXT DEFAULT 'Other'"
        )

    note_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(notes)")
    }

    if "tag" not in note_columns:
        conn.execute(
            "ALTER TABLE notes ADD COLUMN tag TEXT DEFAULT 'General'"
        )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS family_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'Family',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reminder TEXT NOT NULL,
            due_date TEXT,
            assigned_to INTEGER,
            done INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            routine TEXT NOT NULL,
            weekday TEXT,
            assigned_to INTEGER,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS routine_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            routine_id INTEGER NOT NULL,
            completed_date TEXT NOT NULL,
            UNIQUE(routine_id, completed_date)
        )
    """)

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_active_category "
        "ON memories(active, category)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_profile_active "
        "ON memories(profile, scope, active, category)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_profile_text "
        "ON memories(profile COLLATE NOCASE, scope, memory)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_open_due "
        "ON tasks(done, due_date, priority)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_assigned "
        "ON tasks(assigned_to, done)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_reminders_open_due "
        "ON reminders(done, due_date)"
    )
    conn.execute(
        """
        INSERT INTO yoshi_schema (id, version)
        VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET version = excluded.version
        """,
        (SCHEMA_VERSION,)
    )

    conn.commit()
    return conn



def database_ready():
    """Run a cheap, read-only readiness check without schema migrations."""

    if not os.path.isfile(DB_PATH):
        return False

    required_tables = {
        "memories", "notes", "tasks", "family_members",
        "shopping_items", "reminders", "routines",
        "routine_completions"
    }

    try:
        uri = Path(DB_PATH).resolve().as_uri() + "?mode=ro"
        with closing(
            sqlite3.connect(uri, uri=True, timeout=2)
        ) as database:
            tables = {
                row[0]
                for row in database.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        return required_tables.issubset(tables)
    except (OSError, sqlite3.Error, ValueError):
        return False


def add_note(text):
    text = text.strip()
    if not text:
        return "Usage: /note <text>"

    conn = connect_db()
    conn.execute("INSERT INTO notes (note) VALUES (?)", (text,))
    conn.commit()
    conn.close()

    return "Note saved. 📝"


def get_notes():
    conn = connect_db()
    rows = conn.execute(
        "SELECT id, note, tag FROM notes ORDER BY id"
    ).fetchall()
    conn.close()
    return rows


def add_task(text):
    text = text.strip()
    if not text:
        return "Usage: /task <text>"

    conn = connect_db()
    conn.execute(
        "INSERT INTO tasks (task, done) VALUES (?, 0)",
        (text,)
    )
    conn.commit()
    conn.close()

    return "Task added. ✅"


def get_tasks():
    conn = connect_db()

    rows = conn.execute(
        """
        SELECT id, task, done, priority, due_date, tag, assigned_to
        FROM tasks
        ORDER BY done, id
        """
    ).fetchall()

    conn.close()
    return rows


def complete_task(task_id):
    try:
        task_id = int(task_id)
    except ValueError:
        return "Usage: /done <id>"

    conn = connect_db()
    cur = conn.execute(
        "UPDATE tasks SET done = 1 WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    conn.close()

    if cur.rowcount:
        return f"Task #{task_id} completed."
    return "Task not found."


def _normalize_profile(profile):
    clean = " ".join(str(profile or "Hermes").split()).strip()
    return clean[:80] or "Hermes"


def get_memories(
    category=None,
    importance=None,
    include_inactive=False,
    profile=None,
    scope=None
):
    conn = connect_db()

    query = """
        SELECT id, memory, category, importance, created_at, updated_at, active
        FROM memories
        WHERE 1=1
    """
    params = []

    if not include_inactive:
        query += " AND active = 1"

    if profile:
        query += " AND (LOWER(profile) = LOWER(?) OR scope = 'shared')"
        params.append(_normalize_profile(profile))

    if scope:
        query += " AND LOWER(scope) = LOWER(?)"
        params.append(scope)

    if category:
        query += " AND LOWER(category) = LOWER(?)"
        params.append(category)

    if importance:
        query += " AND LOWER(importance) = LOWER(?)"
        params.append(importance)

    query += """
        ORDER BY
            CASE importance
                WHEN 'High' THEN 1
                WHEN 'Normal' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END,
            id
    """

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def memory_center_records(profile="Hermes", include_inactive=True):
    """Return visible memories without crossing private profile boundaries."""
    profile = _normalize_profile(profile)
    conn = connect_db()
    try:
        query = """
            SELECT id, memory, category, importance, created_at, updated_at,
                   active, profile, scope
            FROM memories
            WHERE (LOWER(profile) = LOWER(?) OR scope = 'shared')
        """
        params = [profile]
        if not include_inactive:
            query += " AND active = 1"
        query += " ORDER BY active DESC, updated_at DESC, id DESC"
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    seen = {}
    records = []
    for row in rows:
        normalized = " ".join(str(row[1]).casefold().split())
        duplicate = normalized in seen
        seen.setdefault(normalized, row[0])
        records.append({
            "id": row[0],
            "memory": row[1],
            "category": row[2],
            "importance": row[3],
            "created_at": row[4],
            "updated_at": row[5],
            "active": bool(row[6]),
            "profile": row[7],
            "scope": row[8],
            "editable": str(row[7]).casefold() == profile.casefold(),
            "duplicate": duplicate,
        })
    return records


def update_memory_record(
    profile, memory_id, text, category="General",
    importance="Normal", scope="private"
):
    profile = _normalize_profile(profile)
    clean_text = " ".join(str(text or "").split()).strip()[:4000]
    if not clean_text:
        raise ValueError("Memory text is required.")
    clean_category = str(category or "General").strip().title()[:40]
    clean_importance = str(importance or "Normal").strip().title()
    if clean_importance not in {"Low", "Normal", "High"}:
        clean_importance = "Normal"
    clean_scope = "shared" if str(scope).casefold() == "shared" else "private"
    conn = connect_db()
    try:
        cursor = conn.execute(
            """
            UPDATE memories
            SET memory = ?, category = ?, importance = ?, scope = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND LOWER(profile) = LOWER(?)
            """,
            (
                clean_text, clean_category, clean_importance, clean_scope,
                int(memory_id), profile,
            ),
        )
        if not cursor.rowcount:
            raise ValueError("That memory is unavailable or belongs to another profile.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return "Memory updated."


def set_memory_active(profile, memory_id, active):
    profile = _normalize_profile(profile)
    conn = connect_db()
    try:
        cursor = conn.execute(
            """
            UPDATE memories
            SET active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND LOWER(profile) = LOWER(?)
            """,
            (1 if active else 0, int(memory_id), profile),
        )
        if not cursor.rowcount:
            raise ValueError("That memory is unavailable or belongs to another profile.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return "Memory restored." if active else "Memory deactivated."


def create_memory_backup():
    backup_root = Path(YOSHI_DIR) / "backups" / "memory-center"
    backup_root.mkdir(parents=True, exist_ok=True)
    target = backup_root / time.strftime("memory-%Y%m%d-%H%M%S.db")
    source = connect_db()
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
        destination.commit()
        integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError("Memory backup integrity check failed.")
    finally:
        destination.close()
        source.close()
    os.chmod(target, 0o600)
    return str(target.relative_to(Path(YOSHI_DIR)))


def detect_memory_category(text):
    lower = text.lower()

    # Yoshi project memories get classified before broad rules.
    if "yoshi" in lower:
        if any(x in lower for x in (
            "goal",
            "plan",
            "working on",
            "upgrading",
            "improving",
            "future",
            "become yoshi home",
        )):
            return "Goal"

        if any(x in lower for x in (
            "termux",
            "linux",
            "qwen",
            "llama",
            "model",
            "ai",
            "router",
            "memory",
            "tool",
            "context",
            "fold",
            "computer",
            "local",
        )):
            return "Tech"

    if any(x in lower for x in (
        "wife", "husband", "son", "daughter",
        "kid", "kids", "family",
        "mother", "father", "mom", "dad"
    )):
        return "Family"

    if any(x in lower for x in (
        "phone", "computer", "pc", "laptop",
        "linux", "windows", "android",
        "samsung", "intel", "gpu", "cpu",
        "router", "wifi"
    )):
        return "Tech"

    if any(x in lower for x in (
        "goal", "plan to", "want to become",
        "working toward", "my future", "career"
    )):
        return "Goal"

    if any(x in lower for x in (
        "home", "house", "garage", "thermostat",
        "light", "camera", "door", "lock"
    )):
        return "Home"

    if any(x in lower for x in (
        "favorite", "i like", "i love",
        "i prefer", "i dislike", "i hate"
    )):
        return "Preference"

    if any(x in lower for x in (
        "game", "gaming", "xbox",
        "playstation", "steam"
    )):
        return "Gaming"

    return "General"


def detect_memory_importance(text, category=None):
    lower = text.lower()

    high_patterns = (
        "important",
        "priority",
        "never forget",
        "emergency",
        "security",
        "medical",
        "allergy",
        "goal",
        "career",
        "family is my priority",
    )

    low_patterns = (
        "favorite color",
        "favorite fruit",
        "favorite season",
        "favorite animal",
    )

    if any(x in lower for x in high_patterns):
        return "High"

    if category in {"Family", "Goal"}:
        return "High"

    if any(x in lower for x in low_patterns):
        return "Low"

    return "Normal"


def add_memory(
    text,
    category="General",
    importance="Normal",
    profile="Hermes",
    scope="private"
):
    text = text.strip()
    profile = _normalize_profile(profile)
    scope = "shared" if str(scope).lower() == "shared" else "private"
    category = (category or "General").strip().title()

    if category == "General":
        category = detect_memory_category(text)

    importance = (importance or "Normal").strip().title()

    if importance == "Normal":
        importance = detect_memory_importance(text, category)

    if not text:
        result = "Usage: /remember <something>"
        print(result)
        return result

    valid_importance = {"Low", "Normal", "High"}
    if importance not in valid_importance:
        importance = "Normal"

    conn = connect_db()
    result = ""

    try:
        conn.execute(
            """
            INSERT INTO memories (
                memory, category, importance, updated_at, active,
                profile, scope
            )
            VALUES
                (?, ?, ?, CURRENT_TIMESTAMP, 1, ?, ?)
            """,
            (text, category, importance, profile, scope)
        )
        conn.commit()
        result = f"Memory saved. 🧠 [{category} | {importance}]"
        print(result)

    except sqlite3.IntegrityError:
        existing = conn.execute(
            """
            SELECT id, active
            FROM memories
            WHERE memory = ?
              AND LOWER(profile) = LOWER(?)
              AND scope = ?
            """,
            (text, profile, scope)
        ).fetchone()

        if existing and existing[1] == 0:
            conn.execute(
                """
                UPDATE memories
                SET active = 1,
                    category = ?,
                    importance = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (category, importance, existing[0])
            )
            conn.commit()
            result = f"Memory restored. 🧠 #{existing[0]}"
            print(result)
        else:
            result = "I already have that memory."
            print(result)

    finally:
        conn.close()

    return result


def forget_memory(memory_id):
    try:
        memory_id = int(memory_id)
    except ValueError:
        print("Usage: /forget <id>")
        return

    conn = connect_db()

    cur = conn.execute(
        """
        UPDATE memories
        SET active = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND active = 1
        """,
        (memory_id,)
    )

    conn.commit()
    conn.close()

    if cur.rowcount:
        print(f"Memory #{memory_id} deactivated.")
    else:
        print("Memory not found or already inactive.")


def restore_memory(memory_id, profile="Hermes"):
    profile = _normalize_profile(profile)
    try:
        memory_id = int(memory_id)
    except (ValueError, TypeError):
        return "Usage: /restore-memory <id>"

    conn = connect_db()

    cur = conn.execute(
        """
        UPDATE memories
        SET active = 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND active = 0
          AND LOWER(profile) = LOWER(?)
        """,
        (memory_id, profile)
    )

    conn.commit()
    conn.close()

    if cur.rowcount:
        return f"Memory #{memory_id} restored. 🧠"

    return "Memory not found or already active."


def update_memory(memory_id, text=None, category=None, importance=None):
    try:
        memory_id = int(memory_id)
    except (ValueError, TypeError):
        return "Invalid memory ID."

    conn = connect_db()

    row = conn.execute(
        """
        SELECT memory, category, importance
        FROM memories
        WHERE id = ?
        """,
        (memory_id,)
    ).fetchone()

    if not row:
        conn.close()
        return "Memory not found."

    new_text = text.strip() if text else row[0]
    new_category = category.strip().title() if category else row[1]
    new_importance = importance.strip().title() if importance else row[2]

    if new_importance not in {"Low", "Normal", "High"}:
        new_importance = "Normal"

    try:
        conn.execute(
            """
            UPDATE memories
            SET memory = ?,
                category = ?,
                importance = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_text, new_category, new_importance, memory_id)
        )

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        return "That memory already exists."

    conn.close()
    return f"Memory #{memory_id} updated. 🧠"



def memory_recategorization_report():
    """Show active memories whose stored metadata no longer matches detection rules."""

    conn = connect_db()

    rows = conn.execute(
        """
        SELECT id, memory, category, importance
        FROM memories
        WHERE active = 1
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    changes = []

    for memory_id, memory, category, importance in rows:
        detected_category = detect_memory_category(memory)
        detected_importance = detect_memory_importance(
            memory,
            detected_category
        )

        current_category = category or "General"
        current_importance = importance or "Normal"

        if (
            current_category != detected_category
            or current_importance != detected_importance
        ):
            changes.append({
                "id": memory_id,
                "memory": memory,
                "old_category": current_category,
                "new_category": detected_category,
                "old_importance": current_importance,
                "new_importance": detected_importance,
            })

    return changes


def run_memory_recategorization(dry_run=True):
    """Update memory category/importance metadata using current rules."""

    changes = memory_recategorization_report()

    if dry_run:
        return {
            "mode": "dry_run",
            "changes": changes,
        }

    conn = connect_db()

    try:
        for item in changes:
            conn.execute(
                """
                UPDATE memories
                SET category = ?,
                    importance = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    item["new_category"],
                    item["new_importance"],
                    item["id"],
                )
            )

        conn.commit()

    finally:
        conn.close()

    return {
        "mode": "applied",
        "updated": len(changes),
        "changes": changes,
    }


def memory_staleness_report():
    """Score memories by likely staleness without changing them."""

    from datetime import datetime, timezone

    conn = connect_db()

    rows = conn.execute(
        """
        SELECT
            id,
            memory,
            category,
            importance,
            created_at,
            updated_at,
            active,
            COALESCE(recall_count, 0),
            last_recalled_at
        FROM memories
        WHERE active = 1
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    now = datetime.now(timezone.utc)
    report = []

    def parse_time(value):
        if not value:
            return None

        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed

    for row in rows:
        (
            memory_id,
            memory,
            category,
            importance,
            created_at,
            updated_at,
            active,
            recall_count,
            last_recalled_at,
        ) = row

        score = 0
        reasons = []

        importance_lower = (importance or "Normal").lower()
        category_lower = (category or "General").lower()

        created = parse_time(created_at)
        updated = parse_time(updated_at)
        recalled = parse_time(last_recalled_at)

        reference = recalled or updated or created

        age_days = None

        if reference:
            age_days = max(
                0,
                int((now - reference).total_seconds() // 86400)
            )

        # Important memories are strongly protected.
        if importance_lower == "high":
            score -= 10
            reasons.append("high importance")

        elif importance_lower == "low":
            score += 3
            reasons.append("low importance")

        # Frequently used memories stay warm.
        if recall_count >= 10:
            score -= 8
            reasons.append("frequently recalled")

        elif recall_count >= 3:
            score -= 4
            reasons.append("recalled several times")

        elif recall_count == 0:
            score += 3
            reasons.append("never recalled")

        # Age contributes only gradually.
        if age_days is not None:
            if age_days >= 180:
                score += 5
                reasons.append("older than 180 days")

            elif age_days >= 90:
                score += 3
                reasons.append("older than 90 days")

            elif age_days >= 30:
                score += 1
                reasons.append("older than 30 days")

        # Generic memories cool faster than specialized memories.
        if category_lower == "general":
            score += 1
            reasons.append("general category")

        # Never auto-target protected categories just because of age.
        if category_lower in {"family", "goal"}:
            score -= 4
            reasons.append("protected category")

        report.append({
            "id": memory_id,
            "memory": memory,
            "category": category or "General",
            "importance": importance or "Normal",
            "recall_count": recall_count,
            "last_recalled_at": last_recalled_at,
            "age_days": age_days,
            "staleness_score": score,
            "candidate": score >= 7,
            "reasons": reasons,
        })

    report.sort(
        key=lambda item: (
            item["staleness_score"],
            -item["recall_count"],
            item["id"],
        ),
        reverse=True,
    )

    return report


def memory_hygiene_report(profile="Hermes"):
    """Inspect one profile's visible memories for low-value clutter."""

    rows = get_memories(
        include_inactive=False,
        profile=_normalize_profile(profile)
    )

    report = {
        "duplicates": [],
        "test_memories": [],
        "weak_memories": [],
    }

    seen = {}

    for row in rows:
        memory_id = row[0]
        memory = row[1]
        category = row[2] or "General"
        importance = row[3] or "Normal"

        normalized = re.sub(
            r"\s+",
            " ",
            memory.strip().lower()
        ).rstrip(".!?")

        if normalized in seen:
            report["duplicates"].append(
                (memory_id, seen[normalized], memory)
            )
        else:
            seen[normalized] = memory_id

        lower = memory.lower()

        if any(
            marker in lower
            for marker in (
                "test color",
                "test memory",
                "testing memory",
                "dummy memory",
            )
        ):
            report["test_memories"].append(
                (memory_id, memory)
            )

        if (
            category == "General"
            and importance == "Low"
            and len(memory) < 20
        ):
            report["weak_memories"].append(
                (memory_id, memory)
            )

    return report


def run_memory_hygiene(dry_run=True, profile="Hermes"):
    """Archive obvious clutter safely.

    dry_run=True only reports what would change.
    dry_run=False deactivates duplicate/test/weak memories.
    """

    report = memory_hygiene_report(profile=profile)

    to_archive = set()

    for memory_id, _original_id, _memory in report["duplicates"]:
        to_archive.add(memory_id)

    for memory_id, _memory in report["test_memories"]:
        to_archive.add(memory_id)

    for memory_id, _memory in report["weak_memories"]:
        to_archive.add(memory_id)

    if dry_run:
        return {
            "mode": "dry_run",
            "report": report,
            "would_archive": sorted(to_archive),
        }

    conn = connect_db()

    try:
        for memory_id in sorted(to_archive):
            conn.execute(
                """
                UPDATE memories
                SET active = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND active = 1
                """,
                (memory_id,)
            )

        conn.commit()

    finally:
        conn.close()

    return {
        "mode": "applied",
        "report": report,
        "archived": sorted(to_archive),
    }


def should_auto_remember(text):
    """Fast first-stage filter for obviously durable memories."""

    clean = (text or "").strip()
    lower = clean.lower()

    if not AUTO_MEMORY:
        return False

    if not clean:
        return False

    if clean.startswith("/"):
        return False

    if clean.endswith("?"):
        return False

    if len(clean) < 8 or len(clean) > 300:
        return False

    strong_patterns = (
        "i like ",
        "i love ",
        "i prefer ",
        "i dislike ",
        "i hate ",
        "i usually ",
        "i always ",
        "i work ",
        "i study ",
        "i live ",
        "i use ",
        "i own ",
        "i have ",
        "i want ",
        "i need ",
        "i'm allergic ",
        "i am allergic ",
        "my favorite ",
        "my goal ",
        "my goals ",
        "my job ",
        "my work ",
        "my school ",
        "my computer ",
        "my phone ",
        "my pc ",
        "my family ",
        "my wife ",
        "my husband ",
        "my son ",
        "my daughter ",
    )

    if lower.startswith(strong_patterns):
        return True

    useful_phrases = (
        "my favorite",
        "my goal is",
        "my goals are",
        "i prefer",
        "i work at",
        "i work as",
        "i am studying",
        "i'm studying",
        "i use a",
        "i own a",
        "i live in",
        "i usually",
        "i always",
        "important to me",
    )

    return any(phrase in lower for phrase in useful_phrases)


def should_consider_ai_memory(text):
    """Return True only for borderline messages worth AI classification."""

    clean = (text or "").strip()
    lower = clean.lower()

    if not AUTO_MEMORY:
        return False

    if not clean or clean.startswith("/") or clean.endswith("?"):
        return False

    if len(clean) < 12 or len(clean) > 300:
        return False

    # Avoid wasting a model call on obvious conversational filler.
    filler = (
        "thank you",
        "thanks",
        "okay",
        "ok ",
        "lol",
        "haha",
        "yes please",
        "no thanks",
        "sounds good",
        "go ahead",
        "next",
    )

    if any(lower == item or lower.startswith(item + " ") for item in filler):
        return False

    # AI judgment is only useful when the statement appears personal.
    personal_markers = (
        "i ",
        "i'm ",
        "i am ",
        "i've ",
        "i have ",
        "i need ",
        "i want ",
        "we ",
        "we're ",
        "our ",
        "my ",
    )

    return lower.startswith(personal_markers)


def ai_should_remember(text):
    """Ask the local model whether a borderline fact is worth saving.

    The request is deliberately tiny so this does not become a large
    performance penalty.
    """

    if not should_consider_ai_memory(text):
        return False

    prompt = (
        "Decide whether this user statement contains a durable personal "
        "fact that would be useful in future conversations. "
        "Remember stable preferences, important relationships, devices, "
        "work, school, goals, routines, accessibility needs, important "
        "health/safety facts, and long-term plans. "
        "Ignore temporary moods, one-time actions, casual chatter, "
        "commands, and facts unlikely to matter later. "
        "Reply with exactly REMEMBER or IGNORE.\n\n"
        f"Statement: {text.strip()}"
    )

    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.0,
        "max_tokens": 4,
        "think": False
    }).encode("utf-8")

    request = urllib.request.Request(
        URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=min(MODEL_TIMEOUT_SECONDS, 20)
        ) as response:
            data = json.loads(response.read().decode("utf-8"))

        answer = (
            data["choices"][0]["message"]["content"]
            .strip()
            .upper()
        )

        return answer.startswith("REMEMBER")

    except Exception:
        # Memory classification should never break normal chat.
        return False


def normalize_memory(text):
    clean = text.strip()

    if clean.lower().startswith("you:"):
        clean = clean[4:].strip()

    lower = clean.lower()

    patterns = [
        (
            r"(?:actually,\s*)?my favorite color is (.+?)(?: now)?[.!]?$",
            "My favorite color is {}."
        ),
        (
            r"(?:actually,\s*)?my favorite season is (.+?)(?: now)?[.!]?$",
            "My favorite season is {}."
        ),
        (
            r"(?:actually,\s*)?my favorite fruit is (.+?)(?: now)?[.!]?$",
            "My favorite fruit is {}."
        ),
        (
            r"(?:actually,\s*)?my favorite animal is (.+?)(?: now)?[.!]?$",
            "My favorite animal is {}."
        ),
        (
            r"(?:actually,\s*)?my favorite test color is (.+?)(?: now)?[.!]?$",
            "My favorite test color is {}."
        ),
    ]

    for pattern, template in patterns:
        match = re.fullmatch(pattern, lower, flags=re.IGNORECASE)

        if match:
            value = match.group(1).strip()
            return template.format(value)

    return clean

def auto_remember(text, profile="Hermes"):
    """Save durable user facts for one profile with safe update handling."""

    profile = _normalize_profile(profile)
    rule_match = should_auto_remember(text)

    if not rule_match and not ai_should_remember(text):
        return False

    clean = normalize_memory(text)
    lower = clean.lower()

    category = detect_memory_category(clean)
    importance = detect_memory_importance(clean, category)

    replaceable_topics = {
        "favorite_color": (
            "my favorite color",
            "favorite color",
        ),
        "favorite_season": (
            "my favorite season",
            "favorite season",
        ),
        "favorite_fruit": (
            "my favorite fruit",
            "favorite fruit",
        ),
        "favorite_animal": (
            "my favorite animal",
            "favorite animal",
        ),
        "phone": (
            "my phone",
            "i use a samsung",
            "i use an iphone",
            "i have a samsung",
            "i have an iphone",
        ),
        "computer": (
            "my computer",
            "my pc",
            "i use a pc",
            "i use a laptop",
            "i have a pc",
            "i have a laptop",
        ),
        "work": (
            "my job",
            "my work",
            "i work at",
            "i work as",
        ),
        "school": (
            "my school",
            "i study",
            "i am studying",
            "i'm studying",
        ),
    }

    conn = connect_db()

    try:
        rows = conn.execute(
            """
            SELECT id, memory, active
            FROM memories
            WHERE LOWER(profile) = LOWER(?)
              AND scope = 'private'
            ORDER BY id
            """,
            (profile,)
        ).fetchall()

        normalized_new = re.sub(
            r"\s+", " ", clean
        ).strip().rstrip(".!?").lower()

        for memory_id, memory, active in rows:
            normalized_old = re.sub(
                r"\s+", " ", memory
            ).strip().rstrip(".!?").lower()

            if normalized_old == normalized_new:
                if not active:
                    conn.execute(
                        """
                        UPDATE memories
                        SET active = 1,
                            category = ?,
                            importance = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (category, importance, memory_id)
                    )
                    conn.commit()
                    return "restored"

                return False

        for markers in replaceable_topics.values():
            if not any(marker in lower for marker in markers):
                continue

            matches = []

            for memory_id, memory, active in rows:
                old_lower = memory.lower()

                if active and any(
                    marker in old_lower for marker in markers
                ):
                    matches.append(memory_id)

            if matches:
                primary_id = matches[0]

                conn.execute(
                    """
                    UPDATE memories
                    SET memory = ?,
                        category = ?,
                        importance = ?,
                        active = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        clean,
                        category,
                        importance,
                        primary_id,
                    )
                )

                for duplicate_id in matches[1:]:
                    conn.execute(
                        """
                        UPDATE memories
                        SET active = 0,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (duplicate_id,)
                    )

                conn.commit()
                return "updated"

        conn.execute(
            """
            INSERT INTO memories (
                memory, category, importance, updated_at, active,
                profile, scope
            )
            VALUES
                (?, ?, ?, CURRENT_TIMESTAMP, 1, ?, 'private')
            """,
            (clean, category, importance, profile)
        )

        conn.commit()
        return "saved"

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()



def _mark_memories_recalled(memory_rows):
    """Record recall frequency without affecting memory contents."""

    if not memory_rows:
        return

    ids = []

    for row in memory_rows:
        try:
            ids.append(int(row[0]))
        except (TypeError, ValueError, IndexError):
            continue

    if not ids:
        return

    conn = connect_db()

    try:
        for memory_id in ids:
            conn.execute(
                """
                UPDATE memories
                SET recall_count = COALESCE(recall_count, 0) + 1,
                    last_recalled_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (memory_id,)
            )

        conn.commit()

    finally:
        conn.close()


def smart_recall(query, limit=5, profile="Hermes", scope=None):
    """Return the selected profile's relevant private and shared memories.

    This intentionally stays dependency-free so it works on WSL, Linux, and
    Termux. It combines token overlap, topic aliases, category matches, and
    importance. A later embedding provider can augment this without changing
    the row contract returned to callers.
    """

    query = (query or "").strip().lower()
    if not query:
        return []

    try:
        limit = max(1, min(20, int(limit)))
    except (TypeError, ValueError):
        limit = 5

    stop_words = {
        "a", "an", "the", "and", "or", "but", "is", "it", "of",
        "on", "in", "to", "for", "my", "me", "i", "that", "this",
        "with", "from", "what", "when", "where", "who", "why", "how",
        "have", "has", "does", "do", "about", "your", "you", "are",
        "was", "were", "can", "could", "would", "should", "tell",
        "know", "remember", "mine"
    }

    def words(value):
        return {
            word for word in re.findall(r"[a-z0-9]+", value.lower())
            if len(word) > 2 and word not in stop_words
        }

    query_words = words(query)
    if not query_words:
        return []

    aliases = {
        "phone": {
            "phone", "mobile", "device", "android", "iphone", "samsung",
            "fold"
        },
        "computer": {
            "computer", "pc", "desktop", "laptop", "linux", "windows",
            "tecra"
        },
        "family": {
            "family", "wife", "husband", "son", "daughter", "child",
            "children", "kid", "kids", "mom", "dad"
        },
        "goal": {"goal", "goals", "future", "career", "plan", "plans"},
        "gaming": {
            "game", "games", "gaming", "xbox", "playstation", "steam"
        },
        "home": {
            "home", "house", "garage", "camera", "thermostat", "door",
            "lock"
        },
        "preference": {
            "favorite", "favourite", "like", "love", "prefer", "dislike"
        },
        "school": {
            "school", "class", "classes", "course", "homework", "study"
        },
    }

    expanded = set(query_words)
    for topic, values in aliases.items():
        if topic in query_words or query_words.intersection(values):
            expanded.add(topic)
            expanded.update(values)

    scored = []
    for row in get_memories(
        profile=_normalize_profile(profile),
        scope=scope,
    ):
        memory = row[1]
        category = row[2] or "General"
        importance = row[3] or "Normal"
        memory_lower = memory.lower()
        memory_words = words(memory_lower)

        score = len(expanded.intersection(memory_words)) * 4
        category_lower = category.lower()
        importance_lower = importance.lower()

        # Strong preference-subtype matching.
        preference_topics = {
            "color": ("color",),
            "animal": ("animal",),
            "fruit": ("fruit",),
            "season": ("season",),
        }

        for topic, topic_words in preference_topics.items():
            query_has_topic = any(word in query_words for word in topic_words)
            memory_has_topic = any(word in memory_words for word in topic_words)

            if query_has_topic and memory_has_topic:
                score += 30
            elif query_has_topic and not memory_has_topic:
                score -= 12

        # Legacy test memories should never outrank real preferences.
        if "test color" in memory_lower:
            score -= 20

        if category_lower in expanded:
            score += 6
        if category_lower in query:
            score += 5
        if query in memory_lower or memory_lower in query:
            score += 12
        if importance_lower == "high" and score:
            score += 2

        # Strongly favor Yoshi-project memories for Yoshi-project questions.
        project_terms = {
            "yoshi", "fold", "linux", "termux",
            "ai", "memory", "tool", "tools",
            "planning", "router", "context",
        }

        if query_words.intersection(project_terms):
            project_overlap = len(
                memory_words.intersection(project_terms)
            )

            score += project_overlap * 8

            if not memory_words.intersection(project_terms):
                score -= 8

            # If the user specifically asks about Yoshi, require either
            # a direct Yoshi reference or several project signals.
            if "yoshi" in query_words:
                if "yoshi" in memory_words:
                    score += 20
                elif project_overlap < 2:
                    score -= 20
        if "important" in query or "priority" in query:
            if importance_lower == "high":
                score += 8

        # Ignore weak accidental matches.
        if score >= 8:
            scored.append((score, row))

    scored.sort(
        key=lambda item: (
            item[0],
            1 if (item[1][3] or "").lower() == "high" else 0,
            item[1][0]
        ),
        reverse=True
    )
    selected = [row for _, row in scored[:limit]]

    _mark_memories_recalled(selected)

    return selected


def show_memories(profile="Hermes"):
    memories = get_memories(profile=profile)

    if not memories:
        print("No saved memories yet.")
        return

    print("\n=== YOSHI MEMORIES ===")

    for row in memories:
        memory_id, memory, category, importance, created_at, updated_at, active = row
        print(
            f"{memory_id}: {memory} "
            f"[{category} | {importance}]"
        )

    print()


def build_system_prompt(memory_rows=None, profile="Hermes"):
    profile = _normalize_profile(profile)
    try:
        with open(IDENTITY_PATH, "r", encoding="utf-8") as f:
            identity = f.read().strip()
    except FileNotFoundError:
        identity = "You are DiYoshi, Hermes's personal AI assistant."

    settings = yoshi_settings.load_settings()
    mode = FORCE_MODE or settings.get("mode", "family")

    mode_instructions = {
        "family": """
CURRENT MODE: FAMILY

Your primary role is to help Hermes and his family.

Prioritize:
- household tasks
- family organization
- shopping lists
- reminders and routines
- school and homework support
- weather and day-to-day planning
- simple, clear explanations
- safe and privacy-conscious assistance

Keep responses practical, warm, concise, and family-friendly.

Do not treat computer-lab experimentation as the priority unless Hermes explicitly asks for technical help.
""",

        "normal": """
CURRENT MODE: NORMAL

Act as a balanced general-purpose personal assistant.

Help with everyday questions, organization, planning, learning, and general problem-solving.
""",

        "tech": """
CURRENT MODE: TECH

Act as DiYoshi's computer-lab mode.

Prioritize:
- Python and coding
- Linux
- Termux
- networking
- virtual machines
- troubleshooting
- computer hardware
- local AI
- debugging
- explaining technical concepts clearly

Teach while helping. When useful, explain why code works instead of only giving commands.

Keep family privacy and safety rules intact.
""",

        "gaming": """
CURRENT MODE: GAMING

Prioritize:
- PC and console troubleshooting
- game settings
- performance tuning
- peripherals
- hardware temperatures
- storage and system performance
- gaming-related questions

Keep the tone relaxed and playful while staying accurate and useful.
"""
    }

    mode_text = mode_instructions.get(
        mode,
        mode_instructions["family"]
    )

    memories = (
        get_memories(profile=profile)
        if memory_rows is None
        else memory_rows
    )

    if memories:
        memory_text = "\n".join(
            f"- [{row[2]} | {row[3]}] {row[1]}"
            for row in memories
        )
    else:
        memory_text = "- No saved long-term memories."

    return f"""
{identity}

{mode_text}

ACTIVE SPEAKER PROFILE: {profile}

You are talking to {profile}. Address this person by name only when natural.
Keep this profile's private memories separate from other people's memories.
Shared household memories may be used for any family profile.
A selected profile personalizes context; it is not proof of identity.

RESPONSE QUALITY RULES:

- Answer {profile}'s actual request first.
- Write in polished, natural American English unless {profile} requests another language or dialect.
- Use correct spelling, grammar, punctuation, capitalization, and complete sentences.
- Use standard pronoun case: write "He and I went" as a subject, not "Him and I went" or "Me and him went."
- Check subject-verb agreement, possessives versus contractions, and consistent verb tense.
- Silently proofread every final response before sending it.
- Prefer clear everyday words, varied sentence structure, and a warm, confident voice.
- Avoid awkward fragments, repetitive wording, filler, canned disclaimers, and robotic transitions.
- Preserve the exact spelling of names, quotations, commands, code, paths, and technical identifiers.
- Match the requested tone and format without imitating errors from the prompt.
- Use saved memory and recent context only when relevant.
- The newest message and {profile}'s latest correction override older context.
- Never invent a device state, completed action, memory, source, or tool result.
- If a key fact is uncertain, say what is uncertain instead of guessing.
- Ask one short clarifying question only when the missing choice materially changes the answer.
- Keep routine answers concise. Give more detail when {profile} asks for it.
- For simple factual questions, answer in one short sentence and stop.
- Do not offer extra help unless {profile} asks for it.
- For technical help, use the DEPENDABLE TECHNICIAN workflow below and preserve {profile}'s existing work.
- Check names, numbers, and internal consistency before answering.

WRITING AND LITERATURE RULES:

- For editing, first preserve the writer's intended meaning, voice, and audience.
- Correct spelling and grammar without making the writing stiff or generic.
- For essays, use a clear thesis, logical paragraphs, textual evidence when provided, and a concise conclusion.
- For stories, maintain point of view, tense, character continuity, setting, and cause-and-effect.
- For poetry, discuss imagery, sound, form, tone, and theme without inventing quotations.
- Distinguish summary, interpretation, and verified fact.
- Never fabricate a quotation, page number, author claim, or source.
- When teaching, explain the correction and give a short example when useful.

DEPENDABLE TECHNICIAN WORKFLOW:

- Confirm the goal, scope, symptoms, and what changed before diagnosing.
- Protect data first. Back up important work and identify rollback before risky changes.
- Gather evidence from errors, logs, configuration, health checks, and reproducible behavior.
- Clearly label confirmed facts, observations, and hypotheses; never present a guess as a diagnosis.
- Isolate the smallest likely cause and change one controlled thing at a time.
- Explain risky, destructive, security-sensitive, or permission-changing actions before proceeding.
- Verify the original symptom is fixed, check for regressions, and do not claim success without evidence.
- Record the root cause, exact change, verification result, rollback, and useful next step.
- Teach the computer-science idea in plain language, including what a command does and what result to expect.
- Scale the detail to the question so routine fixes stay concise.

IMPORTANT MEMORY RULES:

You have a persistent long-term memory database.

The facts below are private memories for {profile} plus shared household facts.
Treat them as true user-provided facts unless {profile} later corrects them.

When {profile} asks about something that appears in memory:
- Answer using the saved memory.
- Do not say that you do not have memory.
- Do not say that AI assistants cannot remember.
- Do not describe the memory as your own personal preference.
- Understand that phrases such as "my favorite" refer to {profile}, not DiYoshi.
- When referring to saved memories about {profile}, use "you" and "your", never "I", "me", or "my".

SAVED LONG-TERM MEMORIES:
{memory_text}

Example:
Memory: "My favorite color is black."
{profile} asks: "What is my favorite color?"
Correct answer: "Your favorite color is black."

Use saved memories naturally and directly.
""".strip()


def server_ready():
    global URL

    for model_url in MODEL_URLS:
        models_url = model_url.replace(
            "/v1/chat/completions", "/v1/models"
        )
        try:
            with urllib.request.urlopen(
                models_url,
                timeout=2
            ) as response:
                if response.status != 200:
                    continue
                model_data = json.loads(
                    response.read().decode("utf-8")
                )
        except Exception:
            continue

        available = set()
        for item in model_data.get("data", []):
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                available.add(item["id"])

        for item in model_data.get("models", []):
            if not isinstance(item, dict):
                continue
            for key in ("name", "model"):
                if isinstance(item.get(key), str):
                    available.add(item[key])

        if MODEL in available:
            URL = model_url
            return True

    return False

def start_server():
    if server_ready():
        print("Yoshi is connected to Ollama. 🦖")
        return None

    print("Ollama is not ready on the configured model port.")
    sys.exit(1)

def _compact_text(text, max_chars):
    """Compact text without cutting the prompt loose entirely."""

    text = " ".join((text or "").split()).strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + "…"


def _build_recent_history(history, max_messages=4, char_budget=2600):
    """Keep the newest useful messages inside a small context budget."""

    cleaned = []

    for item in history or []:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")

        if role not in {"user", "assistant"}:
            continue

        if not isinstance(content, str):
            continue

        content = content.strip()

        if not content:
            continue

        cleaned.append({
            "role": role,
            "content": _compact_text(content, 900)
        })

    cleaned = cleaned[-max_messages:]

    selected = []
    used = 0

    for item in reversed(cleaned):
        size = len(item["content"])

        if used + size > char_budget:
            continue

        selected.append(item)
        used += size

    selected.reverse()
    return selected


def _clean_model_reply(value):
    original = str(value or "").strip()
    reply = original
    unasked_help_endings = (
        r"\s+If you need (?:any )?(?:help|assistance)"
        r"(?: with (?:it|that))?,?\s*feel free to ask[.!]*\s*🦖?\s*$",
        r"\s+If you have (?:any )?(?:other )?questions,?\s*"
        r"feel free to ask[.!]*\s*🦖?\s*$",
        r"\s+Let me know if you need (?:anything|any help)"
        r"(?: else)?[.!]*\s*🦖?\s*$",
    )

    for pattern in unasked_help_endings:
        reply = re.sub(pattern, "", reply, flags=re.IGNORECASE).strip()

    return reply or original



def choose_brain_model(user_text, brain_mode="auto"):
    """Choose an allowlisted manual brain or route automatically."""
    requested = str(brain_mode or "auto").strip().casefold()
    if requested in BRAIN_MODELS:
        return BRAIN_MODELS[requested]

    prompt = str(user_text or "").lower()

    coding_markers = (
        "python", "javascript", "typescript", "html", "css",
        "flask", "django", "fastapi", "pygame", "godot",
        "gdscript", "computer science", "data structure",
        "algorithm", "debug", "traceback", "exception",
        "source code", "write code", "coding mode",
        "game developer", "game engine", "sql", "database",
        "api endpoint", "git command", "linux command",
        "refactor", "unit test"
    )

    if any(marker in prompt for marker in coding_markers):
        return CODING_MODEL

    balanced_markers = (
        "analyze", "compare", "explain why", "step by step",
        "detailed", "essay", "literature", "proofread", "rewrite",
        "plan", "research", "diagnose", "troubleshoot", "security",
        "financial", "medical", "legal", "architecture"
    )
    if len(prompt) > 280 or any(marker in prompt for marker in balanced_markers):
        return MODEL

    return FAST_MODEL

def ask_yoshi(
    history,
    user_text,
    raise_on_error=False,
    profile="Hermes",
    conversation_profile=None,
    system_context="",
    brain_mode="auto",
    request_id="",
    memory_scope="all",
    images=None
):
    """Brain v4.3 profile-aware, model-routed Ollama request."""

    global URL
    selected_model = choose_brain_model(
        str(user_text or "") + " " + str(system_context or ""),
        brain_mode=brain_mode,
    )
    if images:
        selected_model = VISION_MODEL
    profile = _normalize_profile(profile)
    conversation_profile = _normalize_profile(
        conversation_profile or profile
    )
    requested_memory = str(memory_scope or "all").strip().casefold()
    if requested_memory == "none":
        memories = []
    else:
        recall_scope = requested_memory if requested_memory in {"private", "shared"} else None
        memories = smart_recall(
            user_text,
            limit=5,
            profile=profile,
            scope=recall_scope,
        )

    system_prompt = build_system_prompt(memories, profile=profile)
    if selected_model == CODING_MODEL:
        system_prompt += """
        
CODING MODE:
- Act as a patient Python and computer-science teacher.
- Explain the plan before presenting substantial code.
- Prefer small, testable functions and clear names.
- Check syntax, edge cases, security, and data safety.
- For game development, teach the game loop and components.
- Never claim code was executed or verified unless a tool proves it.
- When project evidence is needed, use only approved read-only tools.
- In coding builder mode, inspect exact current text before propose_code_edit.
- For a brand-new app file, use propose_new_file and keep it inside projects/.
- A proposal must remain pending until an administrator approves it.
- Never claim a proposed edit was applied.
""".rstrip()
    if images:
        system_prompt += """
        
VISION MODE:
- Inspect attached images directly and describe only what is visible.
- Answer the user's specific question before extra observations.
- Read visible text carefully and say when text is unclear.
- Never invent objects, people, text, or actions.
- Protect private information visible in screenshots or photos.
""".rstrip()
    room_context = _compact_text(system_context, 800)
    if room_context:
        system_prompt += "\n\nACTIVE ROOM:\n" + room_context

    try:
        summary = yoshi_summary.load_summary(conversation_profile)
    except Exception:
        summary = ""

    if summary:
        summary = _compact_text(summary, 1200)

        system_prompt += (
            "\n\nCONVERSATION CONTEXT:\n"
            + summary
            + "\n\nUse this only when relevant. "
              "The newest user message and recent messages take priority."
        )

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages.extend(
        _build_recent_history(
            history,
            max_messages=4,
            char_budget=2600
        )
    )

    messages.append({
        "role": "user",
        "content": _compact_text(user_text, 8000)
    })

    last_error = None
    for model_url in _model_request_urls():
        try:
            reply = yoshi_tool_agent.chat(
                model_url,
                selected_model,
                messages,
                timeout=MODEL_TIMEOUT_SECONDS,
                request_id=request_id,
                actor_profile=profile,
                can_propose_changes=(
                    profile.casefold() in {"hermes", "aeriel duran"}
                ),
                images=images,
            )
            URL = model_url
            return _clean_model_reply(reply)
        except Exception as error:
            last_error = error

    if raise_on_error:
        raise YoshiModelError(
            "Local model request failed"
        ) from last_error

    return f"Error communicating with local model: {last_error}"


def listen_once():
    try:
        result = subprocess.run(
            ["termux-speech-to-text"],
            capture_output=True,
            text=True,
            timeout=60
        )

        heard = result.stdout.strip()

        if not heard:
            return None

        return heard

    except Exception as e:
        print(f"Voice input error: {e}")
        return None


def speak_text(text):
    try:
        subprocess.run(
            ["termux-tts-speak", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"Voice output error: {e}")



def get_weather(location="El Paso"):
    try:
        location = location.strip().replace(" ", "+")
        url = f"https://wttr.in/{location}?format=3"

        with urllib.request.urlopen(url, timeout=15) as response:
            return response.read().decode("utf-8").strip()

    except Exception as e:
        return f"Weather error: {e}"



def get_forecast(location="El Paso", day_index=1):
    try:
        location_q = location.strip().replace(" ", "+")
        url = f"https://wttr.in/{location_q}?format=j1"

        with urllib.request.urlopen(url, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))

        days = data.get("weather", [])

        if not days or day_index >= len(days):
            return "Forecast data unavailable."

        day = days[day_index]

        date = day.get("date", "unknown date")
        high_f = day.get("maxtempF", "?")
        low_f = day.get("mintempF", "?")

        hourly = day.get("hourly", [])

        rain_chances = []
        descriptions = []

        for hour in hourly:
            try:
                rain_chances.append(int(hour.get("chanceofrain", "0")))
            except ValueError:
                pass

            desc = hour.get("weatherDesc", [])
            if desc and isinstance(desc, list):
                value = desc[0].get("value")
                if value:
                    descriptions.append(value)

        max_rain = max(rain_chances) if rain_chances else 0

        condition = descriptions[len(descriptions)//2] if descriptions else "Unknown"

        return (
            f"{location}: {date}, {condition}, "
            f"high {high_f}°F, low {low_f}°F, "
            f"rain chance up to {max_rain}%"
        )

    except Exception as e:
        return f"Forecast error: {e}"



def get_battery_status():
    try:
        result = subprocess.run(
            ["termux-battery-status"],
            capture_output=True,
            text=True,
            timeout=10
        )

        data = json.loads(result.stdout)

        percentage = data.get("percentage", "?")
        status = data.get("status", "unknown")
        plugged = data.get("plugged", "unknown")
        temperature = data.get("temperature", "?")
        health = data.get("health", "unknown")

        return (
            f"Battery is at {percentage}%. "
            f"Status: {status}. "
            f"Power source: {plugged}. "
            f"Temperature: {temperature}°C. "
            f"Health: {health}."
        )

    except Exception as e:
        return f"Battery status error: {e}"



def get_device_status():
    parts = []

    # Battery
    try:
        result = subprocess.run(
            ["termux-battery-status"],
            capture_output=True,
            text=True,
            timeout=10
        )

        data = json.loads(result.stdout)

        percentage = data.get("percentage", "?")
        status = data.get("status", "unknown")
        plugged = data.get("plugged", "unknown")
        temperature = data.get("temperature", "?")
        health = data.get("health", "unknown")

        parts.append(f"Battery: {percentage}%")
        parts.append(f"Status: {status}")
        parts.append(f"Power: {plugged}")
        parts.append(f"Battery temp: {temperature}°C")
        parts.append(f"Health: {health}")

    except Exception:
        parts.append("Battery: unavailable")

    # User storage
    try:
        usage = subprocess.run(
            ["df", "-h", HOME],
            capture_output=True,
            text=True,
            timeout=10
        ).stdout.strip().splitlines()

        if len(usage) >= 2:
            fields = usage[-1].split()

            if len(fields) >= 5:
                total = fields[1]
                used = fields[2]
                free = fields[3]
                percent = fields[4]

                parts.append(f"Storage: {used} used of {total}")
                parts.append(f"Storage free: {free}")
                parts.append(f"Storage usage: {percent}")

    except Exception:
        parts.append("Storage: unavailable")

    # Yoshi/Termux home usage
    try:
        result = subprocess.run(
            ["du", "-sh", HOME],
            capture_output=True,
            text=True,
            timeout=20
        )

        home_usage = result.stdout.strip().split()[0]
        parts.append(f"Termux/Yoshi files: {home_usage}")

    except Exception:
        pass

    return " | ".join(parts)



def get_clipboard_text():
    try:
        result = subprocess.run(
            ["termux-clipboard-get"],
            capture_output=True,
            text=True,
            timeout=10
        )

        value = result.stdout.strip()

        if not value:
            return "Your clipboard is empty."

        return f"Your clipboard contains: {value}"

    except Exception as e:
        return f"Clipboard error: {e}"



def get_task_summary():
    from datetime import date

    today = date.today().isoformat()

    conn = connect_db()

    overdue = conn.execute(
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE done = 0
          AND due_date IS NOT NULL
          AND due_date < ?
        """,
        (today,)
    ).fetchone()[0]

    due_today = conn.execute(
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE done = 0
          AND due_date = ?
        """,
        (today,)
    ).fetchone()[0]

    from datetime import timedelta

    tomorrow = (
        date.today() + timedelta(days=1)
    ).isoformat()

    due_tomorrow = conn.execute(
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE done = 0
          AND due_date = ?
        """,
        (tomorrow,)
    ).fetchone()[0]

    high_priority = conn.execute(
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE done = 0
          AND priority = 'High'
        """
    ).fetchone()[0]

    weekday = date.today().strftime("%A")

    today_iso = date.today().isoformat()

    routines_today = conn.execute(
        """
        SELECT COUNT(*)
        FROM routines r
        WHERE r.active = 1
          AND lower(r.weekday) = lower(?)
          AND NOT EXISTS (
              SELECT 1
              FROM routine_completions rc
              WHERE rc.routine_id = r.id
                AND rc.completed_date = ?
          )
        """,
        (weekday, today_iso)
    ).fetchone()[0]

    conn.close()

    return {
        "overdue": overdue,
        "due_today": due_today,
        "due_tomorrow": due_tomorrow,
        "high_priority": high_priority,
        "routines_today": routines_today
    }



def search_saved_items(query, profile="Hermes"):
    query = query.strip().lower()

    if not query:
        return []

    results = []

    for memory_id, memory, *_ in get_memories(profile=profile):
        if query in memory.lower():
            results.append({
                "type": "memory",
                "id": memory_id,
                "text": memory
            })

    for note_id, note, *_ in get_notes():
        if query in note.lower():
            results.append({
                "type": "note",
                "id": note_id,
                "text": note
            })

    for task_id, task, done, priority, due_date, *_ in get_tasks():
        if query in task.lower():
            results.append({
                "type": "task",
                "id": task_id,
                "text": task,
                "done": bool(done),
                "priority": priority or "Normal",
                "due_date": due_date or ""
            })

    return results



def add_family_member(name, role="Family", notes=None):
    name = name.strip()
    role = role.strip() or "Family"

    if not name:
        return "Family member name cannot be empty."

    conn = connect_db()
    conn.execute(
        """
        INSERT INTO family_members (name, role, notes)
        VALUES (?, ?, ?)
        """,
        (name, role, notes)
    )
    conn.commit()
    conn.close()

    return f"Added {name} to the family as {role}. 🏠"


def get_family_members():
    conn = connect_db()
    rows = conn.execute(
        """
        SELECT id, name, role, notes
        FROM family_members
        ORDER BY id
        """
    ).fetchall()
    conn.close()
    return rows


def update_family_member(member_id, name=None, role=None, notes=None):
    try:
        member_id = int(member_id)
    except ValueError:
        return "Invalid family member ID."

    conn = connect_db()

    current = conn.execute(
        """
        SELECT name, role, notes
        FROM family_members
        WHERE id = ?
        """,
        (member_id,)
    ).fetchone()

    if not current:
        conn.close()
        return "Family member not found."

    current_name, current_role, current_notes = current

    new_name = name.strip() if name is not None else current_name
    new_role = role.strip() if role is not None else current_role
    new_notes = notes if notes is not None else current_notes

    conn.execute(
        """
        UPDATE family_members
        SET name = ?, role = ?, notes = ?
        WHERE id = ?
        """,
        (
            new_name or current_name,
            new_role or "Family",
            new_notes,
            member_id
        )
    )

    conn.commit()
    conn.close()

    return f"Updated {new_name or current_name}. 🏠"


def remove_family_member(member_id):
    try:
        member_id = int(member_id)
    except ValueError:
        return "Usage: /family remove <id>"

    conn = connect_db()
    cur = conn.execute(
        "DELETE FROM family_members WHERE id = ?",
        (member_id,)
    )
    conn.commit()
    conn.close()

    if cur.rowcount:
        return f"Family member #{member_id} removed."

    return "Family member not found."



def add_shopping_item(
    item,
    quantity=None,
    added_by=None,
    category="Other"
):
    item = item.strip()
    category = (category or "Other").strip().title()

    allowed = {
        "Groceries",
        "Pets",
        "Household",
        "School",
        "Tech",
        "Other",
    }

    if category not in allowed:
        category = "Other"

    if not item:
        return "Shopping item cannot be empty."

    conn = connect_db()

    conn.execute(
        """
        INSERT INTO shopping_items (
            item,
            quantity,
            bought,
            added_by,
            category
        )
        VALUES (?, ?, 0, ?, ?)
        """,
        (
            item,
            quantity,
            added_by,
            category
        )
    )

    conn.commit()
    conn.close()

    return (
        f"Added {item} to the shopping list "
        f"under {category}. 🛒"
    )


def get_shopping_items():
    conn = connect_db()

    rows = conn.execute(
        """
        SELECT
            id,
            item,
            quantity,
            bought,
            added_by,
            category
        FROM shopping_items
        ORDER BY bought, category, id
        """
    ).fetchall()

    conn.close()
    return rows


def set_shopping_bought(item_id, bought=True):
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        return "Invalid shopping item ID."

    conn = connect_db()

    cur = conn.execute(
        """
        UPDATE shopping_items
        SET bought = ?
        WHERE id = ?
        """,
        (1 if bought else 0, item_id)
    )

    conn.commit()
    conn.close()

    if cur.rowcount:
        return "Shopping item updated."

    return "Shopping item not found."


def delete_shopping_item(item_id):
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        return "Invalid shopping item ID."

    conn = connect_db()

    cur = conn.execute(
        "DELETE FROM shopping_items WHERE id = ?",
        (item_id,)
    )

    conn.commit()
    conn.close()

    if cur.rowcount:
        return "Shopping item removed."

    return "Shopping item not found."



def speak_backend(text, rate=0.9, pitch=0.9, language="en", region="US"):
    try:
        subprocess.Popen(
            [
                "termux-tts-speak",
                "-r", str(rate),
                "-p", str(pitch),
                "-l", str(language),
                "-n", str(region),
                "-s", "MUSIC",
                text
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        return True

    except Exception:
        return False


def format_memory_rows(rows):
    if not rows:
        return "No matching memories found."

    lines = []

    for row in rows:
        memory_id, memory, category, importance, created_at, updated_at, active = row
        lines.append(
            f"#{memory_id} [{category} | {importance}] {memory}"
        )

    return "\n".join(lines)




def assign_task_to_family(task_text, family_name):
    task_text = task_text.strip()
    family_name = family_name.strip()

    if not task_text or not family_name:
        return "Task and family member are required."

    conn = connect_db()

    member = conn.execute(
        """
        SELECT id, name
        FROM family_members
        WHERE lower(name) = lower(?)
           OR lower(name) LIKE lower(?) || ' %'
        ORDER BY
            CASE
                WHEN lower(name) = lower(?) THEN 0
                ELSE 1
            END
        LIMIT 1
        """,
        (family_name, family_name, family_name)
    ).fetchone()

    if not member:
        conn.close()
        return f"I couldn't find {family_name} in the family list."

    member_id, member_name = member

    conn.execute(
        """
        INSERT INTO tasks (
            task,
            done,
            priority,
            due_date,
            tag,
            assigned_to
        )
        VALUES (?, 0, 'Normal', NULL, 'Home', ?)
        """,
        (task_text, member_id)
    )

    conn.commit()
    conn.close()

    return f"Assigned {task_text} to {member_name}. 🏠"


def create_backup():
    from datetime import datetime

    home = Path.home()
    downloads = home / "storage" / "downloads"

    if not downloads.exists():
        return "Downloads folder is not available."

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    backup_name = f"Yoshi-Backup-{stamp}.tar.gz"
    backup_path = downloads / backup_name

    try:
        result = subprocess.run(
            [
                "tar",
                "--exclude=yoshi/*.log",
                "--exclude=yoshi/__pycache__",
                "--exclude=yoshi/*.pyc",
                "-czf",
                str(backup_path),
                "yoshi"
            ],
            cwd=str(home),
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            return f"Backup failed: {result.stderr.strip()}"

        return f"Backup created: {backup_name} 💾"

    except Exception as e:
        return f"Backup failed: {e}"



def add_reminder(reminder, due_date=None, assigned_to=None):
    reminder = reminder.strip()

    if not reminder:
        return "Reminder cannot be empty."

    conn = connect_db()

    conn.execute(
        """
        INSERT INTO reminders (
            reminder,
            due_date,
            assigned_to,
            done
        )
        VALUES (?, ?, ?, 0)
        """,
        (reminder, due_date, assigned_to)
    )

    conn.commit()
    conn.close()

    return f"Reminder added: {reminder}. ⏰"


def get_reminders():
    conn = connect_db()

    rows = conn.execute(
        """
        SELECT id, reminder, due_date, assigned_to, done
        FROM reminders
        ORDER BY done, due_date, id
        """
    ).fetchall()

    conn.close()
    return rows


def complete_reminder(reminder_id):
    try:
        reminder_id = int(reminder_id)
    except (ValueError, TypeError):
        return "Invalid reminder ID."

    conn = connect_db()

    cur = conn.execute(
        """
        UPDATE reminders
        SET done = 1
        WHERE id = ?
        """,
        (reminder_id,)
    )

    conn.commit()
    conn.close()

    if cur.rowcount:
        return "Reminder completed. ✅"

    return "Reminder not found."



def add_routine(routine, weekday=None, assigned_to=None):
    routine = routine.strip()

    if not routine:
        return "Routine cannot be empty."

    conn = connect_db()

    conn.execute(
        """
        INSERT INTO routines (
            routine,
            weekday,
            assigned_to,
            active
        )
        VALUES (?, ?, ?, 1)
        """,
        (routine, weekday, assigned_to)
    )

    conn.commit()
    conn.close()

    if weekday:
        return f"Routine added: {routine} every {weekday}. 🔁"

    return f"Routine added: {routine}. 🔁"


def get_routines():
    conn = connect_db()

    rows = conn.execute(
        """
        SELECT id, routine, weekday, assigned_to, active
        FROM routines
        ORDER BY active DESC, id
        """
    ).fetchall()

    conn.close()
    return rows


def delete_routine(routine_id):
    try:
        routine_id = int(routine_id)
    except (ValueError, TypeError):
        return "Invalid routine ID."

    conn = connect_db()

    cur = conn.execute(
        "DELETE FROM routines WHERE id = ?",
        (routine_id,)
    )

    conn.commit()
    conn.close()

    if cur.rowcount:
        return "Routine removed."

    return "Routine not found."



def complete_routine_for_today(routine_id):
    from datetime import date

    try:
        routine_id = int(routine_id)
    except (ValueError, TypeError):
        return "Invalid routine ID."

    today = date.today().isoformat()

    conn = connect_db()

    exists = conn.execute(
        "SELECT id FROM routines WHERE id = ?",
        (routine_id,)
    ).fetchone()

    if not exists:
        conn.close()
        return "Routine not found."

    conn.execute(
        """
        INSERT OR IGNORE INTO routine_completions (
            routine_id,
            completed_date
        )
        VALUES (?, ?)
        """,
        (routine_id, today)
    )

    conn.commit()
    conn.close()

    return "Routine completed for today. ✅"



def add_family_routine(routine, family_name, weekday):
    routine = routine.strip()
    family_name = family_name.strip()
    weekday = weekday.strip().title()

    conn = connect_db()

    member = conn.execute(
        """
        SELECT id, name
        FROM family_members
        WHERE lower(name) = lower(?)
           OR lower(name) LIKE lower(?) || ' %'
        ORDER BY
            CASE
                WHEN lower(name) = lower(?) THEN 0
                ELSE 1
            END
        LIMIT 1
        """,
        (
            family_name,
            family_name,
            family_name
        )
    ).fetchone()

    if not member:
        conn.close()
        return f"I couldn't find {family_name} in the family list."

    member_id, member_name = member

    conn.execute(
        """
        INSERT INTO routines (
            routine,
            weekday,
            assigned_to,
            active
        )
        VALUES (?, ?, ?, 1)
        """,
        (routine, weekday, member_id)
    )

    conn.commit()
    conn.close()

    return (
        f"Routine added for {member_name}: "
        f"{routine} every {weekday}. 🔁"
    )



def find_family_member(name):
    name = name.strip()

    conn = connect_db()

    rows = conn.execute(
        """
        SELECT id, name, role, notes
        FROM family_members
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    exact = [
        row for row in rows
        if row[1].lower() == name.lower()
    ]

    if len(exact) == 1:
        return exact[0]

    first_name_matches = [
        row for row in rows
        if row[1].lower().startswith(name.lower() + " ")
    ]

    if len(first_name_matches) == 1:
        return first_name_matches[0]

    return None


def memory_importance_report():
    """Suggest conservative importance changes based on usage."""

    conn = connect_db()

    rows = conn.execute(
        """
        SELECT
            id,
            memory,
            category,
            importance,
            COALESCE(recall_count, 0)
        FROM memories
        WHERE active = 1
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    changes = []

    for memory_id, memory, category, importance, recall_count in rows:
        current = importance or "Normal"
        category = category or "General"

        if current == "High":
            continue

        suggested = current
        reason = None

        if (
            current == "Normal"
            and recall_count >= 8
            and category != "Preference"
        ):
            suggested = "High"
            reason = "frequently recalled"

        elif (
            current == "Low"
            and recall_count >= 4
        ):
            suggested = "Normal"
            reason = "recalled repeatedly"

        if suggested != current:
            changes.append({
                "id": memory_id,
                "memory": memory,
                "old_importance": current,
                "new_importance": suggested,
                "reason": reason,
            })

    return changes


def run_memory_importance_adjustment(dry_run=True):
    changes = memory_importance_report()

    if dry_run:
        return {
            "mode": "dry_run",
            "changes": changes,
        }

    conn = connect_db()

    try:
        for item in changes:
            conn.execute(
                """
                UPDATE memories
                SET importance = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    item["new_importance"],
                    item["id"],
                )
            )

        conn.commit()

    finally:
        conn.close()

    return {
        "mode": "applied",
        "updated": len(changes),
        "changes": changes,
    }

def main():
    from yoshi_router import route_tool
    connect_db().close()
    server_process = start_server()

    history = []

    print("==============================")
    print("       YOSHI MOBILE AI")
    print("==============================")
    print("Memory: ON")
    print("Local AI: ON")
    print()
    print("Commands:")
    print("  /memories")
    print("  /remember <fact>")
    print("  /forget <id>")
    print("  /update <id> <new fact>")
    print("  /auto on")
    print("  /auto off")
    print("  /voice")
    print("  /voice on")
    print("  /voice off")
    print("  /weather [location]")
    print("  /battery")
    print("  /status")
    print("  /clear")
    print("  /exit")
    print()

    try:
        while True:
            user_text = input("You: ").strip()

            if not user_text:
                continue

            if user_text == "/exit":
                print("Yoshi: See you later, Hermes.")
                break

            elif user_text == "/memories":
                show_memories()
                continue

            elif user_text.startswith("/memories "):
                memory_filter = user_text[len("/memories "):].strip()

                if memory_filter.lower() in {"high", "normal", "low"}:
                    rows = get_memories(
                        importance=memory_filter.title()
                    )
                else:
                    rows = get_memories(
                        category=memory_filter.title()
                    )

                print("\n" + format_memory_rows(rows) + "\n")
                continue

            elif user_text.startswith("/find-memory "):
                query = user_text[len("/find-memory "):].strip()

                if not query:
                    print("Usage: /find-memory <search>")
                else:
                    rows = smart_recall(query, limit=10)
                    print("\n" + format_memory_rows(rows) + "\n")

                continue

            elif user_text.startswith("/remember "):
                add_memory(user_text[len("/remember "):])
                history.clear()
                print("Conversation history refreshed.")
                continue

            elif user_text.startswith("/forget "):
                forget_memory(user_text[len("/forget "):])
                history.clear()
                print("Conversation history refreshed.")
                continue

            elif user_text.startswith("/restore-memory "):
                result = restore_memory(
                    user_text[len("/restore-memory "):].strip()
                )
                print(result)
                history.clear()
                print("Conversation history refreshed.")
                continue

            elif user_text.startswith("/update "):
                raw = user_text[len("/update "):].strip()
                parts = raw.split(" ", 1)

                if len(parts) != 2:
                    print("Usage: /update <id> <new fact>")
                    continue

                memory_id, new_text = parts

                result = update_memory(
                    memory_id,
                    text=new_text
                )

                print(result)
                history.clear()
                print("Conversation history refreshed.")
                continue

            elif user_text.startswith("/memory-category "):
                raw = user_text[len("/memory-category "):].strip()
                parts = raw.split(" ", 1)

                if len(parts) != 2:
                    print("Usage: /memory-category <id> <category>")
                    continue

                memory_id, category = parts

                result = update_memory(
                    memory_id,
                    category=category
                )

                print(result)
                history.clear()
                continue

            elif user_text.startswith("/memory-importance "):
                raw = user_text[len("/memory-importance "):].strip()
                parts = raw.split(" ", 1)

                if len(parts) != 2:
                    print("Usage: /memory-importance <id> <Low|Normal|High>")
                    continue

                memory_id, importance = parts

                result = update_memory(
                    memory_id,
                    importance=importance
                )

                print(result)
                history.clear()
                continue

            elif user_text == "/auto on":
                globals()["AUTO_MEMORY"] = True
                print("Automatic memory: ON")
                continue

            elif user_text == "/auto off":
                globals()["AUTO_MEMORY"] = False
                print("Automatic memory: OFF")
                continue

            elif user_text == "/voice":
                print("Listening...")
                heard = listen_once()

                if not heard:
                    print("I didn't catch that.")
                    continue

                print(f"You said: {heard}")

                saved_automatically = auto_remember(heard)

                if saved_automatically == "updated":
                    history.clear()

                answer = ask_yoshi(history, heard)

                print(f"\nYoshi: {answer}\n")
                speak_text(answer)

                if saved_automatically == "saved":
                    print("🧠 Auto-memory saved.\n")
                elif saved_automatically == "updated":
                    print("🧠 Existing memory updated.\n")

                history.append({
                    "role": "user",
                    "content": heard
                })

                history.append({
                    "role": "assistant",
                    "content": answer
                })

                history = history[-12:]
                continue

            elif user_text == "/voice on":
                globals()["VOICE_MODE"] = True
                print("Voice mode: ON")
                continue

            elif user_text == "/voice off":
                globals()["VOICE_MODE"] = False
                print("Voice mode: OFF")
                continue

            elif user_text == "/weather":
                weather = get_weather("El Paso")
                print(f"Weather: {weather}")
                continue

            elif user_text.startswith("/weather "):
                location = user_text[len("/weather "):].strip()
                weather = get_weather(location)
                print(f"Weather: {weather}")
                continue

            elif user_text == "/battery":
                answer = get_battery_status()
                print(f"Yoshi: {answer}")

                if VOICE_MODE:
                    speak_text(answer)

                continue

            elif user_text == "/status":
                answer = get_device_status()
                print(f"Yoshi: {answer}")

                if VOICE_MODE:
                    speak_text(answer)

                continue

            elif user_text == "/clear":
                history.clear()
                print("Conversation history cleared.")
                continue

            handled, tool_reply = route_tool(user_text)

            if handled:
                print(f"\nYoshi: {tool_reply}\n")

                if VOICE_MODE:
                    speak_text(tool_reply)

                history.append({
                    "role": "user",
                    "content": user_text
                })

                history.append({
                    "role": "assistant",
                    "content": tool_reply
                })

                history = history[-12:]
                continue

            lower_text = user_text.lower()

            battery_phrases = (
                "what's my battery",
                "whats my battery",
                "what is my battery",
                "battery level",
                "battery percentage",
                "am i charging",
                "am i plugged in",
                "how much battery",
            )

            if any(phrase in lower_text for phrase in battery_phrases):
                answer = get_battery_status()

                print(f"\nYoshi: {answer}\n")

                if VOICE_MODE:
                    speak_text(answer)

                history.append({
                    "role": "user",
                    "content": user_text
                })

                history.append({
                    "role": "assistant",
                    "content": answer
                })

                history = history[-12:]
                continue

            device_status_phrases = (
                "how's my phone",
                "hows my phone",
                "how is my phone",
                "device status",
                "phone status",
                "how much storage",
                "how much space",
                "storage left",
                "storage free",
                "is my battery healthy",
                "battery health",
            )

            if any(phrase in lower_text for phrase in device_status_phrases):
                answer = get_device_status()

                print(f"\nYoshi: {answer}\n")

                if VOICE_MODE:
                    speak_text(answer)

                history.append({
                    "role": "user",
                    "content": user_text
                })

                history.append({
                    "role": "assistant",
                    "content": answer
                })

                history = history[-12:]
                continue

            # Tomorrow forecast routing
            if "tomorrow" in lower_text and (
                "weather" in lower_text
                or "forecast" in lower_text
                or "rain" in lower_text
                or "temperature" in lower_text
                or "high" in lower_text
                or "low" in lower_text
            ):
                location = "El Paso"

                match = re.search(
                    r"\bin\s+(.+?)[?.!]?$",
                    user_text,
                    flags=re.IGNORECASE
                )

                if match:
                    location = match.group(1).strip()

                forecast = get_forecast(location, 1)
                answer = f"Tomorrow's forecast: {forecast}"

                print(f"\nYoshi: {answer}\n")

                if VOICE_MODE:
                    speak_text(answer)

                history.append({
                    "role": "user",
                    "content": user_text
                })

                history.append({
                    "role": "assistant",
                    "content": answer
                })

                history = history[-12:]
                continue

            weather_phrases = (
                "what's the weather",
                "whats the weather",
                "what is the weather",
                "weather today",
                "weather outside",
                "how's the weather",
                "hows the weather",
            )

            if any(phrase in lower_text for phrase in weather_phrases):
                location = "El Paso"

                match = re.search(
                    r"(?:weather|weather today|weather outside).*?\bin\s+(.+?)[?.!]?$",
                    user_text,
                    flags=re.IGNORECASE
                )

                if match:
                    location = match.group(1).strip()

                weather = get_weather(location)
                answer = f"Current weather: {weather}"

                print(f"\nYoshi: {answer}\n")

                if VOICE_MODE:
                    speak_text(answer)

                history.append({
                    "role": "user",
                    "content": user_text
                })

                history.append({
                    "role": "assistant",
                    "content": answer
                })

                history = history[-12:]
                continue

            saved_automatically = auto_remember(user_text)

            if saved_automatically == "updated":
                history.clear()

            answer = ask_yoshi(history, user_text)

            print(f"\nYoshi: {answer}\n")

            if VOICE_MODE:
                speak_text(answer)

            if saved_automatically == "saved":
                print("🧠 Auto-memory saved.\n")
            elif saved_automatically == "updated":
                print("🧠 Existing memory updated.\n")

            history.append({
                "role": "user",
                "content": user_text
            })

            history.append({
                "role": "assistant",
                "content": answer
            })

            # Keep phone context usage under control.
            history = history[-12:]

    finally:
        if server_process is not None:
            server_process.terminate()


if __name__ == "__main__":
    main()
