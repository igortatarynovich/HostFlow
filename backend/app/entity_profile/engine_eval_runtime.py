"""CL7 — Requirement Engine evaluation (ready | not_ready + blockers).

Engine is not an Entity Profile implementation — Profile may only ref.
This producer aggregates Presence / Value / Document / Process into
``entity_profile_engine_eval.v1``. Not a boolean. Not Hub ask generation
(DR1-runtime). Not Engine v2. Not Vacancy overlay SoT. Not R5 pack /
tenant_delta merge. Screening is not ``required=true`` on a field.

Refs Requirement Rules Engine P0. Document-kind blockers may appear;
this producer is not the required-doc policy SoT.

No alembic. No E8. No DR1-runtime.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from backend.app.entity_profile.constants import (
    DRIVER_CE_DOCUMENT_PACK_CODE,
    DRIVER_CE_PROFILE_CODE,
    DRIVER_CE_SCREENING_PACK_CODE,
)
from backend.app.entity_profile.membership_runtime import (
    MEMBERSHIP_CONTEXTS,
    is_field_member,
    presence_level,
    resolve_membership,
)

CONTRACT_ID = "entity_profile_engine_eval.v1"
STATUS_READY = "ready"
STATUS_NOT_READY = "not_ready"
KIND_PRESENCE = "presence"
KIND_VALUE = "value"
KIND_DOCUMENT = "document"
KIND_PROCESS = "process"
KINDS = (KIND_PRESENCE, KIND_VALUE, KIND_DOCUMENT, KIND_PROCESS)

ERROR_UNKNOWN_PROFILE = "unknown_profile"
ERROR_BOOLEAN_RESULT = "boolean_result"
ERROR_SCREENING_AS_REQUIRED = "screening_as_required"
ERROR_ENGINE_ON_MEMBERSHIP = "engine_on_membership"
ERROR_HUB_ASK_WRITE = "hub_ask_write"
ERROR_R5_POLICY_MERGE = "r5_policy_merge"
ERROR_VACANCY_OVERLAY_SOT = "vacancy_overlay_sot"
ERROR_ENGINE_V2 = "engine_v2"
ERROR_WRITE_TO_EXTRA = "write_to_extra"

_YEARS_CE = "recruitment.candidate.experience.years_ce"
_CITIZENSHIP = "platform.identity.citizenship"
_LICENSE_DOC = "driver_license"
_SCREENING_YEARS_CE_MIN = {
    DRIVER_CE_SCREENING_PACK_CODE: 2,
}
_PACK_DOCUMENTS = {
    DRIVER_CE_DOCUMENT_PACK_CODE: (
        "passport",
        "driver_license",
        "code95",
        "tacho_card",
    ),
}
_HANDOFF_POINTS = frozenset(
    {"handoff", "ready_for_handoff", "transition"}
)
_R5_KEYS = frozenset(
    {
        "tenant_delta",
        "merge_packs",
        "policy_merge",
        "r5_merge",
        "merge_tenant_delta",
    }
)
_HUB_ASK_KEYS = frozenset(
    {
        "persist_asks",
        "generate_asks",
        "outstanding_asks",
        "write_hub_asks",
        "engine_to_hub_outstanding_ask",
        "mass_generate",
    }
)
_OVERLAY_SOT_KEYS = frozenset(
    {
        "mint_overlay",
        "overlay_sot",
        "vacancy_overlay_sot",
        "catch_up_overlay",
    }
)
_ENGINE_V2_KEYS = frozenset(
    {
        "engine_v2",
        "mint_engine_v2",
        "requirement_engine_v2",
    }
)


def evaluate(
    entity: Mapping[str, Any] | None,
    profile: str | Mapping[str, Any] | None,
    vacancy: Mapping[str, Any] | str | None = None,
    process_point: str | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate ready | not_ready with structured blockers.

    Profile may only ref Engine. Screening is a pack predicate, not
    ``required=true``. Vacancy overlay, if passed, is an input — this
    producer does not mint overlay SoT. Does not write Hub asks.
    """
    entity_payload = entity if isinstance(entity, Mapping) else {}
    vacancy_payload = vacancy if isinstance(vacancy, Mapping) else {}
    point = _process_point_code(process_point)

    policy_error = _policy_error(entity_payload, vacancy_payload, process_point)
    if policy_error is not None:
        return policy_error

    code = _profile_code(profile)
    membership = resolve_membership(code)
    if membership is None:
        return _fail(ERROR_UNKNOWN_PROFILE)

    refs = membership.get("refs") or {}
    if not isinstance(refs, Mapping):
        refs = {}

    values = _entity_values(entity_payload)
    documents = _entity_documents(entity_payload)
    presence_ctx = point if point in MEMBERSHIP_CONTEXTS else "card_save"

    blockers: list[dict[str, Any]] = []
    blockers.extend(_presence_blockers(code, values, presence_ctx))
    blockers.extend(
        _value_blockers(code, values, refs, vacancy_payload, entity_payload)
    )
    blockers.extend(_document_blockers(refs, documents, entity_payload))
    blockers.extend(_process_blockers(point, values, documents, refs))

    status = STATUS_READY if not blockers else STATUS_NOT_READY
    return {
        "ok": True,
        "contract_id": CONTRACT_ID,
        "profile_code": code,
        "status": status,
        "blockers": blockers,
    }


