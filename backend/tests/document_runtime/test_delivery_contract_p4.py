"""Document Runtime Engine P4 — delivery contract consistency tests."""

from __future__ import annotations

from datetime import date, timedelta

from backend.app.document_runtime.constants import DOCUMENT_RUNTIME_V1
from backend.app.document_runtime.delivery_contract import (
    build_instances_delivery_via_contract,
    build_required_documents_delivery_via_contract,
    enrich_documents_via_contract,
    evaluate_snapshot_via_contract,
    runtime_for_type_via_contract,
)
from backend.app.document_runtime.hub_bridge import build_document_hub_runtime_checklist
from backend.app.document_runtime.pe_bridge import build_transition_gate_from_evaluation
from backend.app.document_runtime.readiness_bridge import build_document_runtime_section
from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules


def _profile_view() -> dict:
    manifest = recruitment_candidate_driver_ce_profile()
    return {
        "entity_profile_code": manifest["profile_code"],
        "profile_code": manifest["profile_code"],
        "profile": {
            "profile_code": manifest["profile_code"],
            "entity_type": manifest["entity_type"],
            "document_pack_code": manifest["document_pack_code"],
            "process_profile_code": manifest["process_profile_code"],
        },
        "fields": manifest["fields"],
    }


def _strip_evaluated_at(runtime: dict) -> dict:
    cleaned = dict(runtime)
    cleaned.pop("evaluated_at", None)
    return cleaned


def _delivery_without_timestamps(delivery: dict) -> dict:
    items = []
    for row in delivery.get("items") or []:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        runtime = item.get("document_runtime")
        if isinstance(runtime, dict):
            item["document_runtime"] = _strip_evaluated_at(runtime)
        items.append(item)
    return {**delivery, "items": items}


def _snapshot(**kwargs: object) -> dict:
    base = {"type": "passport", "status": "approved", "has_files": True}
    base.update(kwargs)
    return base


def test_p4_snapshot_runtime_identical_via_contract_and_legacy_wrappers() -> None:
    snapshot = _snapshot(document_id="doc-1")
    direct = _strip_evaluated_at(evaluate_snapshot_via_contract(snapshot, document_type_code="passport"))
    enriched = _strip_evaluated_at(enrich_documents_via_contract([snapshot])[0]["document_runtime"])
    assert direct == enriched


def test_p4_instances_delivery_identical_via_contract_and_readiness_wrapper() -> None:
    docs = enrich_documents_via_contract([_snapshot(), _snapshot(type="driver_license")])
    contract = build_instances_delivery_via_contract(docs)
    legacy = build_document_runtime_section(docs)
    assert contract == legacy
    assert contract["evaluation_version"] == DOCUMENT_RUNTIME_V1


def test_p4_required_delivery_identical_for_hub_and_pe() -> None:
    docs = enrich_documents_via_contract(
        [
            _snapshot(expires_on=(date.today() + timedelta(days=10)).isoformat()),
            _snapshot(type="driver_license"),
            _snapshot(type="code95"),
            _snapshot(type="tacho_card"),
        ]
    )
    evaluation = evaluate_requirement_rules(
        _profile_view(),
        context="readiness",
        normalized_payload={
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48123456789",
        },
        documents=docs,
    )

    hub_delivery = _delivery_without_timestamps(
        build_required_documents_delivery_via_contract(evaluation, documents=docs)
    )
    hub_legacy = _delivery_without_timestamps(build_document_hub_runtime_checklist(evaluation, documents=docs))
    pe_gate = build_transition_gate_from_evaluation(evaluation, documents=docs)
    pe_delivery = _delivery_without_timestamps(pe_gate["document_runtime"])

    assert hub_delivery == hub_legacy
    assert pe_delivery == hub_delivery

    passport_contract = _strip_evaluated_at(
        runtime_for_type_via_contract(evaluation, document_type_code="passport", documents=docs)
    )
    passport_hub = next(row for row in hub_delivery["items"] if row["document_type_code"] == "passport")
    assert passport_contract == passport_hub["document_runtime"]


def test_p4_same_document_same_runtime_across_consumers() -> None:
    soon = (date.today() + timedelta(days=12)).isoformat()
    docs = enrich_documents_via_contract([_snapshot(expires_on=soon)])
    evaluation = evaluate_requirement_rules(
        _profile_view(),
        context="readiness",
        normalized_payload={
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48123456789",
        },
        documents=docs,
    )

    readiness_runtime = _strip_evaluated_at(evaluation["document_runtime"]["documents"][0])
    hub_runtime = _strip_evaluated_at(
        runtime_for_type_via_contract(evaluation, document_type_code="passport", documents=docs)
    )
    pe_runtime = build_transition_gate_from_evaluation(evaluation, documents=docs)
    pe_passport = _strip_evaluated_at(
        next(
            row["document_runtime"]
            for row in pe_runtime["document_runtime"]["items"]
            if row["document_type_code"] == "passport"
        )
    )

    assert readiness_runtime == hub_runtime == pe_passport
    assert hub_runtime["workflow_status"] == "approved"
    assert hub_runtime["expiry_status"] == "expiring_soon"
    assert any(row["code"] == "document_expiring_soon" for row in hub_runtime["warnings"])


def test_p4_pending_document_same_blocker_semantics_everywhere() -> None:
    docs = enrich_documents_via_contract(
        [
            _snapshot(status="uploaded"),
            _snapshot(type="driver_license"),
            _snapshot(type="code95"),
            _snapshot(type="tacho_card"),
        ]
    )
    evaluation = evaluate_requirement_rules(
        _profile_view(),
        context="readiness",
        normalized_payload={
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48123456789",
        },
        documents=docs,
    )

    hub = build_required_documents_delivery_via_contract(evaluation, documents=docs)
    pe = build_transition_gate_from_evaluation(evaluation, documents=docs)
    passport_hub = next(row for row in hub["items"] if row["document_type_code"] == "passport")
    passport_pe = next(
        row for row in pe["document_runtime"]["items"] if row["document_type_code"] == "passport"
    )

    assert _strip_evaluated_at(passport_hub["document_runtime"]) == _strip_evaluated_at(
        passport_pe["document_runtime"]
    )
    assert passport_hub["satisfies_requirement"] is False
    assert passport_hub["lifecycle_status"] == "uploaded"
    assert passport_hub["status"] == "pending"
