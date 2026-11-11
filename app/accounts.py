"""Persistent accounts and encrypted applicant records for both interfaces."""

from __future__ import annotations

import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Sequence

from app.auth import SUPPORTED_MODES, hash_password, verify_password
from app import secure_store


ROOT = Path(__file__).resolve().parents[1]
EMAIL_RE = re.compile(r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$", re.I)


def database_path() -> Path:
    configured = os.environ.get("HIREFLOW_DB_PATH", "").strip()
    if not configured:
        return ROOT / "data" / "hireflow.sqlite3"
    path = Path(configured).expanduser()
    return path if path.is_absolute() else ROOT / path


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=20)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA secure_delete = ON")
        for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
            if candidate.exists():
                try:
                    os.chmod(candidate, 0o600)
                except OSError:
                    pass
        with connection:
            yield connection
    finally:
        connection.close()


def init_db() -> None:
    with _connect() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                email TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                modes TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS applicant_projects (
                id TEXT PRIMARY KEY,
                owner_email TEXT NOT NULL REFERENCES accounts(email),
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                job_text TEXT NOT NULL,
                resume_text TEXT NOT NULL,
                cover_letter TEXT NOT NULL,
                notes TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS applicant_projects_owner ON applicant_projects(owner_email, updated_at DESC)")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS resume_versions (
                id TEXT PRIMARY KEY,
                owner_email TEXT NOT NULL REFERENCES accounts(email),
                name TEXT NOT NULL,
                target_role TEXT NOT NULL,
                template TEXT NOT NULL,
                resume_text TEXT NOT NULL,
                source_id TEXT,
                created_at TEXT NOT NULL
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS resume_versions_owner ON resume_versions(owner_email, created_at DESC)")
        connection.execute("CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        migrated = connection.execute("SELECT value FROM app_meta WHERE key='encrypted_storage'").fetchone()
        if migrated is None:
            for row in connection.execute("SELECT id, company, role, job_text, resume_text, cover_letter, notes FROM applicant_projects").fetchall():
                values = [secure_store.seal(row[key], database_path()) for key in ("company", "role", "job_text", "resume_text", "cover_letter", "notes")]
                connection.execute("UPDATE applicant_projects SET company=?, role=?, job_text=?, resume_text=?, cover_letter=?, notes=? WHERE id=?", (*values, row["id"]))
            for row in connection.execute("SELECT id, name, target_role, resume_text FROM resume_versions").fetchall():
                values = [secure_store.seal(row[key], database_path()) for key in ("name", "target_role", "resume_text")]
                connection.execute("UPDATE resume_versions SET name=?, target_role=?, resume_text=? WHERE id=?", (*values, row["id"]))
            connection.execute("INSERT INTO app_meta(key, value) VALUES ('encrypted_storage', '1')")
        retention = retention_days()
        if retention:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=retention)).isoformat(timespec="seconds")
            connection.execute("DELETE FROM applicant_projects WHERE updated_at < ?", (cutoff,))
            connection.execute("DELETE FROM resume_versions WHERE created_at < ?", (cutoff,))


def retention_days() -> int:
    configured = os.environ.get("HIREFLOW_DATA_RETENTION_DAYS", "0").strip()
    try:
        days = int(configured)
    except ValueError as exc:
        raise ValueError("HIREFLOW_DATA_RETENTION_DAYS must be a non-negative integer.") from exc
    if days < 0:
        raise ValueError("HIREFLOW_DATA_RETENTION_DAYS must be a non-negative integer.")
    return days


def valid_email(email: str) -> bool:
    return len(email) <= 254 and bool(EMAIL_RE.fullmatch(email.strip()))


