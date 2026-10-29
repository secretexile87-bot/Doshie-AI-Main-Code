#!/usr/bin/env python3
"""
doshie_clients.py - Doshie Freelance Tech Business — Client & Job Management

Provides a complete SQLite-backed business layer for Hermes's freelance
computer repair business:
  - Client records (name, contact, devices, location)
  - Consent/authorization tracking (legal protection)
  - Job tickets (open, update, close, time tracking)
  - Invoice generation (plain text + HTML)
  - Revenue reports
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "data" / "doshie_business.db"

BUSINESS_NAME = "Hermes Tech Solutions"
BUSINESS_PHONE = "(915) 329-6410"
BUSINESS_LOCATION = "El Paso, TX"
DEFAULT_HOURLY_RATE = 60.0   # USD per hour
DEFAULT_FLAT_FEE = 0.0       # Optional flat fee per job

# Service Catalog presets
SERVICE_CATALOG = {
    "tuneup": {"title": "PC Tune-up & Speed Optimization", "fee": 50.0, "desc": "Clean temp files, optimize startup apps, disk health scan, OS updates, and registry cleanup."},
    "malware": {"title": "Virus & Malware Removal", "fee": 65.0, "desc": "Deep security scan, malware and adware purging, browser hijack removal, and security hardening."},
    "diagnostic": {"title": "Complete System Diagnostic & Health Audit", "fee": 35.0, "desc": "Hardware stress test, SMART disk check, CPU/RAM thermal inspection, and bottleneck report."},
    "os_reinstall": {"title": "Clean OS Reinstallation & Driver Setup", "fee": 85.0, "desc": "Fresh Windows installation, manufacturer drivers, core utility suite, and data restore."},
    "hardware": {"title": "Hardware Upgrade & Thermal Repaste", "fee": 75.0, "desc": "Component installation (RAM, SSD, GPU, PSU), dust cleaning, and fresh thermal compound."},
}


# ---------------------------------------------------------------------------
# Database bootstrap
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db():
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clients (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                phone       TEXT,
                email       TEXT,
                address     TEXT,
                notes       TEXT,
                consent     INTEGER DEFAULT 0,
                consent_date TEXT,
                consent_method TEXT,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS devices (
                id          TEXT PRIMARY KEY,
                client_id   TEXT NOT NULL REFERENCES clients(id),
                label       TEXT NOT NULL,
                os          TEXT,
                hostname    TEXT,
                tailscale_ip TEXT,
                node_installed INTEGER DEFAULT 0,
                notes       TEXT,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id          TEXT PRIMARY KEY,
                client_id   TEXT NOT NULL REFERENCES clients(id),
                device_id   TEXT REFERENCES devices(id),
                title       TEXT NOT NULL,
                description TEXT,
                status      TEXT DEFAULT 'open',
                hours       REAL DEFAULT 0,
                flat_fee    REAL DEFAULT 0,
                hourly_rate REAL DEFAULT 60,
                parts_cost  REAL DEFAULT 0,
                total       REAL DEFAULT 0,
                paid        INTEGER DEFAULT 0,
                paid_date   TEXT,
                notes       TEXT,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                closed_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS job_log (
                id          TEXT PRIMARY KEY,
                job_id      TEXT NOT NULL REFERENCES jobs(id),
                entry       TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id          TEXT PRIMARY KEY,
                job_id      TEXT NOT NULL REFERENCES jobs(id),
                client_id   TEXT NOT NULL REFERENCES clients(id),
                amount      REAL NOT NULL,
                paid        INTEGER DEFAULT 0,
                paid_date   TEXT,
                html        TEXT,
                created_at  TEXT NOT NULL
            );
        """)


_init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str = "") -> str:
    return (prefix + uuid.uuid4().hex[:10]).strip()


def _calc_total(hours: float, rate: float, flat_fee: float, parts: float) -> float:
    labor = round(hours * rate, 2) if hours > 0 else 0.0
    return round(labor + flat_fee + parts, 2)


# ---------------------------------------------------------------------------
# Client Management
# ---------------------------------------------------------------------------

