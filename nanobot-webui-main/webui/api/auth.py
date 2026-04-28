"""JWT and password authentication utilities."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_DAYS = 7


def _secret_key_path() -> Path:
    from nanobot.config.loader import get_config_path

    return get_config_path().parent / "webui_secret.key"


def _get_secret_key() -> str:
    """Load or generate the JWT signing secret."""
    secret_key_path = _secret_key_path()
    if not secret_key_path.exists():
        secret_key_path.parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_hex(32)
        secret_key_path.write_text(key, encoding="utf-8")
        secret_key_path.chmod(0o600)
    return secret_key_path.read_text(encoding="utf-8").strip()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: str, username: str, role: str) -> str:
    """Create a JWT access token valid for 7 days."""
    expire = datetime.now(timezone.utc) + timedelta(days=_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, _get_secret_key(), algorithms=[_ALGORITHM])
