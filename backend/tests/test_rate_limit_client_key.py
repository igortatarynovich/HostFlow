"""Rate-limit client key must use real IP behind a trusted proxy hop."""
from __future__ import annotations

from starlette.requests import Request

from backend.app.core import rate_limit as rl


def _request(*, client_host: str, headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": "/api/v1/auth/session/sync",
        "raw_path": b"/api/v1/auth/session/sync",
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": (client_host, 12345),
        "server": ("backend", 8000),
    }
    return Request(scope)


def test_client_key_uses_proxy_peer_when_hops_disabled(monkeypatch) -> None:
    monkeypatch.setattr(rl, "TRUSTED_PROXY_HOPS", 0)
    req = _request(
        client_host="172.18.0.5",
        headers={"x-forwarded-for": "203.0.113.9"},
    )
    assert rl._client_key(req) == "172.18.0.5"


def test_client_key_uses_xff_when_trusted_proxy_hops_set(monkeypatch) -> None:
    monkeypatch.setattr(rl, "TRUSTED_PROXY_HOPS", 1)
    req = _request(
        client_host="172.18.0.5",
        headers={"x-forwarded-for": "203.0.113.9"},
    )
    assert rl._client_key(req) == "203.0.113.9"


def test_client_key_skips_rightmost_trusted_hop(monkeypatch) -> None:
    monkeypatch.setattr(rl, "TRUSTED_PROXY_HOPS", 1)
    req = _request(
        client_host="172.18.0.5",
        headers={"x-forwarded-for": "198.51.100.2, 203.0.113.9"},
    )
    assert rl._client_key(req) == "198.51.100.2"


def test_client_key_falls_back_to_x_real_ip(monkeypatch) -> None:
    monkeypatch.setattr(rl, "TRUSTED_PROXY_HOPS", 1)
    req = _request(
        client_host="172.18.0.5",
        headers={"x-real-ip": "203.0.113.44"},
    )
    assert rl._client_key(req) == "203.0.113.44"
