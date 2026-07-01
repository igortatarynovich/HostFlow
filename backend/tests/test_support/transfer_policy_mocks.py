"""Shared mocks for TransferPolicyResolver regression tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from backend.app.services.transfer_policy_resolver import RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY

_ELIGIBILITY_PATCH = (
    "backend.app.services.transfer_policy_resolver.resolve_workforce_eligibility_via_contract"
)
_EXPECTED_DOCS_PATCH = (
    "backend.app.services.transfer_policy_resolver.ReferenceServiceFacade.get_applicable_documents"
)
_PKG_PATCH = "backend.app.services.transfer_policy_resolver.evaluate_recruitment_package"
_FIELD_REQ_PATCH = "backend.app.services.transfer_policy_resolver.evaluate_field_requirements_for_candidate"
_OVERRIDES_PATCH = (
    "backend.app.api.v1.candidates.pipeline_overrides_service.approved_handoff_relaxed_types"
)
_DEST_PATCH = "backend.app.services.transfer_policy_resolver._resolve_destinations_for_candidate"
_GATES_PATCH = "backend.app.services.transfer_policy_resolver.resolve_hiring_pipeline_gates"


def make_candidate_db(*, candidate: Any) -> Any:
    class _Result:
        def scalar_one_or_none(self):
            return candidate

    return SimpleNamespace(execute=AsyncMock(return_value=_Result()))


def make_candidate(
    *,
    candidate_id: str = "cand-1",
    tenant_id: str = "tenant-1",
    stage: str = "docs_got",
    confirmed_blocks: list[str] | None = None,
    phone: str = "+48111222333",
    email: str = "a@b.c",
    address: str = "Street 1",
    company_id: str | None = None,
) -> SimpleNamespace:
    confirmed = confirmed_blocks if confirmed_blocks is not None else ["Passport / ID"]
    return SimpleNamespace(
        id=candidate_id,
        tenant_id=tenant_id,
        deleted_at=None,
        stage=stage,
        company_id=company_id,
        own_company_id=None,
        vacancy_id="vac-1",
        phone=phone,
        email=email,
        _get_extra=lambda: {RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY: confirmed},
        _get_personal_data=lambda: {"address": address},
    )


def eligibility_ready(*, missing: list[str] | None = None, pending: list[str] | None = None) -> dict[str, Any]:
    missing_docs = list(missing or [])
    pending_docs = list(pending or [])
    blockers: list[dict[str, Any]] = []
    for doc in missing_docs:
        blockers.append(
            {
                "code": "missing_required_document",
                "reason": f"Required document '{doc}' is missing.",
                "document_code": doc,
                "source_layer": "document_packs",
            }
        )
    for doc in pending_docs:
        blockers.append(
            {
                "code": "pending_document_verification",
                "reason": f"Required document '{doc}' is not verified yet.",
                "document_code": doc,
                "source_layer": "document_packs",
            }
        )
    handoff_allowed = not missing_docs and not pending_docs
    return {
        "eligibility_status": "eligible" if handoff_allowed else "pending_documents",
        "allowed_operations": {"handoff_to_hr": handoff_allowed},
        "readiness_profiles": {
            "hr_ready": {"status": "ready" if handoff_allowed else "blocked"},
        },
        "missing_documents": missing_docs,
        "pending_verification_documents": pending_docs,
        "blocking_reasons": blockers,
    }


def package_ready(*, missing_fields: list[dict[str, str]] | None = None, blocks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    block_rows = blocks or [{"document_key": "Passport / ID", "status": "ready"}]
    missing_data = list(missing_fields or [])
    blocking_blocks = [b["document_key"] for b in block_rows if b.get("status") in ("missing", "issue", "data")]
    return {
        "ready": not missing_data and not blocking_blocks,
        "blocks": block_rows,
        "blocking_blocks": blocking_blocks,
        "missing_data_fields": missing_data,
    }


def tenant_link(*, internal_hr: bool = True, client: bool = True, enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        get_handoff_enabled=lambda: enabled,
        get_handoff_to_client=lambda: client and enabled,
        get_handoff_to_internal_hr=lambda: internal_hr and enabled,
        get_workforce_handoff_on_ready_for_handoff_stage=lambda: False,
    )


def hiring_gates() -> SimpleNamespace:
    return SimpleNamespace(
        stages_without_doc_pipeline_block=frozenset(),
        stages_verify_uploads_block_forward=frozenset(),
        stages_require_vacancy_for_forward=frozenset(),
    )


def field_requirements_ready(*, missing_fields: list[dict[str, str]] | None = None) -> dict[str, Any]:
    missing = list(missing_fields or [])
    blocking_reasons = [
        {
            "code": "missing_data_field",
            "message": f"Missing required data: {row.get('label') or row.get('field_code')}",
            "source_layer": "field_requirements",
            "field_code": row.get("field_code"),
            "qualified_code": row.get("qualified_code"),
            "label": row.get("label"),
            "requirement_code": row.get("requirement_code", "recruitment_contact_core"),
        }
        for row in missing
    ]
    return {
        "missing_fields": missing,
        "blocking_reasons": blocking_reasons,
        "context": "transition",
        "system_stage": "ready_for_handoff",
        "requirement_count": 1,
    }


def patch_transfer_policy_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    eligibility: dict[str, Any] | None = None,
    pkg: dict[str, Any] | None = None,
    field_requirements: dict[str, Any] | None = None,
    overrides: set[str] | None = None,
    destinations: tuple[list[str], SimpleNamespace | None] | None = None,
) -> None:
    monkeypatch.setattr(
        _ELIGIBILITY_PATCH,
        AsyncMock(return_value=eligibility or eligibility_ready()),
    )
    monkeypatch.setattr(
        _EXPECTED_DOCS_PATCH,
        AsyncMock(return_value=[{"document_code": "passport", "required": True}]),
    )
    monkeypatch.setattr(
        _PKG_PATCH,
        AsyncMock(return_value=pkg or package_ready()),
    )
    resolved_pkg = pkg or package_ready()
    monkeypatch.setattr(
        _FIELD_REQ_PATCH,
        AsyncMock(
            return_value=field_requirements
            if field_requirements is not None
            else field_requirements_ready(missing_fields=resolved_pkg.get("missing_data_fields") or [])
        ),
    )
    monkeypatch.setattr(
        _OVERRIDES_PATCH,
        AsyncMock(return_value=overrides or set()),
    )
    dest = destinations if destinations is not None else (["internal_hr", "client"], tenant_link())
    if len(dest) == 2:
        dest_list, link = dest
        dest = (dest_list, link, {})
    monkeypatch.setattr(_DEST_PATCH, AsyncMock(return_value=dest))
    monkeypatch.setattr(_GATES_PATCH, AsyncMock(return_value=hiring_gates()))
