from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.auth.jwt_tools import decode, encode


def test_decode_rejects_expired_jwt() -> None:
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": "security-test",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }
    token = encode(payload)
    with pytest.raises(HTTPException) as exc:
        decode(token)
    assert exc.value.status_code == 401


def test_decode_accepts_valid_jwt() -> None:
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": "security-test",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = encode(payload)
    out = decode(token)
    assert out["sub"] == "security-test"