def create_account(email: str, display_name: str, password: str, modes: Sequence[str] = SUPPORTED_MODES) -> Dict[str, Any]:
    normalized = email.strip().lower()
    if not valid_email(normalized):
        raise ValueError("Enter a valid email address.")
    name = display_name.strip()
    if not name or len(name) > 100:
        raise ValueError("Enter a name of up to 100 characters.")
    allowed = tuple(mode for mode in SUPPORTED_MODES if mode in modes)
    if not allowed:
        raise ValueError("Choose at least one workspace.")
    encoded = hash_password(password)
    init_db()
    try:
        with _connect() as connection:
            connection.execute(
                "INSERT INTO accounts(email, display_name, password_hash, modes, created_at) VALUES (?, ?, ?, ?, ?)",
                (normalized, name, encoded, ",".join(allowed), datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("An account with this email already exists. Sign in instead.") from exc
    return {"username": normalized, "display_name": name, "password_hash": encoded, "modes": allowed}


def get_account(email: str) -> Optional[Dict[str, Any]]:
    init_db()
    with _connect() as connection:
        row = connection.execute(
            "SELECT email, display_name, password_hash, modes FROM accounts WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    if row is None:
        return None
    return {
        "username": row["email"],
        "display_name": row["display_name"],
        "password_hash": row["password_hash"],
        "modes": tuple(mode for mode in row["modes"].split(",") if mode in SUPPORTED_MODES),
    }


def update_display_name(email: str, display_name: str) -> Dict[str, Any]:
    """Edit the signed-in account's public name without changing its permissions."""
    name = display_name.strip()
    if not name or len(name) > 100:
        raise ValueError("Enter a name of up to 100 characters.")
    with _connect() as connection:
        cursor = connection.execute("UPDATE accounts SET display_name=? WHERE email=?", (name, email.strip().lower()))
        if cursor.rowcount != 1:
            raise ValueError("This account is no longer available.")
    return get_account(email)


PROJECT_STATUSES = ("Interested", "Preparing", "Applied", "Interviewing", "Offer", "Closed")


def save_project(owner_email: str, company: str, role: str, status: str, job_text: str = "", resume_text: str = "", cover_letter: str = "", notes: str = "", project_id: str | None = None) -> str:
    """Create or update an applicant project only for its signed-in owner."""
    owner = owner_email.strip().lower()
    account = get_account(owner)
    if not account or "applicant" not in account["modes"]:
        raise ValueError("Applicant access is required.")
    if status not in PROJECT_STATUSES:
        raise ValueError("Choose a valid application status.")
    company, role, notes = company.strip(), role.strip(), notes.strip()
    if not company or not role or len(company) > 120 or len(role) > 120:
        raise ValueError("Enter a company and role of up to 120 characters each.")
    if any(len(value) > 120_000 for value in (job_text, resume_text, cover_letter)) or len(notes) > 8_000:
        raise ValueError("This project is too large to save.")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    identity = project_id or str(uuid.uuid4())
    with _connect() as connection:
        if project_id:
            cursor = connection.execute(
                """UPDATE applicant_projects SET company=?, role=?, status=?, job_text=?, resume_text=?, cover_letter=?, notes=?, updated_at=?
                WHERE id=? AND owner_email=?""",
                (secure_store.seal(company, database_path()), secure_store.seal(role, database_path()), status, secure_store.seal(job_text, database_path()), secure_store.seal(resume_text, database_path()), secure_store.seal(cover_letter, database_path()), secure_store.seal(notes, database_path()), now, identity, owner),
            )
            if cursor.rowcount != 1:
                raise ValueError("This application is not available to your account.")
        else:
            connection.execute(
                """INSERT INTO applicant_projects(id, owner_email, company, role, status, job_text, resume_text, cover_letter, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (identity, owner, secure_store.seal(company, database_path()), secure_store.seal(role, database_path()), status, secure_store.seal(job_text, database_path()), secure_store.seal(resume_text, database_path()), secure_store.seal(cover_letter, database_path()), secure_store.seal(notes, database_path()), now, now),
            )
    return identity


def list_projects(owner_email: str) -> list[Dict[str, Any]]:
    account = get_account(owner_email)
    if not account or "applicant" not in account["modes"]:
        raise ValueError("Applicant access is required.")
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            "SELECT id, company, role, status, job_text, resume_text, cover_letter, notes, created_at, updated_at FROM applicant_projects WHERE owner_email=? ORDER BY updated_at DESC",
            (owner_email.strip().lower(),),
        ).fetchall()
    return [{**dict(row), **{key: secure_store.unseal(row[key], database_path()) for key in ("company", "role", "job_text", "resume_text", "cover_letter", "notes")}} for row in rows]


def delete_project(owner_email: str, project_id: str) -> bool:
    account = get_account(owner_email)
    if not account or "applicant" not in account["modes"]:
        raise ValueError("Applicant access is required.")
    init_db()
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM applicant_projects WHERE id=? AND owner_email=?", (project_id, owner_email.strip().lower()))
    return cursor.rowcount == 1


def save_resume_version(owner_email: str, name: str, resume_text: str, target_role: str = "", template: str = "Contemporary", source_id: str | None = None) -> str:
    owner = owner_email.strip().lower()
    account = get_account(owner)
    if not account or "applicant" not in account["modes"]:
        raise ValueError("Applicant access is required.")
    name, target_role = name.strip(), target_role.strip()
    if not name or len(name) > 120 or len(target_role) > 120:
        raise ValueError("Name this resume with up to 120 characters.")
    if template not in ("Contemporary", "Classic"):
        raise ValueError("Choose a valid resume template.")
    if len(resume_text.split()) < 8 or len(resume_text) > 120_000:
        raise ValueError("Add a resume with at least eight words before saving.")
    if source_id and not any(version["id"] == source_id for version in list_resume_versions(owner)):
        raise ValueError("The source resume is not available to your account.")
    identity = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as connection:
        connection.execute("INSERT INTO resume_versions(id, owner_email, name, target_role, template, resume_text, source_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (identity, owner, secure_store.seal(name, database_path()), secure_store.seal(target_role, database_path()), template, secure_store.seal(resume_text, database_path()), source_id, now))
    return identity


def list_resume_versions(owner_email: str) -> list[Dict[str, Any]]:
    account = get_account(owner_email)
    if not account or "applicant" not in account["modes"]:
        raise ValueError("Applicant access is required.")
    with _connect() as connection:
        rows = connection.execute("SELECT id, name, target_role, template, resume_text, source_id, created_at FROM resume_versions WHERE owner_email=? ORDER BY created_at DESC, rowid DESC", (owner_email.strip().lower(),)).fetchall()
    return [{**dict(row), **{key: secure_store.unseal(row[key], database_path()) for key in ("name", "target_role", "resume_text")}} for row in rows]


def delete_resume_version(owner_email: str, version_id: str) -> bool:
    account = get_account(owner_email)
    if not account or "applicant" not in account["modes"]:
        raise ValueError("Applicant access is required.")
    with _connect() as connection:
        connection.execute("UPDATE resume_versions SET source_id=NULL WHERE source_id=? AND owner_email=?", (version_id, owner_email.strip().lower()))
        cursor = connection.execute("DELETE FROM resume_versions WHERE id=? AND owner_email=?", (version_id, owner_email.strip().lower()))
    return cursor.rowcount == 1


def export_account_data(email: str) -> Dict[str, Any]:
    account = get_account(email)
    if not account:
        raise ValueError("This account is no longer available.")
    with _connect() as connection:
        row = connection.execute("SELECT created_at FROM accounts WHERE email=?", (account["username"],)).fetchone()
    return {
        "email": account["username"], "display_name": account["display_name"],
        "modes": list(account["modes"]), "created_at": row["created_at"],
        "retention_days": retention_days(),
        "resume_versions": list_resume_versions(email) if "applicant" in account["modes"] else [],
        "applications": list_projects(email) if "applicant" in account["modes"] else [],
    }


def delete_account(email: str, password: str) -> None:
    account = get_account(email)
    if not account or not verify_password(password, account["password_hash"]):
        raise ValueError("Password was not recognized.")
    owner = account["username"]
    with _connect() as connection:
        connection.execute("DELETE FROM applicant_projects WHERE owner_email=?", (owner,))
        connection.execute("DELETE FROM resume_versions WHERE owner_email=?", (owner,))
        if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='web_sessions'").fetchone():
            connection.execute("DELETE FROM web_sessions WHERE email=?", (owner,))
        connection.execute("DELETE FROM accounts WHERE email=?", (owner,))
