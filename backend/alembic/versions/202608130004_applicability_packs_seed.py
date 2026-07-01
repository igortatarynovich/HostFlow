"""M4 applicability packs seed.

Revision ID: 202608130004_applicability_packs_seed
Revises: 09ded874040a
Create Date: 2026-08-13 13:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any, Sequence, Union
from uuid import uuid4

from alembic import op
from sqlalchemy import text

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608130004_applicability_packs_seed"
down_revision: RevisionType = "09ded874040a"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def _j(v: Any) -> str:
    return json.dumps(v, ensure_ascii=True)


def _pack_id(conn, code: str, *, country_code: str | None, industry_code: str | None, name: str) -> str:
    row = conn.execute(text("SELECT id FROM ref_packs WHERE lower(code)=lower(:c)"), {"c": code}).mappings().first()
    if row:
        pid = str(row["id"])
        conn.execute(
            text(
                """
                UPDATE ref_packs
                SET country_code=:country_code, industry_code=:industry_code,
                    status='active', version=1, published_at=CURRENT_TIMESTAMP, meta=:meta
                WHERE id=:id
                """
            ),
            {"id": pid, "country_code": country_code, "industry_code": industry_code, "meta": _j({"name": name})},
        )
        return pid
    pid = str(uuid4())
    conn.execute(
        text(
            """
            INSERT INTO ref_packs (id, code, country_code, industry_code, status, version, published_at, meta)
            VALUES (:id, :code, :country_code, :industry_code, 'active', 1, CURRENT_TIMESTAMP, :meta)
            """
        ),
        {"id": pid, "code": code, "country_code": country_code, "industry_code": industry_code, "meta": _j({"name": name})},
    )
    return pid


def _ver_id(conn, code: str) -> str | None:
    row = conn.execute(
        text(
            """
            SELECT v.id
            FROM ref_document_type_versions v
            JOIN ref_document_types t ON t.id = v.document_type_id
            WHERE lower(t.code)=lower(:code) AND v.version_code='v1'
            """
        ),
        {"code": code},
    ).mappings().first()
    return str(row["id"]) if row else None


def upgrade() -> None:
    conn = op.get_bind()

    packs = [
        ("pl_base_hr", "PL", "hr", "Poland Base HR", ["passport", "tax_declaration", "employment_contract", "zus_zua", "zus_zza"]),
        ("pl_non_eu_worker", "PL", "hr", "Poland Non-EU Worker", ["work_permit", "residence_card", "visa"]),
        ("pl_transport_driver", "PL", "transport", "Poland Transport Driver", ["driver_license", "code_95", "tachograph_card", "medical_certificate", "psychotest"]),
        ("eu_driver_compliance", None, "transport", "EU Driver Compliance", ["driver_license", "code_95", "tachograph_card"]),
        ("client_specific_requirements", None, None, "Client Specific Requirements", ["other"]),
    ]

    for code, cc, ic, name, doc_codes in packs:
        pid = _pack_id(conn, code, country_code=cc, industry_code=ic, name=name)
        conn.execute(text("DELETE FROM ref_pack_items WHERE pack_id=:pid"), {"pid": pid})
        conn.execute(text("DELETE FROM ref_pack_rules WHERE pack_id=:pid"), {"pid": pid})
        for d in doc_codes:
            vid = _ver_id(conn, d)
            if not vid:
                continue
            role = "optional" if d in {"other", "zus_zza", "visa"} else "required"
            conn.execute(
                text("INSERT INTO ref_pack_items (id, pack_id, document_type_version_id, role) VALUES (:id,:pid,:vid,:role)"),
                {"id": str(uuid4()), "pid": pid, "vid": vid, "role": role},
            )


def downgrade() -> None:
    return None
