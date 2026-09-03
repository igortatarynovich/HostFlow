"""Resolve public apply tokens from questionnaire invites and lead drafts.

Revision ID: 202609020001_intake_token_tenant_invites
Revises: 202608310001_bootstrap_admin_schema

``hf_intake_token_tenant`` originally looked only at ``candidates.intake_token``.
Sales questionnaire links use ``lead_questionnaire_invites.token`` (and lead-first
drafts store the apply token in ``leads.normalized``). Without those lookups the
SECURITY DEFINER helper returns NULL; under RLS the ORM fallback can also miss
the row, so ``POST /public/apply/{token}/submit`` 404s after GET already rendered
the form.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "202609020001_intake_token_tenant_invites"
down_revision: Union[str, None] = "202608310001_bootstrap_admin_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FN_CURRENT = """
CREATE OR REPLACE FUNCTION public.hf_intake_token_tenant(p_token text)
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT tid FROM (
    SELECT i.tenant_id::uuid AS tid
    FROM lead_questionnaire_invites i
    WHERE i.token IS NOT NULL
      AND i.token = p_token
    UNION ALL
    SELECT l.tenant_id::uuid
    FROM leads l
    WHERE l.source = 'public_intake'
      AND l.stage IN ('intake_draft', 'questionnaire_submitted', 'intake_draft_abandoned')
      AND l.normalized IS NOT NULL
      AND l.normalized -> 'public_intake_draft_v1' ->> 'intake_token' = p_token
    UNION ALL
    SELECT c.tenant_id::uuid
    FROM candidates c
    WHERE c.intake_token IS NOT NULL
      AND c.intake_token = p_token
      AND c.deleted_at IS NULL
  ) resolved
  LIMIT 1;
$$;
"""

_FN_ORIGINAL = """
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


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(_FN_CURRENT)
    op.execute("GRANT EXECUTE ON FUNCTION public.hf_intake_token_tenant(text) TO PUBLIC;")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(_FN_ORIGINAL)
    op.execute("GRANT EXECUTE ON FUNCTION public.hf_intake_token_tenant(text) TO PUBLIC;")
