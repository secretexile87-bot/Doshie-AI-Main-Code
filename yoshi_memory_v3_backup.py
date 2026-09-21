from pathlib import Path
import sqlite3
import subprocess
import shutil
import urllib.request
import yoshi_settings
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
    "yoshi:latest"
)
PORT = _environment_int("YOSHI_MODEL_PORT", 11434, minimum=1024)
CONTEXT_SIZE = _environment_int("YOSHI_CONTEXT_SIZE", 2048, minimum=512)
MODEL_THREADS = _environment_int("YOSHI_MODEL_THREADS", 4)
MAX_RESPONSE_TOKENS = _environment_int(
    "YOSHI_MAX_RESPONSE_TOKENS",
    400,
    minimum=64
)
MODEL_TEMPERATURE = _environment_float(
    "YOSHI_MODEL_TEMPERATURE",
    0.7
)
MODEL_TIMEOUT_SECONDS = _environment_int(
    "YOSHI_MODEL_TIMEOUT_SECONDS",
    180,
    minimum=10
)
URL = f"http://127.0.0.1:{PORT}/v1/chat/completions"

os.makedirs(YOSHI_DIR, exist_ok=True)

AUTO_MEMORY = True
VOICE_MODE = False
SCHEMA_VERSION = 1


class YoshiModelError(RuntimeError):
    """Raised when the local model cannot complete a request."""


