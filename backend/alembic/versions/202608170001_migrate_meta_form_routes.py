"""Migrate meta_form_routes rows into intake routing foundation (PR-4).

Revision ID: 202608170001_migrate_meta_form_routes
Revises: 202608160002_merge_intake_vacancy_heads
Create Date: 2026-08-17
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202608170001_migrate_meta_form_routes"
down_revision: Union[str, Sequence[str], None] = "202608160002_merge_intake_vacancy_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEAD_TARGET_TO_ROUTE_INTENT = {
    "candidate": "candidate_application",
    "client_lead": "sales_inquiry",
    "service_order_lead": "service_request",
    "partner_lead": "partner_inquiry",
}


def _route_intent(raw: object) -> str:
    value = str(raw or "").strip().lower()
    return LEAD_TARGET_TO_ROUTE_INTENT.get(value, "unknown")


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, tenant_id, form_id, page_id, own_company_id, lead_target_type,
                   pipeline_preset, default_assignee_id, is_active
            FROM meta_form_routes
            """
        )
    ).mappings().all()

    for row in rows:
        form_id = str(row["form_id"] or "").strip()
        if not form_id:
            continue
        tenant_id = str(row["tenant_id"])
        code = f"meta-form-{form_id}"
        profile_id = str(uuid.uuid4())
        route_intent = _route_intent(row["lead_target_type"])

        existing_profile = bind.execute(
            sa.text(
                """
                SELECT id FROM intake_source_profiles
                WHERE tenant_id = :tenant_id AND code = :code
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "code": code},
        ).scalar_one_or_none()

        if existing_profile:
            profile_id = str(existing_profile)
            bind.execute(
                sa.text(
                    """
                    UPDATE intake_source_profiles
                    SET own_company_id = :own_company_id,
                        route_intent = :route_intent,
                        pipeline_preset = :pipeline_preset,
                        default_assignee_id = :default_assignee_id,
                        is_active = :is_active,
                        provider = 'meta',
                        channel = 'paid',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :profile_id
                    """
                ),
                {
                    "profile_id": profile_id,
                    "own_company_id": row["own_company_id"],
                    "route_intent": route_intent,
                    "pipeline_preset": row["pipeline_preset"],
                    "default_assignee_id": row["default_assignee_id"],
                    "is_active": bool(row["is_active"]),
                },
            )
        else:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO intake_source_profiles (
                        id, tenant_id, code, name, provider, channel,
                        own_company_id, route_intent, pipeline_preset,
                        default_assignee_id, is_active, created_at, updated_at
                    ) VALUES (
                        :id, :tenant_id, :code, :name, 'meta', 'paid',
                        :own_company_id, :route_intent, :pipeline_preset,
                        :default_assignee_id, :is_active, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": profile_id,
                    "tenant_id": tenant_id,
                    "code": code,
                    "name": f"Meta form {form_id}",
                    "own_company_id": row["own_company_id"],
                    "route_intent": route_intent,
                    "pipeline_preset": row["pipeline_preset"],
                    "default_assignee_id": row["default_assignee_id"],
                    "is_active": bool(row["is_active"]),
                },
            )

        external_key = f"form_id:{form_id}"
        page_id = str(row["page_id"] or "").strip()
        external_key_secondary = f"page_id:{page_id}" if page_id else ""

        existing_binding = bind.execute(
            sa.text(
                """
                SELECT id FROM intake_source_bindings
                WHERE tenant_id = :tenant_id
                  AND provider = 'meta'
                  AND external_key = :external_key
                  AND external_key_secondary = :external_key_secondary
                LIMIT 1
                """
            ),
            {
                "tenant_id": tenant_id,
                "external_key": external_key,
                "external_key_secondary": external_key_secondary,
            },
        ).scalar_one_or_none()

        if existing_binding:
            bind.execute(
                sa.text(
                    """
                    UPDATE intake_source_bindings
                    SET intake_source_profile_id = :profile_id,
                        is_active = :is_active,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :binding_id
                    """
                ),
                {
                    "binding_id": str(existing_binding),
                    "profile_id": profile_id,
                    "is_active": bool(row["is_active"]),
                },
            )
        else:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO intake_source_bindings (
                        id, tenant_id, intake_source_profile_id, provider,
                        external_key, external_key_secondary, label,
                        is_active, priority, created_at, updated_at
                    ) VALUES (
                        :id, :tenant_id, :profile_id, 'meta',
                        :external_key, :external_key_secondary, :label,
                        :is_active, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "profile_id": profile_id,
                    "external_key": external_key,
                    "external_key_secondary": external_key_secondary,
                    "label": f"Meta form {form_id}",
                    "is_active": bool(row["is_active"]),
                },
            )


def downgrade() -> None:
    # Data migration is forward-only; foundation rows may be edited after deploy.
    return None
