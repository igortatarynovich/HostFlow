"""Transfer Policy resolver tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.services.transfer_policy_resolver import (
    RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY,
    TransferPolicyResolver,
    _pending_confirmations,
    _read_confirmed_blocks,
    _resolve_destinations_from_link,
)


def test_read_confirmed_blocks() -> None:
    extra = {RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY: ["Passport / ID", "  ", "Driver license"]}
    assert _read_confirmed_blocks(extra) == ["Passport / ID", "Driver license"]


def test_pending_confirmations() -> None:
    blocks = [
        {"document_key": "Passport / ID", "status": "ready"},
        {"document_key": "Driver license", "status": "ready"},
        {"document_key": "Medical", "status": "missing"},
    ]
    pending = _pending_confirmations(blocks, ["Passport / ID"])
    assert pending == [{"block_key": "Driver license", "confirmed_by_role": "recruiter"}]


def test_resolve_destinations_from_link() -> None:
    link = SimpleNamespace(
        get_handoff_enabled=lambda: True,
        get_handoff_to_internal_hr=lambda: True,
        get_handoff_to_client=lambda: False,
    )
    assert _resolve_destinations_from_link(link) == ["internal_hr"]

    disabled = SimpleNamespace(get_handoff_enabled=lambda: False)
    assert _resolve_destinations_from_link(disabled) == []


@pytest.mark.anyio
async def test_transfer_policy_blocked_by_unconfirmed_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    cand = SimpleNamespace(
        id="cand-1",
        tenant_id="tenant-1",
        deleted_at=None,
        stage="docs_got",
        company_id=None,
        own_company_id=None,
        vacancy_id=None,
        phone="+48111222333",
        email="a@b.c",
        _get_extra=lambda: {RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY: []},
        _get_personal_data=lambda: {"address": "Street 1"},
    )

    class _Result:
        def scalar_one_or_none(self):
            return cand

    db = SimpleNamespace(execute=AsyncMock(return_value=_Result()))

    async def _eligibility(*args, **kwargs):
        return {
            "eligibility_status": "eligible",
            "allowed_operations": {"handoff_to_hr": True},
            "readiness_profiles": {"hr_ready": {"status": "ready"}},
            "missing_documents": [],
            "pending_verification_documents": [],
            "blocking_reasons": [],
        }

    async def _expected_docs(*args, **kwargs):
        return [{"document_code": "passport", "required": True}]

    async def _pkg(*args, **kwargs):
        return {
            "ready": True,
            "blocks": [{"document_key": "Passport / ID", "status": "ready"}],
            "blocking_blocks": [],
            "missing_data_fields": [],
        }

    async def _overrides(*args, **kwargs):
        return set()

    async def _dest(*args, **kwargs):
        return (
            ["internal_hr"],
            SimpleNamespace(
                get_handoff_enabled=lambda: True,
                get_handoff_to_client=lambda: False,
                get_handoff_to_internal_hr=lambda: True,
                get_workforce_handoff_on_ready_for_handoff_stage=lambda: False,
            ),
            {},
        )

    async def _gates(*args, **kwargs):
        return SimpleNamespace(
            stages_without_doc_pipeline_block=frozenset(),
            stages_verify_uploads_block_forward=frozenset(),
            stages_require_vacancy_for_forward=frozenset(),
        )

    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.resolve_workforce_eligibility_via_contract",
        _eligibility,
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.ReferenceServiceFacade.get_applicable_documents",
        _expected_docs,
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.evaluate_recruitment_package",
        _pkg,
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.evaluate_field_requirements_for_candidate",
        AsyncMock(return_value={"missing_fields": [], "blocking_reasons": []}),
    )
    monkeypatch.setattr(
        "backend.app.api.v1.candidates.pipeline_overrides_service.approved_handoff_relaxed_types",
        _overrides,
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver._resolve_destinations_for_candidate",
        _dest,
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.resolve_hiring_pipeline_gates",
        _gates,
    )

    report = await TransferPolicyResolver.resolve(
        db,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )
    assert report["transfer_allowed"] is False
    assert report["required_confirmations"]
    assert any(r["code"] == "unconfirmed_block" for r in report["blocking_reasons"])
    assert "recruiter_confirmation" in report["source_layers"]


@pytest.mark.anyio
async def test_transfer_policy_allowed_when_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    cand = SimpleNamespace(
        id="cand-2",
        tenant_id="tenant-1",
        deleted_at=None,
        stage="docs_got",
        company_id="company-1",
        own_company_id=None,
        vacancy_id="vac-1",
        phone="+48111222333",
        email="a@b.c",
        _get_extra=lambda: {RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY: ["Passport / ID"]},
        _get_personal_data=lambda: {"address": "Street 1"},
    )

    class _Result:
        def scalar_one_or_none(self):
            return cand

    db = SimpleNamespace(execute=AsyncMock(return_value=_Result()))

    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.resolve_workforce_eligibility_via_contract",
        AsyncMock(
            return_value={
                "eligibility_status": "eligible",
                "allowed_operations": {"handoff_to_hr": True},
                "readiness_profiles": {"hr_ready": {"status": "ready"}},
                "missing_documents": [],
                "pending_verification_documents": [],
                "blocking_reasons": [],
            }
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.ReferenceServiceFacade.get_applicable_documents",
        AsyncMock(return_value=[{"document_code": "passport", "required": True}]),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.evaluate_recruitment_package",
        AsyncMock(
            return_value={
                "ready": True,
                "blocks": [{"document_key": "Passport / ID", "status": "ready"}],
                "blocking_blocks": [],
                "missing_data_fields": [],
            }
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.evaluate_field_requirements_for_candidate",
        AsyncMock(return_value={"missing_fields": [], "blocking_reasons": []}),
    )
    monkeypatch.setattr(
        "backend.app.api.v1.candidates.pipeline_overrides_service.approved_handoff_relaxed_types",
        AsyncMock(return_value=set()),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver._resolve_destinations_for_candidate",
        AsyncMock(
            return_value=(
                ["internal_hr", "client"],
                SimpleNamespace(
                    get_handoff_enabled=lambda: True,
                    get_handoff_to_client=lambda: True,
                    get_handoff_to_internal_hr=lambda: True,
                    get_workforce_handoff_on_ready_for_handoff_stage=lambda: True,
                ),
                {},
            )
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.resolve_hiring_pipeline_gates",
        AsyncMock(
            return_value=SimpleNamespace(
                stages_without_doc_pipeline_block=frozenset(),
                stages_verify_uploads_block_forward=frozenset(),
                stages_require_vacancy_for_forward=frozenset(),
            )
        ),
    )

    report = await TransferPolicyResolver.resolve(
        db,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-2",
    )
    assert report["transfer_allowed"] is True
    assert report["handoff_create_allowed"] is True
    assert report["destinations_allowed"] == ["internal_hr", "client"]
