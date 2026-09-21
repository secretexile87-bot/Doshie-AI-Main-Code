"""Yoshi Memory v3 helpers.
Adds life archive organization without replacing existing memory.
"""
from datetime import datetime
import json
from pathlib import Path

BASE = Path.home() / "yoshi"
JOURNAL = BASE / "life_journal.jsonl"

CATEGORIES = [
    "Personal", "Family", "Life", "Technology",
    "Yoshi", "Goals", "Lessons"
]


def add_life_entry(kind, text, category="Life"):
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "kind": kind,
        "category": category,
        "text": text,
    }
    with JOURNAL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def timeline(limit=20):
    if not JOURNAL.exists():
        return []
    rows = JOURNAL.read_text(encoding="utf-8").splitlines()
    return [json.loads(x) for x in rows[-limit:]]


def profile_summary():
    return {
        "categories": CATEGORIES,
        "journal": str(JOURNAL),
        "entries": len(timeline(100000)),
    }


def export_story():
    rows = timeline(100000)
    return "\n".join(
        f"{r['time']} [{r['category']}] {r['text']}"
        for r in rows
    )
