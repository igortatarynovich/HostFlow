"""Execute intake mapping onto Candidate fields at Lead → Candidate conversion.

Rule: if an answer has an executable mapping to a Candidate destination, copy
it at convert onto the matching candidate column / extra / personal field.
Unmapped answers stay on the Lead (``normalized.field_answers``). They must
not be copied onto the candidate card as a questionnaire dump.

This is not a conversion-specific field whitelist. Destinations come from the
intake field registry (qualified codes) plus compact ``mapping_applied_v1``
rules stamped at ingest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from backend.app.acquisition.mapping_applied_stamp import read_mapping_applied_stamp
from backend.app.field_registry.intake_mapping import (
    LEAD_INTAKE_QUALIFIED_TO_NORMALIZED,
    resolve_intake_mapping_target,
)

# qualified_code → where to write on the candidate payload.
# Lead-only hints (recruitment.lead.*) are intentionally omitted.
CANDIDATE_WRITE_BY_QUALIFIED: dict[str, dict[str, str]] = {
    "recruitment.candidate.first_name": {"column": "first_name"},
    "recruitment.candidate.last_name": {"column": "last_name"},
    "recruitment.candidate.contacts.phone": {"column": "phone", "contacts": "phone"},
    "recruitment.candidate.contacts.phone_country_code": {
        "column": "phone_country_code",
        "contacts": "phone_country_code",
    },
    "recruitment.candidate.contacts.email": {"column": "email", "contacts": "email"},
    "recruitment.candidate.contacts.preferred_messenger": {
        "extra": "preferred_contact",
        "contacts": "preferred_messenger",
    },
    "platform.identity.citizenship": {"extra": "citizenship", "personal": "citizenship"},
    "platform.identity.address": {"extra": "address", "personal": "address"},
    "platform.identity.birth_date": {"personal": "birth_date"},
    "recruitment.candidate.personal.residency_status": {
        "extra": "poland_stay_basis",
        "personal": "residency_status",
    },
    "recruitment.candidate.personal.current_location": {
        "extra": "current_location",
        "personal": "current_location",
    },
    "recruitment.candidate.personal.in_poland": {
        "extra": "in_poland",
        "personal": "in_poland",
    },
    "recruitment.candidate.experience.years_ce": {"extra": "experience_eu_years"},
    "recruitment.candidate.experience.intl_experience": {"extra": "intl_experience"},
}

_LEAD_ONLY_TARGETS = frozenset(
    {
        "vacancy_hint",
        "vacancy_id",
        "vacancy_id_hint",
        "company_id",
        "company_id_hint",
        "company_name_hint",
    }
)

_SKIP_ANSWER_NAMES = frozenset(
    {
        "id",
        "lead_id",
        "leadgen_id",
        "external_id",
        "ad_id",
        "adset_id",
        "adgroup_id",
        "form_id",
        "created_time",
        "campaign_id",
        "campaign_name",
        "page_id",
        "platform",
        "is_organic",
        "inbox_url",
        "retailer_item_id",
    }
)


@dataclass
class ConversionFieldWrite:
    columns: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
    personal: dict[str, Any] = field(default_factory=dict)
    contacts: dict[str, Any] = field(default_factory=dict)
    mapped_sources: list[str] = field(default_factory=list)


def compact_executable_rules(rules: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    """Compact mapping rules stored on ``mapping_applied_v1`` for convert-time execute."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in rules or []:
        if not isinstance(raw, Mapping):
            continue
        if str(raw.get("action") or "").strip().lower() == "ignore":
            continue
        source = str(raw.get("source") or "").strip()
        qualified = str(raw.get("qualified_field_code") or "").strip() or None
        target = resolve_intake_mapping_target(dict(raw))
        if not source or (not qualified and not target):
            continue
        if str(target or "") in _LEAD_ONLY_TARGETS:
            continue
        if qualified and qualified.startswith("recruitment.lead."):
            continue
        key = (source.lower(), (qualified or target or "").lower())
        if key in seen:
            continue
        seen.add(key)
        label = (
            str(raw.get("label") or raw.get("source_label") or raw.get("question") or "").strip()
            or None
        )
        item: dict[str, Any] = {"source": source}
        if qualified:
            item["qualified_field_code"] = qualified
        if target:
            item["normalized_target"] = target
        if label:
            item["label"] = label
        out.append(item)
    return out


def _coerce_scalar(value: Any) -> Any:
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        lowered = s.lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
        return s
    if isinstance(value, (list, tuple)):
        items = [str(v).strip() for v in value if v is not None and str(v).strip()]
        if not items:
            return None
        if len(items) == 1:
            return _coerce_scalar(items[0])
        return ", ".join(items)
    return value


def _value_from_normalized(normalized: Mapping[str, Any], target: str) -> Any:
    if not target:
        return None
    if "." in target:
        cur: Any = normalized
        for part in target.split("."):
            if not isinstance(cur, Mapping):
                return None
            cur = cur.get(part)
        return _coerce_scalar(cur)
    return _coerce_scalar(normalized.get(target))