def contract_metadata() -> dict[str, str]:
    return {
        "contract_id": CONTRACT_ID,
        "proof_profile": DRIVER_CE_PROFILE_CODE,
        "producer": "backend.app.entity_profile.engine_eval_runtime",
    }


def _fail(error: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "error": error, "contract_id": CONTRACT_ID}
    out.update(extra)
    return out


def _profile_code(profile: str | Mapping[str, Any] | None) -> str:
    if isinstance(profile, str):
        return profile.strip()
    if isinstance(profile, Mapping):
        for key in ("profile_code", "code", "entity_profile_code"):
            value = str(profile.get(key) or "").strip()
            if value:
                return value
    return ""


def _process_point_code(process_point: str | Mapping[str, Any] | None) -> str:
    if isinstance(process_point, str):
        return process_point.strip().lower()
    if isinstance(process_point, Mapping):
        for key in ("process_point", "code", "stage", "stage_code", "point"):
            value = str(process_point.get(key) or "").strip().lower()
            if value:
                return value
    return "card_save"


def _policy_error(
    entity: Mapping[str, Any],
    vacancy: Mapping[str, Any],
    process_point: str | Mapping[str, Any] | None,
) -> Optional[dict[str, Any]]:
    payloads: list[Mapping[str, Any]] = [entity, vacancy]
    if isinstance(process_point, Mapping):
        payloads.append(process_point)
    for payload in payloads:
        extra_error = _extra_error(payload)
        if extra_error is not None:
            return extra_error
        if _wants_boolean(payload):
            return _fail(ERROR_BOOLEAN_RESULT)
        if _is_truthy(payload.get("screening_as_required")) or _is_truthy(
            payload.get("required_true")
        ):
            return _fail(ERROR_SCREENING_AS_REQUIRED)
        years = payload.get(_YEARS_CE) or payload.get("years_ce")
        if isinstance(years, Mapping) and _is_truthy(years.get("required")):
            return _fail(ERROR_SCREENING_AS_REQUIRED)
        if _is_truthy(payload.get("put_on_membership")) or _is_truthy(
            payload.get("engine_on_membership")
        ):
            return _fail(ERROR_ENGINE_ON_MEMBERSHIP)
        for key in _HUB_ASK_KEYS:
            if key in payload and payload.get(key) not in (None, False, "", [], {}):
                return _fail(ERROR_HUB_ASK_WRITE)
        if _is_truthy(payload.get("persist_asks")) or _is_truthy(
            payload.get("generate_asks")
        ):
            return _fail(ERROR_HUB_ASK_WRITE)
        for key in _R5_KEYS:
            if key in payload and payload.get(key) not in (None, False, "", [], {}):
                return _fail(ERROR_R5_POLICY_MERGE)
        for key in _OVERLAY_SOT_KEYS:
            if _is_truthy(payload.get(key)):
                return _fail(ERROR_VACANCY_OVERLAY_SOT)
        for key in _ENGINE_V2_KEYS:
            if _is_truthy(payload.get(key)):
                return _fail(ERROR_ENGINE_V2)
    return None


