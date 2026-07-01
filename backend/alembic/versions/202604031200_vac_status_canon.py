"""vacancies.status canonicalization (Phase 2.6.D Stage B).

Backfills `vacancies.status` to the canonical Python enum
`VacancyStatus = {open, on_hold, closed, filled, cancelled}` and
moves the legacy `archived` status into the orthogonal boolean
`vacancies.is_archived`.

See `docs/specs/vacancy-statuses.md` for the full plan and
`backend/app/models/vacancy.py::normalize_vacancy_status` for the
runtime normalizer that protects writes after this migration runs.

Rewrite rules (idempotent):

  * `paused`           → `on_hold`
  * `archived`         → `closed` AND `is_archived = TRUE`
                         (archive flag retained even if it was already
                          set; status component lifts the soft-delete
                          rather than introducing a hidden state.)
  * Anything outside the canonical 5 codes (case-insensitive)
                       → `open` (with NOTICE so dirty rows stay visible
                         in pg logs during the rollout).

Lower-cased values in the canonical set are passed through unchanged
so this migration is safe to run multiple times.

Revision ID: 202604031200_vac_status_canon
Revises: 202604021600_meta_oauth_p
Create Date: 2026-04-03
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "202604031200_vac_status_canon"
down_revision: Union[str, None] = "202604021600_meta_oauth_p"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CANONICAL_STATUSES = ("open", "on_hold", "closed", "filled", "cancelled")


def upgrade() -> None:
    bind = op.get_bind()

    # SQLite test runs do not exercise data backfills — schema-only
    # tests rely on `normalize_vacancy_status` at the API layer for
    # canonicalisation. Skip cleanly there to keep the test fixture
    # idempotent.
    if bind.dialect.name != "postgresql":
        return

    # 1. paused → on_hold (case-insensitive).
    op.execute(
        """
        UPDATE vacancies
        SET status = 'on_hold'
        WHERE LOWER(status) = 'paused'
        """
    )

    # 2. archived → closed + is_archived=TRUE. The archive flag is
    #    orthogonal so we OR it on top of any existing value. We
    #    deliberately set status='closed' rather than 'cancelled' to
    #    preserve the historical semantic ("vacancy is no longer in
    #    scope") without inventing a fresh terminal reason.
    op.execute(
        """
        UPDATE vacancies
        SET status = 'closed',
            is_archived = TRUE
        WHERE LOWER(status) = 'archived'
        """
    )

    # 3. Lowercase any uppercased rows so the runtime normalizer's
    #    case-insensitive comparison does not have to swallow garbage.
    op.execute(
        """
        UPDATE vacancies
        SET status = LOWER(status)
        WHERE status IS NOT NULL
          AND status <> LOWER(status)
          AND LOWER(status) IN ('open', 'on_hold', 'closed', 'filled', 'cancelled')
        """
    )

    # 4. Clamp anything still outside the canonical set to `open`.
    #    The runtime normalizer would do this on read anyway, but
    #    persisting the canonical value here means analytics and
    #    drilldowns based on raw `vacancies.status` agree with NBA
    #    branch logic without an in-flight translation.
    canonical_in = ", ".join(f"'{s}'" for s in _CANONICAL_STATUSES)
    op.execute(
        f"""
        DO $$
        DECLARE
            dirty_count INTEGER := 0;
        BEGIN
            SELECT COUNT(*) INTO dirty_count
            FROM vacancies
            WHERE status IS NULL
               OR LOWER(status) NOT IN ({canonical_in});

            IF dirty_count > 0 THEN
                RAISE NOTICE
                    'vacancy_status_canonicalization: clamping % rows with unknown status to open',
                    dirty_count;
            END IF;

            UPDATE vacancies
            SET status = 'open'
            WHERE status IS NULL
               OR LOWER(status) NOT IN ({canonical_in});
        END $$;
        """
    )


def downgrade() -> None:
    # Best-effort partial rollback: we can restore `paused` from
    # `on_hold` (lossy — there's no marker to know which `on_hold`
    # rows were originally `paused`), but `archived` cannot be
    # reconstructed because the upgrade fanned it out to two
    # independent fields. Leave both forward-only.
    #
    # Operators rolling back should accept that the canonicalised
    # state is the new baseline; reverting to the pre-Stage-B world
    # requires restoring from a snapshot, not running this migration
    # in reverse.
    pass
