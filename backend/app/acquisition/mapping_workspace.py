"""MA-3 mapping workspace envelope — schema-first, sample optional.

Does not open a fourth store. Does not cut over vocabulary (MA-4).
Does not absorb Sales convert, OCR, or CL6.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.sources_sample import (
    _publication_config,
    build_discovered_fields,
    get_discovery_state,
)
from backend.app.field_registry.resolver import list_canonical_fields_for_scope

SCHEMA_CONFIG_KEY = "mapping_schema_v1"
OPTION_IGNORE_VALUE = "__ignore__"
CHOICE_TYPES = frozenset(
    {"select", "enum", "choice", "boolean", "reference", "multiselect", "multi_select"}
)


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
        out.append(
            {
                "source": source,
                "label": str(item.get("label") or source).strip() or source,
                "options": options,
            }
        )
    return out


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


def _human_summary(
    *,
    total: int,
    mapped: int,
    ignored: int,
    unmapped: int,
    new_questions: int,
    option_drift: int,
    has_schema: bool,
) -> dict[str, Any]:
    configured = mapped + ignored
    if total <= 0 and not has_schema:
        headline = "empty_schema"
        human = "No questions yet. Mapping is still possible once the form schema is available."
    elif option_drift:
        headline = "option_drift"
        human = (
            f"The form changed. Check {option_drift} answer"
            f"{'s' if option_drift != 1 else ''} before automatic evaluation continues."
        )
    elif new_questions or unmapped:
        pending = new_questions or unmapped
        headline = "needs_check"
        human = f"Needs a check — {pending} question{'s' if pending != 1 else ''} to set"
    else:
        headline = "all_set"
        human = f"All set — {configured} of {total} questions"
    health = "valid"
    if option_drift:
        health = "needs_review"
    elif unmapped or new_questions:
        health = "needs_review" if has_schema or total else "needs_review"
    if total == 0 and not has_schema:
        health = "needs_review"
    return {
        "headline": headline,
        "configured_count": configured,
        "total_count": total,
        "mapped_count": mapped,
        "ignored_count": ignored,
        "unmapped_count": unmapped,
        "new_question_count": new_questions,
        "option_drift_count": option_drift,
        "human": human,
        "contract_health": health,
    }


def _sample_examples(
    *,
    profile: Any,
    mapping_rules: list[dict[str, Any]],
) -> dict[str, str]:
    discovery = get_discovery_state(profile)
    payload = discovery.get("sample_payload")
    if not isinstance(payload, dict) or not payload:
        return {}
    fields = build_discovered_fields(raw_payload=payload, mapping_rules=mapping_rules)
    return {
        f.source.lower(): f.sample_value_masked
        for f in fields
        if f.sample_value_masked
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
        fields.append(
            {
                "source": source,
                "label": str(row.get("label") or source).strip() or source,
                "options": options,
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

    def _append(source: str, label: str, options: list[str], *, in_schema: bool) -> None:
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
        choice = bool((dest or {}).get("choice")) or _is_choice_type(dest_type) or bool(options)
        drift: Optional[str] = None
        if in_schema and binding == "unmapped":
            drift = "new_question"
        elif not in_schema and has_schema:
            drift = "missing_from_form"
        elif dest_code and destinations and dest is None:
            drift = "destination_invalid"
        elif binding == "mapped" and options:
            decided_opts = {k.lower() for k in option_map}
            schema_opts = {o.lower() for o in options}
            if schema_opts - decided_opts:
                drift = "changed_options"
            elif decided_opts - schema_opts:
                drift = "missing_option"
        rows.append(
            {
                "source": source,
                "label": label,
                "options": options,
                "sample_example": sample_by_source.get(key) or None,
                "binding": binding,
                "destination_code": dest_code or None,
                "destination_label": dest_label if dest_code else None,
                "destination_type": dest_type or None,
                "choice": choice,
                "option_map": option_map,
                "destination_options": dest_options,
                "in_schema": in_schema,
                "drift": drift,
            }
        )

    for field in schema_fields:
        _append(
            str(field.get("source") or ""),
            str(field.get("label") or field.get("source") or ""),
            list(field.get("options") or []),
            in_schema=True,
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
    new_questions = sum(1 for r in rows if r.get("drift") == "new_question")
    option_drift = sum(
        1
        for r in rows
        if r.get("drift") in {"changed_options", "missing_option", "destination_invalid"}
    )
    summary = _human_summary(
        total=len(rows),
        mapped=mapped,
        ignored=ignored,
        unmapped=unmapped,
        new_questions=new_questions,
        option_drift=option_drift,
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


async def workspace_envelope(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile: Any,
    mapping_rules: list[dict[str, Any]],
) -> dict[str, Any]:
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
    destinations = await _destinations_for_tenant(db, tenant_id=tenant_id)
    sample_by_source = _sample_examples(profile=profile, mapping_rules=mapping_rules)
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
        "has_sample": bool(sample_by_source),
        "schema_fields": rows,
        "summary": summary,
        "contract_health": summary.get("contract_health"),
        "destinations": destinations,
        "projection": build_projection(rows),
    }


__all__ = [
    "SCHEMA_CONFIG_KEY",
    "OPTION_IGNORE_VALUE",
    "workspace_envelope",
    "coerce_schema_fields",
    "set_schema_snapshot",
    "get_schema_snapshot",
    "build_workspace_rows",
    "build_projection",
]
