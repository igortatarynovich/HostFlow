"""Vacancy Overlay operator write — effective human intent → minimal Overlay delta.

Round-trip safe: operator sees effective requirements (Profile/Pack + vacancy).
Save persists only tighten/add deltas. Inherited pack requirements are never
copied wholesale into the vacancy Overlay.

Never writes ``lead_criteria_v1`` or RPM ``tenant_delta``.

Contract: ``docs/specs/tasks/vacancy-overlay-write-ui.md``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.vacancy_overlay_runtime import (
    CONTRACT_ID as OVERLAY_CONTRACT_ID,
    KIND_DOCUMENT,
    KIND_VALUE,
    OP_ADD,
    OP_TIGHTEN,
    merge as merge_overlay,
    resolve_overlay,
)

_YEARS_CE = "recruitment.candidate.experience.years_ce"

FORBIDDEN_EXTRA_KEYS = frozenset(
    {
        "lead_criteria_v1",
        "lead_fit_evaluation_enabled_v1",
        "tenant_delta",
        "merge_packs",
        "policy_merge",
        "r5_merge",
        "merge_tenant_delta",
    }
)

_DOC_LABELS = {
    "passport": "Passport",
    "driver_license": "Driver license",
    "code95": "Code 95",
    "tacho_card": "Tachograph card",
}


class VacancyOverlayWriteError(ValueError):
    """Operator intent rejected (architecture / validation)."""


def _profile_code(profile: str | None) -> str:
    code = str(profile or "").strip()
    return code or DRIVER_CE_PROFILE_CODE


def inherited_base_requirements(profile: str | None = None) -> dict[str, Any]:
    """Profile/Pack effective baseline with empty vacancy Overlay."""
    code = _profile_code(profile)
    overlay = resolve_overlay(code, {"vacancy_ref": "inherited-base"})
    if overlay.get("ok") is False:
        raise VacancyOverlayWriteError(str(overlay.get("error") or "overlay_invalid"))
    merged = merge_overlay(code, overlay.get("base"), overlay)
    if merged.get("ok") is False:
        raise VacancyOverlayWriteError(str(merged.get("error") or "overlay_merge_invalid"))
    years = merged.get("years_ce_min")
    docs = [
        str(x).strip().lower()
        for x in (merged.get("document_types") or [])
        if str(x or "").strip()
    ]
    return {
        "profile_code": code,
        "years_ce_min": float(years) if years is not None else None,
        "document_types": docs,
    }


def _reject_forbidden(intent: Mapping[str, Any] | None) -> None:
    if not isinstance(intent, Mapping):
        return
    for key in FORBIDDEN_EXTRA_KEYS:
        if key in intent and intent.get(key) not in (None, False, "", [], {}):
            raise VacancyOverlayWriteError(f"forbidden_key:{key}")


def _parse_years(raw: Any) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise VacancyOverlayWriteError("years_ce_min_invalid") from exc
    if value < 0:
        raise VacancyOverlayWriteError("years_ce_min_invalid")
    return value


def _parse_docs(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (str, bytes)):
        raw = [raw]
    if not isinstance(raw, Sequence):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        code = str(item or "").strip().lower()
        if not code or code in seen:
            continue
        seen.add(code)
        out.append(code)
    return out


def build_minimal_overlay_delta(
    *,
    profile: str | None,
    effective_intent: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Diff effective operator intent against Profile/Pack — only vacancy deltas.

    - Unchanged inherited years/docs → absent from delta.
    - Reset years to inherited → years delta disappears.
    - Extra documents beyond pack → document add deltas only.
    - Cannot relax below inherited years / remove pack documents via this path.
    """
    _reject_forbidden(effective_intent)
    base = inherited_base_requirements(profile)
    base_years = base.get("years_ce_min")
    base_docs = set(base.get("document_types") or [])
    intent = effective_intent if isinstance(effective_intent, Mapping) else {}

    deltas: list[dict[str, Any]] = []
    years = _parse_years(intent.get("years_ce_min"))
    if years is not None:
        if base_years is not None and years + 1e-9 < float(base_years):
            raise VacancyOverlayWriteError("cannot_relax_years_ce_min")
        if base_years is None or abs(years - float(base_years)) > 1e-9:
            deltas.append(
                {
                    "kind": KIND_VALUE,
                    "op": OP_TIGHTEN,
                    "owner": "vacancy",
                    "code": "vacancy.years_ce.min",
                    "predicate": {
                        "qualified_code": _YEARS_CE,
                        "op": ">=",
                        "value": years,
                    },
                }
            )

    # Operator may send full effective doc list or vacancy-only extras.
    docs = _parse_docs(
        intent.get("required_documents")
        or intent.get("extra_document_types")
        or intent.get("vacancy_extra_documents")
    )
    for code in docs:
        if code in base_docs:
            # Inherited — must not appear in Overlay delta.
            continue
        deltas.append(
            {
                "kind": KIND_DOCUMENT,
                "op": OP_ADD,
                "owner": "vacancy",
                "code": f"vacancy.document.{code}",
                "predicate": {"document_type_code": code},
            }
        )
    return deltas


