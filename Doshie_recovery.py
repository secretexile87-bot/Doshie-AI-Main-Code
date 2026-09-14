from pathlib import Path
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import ssl
import tempfile
import threading
import time
from email.message import EmailMessage
from urllib import parse, request

BASE_DIR = Path.home() / "yoshi"
CONTACTS_FILE = BASE_DIR / "profile_recovery.json"
CONFIG_FILE = BASE_DIR / "recovery_delivery.json"
STATE_FILE = BASE_DIR / "recovery_state.json"
CODE_SECONDS = 10 * 60
RESET_SECONDS = 10 * 60
MAX_ATTEMPTS = 5
_LOCK = threading.RLock()
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


class RecoveryError(RuntimeError):
    pass
def _profile_key(profile):
    return " ".join(str(profile or "").split()).strip().casefold()


def _load(path, default):
    if not path.exists():
        return default()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RecoveryError("Recovery data needs repair.") from error
    if not isinstance(value, dict):
        raise RecoveryError("Recovery data needs repair.")
    return value


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(value, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def _default_config():
    return {
        "version": 1,
        "hmac_key": secrets.token_urlsafe(32),
        "smtp": {
            "host": "", "port": 587, "username": "",
            "password": "", "from_address": "", "use_tls": True,
        },
        "twilio": {
            "account_sid": "", "auth_token": "", "from_number": "",
        },
    }


def _config():
    value = _load(CONFIG_FILE, _default_config)
    if not value.get("hmac_key"):
        value["hmac_key"] = secrets.token_urlsafe(32)
        _save(CONFIG_FILE, value)
    return value


def _mask_email(value):
    local, _, domain = str(value or "").partition("@")
    if not local or not domain:
        return ""
    return local[:1] + "***@" + domain
def _mask_phone(value):
    digits = str(value or "")
    return ("*" * max(0, len(digits) - 4)) + digits[-4:] if digits else ""


def delivery_status():
    with _LOCK:
        config = _config()
    smtp = config.get("smtp", {})
    twilio = config.get("twilio", {})
    return {
        "email_ready": bool(
            smtp.get("host") and smtp.get("from_address")
            and smtp.get("username") and smtp.get("password")
        ),
        "sms_ready": bool(
            twilio.get("account_sid") and twilio.get("auth_token")
            and twilio.get("from_number")
        ),
        "smtp_host": smtp.get("host", ""),
        "smtp_port": int(smtp.get("port") or 587),
        "smtp_username": smtp.get("username", ""),
        "smtp_from_address": smtp.get("from_address", ""),
        "smtp_use_tls": bool(smtp.get("use_tls", True)),
        "twilio_account_sid": (
            str(twilio.get("account_sid", ""))[:6] + "…"
            if twilio.get("account_sid") else ""
        ),
        "twilio_from_number": twilio.get("from_number", ""),
    }
def save_delivery_settings(data):
    with _LOCK:
        config = _config()
        smtp = config.setdefault("smtp", {})
        twilio = config.setdefault("twilio", {})
        smtp["host"] = str(data.get("smtp_host", smtp.get("host", ""))).strip()
        try:
            smtp["port"] = int(data.get("smtp_port", smtp.get("port", 587)))
        except (TypeError, ValueError):
            raise ValueError("SMTP port must be a number.")
        smtp["username"] = str(
            data.get("smtp_username", smtp.get("username", ""))
        ).strip()
        smtp["from_address"] = str(
            data.get("smtp_from_address", smtp.get("from_address", ""))
        ).strip()
        smtp["use_tls"] = bool(data.get("smtp_use_tls", True))
        if data.get("smtp_password"):
            smtp["password"] = str(data["smtp_password"])
        if data.get("twilio_account_sid"):
            twilio["account_sid"] = str(data["twilio_account_sid"]).strip()
        if data.get("twilio_auth_token"):
            twilio["auth_token"] = str(data["twilio_auth_token"])
        twilio["from_number"] = str(
            data.get("twilio_from_number", twilio.get("from_number", ""))
        ).strip()
        if smtp.get("from_address") and not EMAIL_PATTERN.fullmatch(
            smtp["from_address"]
        ):
            raise ValueError("Enter a valid sender email address.")
        if twilio.get("from_number") and not PHONE_PATTERN.fullmatch(
            twilio["from_number"]
        ):
            raise ValueError("Twilio sender must use +countrycode format.")
        _save(CONFIG_FILE, config)
    return delivery_status()
def get_profile_contact(profile):
    key = _profile_key(profile)
    with _LOCK:
        contacts = _load(CONTACTS_FILE, lambda: {"version": 1, "profiles": {}})
        item = contacts.get("profiles", {}).get(key, {})
    email = str(item.get("email", ""))
    phone = str(item.get("phone", ""))
    return {
        "profile": " ".join(str(profile or "").split()).strip(),
        "email_masked": _mask_email(email),
        "phone_masked": _mask_phone(phone),
        "has_email": bool(email),
        "has_phone": bool(phone),
    }


def save_profile_contact(profile, email=None, phone=None):
    name = " ".join(str(profile or "").split()).strip()
    with _LOCK:
        contacts = _load(CONTACTS_FILE, lambda: {"version": 1, "profiles": {}})
        existing = contacts.get("profiles", {}).get(_profile_key(name), {})
        email = (
            str(existing.get("email", ""))
            if email is None or str(email).strip() == ""
            else str(email).strip().lower()
        )
        phone = (
            str(existing.get("phone", ""))
            if phone is None or str(phone).strip() == ""
            else re.sub(r"[\s().-]", "", str(phone).strip())
        )
        if email and not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("Enter a valid recovery email.")
        if phone and not PHONE_PATTERN.fullmatch(phone):
            raise ValueError("Phone must use +countrycode format, such as +19155551234.")
        contacts.setdefault("profiles", {})[_profile_key(name)] = {
            "profile": name, "email": email, "phone": phone,
            "updated_at": int(time.time()),
        }
        _save(CONTACTS_FILE, contacts)
    return get_profile_contact(name)
def _raw_contact(profile, method):
    contacts = _load(CONTACTS_FILE, lambda: {"version": 1, "profiles": {}})
    item = contacts.get("profiles", {}).get(_profile_key(profile), {})
    return str(item.get("email" if method == "email" else "phone", ""))


def _digest(config, profile, purpose, value):
    message = f"{_profile_key(profile)}|{purpose}|{value}".encode()
    return hmac.new(
        str(config["hmac_key"]).encode(), message, hashlib.sha256
    ).hexdigest()


def _send_email(config, destination, code):
    smtp = config.get("smtp", {})
    message = EmailMessage()
    message["Subject"] = "Your DiYoshi recovery code"
    message["From"] = smtp["from_address"]
    message["To"] = destination
    message.set_content(
        "Your DiYoshi recovery code is "
        + code + ". It expires in 10 minutes. "
        "If you did not request it, ignore this message."
    )
    host = smtp["host"]
    port = int(smtp.get("port") or 587)
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as server:
            server.login(smtp["username"], smtp["password"])
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            if smtp.get("use_tls", True):
                server.starttls(context=context)
                server.ehlo()
            server.login(smtp["username"], smtp["password"])
            server.send_message(message)


def _send_sms(config, destination, code):
    twilio = config.get("twilio", {})
    account_sid = twilio["account_sid"]
    url = (
        "https://api.twilio.com/2010-04-01/Accounts/"
        + parse.quote(account_sid) + "/Messages.json"
    )
    body = parse.urlencode({
        "To": destination,
        "From": twilio["from_number"],
        "Body": (
            "Your DiYoshi recovery code is " + code
            + ". It expires in 10 minutes."
        ),
    }).encode()
    token = base64.b64encode(
        f"{account_sid}:{twilio['auth_token']}".encode()
    ).decode()
    outgoing = request.Request(
        url, data=body, method="POST",
        headers={
            "Authorization": "Basic " + token,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with request.urlopen(outgoing, timeout=20) as response:
        if response.status not in {200, 201}:
            raise RecoveryError("SMS provider rejected the recovery message.")


def request_code(profile, method):
    method = str(method or "").strip().casefold()
    if method not in {"email", "sms"}:
        raise ValueError("Choose email or SMS recovery.")
    with _LOCK:
        config = _config()
        destination = _raw_contact(profile, method)
        status = delivery_status()
        ready = status["email_ready" if method == "email" else "sms_ready"]
        if not destination or not ready:
            raise RecoveryError("That recovery method is not configured.")
        state = _load(STATE_FILE, lambda: {"version": 1, "requests": {}})
        previous = state.get("requests", {}).get(_profile_key(profile), {})
        if time.time() - float(previous.get("sent_at") or 0) < 60:
            raise RecoveryError("Wait one minute before requesting another code.")
        code = f"{secrets.randbelow(1000000):06d}"
        state.setdefault("requests", {})[_profile_key(profile)] = {
            "profile": profile,
            "method": method,
            "code_hash": _digest(config, profile, "code", code),
            "expires_at": time.time() + CODE_SECONDS,
            "attempts": 0,
            "sent_at": time.time(),
            "reset_hash": "",
            "reset_expires_at": 0,
        }
        _save(STATE_FILE, state)
    try:
        if method == "email":
            _send_email(config, destination, code)
        else:
            _send_sms(config, destination, code)
    except Exception:
        with _LOCK:
            state = _load(STATE_FILE, lambda: {"version": 1, "requests": {}})
            state.get("requests", {}).pop(_profile_key(profile), None)
            _save(STATE_FILE, state)
        raise
    return {
        "method": method,
        "destination": (
            _mask_email(destination) if method == "email"
            else _mask_phone(destination)
        ),
    }
def verify_code(profile, code):
    candidate = str(code or "").strip()
    if not re.fullmatch(r"\d{6}", candidate):
        return None
    with _LOCK:
        config = _config()
        state = _load(STATE_FILE, lambda: {"version": 1, "requests": {}})
        item = state.get("requests", {}).get(_profile_key(profile))
        if not item or float(item.get("expires_at") or 0) <= time.time():
            return None
        if int(item.get("attempts") or 0) >= MAX_ATTEMPTS:
            return None
        item["attempts"] = int(item.get("attempts") or 0) + 1
        expected = _digest(config, profile, "code", candidate)
        if not hmac.compare_digest(str(item.get("code_hash", "")), expected):
            _save(STATE_FILE, state)
            return None
        token = secrets.token_urlsafe(32)
        item["code_hash"] = ""
        item["reset_hash"] = _digest(config, profile, "reset", token)
        item["reset_expires_at"] = time.time() + RESET_SECONDS
        _save(STATE_FILE, state)
        return token


def consume_reset_token(profile, token):
    candidate = str(token or "").strip()
    if not candidate:
        return False
    with _LOCK:
        config = _config()
        state = _load(STATE_FILE, lambda: {"version": 1, "requests": {}})
        item = state.get("requests", {}).get(_profile_key(profile))
        if not item or float(item.get("reset_expires_at") or 0) <= time.time():
            return False
        expected = _digest(config, profile, "reset", candidate)
        if not hmac.compare_digest(str(item.get("reset_hash", "")), expected):
            return False
        state.get("requests", {}).pop(_profile_key(profile), None)
        _save(STATE_FILE, state)
        return True


def state_valid():
    try:
        with _LOCK:
            _config()
            _load(CONTACTS_FILE, lambda: {"version": 1, "profiles": {}})
            _load(STATE_FILE, lambda: {"version": 1, "requests": {}})
        return True
    except RecoveryError:
        return False
