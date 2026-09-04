"""MA-3 mapping workspace envelope — schema-first, sample optional.

Does not open a fourth store. Does not cut over vocabulary (MA-4).
Does not absorb Sales convert, OCR, or CL6.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.sources_sample import (
    _publication_config,
    resolve_sample_for_profile,
)
from backend.app.field_registry.resolver import list_canonical_fields_for_scope

SCHEMA_CONFIG_KEY = "mapping_schema_v1"
OPTION_IGNORE_VALUE = "__ignore__"
CHOICE_TYPES = frozenset(
    {"select", "enum", "choice", "boolean", "reference", "multiselect", "multi_select"}
)

DRIFT_FIELD_ADDED = "field_added"
DRIFT_FIELD_REMOVED = "field_removed"
DRIFT_OPTION_ADDED = "option_added"
DRIFT_OPTION_REMOVED = "option_removed"
DRIFT_TYPE_CHANGED = "type_changed"
DRIFT_DESTINATION_INVALID = "destination_invalid"

DRIFT_HUMAN = {
    DRIFT_FIELD_ADDED: "A new question appeared on the form",
    DRIFT_FIELD_REMOVED: "This question was removed from the form — review this binding",
    DRIFT_OPTION_ADDED: "The form added an answer that is not decided",
    DRIFT_OPTION_REMOVED: "The form removed an answer that was mapped",
    DRIFT_TYPE_CHANGED: "This question’s type changed",
    DRIFT_DESTINATION_INVALID: "The HostFlow field is no longer valid",
}
TAXONOMY_DRIFT = frozenset(DRIFT_HUMAN)


def get_schema_snapshot(profile: Any) -> dict[str, Any]:
    cfg = _publication_config(profile)
    raw = cfg.get(SCHEMA_CONFIG_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def set_schema_snapshot(profile: Any, snapshot: dict[str, Any]) -> None:
    cfg = _publication_config(profile)
    cfg[SCHEMA_CONFIG_KEY] = dict(snapshot or {})
    profile.publication_config_v1 = cfg


def coerce_schema_fields(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        raw = raw.get("fields")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or item.get("key") or item.get("name") or "").strip()
        if not source:
            continue
        key = source.lower()
        if key in seen:
            continue
        seen.add(key)
        options = [
            str(opt).strip()
            for opt in (item.get("options") or [])
            if str(opt).strip()
        ]
        field_type = str(item.get("field_type") or item.get("type") or "").strip()
        if not field_type:
            field_type = "choice" if options else "text"
        out.append(
            {
                "source": source,
                "label": str(item.get("label") or source).strip() or source,
                "options": options,
                "field_type": field_type,
            }
        )
    return out


def schema_fields_from_graph_questions(questions: Any) -> list[dict[str, Any]]:
    """Graph Lead Form ``questions`` → workspace schema fields. Sample is not used."""
    if not isinstance(questions, list):
        return []
    raw: list[dict[str, Any]] = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        source = str(item.get("key") or item.get("id") or item.get("name") or "").strip()
        if not source:
            continue
        options: list[str] = []
        for opt in item.get("options") or []:
            if isinstance(opt, dict):
                val = str(opt.get("value") or opt.get("key") or opt.get("label") or "").strip()
            else:
                val = str(opt).strip()
            if val:
                options.append(val)
        field_type = str(item.get("type") or item.get("field_type") or "").strip()
        if not field_type:
            field_type = "choice" if options else "text"
        elif options and field_type.upper() in {"CUSTOM", "SELECT", "CHOICE"}:
            field_type = "choice"
        raw.append(
            {
                "source": source,
                "label": str(item.get("label") or source).strip() or source,
                "options": options,
                "field_type": field_type,
            }
        )
    return coerce_schema_fields(raw)


def fingerprint_schema_fields(fields: Sequence[Mapping[str, Any]] | None) -> str:
    """Deterministic schema fingerprint — questions, types, options. Not mapping rules."""
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in fields or []:
        if not isinstance(raw, Mapping):
            continue
        source = str(raw.get("source") or "").strip().lower()
        if not source or source in seen:
            continue
        seen.add(source)
        options = sorted(
            {str(opt).strip().lower() for opt in (raw.get("options") or []) if str(opt).strip()}
        )
        field_type = str(raw.get("field_type") or raw.get("type") or "").strip().lower()
        cleaned.append({"source": source, "field_type": field_type, "options": options})
    cleaned.sort(key=lambda row: str(row["source"]))
    blob = json.dumps(cleaned, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def build_schema_identity(
    *,
    schema_fields: list[dict[str, Any]],
    schema_source: str,
    profile: Any,
    meta_form_id: Optional[str] = None,
) -> dict[str, Any]:
    """Source schema identity for the operator workspace. Not applied-stale rules."""
    fingerprint = fingerprint_schema_fields(schema_fields) if schema_fields else None
    native_id = str(meta_form_id or "").strip() or None
    kind = "none"
    if native_id:
        kind = "meta_form"
    else:
        presentation = str(getattr(profile, "presentation_code", None) or "").strip()
        slug = str(getattr(profile, "public_slug", None) or "").strip()
        if presentation:
            native_id = presentation
            kind = "presentation"
        elif slug:
            native_id = slug
            kind = "form"
        elif schema_source and schema_source != "none":
            kind = schema_source
    if fingerprint and native_id:
        human = f"{native_id} · {fingerprint}"
    elif fingerprint:
        human = fingerprint
    else:
        human = "No schema yet"
    return {
        "kind": kind,
        "native_id": native_id,
        "fingerprint": fingerprint,
        "schema_source": schema_source,
        "question_count": len(schema_fields),
        "human": human,
    }


def _rule_index(rules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        source = str(rule.get("source") or "").strip()
        if source:
            out[source.lower()] = rule
    return out


def _binding_for_rule(rule: Optional[dict[str, Any]]) -> str:
    if not rule:
        return "unmapped"
    action = str(rule.get("action") or "").strip().lower()
    if action == "ignore":
        return "ignored"
    dest = str(rule.get("qualified_field_code") or rule.get("target") or "").strip()
    if dest:
        return "mapped"
    return "unmapped"


def _is_choice_type(field_type: str) -> bool:
    return str(field_type or "").strip().lower() in CHOICE_TYPES


def _dest_options(field: dict[str, Any]) -> list[dict[str, str]]:
    config = field.get("storage") if isinstance(field.get("storage"), dict) else {}
    raw = field.get("options") or config.get("options") or config.get("choices") or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            value = str(item.get("value") or item.get("code") or "").strip()
            label = str(item.get("label") or item.get("name") or value).strip()
            if value:
                out.append({"value": value, "label": label or value})
        else:
            value = str(item).strip()
            if value:
                out.append({"value": value, "label": value})
    return out


def _destination_lookup(
    destinations: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for dest in destinations:
        code = str(dest.get("code") or "").strip()
        if code:
            by_key[code.lower()] = dest
        for alias in dest.get("aliases") or []:
            alias_s = str(alias).strip()
            if alias_s:
                by_key.setdefault(alias_s.lower(), dest)
    return by_key


def _source_type(field_type: str, options: list[str]) -> str:
    raw = str(field_type or "").strip().lower()
    if raw:
        return raw
    return "choice" if options else "text"


def _choice_options_incomplete(
    *,
    binding: str,
    choice: bool,
    options: list[str],
    option_map: dict[str, str],
) -> bool:
    if binding != "mapped" or not options:
        return False
    if not (choice or options):
        return False
    decided = {k.lower() for k in option_map}
    return any(str(opt).lower() not in decided for opt in options)


def _human_summary(
    *,
    total: int,
    mapped: int,
    ignored: int,
    unmapped: int,
    field_added: int,
    field_removed: int,
    option_added: int,
    option_removed: int,
    type_changed: int,
    destination_invalid: int,
    incomplete_options: int,
    has_schema: bool,
) -> dict[str, Any]:
    configured = mapped + ignored
    option_drift = option_added + option_removed
    blocking = destination_invalid + type_changed
    if total <= 0 and not has_schema:
        headline = "empty_schema"
        human = "No questions yet. Mapping is still possible once the form schema is available."
        health = "needs_review"
    elif destination_invalid:
        headline = DRIFT_DESTINATION_INVALID
        human = (
            f"A HostFlow field is no longer valid. Check {destination_invalid} question"
            f"{'s' if destination_invalid != 1 else ''}."
        )
        health = "invalid"
    elif type_changed:
        headline = DRIFT_TYPE_CHANGED
        human = (
            f"A question’s type changed. Check {type_changed} question"
            f"{'s' if type_changed != 1 else ''}."
        )
        health = "invalid"
    elif option_drift:
        headline = "option_drift"
        human = (
            f"The form changed. Check {option_drift} answer"
            f"{'s' if option_drift != 1 else ''} before automatic evaluation continues."
        )
        health = "needs_review"
    elif field_removed:
        headline = DRIFT_FIELD_REMOVED
        human = (
            f"The form removed {field_removed} question"
            f"{'s' if field_removed != 1 else ''}. Review those bindings."
        )
        health = "needs_review"
    elif field_added:
        headline = DRIFT_FIELD_ADDED
        human = (
            f"Needs a check — {field_added} new question"
            f"{'s' if field_added != 1 else ''} appeared on the form"
        )
        health = "needs_review"
    elif unmapped or incomplete_options:
        pending = unmapped or incomplete_options
        headline = "needs_check"
        human = f"Needs a check — {pending} question{'s' if pending != 1 else ''} to set"
        health = "needs_review"
    else:
        headline = "all_set"
        human = f"All set — {configured} of {total} questions"
        health = "valid"
    pending = unmapped or incomplete_options
    if headline == "needs_check":
        n = max(pending, 1)
        cta = "1 field is not configured" if n == 1 else f"{n} fields are not configured"
    elif headline in {"empty_schema", "all_set"}:
        cta = "Open Mapping"
    else:
        cta = "Check Mapping"
    return {
        "headline": headline,
        "configured_count": configured,
        "total_count": total,
        "mapped_count": mapped,
        "ignored_count": ignored,
        "unmapped_count": unmapped,
        "new_question_count": field_added,
        "field_added_count": field_added,
        "field_removed_count": field_removed,
        "option_added_count": option_added,
        "option_removed_count": option_removed,
        "type_changed_count": type_changed,
        "destination_invalid_count": destination_invalid,
        "option_drift_count": option_drift,
        "incomplete_option_count": incomplete_options,
        "human": human,
        "cta": cta,
        "contract_health": health,
        "blocking_drift_count": blocking,
    }


def _sample_by_source(sample: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in sample.get("fields") or []:
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("source") or "").strip().lower()
        value = str(raw.get("sample_value_masked") or "").strip()
        if source and value:
            out[source] = value
    return out


def _sample_evidence(
    *,
    sample: dict[str, Any],
    rows: list[dict[str, Any]],
    error: Optional[str] = None,
) -> dict[str, Any]:
    question_count = sum(1 for row in rows if row.get("in_schema"))
    filled_count = sum(1 for row in rows if str(row.get("sample_example") or "").strip())
    return {
        "present": bool(sample.get("has_sample")),
        "source": str(sample.get("sample_source") or "none") or "none",
        "captured_at": sample.get("captured_at"),
        "lead_id": sample.get("lead_id"),
        "capture_next_until": sample.get("capture_next_until"),
        "question_count": question_count,
        "filled_count": filled_count,
        "error": error,
    }


async def _destinations_for_tenant(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> list[dict[str, Any]]:
    try:
        rows = await list_canonical_fields_for_scope(db, tenant_id=str(tenant_id))
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("qualified_code") or "").strip()
        if not code:
            continue
        status = str(row.get("status") or "active").strip().lower()
        if status and status not in {"active", "published", ""}:
            continue
        label = str(row.get("name") or row.get("label_key") or code.split(".")[-1]).strip()
        field_type = str(row.get("field_type") or "string").strip() or "string"
        aliases = [str(a).strip() for a in (row.get("legacy_aliases") or []) if str(a).strip()]
        out.append(
            {
                "code": code,
                "label": label or code,
                "field_type": field_type,
                "choice": _is_choice_type(field_type),
                "aliases": aliases,
                "options": _dest_options(row),
            }
        )
    out.sort(key=lambda d: str(d.get("label") or "").lower())
    return out


async def _schema_from_presentation(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile: Any,
) -> list[dict[str, Any]]:
    entity_code = str(getattr(profile, "entity_profile_code", None) or "").strip()
    presentation_code = str(getattr(profile, "presentation_code", None) or "").strip()
    if not entity_code or not presentation_code:
        return []
    try:
        from backend.app.entity_profile.presentation_runtime import (
            resolve_form_presentation_for_intake_source,
        )

        view = await resolve_form_presentation_for_intake_source(
            db,
            tenant_id=str(tenant_id),
            intake_source_profile_id=str(profile.id),
            presentation_code=presentation_code,
        )
    except Exception:
        return []
    fields: list[dict[str, Any]] = []
    for row in view.get("fields") or []:
        if not isinstance(row, dict):
            continue
        source = str(row.get("qualified_code") or "").strip()
        if not source:
            continue
        options: list[str] = []
        embedded = row.get("field") if isinstance(row.get("field"), dict) else {}
        raw_opts = embedded.get("options") or embedded.get("choices") or []
        if isinstance(raw_opts, list):
            for opt in raw_opts:
                if isinstance(opt, dict):
                    val = str(opt.get("value") or opt.get("label") or "").strip()
                else:
                    val = str(opt).strip()
                if val:
                    options.append(val)
        field_type = str(embedded.get("field_type") or embedded.get("type") or "").strip()
        if not field_type:
            field_type = "choice" if options else "text"
        fields.append(
            {
                "source": source,
                "label": str(row.get("label") or source).strip() or source,
                "options": options,
                "field_type": field_type,
            }
        )
    return fields


def build_workspace_rows(
    *,
    schema_fields: list[dict[str, Any]],
    mapping_rules: list[dict[str, Any]],
    sample_by_source: dict[str, str],
    destinations: list[dict[str, Any]],
    has_schema: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rules = _rule_index(mapping_rules)
    dest_by_key = _destination_lookup(destinations)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    has_saved_decisions = any(
        _binding_for_rule(rule) in {"mapped", "ignored"} for rule in mapping_rules
    )

    def _append(
        source: str,
        label: str,
        options: list[str],
        *,
        in_schema: bool,
        field_type: str = "",
    ) -> None:
        key = source.lower()
        if key in seen:
            return
        seen.add(key)
        rule = rules.get(key)
        binding = _binding_for_rule(rule)
        dest_code = ""
        option_map: dict[str, str] = {}
        if rule:
            dest_code = str(rule.get("qualified_field_code") or rule.get("target") or "").strip()
            raw_map = rule.get("option_map")
            if isinstance(raw_map, dict):
                option_map = {
                    str(k): str(v)
                    for k, v in raw_map.items()
                    if str(k).strip() and str(v).strip()
                }
        dest = dest_by_key.get(dest_code.lower()) if dest_code else None
        dest_type = str((dest or {}).get("field_type") or "")
        dest_label = str((dest or {}).get("label") or dest_code)
        dest_options = list((dest or {}).get("options") or [])
        source_type = _source_type(field_type, options)
        source_choice = _is_choice_type(source_type) or bool(options)
        dest_choice = bool((dest or {}).get("choice")) or _is_choice_type(dest_type)
        choice = dest_choice or source_choice
        drift: Optional[str] = None
        if not in_schema and has_schema:
            drift = DRIFT_FIELD_REMOVED
        elif in_schema and binding == "unmapped" and has_saved_decisions:
            drift = DRIFT_FIELD_ADDED
        elif dest_code and destinations and dest is None:
            drift = DRIFT_DESTINATION_INVALID
        elif dest and binding == "mapped" and source_choice != dest_choice:
            drift = DRIFT_TYPE_CHANGED
        elif binding == "mapped" and options:
            decided_opts = {k.lower() for k in option_map}
            schema_opts = {o.lower() for o in options}
            extra_decisions = decided_opts - schema_opts
            missing_decisions = schema_opts - decided_opts
            if extra_decisions:
                drift = DRIFT_OPTION_REMOVED
            elif missing_decisions and decided_opts:
                drift = DRIFT_OPTION_ADDED
        incomplete = _choice_options_incomplete(
            binding=binding,
            choice=choice,
            options=options,
            option_map=option_map,
        )
        rows.append(
            {
                "source": source,
                "label": label,
                "options": options,
                "field_type": source_type,
                "sample_example": sample_by_source.get(key) or None,
                "binding": binding,
                "destination_code": dest_code or None,
                "destination_label": dest_label if dest_code else None,
                "destination_type": dest_type or None,
                "choice": choice,
                "option_map": option_map,
                "destination_options": dest_options,
                "in_schema": in_schema,
                "historical": not in_schema,
                "drift": drift,
                "drift_human": DRIFT_HUMAN.get(drift or ""),
                "incomplete_options": incomplete,
            }
        )

    for field in schema_fields:
        _append(
            str(field.get("source") or ""),
            str(field.get("label") or field.get("source") or ""),
            list(field.get("options") or []),
            in_schema=True,
            field_type=str(field.get("field_type") or ""),
        )
    for rule in mapping_rules:
        if not isinstance(rule, dict):
            continue
        source = str(rule.get("source") or "").strip()
        if source:
            _append(source, source, [], in_schema=False)

    mapped = sum(1 for r in rows if r["binding"] == "mapped")
    ignored = sum(1 for r in rows if r["binding"] == "ignored")
    unmapped = sum(1 for r in rows if r["binding"] == "unmapped")
    summary = _human_summary(
        total=len(rows),
        mapped=mapped,
        ignored=ignored,
        unmapped=unmapped,
        field_added=sum(1 for r in rows if r.get("drift") == DRIFT_FIELD_ADDED),
        field_removed=sum(1 for r in rows if r.get("drift") == DRIFT_FIELD_REMOVED),
        option_added=sum(1 for r in rows if r.get("drift") == DRIFT_OPTION_ADDED),
        option_removed=sum(1 for r in rows if r.get("drift") == DRIFT_OPTION_REMOVED),
        type_changed=sum(1 for r in rows if r.get("drift") == DRIFT_TYPE_CHANGED),
        destination_invalid=sum(1 for r in rows if r.get("drift") == DRIFT_DESTINATION_INVALID),
        incomplete_options=sum(1 for r in rows if r.get("incomplete_options")),
        has_schema=has_schema,
    )
    return rows, summary


def _canonical_example_out(
    *,
    example_in: str,
    option_map: dict[str, str],
    dest_options: list[dict[str, str]],
    choice: bool,
) -> str:
    """Return a canonical example, never a raw provider label for choice fields."""
    mapped = ""
    if example_in and option_map:
        mapped = str(option_map.get(example_in) or "")
        if not mapped:
            for key, val in option_map.items():
                if str(key).lower() == example_in.lower():
                    mapped = str(val)
                    break
    if mapped and mapped != OPTION_IGNORE_VALUE:
        for opt in dest_options:
            if str(opt.get("value") or "").strip().lower() == mapped.lower():
                return str(opt.get("label") or mapped).strip() or mapped
        return mapped
    if choice:
        return ""
    return example_in


def build_projection(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("binding") != "mapped":
            continue
        dest_label = str(row.get("destination_label") or row.get("destination_code") or "").strip()
        if not dest_label:
            continue
        example_in = str(row.get("sample_example") or "").strip()
        option_map = row.get("option_map") if isinstance(row.get("option_map"), dict) else {}
        dest_options = list(row.get("destination_options") or [])
        choice = bool(row.get("choice")) or bool(row.get("options"))
        example_out = _canonical_example_out(
            example_in=example_in,
            option_map=option_map,
            dest_options=dest_options,
            choice=choice,
        )
        if example_out:
            sentence = f"The next application will write {dest_label} = {example_out}"
        else:
            sentence = f"The next application will write {dest_label}"
        out.append(
            {
                "source": row.get("source"),
                "destination_label": dest_label,
                "example_in": example_in or None,
                "example_out": example_out or None,
                "sentence": sentence,
            }
        )
    return out


async def _schema_for_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile: Any,
    mapping_rules: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str, bool]:
    snapshot_fields = coerce_schema_fields(get_schema_snapshot(profile))
    schema_source = "snapshot" if snapshot_fields else "none"
    schema_fields = list(snapshot_fields)
    if not schema_fields:
        presented = await _schema_from_presentation(
            db, tenant_id=tenant_id, profile=profile
        )
        if presented:
            schema_fields = presented
            schema_source = "presentation"
    has_schema = schema_source in {"snapshot", "presentation"}
    if not schema_fields and mapping_rules:
        schema_source = "rules"
    return schema_fields, schema_source, has_schema


def assess_mapping(
    *,
    schema_fields: list[dict[str, Any]],
    mapping_rules: list[dict[str, Any]],
    destinations: list[dict[str, Any]],
    has_schema: bool,
) -> dict[str, Any]:
    """Canonical mapping assessment — same object the workspace summary uses."""
    _rows, summary = build_workspace_rows(
        schema_fields=schema_fields,
        mapping_rules=mapping_rules,
        sample_by_source={},
        destinations=destinations,
        has_schema=has_schema,
    )
    return summary


async def mapping_assessment_for_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile: Any,
    mapping_rules: list[dict[str, Any]],
    destinations: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    schema_fields, _schema_source, has_schema = await _schema_for_profile(
        db,
        tenant_id=tenant_id,
        profile=profile,
        mapping_rules=mapping_rules,
    )
    dests = (
        destinations
        if destinations is not None
        else await _destinations_for_tenant(db, tenant_id=tenant_id)
    )
    return assess_mapping(
        schema_fields=schema_fields,
        mapping_rules=mapping_rules,
        destinations=dests,
        has_schema=has_schema,
    )


async def workspace_envelope(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile: Any,
    mapping_rules: list[dict[str, Any]],
    meta_form_id: Optional[str] = None,
) -> dict[str, Any]:
    schema_fields, schema_source, has_schema = await _schema_for_profile(
        db,
        tenant_id=tenant_id,
        profile=profile,
        mapping_rules=mapping_rules,
    )
    destinations = await _destinations_for_tenant(db, tenant_id=tenant_id)
    sample = await resolve_sample_for_profile(
        db,
        tenant_id=str(tenant_id),
        profile=profile,
        meta_form_id=meta_form_id,
        mapping_rules=mapping_rules,
    )
    sample_by_source = _sample_by_source(sample)
    rows, summary = build_workspace_rows(
        schema_fields=schema_fields,
        mapping_rules=mapping_rules,
        sample_by_source=sample_by_source,
        destinations=destinations,
        has_schema=has_schema,
    )
    return {
        "schema_source": schema_source,
        "has_schema": has_schema,
        "has_sample": bool(sample.get("has_sample")),
        "schema_fields": rows,
        "summary": summary,
        "contract_health": summary.get("contract_health"),
        "destinations": destinations,
        "projection": build_projection(rows),
        "schema_identity": build_schema_identity(
            schema_fields=schema_fields,
            schema_source=schema_source,
            profile=profile,
            meta_form_id=meta_form_id,
        ),
        "sample_evidence": _sample_evidence(sample=sample, rows=rows),
    }


__all__ = [
    "SCHEMA_CONFIG_KEY",
    "OPTION_IGNORE_VALUE",
    "DRIFT_FIELD_ADDED",
    "DRIFT_FIELD_REMOVED",
    "DRIFT_OPTION_ADDED",
    "DRIFT_OPTION_REMOVED",
    "DRIFT_TYPE_CHANGED",
    "DRIFT_DESTINATION_INVALID",
    "DRIFT_HUMAN",
    "TAXONOMY_DRIFT",
    "workspace_envelope",
    "coerce_schema_fields",
    "set_schema_snapshot",
    "get_schema_snapshot",
    "fingerprint_schema_fields",
    "schema_fields_from_graph_questions",
    "build_schema_identity",
    "assess_mapping",
    "mapping_assessment_for_profile",
    "build_workspace_rows",
    "build_projection",
]
