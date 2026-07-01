from __future__ import annotations

from datetime import date

from backend.app.modules.documents.reminder_candidate_projection import project_reminder_candidates_from_packs
from backend.app.modules.documents.reminder_work_queue_projection import (
    project_reminder_work_queue,
    resolve_owner_identity,
)


def test_resolve_owner_identity_prefers_employee() -> None:
    owner_type, owner_id = resolve_owner_identity(
        {"candidate_id": "cand-1", "employee_id": "emp-123"}
    )
    assert owner_type == "employee"
    assert owner_id == "emp-123"


def test_project_work_queue_from_expired_passport() -> None:
    candidates = [
        {
            "document_code": "passport",
            "reason": "expired",
            "why": "document_expired",
            "severity": "critical",
            "due_date": "2026-05-29",
            "days_left": -3,
            "source_pack": "legal_stay_pack",
            "owner_type": "employee",
            "recipient_role": "hr",
        }
    ]
    out = project_reminder_work_queue(
        candidates,
        owner_type="employee",
        owner_id="123",
    )
    assert len(out) == 1
    row = out[0]
    assert row["task_key"] == "document:passport:expired:employee:123"
    assert row["title"] == "Passport expired"
    assert row["severity"] == "critical"
    assert row["owner_type"] == "employee"
    assert row["owner_id"] == "123"
    assert row["recipient_role"] == "hr"
    assert row["due_date"] == "2026-05-29"
    assert row["source_pack"] == "legal_stay_pack"
    assert row["action"] == "request_update"


def test_project_work_queue_missing_document_upload_action() -> None:
    candidates = [
        {
            "document_code": "driver_license",
            "reason": "missing",
            "severity": "high",
            "due_date": "2026-05-29",
            "source_pack": "driver_pack",
            "owner_type": "candidate",
            "recipient_role": "hr",
        }
    ]
    out = project_reminder_work_queue(candidates, owner_type="candidate", owner_id="cand-9")
    assert out[0]["action"] == "upload_document"
    assert out[0]["title"] == "Driver License missing"


def test_project_work_queue_empty_without_owner_id() -> None:
    assert project_reminder_work_queue([], owner_type="candidate", owner_id="") == []


def test_owner_summary_includes_reminder_work_queue() -> None:
    from backend.app.modules.documents.owner_summary import compute_owner_summary
    from backend.app.services.document_ruleset import load_default_ruleset

    ruleset = load_default_ruleset()
    ctx = {
        "citizenship": "UA",
        "work_country": "PL",
        "position_category": "driver",
        "candidate_id": "cand-1",
        "employee_id": "emp-123",
    }
    out = compute_owner_summary(ctx, ruleset, [])
    assert "reminder_work_queue" in out
    assert isinstance(out["reminder_work_queue"], list)
    if out["reminder_work_queue"]:
        item = out["reminder_work_queue"][0]
        assert item["owner_type"] == "employee"
        assert item["owner_id"] == "emp-123"
        assert "task_key" in item
        assert "action" in item


def test_end_to_end_candidates_to_work_queue() -> None:
    packs = [
        {
            "code": "legal_stay_pack",
            "label": "Legal Stay Pack",
            "status": "gaps",
            "skeleton": False,
            "missing": [],
            "expired": ["passport"],
            "missing_expiry": [],
            "expiring_soon": [],
        }
    ]
    candidates = project_reminder_candidates_from_packs(
        packs,
        owner_type="employee",
        reference_date=date(2026, 5, 29),
    )
    queue = project_reminder_work_queue(candidates, owner_type="employee", owner_id="123")
    assert queue[0]["document_code"] == "passport"
    assert queue[0]["action"] == "request_update"
