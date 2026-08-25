"""DR1-runtime — Engine writes Hub outstanding asks.

Proof consumer: ``recruitment.candidate.driver_ce``.
Contract: ``engine_to_hub_outstanding_ask.v1``.

CL7 ``evaluate`` (Overlay as defined input)
  → DR1-contract ``project_engine_evaluation_to_outstanding_asks``
  → Hub persist on ``documents.hub_adapter_v1``
     [{doc_type: <canonical>, state: missing|requested|problem}]

Not a second projection producer. Not a Hub request table. Not Catalog
``document.requested``. Not mass generation. Not CL8. Not Engine v2.
Not E8-bind / E8-eval. Overlay is input, not this writer. Evaluate
does not write asks.

No alembic. Persist is Hub-owned, keyed by Document Link identity
(required type + entity) — existing E7 SoT, not a new table.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from backend.app.document_types.registry import (
    is_canonical_code,
    load_legacy_aliases_payload,
)
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.engine_eval_runtime import (
    KIND_DOCUMENT,
    STATUS_READY,
    evaluate,
)
from backend.app.entity_profile.membership_runtime import resolve_membership
from backend.app.entity_profile.vacancy_overlay_runtime import merge, resolve_overlay
from backend.app.requirement_rules.constants import REQUIREMENT_EVALUATION_V1
from backend.app.requirement_rules.engine_to_hub_outstanding_ask_contract import (
    CONTRACT_ID,
    HUB_ADAPTER_ID,
    OUTSTANDING_ASK_STATES,
    project_engine_evaluation_to_outstanding_asks,
    validate_outstanding_ask_row,
)
from backend.app.services.document_hub_delivery_contract import (
    E4_LINKED_ENTITY_TYPE,
    persist_outstanding_asks_via_contract,
)

PROOF_PROFILE = DRIVER_CE_PROFILE_CODE
ERROR_MASS_GENERATE = "mass_generate"
ERROR_CL8 = "cl8"
ERROR_E8 = "e8"
ERROR_ENGINE_V2 = "engine_v2"
ERROR_HUB_REQUEST_TABLE = "hub_request_table"
ERROR_CATALOG_DOCUMENT_REQUESTED = "catalog_document_requested"
ERROR_MISSING_ENTITY_REF = "missing_entity_ref"
ERROR_SCREENING_AS_REQUIRED = "screening_as_required"

_MASS_KEYS = frozenset(
    {
        "mass_generate",
        "mass_generation",
        "all_entities",
        "all_tenants",
        "entity_ids",
        "tenant_ids",
    }
)
_CL8_KEYS = frozenset({"cl8", "mint_cl8", "as_cl8"})
_E8_KEYS = frozenset(
    {
        "e8",
        "e8_bind",
        "e8_eval",
        "packages",
        "ocr_requirement_matching",
    }
)
_ENGINE_V2_KEYS = frozenset(
    {
        "engine_v2",
        "mint_engine_v2",
        "requirement_engine_v2",
    }
)
_HUB_REQUEST_TABLE_KEYS = frozenset(
    {
        "hub_request_table",
        "document_request_table",
        "mint_hub_request",
        "reminder_table",
    }
)
_CATALOG_REQUESTED_KEYS = frozenset(
    {
        "document.requested",
        "catalog_document_requested",
        "mint_document_requested",
    }
)


def write_engine_outstanding_asks(
    entity: Mapping[str, Any] | None,
    profile: str | Mapping[str, Any] | None,
    vacancy: Mapping[str, Any] | str | None = None,
    process_point: str | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create Hub outstanding asks from CL7 evaluate via DR1-contract."""
    entity_payload = entity if isinstance(entity, Mapping) else {}
    vacancy_payload = vacancy if isinstance(vacancy, Mapping) else {}
    if isinstance(vacancy, str) and vacancy.strip():
        vacancy_payload = {"vacancy_ref": vacancy.strip()}

    policy_error = _policy_error(entity_payload, vacancy_payload, process_point)
    if policy_error is not None:
        return policy_error

    target = _hub_target(entity_payload)
    if target is None:
        return _fail(ERROR_MISSING_ENTITY_REF)

    evaluation = evaluate(entity_payload, profile, vacancy_payload, process_point)
    if evaluation.get("ok") is False:
        return dict(evaluation)

    overlay = resolve_overlay(evaluation.get("profile_code"), vacancy_payload)
    if overlay.get("ok") is False:
        return overlay
    membership = resolve_membership(str(evaluation.get("profile_code") or ""))
    refs = membership.get("refs") if isinstance(membership, Mapping) else {}
    if not isinstance(refs, Mapping):
        refs = {}
    effective = merge(
        evaluation.get("profile_code"),
        refs.get("screening_pack_code"),
        overlay,
    )
    if effective.get("ok") is False:
        return effective

    requirement_evaluation = _requirement_evaluation_from_cl7(
        evaluation,
        entity_payload,
        effective,
    )
    documents = requirement_evaluation.get("documents")
    asks = [
        row
        for row in project_engine_evaluation_to_outstanding_asks(
            requirement_evaluation,
            documents=documents if isinstance(documents, list) else None,
        )
        if validate_outstanding_ask_row(row)
        and is_canonical_code(row.get("doc_type"))
        and row.get("state") in OUTSTANDING_ASK_STATES
    ]
    persisted = persist_outstanding_asks_via_contract(
        asks,
        linked_entity_type=target["linked_entity_type"],
        linked_entity_id=target["linked_entity_id"],
    )
    return {
        "ok": True,
        "contract_id": CONTRACT_ID,
        "hub_adapter_id": HUB_ADAPTER_ID,
        "profile_code": evaluation.get("profile_code"),
        "proof_profile": PROOF_PROFILE,
        "status": evaluation.get("status"),
        "overlay": evaluation.get("overlay"),
        "outstanding_asks": persisted,
        "persisted": True,
        "mass_generate": False,
        "hub_request_table": False,
        "catalog_event": None,
    }


