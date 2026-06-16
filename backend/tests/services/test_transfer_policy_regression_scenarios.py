"""Transfer Policy regression scenarios — unit coverage for TransferPolicyResolver."""

from __future__ import annotations

import inspect

import pytest

from backend.app.services.transfer_policy_resolver import TransferPolicyResolver
from backend.tests.test_support.transfer_policy_mocks import (
    eligibility_ready,
    field_requirements_ready,
    make_candidate,
    make_candidate_db,
    package_ready,
    patch_transfer_policy_dependencies,
    tenant_link,
)


@pytest.mark.anyio
async def test_regression_missing_required_document_blocks_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    cand = make_candidate(confirmed_blocks=["Passport / ID"])
    patch_transfer_policy_dependencies(
        monkeypatch,
        eligibility=eligibility_ready(missing=["work_permit"]),
    )
    report = await TransferPolicyResolver.resolve(
        make_candidate_db(candidate=cand),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )
    assert report["transfer_allowed"] is False
    assert "work_permit" in report["missing_documents"]
    assert any(
        r.get("source_layer") == "document_packs"
        for r in report["blocking_reasons"]
    )


@pytest.mark.anyio
async def test_regression_pending_verification_blocks_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    cand = make_candidate()
    patch_transfer_policy_dependencies(
        monkeypatch,
        eligibility=eligibility_ready(pending=["driver_license"]),
    )
    report = await TransferPolicyResolver.resolve(
        make_candidate_db(candidate=cand),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )
    assert report["transfer_allowed"] is False
    assert "driver_license" in report["pending_verification_documents"]
    assert any(r.get("code") == "pending_document_verification" for r in report["blocking_reasons"])


@pytest.mark.anyio
async def test_regression_missing_contact_data_blocks_recruitment_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cand = make_candidate(phone="", email="", address="")
    patch_transfer_policy_dependencies(
        monkeypatch,
        pkg=package_ready(
            missing_fields=[
                {"field_code": "phone", "label": "Phone"},
                {"field_code": "email", "label": "Email"},
                {"field_code": "address", "label": "Address"},
            ]
        ),
        field_requirements=field_requirements_ready(
            missing_fields=[
                {"field_code": "phone", "label": "Phone", "qualified_code": "recruitment.candidate.contacts.phone"},
                {"field_code": "email", "label": "Email", "qualified_code": "recruitment.candidate.contacts.email"},
                {"field_code": "address", "label": "Address", "qualified_code": "platform.identity.address"},
            ]
        ),
    )
    report = await TransferPolicyResolver.resolve(
        make_candidate_db(candidate=cand),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )
    assert report["transfer_allowed"] is False
    assert len(report["missing_data_fields"]) == 3
    assert any(
        r.get("source_layer") == "field_requirements" and r.get("code") == "missing_data_field"
        for r in report["blocking_reasons"]
    )


@pytest.mark.anyio
async def test_regression_unconfirmed_blocks_block_transfer(monkeypatch: pytest.MonkeyPatch) -> None:
    cand = make_candidate(confirmed_blocks=[])
    patch_transfer_policy_dependencies(
        monkeypatch,
        pkg=package_ready(blocks=[{"document_key": "Passport / ID", "status": "ready"}]),
    )
    report = await TransferPolicyResolver.resolve(
        make_candidate_db(candidate=cand),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )
    assert report["transfer_allowed"] is False
    assert report["required_confirmations"]
    assert any(r.get("code") == "unconfirmed_block" for r in report["blocking_reasons"])


@pytest.mark.anyio
async def test_regression_stage_allowed_handoff_route_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    cand = make_candidate()
    patch_transfer_policy_dependencies(
        monkeypatch,
        destinations=([], tenant_link(enabled=False)),
    )
    report = await TransferPolicyResolver.resolve(
        make_candidate_db(candidate=cand),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )
    assert report["transfer_allowed"] is True
    assert report["handoff_create_allowed"] is False
    assert report["destinations_allowed"] == []
    assert any(w.get("code") == "no_destination" for w in report.get("warnings") or [])


@pytest.mark.anyio
async def test_regression_approved_override_clears_document_blocker(monkeypatch: pytest.MonkeyPatch) -> None:
    cand = make_candidate()
    patch_transfer_policy_dependencies(
        monkeypatch,
        eligibility=eligibility_ready(missing=["work_permit"]),
        overrides={"work_permit"},
    )
    report = await TransferPolicyResolver.resolve(
        make_candidate_db(candidate=cand),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )
    assert report["transfer_allowed"] is True
    assert "work_permit" in report["approved_overrides"]
    assert "work_permit" not in report["missing_documents"]
    assert "pipeline_override" in report["source_layers"]


@pytest.mark.anyio
async def test_regression_tenant_link_disabled_blocks_handoff_only(monkeypatch: pytest.MonkeyPatch) -> None:
    cand = make_candidate()
    patch_transfer_policy_dependencies(
        monkeypatch,
        destinations=([], tenant_link(enabled=False)),
    )
    report = await TransferPolicyResolver.resolve(
        make_candidate_db(candidate=cand),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
        require_destination=True,
    )
    assert report["transfer_allowed"] is True
    assert report["handoff_create_allowed"] is False
    assert any(r.get("code") == "no_destination" for r in report["blocking_reasons"])


@pytest.mark.anyio
async def test_regression_processing_by_hr_stage_report_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    cand = make_candidate(stage="processing_by_hr")
    patch_transfer_policy_dependencies(monkeypatch)
    report = await TransferPolicyResolver.resolve(
        make_candidate_db(candidate=cand),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )
    assert report["candidate_id"] == "cand-1"
    assert "policy_version" in report
    assert isinstance(report["blocking_reasons"], list)


def test_regression_legacy_ruleset_not_used_in_resolver_gate() -> None:
    resolve_source = inspect.getsource(TransferPolicyResolver.resolve)
    assert_source = inspect.getsource(TransferPolicyResolver.assert_transfer_allowed)
    for source in (resolve_source, assert_source):
        assert "rules_engine" not in source
        assert "compute_candidate_checklist" not in source
        assert "load_ruleset" not in source
        assert "document_ruleset_versions" not in source


@pytest.mark.anyio
async def test_regression_full_green_allows_stage_and_handoff(monkeypatch: pytest.MonkeyPatch) -> None:
    cand = make_candidate()
    patch_transfer_policy_dependencies(monkeypatch)
    report = await TransferPolicyResolver.resolve(
        make_candidate_db(candidate=cand),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
        require_destination=True,
    )
    assert report["transfer_allowed"] is True
    assert report["handoff_create_allowed"] is True
    err = await TransferPolicyResolver.assert_transfer_allowed(
        make_candidate_db(candidate=cand),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
        require_destination=False,
    )
    assert err == {}
