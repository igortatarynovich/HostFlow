"""meta_form_routes: add service_code for Service Inquiry forms.

For forms routed as Service Inquiries (lead_target_type=service_order_lead),
service_code names the catalog service the form sells (e.g. "targeting_ads").
It is carried onto ingested leads so Sales preselects the right Service Order line.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202607081400_mfr_svc_code"
down_revision = "202607081300_svc_cust_ben"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meta_form_routes",
        sa.Column("service_code", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meta_form_routes", "service_code")