def _extra_error(payload: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    if str(payload.get("write_to") or "").strip() == "extra":
        return _fail(ERROR_WRITE_TO_EXTRA)
    if _is_truthy(payload.get("copy_to_extra")):
        return _fail(ERROR_WRITE_TO_EXTRA)
    extra = payload.get("extra")
    if isinstance(extra, Mapping) and extra:
        return _fail(ERROR_WRITE_TO_EXTRA)
    return None


def _wants_boolean(payload: Mapping[str, Any]) -> bool:
    if _is_truthy(payload.get("boolean")) or _is_truthy(payload.get("as_boolean")):
        return True
    result_shape = str(payload.get("result") or payload.get("status_shape") or "").strip()
    return result_shape.lower() in {"boolean", "bool", "true_false"}


def _entity_values(entity: Mapping[str, Any]) -> dict[str, Any]:
    for key in ("values", "fields", "payload", "normalized_payload"):
        raw = entity.get(key)
        if isinstance(raw, Mapping):
            return dict(raw)
    skip = {
        "documents",
        "values",
        "fields",
        "payload",
        "normalized_payload",
        "extra",
        "write_to",
        "copy_to_extra",
    }
    return {
        str(key): value
        for key, value in entity.items()
        if str(key) not in skip and "." in str(key)
    }


def _entity_documents(entity: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = entity.get("documents")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    return [row for row in raw if isinstance(row, Mapping)]


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple)):
        return len(value) == 0
    return False


def _payload_value(values: Mapping[str, Any], qualified_code: str) -> Any:
    if qualified_code in values:
        return values.get(qualified_code)
    aliases = {
        "recruitment.candidate.first_name": ("first_name",),
        "recruitment.candidate.last_name": ("last_name",),
        "recruitment.candidate.contacts.phone": ("phone",),
        "recruitment.candidate.contacts.email": ("email",),
        "platform.identity.citizenship": ("citizenship",),
        "platform.identity.address": ("address",),
        _YEARS_CE: ("years_ce", "experience_eu_years"),
    }
    for alias in aliases.get(qualified_code, ()):
        if alias in values and not _is_empty(values.get(alias)):
            return values.get(alias)
    return values.get(qualified_code)


def _blocker(
    kind: str,
    code: str,
    owner: str,
    message: str,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "kind": kind,
        "code": code,
        "owner": owner,
        "message": message,
        "evidence": dict(evidence),
    }


def _presence_blockers(
    profile_code: str,
    values: Mapping[str, Any],
    context: str,
) -> list[dict[str, Any]]:
    membership = resolve_membership(profile_code)
    if membership is None:
        return []
    out: list[dict[str, Any]] = []
    for row in membership.get("fields") or []:
        qualified = str(row.get("qualified_code") or "").strip()
        if not qualified:
            continue
        level = presence_level(profile_code, qualified, context)
        if level != "required":
            continue
        if not _is_empty(_payload_value(values, qualified)):
            continue
        out.append(
            _blocker(
                KIND_PRESENCE,
                f"presence.{qualified}",
                "profile",
                f"{qualified} must be present",
                {
                    "qualified_code": qualified,
                    "context": context,
                    "presence": level,
                },
            )
        )
    return out


