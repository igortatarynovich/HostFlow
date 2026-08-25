"""CL6 — Flight mapping runtime (map snapshot on Binding).

Mapping is a Flight/Binding consumer artifact, not an Entity Profile
implementation. Profile may only ref. CL6 executes Map
(raw / source_key + answer → qualified_code). Destination = Profile
member fields, not the Flight entity, not extra, not question text.

Snapshot lives on Binding. Not Zapier-style mapper UX. Not Meta ads
admin as mapping SoT. qa_only stays in CL5 Q&A. ignore is dropped.

Do not reopen Acquisition Stage 4 Flight Runtime (lifecycle/status).
Do not promote mapping_write.py as this contract. No DB column drop.
No alembic. No E8. No DR1-runtime.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.membership_runtime import (
    is_field_member,
    resolve_membership,
)
from backend.app.entity_profile.qa_runtime import (
    DISPOSITION_IGNORE,
    DISPOSITION_MAP,
    DISPOSITION_QA_ONLY,
    DISPOSITIONS,
)

CONTRACT_ID = "entity_profile_flight_map.v1"
SNAPSHOT_ON_BINDING = "binding"

ERROR_UNKNOWN_DISPOSITION = "unknown_disposition"
ERROR_UNKNOWN_PROFILE = "unknown_profile"
ERROR_MINTED_FIELD_SEMANTICS = "minted_field_semantics"
ERROR_WRITE_TO_EXTRA = "write_to_extra"
ERROR_NON_MEMBER_DEST = "non_member_dest"
ERROR_DEST_IS_FLIGHT = "dest_is_flight_entity"
ERROR_ZAPIER_UX = "zapier_ux"
ERROR_META_ADMIN_SOT = "meta_admin_sot"
ERROR_MISSING_BINDING = "missing_binding"
ERROR_QA_IN_SNAPSHOT = "qa_in_snapshot"
ERROR_P9_NOT_CL6 = "p9_not_cl6"
ERROR_SNAPSHOT_NOT_ON_BINDING = "snapshot_not_on_binding"

_ZAPIER_KEYS = frozenset(
    {
        "zapier",
        "zapier_ux",
        "mapper_canvas",
        "visual_mapper",
        "zapier_mapper",
    }
)
_META_ADMIN_MARKERS = frozenset(
    {
        "meta_admin",
        "meta_ads_admin",
        "ads_manager",
        "meta_ads_manager",
    }
)
_FLIGHT_DEST_MARKERS = frozenset(
    {
        "flight",
        "flight_entity",
        "flight.entity",
    }
)
_P9_MARKERS = frozenset(
    {
        "mapping_write",
        "p9",
        "intake_mapping_write",
    }
)


def apply_map(
    profile_code: str,
    source_answers: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None = None,
    binding: Mapping[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Execute Map items onto a Binding snapshot.

    Only ``disposition=map`` rows become snapshot entries. ``qa_only`` is
    absent. ``ignore`` is dropped. Destination must be a CL2 member
    ``qualified_code``.
    """
    envelope, rows = _envelope_and_rows(source_answers)
    code = str(profile_code or "").strip()
    membership = resolve_membership(code)
    if membership is None:
        return _fail(ERROR_UNKNOWN_PROFILE)

    extra_error = _extra_error(envelope)
    if extra_error is not None:
        return extra_error
    policy_error = _policy_error(envelope, binding)
    if policy_error is not None:
        return policy_error

    binding_ref = _binding_ref(binding)
    if not binding_ref:
        return _fail(ERROR_MISSING_BINDING)

    snapshot: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        extra_error = _extra_error(row)
        if extra_error is not None:
            return extra_error
        policy_error = _policy_error(row, binding)
        if policy_error is not None:
            return policy_error

        disposition = str(row.get("disposition") or "").strip()
        if disposition not in DISPOSITIONS:
            return _fail(ERROR_UNKNOWN_DISPOSITION, disposition=disposition)
        if disposition == DISPOSITION_IGNORE:
            continue
        if disposition == DISPOSITION_QA_ONLY:
            continue
        if disposition != DISPOSITION_MAP:
            continue

        source_key = str(row.get("source_key") or "").strip()
        question_label = str(row.get("question_label") or "").strip()
        qualified = str(row.get("qualified_code") or "").strip()
        minted = _minted_error(qualified, question_label, source_key)
        if minted is not None:
            return minted
        if _dest_is_flight(qualified, row):
            return _fail(ERROR_DEST_IS_FLIGHT, qualified_code=qualified)
        if not qualified or not is_field_member(code, qualified):
            return _fail(ERROR_NON_MEMBER_DEST, qualified_code=qualified)

        value = row.get("answer")
        if "value" in row and row.get("value") is not None:
            value = row.get("value")
        snapshot.append(
            {
                "source_key": source_key,
                "qualified_code": qualified,
                "value": value,
            }
        )

    return {
        "ok": True,
        "contract_id": CONTRACT_ID,
        "profile_code": code,
        "binding_ref": binding_ref,
        "snapshot_on": SNAPSHOT_ON_BINDING,
        "snapshot": snapshot,
    }


def contract_metadata() -> dict[str, str]:
    return {
        "contract_id": CONTRACT_ID,
        "proof_profile": DRIVER_CE_PROFILE_CODE,
        "snapshot_on": SNAPSHOT_ON_BINDING,
        "producer": "backend.app.entity_profile.flight_map_runtime",
    }


