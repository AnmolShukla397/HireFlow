"""Credential loading and session helpers for the Streamlit application."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from collections import deque
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple


SUPPORTED_MODES = ("recruiter", "applicant")
PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ROUNDS = 600_000
MIN_PASSWORD_ROUNDS = 100_000
MAX_PASSWORD_ROUNDS = 2_000_000
IDLE_TIMEOUT_SECONDS = 30 * 60
ABSOLUTE_TIMEOUT_SECONDS = 8 * 60 * 60
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW_SECONDS = 10 * 60
LOCKOUT_SECONDS = 60

_attempts: Dict[str, deque] = {}
_locked_until: Dict[str, float] = {}


class AuthConfigurationError(ValueError):
    """Raised when configured users cannot be safely loaded."""


def hash_password(password: str, rounds: int = PASSWORD_ROUNDS) -> str:
    """Create a salted PBKDF2-SHA256 password hash for secrets configuration."""
    if not isinstance(password, str) or len(password) < 8 or len(password) > 256:
        raise ValueError("Passwords must contain 8 to 256 characters.")
    if rounds < MIN_PASSWORD_ROUNDS or rounds > MAX_PASSWORD_ROUNDS:
        raise ValueError("The PBKDF2 work factor is outside the supported range.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return "{}${}${}${}".format(
        PASSWORD_SCHEME,
        rounds,
        salt.hex(),
        digest.hex(),
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password hash without exposing timing differences in comparison."""
    try:
        scheme, rounds_text, salt_hex, expected_hex = encoded_hash.split("$", 3)
        rounds = int(rounds_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
        if (
            scheme != PASSWORD_SCHEME
            or rounds < MIN_PASSWORD_ROUNDS
            or rounds > MAX_PASSWORD_ROUNDS
            or len(salt) < 16
            or len(expected) != 32
        ):
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, rounds
        )
        return hmac.compare_digest(actual, expected)
    except (AttributeError, TypeError, ValueError):
        return False


def _to_plain_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    if hasattr(value, "items"):
        try:
            return {str(key): item for key, item in value.items()}
        except Exception:
            return {}
    return {}


def _is_password_hash_valid(encoded_hash: str) -> bool:
    try:
        scheme, rounds_text, salt_hex, digest_hex = encoded_hash.split("$", 3)
        rounds = int(rounds_text)
        salt = bytes.fromhex(salt_hex)
        digest = bytes.fromhex(digest_hex)
        return (
            scheme == PASSWORD_SCHEME
            and MIN_PASSWORD_ROUNDS <= rounds <= MAX_PASSWORD_ROUNDS
            and len(salt) >= 16
            and len(digest) == 32
        )
    except (AttributeError, TypeError, ValueError):
        return False


def normalize_users(raw_users: Any) -> Dict[str, Dict[str, Any]]:
    """Normalize a user map while rejecting unsafe or incomplete entries."""
    users: Dict[str, Dict[str, Any]] = {}
    for raw_identifier, raw_config in _to_plain_mapping(raw_users).items():
        identifier = raw_identifier.strip().lower()
        config = _to_plain_mapping(raw_config)
        password_hash = config.get("password_hash")
        if not identifier or not isinstance(password_hash, str):
            continue
        # Fail closed on malformed hashes rather than letting a bad account
        # turn into a passwordless login.
        if not _is_password_hash_valid(password_hash):
            continue
        configured_modes = config.get("modes", SUPPORTED_MODES)
        if isinstance(configured_modes, str):
            configured_modes = [part.strip() for part in configured_modes.split(",")]
        if not isinstance(configured_modes, Iterable):
            configured_modes = SUPPORTED_MODES
        modes = tuple(
            sorted(
                {
                    str(mode).strip().lower()
                    for mode in configured_modes
                    if str(mode).strip().lower() in SUPPORTED_MODES
                }
            )
        )
        if not modes:
            continue
        users[identifier] = {
            "username": identifier,
            "display_name": str(config.get("display_name") or identifier),
            "password_hash": password_hash,
            "modes": modes,
        }
    return users