def _is_skippable_source(name: str) -> bool:
    key = name.strip().lower()
    if not key:
        return True
    return key in _SKIP_ANSWER_NAMES or key.startswith("utm")


def _value_from_field_answers(normalized: Mapping[str, Any], source: str) -> Any:
    raw = normalized.get("field_answers")
    if not isinstance(raw, list):
        return None
    want = source.strip().lower()
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip().lower()
        if name != want:
            continue
        return _coerce_scalar(item.get("values"))
    return None


def _apply_write(
    dest: Mapping[str, str],
    value: Any,
    out: ConversionFieldWrite,
) -> None:
    if value is None or value == "":
        return
    col = dest.get("column")
    if col and col not in out.columns:
        out.columns[col] = value
    extra = dest.get("extra")
    if extra and extra not in out.extra:
        out.extra[extra] = value
    personal = dest.get("personal")
    if personal and personal not in out.personal:
        out.personal[personal] = value
    contacts = dest.get("contacts")
    if contacts and contacts not in out.contacts:
        out.contacts[contacts] = value


def _write_qualified(qualified: str, value: Any, out: ConversionFieldWrite) -> bool:
    if value is None or value == "":
        return False
    dest = CANDIDATE_WRITE_BY_QUALIFIED.get(qualified)
    if dest:
        _apply_write(dest, value, out)
        return True
    if qualified.startswith("recruitment.candidate.") or qualified.startswith("platform.identity."):
        key = qualified.rsplit(".", 1)[-1]
        if key and key not in out.extra:
            out.extra[key] = value
        return True
    return False


def _executable_rules_from_normalized(normalized: Mapping[str, Any]) -> list[dict[str, Any]]:
    stamp = read_mapping_applied_stamp(normalized)
    raw = stamp.get("executable_rules")
    if isinstance(raw, list) and raw:
        return [dict(r) for r in raw if isinstance(r, Mapping)]
    envelope = normalized.get("ingest_envelope_v1")
    if isinstance(envelope, Mapping):
        mapping_result = envelope.get("mapping_result")
        if isinstance(mapping_result, Mapping):
            rules = mapping_result.get("rules")
            if isinstance(rules, list):
                return compact_executable_rules(rules)
    return []


def apply_executable_intake_mapping(normalized: Mapping[str, Any] | None) -> ConversionFieldWrite:
    """Map executable intake answers onto candidate columns / extra / personal."""
    n = dict(normalized) if isinstance(normalized, Mapping) else {}
    out = ConversionFieldWrite()

    for qualified, target in LEAD_INTAKE_QUALIFIED_TO_NORMALIZED.items():
        if qualified.startswith("recruitment.lead."):
            continue
        value = _value_from_normalized(n, target)
        if _write_qualified(qualified, value, out):
            out.mapped_sources.append(target)

    for rule in _executable_rules_from_normalized(n):
        source = str(rule.get("source") or "").strip()
        if source and _is_skippable_source(source):
            continue
        qualified = str(rule.get("qualified_field_code") or "").strip()
        target = str(rule.get("normalized_target") or rule.get("target") or "").strip()
        value = _value_from_normalized(n, target) if target else None
        if value is None and source:
            value = _value_from_field_answers(n, source)
        wrote = False
        if qualified:
            wrote = _write_qualified(qualified, value, out)
        elif target and target not in _LEAD_ONLY_TARGETS and value not in (None, ""):
            if target not in out.extra and target not in out.columns:
                out.extra[target] = value
                wrote = True
        if wrote and source:
            out.mapped_sources.append(source)

    return out


def attach_field_answer_labels(
    field_answers: list[dict[str, Any]],
    rules: Sequence[Mapping[str, Any]] | None,
) -> dict[str, str]:
    """Stamp human labels onto ``field_answers`` from mapping rules. Returns name→label."""
    labels: dict[str, str] = {}
    for rule in rules or []:
        if not isinstance(rule, Mapping):
            continue
        source = str(rule.get("source") or "").strip()
        label = str(rule.get("label") or rule.get("source_label") or rule.get("question") or "").strip()
        if not source:
            continue
        if not label and _looks_like_human_question(source):
            label = source.replace("_", " ")
        if label:
            labels[source.lower()] = label
    for row in field_answers:
        name = str(row.get("name") or "").strip()
        existing = str(row.get("label") or "").strip()
        if existing:
            labels[name.lower()] = existing
            continue
        label = labels.get(name.lower())
        if not label and _looks_like_human_question(name):
            label = name.replace("_", " ").strip()
        if label:
            row["label"] = label
            labels[name.lower()] = label
    return labels


def _looks_like_human_question(raw: str) -> bool:
    s = str(raw or "").strip()
    if not s:
        return False
    if " " in s or "?" in s:
        return True
    if any(ord(ch) > 127 for ch in s):
        return True
    return False


__all__ = [
    "CANDIDATE_WRITE_BY_QUALIFIED",
    "ConversionFieldWrite",
    "apply_executable_intake_mapping",
    "attach_field_answer_labels",
    "compact_executable_rules",
]
