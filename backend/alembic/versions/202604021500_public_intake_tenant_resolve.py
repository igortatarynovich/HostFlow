"""Public intake: global lead-form slug + SECURITY DEFINER helpers for token→tenant (RLS).

Revision ID: 202604021500_intake_tenant
Revises: 202603301301_tlf_public_slug
Create Date: 2026-04-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "202604021500_intake_tenant"
down_revision: Union[str, None] = "202603301301_tlf_public_slug"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        WITH ranked AS (
          SELECT id,
            row_number() OVER (
              PARTITION BY lower(btrim(public_slug))
              ORDER BY tenant_id, id
            ) AS rn
          FROM tenant_lead_forms
          WHERE public_slug IS NOT NULL AND btrim(public_slug) <> ''
        )
        UPDATE tenant_lead_forms t
        SET public_slug = NULL, updated_at = NOW()
        FROM ranked r
        WHERE t.id = r.id AND r.rn > 1;
        """
    )
    op.drop_constraint("uq_tenant_lead_forms_tenant_public_slug", "tenant_lead_forms", type_="unique")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_tenant_lead_forms_public_slug_global
        ON tenant_lead_forms (lower(btrim(public_slug)))
        WHERE public_slug IS NOT NULL AND btrim(public_slug) <> '';
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.hf_intake_token_tenant(p_token text)
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
          SELECT c.tenant_id::uuid
          FROM candidates c
          WHERE c.intake_token IS NOT NULL
            AND c.intake_token = p_token
            AND c.deleted_at IS NULL
          LIMIT 1;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.hf_status_share_token_tenant(p_token text)
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
          SELECT c.tenant_id::uuid
          FROM candidates c
          WHERE c.status_share_token IS NOT NULL
            AND c.status_share_token = p_token
            AND c.deleted_at IS NULL
          LIMIT 1;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.hf_magic_link_token_tenant(p_token text)
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
          SELECT m.tenant_id::uuid
          FROM magic_links m
          WHERE m.token = p_token
          LIMIT 1;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.hf_lead_form_by_public_slug(p_slug text)
        RETURNS TABLE(tenant_id uuid, form_id uuid)
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
          SELECT f.tenant_id::uuid, f.id::uuid
          FROM tenant_lead_forms f
          WHERE f.is_active IS TRUE
            AND f.public_slug IS NOT NULL
            AND btrim(f.public_slug) <> ''
            AND lower(btrim(f.public_slug)) = lower(btrim(p_slug))
          LIMIT 1;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.hf_lead_form_by_id(p_id text)
        RETURNS TABLE(tenant_id uuid, form_id uuid)
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
          SELECT f.tenant_id::uuid, f.id::uuid
          FROM tenant_lead_forms f
          WHERE f.id::text = p_id
            AND f.is_active IS TRUE
          LIMIT 1;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.hf_lead_form_public_slug_taken(p_slug text, p_exclude_id text)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
          SELECT EXISTS (
            SELECT 1
            FROM tenant_lead_forms f
            WHERE f.public_slug IS NOT NULL
              AND btrim(f.public_slug) <> ''
              AND lower(btrim(f.public_slug)) = lower(btrim(p_slug))
              AND (p_exclude_id IS NULL OR btrim(p_exclude_id) = '' OR f.id::text <> p_exclude_id)
          );
        $$;
        """
    )

    op.execute("GRANT EXECUTE ON FUNCTION public.hf_intake_token_tenant(text) TO PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION public.hf_status_share_token_tenant(text) TO PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION public.hf_magic_link_token_tenant(text) TO PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION public.hf_lead_form_by_public_slug(text) TO PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION public.hf_lead_form_by_id(text) TO PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION public.hf_lead_form_public_slug_taken(text, text) TO PUBLIC;")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for name in (
        "hf_lead_form_public_slug_taken(text,text)",
        "hf_lead_form_by_id(text)",
        "hf_lead_form_by_public_slug(text)",
        "hf_magic_link_token_tenant(text)",
        "hf_status_share_token_tenant(text)",
        "hf_intake_token_tenant(text)",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS public.{name};")
    op.execute("DROP INDEX IF EXISTS uq_tenant_lead_forms_public_slug_global;")
    op.create_unique_constraint(
        "uq_tenant_lead_forms_tenant_public_slug",
        "tenant_lead_forms",
        ["tenant_id", "public_slug"],
    )
