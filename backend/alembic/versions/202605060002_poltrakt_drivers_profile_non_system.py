"""Poltrakt Drivers candidate profile is editable; only driver_ce_default stays system.

Revision ID: 202605060002_poltrakt_drivers_profile_non_system
Revises: 202605060001_document_dossier_zones
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202605060002_poltrakt_drivers_profile_non_system"
down_revision: Union[str, None] = "202605060001_document_dossier_zones"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "candidate_profiles"):
        return
    op.execute(
        sa.text(
            "UPDATE candidate_profiles SET is_system = false "
            "WHERE code = 'poltrakt_drivers'"
        )
    )
    # Replace legacy seed notes so admin UI does not show "system profile" text.
    op.execute(
        sa.text(
            "UPDATE candidate_profiles SET notes = :new_note "
            "WHERE code = 'poltrakt_drivers' AND notes = :old_note"
        ).bindparams(
            new_note="Poltrakt drivers profile — document requirements are editable in admin.",
            old_note="System profile for POLTRAKT vacancies (Focus tenant.)",
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "candidate_profiles"):
        return
    op.execute(
        sa.text(
            "UPDATE candidate_profiles SET is_system = true "
            "WHERE code = 'poltrakt_drivers'"
        )
    )
