from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from backend.app.core.settings import settings


_FERNET_CACHE: Optional[Fernet] = None


def _derive_key(source: str) -> Fernet:
    """
    Derive a 32-byte Fernet key from arbitrary secret text.

    We hash the provided string (or fallback) with SHA-256, then
    use urlsafe_b64encode to build a valid Fernet key.
    """
    global _FERNET_CACHE

    if _FERNET_CACHE is not None:
        return _FERNET_CACHE

    raw = (source or "").strip()
    if not raw:
        raw = settings.jwt_secret or "hostflow-dev-secret"

    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    _FERNET_CACHE = Fernet(key)
    return _FERNET_CACHE


def _get_cipher() -> Fernet:
    key_source = settings.meta_credentials_key or settings.jwt_secret or "hostflow-dev-secret"
    return _derive_key(key_source)


def encrypt_secret(value: Optional[str]) -> Optional[str]:
    """Encrypt sensitive values for storage (returns urlsafe base64 string)."""
    if value is None:
        return None
    text = str(value)
    if not text:
        return None
    cipher = _get_cipher()
    token = cipher.encrypt(text.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(token: Optional[str]) -> Optional[str]:
    """Decrypt previously encrypted values; returns None on failure or empty input."""
    if token is None:
        return None
    token_str = token.strip()
    if not token_str:
        return None
    cipher = _get_cipher()
    try:
        decrypted = cipher.decrypt(token_str.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        return None


def generate_secret(length: int = 40) -> str:
    """Generate a random url-safe secret for webhook signing."""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
