"""CL5 — Recruiter Q&A runtime (qa_only artifact).

Q&A is a consumer artifact, not an Entity Profile implementation.
Profile may only ref; Q&A is not membership, not a layout widget, not
``candidate.extra``. Three dispositions exist: ``map`` / ``qa_only`` /
``ignore``. This slice emits ``qa_only`` only.

Map (raw → ``qualified_code``) is CL6 Flight mapping — recognized, not
executed. Ignore is dropped. Visible after convert
(``survives_convert=true``). Source = Lead / Application, never a copy
in extra. Question text is not field SoT — do not mint ``phone`` from
«Telefon?». Flight / E8 / DR1-runtime stay later. No DB column drop.
No alembic.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.membership_runtime import (
    is_field_member,
    resolve_membership,
)

CONTRACT_ID = "entity_profile_qa.v1"
SOURCE_LEAD_APPLICATION = "lead_application"
DISPOSITION_MAP = "map"
DISPOSITION_QA_ONLY = "qa_only"
DISPOSITION_IGNORE = "ignore"
DISPOSITIONS = (DISPOSITION_MAP, DISPOSITION_QA_ONLY, DISPOSITION_IGNORE)

ERROR_UNKNOWN_DISPOSITION = "unknown_disposition"
ERROR_UNKNOWN_PROFILE = "unknown_profile"
ERROR_MINTED_FIELD_SEMANTICS = "minted_field_semantics"
ERROR_WRITE_TO_EXTRA = "write_to_extra"
ERROR_QA_ON_MEMBERSHIP = "qa_on_membership"
ERROR_MAP_IS_CL6 = "map_is_cl6"
ERROR_HIDDEN_AFTER_CONVERT = "hidden_after_convert"

_EXECUTE_MAP_KEYS = frozenset(
    {
        "execute_map",
        "apply_map",
        "execute_flight",
        "flight_snapshot",
        "flight_mapper",
        "mapped_value",
    }
)


def list_qa_dispositions() -> tuple[str, ...]:
    return DISPOSITIONS


def resolve_qa(
    profile_code: str,
    source_answers: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project qa_only items from Lead / Application answers.

    Mapped member fields are absent (they belong to the profile). Ignore
    is dropped. Map is catalogued, not executed (CL6).
    """
    envelope, rows = _envelope_and_rows(source_answers)
    code = str(profile_code or "").strip()
    membership = resolve_membership(code)
    if membership is None:
        return _fail(ERROR_UNKNOWN_PROFILE)

    extra_error = _extra_error(envelope)
    if extra_error is not None:
        return extra_error
    if _wants_execute_map(envelope):
        return _fail(ERROR_MAP_IS_CL6)
    if _is_truthy(envelope.get("hide_after_convert")) or envelope.get(
        "survives_convert"
    ) is False:
        return _fail(ERROR_HIDDEN_AFTER_CONVERT)
    if _is_truthy(envelope.get("put_on_membership")):
        return _fail(ERROR_QA_ON_MEMBERSHIP)

    items: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        extra_error = _extra_error(row)
        if extra_error is not None:
            return extra_error
        if _wants_execute_map(row):
            return _fail(ERROR_MAP_IS_CL6)

        disposition = str(row.get("disposition") or "").strip()
        if disposition not in DISPOSITIONS:
            return _fail(ERROR_UNKNOWN_DISPOSITION, disposition=disposition)

        source_key = str(row.get("source_key") or "").strip()
        question_label = str(row.get("question_label") or "").strip()
        qualified = str(row.get("qualified_code") or "").strip()
        minted = _minted_error(qualified, question_label, source_key)
        if minted is not None:
            return minted

        if disposition == DISPOSITION_QA_ONLY:
            if _is_membership_bind(code, source_key, qualified):
                return _fail(ERROR_QA_ON_MEMBERSHIP, qualified_code=qualified or source_key)
            if qualified:
                return _fail(ERROR_MINTED_FIELD_SEMANTICS, qualified_code=qualified)
            items.append(
                {
                    "source_key": source_key,
                    "question_label": question_label,
                    "answer": row.get("answer"),
                    "disposition": DISPOSITION_QA_ONLY,
                }
            )
            continue

        # map: recognized, not emitted, not executed. ignore: dropped.
        if disposition == DISPOSITION_MAP and qualified and _is_minted_field_code(qualified):
            return _fail(ERROR_MINTED_FIELD_SEMANTICS, qualified_code=qualified)

    return {
        "ok": True,
        "contract_id": CONTRACT_ID,
        "profile_code": code,
        "source": SOURCE_LEAD_APPLICATION,
        "survives_convert": True,
        "items": items,
    }


def contract_metadata() -> dict[str, str]:
    return {
        "contract_id": CONTRACT_ID,
        "proof_profile": DRIVER_CE_PROFILE_CODE,
        "source": SOURCE_LEAD_APPLICATION,
        "producer": "backend.app.entity_profile.qa_runtime",
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


def _wants_execute_map(payload: Mapping[str, Any]) -> bool:
    if _is_truthy(payload.get("execute")):
        return True
    for key in _EXECUTE_MAP_KEYS:
        value = payload.get(key)
        if value in (None, "", False):
            continue
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
        return _fail(ERROR_MINTED_FIELD_SEMANTICS, qualified_code=qualified or source_key)
    return None


def _is_minted_field_code(code: str) -> bool:
    """Leaf names like ``phone`` are not field SoT; question text is not either."""
    return bool(code) and "." not in code


def _is_membership_bind(profile_code: str, source_key: str, qualified: str) -> bool:
    if qualified and is_field_member(profile_code, qualified):
        return True
    if source_key and is_field_member(profile_code, source_key):
        return True
    return False


def _is_truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"1", "true", "yes"}:
        return True
    return False
