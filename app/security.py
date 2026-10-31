"""Security helpers: hashing app secrets, and making and checking tokens."""
import hashlib
import os
import time

import jwt

ALGORITHM = "HS256"
TOKEN_LIFETIME_SECONDS = 3600  # one hour


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _signing_key() -> str:
    key = os.getenv("ROSTER_JWT_SECRET")
    if not key:  # no unsafe default: refuse to run without a real key
        raise RuntimeError("ROSTER_JWT_SECRET is not set")
    return key


def create_token(client_id: str, tenant_id: str) -> str:
    now = int(time.time())
    claims = {
        "sub": client_id,        # who this wristband belongs to
        "tenant": tenant_id,     # the one district it opens
        "scope": "roster:read",  # what it allows
        "iat": now,              # issued at
        "exp": now + TOKEN_LIFETIME_SECONDS,  # expires
    }
    return jwt.encode(claims, _signing_key(), algorithm=ALGORITHM)


def read_token(token: str) -> dict:
    """Return the token's claims, or raise jwt.InvalidTokenError if it is fake or expired."""
    return jwt.decode(token, _signing_key(), algorithms=[ALGORITHM])