def apply_recruitment_requirements_to_extra(
    extra: Mapping[str, Any] | None,
    intent: Mapping[str, Any] | None,
    *,
    profile: str | None = None,
) -> dict[str, Any]:
    """Return Vacancy.extra with minimal Overlay SoT from effective intent."""
    out: dict[str, Any] = dict(extra) if isinstance(extra, Mapping) else {}
    for key in FORBIDDEN_EXTRA_KEYS:
        out.pop(key, None)

    code = _profile_code(profile)
    deltas = build_minimal_overlay_delta(profile=code, effective_intent=intent)
    out[OVERLAY_CONTRACT_ID] = {
        "contract_id": OVERLAY_CONTRACT_ID,
        "profile_code": code,
        "delta": deltas,
    }

    base = inherited_base_requirements(code)
    base_years = base.get("years_ce_min")
    years = _parse_years(
        intent.get("years_ce_min") if isinstance(intent, Mapping) else None
    )
    if years is not None and (
        base_years is None or abs(years - float(base_years)) > 1e-9
    ):
        out["years_ce_min"] = years
    else:
        out.pop("years_ce_min", None)

    base_docs = set(base.get("document_types") or [])
    docs = _parse_docs(
        (intent or {}).get("required_documents")
        if isinstance(intent, Mapping)
        else None
    )
    extras = [d for d in docs if d not in base_docs]
    if extras:
        out["extra_document_types"] = extras
    else:
        out.pop("extra_document_types", None)
        out.pop("add_document_types", None)

    probe = {"vacancy_ref": "write-probe", "delta": deltas}
    resolved = resolve_overlay(code, probe)
    if resolved.get("ok") is False:
        raise VacancyOverlayWriteError(str(resolved.get("error") or "overlay_invalid"))
    merged = merge_overlay(code, resolved.get("base"), resolved)
    if merged.get("ok") is False:
        raise VacancyOverlayWriteError(str(merged.get("error") or "overlay_merge_invalid"))
    return out


def read_vacancy_overlay_extras(extra: Mapping[str, Any] | None) -> dict[str, Any]:
    """Vacancy-only Overlay extras (not inherited pack) — human fields."""
    if not isinstance(extra, Mapping):
        return {"years_ce_min": None, "required_documents": []}
    years = extra.get("years_ce_min")
    docs = list(extra.get("extra_document_types") or [])
    overlay = extra.get(OVERLAY_CONTRACT_ID)
    if isinstance(overlay, Mapping) and isinstance(overlay.get("delta"), list):
        for row in overlay["delta"]:
            if not isinstance(row, Mapping):
                continue
            pred = row.get("predicate") if isinstance(row.get("predicate"), Mapping) else {}
            if row.get("kind") == KIND_VALUE and pred.get("qualified_code") == _YEARS_CE:
                years = pred.get("value", pred.get("minimum", years))
            if row.get("kind") == KIND_DOCUMENT:
                code = str(
                    pred.get("document_type_code")
                    or pred.get("type_code")
                    or pred.get("type")
                    or ""
                ).strip().lower()
                if code and code not in docs:
                    docs.append(code)
    if not isinstance(docs, list):
        docs = []
    docs = [str(x).strip().lower() for x in docs if str(x or "").strip()]
    return {"years_ce_min": years, "required_documents": docs}


def project_effective_requirements(
    *,
    profile: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Human effective requirements for edit UI (Profile/Pack ∪ vacancy Overlay)."""
    code = _profile_code(profile)
    base = inherited_base_requirements(code)
    vacancy = read_vacancy_overlay_extras(extra)
    base_docs = list(base.get("document_types") or [])
    extra_docs = [d for d in vacancy.get("required_documents") or [] if d not in base_docs]
    years = vacancy.get("years_ce_min")
    if years is None:
        years = base.get("years_ce_min")
    return {
        "profile_code": code,
        "years_ce_min": years,
        "inherited_years_ce_min": base.get("years_ce_min"),
        "inherited_documents": base_docs,
        "vacancy_extra_documents": extra_docs,
        "required_documents": list(dict.fromkeys([*base_docs, *extra_docs])),
        "labels": {
            "years_ce": "EU C+E experience (years)",
            "documents": {
                code: _DOC_LABELS.get(code, code.replace("_", " ").title())
                for code in dict.fromkeys([*base_docs, *extra_docs])
            },
        },
    }


# Back-compat alias used by early callers / tests.
def build_overlay_delta_from_intent(intent: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    return build_minimal_overlay_delta(profile=None, effective_intent=intent)


def read_operator_intent_from_extra(extra: Mapping[str, Any] | None) -> dict[str, Any]:
    return read_vacancy_overlay_extras(extra)


__all__ = [
    "FORBIDDEN_EXTRA_KEYS",
    "VacancyOverlayWriteError",
    "inherited_base_requirements",
    "build_minimal_overlay_delta",
    "build_overlay_delta_from_intent",
    "apply_recruitment_requirements_to_extra",
    "read_vacancy_overlay_extras",
    "read_operator_intent_from_extra",
    "project_effective_requirements",
]