def _fail(error: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "error": error, "contract_id": CONTRACT_ID}
    out.update(extra)
    return out


def _envelope_and_rows(
    source_answers: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None,
) -> tuple[Mapping[str, Any], Sequence[Any]]:
    if source_answers is None:
        return {}, ()
    if isinstance(source_answers, Mapping):
        raw = source_answers.get("answers")
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            return source_answers, raw
        if "disposition" in source_answers or "source_key" in source_answers:
            return {}, (source_answers,)
        return source_answers, ()
    return {}, source_answers


def _binding_ref(binding: Mapping[str, Any] | str | None) -> Optional[str]:
    if binding is None:
        return None
    if isinstance(binding, str):
        return binding.strip() or None
    if isinstance(binding, Mapping):
        for key in ("binding_ref", "ref", "id", "binding_id"):
            value = str(binding.get(key) or "").strip()
            if value:
                return value
    return None


def _policy_error(
    payload: Mapping[str, Any],
    binding: Mapping[str, Any] | str | None,
) -> Optional[dict[str, Any]]:
    if _is_truthy(payload.get("include_qa")) or _is_truthy(payload.get("include_qa_only")):
        return _fail(ERROR_QA_IN_SNAPSHOT)
    snapshot_on = str(payload.get("snapshot_on") or "").strip().lower()
    if snapshot_on and snapshot_on != SNAPSHOT_ON_BINDING:
        return _fail(ERROR_SNAPSHOT_NOT_ON_BINDING, snapshot_on=snapshot_on)
    if _zapier_error(payload) is not None:
        return _zapier_error(payload)
    if _meta_admin_error(payload) is not None:
        return _meta_admin_error(payload)
    if _p9_error(payload) is not None:
        return _p9_error(payload)
    if isinstance(binding, Mapping):
        if _zapier_error(binding) is not None:
            return _zapier_error(binding)
        if _meta_admin_error(binding) is not None:
            return _meta_admin_error(binding)
        if _p9_error(binding) is not None:
            return _p9_error(binding)
        dest = str(binding.get("dest") or binding.get("destination") or "").strip()
        if _dest_is_flight(dest, binding):
            return _fail(ERROR_DEST_IS_FLIGHT, qualified_code=dest)
    return None


def _extra_error(payload: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    source = str(payload.get("source") or "").strip()
    if source == "extra":
        return _fail(ERROR_WRITE_TO_EXTRA)
    if str(payload.get("write_to") or "").strip() == "extra":
        return _fail(ERROR_WRITE_TO_EXTRA)
    if _is_truthy(payload.get("copy_to_extra")):
        return _fail(ERROR_WRITE_TO_EXTRA)
    extra = payload.get("extra")
    if isinstance(extra, Mapping) and extra:
        return _fail(ERROR_WRITE_TO_EXTRA)
    return None


def _zapier_error(payload: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    for key in _ZAPIER_KEYS:
        if _is_truthy(payload.get(key)):
            return _fail(ERROR_ZAPIER_UX)
    ux = str(payload.get("ux") or payload.get("mapper_ux") or "").strip().lower()
    if ux in {"zapier", "zapier_ux", "canvas"}:
        return _fail(ERROR_ZAPIER_UX)
    return None


def _meta_admin_error(payload: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    for key in ("mapping_sot", "sot", "source", "admin"):
        value = str(payload.get(key) or "").strip().lower()
        if value in _META_ADMIN_MARKERS:
            return _fail(ERROR_META_ADMIN_SOT)
    return None


def _p9_error(payload: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    producer = str(payload.get("producer") or payload.get("so_t") or payload.get("sot") or "").strip()
    if producer in _P9_MARKERS:
        return _fail(ERROR_P9_NOT_CL6)
    if _is_truthy(payload.get("use_p9")) or _is_truthy(payload.get("use_mapping_write")):
        return _fail(ERROR_P9_NOT_CL6)
    return None


def _dest_is_flight(qualified: str, row: Mapping[str, Any]) -> bool:
    dest_kind = str(
        row.get("dest") or row.get("destination") or row.get("dest_kind") or ""
    ).strip().lower()
    if dest_kind in _FLIGHT_DEST_MARKERS:
        return True
    code = str(qualified or "").strip().lower()
    if code == "flight" or code.startswith("flight."):
        return True
    return False


def _minted_error(
    qualified: str,
    question_label: str,
    source_key: str,
) -> Optional[dict[str, Any]]:
    if qualified and (
        _is_minted_field_code(qualified)
        or qualified == question_label
        or qualified == source_key
    ):
        return _fail(ERROR_MINTED_FIELD_SEMANTICS, qualified_code=qualified)
    if source_key and ("?" in source_key or source_key == question_label) and qualified:
        if _is_minted_field_code(qualified) or qualified == source_key:
            return _fail(ERROR_MINTED_FIELD_SEMANTICS, qualified_code=qualified or source_key)
    return None


def _is_minted_field_code(code: str) -> bool:
    """Leaf names like ``phone`` are not field SoT; question text is not either."""
    return bool(code) and "." not in code


def _is_truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"1", "true", "yes"}:
        return True
    return False