def add_client(
    name: str,
    phone: str = "",
    email: str = "",
    address: str = "",
    notes: str = "",
    consent: bool = False,
    consent_method: str = "verbal",
) -> Dict[str, Any]:
    """Add a new client to the business database."""
    name = str(name or "").strip()
    if not name:
        return {"ok": False, "error": "Client name is required."}
    client_id = _new_id("cli_")
    now = _now()
    consent_date = now if consent else None
    with _connect() as conn:
        conn.execute(
            """INSERT INTO clients
               (id, name, phone, email, address, notes, consent, consent_date, consent_method, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (client_id, name, phone, email, address, notes,
             1 if consent else 0, consent_date, consent_method if consent else None, now, now),
        )
    return {
        "ok": True,
        "client_id": client_id,
        "name": name,
        "consent": consent,
        "message": f"Client '{name}' added successfully.",
    }


def get_client(client_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a client record by ID."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    if not row:
        return None
    return dict(row)


def search_clients(query: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    """Search clients by name, phone, or email."""
    q = str(query or "").strip()
    with _connect() as conn:
        if q:
            rows = conn.execute(
                "SELECT * FROM clients WHERE name LIKE ? OR phone LIKE ? OR email LIKE ? ORDER BY name LIMIT ?",
                (f"%{q}%", f"%{q}%", f"%{q}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM clients ORDER BY name LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


def update_client_consent(client_id: str, consent_method: str = "verbal") -> Dict[str, Any]:
    """Mark a client as having given consent/authorization."""
    with _connect() as conn:
        now = _now()
        conn.execute(
            "UPDATE clients SET consent=1, consent_date=?, consent_method=?, updated_at=? WHERE id=?",
            (now, consent_method, now, client_id),
        )
    return {"ok": True, "client_id": client_id, "consent_recorded": now}


def check_client_consent(client_id: str) -> Dict[str, Any]:
    """Check if a client has authorized remote access — call before connecting."""
    client = get_client(client_id)
    if not client:
        return {"ok": False, "authorized": False, "error": "Client not found."}
    return {
        "ok": True,
        "client_id": client_id,
        "name": client["name"],
        "authorized": bool(client["consent"]),
        "consent_date": client.get("consent_date"),
        "consent_method": client.get("consent_method"),
        "warning": None if client["consent"] else "⚠️ No consent on file. Get authorization before connecting to this client's PC.",
    }


def add_device(
    client_id: str,
    label: str,
    os: str = "windows",
    hostname: str = "",
    tailscale_ip: str = "",
    node_installed: bool = False,
    notes: str = "",
) -> Dict[str, Any]:
    """Add a device/computer to a client's record."""
    if not get_client(client_id):
        return {"ok": False, "error": f"Client {client_id} not found."}
    device_id = _new_id("dev_")
    with _connect() as conn:
        conn.execute(
            """INSERT INTO devices
               (id, client_id, label, os, hostname, tailscale_ip, node_installed, notes, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (device_id, client_id, label, os, hostname, tailscale_ip,
             1 if node_installed else 0, notes, _now()),
        )
    return {"ok": True, "device_id": device_id, "label": label, "client_id": client_id}


def get_client_devices(client_id: str) -> List[Dict[str, Any]]:
    """Get all devices registered under a client."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM devices WHERE client_id=? ORDER BY label", (client_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Job Management
# ---------------------------------------------------------------------------

def open_job(
    client_id: str,
    title: str,
    description: str = "",
    device_id: str = "",
    hourly_rate: float = DEFAULT_HOURLY_RATE,
    flat_fee: float = DEFAULT_FLAT_FEE,
) -> Dict[str, Any]:
    """Open a new job/service ticket for a client."""
    if not get_client(client_id):
        return {"ok": False, "error": f"Client {client_id} not found."}
    title = str(title or "").strip()
    if not title:
        return {"ok": False, "error": "Job title is required."}
    job_id = _new_id("job_")
    now = _now()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO jobs
               (id, client_id, device_id, title, description, status, hours, flat_fee, hourly_rate, parts_cost, total, paid, created_at, updated_at)
               VALUES (?,?,?,?,?,'open',0,?,?,0,0,0,?,?)""",
            (job_id, client_id, device_id or None, title, description,
             flat_fee, hourly_rate, now, now),
        )
    return {
        "ok": True,
        "job_id": job_id,
        "title": title,
        "client_id": client_id,
        "status": "open",
        "message": f"Job '{title}' opened.",
    }


def log_job_action(job_id: str, entry: str) -> Dict[str, Any]:
    """Add a log entry to a job (records what was done)."""
    entry = str(entry or "").strip()
    if not entry:
        return {"ok": False, "error": "Log entry cannot be empty."}
    with _connect() as conn:
        conn.execute(
            "INSERT INTO job_log (id, job_id, entry, created_at) VALUES (?,?,?,?)",
            (_new_id("log_"), job_id, entry, _now()),
        )
        conn.execute("UPDATE jobs SET updated_at=? WHERE id=?", (_now(), job_id))
    return {"ok": True, "job_id": job_id, "logged": entry}


def update_job(
    job_id: str,
    hours: Optional[float] = None,
    parts_cost: Optional[float] = None,
    notes: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Update job hours, parts cost, notes, or status."""
    with _connect() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job:
            return {"ok": False, "error": f"Job {job_id} not found."}
        job = dict(job)
        new_hours = float(hours) if hours is not None else job["hours"]
        new_parts = float(parts_cost) if parts_cost is not None else job["parts_cost"]
        new_notes = str(notes) if notes is not None else job["notes"]
        new_status = str(status) if status in ("open", "in_progress", "closed") else job["status"]
        new_total = _calc_total(new_hours, job["hourly_rate"], job["flat_fee"], new_parts)
        now = _now()
        closed_at = now if new_status == "closed" and job["status"] != "closed" else job.get("closed_at")
        conn.execute(
            """UPDATE jobs SET hours=?, parts_cost=?, notes=?, status=?, total=?, updated_at=?, closed_at=?
               WHERE id=?""",
            (new_hours, new_parts, new_notes, new_status, new_total, now, closed_at, job_id),
        )
    return {"ok": True, "job_id": job_id, "total": new_total, "status": new_status}


def close_job(
    job_id: str,
    hours: float = 0,
    parts_cost: float = 0,
    notes: str = "",
) -> Dict[str, Any]:
    """Close a job and calculate the final total."""
    result = update_job(job_id, hours=hours, parts_cost=parts_cost, notes=notes, status="closed")
    if result.get("ok"):
        result["message"] = f"Job closed. Total: ${result['total']:.2f}"
    return result


def mark_job_paid(job_id: str) -> Dict[str, Any]:
    """Mark a job as paid."""
    now = _now()
    with _connect() as conn:
        conn.execute(
            "UPDATE jobs SET paid=1, paid_date=?, updated_at=? WHERE id=?",
            (now, now, job_id),
        )
    return {"ok": True, "job_id": job_id, "paid_date": now}


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a job record including its log entries."""
    with _connect() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job:
            return None
        logs = conn.execute(
            "SELECT entry, created_at FROM job_log WHERE job_id=? ORDER BY created_at", (job_id,)
        ).fetchall()
    result = dict(job)
    result["log"] = [dict(l) for l in logs]
    return result


def list_jobs(client_id: str = "", status: str = "", limit: int = 30) -> List[Dict[str, Any]]:
    """List jobs, optionally filtered by client or status."""
    with _connect() as conn:
        clauses, params = [], []
        if client_id:
            clauses.append("j.client_id=?")
            params.append(client_id)
        if status:
            clauses.append("j.status=?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"""SELECT j.*, c.name as client_name
                FROM jobs j JOIN clients c ON j.client_id=c.id
                {where} ORDER BY j.created_at DESC LIMIT ?""",
            params + [limit],
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Invoice Generation
# ---------------------------------------------------------------------------

def generate_invoice(job_id: str) -> Dict[str, Any]:
    """Generate an invoice for a closed job."""
    job = get_job(job_id)
    if not job:
        return {"ok": False, "error": f"Job {job_id} not found."}
    client = get_client(job["client_id"])
    if not client:
        return {"ok": False, "error": "Client not found."}

    inv_id = _new_id("inv_")
    now = _now()
    date_str = datetime.now().strftime("%B %d, %Y")
    amount = job["total"]

    labor = round(job["hours"] * job["hourly_rate"], 2)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Invoice {inv_id} - {BUSINESS_NAME}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 750px; margin: 30px auto; padding: 25px; color: #1f2937; background: #fafafa; }}
  .invoice-card {{ background: #ffffff; border-radius: 12px; padding: 35px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #e5e7eb; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #3b82f6; padding-bottom: 20px; }}
  .brand {{ font-size: 26px; font-weight: 800; color: #1e3a8a; letter-spacing: -0.5px; }}
  .brand-sub {{ color: #6b7280; font-size: 13px; margin-top: 4px; }}
  .invoice-meta {{ text-align: right; }}
  .invoice-tag {{ background: #eff6ff; color: #1d4ed8; font-weight: 700; padding: 4px 12px; border-radius: 6px; font-size: 12px; display: inline-block; margin-bottom: 6px; }}
  .two-col {{ display: flex; justify-content: space-between; margin-top: 25px; font-size: 14px; line-height: 1.6; }}
  .section-title {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; font-weight: 700; margin-bottom: 6px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 30px; font-size: 14px; }}
  th {{ background: #f8fafc; color: #475569; font-weight: 600; text-align: left; padding: 12px 14px; border-bottom: 1px solid #e2e8f0; }}
  td {{ padding: 14px; border-bottom: 1px solid #f1f5f9; }}
  .text-right {{ text-align: right; }}
  .total-row td {{ font-size: 18px; font-weight: 800; color: #1e3a8a; border-top: 2px solid #e2e8f0; border-bottom: none; }}
  .status-badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; margin-top: 20px; }}
  .status-paid {{ background: #dcfce7; color: #15803d; }}
  .status-due {{ background: #fee2e2; color: #b91c1c; }}
  .payment-box {{ margin-top: 30px; padding: 16px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 13px; }}
  .footer {{ margin-top: 30px; text-align: center; color: #9ca3af; font-size: 12px; border-top: 1px solid #f1f5f9; padding-top: 16px; }}
</style>
</head>
<body>
<div class="invoice-card">
  <div class="header">
    <div>
      <div class="brand">⚡ {BUSINESS_NAME}</div>
      <div class="brand-sub">Computer Diagnostics, Tune-ups & IT Support • {BUSINESS_LOCATION}</div>
      <div class="brand-sub">📞 {BUSINESS_PHONE}</div>
    </div>
    <div class="invoice-meta">
      <div class="invoice-tag">INVOICE</div>
      <div><strong>#{inv_id}</strong></div>
      <div style="color: #6b7280; font-size: 13px;">Date: {date_str}</div>
    </div>
  </div>

  <div class="two-col">
    <div>
      <div class="section-title">Client Information</div>
      <div style="font-weight: 700; font-size: 16px;">{client['name']}</div>
      <div>{client.get('phone','') or ''}</div>
      <div>{client.get('email','') or ''}</div>
      <div>{client.get('address','') or ''}</div>
    </div>
    <div style="text-align: right;">
      <div class="section-title">Service Performed</div>
      <div style="font-weight: 700; font-size: 15px;">{job['title']}</div>
      <div style="color: #6b7280; max-width: 280px; margin-left: auto;">{job.get('description','') or ''}</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Service Item</th>
        <th>Description / Units</th>
        <th class="text-right">Amount</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Labor & Diagnostics</strong></td>
        <td>{job['hours']:.1f} hrs @ ${job['hourly_rate']:.2f}/hr</td>
        <td class="text-right">${labor:.2f}</td>
      </tr>
      {'<tr><td><strong>Flat Service Rate</strong></td><td>Service standard</td><td class="text-right">$' + f"{job['flat_fee']:.2f}" + '</td></tr>' if job['flat_fee'] > 0 else ''}
      {'<tr><td><strong>Parts / Replacement</strong></td><td>Materials</td><td class="text-right">$' + f"{job['parts_cost']:.2f}" + '</td></tr>' if job['parts_cost'] > 0 else ''}
      <tr class="total-row">
        <td colspan="2">TOTAL</td>
        <td class="text-right">${amount:.2f}</td>
      </tr>
    </tbody>
  </table>

  <div>
    {'<div class="status-badge status-paid">✅ PAID IN FULL — ' + (job.get("paid_date","") or "") + '</div>' if job['paid'] else '<div class="status-badge status-due">⚠️ BALANCE DUE: $' + f"{amount:.2f}" + '</div>'}
  </div>

  <div class="payment-box">
    <strong>Payment Methods:</strong><br>
    • <strong>Zelle:</strong> {BUSINESS_PHONE}<br>
    • <strong>CashApp / Venmo / Cash:</strong> Accepted upon delivery.<br>
    <div style="margin-top: 6px; color: #6b7280; font-size: 12px;">Authorized by client on {client.get('consent_date','N/A')} via {client.get('consent_method','verbal')} agreement.</div>
  </div>

  <div class="footer">
    Thank you for choosing {BUSINESS_NAME}! We appreciate your business.
  </div>
</div>
</body>
</html>"""

    with _connect() as conn:
        conn.execute(
            "INSERT INTO invoices (id, job_id, client_id, amount, paid, html, created_at) VALUES (?,?,?,?,?,?,?)",
            (inv_id, job_id, job["client_id"], amount, job["paid"], html, now),
        )

    # Save HTML file
    invoice_dir = Path(__file__).resolve().parent / "data" / "invoices"
    invoice_dir.mkdir(parents=True, exist_ok=True)
    invoice_path = invoice_dir / f"{inv_id}.html"
    invoice_path.write_text(html, encoding="utf-8")

    return {
        "ok": True,
        "invoice_id": inv_id,
        "client": client["name"],
        "job": job["title"],
        "amount": amount,
        "paid": bool(job["paid"]),
        "invoice_path": str(invoice_path),
        "message": f"Invoice generated: ${amount:.2f} for {client['name']}. Saved to {invoice_path}",
    }


# ---------------------------------------------------------------------------
# Revenue Reports
# ---------------------------------------------------------------------------

def revenue_report(period: str = "month") -> Dict[str, Any]:
    """
    Generate a revenue summary.
    period: 'week', 'month', 'year', or 'all'
    """
    now_dt = datetime.now(timezone.utc)
    if period == "week":
        since = now_dt.replace(hour=0, minute=0, second=0) 
        since = since.replace(day=since.day - since.weekday())
        label = "This Week"
    elif period == "month":
        since = now_dt.replace(day=1, hour=0, minute=0, second=0)
        label = now_dt.strftime("%B %Y")
    elif period == "year":
        since = now_dt.replace(month=1, day=1, hour=0, minute=0, second=0)
        label = str(now_dt.year)
    else:
        since = None
        label = "All Time"

    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ") if since else "2000-01-01T00:00:00Z"

    with _connect() as conn:
        rows = conn.execute(
            """SELECT j.*, c.name as client_name FROM jobs j
               JOIN clients c ON j.client_id=c.id
               WHERE j.created_at >= ? AND j.status='closed'
               ORDER BY j.created_at DESC""",
            (since_str,),
        ).fetchall()

    jobs = [dict(r) for r in rows]
    total_revenue = sum(j["total"] for j in jobs)
    total_paid = sum(j["total"] for j in jobs if j["paid"])
    total_unpaid = total_revenue - total_paid
    total_hours = sum(j["hours"] for j in jobs)

    return {
        "ok": True,
        "period": label,
        "total_jobs": len(jobs),
        "total_hours": round(total_hours, 1),
        "total_revenue": round(total_revenue, 2),
        "total_paid": round(total_paid, 2),
        "total_unpaid": round(total_unpaid, 2),
        "jobs": [
            {
                "client": j["client_name"],
                "title": j["title"],
                "total": j["total"],
                "paid": bool(j["paid"]),
                "date": j["created_at"][:10],
            }
            for j in jobs
        ],
    }
