"""Authenticated encryption for saved applicant documents."""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


PREFIX = "hfenc:v1:"


def _cipher(database: Path) -> Fernet:
    configured = os.environ.get("HIREFLOW_DATA_KEY", "").strip()
    if configured:
        key = configured.encode("ascii")
    else:
        key_path = database.with_suffix(".key")
        if not key_path.exists():
            key_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(descriptor, "wb") as output:
                    output.write(Fernet.generate_key())
        key = key_path.read_bytes().strip()
        os.chmod(key_path, 0o600)
    try:
        return Fernet(key)
    except (ValueError, TypeError) as exc:
        raise ValueError("HIREFLOW_DATA_KEY must be a valid Fernet key.") from exc


def seal(value: str, database: Path) -> str:
    if not value:
        return ""
    if value.startswith(PREFIX):
        return value
    return PREFIX + _cipher(database).encrypt(value.encode("utf-8")).decode("ascii")


def unseal(value: str, database: Path) -> str:
    if not value or not value.startswith(PREFIX):
        return value
    try:
        return _cipher(database).decrypt(value[len(PREFIX):].encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise ValueError("Saved documents cannot be opened with the configured data key.") from exc
