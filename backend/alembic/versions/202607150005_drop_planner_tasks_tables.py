"""drop_planner_tasks_tables — Phase 2.1 finalisation (ADR-012).

Revision ID: 202607150005_dptt
Revises: 202607150004_pti
Create Date: 2026-05-09

Phase 2.1 finalisation revision. Drops the legacy operational-task tables
that ``202607150004_planner_tasks_into_activities`` backfilled into
``activities``:

* ``candidate_tasks``
* ``communication_planner_events``

This revision is **not** to be applied until canary completes. The
prerequisites are documented in
``docs/specs/architecture/phase-2-1-planner-tasks-into-activities.md``
(§"Removal sequencing"):

1. ``202607150004_pti`` is in ``alembic_version`` on every environment
   (dev / staging / prod).
2. ``backfill_audit`` shows the row counts match — see the audit query
   in §"Acceptance" of the plan. Otherwise pre-existing legacy rows are
   silently dropped.
3. **Backend routes that read these tables are removed**:
       - ``GET/POST/PATCH/DELETE /api/v1/candidates/{id}/tasks``
       - ``GET/POST/PATCH/DELETE /api/v1/communications/planner/events*``
4. **Backend services that write to these tables are rewired** to
   ``Activity`` (or deleted as dead code):
       - ``app/services/timeoff_cleanup.py``
       - ``app/services/lead_lifecycle.py``
       - ``app/services/candidate_lifecycle.py``
       - ``app/services/team_assignee_auto.py``
       - ``app/services/communications_scheduler.py``
       - ``app/services/assignee_load_taxonomy.py``
5. **Frontend shim is wired** to ``listActivities`` /
   ``createActivity`` / ``patchActivity`` (no direct references to
   ``/communications/planner/events`` or ``/candidates/{id}/tasks``
   remain in the React tree).

Once those preconditions hold, this revision is what flips the table
schema from "legacy + canonical co-existing" to "canonical only".

Idempotency: ``op.drop_table`` is wrapped with a table-existence guard
so re-running upgrade after partial failure (or running on a fresh
environment that never had the legacy tables — e.g. a brand new dev
DB) is safe.

Downgrade strategy: re-creates **empty** legacy tables with the same
column shape (no FKs / RLS — the prod schema came from the
``recruitment_module_v1`` migration; we only need enough surface for
``alembic downgrade`` to succeed). The Phase 2.1 backfill rows are
**still in ``activities``** with ``metadata.legacy_source`` markers, so
downgrading the *backfill* revision (`202607150004_pti`) cleanly
removes them. There is no automatic re-population of the legacy
tables from canonical activities — that would be a forward-only
re-projection and is out of scope.
"""

from __future__ import annotations

import logging
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607150005_dptt"
down_revision: Union[str, None] = "202607150004_pti"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


logger = logging.getLogger("alembic.runtime.migration")

# Hard gate. Until canary completes (see plan §"Removal sequencing"),
# every environment must run ``alembic upgrade 202607150004_pti``
# explicitly so a casual ``alembic upgrade head`` does not silently
# drop the legacy tables. The flag is intentionally awkward — it must
# be set deliberately by the operator who has just verified backend
# routes / services / FE shim are wired off the legacy tables.
_GATE_ENV = "HOSTFLOW_PHASE_2_1_DROP_OK"


def _gate_open() -> bool:
    return os.environ.get(_GATE_ENV, "").strip().lower() in ("1", "true", "yes")


def _has_table(conn: sa.Connection, name: str) -> bool:
    return name in set(sa.inspect(conn).get_table_names())


def _is_postgres(conn: sa.Connection) -> bool:
    return conn.dialect.name == "postgresql"


def upgrade() -> None:
    """Drop the legacy planner / candidate_tasks tables.

    Behaviour matrix:

    * ``HOSTFLOW_PHASE_2_1_DROP_OK`` not set → log a loud warning and
      no-op. The revision is still **recorded** in ``alembic_version``,
      so ``alembic upgrade head`` is non-destructive on every
      environment that has not opted in. Operators who want to actually
      drop the tables must (a) downgrade past this revision, then (b)
      re-upgrade with the env flag set:

      .. code-block:: bash

          alembic downgrade 202607150004_pti
          HOSTFLOW_PHASE_2_1_DROP_OK=1 alembic upgrade head

    * ``HOSTFLOW_PHASE_2_1_DROP_OK=1`` → physically drops the tables
      (idempotent — guarded by ``_has_table``).

    Why a soft gate instead of ``raise``
    ------------------------------------
    Hard-failing ``upgrade()`` would break ``alembic upgrade head`` in
    CI and dev environments that still need the legacy tables on disk
    while routes / services / FE shims are being unwired. Soft-gating
    keeps ``alembic upgrade head`` working everywhere; the destructive
    step is only taken on environments where the operator opts in.
    """
    conn = op.get_bind()

    if not _gate_open():
        ct = "yes" if _has_table(conn, "candidate_tasks") else "no"
        pe = "yes" if _has_table(conn, "communication_planner_events") else "no"
        logger.warning(
            "[phase_2_1] DROP revision is gated; tables left in place "
            "(candidate_tasks_present=%s, planner_events_present=%s). "
            "Set %s=1 to actually drop them after canary completes.",
            ct, pe, _GATE_ENV,
        )
        return

    if _has_table(conn, "candidate_tasks"):
        logger.info("[phase_2_1] dropping candidate_tasks")
        op.drop_table("candidate_tasks")

    if _has_table(conn, "communication_planner_events"):
        logger.info("[phase_2_1] dropping communication_planner_events")
        op.drop_table("communication_planner_events")


def downgrade() -> None:
    conn = op.get_bind()

    # Re-create the **shape** of both tables for ``alembic downgrade``
    # symmetry. We do NOT replay any data — the backfill revision
    # (`202607150004_pti`) handles row-level removal via
    # ``metadata.legacy_source`` on its own downgrade. RLS / FKs / RLS
    # policies are intentionally omitted: they were owned by the
    # original ``recruitment_module_v1`` and ``communications`` blueprint
    # migrations and the legacy tables are write-only-empty after this
    # downgrade.

    if not _has_table(conn, "candidate_tasks"):
        op.create_table(
            "candidate_tasks",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
            sa.Column("candidate_id", sa.String(36), nullable=False, index=True),
            sa.Column("title", sa.String(256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("due_on", sa.String(32), nullable=True),
            sa.Column("priority", sa.String(16), nullable=True),
            sa.Column("assigned_to", sa.String(120), nullable=True),
            sa.Column(
                "completed",
                sa.Integer,
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column("meta", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    if not _has_table(conn, "communication_planner_events"):
        op.create_table(
            "communication_planner_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
            sa.Column("title", sa.String(256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("kind", sa.String(32), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("priority", sa.String(16), nullable=True),
            sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "all_day",
                sa.Boolean,
                nullable=False,
                server_default=sa.text("false") if _is_postgres(conn) else sa.text("0"),
            ),
            sa.Column("owner_id", sa.String(36), nullable=True),
            sa.Column("assignee_id", sa.String(36), nullable=True),
            sa.Column("entity_type", sa.String(64), nullable=True),
            sa.Column("entity_id", sa.String(120), nullable=True),
            sa.Column("linked_candidate_id", sa.String(36), nullable=True),
            sa.Column("linked_company_id", sa.String(36), nullable=True),
            sa.Column("source", sa.String(64), nullable=True),
            sa.Column("payload", sa.JSON, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
