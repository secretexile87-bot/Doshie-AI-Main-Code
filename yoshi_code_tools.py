from pathlib import Path

ROOT = Path.home().joinpath("yoshi").resolve()

ALLOWED_SUFFIXES = {
    ".py", ".js", ".css", ".html", ".md", ".sh"
}

BLOCKED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    "backups"
}

BLOCKED_NAMES = {
    ".env", "identity.txt", "settings.json", "profile_session.key",
    "memory.db", "memory_backup.db", "chat_history.json"
}

BLOCKED_SUFFIXES = {
    ".key", ".crt", ".db", ".sqlite", ".sqlite3", ".jsonl"
}


def _allowed_file(path):
    try:
        resolved = path.resolve()
        resolved.relative_to(ROOT)
    except (OSError, ValueError):
        return False

    relative = resolved.relative_to(ROOT)

    if any(part in BLOCKED_DIRS for part in relative.parts):
        return False

    if resolved.name in BLOCKED_NAMES:
        return False

    if ".before-" in resolved.name or resolved.name.endswith(".disabled"):
        return False

    if resolved.suffix.lower() in BLOCKED_SUFFIXES:
        return False

    return (
        resolved.is_file()
        and resolved.suffix.lower() in ALLOWED_SUFFIXES
    )


def _resolve(relative_path):
    raw = str(relative_path or "").strip()

    if not raw or Path(raw).is_absolute():
        raise ValueError("Use a relative project path.")

    candidate = ROOT.joinpath(raw).resolve()

    try:
        candidate.relative_to(ROOT)
    except ValueError as error:
        raise ValueError("Path leaves the Yoshi project.") from error

    if not _allowed_file(candidate):
        raise ValueError("That file is private, unsupported, or unavailable.")

    return candidate


def list_code_files(limit=200):
    files = []

    for path in ROOT.rglob("*"):
        if _allowed_file(path):
            files.append(path.relative_to(ROOT).as_posix())

    files.sort()
    return files[:max(1, min(int(limit), 500))]


def read_code_file(relative_path, start_line=1, line_count=200):
    path = _resolve(relative_path)

    if path.stat().st_size > 200_000:
        raise ValueError("File is too large for automatic reading.")

    lines = path.read_text(
        encoding="utf-8",
        errors="replace"
    ).splitlines()

    start = max(1, int(start_line))
    count = max(1, min(int(line_count), 300))
    selected = lines[start - 1:start - 1 + count]

    return "\n".join(
        f"{number}: {line}"
        for number, line in enumerate(selected, start=start)
    )


def search_code(query, limit=30):
    needle = str(query or "").strip().lower()

    if len(needle) < 2:
        raise ValueError("Search text must contain at least two characters.")

    matches = []
    maximum = max(1, min(int(limit), 100))

    for relative in list_code_files(limit=500):
        path = ROOT.joinpath(relative)

        if path.stat().st_size > 200_000:
            continue

        for number, line in enumerate(
            path.read_text(
                encoding="utf-8",
                errors="replace"
            ).splitlines(),
            start=1
        ):
            if needle in line.lower():
                matches.append(
                    f"{relative}:{number}: {line.strip()[:240]}"
                )

                if len(matches) >= maximum:
                    return matches

    return matches
