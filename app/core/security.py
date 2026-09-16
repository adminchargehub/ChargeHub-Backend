"""Password hashing and JWT issuing.

The legacy platform stored passwords as plaintext in `userprofile.password
varchar(15)`. That is fixed here at the foundation: bcrypt only, no reversible
storage, and the hash column is sized for it.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

#: bcrypt silently truncates anything past 72 bytes, which would make
#: "longpassword…" and "longpassword…extra" the same credential. We reject
#: instead of truncating; `RegisterRequest` enforces the same bound up front.
MAX_PASSWORD_BYTES = 72


def hash_password(plain: str) -> str:
    encoded = plain.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password exceeds {MAX_PASSWORD_BYTES} bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    encoded = plain.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except ValueError:
        # Malformed/legacy hash in the row — treat as a failed login, never a 500.
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire, "iat": datetime.now(UTC)}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
