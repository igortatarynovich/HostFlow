"""Merge intake routing foundation and vacancy process profile binding heads.

Revision ID: 202608160002_merge_intake_vacancy_heads
Revises: 202608160001_intake_routing_foundation, 202608160001_vacancy_process_profile_binding_p3
Create Date: 2026-08-16 12:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608160002_merge_intake_vacancy_heads"
down_revision: RevisionType = (
    "202608160001_intake_routing_foundation",
    "202608160001_vacancy_process_profile_binding_p3",
)
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
