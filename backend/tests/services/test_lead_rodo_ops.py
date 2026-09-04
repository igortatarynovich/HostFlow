"""Unit tests for the RODO obligations ops projection (not a second state-machine)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.services.lead_rodo import (
    ComplianceTransitionError,
    mark_lead_rodo_exempt,
)
from backend.app.services.lead_rodo_bulk_retry import bulk_retry_lead_rodo
from backend.app.services.lead_rodo_ops import (
    is_retryable_open_state,
    operator_actions_for,
    project_open_obligation,
    retry_open_obligation_send,
    sla_due_at,
    smtp_exhaustion,
    stamp_ops_escalation,
)


@pytest.fixture(autouse=True)
def _noop_orm_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sqlalchemy.orm.attributes.flag_modified", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "backend.app.modules.leads.intake_lifecycle.mark_recruitment_intake_in_progress",
        lambda *_a, **_k: None,
    )


def _lead(rodo: dict, *, stage: str = "new", source: str = "csv_import") -> SimpleNamespace:
    return SimpleNamespace(
        id="lead-1",
        tenant_id="t1",
        status="new",
        stage=stage,
        source=source,
        normalized={"email": "a@b.test", "first_name": "Ada", "rodo": rodo},
    )


def test_queue_sees_only_open_states() -> None:
    closed = _lead(
        {
            "status": "sent",
            "compliance_state": "delivered",
            "sent_at": "2026-09-01T00:00:00Z",
            "delivery_evidence": {
                "state": "delivered",
                "sent_at": "2026-09-01T00:00:00Z",
                "recipient": "a@b.test",
                "attempts": [{"via": "tenant_smtp", "ok": True}],
            },
        }
    )
    assert project_open_obligation(closed) is None
    open_item = project_open_obligation(
        _lead({"status": "review_required", "compliance_state": "review_required"})
    )
    assert open_item is not None
    assert open_item.compliance_state == "review_required"


def test_open_status_wins_over_closed_flag_in_queue() -> None:
    item = project_open_obligation(
        _lead({"status": "review_required", "compliance_state": "compliant"})
    )
    assert item is not None
    assert item.compliance_state == "review_required"


def test_art14_sla_is_one_month_until_first_contact() -> None:
    evaluated = datetime(2026, 8, 1, tzinfo=timezone.utc)
    block = {"evaluated_at": evaluated.isoformat(), "article": "14"}
    due = sla_due_at(block, article="14")
    assert due == evaluated + timedelta(days=30)
    due_contact = sla_due_at(block, article="14", lead_stage="contacted")
    assert due_contact == evaluated


def test_art13_sla_is_immediate() -> None:
    evaluated = datetime(2026, 9, 1, tzinfo=timezone.utc)
    due = sla_due_at({"evaluated_at": evaluated.isoformat()}, article="13")
    assert due == evaluated


def test_retryable_states_exclude_review_required() -> None:
    assert is_retryable_open_state("delivery_failed")
    assert is_retryable_open_state("delivery_required")
    assert not is_retryable_open_state("review_required")
    assert operator_actions_for("review_required") == ("send", "covered_at_source", "exempt")
    assert "retry" in operator_actions_for("delivery_failed")


def test_smtp_exhaustion_requires_failed_smtp_paths() -> None:
    block = {
        "compliance_state": "delivery_failed",
        "status": "failed",
        "delivery_evidence": {
            "attempts": [
                {"via": "tenant_smtp", "ok": False, "error": "timeout"},
                {"via": "platform_smtp", "ok": False, "error": "rejected"},
            ]
        },
    }
    tenant_ex, platform_ex, escalated = smtp_exhaustion(block)
    assert tenant_ex is True
    assert platform_ex is True
    assert escalated is True


def test_platform_fallback_success_is_not_escalation() -> None:
    block = {
        "compliance_state": "delivered",
        "delivery_evidence": {
            "attempts": [
                {"via": "tenant_smtp", "ok": False},
                {"via": "platform_smtp", "ok": True},
            ]
        },
    }
    _, _, escalated = smtp_exhaustion(block)
    assert escalated is False


def test_webhook_attempt_is_not_smtp_success() -> None:
    block = {
        "compliance_state": "delivery_failed",
        "status": "failed",
        "delivery_evidence": {
            "attempts": [{"via": "webhook", "ok": True}],
            "failure_reason": "gdpr_notice_delivery_exhausted",
        },
    }
    _, _, escalated = smtp_exhaustion(block)
    assert escalated is True


def test_stamp_ops_escalation_does_not_change_compliance_state() -> None:
    lead = _lead(
        {
            "status": "failed",
            "compliance_state": "delivery_failed",
            "delivery_evidence": {
                "attempts": [
                    {"via": "tenant_smtp", "ok": False},
                    {"via": "platform_smtp", "ok": False},
                ]
            },
        }
    )
    assert stamp_ops_escalation(lead) is True
    assert lead.normalized["rodo"]["compliance_state"] == "delivery_failed"
    assert lead.normalized["rodo"]["ops"]["escalation_reason"] == "smtp_exhausted"
    assert stamp_ops_escalation(lead) is False


def test_exempt_requires_lawful_code_and_actor() -> None:
    lead = _lead({"status": "review_required", "compliance_state": "review_required"})
    with pytest.raises(ComplianceTransitionError, match="actor"):
        mark_lead_rodo_exempt(lead, exemption_code="art_14_5_b", actor_id=None)
    with pytest.raises(ComplianceTransitionError, match="lawful"):
        mark_lead_rodo_exempt(lead, exemption_code="nope", actor_id="u1")
    mark_lead_rodo_exempt(lead, exemption_code="art_14_5_b", actor_id="u1", note="legal secrecy")
    assert lead.normalized["rodo"]["compliance_state"] == "exempt"
    assert lead.normalized["rodo"]["exemption_code"] == "art_14_5_b"


def test_exempt_cannot_rewrite_delivered() -> None:
    lead = _lead(
        {
            "status": "sent",
            "compliance_state": "delivered",
            "sent_at": "2026-09-01T00:00:00Z",
            "delivery_evidence": {
                "state": "delivered",
                "sent_at": "2026-09-01T00:00:00Z",
                "recipient": "a@b.test",
                "attempts": [{"via": "tenant_smtp", "ok": True}],
            },
        }
    )
    with pytest.raises(ComplianceTransitionError):
        mark_lead_rodo_exempt(lead, exemption_code="art_14_5_b", actor_id="u1")


@pytest.mark.asyncio
async def test_retry_rejects_review_required() -> None:
    lead = _lead({"status": "review_required", "compliance_state": "review_required"})
    db = AsyncMock()
    with pytest.raises(ComplianceTransitionError, match="review_required"):
        await retry_open_obligation_send(db, tenant_id="t1", lead=lead, actor_id="u1")


@pytest.mark.asyncio
async def test_bulk_retry_skips_review_required_and_matches_canonical_failed() -> None:
    failed = SimpleNamespace(
        id="lead-failed",
        tenant_id="t1",
        status="new",
        created_at=None,
        normalized={
            "email": "a@b.test",
            "rodo": {"status": "failed", "compliance_state": "delivery_failed"},
        },
    )
    review = SimpleNamespace(
        id="lead-review",
        tenant_id="t1",
        status="new",
        created_at=None,
        normalized={
            "email": "b@b.test",
            "rodo": {"status": "review_required", "compliance_state": "review_required"},
        },
    )
    db = AsyncMock()
    result_proxy = AsyncMock()
    result_proxy.scalars = lambda: SimpleNamespace(all=lambda: [failed, review])
    db.execute = AsyncMock(return_value=result_proxy)

    with patch(
        "backend.app.services.lead_rodo_bulk_retry.get_lead_rodo_settings",
        new_callable=AsyncMock,
        return_value=SimpleNamespace(channels=("email",), template_id=None, message_template_id=None),
    ):
        out = await bulk_retry_lead_rodo(db, tenant_id="t1", dry_run=True, max_items=10)

    assert out.attempted == 1
    assert out.items[0].lead_id == "lead-failed"
    assert out.items[0].compliance_state_before == "delivery_failed"


@pytest.mark.asyncio
async def test_bulk_retry_rejects_review_required_filter() -> None:
    db = AsyncMock()
    with pytest.raises(ValueError, match="review_required"):
        await bulk_retry_lead_rodo(db, tenant_id="t1", statuses=["review_required"])