def load_users(secret_config: Any = None) -> Dict[str, Dict[str, Any]]:
    """Load account definitions from HIREFLOW_USERS_JSON or Streamlit secrets."""
    env_value = os.environ.get("HIREFLOW_USERS_JSON", "").strip()
    if env_value:
        try:
            raw = json.loads(env_value)
        except json.JSONDecodeError as exc:
            raise AuthConfigurationError(
                "HIREFLOW_USERS_JSON must contain a JSON object of account records."
            ) from exc
        users = normalize_users(raw)
        if not users:
            raise AuthConfigurationError(
                "HIREFLOW_USERS_JSON contains no accounts with valid password hashes."
            )
        return users

    config = _to_plain_mapping(secret_config)
    if not config:
        return {}
    auth_config = _to_plain_mapping(config.get("auth"))
    users = normalize_users(auth_config.get("users"))
    if auth_config.get("users") and not users:
        raise AuthConfigurationError(
            "The [auth.users] entries contain no accounts with valid password hashes."
        )
    return users


def _attempt_key(identifier: str) -> str:
    # Keep the limit account-scoped so opening a fresh browser session does not
    # reset failed attempts. The identifier is hashed because this map lives in
    # process memory for the lifetime of the Streamlit server.
    normalized = identifier.strip().lower().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def authenticate(
    session_id: str,
    identifier: str,
    password: str,
    users: Mapping[str, Mapping[str, Any]],
    now: Optional[float] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
    """Authenticate one account and return (user, seconds_until_retry)."""
    now = time.time() if now is None else now
    normalized_identifier = identifier.strip().lower()
    key = _attempt_key(normalized_identifier)
    locked_until = _locked_until.get(key, 0.0)
    if locked_until > now:
        return None, max(1, int(locked_until - now + 0.999))

    user = users.get(normalized_identifier)
    password_hash = user.get("password_hash") if user else None
    if not password_hash:
        # Keep the missing-account path close to a normal password check.
        hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), b"hireflow-auth-dummy-salt", PASSWORD_ROUNDS
        )
        valid = False
    else:
        valid = verify_password(password, str(password_hash))

    attempts = _attempts.setdefault(key, deque())
    while attempts and now - attempts[0] > ATTEMPT_WINDOW_SECONDS:
        attempts.popleft()
    if valid and user:
        _attempts.pop(key, None)
        _locked_until.pop(key, None)
        return dict(user), None

    attempts.append(now)
    if len(attempts) >= MAX_ATTEMPTS:
        _locked_until[key] = now + LOCKOUT_SECONDS
        attempts.clear()
        return None, LOCKOUT_SECONDS
    return None, None


def start_session(session_state: Any, user: Mapping[str, Any], now: Optional[float] = None) -> None:
    """Replace the current Streamlit session state with a fresh authenticated session."""
    now = time.time() if now is None else now
    session_state.clear()
    session_state["auth_user"] = {
        "username": str(user["username"]),
        "display_name": str(user["display_name"]),
        "modes": tuple(user["modes"]),
    }
    session_state["auth_session_id"] = secrets.token_urlsafe(32)
    session_state["auth_created_at"] = now
    session_state["auth_last_activity"] = now
    session_state["active_mode"] = None
    session_state["active_view"] = None


def session_status(session_state: Any, now: Optional[float] = None) -> Tuple[bool, bool]:
    """Return (authenticated, expired), refreshing the idle clock when valid."""
    now = time.time() if now is None else now
    user = session_state.get("auth_user")
    if not user or not session_state.get("auth_session_id"):
        return False, False
    created = float(session_state.get("auth_created_at", 0))
    last_activity = float(session_state.get("auth_last_activity", 0))
    expired = (
        now - last_activity >= IDLE_TIMEOUT_SECONDS
        or now - created >= ABSOLUTE_TIMEOUT_SECONDS
    )
    if expired:
        session_state.clear()
        session_state["auth_notice"] = "Your session expired. Sign in again to continue."
        return False, True
    session_state["auth_last_activity"] = now
    return True, False


def clear_session(session_state: Any, notice: Optional[str] = None) -> None:
    session_state.clear()
    if notice:
        session_state["auth_notice"] = notice
