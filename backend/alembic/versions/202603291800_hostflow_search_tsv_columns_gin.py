"""Stored tsvector columns + GIN (§2.6) — threads + lead JSON

Revision ID: 202603291800_hostflow_tsv_gin
Revises: 202603291700_gs_fts_gin
Create Date: 2026-03-29

GIN on ``to_tsvector(...)`` expressions is rejected on PG15+ (immutability).
Physical ``tsvector`` columns maintained by triggers accept plain ``USING gin(col)``.

"""
from typing import Sequence, Union

from alembic import op

revision: str = "202603291800_hostflow_tsv_gin"
down_revision: Union[str, None] = "202603291700_gs_fts_gin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE communication_threads
        ADD COLUMN IF NOT EXISTS hostflow_search_tsv tsvector
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_refresh_communication_thread_search_tsv()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $f$
        BEGIN
          NEW.hostflow_search_tsv := to_tsvector(
            'pg_catalog.simple'::regconfig,
            concat_ws(
              ' ',
              COALESCE(NEW.subject, ''),
              COALESCE(NEW.last_message_preview, ''),
              COALESCE(NEW.channel_thread_ref::text, '')
            )
          );
          RETURN NEW;
        END;
        $f$
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_comm_threads_hostflow_search_tsv ON communication_threads")
    op.execute(
        """
        CREATE TRIGGER trg_comm_threads_hostflow_search_tsv
        BEFORE INSERT OR UPDATE OF subject, last_message_preview, channel_thread_ref
        ON communication_threads
        FOR EACH ROW
        EXECUTE PROCEDURE trg_refresh_communication_thread_search_tsv()
        """
    )
    op.execute(
        """
        UPDATE communication_threads SET subject = subject
        WHERE hostflow_search_tsv IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_comm_threads_hostflow_search_tsv_gin
        ON communication_threads
        USING gin (hostflow_search_tsv)
        WHERE is_archived IS FALSE
        """
    )

    op.execute(
        """
        ALTER TABLE leads
        ADD COLUMN IF NOT EXISTS hostflow_lead_json_tsv tsvector
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_refresh_lead_json_search_tsv()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $f$
        BEGIN
          NEW.hostflow_lead_json_tsv := to_tsvector(
            'pg_catalog.simple'::regconfig,
            concat_ws(
              ' ',
              COALESCE(NEW.normalized::text, ''),
              COALESCE(NEW.payload::text, '')
            )
          );
          RETURN NEW;
        END;
        $f$
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_leads_hostflow_json_tsv ON leads")
    op.execute(
        """
        CREATE TRIGGER trg_leads_hostflow_json_tsv
        BEFORE INSERT OR UPDATE OF normalized, payload
        ON leads
        FOR EACH ROW
        EXECUTE PROCEDURE trg_refresh_lead_json_search_tsv()
        """
    )
    op.execute(
        """
        UPDATE leads SET normalized = normalized
        WHERE hostflow_lead_json_tsv IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_leads_hostflow_lead_json_tsv_gin
        ON leads
        USING gin (hostflow_lead_json_tsv)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_leads_hostflow_lead_json_tsv_gin")
    op.execute("DROP TRIGGER IF EXISTS trg_leads_hostflow_json_tsv ON leads")
    op.execute("DROP FUNCTION IF EXISTS trg_refresh_lead_json_search_tsv()")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS hostflow_lead_json_tsv")

    op.execute("DROP INDEX IF EXISTS ix_comm_threads_hostflow_search_tsv_gin")
    op.execute("DROP TRIGGER IF EXISTS trg_comm_threads_hostflow_search_tsv ON communication_threads")
    op.execute("DROP FUNCTION IF EXISTS trg_refresh_communication_thread_search_tsv()")
    op.execute("ALTER TABLE communication_threads DROP COLUMN IF EXISTS hostflow_search_tsv")
