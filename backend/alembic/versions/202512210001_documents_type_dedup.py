"""Deduplicate document types and align canonical codes.

Revision ID: 202512210001_documents_type_dedup
Revises: 202512200001_meta_leads_admin_console
Create Date: 2025-12-21 10:15:00.000000
"""

from __future__ import annotations

import json
from typing import Any, Dict

import sqlalchemy as sa
from alembic import op

revision: str = "202512210001_documents_type_dedup"
down_revision: str | None = "202512200001_meta_leads_admin_console"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


_TYPE_MAPPING: Dict[str, str] = {
    "code95": "qualification_code95",
    "code_95": "qualification_code95",
    "insurance_a1": "insurance",
    "employer_insurance": "insurance",
    "work_assignment": "assignment",
    "employment_contract": "contract",
    "bhp_instruction": "bhp",
    "accommodation_declaration": "accommodation",
    "tachograph_exchange": "tachograph_card",
}


_NAME_OVERRIDES: Dict[str, str] = {
    "qualification_code95": "Qualification code 95",
    "insurance": "Insurance",
    "assignment": "Work assignment",
    "contract": "Employment contract",
    "bhp": "BHP instruction",
    "accommodation": "Accommodation declaration",
    "tachograph_card": "Tachograph card",
}


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        return any(row[1] == column for row in rows)
    row = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :t
              AND column_name = :c
            LIMIT 1
            """
        ),
        {"t": table, "c": column},
    ).fetchone()
    return row is not None


def _normalize_code(code: str | None) -> str:
    raw = (code or "").strip()
    if not raw:
        return "other"
    return _TYPE_MAPPING.get(raw, raw)


def _load_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:  # pragma: no cover - defensive for bad data
        return value


def upgrade() -> None:  # noqa: D401 - Alembic entrypoint
    bind = op.get_bind()

    documents_table = sa.table(
        "documents",
        sa.column("id", sa.String()),
        sa.column("tenant_id", sa.String()),
        sa.column("doc_type", sa.String()),
        sa.column("meta", sa.JSON()),
    )

    documents_types_table = sa.table(
        "document_types",
        sa.column("id", sa.String()),
        sa.column("tenant_id", sa.String()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
    )

    templates_table = sa.table(
        "document_templates",
        sa.column("id", sa.String()),
        sa.column("documents", sa.JSON()),
    )

    ruleset_versions_table = sa.table(
        "document_ruleset_versions",
        sa.column("id", sa.String()),
        sa.column("json_data", sa.JSON()),
    )

    # --- documents table ---
    if not _has_column("documents", "doc_type"):
        op.add_column("documents", sa.Column("doc_type", sa.String(length=64), nullable=True))
    if not _has_column("documents", "meta"):
        op.add_column("documents", sa.Column("meta", sa.JSON(), nullable=True))

    rows = bind.execute(
        sa.text("SELECT id, doc_type, meta FROM documents")
    ).fetchall()
    for row in rows:
        new_code = _normalize_code(row.doc_type)
        meta = _load_json(row.meta)
        updated = False

        if new_code != row.doc_type:
            bind.execute(
                documents_table.update()
                .where(documents_table.c.id == row.id)
                .values(doc_type=new_code)
            )
            updated = True

        if isinstance(meta, dict):
            meta_code = _normalize_code(meta.get("doc_type"))
            if meta_code != meta.get("doc_type"):
                meta["doc_type"] = meta_code
                bind.execute(
                    documents_table.update()
                    .where(documents_table.c.id == row.id)
                    .values(meta=meta)
                )
                updated = True

        if updated and isinstance(meta, dict):
            # ensure extra/meta_json derivatives keep canonical doc_type
            for key in ("extra", "meta_json"):
                if key in meta and isinstance(meta[key], dict):
                    inner = meta[key]
                    inner_code = _normalize_code(inner.get("doc_type"))
                    if inner_code != inner.get("doc_type"):
                        inner["doc_type"] = inner_code
            bind.execute(
                documents_table.update()
                .where(documents_table.c.id == row.id)
                .values(meta=meta)
            )

    # --- document_types table ---
    rows = bind.execute(
        sa.text("SELECT id, tenant_id, code, name FROM document_types")
    ).fetchall()
    seen: Dict[tuple[str, str], str] = {}
    for row in rows:
        canonical = _normalize_code(row.code)
        name = _NAME_OVERRIDES.get(canonical, row.name)
        key = (row.tenant_id, canonical)

        if key in seen:
            # duplicate after normalization -> drop the extra row
            bind.execute(
                documents_types_table.delete().where(documents_types_table.c.id == row.id)
            )
            continue

        seen[key] = row.id
        if canonical != row.code or name != row.name:
            bind.execute(
                documents_types_table.update()
                .where(documents_types_table.c.id == row.id)
                .values(code=canonical, name=name)
            )

    # --- document_templates JSON payload ---
    rows = bind.execute(
        sa.text("SELECT id, documents FROM document_templates")
    ).fetchall()
    for row in rows:
        docs_payload = _load_json(row.documents)
        if not isinstance(docs_payload, list):
            continue
        changed = False
        for entry in docs_payload:
            if not isinstance(entry, dict):
                continue
            doc_type = entry.get("doc_type")
            canonical = _normalize_code(doc_type)
            if canonical != doc_type:
                entry["doc_type"] = canonical
                changed = True
        if changed:
            bind.execute(
                templates_table.update()
                .where(templates_table.c.id == row.id)
                .values(documents=docs_payload)
            )

    # --- ruleset versions JSON payload ---
    rows = bind.execute(
        sa.text("SELECT id, json_data FROM document_ruleset_versions")
    ).fetchall()
    for row in rows:
        payload = _load_json(row.json_data)
        if not isinstance(payload, dict):
            continue
        changed = _normalize_ruleset_payload(payload)
        if changed:
            bind.execute(
                ruleset_versions_table.update()
                .where(ruleset_versions_table.c.id == row.id)
                .values(json_data=payload)
            )


def _normalize_ruleset_payload(payload: Dict[str, Any]) -> bool:
    changed = False

    def _normalize_list(items: Any) -> Any:
        nonlocal changed
        if isinstance(items, list):
            out: list[Any] = []
            for item in items:
                if isinstance(item, str):
                    canonical = _normalize_code(item)
                    if canonical != item:
                        changed = True
                    out.append(canonical)
                else:
                    out.append(item)
            return out
        return items

    for key in ("requiredTypes", "optionalTypes"):
        if key in payload:
            payload[key] = _normalize_list(payload[key])

    candidate = payload.get("candidate")
    if isinstance(candidate, dict):
        defaults = candidate.get("defaults")
        if isinstance(defaults, dict):
            for key in ("requiredTypes", "optionalTypes"):
                if key in defaults:
                    defaults[key] = _normalize_list(defaults[key])
        overrides = candidate.get("overrides")
        if isinstance(overrides, list):
            for rule in overrides:
                if isinstance(rule, dict):
                    for key in ("require", "remove"):
                        if key in rule:
                            rule[key] = _normalize_list(rule[key])

    vacancy = payload.get("vacancy")
    if isinstance(vacancy, dict):
        category_sets = vacancy.get("category_sets")
        if isinstance(category_sets, dict):
            for cfg in category_sets.values():
                if isinstance(cfg, dict):
                    for key in ("requiredTypes", "optionalTypes"):
                        if key in cfg:
                            cfg[key] = _normalize_list(cfg[key])
        additions = vacancy.get("additions")
        if isinstance(additions, list):
            for rule in additions:
                if isinstance(rule, dict) and "require" in rule:
                    rule["require"] = _normalize_list(rule["require"])

    validity = payload.get("validity")
    if isinstance(validity, dict):
        items = list(validity.items())
        for key, value in items:
            canonical = _normalize_code(key)
            if canonical != key:
                validity[canonical] = value
                del validity[key]
                changed = True

    return changed


def downgrade() -> None:  # noqa: D401 - Alembic entrypoint
    # Downgrade intentionally left as no-op because reverting document type
    # normalization would require reintroducing deprecated codes.
    pass