def _value_blockers(
    profile_code: str,
    values: Mapping[str, Any],
    refs: Mapping[str, Any],
    vacancy: Mapping[str, Any],
    entity: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if not is_field_member(profile_code, _YEARS_CE):
        return []
    pack = str(refs.get("screening_pack_code") or "").strip()
    if not pack:
        return []
    minimum = _SCREENING_YEARS_CE_MIN.get(pack)
    overlay_min = vacancy.get("years_ce_min")
    if overlay_min is None:
        overlay_min = entity.get("years_ce_min")
    if overlay_min is not None:
        try:
            minimum = int(overlay_min)
        except (TypeError, ValueError):
            pass
    if minimum is None:
        return []
    raw = _payload_value(values, _YEARS_CE)
    if _is_empty(raw):
        return []
    try:
        years = int(raw)
    except (TypeError, ValueError):
        years = None
    if years is not None and years >= minimum:
        return []
    return [
        _blocker(
            KIND_VALUE,
            "screening.years_ce.min",
            "screening_pack",
            f"{_YEARS_CE} must be ≥ {minimum}",
            {
                "qualified_code": _YEARS_CE,
                "value": raw,
                "minimum": minimum,
                "screening_pack_code": pack,
                "required": False,
            },
        )
    ]


def _document_type_code(doc: Mapping[str, Any]) -> str:
    for key in ("document_type_code", "type", "type_code", "doc_type"):
        raw = doc.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip().lower()
    return ""


def _document_blockers(
    refs: Mapping[str, Any],
    documents: Sequence[Mapping[str, Any]],
    entity: Mapping[str, Any],
) -> list[dict[str, Any]]:
    pack = str(refs.get("document_pack_code") or "").strip()
    if not pack:
        return []
    required = _PACK_DOCUMENTS.get(pack, ())
    present = {_document_type_code(row) for row in documents}
    present.discard("")
    extra_types = entity.get("document_types")
    if isinstance(extra_types, Sequence) and not isinstance(extra_types, (str, bytes)):
        present.update(str(item).strip().lower() for item in extra_types if item)
    out: list[dict[str, Any]] = []
    for doc_type in required:
        if doc_type in present:
            continue
        out.append(
            _blocker(
                KIND_DOCUMENT,
                f"document.{doc_type}.missing",
                "document_pack",
                f"{doc_type} must be present",
                {
                    "document_type_code": doc_type,
                    "document_pack_code": pack,
                },
            )
        )
    return out


def _license_verified(documents: Sequence[Mapping[str, Any]]) -> bool:
    for row in documents:
        if _document_type_code(row) != _LICENSE_DOC:
            continue
        if _is_truthy(row.get("verified")) or _is_truthy(row.get("is_verified")):
            return True
        status = str(row.get("verification") or row.get("status") or "").strip().lower()
        if status in {"verified", "valid"}:
            return True
    return False


def _process_blockers(
    process_point: str,
    values: Mapping[str, Any],
    documents: Sequence[Mapping[str, Any]],
    refs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if process_point not in _HANDOFF_POINTS:
        return []
    process_ref = str(refs.get("process_profile_code") or "").strip() or "process"
    out: list[dict[str, Any]] = []
    if _is_empty(_payload_value(values, _CITIZENSHIP)):
        out.append(
            _blocker(
                KIND_PROCESS,
                "process.handoff.citizenship",
                "process",
                "citizenship must hold before handoff",
                {
                    "qualified_code": _CITIZENSHIP,
                    "process_point": process_point,
                    "process_profile_code": process_ref,
                },
            )
        )
    if not _license_verified(documents):
        out.append(
            _blocker(
                KIND_PROCESS,
                "process.handoff.licence_verified",
                "process",
                "licence must be verified before handoff",
                {
                    "document_type_code": _LICENSE_DOC,
                    "process_point": process_point,
                    "process_profile_code": process_ref,
                },
            )
        )
    return out


def _is_truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"1", "true", "yes"}:
        return True
    return False
