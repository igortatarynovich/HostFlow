"""Live compose deploy path: publish into the Caddy bind-mount, not the host decoy."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_LIVE = _REPO / "scripts" / "deploy" / "deploy-live.sh"
_WRAPPER = _REPO / "rebuild-frontend.sh"
_COMPOSE = _REPO / "docker-compose.yml"
_CADDY = _REPO / "Caddyfile"


def test_live_deploy_script_exists_and_avoids_host_www_decoy() -> None:
    text = _LIVE.read_text(encoding="utf-8")
    assert _LIVE.is_file()
    assert "hostflow-frontend/dist" in text
    assert "rsync -a --delete" in text
    assert "HOSTFLOW_REVISION" in text
    assert "force-recreate" in text
    assert "alembic upgrade heads" in text
    # Must not treat the unused host path as the publish target.
    assert "rsync -a --delete hostflow-frontend/dist/ /var/www/hostflow-frontend/" not in text


def test_rebuild_frontend_wrapper_delegates_to_live_deploy() -> None:
    text = _WRAPPER.read_text(encoding="utf-8")
    assert "scripts/deploy/deploy-live.sh" in text
    assert "--frontend-only" in text
    assert "/var/www/hostflow-frontend/" not in text or "not" in text.lower()


def test_live_compose_carries_build_identity_env() -> None:
    text = _COMPOSE.read_text(encoding="utf-8")
    assert "HOSTFLOW_REVISION=${HOSTFLOW_REVISION:-unknown}" in text
    assert "./hostflow-frontend/dist:/var/www/hostflow-frontend:ro" in text
    assert "./backend:/app" in text


def test_live_caddyfile_proxies_build_identity() -> None:
    text = _CADDY.read_text(encoding="utf-8")
    assert "handle /build" in text
    assert "reverse_proxy backend:8000" in text
    assert "root * /var/www/hostflow-frontend" in text
