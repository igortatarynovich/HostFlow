"""Vacancy Overlay — SoT + merge for vacancy-specific requirement delta.

Overlay is not an Entity Profile implementation — Profile may only ref.
``resolve_overlay(profile, vacancy)`` returns ``entity_profile_vacancy_overlay.v1``.
``merge(profile, screening_pack, overlay)`` is the defined input to CL7
``evaluate``. Not CL8. Not Engine v2. Not Hub ask write. Not DR1-runtime.
Not E8. Not vacancy UI. Not Reference R5 ``merge(pack, tenant_delta)``.
Ad-hoc ``years_ce_min`` is not the contract — it may only map into ``delta[]``.

No alembic. Overlay may tighten or add; it must not fork pack identity.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from backend.app.entity_profile.constants import (
    DRIVER_CE_DOCUMENT_PACK_CODE,
    DRIVER_CE_PROFILE_CODE,
    DRIVER_CE_SCREENING_PACK_CODE,
)
from backend.app.entity_profile.membership_runtime import resolve_membership

CONTRACT_ID = "entity_profile_vacancy_overlay.v1"
KIND_PRESENCE = "presence"
KIND_VALUE = "value"
KIND_DOCUMENT = "document"
KIND_PROCESS = "process"
KINDS = (KIND_PRESENCE, KIND_VALUE, KIND_DOCUMENT, KIND_PROCESS)
OP_TIGHTEN = "tighten"
OP_ADD = "add"
OPS = (OP_TIGHTEN, OP_ADD)

ERROR_UNKNOWN_PROFILE = "unknown_profile"
ERROR_OVERLAY_FORK = "overlay_fork"
ERROR_OVERLAY_RELAX = "overlay_relax"
ERROR_R5_POLICY_MERGE = "r5_policy_merge"
ERROR_HUB_ASK_WRITE = "hub_ask_write"
ERROR_ENGINE_V2 = "engine_v2"
ERROR_OVERLAY_ON_MEMBERSHIP = "overlay_on_membership"
ERROR_SCREENING_AS_REQUIRED = "screening_as_required"
ERROR_WRITE_TO_EXTRA = "write_to_extra"
ERROR_VACANCY_UI = "vacancy_ui"
ERROR_CL8 = "cl8"
ERROR_INVALID_DELTA = "invalid_delta"

_YEARS_CE = "recruitment.candidate.experience.years_ce"
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
_ENGINE_V2_KEYS = frozenset(
    {
        "engine_v2",
        "mint_engine_v2",
        "requirement_engine_v2",
    }
)
_VACANCY_UI_KEYS = frozenset(
    {
        "vacancy_ui",
        "render_vacancy_card",
        "vacancy_workspace",
        "vacancy_card_ui",
    }
)
_CL8_KEYS = frozenset({"cl8", "mint_cl8", "as_cl8"})
_FORK_KEYS = frozenset({"fork", "replace_pack", "replace_profile", "new_pack"})
_RELAX_OPS = frozenset({"relax", "replace", "fork", "delete"})


def resolve_overlay(
    profile: str | Mapping[str, Any] | None,
    vacancy: Mapping[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Return vacancy-specific requirement delta over Profile / Screening Pack."""
    vacancy_payload = _vacancy_payload(vacancy)
    policy_error = _policy_error(vacancy_payload)
    if policy_error is not None:
        return policy_error

    code = _profile_code(profile)
    membership = resolve_membership(code)
    if membership is None:
        return _fail(ERROR_UNKNOWN_PROFILE)

    refs = membership.get("refs") or {}
    if not isinstance(refs, Mapping):
        refs = {}
    screening = str(refs.get("screening_pack_code") or "").strip() or None

    deltas, delta_error = _resolve_deltas(vacancy_payload)
    if delta_error is not None:
        return delta_error

    return {
        "ok": True,
        "contract_id": CONTRACT_ID,
        "profile_code": code,
        "vacancy_ref": _vacancy_ref(vacancy_payload),
        "base": screening,
        "delta": deltas,
    }


