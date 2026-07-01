"""Mirror legacy CRM companies (client rows) into client_companies — §2.4

Rules:
- ``companies.extra.company_role == 'operating'`` → skip (issuer / own-company track).
- Any other or missing role → treat as **client**; copy row into ``client_companies`` with the **same id**
  so future FK moves stay 1:1. Idempotent (skips existing ``client_companies.id``).

Revision ID: 202603291300_client_co_mirror
Revises: 202603291200_meta_ac_fit
Create Date: 2026-03-29

"""

from __future__ import annotations

import json
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202603291300_client_co_mirror"
down_revision: Union[str, None] = "202603291200_meta_ac_fit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn: sa.Connection, name: str) -> bool:
    return name in sa.inspect(conn).get_table_names()


def _parse_extra(raw: Any) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw) if raw.strip() else {}
        except Exception:
            return {}
    return {}


def _json_bind(value: Any) -> str:
    """JSON text for bound params. psycopg3 cannot adapt raw dict to %s in sa.text()."""
    if value is None:
        return "{}"
    if isinstance(value, str):
        return value if value.strip() else "{}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return json.dumps(value, default=str)


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "companies") or not _has_table(conn, "client_companies"):
        return

    rows = conn.execute(
        sa.text(
            "SELECT id, tenant_id, name, legal_name, tax_id, phone, email, website, "
            "country_code, country, city, address, notes, is_archived, contacts, extra, "
            "created_at, updated_at FROM companies"
        )
    ).mappings().all()

    is_pg = conn.dialect.name == "postgresql"
    # PG: cast string param to jsonb. SQLite: store JSON text in JSON column.
    contacts_sql = "CAST(:contacts AS jsonb)" if is_pg else ":contacts"
    extra_sql = "CAST(:extra AS jsonb)" if is_pg else ":extra"

    for r in rows:
        extra = _parse_extra(r.get("extra"))
        role = str(extra.get("company_role") or "").strip().lower() or "client"
        if role == "operating":
            continue
        cid = str(r.get("id") or "").strip()
        if not cid:
            continue
        exists = conn.execute(
            sa.text("SELECT 1 FROM client_companies WHERE id = :id LIMIT 1"),
            {"id": cid},
        ).scalar()
        if exists:
            continue

        contacts_raw = r.get("contacts") or {}
        if isinstance(contacts_raw, str):
            try:
                contacts_raw = json.loads(contacts_raw) if contacts_raw.strip() else {}
            except Exception:
                contacts_raw = {}
        extra_raw = r.get("extra") or {}
        if isinstance(extra_raw, str):
            extra_raw = _parse_extra(extra_raw)

        contacts = _json_bind(contacts_raw if isinstance(contacts_raw, (dict, list)) else {})
        extra_col = _json_bind(extra_raw if isinstance(extra_raw, (dict, list)) else {})
        is_archived = bool(r.get("is_archived"))

        conn.execute(
            sa.text(
                f"""
                INSERT INTO client_companies (
                    id, tenant_id, name, legal_name, tax_id, phone, email, website,
                    country_code, country, city, address, notes, is_archived, contacts, extra,
                    created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :name, :legal_name, :tax_id, :phone, :email, :website,
                    :country_code, :country, :city, :address, :notes, :is_archived, {contacts_sql}, {extra_sql},
                    :created_at, :updated_at
                )
                """
            ),
            {
                "id": cid,
                "tenant_id": str(r.get("tenant_id") or ""),
                "name": str(r.get("name") or "")[:255] or "—",
                "legal_name": r.get("legal_name"),
                "tax_id": r.get("tax_id"),
                "phone": r.get("phone"),
                "email": r.get("email"),
                "website": r.get("website"),
                "country_code": r.get("country_code"),
                "country": r.get("country"),
                "city": r.get("city"),
                "address": r.get("address"),
                "notes": r.get("notes"),
                "is_archived": is_archived,
                "contacts": contacts,
                "extra": extra_col,
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at"),
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "companies") or not _has_table(conn, "client_companies"):
        return

    rows = conn.execute(
        sa.text("SELECT id, extra FROM companies"),
    ).mappings().all()
    for r in rows:
        extra = _parse_extra(r.get("extra"))
        role = str(extra.get("company_role") or "").strip().lower() or "client"
        if role == "operating":
            continue
        cid = str(r.get("id") or "").strip()
        if not cid:
            continue
        conn.execute(sa.text("DELETE FROM client_companies WHERE id = :id"), {"id": cid})
