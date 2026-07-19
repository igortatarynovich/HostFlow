"""G13: CommunicationThread entity links table + backfill.

Revision ID: 202607160001_comm_thread_entity_links
Revises: 202607151100_questionnaire_ssot_repair
Create Date: 2026-07-16 14:40:00.000000
"""

from __future__ import annotations

import json
from typing import Any, Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607160001_comm_thread_entity_links"
down_revision: RevisionType = "202607151100_questionnaire_ssot_repair"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def _trim(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_entity_type(entity_type: str) -> str:
    key = str(entity_type or "").strip().lower()
    aliases = {
        "inquiry": "lead",
        "sales_inquiry": "lead",
        "client": "client_account",
        "clientaccount": "client_account",
        "order": "service_order",
        "serviceorder": "service_order",
    }
    return aliases.get(key, key)


def upgrade() -> None:
    op.create_table(
        "communication_thread_entity_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("is_immutable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["communication_threads.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "thread_id",
            "entity_type",
            "entity_id",
            name="uq_comm_thread_entity_link",
        ),
    )
    op.create_index(
        "ix_comm_thread_links_tenant_entity",
        "communication_thread_entity_links",
        ["tenant_id", "entity_type", "entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_comm_thread_links_tenant_thread",
        "communication_thread_entity_links",
        ["tenant_id", "thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_communication_thread_entity_links_tenant_id",
        "communication_thread_entity_links",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_communication_thread_entity_links_thread_id",
        "communication_thread_entity_links",
        ["thread_id"],
        unique=False,
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT id, tenant_id, entity_type, entity_id,
                   linked_company_id, linked_candidate_id, thread_meta
            FROM communication_threads
            """
        )
    ).mappings().all()

    insert_sql = sa.text(
        """
        INSERT INTO communication_thread_entity_links
            (id, tenant_id, thread_id, entity_type, entity_id, is_immutable)
        VALUES
            (:id, :tenant_id, :thread_id, :entity_type, :entity_id, :is_immutable)
        """
    )

    seen: set[tuple[str, str, str, str]] = set()

    def _add(tenant_id: str, thread_id: str, entity_type: str, entity_id: str, immutable: bool) -> None:
        et = _normalize_entity_type(entity_type)
        eid = _trim(entity_id)
        if not et or not eid:
            return
        key = (tenant_id, thread_id, et, eid)
        if key in seen:
            return
        seen.add(key)
        conn.execute(
            insert_sql,
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "thread_id": thread_id,
                "entity_type": et,
                "entity_id": eid,
                "is_immutable": immutable,
            },
        )

    for row in rows:
        tenant_id = str(row["tenant_id"])
        thread_id = str(row["id"])
        et = _trim(row.get("entity_type"))
        eid = _trim(row.get("entity_id"))
        if et and eid:
            _add(tenant_id, thread_id, et, eid, _normalize_entity_type(et) == "lead")
        company_id = _trim(row.get("linked_company_id"))
        if company_id:
            _add(tenant_id, thread_id, "company", company_id, False)
        candidate_id = _trim(row.get("linked_candidate_id"))
        if candidate_id:
            _add(tenant_id, thread_id, "candidate", candidate_id, False)
        meta_raw = row.get("thread_meta")
        meta: dict[str, Any] = {}
        if isinstance(meta_raw, dict):
            meta = meta_raw
        elif isinstance(meta_raw, str) and meta_raw.strip():
            try:
                parsed = json.loads(meta_raw)
                if isinstance(parsed, dict):
                    meta = parsed
            except Exception:
                meta = {}
        uos = meta.get("uos") if isinstance(meta.get("uos"), dict) else {}
        so_id = _trim(uos.get("linked_service_order_id"))
        if so_id:
            _add(tenant_id, thread_id, "service_order", so_id, False)


def downgrade() -> None:
    op.drop_index("ix_communication_thread_entity_links_thread_id", table_name="communication_thread_entity_links")
    op.drop_index("ix_communication_thread_entity_links_tenant_id", table_name="communication_thread_entity_links")
    op.drop_index("ix_comm_thread_links_tenant_thread", table_name="communication_thread_entity_links")
    op.drop_index("ix_comm_thread_links_tenant_entity", table_name="communication_thread_entity_links")
    op.drop_table("communication_thread_entity_links")
