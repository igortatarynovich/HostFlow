"""Add FK users.id ON DELETE SET NULL on owner-columns (Phase 2.6.G-5 Stage E).

Spec: ``docs/specs/manager-assignment.md`` §4 Stage E.

Today (pre-Stage E) five operational owner-columns hold a user UUID as a
plain ``VARCHAR(36)`` without referential integrity:

* ``reminders.assignee_id``
* ``communication_planner_events.assignee_id``
* ``communication_threads.assignee_id``
* ``document_policies.owner_user_id``
* ``candidate_profiles.owner_user_id``

When a user is deleted (soft-delete via ``users.is_active = false`` is OK;
hard-delete is what actually breaks referential integrity) the orphan
value stays on the row and surfaces as a ghost-assignee in ``/app/tasks``,
``/app/calendar``, the bell panel, or the document owner column — a click
on the assignee chip eventually 404s when the frontend tries to fetch
``/users/{id}``.

Stage E closes the gap:

1. **Pre-migration cleanup.** For every affected column, NULL out values
   that point to a non-existent ``users.id``. This is the orphan sweep;
   without it the ``ADD CONSTRAINT`` would fail. We do it defensively per
   column so one polluted table does not block the rest.
2. **Add FOREIGN KEY (…) REFERENCES users(id) ON DELETE SET NULL.** Named
   following the existing convention ``fk_<table>_<column>_users`` so
   ``alembic downgrade`` can reliably drop them.
3. **Add missing indexes** on ``document_policies.owner_user_id`` and
   ``candidate_profiles.owner_user_id``. The other three columns already
   have a covering or composite index (see ``ix_reminders_assignee_due``,
   ``ix_comm_planner_tenant_assignee``, ``ix_comm_threads_tenant_assignee``).
   Indexing the remaining two keeps the FK ``ON DELETE SET NULL``
   efficient at scale (PG uses the index to locate rows to update).

Out of scope:

* ``communication_allocation_audits.assignee_id`` — forensic audit table;
  losing the original assignee UUID on user delete would weaken the
  trail. Left as a plain column on purpose.
* ``Candidate.manager`` — scheduled for ``DROP COLUMN`` in Stage G; adding
  a FK here would only be thrown away.
* ``Vacancy.manager`` — scheduled for rename to ``primary_recruiter_id``
  with FK in Stage G.

Revision ID: 202604190002_owner_fk_set_null
Revises: 202604190001_candidate_assignee_history
Create Date: 2026-04-19 14:00:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "202604190002_owner_fk_set_null"
down_revision = "202604190001_candidate_assignee_history"
branch_labels = None
depends_on = None


# (table, column, fk_name, ix_name_if_missing)
_TARGETS: tuple[tuple[str, str, str, str | None], ...] = (
    (
        "reminders",
        "assignee_id",
        "fk_reminders_assignee_id_users",
        None,  # covered by ix_reminders_assignee_due / ix_reminders_assignee_remind
    ),
    (
        "communication_planner_events",
        "assignee_id",
        "fk_comm_planner_events_assignee_id_users",
        None,  # covered by ix_comm_planner_tenant_assignee
    ),
    (
        "communication_threads",
        "assignee_id",
        "fk_comm_threads_assignee_id_users",
        None,  # covered by ix_comm_threads_tenant_assignee
    ),
    (
        "document_policies",
        "owner_user_id",
        "fk_document_policies_owner_user_id_users",
        "ix_document_policies_owner_user_id",
    ),
    (
        "candidate_profiles",
        "owner_user_id",
        "fk_candidate_profiles_owner_user_id_users",
        "ix_candidate_profiles_owner_user_id",
    ),
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Orphan sweep — defensive, per-column. Any owner-UUID that does
    #    not resolve to a live ``users.id`` is NULLed BEFORE we add the
    #    FK, otherwise ``ADD CONSTRAINT`` fails on existing data.
    for table, column, _fk_name, _ix_name in _TARGETS:
        bind.exec_driver_sql(
            f"""
            UPDATE {table}
            SET {column} = NULL
            WHERE {column} IS NOT NULL
              AND {column} NOT IN (SELECT id FROM users)
            """
        )

    # 2. Add FK ON DELETE SET NULL. Naming convention:
    #    fk_<table>_<column>_users (mirrors the existing
    #    fk_candidates_recruiter_id_users / fk_companies_owner_user_id_users
    #    constraints).
    for table, column, fk_name, _ix_name in _TARGETS:
        op.create_foreign_key(
            fk_name,
            source_table=table,
            referent_table="users",
            local_cols=[column],
            remote_cols=["id"],
            ondelete="SET NULL",
        )

    # 3. Indexes on owner columns that did not have one. These two
    #    columns are scanned on every user-delete (the PG planner uses
    #    the index to locate rows to NULL) AND by application-level
    #    ``?owner=<user>`` filters in the documents / candidate-profile
    #    admin views.
    for table, column, _fk_name, ix_name in _TARGETS:
        if ix_name is None:
            continue
        op.create_index(ix_name, table, [column])


def downgrade() -> None:
    # Reverse order: drop indexes we added, then FKs. Orphan cleanup is
    # intentionally NOT reverted — NULL is a strictly safer state than a
    # dangling UUID, so leaving it in place is correct.
    for table, _column, _fk_name, ix_name in _TARGETS:
        if ix_name is None:
            continue
        op.drop_index(ix_name, table_name=table)

    for table, _column, fk_name, _ix_name in _TARGETS:
        op.drop_constraint(fk_name, table, type_="foreignkey")
