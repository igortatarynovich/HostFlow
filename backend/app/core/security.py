from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt  # PyJWT

try:  # pragma: no cover - optional dependency in minimal test envs
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _HAS_PASSLIB = True
except ImportError:  # pragma: no cover
    import hashlib
    import hmac
    import secrets

    _HAS_PASSLIB = False

    class _SimpleContext:
        def hash(self, password: str) -> str:
            salt = secrets.token_hex(16)
            digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 390000)
            return f"pbkdf2_sha256${salt}${digest.hex()}"

        def verify(self, plain: str, stored: str) -> bool:
            try:
                _, salt, hashed = stored.split("$", 2)
            except ValueError:
                return False
            digest = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), 390000)
            return hmac.compare_digest(digest.hex(), hashed)

    _pwd_context = _SimpleContext()

from backend.app.core.settings import settings

JWT_ALG = "HS256"

def _secret() -> str:
    return settings.jwt_secret or "hostflow-dev-secret"


def create_access_token(
    to_encode: Dict[str, Any], expires_minutes: Optional[int] = None
) -> str:
    """
    Создаёт JWT, подписанный единым секретом.
    Если expires_minutes не задан — берём из ENV JWT_EXPIRES_MIN (по дефолту 60).
    """
    minutes = (
        expires_minutes
        if expires_minutes is not None
        else int(os.getenv("JWT_EXPIRES_MIN", "60"))
    )

    payload = dict(to_encode)
    now = datetime.now(timezone.utc)
    payload["iat"] = int(now.timestamp())
    payload["exp"] = int((now + timedelta(minutes=minutes)).timestamp())

    return jwt.encode(payload, _secret(), algorithm=JWT_ALG)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, _secret(), algorithms=[JWT_ALG])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет пароль пользователя.

    Возвращает False, если passlib не сможет провалидировать hash.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def hash_password(password: str) -> str:
    """
    Хеширует пароль для сохранения в БД.
    """
    if not password:
        raise ValueError("Password must be non-empty")
    return _pwd_context.hash(password)


# Старое имя для обратной совместимости со скриптами сидов
get_password_hash = hash_password
