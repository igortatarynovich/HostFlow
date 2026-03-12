"""Fix vacancies pointing to deleted/missing candidate profile (e.g. d629b14b-...).

Sets candidate_profile_id to driver_ce_default for the same tenant when the
referenced profile does not exist or is inactive.

Revision ID: 202602080003
Revises: 202602080002
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202602080003"
down_revision: Union[str, Sequence[str], None] = "202602080002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DRIVER_CE_DEFAULT_CODE = "driver_ce_default"


def upgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    if is_sqlite:
        conn.execute(
            sa.text("""
                UPDATE vacancies
                SET candidate_profile_id = (
                    SELECT id FROM candidate_profiles
                    WHERE candidate_profiles.tenant_id = vacancies.tenant_id
                      AND code = :code
                    LIMIT 1
                )
                WHERE candidate_profile_id IS NOT NULL
                  AND candidate_profile_id NOT IN (
                    SELECT id FROM candidate_profiles
                    WHERE candidate_profiles.tenant_id = vacancies.tenant_id
                      AND is_active = 1
                  )
            """),
            {"code": DRIVER_CE_DEFAULT_CODE},
        )
    else:
        conn.execute(
            sa.text("""
                UPDATE vacancies v
                SET candidate_profile_id = dp.id
                FROM candidate_profiles dp
                WHERE dp.tenant_id = v.tenant_id
                  AND dp.code = :code
                  AND v.candidate_profile_id IS NOT NULL
                  AND (
                    v.candidate_profile_id NOT IN (
                      SELECT id FROM candidate_profiles cp
                      WHERE cp.tenant_id = v.tenant_id AND cp.is_active = true
                    )
                  )
            """),
            {"code": DRIVER_CE_DEFAULT_CODE},
        )


def downgrade() -> None:
    pass
