"""Rename documents.status_new to documents.status.

Revision ID: 202609220001_documents_status_column
Revises: 202609131001_start_allowed_exceptions
Create Date: 2026-09-22

``202512150001_unify_documents_module`` inspects columns once, then adds
``status_new`` and later asks that same snapshot whether ``status_new``
exists. On a database that still had ``status`` at inspect time, the old
column is dropped and the rename is skipped. ``alembic upgrade heads``
therefore leaves ``documents.status_new`` while ``Document.status`` reads
``documents.status``.

Databases that already have ``status`` are unchanged.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202609220001_documents_status_column"
down_revision: Union[str, None] = "202609131001_start_allowed_exceptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _document_columns() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns("documents")}


def upgrade() -> None:
    columns = _document_columns()
    if "status" in columns or "status_new" not in columns:
        return
    op.alter_column("documents", "status_new", new_column_name="status")


def downgrade() -> None:
    # Reversing the rename would put fresh installs back on the broken
    # column and would also rename ``status`` on databases that already
    # had the ORM column before this revision. Leave the healed name.
    return
