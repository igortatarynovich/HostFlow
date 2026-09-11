"""Canonical fact occupancy — one representation, one read path.

Decision consumers (RSO package projection, ESO-1…2, readiness/slots) must use
these helpers. Transport bags (``lead.normalized``, ``field_answers``, Meta
payload, CSV) are never decision authority.

Contract: ``docs/specs/tasks/canonical-facts-completeness.md``.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, MutableMapping

CITIZENSHIP_QUALIFIED = "platform.identity.citizenship"
YEARS_CE_QUALIFIED = "recruitment.candidate.experience.years_ce"


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _upper_alpha2(value: Any) -> str:
    code = _text(value).upper()
    return code if len(code) == 2 and code.isalpha() else ""


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _candidate_personal(candidate: Any) -> dict[str, Any]:
    if candidate is None:
        return {}
    if hasattr(candidate, "_get_personal_data"):
        try:
            pd = candidate._get_personal_data()
            return _as_mapping(pd)
        except Exception:
            pass
    return _as_mapping(getattr(candidate, "personal_data", None))


def _candidate_extra(candidate: Any) -> dict[str, Any]:
    if candidate is None:
        return {}
    if hasattr(candidate, "_get_extra"):
        try:
            return _as_mapping(candidate._get_extra())
        except Exception:
            pass
    raw = getattr(candidate, "extra", None)
    if isinstance(raw, str):
        try:
            return _as_mapping(json.loads(raw or "{}"))
        except Exception:
            return {}
    return _as_mapping(raw)


def _nested_get(data: Mapping[str, Any], *path: str) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(key)
    return cur


def read_citizenship_alpha2(source: Any) -> str:
    """Single read path for citizenship (ISO alpha-2).

    * Candidate: ``personal_data.citizenship``; strangler ``extra.citizenship`` only.
    * Package / mapping: ``person.identity_facts.citizenship`` only.

    Never reads ``nationality``, ``country``, ``country_code``, or ``field_answers``.
    """
    if source is None:
        return ""
    if isinstance(source, Mapping):
        person = source.get("person")
        if isinstance(person, Mapping):
            identity = person.get("identity_facts")
            if isinstance(identity, Mapping):
                code = _upper_alpha2(identity.get("citizenship"))
                if code:
                    return code
            # Package projection may mirror at person.citizenship after ensure —
            # only the citizenship key, never nationality.
            code = _upper_alpha2(person.get("citizenship"))
            if code:
                return code
        identity = source.get("identity_facts")
        if isinstance(identity, Mapping):
            return _upper_alpha2(identity.get("citizenship"))
        return _upper_alpha2(source.get("citizenship"))

    personal = _candidate_personal(source)
    code = _upper_alpha2(personal.get("citizenship"))
    if code:
        return code
    # Leftover Candidate occupancy (not transport): promote-read only.
    extra = _candidate_extra(source)
    return _upper_alpha2(extra.get("citizenship"))


def read_years_ce(source: Any) -> Any:
    """Single read path for years CE.

    * Candidate: ``extra.experience.years_ce``; strangler flat ``experience_eu_years`` / ``years_ce``.
    * Package: ``recruitment_facts.years_ce`` or mapping with qualified key.
    """
    if source is None:
        return None
    if isinstance(source, Mapping):
        if YEARS_CE_QUALIFIED in source and source.get(YEARS_CE_QUALIFIED) not in (None, ""):
            return source.get(YEARS_CE_QUALIFIED)
        facts = source.get("recruitment_facts")
        if isinstance(facts, Mapping) and facts.get("years_ce") not in (None, ""):
            return facts.get("years_ce")
        nested = _nested_get(source, "experience", "years_ce")
        if nested not in (None, ""):
            return nested
        return None

    extra = _candidate_extra(source)
    nested = _nested_get(extra, "experience", "years_ce")
    if nested not in (None, ""):
        return nested
    # Leftover flat keys on Candidate.extra (not lead.normalized).
    for key in ("experience_eu_years", "years_ce"):
        if extra.get(key) not in (None, ""):
            return extra.get(key)
    return None


def project_identity_facts_from_candidate(candidate: Any) -> dict[str, Any]:
    """Projection for ``ready_for_employment.v1`` person.identity_facts."""
    personal = _candidate_personal(candidate)
    out: dict[str, Any] = {}
    citizenship = read_citizenship_alpha2(candidate)
    if citizenship:
        out["citizenship"] = citizenship
    for key in ("first_name", "last_name"):
        val = _text(getattr(candidate, key, None) or personal.get(key))
        if val:
            out[key] = val
    return out


def occupy_citizenship_on_personal(
    personal: MutableMapping[str, Any],
    *,
    value: Any,
) -> str:
    """Write citizenship into the canonical personal_data path. Returns alpha-2 or ''."""
    code = _upper_alpha2(value)
    if not code:
        return ""
    personal["citizenship"] = code
    return code


def occupy_years_ce_on_extra(extra: MutableMapping[str, Any], *, value: Any) -> Any:
    """Write years CE into ``extra.experience.years_ce``."""
    if value in (None, ""):
        return None
    experience = extra.get("experience")
    if not isinstance(experience, dict):
        experience = {}
        extra["experience"] = experience
    experience["years_ce"] = value
    return value


def set_nested_extra_path(extra: MutableMapping[str, Any], dotted: str, value: Any) -> None:
    """Set ``a.b.c`` under extra dict."""
    parts = [p for p in str(dotted).split(".") if p]
    if not parts:
        return
    cur: MutableMapping[str, Any] = extra
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


__all__ = [
    "CITIZENSHIP_QUALIFIED",
    "YEARS_CE_QUALIFIED",
    "read_citizenship_alpha2",
    "read_years_ce",
    "project_identity_facts_from_candidate",
    "occupy_citizenship_on_personal",
    "occupy_years_ce_on_extra",
    "set_nested_extra_path",
]
