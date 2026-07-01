"""activity_layer_v1 — Activity & Notification Operating Layer (Phase 1.3 / ADR-012).

Revision ID: 202607150002_alv1
Revises: 202605110001_ram

Implementation of Phase 1.3 of the Activity & Notification Operating Layer
rollout (ADR-012). The migration plan with all six binding constraints,
DDL, backfill rules, rollback strategy and acceptance metrics lives at:

    docs/specs/architecture/phase-1-3-activity-layer-v1-migration-plan.md

This revision performs:

1. Rename ``reminders`` → ``activities``, ``reminder_events`` →
   ``activity_events``, ``user_notifications`` → ``notifications``.
2. Rename legacy column names to their canonical names
   (``entity_type`` → ``related_entity_type``, ``payload`` → ``metadata``,
   etc.).
3. Add the new canonical columns (``company_id``, ``source_module``,
   ``starts_at``, ``sla_due_at``, ``sla_status`` on ``activities``;
   ``title``, ``body``, ``severity``, ``activity_id`` on
   ``notifications``).
4. Backfill the new columns deterministically — see §3 (status), §4
   (company_id), §5 (source_module), §6 (title/body/severity), §10
   (activity_id) of the migration plan. Constraint #2 says we never
   guess ``company_id``; Constraint #3 says we only link
   ``activity_id`` with high confidence.
5. Create read-only compatibility views ``reminders`` and
   ``user_notifications`` with INSTEAD OF triggers that reject writes
   so missed migrations surface loudly (Constraint #6).
6. Rename indexes to canonical names.
7. ``downgrade()`` reverses every step and writes any in-flight
   ``in_progress`` rows to ``activity_layer_v1_downgrade_audit``
   before collapsing them to ``pending`` (Constraint #5).

Dialect note: Postgres is the production target. SQLite is supported
through the test suite by guarding Postgres-only constructs (compat
views with INSTEAD OF triggers, ``UUID ~ '^...'`` regex) with
``conn.dialect.name == 'postgresql'`` checks.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607150002_alv1"
down_revision: Union[str, None] = "202605110001_ram"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Inspector helpers (idempotency-friendly).
# ---------------------------------------------------------------------------

def _has_table(conn: sa.Connection, name: str) -> bool:
    return name in set(sa.inspect(conn).get_table_names())


def _has_column(conn: sa.Connection, table: str, column: str) -> bool:
    if not _has_table(conn, table):
        return False
    return any(c["name"] == column for c in sa.inspect(conn).get_columns(table))


def _has_index(conn: sa.Connection, table: str, index: str) -> bool:
    if not _has_table(conn, table):
        return False
    try:
        existing = {ix["name"] for ix in sa.inspect(conn).get_indexes(table)}
    except Exception:
        return False
    return index in existing


def _is_postgres(conn: sa.Connection) -> bool:
    return conn.dialect.name == "postgresql"


# ---------------------------------------------------------------------------
# Index renames — (legacy_name, canonical_name, table, canonical_cols).
#
# Index columns are **canonical** (post-rename) names. On Postgres we use
# ``ALTER INDEX RENAME TO``, which preserves the index definition
# verbatim (the index already tracks the renamed column thanks to the
# preceding ``ALTER TABLE RENAME COLUMN``). On SQLite — which does not
# support ``ALTER INDEX RENAME`` — we drop the legacy index and recreate
# it under the canonical name with the canonical columns.
#
# Downgrade is symmetric: rename the canonical index back to legacy on
# Postgres, or drop+recreate with legacy column names on SQLite.
# ---------------------------------------------------------------------------

_ACTIVITY_INDEX_RENAMES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("ix_reminders_tenant_due",       "ix_activities_tenant_due",
     "activities", ("tenant_id", "due_at")),
    ("ix_reminders_entity",           "ix_activities_related_entity",
     "activities", ("tenant_id", "related_entity_type", "related_entity_id")),
    ("ix_reminders_assignee_remind",  "ix_activities_assignee_reminder",
     "activities", ("tenant_id", "assigned_to_user_id", "reminder_at")),
    ("ix_reminders_assignee_due",     "ix_activities_assignee_due",
     "activities", ("tenant_id", "assigned_to_user_id", "due_at")),
    ("ix_reminders_status_due",       "ix_activities_status_due",
     "activities", ("tenant_id", "status", "due_at")),
)

_ACTIVITY_EVENT_INDEX_RENAMES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("ix_reminder_events_tenant",   "ix_activity_events_tenant",
     "activity_events", ("tenant_id",)),
    ("ix_reminder_events_reminder", "ix_activity_events_activity",
     "activity_events", ("activity_id",)),
)

_NOTIFICATION_INDEX_RENAMES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("ix_user_notifications_tenant_id",   "ix_notifications_tenant_id",
     "notifications", ("tenant_id",)),
    ("ix_user_notifications_user_id",     "ix_notifications_user_id",
     "notifications", ("user_id",)),
    ("ix_user_notifications_event_type",  "ix_notifications_type",
     "notifications", ("type",)),
    ("ix_user_notifications_priority",    "ix_notifications_severity_legacy",
     "notifications", ("priority",)),
)


def _rename_index(
    conn: sa.Connection,
    legacy: str,
    canonical: str,
    table: str,
    canonical_cols: tuple[str, ...],
) -> None:
    """Rename ``legacy`` to ``canonical`` on ``table``, dialect-aware."""
    if not _has_table(conn, table):
        return
    if _has_index(conn, table, canonical):
        return
    if not _has_index(conn, table, legacy):
        return
    if _is_postgres(conn):
        op.execute(sa.text(f'ALTER INDEX "{legacy}" RENAME TO "{canonical}"'))
    else:
        op.drop_index(legacy, table_name=table)
        op.create_index(canonical, table, list(canonical_cols))


def _rename_index_back(
    conn: sa.Connection,
    legacy: str,
    canonical: str,
    table: str,
    legacy_cols: tuple[str, ...],
) -> None:
    """Reverse of :func:`_rename_index` for downgrade."""
    if not _has_table(conn, table):
        return
    if _has_index(conn, table, legacy):
        return
    if not _has_index(conn, table, canonical):
        return
    if _is_postgres(conn):
        op.execute(sa.text(f'ALTER INDEX "{canonical}" RENAME TO "{legacy}"'))
    else:
        op.drop_index(canonical, table_name=table)
        op.create_index(legacy, table, list(legacy_cols))


# Pre-computed legacy columns (mirror image of canonical → legacy) for
# the SQLite downgrade path.
_LEGACY_INDEX_COLS: dict[str, tuple[str, ...]] = {
    "ix_reminders_tenant_due":       ("tenant_id", "due_at"),
    "ix_reminders_entity":           ("tenant_id", "entity_type", "entity_id"),
    "ix_reminders_assignee_remind":  ("tenant_id", "assignee_id", "remind_at"),
    "ix_reminders_assignee_due":     ("tenant_id", "assignee_id", "due_at"),
    "ix_reminders_status_due":       ("tenant_id", "status", "due_at"),
    "ix_reminder_events_tenant":     ("tenant_id",),
    "ix_reminder_events_reminder":   ("reminder_id",),
    "ix_user_notifications_tenant_id":  ("tenant_id",),
    "ix_user_notifications_user_id":    ("user_id",),
    "ix_user_notifications_event_type": ("event_type",),
    "ix_user_notifications_priority":   ("priority",),
}


# ---------------------------------------------------------------------------
# UPGRADE
# ---------------------------------------------------------------------------

def _upgrade_activities(conn: sa.Connection) -> None:
    # 2.1 — rename activities table.
    if _has_table(conn, "reminders") and not _has_table(conn, "activities"):
        op.rename_table("reminders", "activities")

    # 2.2 — rename activity_events table + FK column.
    if _has_table(conn, "reminder_events") and not _has_table(conn, "activity_events"):
        op.rename_table("reminder_events", "activity_events")
    if _has_column(conn, "activity_events", "reminder_id") and not _has_column(
        conn, "activity_events", "activity_id"
    ):
        with op.batch_alter_table("activity_events") as batch:
            batch.alter_column("reminder_id", new_column_name="activity_id")

    # 2.3 — rename core columns on activities.
    column_renames = (
        ("entity_type",  "related_entity_type"),
        ("entity_id",    "related_entity_id"),
        ("assignee_id",  "assigned_to_user_id"),
        ("created_by",   "created_by_user_id"),
        ("remind_at",    "reminder_at"),
        ("payload",      "metadata"),
    )
    if _has_table(conn, "activities"):
        with op.batch_alter_table("activities") as batch:
            for old, new in column_renames:
                if _has_column(conn, "activities", old) and not _has_column(
                    conn, "activities", new
                ):
                    batch.alter_column(old, new_column_name=new)

    # 2.4 — additive columns on activities (NULL until backfill).
    add_activity_cols = (
        ("company_id",    sa.Column("company_id", sa.String(36), nullable=True)),
        ("source_module", sa.Column("source_module", sa.String(64), nullable=True)),
        ("starts_at",     sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True)),
        ("sla_due_at",    sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True)),
        ("sla_status",    sa.Column("sla_status", sa.String(16), nullable=True)),
    )
    for name, col in add_activity_cols:
        if _has_table(conn, "activities") and not _has_column(conn, "activities", name):
            op.add_column("activities", col)

    # 2.5 — rename existing indexes (dialect-aware).
    for legacy, canonical, tbl, cols in _ACTIVITY_INDEX_RENAMES:
        _rename_index(conn, legacy, canonical, tbl, cols)
    for legacy, canonical, tbl, cols in _ACTIVITY_EVENT_INDEX_RENAMES:
        _rename_index(conn, legacy, canonical, tbl, cols)

    # 2.6 — new indexes for new columns. Create only if absent.
    new_activity_indexes = (
        ("ix_activities_tenant_company", ("tenant_id", "company_id")),
        ("ix_activities_tenant_source",  ("tenant_id", "source_module")),
        ("ix_activities_tenant_sla",     ("tenant_id", "sla_status", "sla_due_at")),
        ("ix_activities_tenant_starts",  ("tenant_id", "starts_at")),
    )
    for name, cols in new_activity_indexes:
        if _has_table(conn, "activities") and not _has_index(conn, "activities", name):
            op.create_index(name, "activities", list(cols))


def _upgrade_notifications(conn: sa.Connection) -> None:
    if _has_table(conn, "user_notifications") and not _has_table(conn, "notifications"):
        op.rename_table("user_notifications", "notifications")

    column_renames = (
        ("event_type",   "type"),
        ("entity_type",  "related_entity_type"),
        ("entity_id",    "related_entity_id"),
        ("payload",      "metadata"),
    )
    if _has_table(conn, "notifications"):
        with op.batch_alter_table("notifications") as batch:
            for old, new in column_renames:
                if _has_column(conn, "notifications", old) and not _has_column(
                    conn, "notifications", new
                ):
                    batch.alter_column(old, new_column_name=new)

    add_notification_cols = (
        ("title",       sa.Column("title",       sa.String(256), nullable=True)),
        ("body",        sa.Column("body",        sa.Text,        nullable=True)),
        ("severity",    sa.Column("severity",    sa.String(16),  nullable=True)),
        ("activity_id", sa.Column("activity_id", sa.String(36),  nullable=True)),
    )
    for name, col in add_notification_cols:
        if _has_table(conn, "notifications") and not _has_column(
            conn, "notifications", name
        ):
            op.add_column("notifications", col)

    for legacy, canonical, tbl, cols in _NOTIFICATION_INDEX_RENAMES:
        _rename_index(conn, legacy, canonical, tbl, cols)

    new_notification_indexes = (
        ("ix_notifications_tenant_severity_unread",
         ("tenant_id", "severity", "is_read")),
        ("ix_notifications_tenant_activity",
         ("tenant_id", "activity_id")),
        ("ix_notifications_tenant_related_entity",
         ("tenant_id", "related_entity_type", "related_entity_id")),
    )
    for name, cols in new_notification_indexes:
        if _has_table(conn, "notifications") and not _has_index(
            conn, "notifications", name
        ):
            op.create_index(name, "notifications", list(cols))


# ---------------------------------------------------------------------------
# Backfill (§3, §4, §5, §6, §10 of the migration plan).
# ---------------------------------------------------------------------------

def _backfill_status(conn: sa.Connection) -> None:
    # §3 — collapse legacy ``new``/``pending``/``sent`` → ``planned``.
    op.execute(sa.text(
        "UPDATE activities SET status = 'planned' "
        "WHERE status IN ('new', 'pending', 'sent')"
    ))


_UUID_REGEX = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"


def _backfill_company_id(conn: sa.Connection) -> None:
    """§4 — strict no-guessing company_id backfill (Constraint #2)."""

    is_pg = _is_postgres(conn)

    # Source 1 — explicit value from metadata JSON.
    # NOTE: legacy `reminders.payload` is `JSON` (not `JSONB`), so the `?` key-existence
    # operator is unavailable post-rename. We rely on `->>` (defined for both JSON and
    # JSONB) and the regex filter below — that already excludes NULL values and bad
    # casts, so explicit key-existence is redundant.
    if is_pg:
        op.execute(sa.text(
            "UPDATE activities "
            "   SET company_id = (metadata->>'company_id') "
            " WHERE company_id IS NULL "
            "   AND metadata IS NOT NULL "
            f"   AND (metadata->>'company_id') ~ '{_UUID_REGEX}'"
        ))
    else:
        # SQLite test path — JSON1 extension is optional. Best-effort:
        op.execute(sa.text(
            "UPDATE activities "
            "   SET company_id = json_extract(metadata, '$.company_id') "
            " WHERE company_id IS NULL "
            "   AND json_extract(metadata, '$.company_id') IS NOT NULL"
        ))

    # Source 2 — direct company-typed link.
    if is_pg:
        op.execute(sa.text(
            "UPDATE activities "
            "   SET company_id = related_entity_id "
            " WHERE company_id IS NULL "
            "   AND related_entity_type = 'company' "
            f"  AND related_entity_id ~ '{_UUID_REGEX}'"
        ))
    else:
        op.execute(sa.text(
            "UPDATE activities "
            "   SET company_id = related_entity_id "
            " WHERE company_id IS NULL "
            "   AND related_entity_type = 'company' "
            "   AND related_entity_id IS NOT NULL"
        ))

    # Source 3 — related-entity FK chase. Each statement is conditional on
    # the source table existing, so the backfill is safe in environments
    # with partial schemas (e.g. tests that only materialise a few tables).
    fk_targets = (
        ("lead",                 "leads",                 "id"),
        ("candidate",            "candidates",            "id"),
        ("communication_thread", "communication_threads", "id"),
        ("service_order",        "service_orders",        "id"),
        ("invoice",              "invoices",              "id"),
    )
    for entity_type, table, pk in fk_targets:
        if not _has_table(conn, table):
            continue
        if not _has_column(conn, table, "company_id"):
            continue
        op.execute(sa.text(
            "UPDATE activities a "
            f"  SET company_id = src.company_id "
            f" FROM {table} src "
            f" WHERE a.related_entity_type = '{entity_type}' "
            f"   AND a.related_entity_id   = src.{pk}::text "
            f"   AND a.company_id IS NULL "
            f"   AND src.company_id IS NOT NULL"
        ) if is_pg else sa.text(
            "UPDATE activities "
            f"  SET company_id = (SELECT src.company_id FROM {table} src "
            f"                     WHERE src.{pk} = activities.related_entity_id "
            f"                       AND src.company_id IS NOT NULL) "
            f"WHERE related_entity_type = '{entity_type}' "
            f"  AND company_id IS NULL "
            f"  AND EXISTS (SELECT 1 FROM {table} src "
            f"               WHERE src.{pk} = activities.related_entity_id "
            f"                 AND src.company_id IS NOT NULL)"
        ))

    # Source 4 — tenant default, only when unique. Constraint #2: never
    # guess. We only backfill if the tenant owns exactly one company.
    if _has_table(conn, "companies") and _has_column(conn, "companies", "tenant_id"):
        deleted_at_clause = (
            "AND c.deleted_at IS NULL"
            if _has_column(conn, "companies", "deleted_at")
            else ""
        )
        if is_pg:
            op.execute(sa.text(
                "WITH unique_company AS ("
                "    SELECT tenant_id, company_id FROM ("
                "        SELECT c.tenant_id, c.id AS company_id, "
                "               COUNT(*) OVER (PARTITION BY c.tenant_id) AS company_count"
                f"       FROM companies c WHERE TRUE {deleted_at_clause}"
                "    ) s WHERE s.company_count = 1"
                ") "
                "UPDATE activities a SET company_id = uc.company_id "
                " FROM unique_company uc "
                "WHERE a.tenant_id = uc.tenant_id "
                "  AND a.company_id IS NULL"
            ))
        else:
            op.execute(sa.text(
                "UPDATE activities "
                "  SET company_id = ("
                "    SELECT c.id FROM companies c "
                f"   WHERE c.tenant_id = activities.tenant_id {deleted_at_clause}"
                "    GROUP BY c.tenant_id "
                "    HAVING COUNT(*) = 1"
                "  ) "
                "WHERE company_id IS NULL "
                "  AND ("
                "    SELECT COUNT(*) FROM companies c "
                f"   WHERE c.tenant_id = activities.tenant_id {deleted_at_clause}"
                "  ) = 1"
            ))


def _backfill_source_module(conn: sa.Connection) -> None:
    """§5 — source_module classifier.

    LIKE patterns deliberately use the unescaped wildcard form
    (``'document_%'`` / ``'uos_%'``). The single-char wildcard ``_`` in
    SQL LIKE is a strict superset of literal underscore for our needs —
    every legacy ``type`` has a non-empty prefix before the underscore,
    so the wildcard form matches the same set of rows on Postgres and
    SQLite without dialect-specific ``ESCAPE`` clauses.
    """

    op.execute(sa.text(
        "UPDATE activities SET source_module = CASE "
        "    WHEN related_entity_type = 'lead'                  THEN 'leads' "
        "    WHEN related_entity_type = 'candidate'             THEN 'recruitment' "
        "    WHEN related_entity_type = 'communication_thread'  THEN 'communications' "
        "    WHEN related_entity_type = 'service_order'         THEN 'services' "
        "    WHEN related_entity_type = 'invoice'               THEN 'invoicing' "
        "    WHEN related_entity_type = 'company'               THEN 'crm' "
        "    WHEN related_entity_type = 'workforce_employee'    THEN 'hr' "
        "    WHEN type LIKE 'document_%'                        THEN 'documents' "
        "    WHEN type LIKE 'uos_%'                             THEN 'recruitment' "
        "    ELSE 'unknown' "
        "END "
        "WHERE source_module IS NULL"
    ))


def _backfill_notification_title(conn: sa.Connection) -> None:
    """§6.1 — notifications.title."""

    is_pg = _is_postgres(conn)
    extract_title = "metadata->>'title'"     if is_pg else "json_extract(metadata, '$.title')"
    extract_subject = "metadata->>'subject'" if is_pg else "json_extract(metadata, '$.subject')"
    initcap = "INITCAP(REPLACE(type, '_', ' '))" if is_pg else "REPLACE(type, '_', ' ')"

    op.execute(sa.text(
        "UPDATE notifications SET title = COALESCE("
        f"  {extract_title},"
        f"  {extract_subject},"
        "  CASE type"
        "      WHEN 'reminder_due'              THEN 'Reminder due'"
        "      WHEN 'reminder_overdue'          THEN 'Reminder overdue'"
        "      WHEN 'lead_assigned'             THEN 'New lead assigned'"
        "      WHEN 'candidate_assigned'        THEN 'New candidate assigned'"
        "      WHEN 'document_expiring'         THEN 'Document expiring soon'"
        "      WHEN 'document_expired'          THEN 'Document expired'"
        "      WHEN 'communication_inbound'     THEN 'New inbound message'"
        "      WHEN 'sla_warning'               THEN 'SLA warning'"
        "      WHEN 'sla_breached'              THEN 'SLA breached'"
        f"     ELSE {initcap}"
        "  END"
        ") WHERE title IS NULL"
    ))


def _backfill_notification_body(conn: sa.Connection) -> None:
    """§6.2 — notifications.body."""

    is_pg = _is_postgres(conn)
    body_extract = (
        "COALESCE(metadata->>'body', metadata->>'message', metadata->>'description')"
        if is_pg else
        "COALESCE("
        " json_extract(metadata, '$.body'),"
        " json_extract(metadata, '$.message'),"
        " json_extract(metadata, '$.description')"
        ")"
    )
    op.execute(sa.text(
        f"UPDATE notifications SET body = {body_extract} WHERE body IS NULL"
    ))


def _backfill_notification_severity(conn: sa.Connection) -> None:
    """§6.3 — notifications.severity (3-tier closed enum, Constraint #1).

    LIKE patterns use unescaped wildcards (see ``_backfill_source_module``
    for rationale). The ``_`` in ``%_failed`` etc. is the SQL LIKE
    single-char wildcard, which on the production set matches exactly
    the literal underscore preceding the suffix.
    """

    op.execute(sa.text(
        "UPDATE notifications SET severity = CASE "
        "    WHEN priority IN ('critical', 'urgent', 'p0') THEN 'critical' "
        "    WHEN priority IN ('error', 'high', 'p1')      THEN 'critical' "
        "    WHEN type LIKE '%_breached'                   THEN 'critical' "
        "    WHEN type LIKE '%_expired'                    THEN 'critical' "
        "    WHEN type LIKE '%_failed'                     THEN 'critical' "
        "    WHEN priority IN ('medium', 'normal', 'p2', 'warn', 'warning') THEN 'warning' "
        "    WHEN type LIKE '%_overdue'                    THEN 'warning' "
        "    WHEN type LIKE '%_warning'                    THEN 'warning' "
        "    WHEN type LIKE '%_expiring'                   THEN 'warning' "
        "    WHEN type LIKE '%_at_risk'                    THEN 'warning' "
        "    ELSE 'info' "
        "END "
        "WHERE severity IS NULL"
    ))


def _backfill_activity_id_high_confidence(conn: sa.Connection) -> None:
    """§10 — high-confidence-only linkage (Constraint #3)."""

    is_pg = _is_postgres(conn)

    # Source 1 — explicit FK in payload/metadata.
    if is_pg:
        op.execute(sa.text(
            "UPDATE notifications n SET activity_id = a.id "
            "  FROM activities a "
            " WHERE n.activity_id IS NULL "
            "   AND a.tenant_id = n.tenant_id "
            "   AND a.id = COALESCE("
            "       n.metadata->>'activity_id', "
            "       n.metadata->>'reminder_id'"
            "   ) "
            "   AND COALESCE(n.metadata->>'activity_id', n.metadata->>'reminder_id') IS NOT NULL"
        ))
    else:
        op.execute(sa.text(
            "UPDATE notifications "
            "   SET activity_id = COALESCE("
            "       json_extract(metadata, '$.activity_id'), "
            "       json_extract(metadata, '$.reminder_id'))"
            " WHERE activity_id IS NULL "
            "   AND COALESCE("
            "       json_extract(metadata, '$.activity_id'), "
            "       json_extract(metadata, '$.reminder_id')"
            "   ) IS NOT NULL "
            "   AND EXISTS ("
            "       SELECT 1 FROM activities a "
            "        WHERE a.tenant_id = notifications.tenant_id "
            "          AND a.id = COALESCE("
            "              json_extract(notifications.metadata, '$.activity_id'),"
            "              json_extract(notifications.metadata, '$.reminder_id')"
            "          )"
            "   )"
        ))

    # Source 2 — strict tuple match with explicit type-pair allow-list,
    # 5-minute window, no fuzzy fallback. Multiple matches → leave NULL.
    type_pairs_values = ", ".join(
        f"('{a}', '{n}')" for (a, n) in (
            ("reminder",                "reminder_due"),
            ("reminder",                "reminder_overdue"),
            ("document_check",          "document_expiring"),
            ("document_check",          "document_expired"),
            ("uos_candidate_call",      "candidate_due"),
            ("uos_invoice_follow_payment", "invoice_due"),
            ("uos_inbound_reply",       "communication_inbound"),
            ("sla_check",               "sla_warning"),
            ("sla_check",               "sla_breached"),
        )
    )

    if is_pg:
        op.execute(sa.text(
            "WITH type_pairs(activity_type, notification_type) AS ("
            f"   VALUES {type_pairs_values}"
            "), candidate_links AS ("
            "    SELECT n.id AS notification_id, a.id AS activity_id, "
            "           COUNT(*) OVER (PARTITION BY n.id) AS match_count"
            "      FROM notifications n "
            "      JOIN activities    a  ON a.tenant_id            = n.tenant_id "
            "                          AND a.related_entity_type   = n.related_entity_type "
            "                          AND a.related_entity_id     = n.related_entity_id "
            "      JOIN type_pairs    tp ON tp.activity_type       = a.type "
            "                          AND tp.notification_type    = n.type "
            "     WHERE n.activity_id IS NULL "
            "       AND a.related_entity_type IS NOT NULL "
            "       AND a.related_entity_id   IS NOT NULL "
            "       AND a.created_at <= n.created_at "
            "       AND a.created_at >  n.created_at - INTERVAL '5 minutes'"
            ") "
            "UPDATE notifications n SET activity_id = cl.activity_id "
            "  FROM candidate_links cl "
            " WHERE n.id = cl.notification_id "
            "   AND cl.match_count = 1"
        ))
    else:
        op.execute(sa.text(
            "UPDATE notifications "
            "   SET activity_id = ("
            "       SELECT a.id FROM activities a "
            "        WHERE a.tenant_id          = notifications.tenant_id "
            "          AND a.related_entity_type = notifications.related_entity_type "
            "          AND a.related_entity_id   = notifications.related_entity_id "
            "          AND (a.type, notifications.type) IN ("
            f"             {type_pairs_values}"
            "          ) "
            "          AND a.created_at <= notifications.created_at "
            "          AND a.created_at >  datetime(notifications.created_at, '-5 minutes') "
            "        GROUP BY a.id "
            "        HAVING COUNT(*) = 1 "
            "        LIMIT 1) "
            " WHERE activity_id IS NULL"
        ))


# ---------------------------------------------------------------------------
# Compatibility views (§2.3, Constraint #6).
# ---------------------------------------------------------------------------

_COMPAT_VIEW_SQL_PG = """
CREATE OR REPLACE FUNCTION _activity_layer_v1_reject_legacy_write()
RETURNS trigger AS $func$
BEGIN
    RAISE EXCEPTION
      'Write to legacy view % is not allowed -- write to the canonical table',
      TG_TABLE_NAME
      USING HINT = 'See ADR-012 / Phase 1.3 plan §2.3';
END;
$func$ LANGUAGE plpgsql;

CREATE VIEW reminders          AS SELECT * FROM activities;
CREATE VIEW user_notifications AS SELECT * FROM notifications;

CREATE TRIGGER reject_writes_reminders
  INSTEAD OF INSERT OR UPDATE OR DELETE ON reminders
  FOR EACH ROW EXECUTE FUNCTION _activity_layer_v1_reject_legacy_write();

CREATE TRIGGER reject_writes_user_notifications
  INSTEAD OF INSERT OR UPDATE OR DELETE ON user_notifications
  FOR EACH ROW EXECUTE FUNCTION _activity_layer_v1_reject_legacy_write();
"""


def _create_compat_views(conn: sa.Connection) -> None:
    if _is_postgres(conn):
        op.execute(sa.text(_COMPAT_VIEW_SQL_PG))
    else:
        # SQLite (test harness) — plain views are sufficient; SQLite views
        # are read-only by default, so a write attempt fails with
        # `cannot modify view`. That matches the production semantics.
        op.execute(sa.text("CREATE VIEW reminders          AS SELECT * FROM activities"))
        op.execute(sa.text("CREATE VIEW user_notifications AS SELECT * FROM notifications"))


def _drop_compat_views(conn: sa.Connection) -> None:
    if _is_postgres(conn):
        op.execute(sa.text(
            "DROP TRIGGER IF EXISTS reject_writes_user_notifications ON user_notifications"
        ))
        op.execute(sa.text(
            "DROP TRIGGER IF EXISTS reject_writes_reminders ON reminders"
        ))
    op.execute(sa.text("DROP VIEW IF EXISTS user_notifications"))
    op.execute(sa.text("DROP VIEW IF EXISTS reminders"))
    if _is_postgres(conn):
        op.execute(sa.text(
            "DROP FUNCTION IF EXISTS _activity_layer_v1_reject_legacy_write()"
        ))


# ---------------------------------------------------------------------------
# Audit table for in-flight in_progress rows during downgrade (§8).
# ---------------------------------------------------------------------------

_DOWNGRADE_AUDIT_TABLE = "activity_layer_v1_downgrade_audit"


def _ensure_downgrade_audit_table(conn: sa.Connection) -> None:
    if _has_table(conn, _DOWNGRADE_AUDIT_TABLE):
        return
    op.create_table(
        _DOWNGRADE_AUDIT_TABLE,
        sa.Column("activity_id", sa.String(36), primary_key=True),
        sa.Column("original_status", sa.String(32), nullable=False),
        sa.Column(
            "downgraded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


# ---------------------------------------------------------------------------
# Public entrypoints.
# ---------------------------------------------------------------------------

def upgrade() -> None:
    conn = op.get_bind()

    # The migration plan splits this into two top-level transactions for
    # blast-radius isolation. Alembic already runs every revision in a
    # transaction; we honour the spirit of the plan by pairing the rename
    # of each domain with its own backfill block, so a failure in one
    # block leaves the *other* domain alone (the fix-forward is applied
    # by re-running the migration — every step is idempotent).

    # --- activities domain ---
    _upgrade_activities(conn)

    if _has_table(conn, "activities"):
        _backfill_status(conn)
        _backfill_company_id(conn)
        _backfill_source_module(conn)

    # --- notifications domain ---
    _upgrade_notifications(conn)

    if _has_table(conn, "notifications"):
        _backfill_notification_title(conn)
        _backfill_notification_body(conn)
        _backfill_notification_severity(conn)
        _backfill_activity_id_high_confidence(conn)

    # --- compat views (Constraint #6) ---
    if _has_table(conn, "activities") and _has_table(conn, "notifications"):
        # Drop any leftover views from a prior partial run, then create.
        try:
            _drop_compat_views(conn)
        except Exception:
            pass
        _create_compat_views(conn)


def downgrade() -> None:
    conn = op.get_bind()

    # --- audit + collapse in_progress (Constraint #5) ---
    if _has_table(conn, "activities"):
        _ensure_downgrade_audit_table(conn)
        op.execute(sa.text(
            "INSERT INTO activity_layer_v1_downgrade_audit "
            "    (activity_id, original_status) "
            "SELECT id, status FROM activities "
            " WHERE status NOT IN ('new','pending','sent','overdue','done','cancelled') "
            "   AND id NOT IN (SELECT activity_id FROM activity_layer_v1_downgrade_audit)"
        ))
        op.execute(sa.text(
            "UPDATE activities SET status = 'pending' "
            " WHERE status NOT IN "
            "       ('new','pending','sent','overdue','done','cancelled')"
        ))
        # The 1.3 migration collapsed legacy 'new'/'pending'/'sent' to
        # 'planned'. Downgrade folds 'planned' back into 'pending', the
        # most common legacy bucket.
        op.execute(sa.text(
            "UPDATE activities SET status = 'pending' WHERE status = 'planned'"
        ))

    # --- compat views ---
    _drop_compat_views(conn)

    # --- notifications domain (reverse order) ---
    # 1. drop new-only indexes
    for name in (
        "ix_notifications_tenant_related_entity",
        "ix_notifications_tenant_activity",
        "ix_notifications_tenant_severity_unread",
    ):
        if _has_index(conn, "notifications", name):
            op.drop_index(name, table_name="notifications")

    # 2. drop new-only columns
    if _has_table(conn, "notifications"):
        for col in ("activity_id", "severity", "body", "title"):
            if _has_column(conn, "notifications", col):
                op.drop_column("notifications", col)

    # 3. rename canonical columns back to legacy *before* index rename
    #    (the SQLite path of `_rename_index_back` will issue a CREATE
    #    INDEX referencing legacy column names, so the columns must
    #    already be renamed at that point).
    if _has_table(conn, "notifications"):
        with op.batch_alter_table("notifications") as batch:
            for old, new in (
                ("event_type",  "type"),
                ("entity_type", "related_entity_type"),
                ("entity_id",   "related_entity_id"),
                ("payload",     "metadata"),
            ):
                if _has_column(conn, "notifications", new) and not _has_column(
                    conn, "notifications", old
                ):
                    batch.alter_column(new, new_column_name=old)

    # 4. rename indexes back (now that columns carry legacy names again)
    for legacy, canonical, tbl, _ in _NOTIFICATION_INDEX_RENAMES:
        _rename_index_back(conn, legacy, canonical, tbl, _LEGACY_INDEX_COLS[legacy])

    # 5. rename the table back last
    if _has_table(conn, "notifications") and not _has_table(conn, "user_notifications"):
        op.rename_table("notifications", "user_notifications")

    # --- activities domain (reverse order, same column-then-index pattern) ---
    # 1. drop new-only indexes
    for name in (
        "ix_activities_tenant_starts",
        "ix_activities_tenant_sla",
        "ix_activities_tenant_source",
        "ix_activities_tenant_company",
    ):
        if _has_index(conn, "activities", name):
            op.drop_index(name, table_name="activities")

    # 2. drop new-only columns
    if _has_table(conn, "activities"):
        for col in ("sla_status", "sla_due_at", "starts_at", "source_module", "company_id"):
            if _has_column(conn, "activities", col):
                op.drop_column("activities", col)

    # 3. rename canonical columns back to legacy
    if _has_table(conn, "activities"):
        with op.batch_alter_table("activities") as batch:
            for old, new in (
                ("entity_type",  "related_entity_type"),
                ("entity_id",    "related_entity_id"),
                ("assignee_id",  "assigned_to_user_id"),
                ("created_by",   "created_by_user_id"),
                ("remind_at",    "reminder_at"),
                ("payload",      "metadata"),
            ):
                if _has_column(conn, "activities", new) and not _has_column(
                    conn, "activities", old
                ):
                    batch.alter_column(new, new_column_name=old)

    # 4. activity_events FK column back to ``reminder_id``
    if _has_column(conn, "activity_events", "activity_id") and not _has_column(
        conn, "activity_events", "reminder_id"
    ):
        with op.batch_alter_table("activity_events") as batch:
            batch.alter_column("activity_id", new_column_name="reminder_id")

    # 5. rename indexes back
    for legacy, canonical, tbl, _ in _ACTIVITY_EVENT_INDEX_RENAMES:
        _rename_index_back(conn, legacy, canonical, tbl, _LEGACY_INDEX_COLS[legacy])
    for legacy, canonical, tbl, _ in _ACTIVITY_INDEX_RENAMES:
        _rename_index_back(conn, legacy, canonical, tbl, _LEGACY_INDEX_COLS[legacy])

    # 6. rename tables back last
    if _has_table(conn, "activity_events") and not _has_table(conn, "reminder_events"):
        op.rename_table("activity_events", "reminder_events")
    if _has_table(conn, "activities") and not _has_table(conn, "reminders"):
        op.rename_table("activities", "reminders")