def contract_metadata() -> dict[str, str]:
    return {
        "contract_id": CONTRACT_ID,
        "hub_adapter_id": HUB_ADAPTER_ID,
        "proof_profile": PROOF_PROFILE,
        "producer": "backend.app.requirement_rules.engine_outstanding_ask_runtime",
    }


def _fail(error: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "error": error, "contract_id": CONTRACT_ID}
    out.update(extra)
    return out


def _hub_target(entity: Mapping[str, Any]) -> Optional[dict[str, str]]:
    etype = str(
        entity.get("linked_entity_type") or E4_LINKED_ENTITY_TYPE
    ).strip()
    eid = ""
    for key in ("linked_entity_id", "id", "entity_id", "candidate_id"):
        raw = entity.get(key)
        if raw is not None and str(raw).strip():
            eid = str(raw).strip()
            break
    if not etype or not eid:
        return None
    return {"linked_entity_type": etype, "linked_entity_id": eid}


def _canonical_document_type_code(code: str) -> str:
    """Canonical registry code via R3 identity + R4 alias map. Not a local dict."""
    raw = str(code or "").strip().lower().replace("-", "_")
    if not raw:
        return ""
    if is_canonical_code(raw):
        return raw
    aliases = load_legacy_aliases_payload().get("aliases") or {}
    mapped = str(aliases.get(raw) or "").strip().lower().replace("-", "_")
    if mapped and is_canonical_code(mapped):
        return mapped
    return ""


def _requirement_evaluation_from_cl7(
    evaluation: Mapping[str, Any],
    entity: Mapping[str, Any],
    effective: Mapping[str, Any],
) -> dict[str, Any]:
    required: list[dict[str, Any]] = []
    seen: set[str] = set()
    for code in effective.get("document_types") or ():
        normalized = _canonical_document_type_code(str(code or ""))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        required.append(
            {
                "document_type_code": normalized,
                "level": "blocking",
                "verification": "required",
            }
        )
    for blocker in evaluation.get("blockers") or []:
        if not isinstance(blocker, Mapping):
            continue
        if str(blocker.get("kind") or "") != KIND_DOCUMENT:
            continue
        evidence = blocker.get("evidence") if isinstance(blocker.get("evidence"), Mapping) else {}
        code = _canonical_document_type_code(
            str(evidence.get("document_type_code") or "")
        )
        if not code or code in seen:
            continue
        seen.add(code)
        required.append(
            {
                "document_type_code": code,
                "level": "blocking",
                "verification": "required",
            }
        )
    return {
        "entity_profile_code": evaluation.get("profile_code"),
        "evaluation_version": REQUIREMENT_EVALUATION_V1,
        "context": "readiness",
        "satisfied": evaluation.get("status") == STATUS_READY,
        "required_documents": required,
        "rule_sources_applied": [],
        "documents": _hub_documents(entity),
    }


