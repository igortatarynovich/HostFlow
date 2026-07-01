from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models import ActivityLog


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def test_post_analytics_event_ttv_step_roundtrip(monkeypatch):
    """
    Базовая проверка: /analytics/events принимает ttv_step и пишет ActivityLog
    без падения валидации.
    """

    # Подменяем get_db_with_tenant, get_current_user через dependency_overrides
    from backend.app.api.v1.analytics import get_db_with_tenant, get_current_user  # type: ignore

    tenant_id = "11111111-1111-1111-1111-111111111111"

    class DummyUser:
        def __init__(self, tenant_id: str, sub: str):
            self.tenant_id = tenant_id
            self.sub = sub

    def override_db_tenant():
        db = SessionLocal()
        try:
            yield db, tenant_id
        finally:
            db.close()

    def override_current_user():
        return DummyUser(tenant_id=tenant_id, sub="22222222-2222-2222-2222-222222222222")

    app.dependency_overrides[get_db_with_tenant] = override_db_tenant
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)

    payload = {
        "event": "ttv_step",
        "action": "completed",
        "step_key": "signup",
    }

    resp = client.post("/api/v1/analytics/events", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is True

    # Убеждаемся, что запись в ActivityLog появилась
    db = SessionLocal()
    try:
        rows = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == "analytics.ttv_step.completed",
            )
            .all()
        )
        assert rows, "ActivityLog for ttv_step.completed must be created"
        assert any((row.payload or {}).get("step_key") == "signup" for row in rows)
    finally:
        db.close()


def test_ttv_report_aggregates_durations(monkeypatch):
    """
    Проверяем, что /analytics/ttv-report агрегирует дельты между signup и шагами.
    """
    from backend.app.api.v1.analytics import get_db_with_tenant, get_current_user  # type: ignore

    tenant_id = "11111111-1111-1111-1111-111111111111"

    class DummyUser:
        def __init__(self, tenant_id: str, sub: str):
            self.tenant_id = tenant_id
            self.sub = sub

    def override_db_tenant():
        db = SessionLocal()
        try:
            yield db, tenant_id
        finally:
            db.close()

    def override_current_user():
        return DummyUser(tenant_id=tenant_id, sub="22222222-2222-2222-2222-222222222222")

    app.dependency_overrides[get_db_with_tenant] = override_db_tenant
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)

    base = _utc(datetime.utcnow() - timedelta(minutes=10))

    # signup
    resp = client.post(
        "/api/v1/analytics/events",
        json={"event": "ttv_step", "action": "completed", "step_key": "signup"},
    )
    assert resp.status_code == 200

    # принудительно поправим created_at для наглядной дельты
    db = SessionLocal()
    try:
        row = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == "analytics.ttv_step.completed",
            )
            .order_by(ActivityLog.created_at.desc())
            .first()
        )
        assert row is not None
        row.created_at = base
        db.commit()
    finally:
        db.close()

    # step: first_client_created через 5 минут
    later = base + timedelta(minutes=5)
    resp2 = client.post(
        "/api/v1/analytics/events",
        json={
            "event": "ttv_step",
            "action": "completed",
            "step_key": "first_client_created",
        },
    )
    assert resp2.status_code == 200

    db = SessionLocal()
    try:
        row2 = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == "analytics.ttv_step.completed",
            )
            .order_by(ActivityLog.created_at.desc())
            .first()
        )
        assert row2 is not None
        row2.created_at = later
        db.commit()
    finally:
        db.close()

    # Запрашиваем отчет
    report_resp = client.get("/api/v1/analytics/ttv-report?days=1")
    assert report_resp.status_code == 200
    data = report_resp.json()
    assert data["actors"] >= 1
    steps = {step["step_key"]: step for step in data.get("steps", [])}
    assert "first_client_created" in steps
    # Дельта около 300 секунд
    assert 250 <= steps["first_client_created"]["p50_seconds"] <= 350