def connect_db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
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
            memory TEXT NOT NULL UNIQUE,
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
    }

    for name, definition in memory_upgrades.items():
        if name not in memory_columns:
            conn.execute(
                f"ALTER TABLE memories ADD COLUMN {name} {definition}"
            )

    conn.execute("""
        UPDATE memories
        SET updated_at = created_at
        WHERE updated_at IS NULL
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
        with sqlite3.connect(uri, uri=True, timeout=2) as database:
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


def get_memories(category=None, importance=None, include_inactive=False):
    conn = connect_db()

    query = """
        SELECT id, memory, category, importance, created_at, updated_at, active
        FROM memories
        WHERE 1=1
    """
    params = []

    if not include_inactive:
        query += " AND active = 1"

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



def detect_memory_category(text):
    lower = text.lower()

    if any(x in lower for x in (
        "wife", "husband", "son", "daughter", "kid", "kids",
        "family", "mother", "father", "mom", "dad"
    )):
        return "Family"

    if any(x in lower for x in (
        "phone", "computer", "pc", "laptop", "linux", "windows",
        "android", "samsung", "intel", "gpu", "cpu", "router", "wifi"
    )):
        return "Tech"

    if any(x in lower for x in (
        "goal", "plan to", "want to become", "working toward",
        "my future", "career"
    )):
        return "Goal"

    if any(x in lower for x in (
        "home", "house", "garage", "thermostat", "light",
        "camera", "door", "lock"
    )):
        return "Home"

    if any(x in lower for x in (
        "favorite", "i like", "i love", "i prefer", "i dislike",
        "i hate"
    )):
        return "Preference"

    if any(x in lower for x in (
        "game", "gaming", "xbox", "playstation", "steam"
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


def add_memory(text, category="General", importance="Normal"):
    text = text.strip()
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
            INSERT INTO memories
                (memory, category, importance, updated_at, active)
            VALUES
                (?, ?, ?, CURRENT_TIMESTAMP, 1)
            """,
            (text, category, importance)
        )
        conn.commit()
        result = f"Memory saved. 🧠 [{category} | {importance}]"
        print(result)

    except sqlite3.IntegrityError:
        existing = conn.execute(
            "SELECT id, active FROM memories WHERE memory = ?",
            (text,)
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


def restore_memory(memory_id):
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
        WHERE id = ? AND active = 0
        """,
        (memory_id,)
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



def should_auto_remember(text):
    clean = text.strip()
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
    )

    return any(phrase in lower for phrase in useful_phrases)



def normalize_memory(text):
    clean = text.strip()

    if clean.lower().startswith("you:"):
        clean = clean[4:].strip()

    lower = clean.lower()

    patterns = [
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

def auto_remember(text):
    if not should_auto_remember(text):
        return False

    clean = normalize_memory(text)
    lower = clean.lower()

    categories = {
        "favorite season": "my favorite season",
        "favorite fruit": "my favorite fruit",
        "favorite animal": "my favorite animal",
        "favorite test color": "my favorite test color",

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

        "goal": (
            "my goal",
            "my goals",
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
            "SELECT id, memory FROM memories ORDER BY id"
        ).fetchall()

        for category, markers in categories.items():

            if isinstance(markers, str):
                markers = (markers,)

            new_matches_category = any(
                marker in lower for marker in markers
            )

            if not new_matches_category:
                continue

            existing = []

            for memory_id, memory in rows:
                old_lower = memory.lower()

                if any(marker in old_lower for marker in markers):
                    existing.append((memory_id, memory))

            if existing:
                memory_id = existing[0][0]

                conn.execute(
                    "UPDATE memories SET memory = ? WHERE id = ?",
                    (clean, memory_id)
                )

                for duplicate_id, _ in existing[1:]:
                    conn.execute(
                        "DELETE FROM memories WHERE id = ?",
                        (duplicate_id,)
                    )

                conn.commit()
                return "updated"

        conn.execute(
            "INSERT INTO memories (memory) VALUES (?)",
            (clean,)
        )

        conn.commit()
        return "saved"

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


def smart_recall(query, limit=5):
    """Return the saved memories most relevant to a message.

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
    for row in get_memories():
        memory = row[1]
        category = row[2] or "General"
        importance = row[3] or "Normal"
        memory_lower = memory.lower()
        memory_words = words(memory_lower)

        score = len(expanded.intersection(memory_words)) * 4
        category_lower = category.lower()
        importance_lower = importance.lower()

        if category_lower in expanded:
            score += 6
        if category_lower in query:
            score += 5
        if query in memory_lower or memory_lower in query:
            score += 12
        if importance_lower == "high" and score:
            score += 2
        if "important" in query or "priority" in query:
            if importance_lower == "high":
                score += 8

        if score:
            scored.append((score, row))

    scored.sort(
        key=lambda item: (
            item[0],
            1 if (item[1][3] or "").lower() == "high" else 0,
            item[1][0]
        ),
        reverse=True
    )
    return [row for _, row in scored[:limit]]


def show_memories():
    memories = get_memories()

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


def build_system_prompt(memory_rows=None):
    try:
        with open(IDENTITY_PATH, "r", encoding="utf-8") as f:
            identity = f.read().strip()
    except FileNotFoundError:
        identity = "You are Yoshi, Hermes's personal AI assistant."

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

Act as Yoshi's computer-lab mode.

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

    memories = get_memories() if memory_rows is None else memory_rows

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

IMPORTANT MEMORY RULES:

You have a persistent long-term memory database.

The facts below are memories about Hermes.
Treat them as true user-provided facts unless Hermes later corrects them.

When Hermes asks about something that appears in memory:
- Answer using the saved memory.
- Do not say that you do not have memory.
- Do not say that AI assistants cannot remember.
- Do not describe the memory as your own personal preference.
- Understand that phrases such as "my favorite" refer to Hermes, not Yoshi.
- When referring to saved memories about Hermes, use "you" and "your", never "I", "me", or "my".

SAVED LONG-TERM MEMORIES:
{memory_text}

Example:
Memory: "My favorite color is black."
Hermes asks: "What is my favorite color?"
Correct answer: "Your favorite color is black."

Use saved memories naturally and directly.
""".strip()


def server_ready():
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{PORT}/v1/models",
            timeout=2
        ) as response:
            if response.status != 200:
                return False
            model_data = json.loads(response.read().decode("utf-8"))

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

        return MODEL in available

    except Exception:
        return False

def start_server():
    if server_ready():
        print("Yoshi is connected to Ollama. 🦖")
        return None

    print("Ollama is not ready on the configured model port.")
    sys.exit(1)

def ask_yoshi(history, user_text, raise_on_error=False):
    memories = smart_recall(user_text, limit=5)

    if memories:
        memory_text = "\n".join(
            f"- [{row[2]} | {row[3]}] {row[1]}"
            for row in memories
        )
    else:
        memory_text = "- No directly relevant saved memories found."

    try:
        import yoshi_history
        life_entries = [
            entry for entry in yoshi_history.recall_life_journal(user_text, limit=12)
            if entry.get("role") == "user"
        ][:6]
    except Exception:
        life_entries = []

    system_prompt = build_system_prompt(memories)
    if life_entries:
        life_text = "\n".join(
            f"- {entry.get('timestamp', 'unknown time')} | "
            f"Hermes: "
            f"{str(entry.get('content', ''))[:700]}"
            for entry in life_entries
        )
        system_prompt += (
            "\n\nRELEVANT LIFE ARCHIVE EXCERPTS:\n" + life_text +
            "\n\nThese are excerpts from Hermes's permanent conversation archive. "
            "Use them when relevant. These excerpts contain Hermes's own words only. "
            "When speaking directly to Hermes, refer to Hermes as you/your rather than he/his. "
            "Do not invent details that are not present."
        )

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": (
                "Here are persistent facts about Hermes that you must use "
                "when relevant:\n"
                f"{memory_text}\n\n"
                "Acknowledge these internally and answer future questions "
                "using them naturally."
            )
        },
        {
            "role": "assistant",
            "content": "Understood. I will use those saved facts when relevant."
        }
    ]

    messages.extend(history)

    messages.append(
        {
            "role": "user",
            "content": user_text
        }
    )

    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "temperature": MODEL_TEMPERATURE,
        "max_tokens": MAX_RESPONSE_TOKENS,
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
            timeout=MODEL_TIMEOUT_SECONDS
        ) as response:
            data = json.loads(response.read().decode("utf-8"))

        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        if raise_on_error:
            raise YoshiModelError("Local model request failed") from e
        return f"Error communicating with local model: {e}"



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



def search_saved_items(query):
    query = query.strip().lower()

    if not query:
        return []

    results = []

    for memory_id, memory, *_ in get_memories():
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



def speak_backend(text, rate=0.95, pitch=1.0, language="en", region="US"):
    """Fallback TTS when browser/device speech synthesis is unavailable."""
    try:
        termux_tts = shutil.which("termux-tts-speak")
        if termux_tts:
            subprocess.Popen(
                [
                    termux_tts,
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

        speech_dispatcher = shutil.which("spd-say")
        if speech_dispatcher:
            subprocess.Popen(
                [speech_dispatcher, text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
    except Exception:
        pass

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
