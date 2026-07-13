"""Backfill empty active document rulesets for the default dev tenant.

Revision ID: 202605121400_def_ruleset
Revises: 202605140900_ch_snap
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence, Union

import sqlalchemy as sa
from alembic import op

DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"
BASELINE_RULESET_COMMENT = "Baseline required-documents matrix (default-tenant backfill)"


def _load_baseline_ruleset_dict() -> dict[str, Any]:
    backend_root = Path(__file__).resolve().parents[2]
    path = backend_root / "app" / "modules" / "documents" / "data" / "sample_ruleset.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _ruleset_required_matrix_empty(json_data: Any) -> bool:
    if json_data is None:
        return True
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except Exception:
            return True
    if not isinstance(json_data, Mapping):
        return True
    req = json_data.get("required")
    if isinstance(req, list) and len(req) > 0:
        return False
    cand = json_data.get("candidate") or {}
    defaults = cand.get("defaults") or {}
    rt = defaults.get("requiredTypes") or []
    return len(rt) == 0


def _column_exists(insp: sa.Inspector, table: str, column: str) -> bool:
    return column in {c["name"] for c in insp.get_columns(table)}

revision: str = "202605121400_def_ruleset"
down_revision: Union[str, None] = "202605140900_ch_snap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("document_ruleset_versions"):
        return

    baseline = _load_baseline_ruleset_dict()
    payload = json.dumps(baseline, ensure_ascii=False)

    rows = conn.execute(
        sa.text(
            "SELECT id, json_data FROM document_ruleset_versions "
            "WHERE tenant_id = :tid AND is_active IS TRUE"
        ),
        {"tid": DEFAULT_TENANT_ID},
    ).fetchall()

    for rid, jd in rows:
        if not _ruleset_required_matrix_empty(jd):
            continue
        conn.execute(
            sa.text(
                "UPDATE document_ruleset_versions SET json_data = CAST(:js AS JSON), "
                "comment = :cm WHERE id = :id"
            ),
            {"js": payload, "cm": BASELINE_RULESET_COMMENT, "id": rid},
        )

    global_rows = conn.execute(
        sa.text(
            "SELECT id, json_data FROM document_ruleset_versions "
            "WHERE tenant_id = :tid AND own_company_id IS NULL AND is_active IS TRUE"
        ),
        {"tid": DEFAULT_TENANT_ID},
    ).fetchall()
    if any(not _ruleset_required_matrix_empty(jd) for _rid, jd in global_rows):
        return

    mv = conn.execute(
        sa.text(
            "SELECT COALESCE(MAX(version), 0) FROM document_ruleset_versions "
            "WHERE tenant_id = :tid AND own_company_id IS NULL"
        ),
        {"tid": DEFAULT_TENANT_ID},
    ).scalar()
    next_v = int(mv or 0) + 1
    insert_params = {
        "id": str(uuid.uuid4()),
        "tid": DEFAULT_TENANT_ID,
        "ver": next_v,
        "js": payload,
        "cm": BASELINE_RULESET_COMMENT,
    }
    if _column_exists(insp, "document_ruleset_versions", "signature"):
        conn.execute(
            sa.text(
                "INSERT INTO document_ruleset_versions ("
                "id, tenant_id, own_company_id, version, json_data, comment, "
                "is_active, signature, created_at"
                ") VALUES ("
                ":id, :tid, NULL, :ver, CAST(:js AS JSON), :cm, TRUE, '', CURRENT_TIMESTAMP"
                ")"
            ),
            insert_params,
        )
    else:
        conn.execute(
            sa.text(
                "INSERT INTO document_ruleset_versions ("
                "id, tenant_id, own_company_id, version, json_data, comment, "
                "is_active, created_at"
                ") VALUES ("
                ":id, :tid, NULL, :ver, CAST(:js AS JSON), :cm, TRUE, CURRENT_TIMESTAMP"
                ")"
            ),
            insert_params,
        )


def downgrade() -> None:
    """Irreversible data repair (empty-matrix backfill)."""
    pass