def merge(
    profile: str | Mapping[str, Any] | None,
    screening_pack: str | None,
    overlay: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Merge Profile + Screening Pack with overlay delta. Overlay ≠ fork."""
    if overlay is None:
        overlay = {}
    if overlay.get("ok") is False:
        return dict(overlay)

    policy_error = _policy_error(overlay)
    if policy_error is not None:
        return policy_error

    code = _profile_code(profile) or str(overlay.get("profile_code") or "").strip()
    membership = resolve_membership(code)
    if membership is None:
        return _fail(ERROR_UNKNOWN_PROFILE)

    refs = membership.get("refs") or {}
    if not isinstance(refs, Mapping):
        refs = {}
    pack = (
        str(screening_pack or "").strip()
        or str(overlay.get("base") or "").strip()
        or str(refs.get("screening_pack_code") or "").strip()
    )
    document_pack = str(refs.get("document_pack_code") or "").strip()
    overlay_pack = str(overlay.get("screening_pack_code") or overlay.get("base") or "").strip()
    if overlay_pack and pack and overlay_pack != pack:
        return _fail(ERROR_OVERLAY_FORK)
    if _is_truthy(overlay.get("fork")) or _is_truthy(overlay.get("replace_pack")):
        return _fail(ERROR_OVERLAY_FORK)

    years_min = _SCREENING_YEARS_CE_MIN.get(pack)
    years_owner = "screening_pack"
    documents = list(_PACK_DOCUMENTS.get(document_pack, ()))
    presence_required: list[dict[str, Any]] = []
    process_deltas: list[dict[str, Any]] = []

    for row in overlay.get("delta") or []:
        if not isinstance(row, Mapping):
            return _fail(ERROR_INVALID_DELTA)
        op = str(row.get("op") or "").strip().lower()
        kind = str(row.get("kind") or "").strip().lower()
        if op in _RELAX_OPS:
            return _fail(ERROR_OVERLAY_RELAX if op == "relax" else ERROR_OVERLAY_FORK)
        if op not in OPS or kind not in KINDS:
            return _fail(ERROR_INVALID_DELTA)
        predicate = row.get("predicate") if isinstance(row.get("predicate"), Mapping) else {}
        if kind == KIND_VALUE:
            applied, error = _apply_value_delta(years_min, op, predicate)
            if error is not None:
                return error
            if applied is not None:
                years_min = applied
                years_owner = str(row.get("owner") or "vacancy")
        elif kind == KIND_DOCUMENT:
            extra = _document_type_from_predicate(predicate)
            if extra and extra not in documents:
                if op != OP_ADD:
                    return _fail(ERROR_INVALID_DELTA)
                documents.append(extra)
        elif kind == KIND_PRESENCE:
            qualified = str(predicate.get("qualified_code") or "").strip()
            if qualified:
                if op != OP_ADD:
                    return _fail(ERROR_INVALID_DELTA)
                presence_required.append(
                    {
                        "qualified_code": qualified,
                        "context": str(predicate.get("context") or "card_save"),
                        "owner": str(row.get("owner") or "vacancy"),
                        "code": str(row.get("code") or f"presence.{qualified}"),
                    }
                )
        elif kind == KIND_PROCESS:
            if op != OP_ADD:
                return _fail(ERROR_INVALID_DELTA)
            process_deltas.append(
                {
                    "code": str(row.get("code") or "process.overlay"),
                    "owner": str(row.get("owner") or "vacancy"),
                    "predicate": dict(predicate),
                    "message": str(row.get("message") or "").strip(),
                }
            )

    return {
        "ok": True,
        "contract_id": CONTRACT_ID,
        "profile_code": code,
        "screening_pack_code": pack or None,
        "document_pack_code": document_pack or None,
        "years_ce_min": years_min,
        "years_ce_owner": years_owner,
        "document_types": documents,
        "presence_required": presence_required,
        "process_deltas": process_deltas,
        "fork": False,
        "tenant_delta": False,
    }


def contract_metadata() -> dict[str, str]:
    return {
        "contract_id": CONTRACT_ID,
        "proof_profile": DRIVER_CE_PROFILE_CODE,
        "producer": "backend.app.entity_profile.vacancy_overlay_runtime",
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


def _vacancy_payload(vacancy: Mapping[str, Any] | str | None) -> dict[str, Any]:
    if isinstance(vacancy, Mapping):
        return dict(vacancy)
    if isinstance(vacancy, str) and vacancy.strip():
        return {"vacancy_ref": vacancy.strip()}
    return {}


def _vacancy_ref(vacancy: Mapping[str, Any]) -> Optional[str]:
    for key in ("vacancy_ref", "id", "vacancy_id", "code"):
        value = vacancy.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _resolve_deltas(
    vacancy: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], Optional[dict[str, Any]]]:
    raw = vacancy.get("delta")
    if raw is None and isinstance(vacancy.get("overlay"), Mapping):
        raw = vacancy["overlay"].get("delta")
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        out: list[dict[str, Any]] = []
        for row in raw:
            if not isinstance(row, Mapping):
                return [], _fail(ERROR_INVALID_DELTA)
            normalized, error = _normalize_delta(row)
            if error is not None:
                return [], error
            if normalized is not None:
                out.append(normalized)
        return out, None

    mapped: list[dict[str, Any]] = []
    years_min = vacancy.get("years_ce_min")
    if years_min is not None:
        mapped.append(
            {
                "kind": KIND_VALUE,
                "code": "screening.years_ce.min",
                "owner": "vacancy",
                "op": OP_TIGHTEN,
                "predicate": {
                    "qualified_code": _YEARS_CE,
                    "op": ">=",
                    "value": years_min,
                },
            }
        )
    extra_docs = vacancy.get("extra_document_types") or vacancy.get("add_document_types")
    if isinstance(extra_docs, Sequence) and not isinstance(extra_docs, (str, bytes)):
        for item in extra_docs:
            code = str(item or "").strip().lower()
            if not code:
                continue
            mapped.append(
                {
                    "kind": KIND_DOCUMENT,
                    "code": f"document.{code}.missing",
                    "owner": "vacancy",
                    "op": OP_ADD,
                    "predicate": {"document_type_code": code},
                }
            )
    return mapped, None


def _normalize_delta(
    row: Mapping[str, Any],
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    kind = str(row.get("kind") or "").strip().lower()
    op = str(row.get("op") or "").strip().lower()
    if op in _RELAX_OPS:
        error = ERROR_OVERLAY_RELAX if op == "relax" else ERROR_OVERLAY_FORK
        return None, _fail(error)
    if kind not in KINDS or op not in OPS:
        return None, _fail(ERROR_INVALID_DELTA)
    predicate = row.get("predicate") if isinstance(row.get("predicate"), Mapping) else {}
    return (
        {
            "kind": kind,
            "code": str(row.get("code") or "").strip(),
            "owner": str(row.get("owner") or "vacancy").strip() or "vacancy",
            "op": op,
            "predicate": dict(predicate),
            "message": str(row.get("message") or "").strip(),
        },
        None,
    )


def _apply_value_delta(
    current_min: int | None,
    op: str,
    predicate: Mapping[str, Any],
) -> tuple[int | None, Optional[dict[str, Any]]]:
    raw = predicate.get("value", predicate.get("minimum"))
    if raw is None:
        return current_min, None
    try:
        new_min = int(raw)
    except (TypeError, ValueError):
        return current_min, _fail(ERROR_INVALID_DELTA)
    if current_min is not None and new_min < current_min:
        return current_min, _fail(ERROR_OVERLAY_RELAX)
    if op == OP_ADD and current_min is None:
        return new_min, None
    if op not in {OP_TIGHTEN, OP_ADD}:
        return current_min, _fail(ERROR_INVALID_DELTA)
    if current_min is None:
        return new_min, None
    return max(current_min, new_min), None


def _document_type_from_predicate(predicate: Mapping[str, Any]) -> str:
    for key in ("document_type_code", "type", "type_code", "doc_type"):
        raw = predicate.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip().lower()
    return ""


def _policy_error(payload: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    extra_error = _extra_error(payload)
    if extra_error is not None:
        return extra_error
    if _is_truthy(payload.get("screening_as_required")) or _is_truthy(
        payload.get("required_true")
    ):
        return _fail(ERROR_SCREENING_AS_REQUIRED)
    if _is_truthy(payload.get("put_on_membership")) or _is_truthy(
        payload.get("overlay_on_membership")
    ):
        return _fail(ERROR_OVERLAY_ON_MEMBERSHIP)
    for key in _HUB_ASK_KEYS:
        if key in payload and payload.get(key) not in (None, False, "", [], {}):
            return _fail(ERROR_HUB_ASK_WRITE)
    for key in _R5_KEYS:
        if key in payload and payload.get(key) not in (None, False, "", [], {}):
            return _fail(ERROR_R5_POLICY_MERGE)
    for key in _ENGINE_V2_KEYS:
        if _is_truthy(payload.get(key)):
            return _fail(ERROR_ENGINE_V2)
    for key in _VACANCY_UI_KEYS:
        if _is_truthy(payload.get(key)):
            return _fail(ERROR_VACANCY_UI)
    for key in _CL8_KEYS:
        if _is_truthy(payload.get(key)):
            return _fail(ERROR_CL8)
    for key in _FORK_KEYS:
        if _is_truthy(payload.get(key)):
            return _fail(ERROR_OVERLAY_FORK)
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


def _is_truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"1", "true", "yes"}:
        return True
    return False