def _hub_documents(entity: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = entity.get("documents")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    out: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, Mapping):
            continue
        snapshot = dict(row)
        code = ""
        for key in ("document_type_code", "type", "type_code", "doc_type"):
            value = snapshot.get(key)
            if value is not None and str(value).strip():
                code = str(value).strip().lower()
                break
        canonical = _canonical_document_type_code(code) or code
        if canonical:
            snapshot["document_type_code"] = canonical
            snapshot["type"] = canonical
        if _is_truthy(snapshot.get("verified")) or _is_truthy(snapshot.get("is_verified")):
            snapshot.setdefault("status", "verified")
        verification = str(
            snapshot.get("verification") or snapshot.get("status") or ""
        ).strip().lower()
        if verification in {"verified", "valid"}:
            snapshot.setdefault("status", "verified")
        out.append(snapshot)
    extra_types = entity.get("document_types")
    if isinstance(extra_types, Sequence) and not isinstance(extra_types, (str, bytes)):
        present = {str(row.get("type") or "").strip().lower() for row in out}
        for item in extra_types:
            code = _canonical_document_type_code(str(item or ""))
            if not code or code in present:
                continue
            present.add(code)
            out.append(
                {
                    "document_type_code": code,
                    "type": code,
                    "status": "verified",
                }
            )
    return out


def _policy_error(
    entity: Mapping[str, Any],
    vacancy: Mapping[str, Any],
    process_point: str | Mapping[str, Any] | None,
) -> Optional[dict[str, Any]]:
    payloads: list[Mapping[str, Any]] = [entity, vacancy]
    if isinstance(process_point, Mapping):
        payloads.append(process_point)
    for payload in payloads:
        if _is_truthy(payload.get("screening_as_required")) or _is_truthy(
            payload.get("required_true")
        ):
            return _fail(ERROR_SCREENING_AS_REQUIRED)
        for key in _MASS_KEYS:
            value = payload.get(key)
            if key in {"entity_ids", "tenant_ids", "all_entities", "all_tenants"}:
                if isinstance(value, (list, tuple, set)) and len(value) > 1:
                    return _fail(ERROR_MASS_GENERATE)
                if _is_truthy(value) and not isinstance(value, (list, tuple, set)):
                    return _fail(ERROR_MASS_GENERATE)
            elif _is_truthy(value) or (isinstance(value, (list, tuple, set)) and value):
                return _fail(ERROR_MASS_GENERATE)
        for key in _CL8_KEYS:
            if _is_truthy(payload.get(key)):
                return _fail(ERROR_CL8)
        for key in _E8_KEYS:
            if _is_truthy(payload.get(key)):
                return _fail(ERROR_E8)
        for key in _ENGINE_V2_KEYS:
            if _is_truthy(payload.get(key)):
                return _fail(ERROR_ENGINE_V2)
        for key in _HUB_REQUEST_TABLE_KEYS:
            if _is_truthy(payload.get(key)):
                return _fail(ERROR_HUB_REQUEST_TABLE)
        for key in _CATALOG_REQUESTED_KEYS:
            if key in payload and payload.get(key) not in (None, False, "", [], {}):
                return _fail(ERROR_CATALOG_DOCUMENT_REQUESTED)
            dotted = str(payload.get("catalog_event") or "").strip()
            if dotted == "document.requested":
                return _fail(ERROR_CATALOG_DOCUMENT_REQUESTED)
    return None


def _is_truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"1", "true", "yes"}:
        return True
    return False
