import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path


ROOT = Path.home().joinpath("yoshi").resolve()
REQUESTS_PATH = ROOT / "permission_requests.json"
AUDIT_PATH = ROOT / "permission_audit.jsonl"
BACKUP_ROOT = ROOT / "backups" / "permission-actions"
ALLOWED_ACTIONS = {"exact_replace", "create_file", "run_regression"}
ALLOWED_SUFFIXES = {".py", ".js", ".css", ".html", ".md", ".sh"}
BLOCKED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "backups"}
BLOCKED_NAMES = {".env", "identity.txt", "settings.json", "profile_session.key"}
MAX_TEXT = 20000
_LOCK = threading.RLock()


class PermissionRequestError(RuntimeError):
    pass


def _atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def _load():
    if not REQUESTS_PATH.exists():
        return []
    try:
        value = json.loads(REQUESTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PermissionRequestError("Permission queue needs repair.") from error
    return value if isinstance(value, list) else []


def _audit(event, record, detail=""):
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({
        "timestamp": int(time.time()),
        "event": event,
        "request_id": record.get("id"),
        "actor": record.get("reviewed_by") or record.get("requested_by"),
        "action": record.get("action"),
        "target": record.get("target", ""),
        "detail": str(detail or "")[:2000],
    }, ensure_ascii=False)
    with open(AUDIT_PATH, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(AUDIT_PATH, 0o600)


def _resolve_target(relative_path):
    raw = str(relative_path or "").strip()
    if not raw or Path(raw).is_absolute():
        raise PermissionRequestError("Use a relative Yoshi project path.")
    target = ROOT.joinpath(raw).resolve()
    try:
        relative = target.relative_to(ROOT)
    except ValueError as error:
        raise PermissionRequestError("Target leaves the Yoshi project.") from error
    if any(part in BLOCKED_DIRS for part in relative.parts):
        raise PermissionRequestError("That directory is not writable by DiYoshi.")
    if target.name in BLOCKED_NAMES or ".before-" in target.name:
        raise PermissionRequestError("That private or backup file is blocked.")
    if target.suffix.lower() not in ALLOWED_SUFFIXES or not target.is_file():
        raise PermissionRequestError("Target must be an approved existing source file.")
    return target, relative


def _resolve_new_target(relative_path):
    raw = str(relative_path or "").strip()
    if not raw or Path(raw).is_absolute():
        raise PermissionRequestError("Use a relative project path.")
    target = ROOT.joinpath(raw).resolve()
    try:
        relative = target.relative_to(ROOT)
    except ValueError as error:
        raise PermissionRequestError("Target leaves the Yoshi project.") from error
    if not relative.parts or relative.parts[0] != "projects":
        raise PermissionRequestError("New Builder files must stay inside projects/.")
    if any(part in BLOCKED_DIRS for part in relative.parts):
        raise PermissionRequestError("That directory is blocked.")
    if target.suffix.lower() not in ALLOWED_SUFFIXES:
        raise PermissionRequestError("That new file type is not approved.")
    if target.exists():
        raise PermissionRequestError("That file already exists; propose an exact edit instead.")
    return target, relative


def create_code_edit(requested_by, summary, target, old_text, new_text, run_tests=True):
    clean_summary = " ".join(str(summary or "").split()).strip()[:500]
    old_value = str(old_text or "")
    new_value = str(new_text or "")
    _resolve_target(target)
    if not clean_summary:
        raise PermissionRequestError("A change summary is required.")
    if not old_value or not new_value:
        raise PermissionRequestError("Exact original and replacement text are required.")
    if len(old_value) > MAX_TEXT or len(new_value) > MAX_TEXT:
        raise PermissionRequestError("Proposed edit is too large.")
    record = {
        "id": uuid.uuid4().hex,
        "created_at": int(time.time()),
        "requested_by": str(requested_by or "DiYoshi")[:80],
        "summary": clean_summary,
        "action": "exact_replace",
        "target": str(target).strip(),
        "old_text": old_value,
        "new_text": new_value,
        "run_tests": bool(run_tests),
        "status": "pending",
    }
    with _LOCK:
        records = _load()
        records.append(record)
        _atomic_json(REQUESTS_PATH, records[-200:])
        _audit("requested", record)
    return dict(record)


def create_file_request(
    requested_by, summary, target, content, run_tests=False
):
    clean_summary = " ".join(str(summary or "").split()).strip()[:500]
    content_value = str(content or "")
    _resolve_new_target(target)
    if not clean_summary:
        raise PermissionRequestError("A file summary is required.")
    if not content_value or len(content_value) > MAX_TEXT:
        raise PermissionRequestError("New file content is empty or too large.")
    record = {
        "id": uuid.uuid4().hex,
        "created_at": int(time.time()),
        "requested_by": str(requested_by or "DiYoshi")[:80],
        "summary": clean_summary,
        "action": "create_file",
        "target": str(target).strip(),
        "old_text": "",
        "new_text": content_value,
        "run_tests": bool(run_tests),
        "status": "pending",
    }
    with _LOCK:
        records = _load()
        records.append(record)
        _atomic_json(REQUESTS_PATH, records[-200:])
        _audit("requested", record)
    return dict(record)


def create_regression_request(requested_by, summary="Run DiYoshi regression tests"):
    record = {
        "id": uuid.uuid4().hex,
        "created_at": int(time.time()),
        "requested_by": str(requested_by or "DiYoshi")[:80],
        "summary": " ".join(str(summary or "").split()).strip()[:500],
        "action": "run_regression",
        "target": "",
        "status": "pending",
    }
    with _LOCK:
        records = _load()
        records.append(record)
        _atomic_json(REQUESTS_PATH, records[-200:])
        _audit("requested", record)
    return dict(record)


def list_requests(limit=100):
    with _LOCK:
        records = _load()
    maximum = max(1, min(int(limit), 200))
    return [dict(item) for item in records[-maximum:]][::-1]


def _run_regression():
    command = [
        str(ROOT / "venv" / "bin" / "python"),
        "-m", "unittest", "discover", "-s", "tests", "-q",
    ]
    if not Path(command[0]).exists():
        command[0] = sys.executable
    result = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True,
        timeout=120, check=False,
    )
    output = (result.stdout + "\n" + result.stderr).strip()[-5000:]
    if result.returncode != 0:
        raise PermissionRequestError("Regression tests failed.\n" + output)
    return output or "Regression tests passed."


def _write_exact(record):
    target, relative = _resolve_target(record.get("target"))
    original = target.read_text(encoding="utf-8")
    old_text = str(record.get("old_text") or "")
    new_text = str(record.get("new_text") or "")
    if original.count(old_text) != 1:
        raise PermissionRequestError("Original text no longer has exactly one match.")
    backup = BACKUP_ROOT / record["id"] / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup)
    os.chmod(backup, 0o600)
    updated = original.replace(old_text, new_text, 1)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=f".{target.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, target.stat().st_mode & 0o777)
        os.replace(temporary, target)
        temporary = None
        if target.suffix.lower() == ".py":
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(target)],
                cwd=ROOT, capture_output=True, text=True,
                timeout=30, check=False,
            )
            if result.returncode:
                raise PermissionRequestError(result.stderr.strip() or "Python compile failed.")
        verification = "Syntax verification passed."
        if record.get("run_tests"):
            verification = _run_regression()
        return str(backup.relative_to(ROOT)), verification
    except Exception:
        shutil.copy2(backup, target)
        raise
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def _write_new(record):
    target, _relative = _resolve_new_target(record.get("target"))
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=f".{target.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(str(record.get("new_text") or ""))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        temporary = None
        if target.suffix.lower() == ".py":
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(target)],
                cwd=ROOT, capture_output=True, text=True,
                timeout=30, check=False,
            )
            if result.returncode:
                target.unlink(missing_ok=True)
                raise PermissionRequestError(result.stderr.strip() or "Python compile failed.")
        verification = "New file created and syntax verification passed."
        if record.get("run_tests"):
            verification = _run_regression()
        return verification
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def review(request_id, reviewer, decision):
    clean_decision = str(decision or "").strip().casefold()
    if clean_decision not in {"approve", "reject"}:
        raise PermissionRequestError("Decision must be approve or reject.")
    with _LOCK:
        records = _load()
        record = next((item for item in records if item.get("id") == request_id), None)
        if not record:
            raise PermissionRequestError("Permission request was not found.")
        if record.get("status") != "pending":
            raise PermissionRequestError("Permission request is no longer pending.")
        record["reviewed_by"] = str(reviewer or "")[:80]
        record["reviewed_at"] = int(time.time())
        if clean_decision == "reject":
            record["status"] = "rejected"
            _atomic_json(REQUESTS_PATH, records)
            _audit("rejected", record)
            return dict(record)
        record["status"] = "running"
        _atomic_json(REQUESTS_PATH, records)
        try:
            if record.get("action") == "exact_replace":
                backup, result = _write_exact(record)
                record["backup"] = backup
            elif record.get("action") == "create_file":
                result = _write_new(record)
                record["created_new"] = True
            elif record.get("action") == "run_regression":
                result = _run_regression()
            else:
                raise PermissionRequestError("Requested action is not allowlisted.")
            record["status"] = "completed"
            record["result"] = str(result)[-5000:]
            _audit("completed", record, result)
        except Exception as error:
            record["status"] = "failed"
            record["result"] = str(error)[:5000]
            _audit("failed", record, error)
        _atomic_json(REQUESTS_PATH, records)
        return dict(record)


def rollback(request_id, reviewer):
    with _LOCK:
        records = _load()
        record = next((item for item in records if item.get("id") == request_id), None)
        if not record or record.get("action") not in {"exact_replace", "create_file"}:
            raise PermissionRequestError("A completed code change is required.")
        if record.get("status") != "completed":
            raise PermissionRequestError("Only a completed code change can be rolled back.")
        if record.get("action") == "create_file":
            target, _relative = _resolve_target(record.get("target"))
            target.unlink()
        else:
            backup_value = str(record.get("backup") or "")
            if not backup_value:
                raise PermissionRequestError("This request has no rollback backup.")
            backup = ROOT.joinpath(backup_value).resolve()
            target, _relative = _resolve_target(record.get("target"))
            if not backup.is_file():
                raise PermissionRequestError("Rollback backup is unavailable.")
            shutil.copy2(backup, target)
        record["status"] = "rolled_back"
        record["reviewed_by"] = str(reviewer or "")[:80]
        record["rolled_back_at"] = int(time.time())
        _atomic_json(REQUESTS_PATH, records)
        _audit("rolled_back", record)
        return dict(record)
