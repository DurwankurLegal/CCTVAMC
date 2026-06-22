"""Symmetric column-level encryption (Fernet) for sensitive fields such as
vendor bank account details (TAD 8.8). The key comes from settings.ENCRYPTION_KEY;
if unset it is derived deterministically from JWT_SECRET_KEY so dev/test work
without extra configuration (set a dedicated key in production)."""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from typing import Optional

from app.core.config import get_settings


@lru_cache
def _fernet():
    from cryptography.fernet import Fernet
    settings = get_settings()
    key = settings.ENCRYPTION_KEY
    if not key:
        # Derive a valid 32-byte urlsafe-base64 key from the JWT secret.
        digest = hashlib.sha256(settings.JWT_SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: Optional[str]) -> Optional[str]:
    if not plaintext:
        return plaintext
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: Optional[str]) -> Optional[str]:
    if not ciphertext:
        return ciphertext
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except Exception:
        # Not encrypted (legacy/plaintext) — return as-is.
        return ciphertext
