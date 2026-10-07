#!/usr/bin/env python3
"""Doshie Command-Line Notepad Application.

A lightweight, robust notes manager supporting both interactive menu mode
and direct command-line arguments.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys

NOTES_DIR = Path.home() / ".doshie"
NOTES_FILE = NOTES_DIR / "notepad_data.json"


def ensure_storage() -> list[dict]:
    """Ensure storage directory and file exist, return notes list."""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    if not NOTES_FILE.exists():
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_notes(notes: list[dict]) -> None:
    """Save notes to disk."""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


def add_note(title: str, content: str = "", tags: list[str] | None = None) -> dict:
    """Add a new note."""
    notes = ensure_storage()
    new_id = (max([n.get("id", 0) for n in notes]) + 1) if notes else 1
    note = {
        "id": new_id,
        "title": title.strip(),
        "content": content.strip(),
        "tags": tags or [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    notes.append(note)
    save_notes(notes)
    print(f"✅ Note #{new_id} added: '{note['title']}'")
    return note


def list_notes() -> None:
    """Display all notes."""
    notes = ensure_storage()
    if not notes:
        print("📭 No notes found. Add one with: python3 notepad.py add 'My note'")
        return

    print("\n" + "=" * 60)
    print(f"📝 DOSHIE NOTEPAD ({len(notes)} note{'s' if len(notes) != 1 else ''})")
    print("=" * 60)
    for n in notes:
        tags_str = f" [tags: {', '.join(n.get('tags', []))}]" if n.get("tags") else ""
        print(f"[{n['id']}] {n['title']}{tags_str} ({n.get('updated_at', '')})")
        if n.get("content"):
            snippet = n['content'].replace("\n", " ")
            if len(snippet) > 80:
                snippet = snippet[:77] + "..."
            print(f"    {snippet}")
    print("=" * 60 + "\n")


def view_note(note_id: int) -> None:
    """View details of a specific note."""
    notes = ensure_storage()
    for n in notes:
        if n.get("id") == note_id:
            print("\n" + "-" * 50)
            print(f"Note #{n['id']}: {n['title']}")
            print(f"Created: {n.get('created_at')} | Updated: {n.get('updated_at')}")
            if n.get("tags"):
                print(f"Tags: {', '.join(n['tags'])}")
            print("-" * 50)
            print(n.get("content") or "(Empty note)")
            print("-" * 50 + "\n")
            return
    print(f"❌ Note #{note_id} not found.")


def delete_note(note_id: int) -> None:
    """Delete a note by ID."""
    notes = ensure_storage()
    initial_len = len(notes)
    notes = [n for n in notes if n.get("id") != note_id]
    if len(notes) < initial_len:
        save_notes(notes)
        print(f"🗑️ Note #{note_id} deleted.")
    else:
        print(f"❌ Note #{note_id} not found.")


def search_notes(query: str) -> None:
    """Search notes by title, content, or tags."""
    notes = ensure_storage()
    q = query.lower()
    matches = [
        n for n in notes
        if q in n.get("title", "").lower()
        or q in n.get("content", "").lower()
        or any(q in t.lower() for t in n.get("tags", []))
    ]
    if not matches:
        print(f"🔍 No notes matching '{query}'.")
        return

    print(f"\n🔍 Found {len(matches)} match(es) for '{query}':")
    for n in matches:
        print(f"[{n['id']}] {n['title']} ({n.get('created_at')})")


def interactive_menu() -> None:
    """Interactive CLI menu."""
    while True:
        print("\n--- 📝 Doshie Notepad CLI ---")
        print("1. List notes")
        print("2. Add note")
        print("3. View note")
        print("4. Search notes")
        print("5. Delete note")
        print("6. Exit")
        try:
            choice = input("Select option (1-6): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if choice == "1":
            list_notes()
        elif choice == "2":
            title = input("Enter note title: ").strip()
            if not title:
                print("Title cannot be empty.")
                continue
            content = input("Enter note body (optional): ").strip()
            tags_raw = input("Enter tags (comma separated, optional): ").strip()
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            add_note(title, content, tags)
        elif choice == "3":
            val = input("Enter note ID: ").strip()
            if val.isdigit():
                view_note(int(val))
        elif choice == "4":
            q = input("Search query: ").strip()
            if q:
                search_notes(q)
        elif choice == "5":
            val = input("Enter note ID to delete: ").strip()
            if val.isdigit():
                delete_note(int(val))
        elif choice == "6" or choice.lower() in ["exit", "q", "quit"]:
            print("Goodbye!")
            break


def main():
    parser = argparse.ArgumentParser(description="Doshie Command-Line Notepad App")
    subparsers = parser.add_subparsers(dest="command")

    # Add command
    p_add = subparsers.add_parser("add", help="Add a new note")
    p_add.add_argument("title", help="Note title")
    p_add.add_argument("-c", "--content", default="", help="Note body content")
    p_add.add_argument("-t", "--tags", nargs="*", default=[], help="Tags")

    # List command
    subparsers.add_parser("list", help="List all notes")

    # View command
    p_view = subparsers.add_parser("view", help="View note details")
    p_view.add_argument("id", type=int, help="Note ID")

    # Delete command
    p_del = subparsers.add_parser("delete", help="Delete note")
    p_del.add_argument("id", type=int, help="Note ID")

    # Search command
    p_search = subparsers.add_parser("search", help="Search notes")
    p_search.add_argument("query", help="Keyword to search")

    args = parser.parse_args()

    if args.command == "add":
        add_note(args.title, args.content, args.tags)
    elif args.command == "list":
        list_notes()
    elif args.command == "view":
        view_note(args.id)
    elif args.command == "delete":
        delete_note(args.id)
    elif args.command == "search":
        search_notes(args.query)
    else:
        # If no arguments provided in a TTY, launch interactive menu; otherwise show list
        if sys.stdin.isatty():
            interactive_menu()
        else:
            list_notes()


if __name__ == "__main__":
    main()
