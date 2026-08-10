"""ADR-036: remap legacy job/portal role strings to trust roles + presets.

Bridge revision for checkouts that already applied ADR-035 pipeline migrations
(`202608070002`). Same body as integration `202608100001_adr036_remap_legacy_trust_roles`
(idempotent). On merge of integration, keep both; remap is a no-op if already applied.

Revision ID: 202608110001_adr036_remap_legacy_trust_roles
Revises: 202608070002_funnel_stage_labels_i18n
Create Date: 2026-08-10 12:00:00.000000

- users.role / user_memberships.role / user_invites.role → administrator|employee|viewer
- preferences.preset_id + access_context for job/portal semantics
- relax ck_users_supervisor_role so employee may have supervisor_id
"""

from __future__ import annotations

import json
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608110001_adr036_remap_legacy_trust_roles"
down_revision: RevisionType = "202608070002_funnel_stage_labels_i18n"
branch_labels: RevisionType = None
depends_on: RevisionType = None

# legacy role string → (trust role, optional preset_id, optional access_context)
_ROLE_MAP: dict[str, tuple[str, str | None, str | None]] = {
    "recruiter": ("employee", "recruiter", None),
    "supervisor": ("employee", "team_lead", None),
    "manager": ("employee", "team_lead", None),
    "lead": ("employee", "team_lead", None),
    "hr": ("employee", "hr", None),
    "hr_officer": ("employee", "hr", None),
    "people_ops": ("employee", "hr", None),
    "compliance_officer": ("employee", "compliance", None),
    "compliance": ("employee", "compliance", None),
    "docs_officer": ("employee", "compliance", None),
    "client_manager": ("viewer", "portal_guest", "portal"),
    "client_processor": ("viewer", "portal_guest", "portal"),
    "client": ("viewer", "portal_guest", "portal"),
    "processor": ("viewer", "portal_guest", "portal"),
    "admin": ("administrator", None, None),
    "owner": ("administrator", None, None),
    "user": ("viewer", None, None),
}


def _bind_dialect() -> str:
    return op.get_bind().dialect.name


def _merge_prefs(raw: Any, preset_id: str | None, access_context: str | None) -> dict[str, Any]:
    prefs: dict[str, Any]
    if isinstance(raw, dict):
        prefs = dict(raw)
    elif isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            prefs = dict(parsed) if isinstance(parsed, dict) else {}
        except Exception:
            prefs = {}
    else:
        prefs = {}
    if preset_id and not str(prefs.get("preset_id") or "").strip():
        prefs["preset_id"] = preset_id
    if access_context:
        prefs["access_context"] = access_context
    elif preset_id == "portal_guest":
        prefs["access_context"] = "portal"
    return prefs


def _remap_table_role_column(table: str, role_col: str = "role") -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"SELECT id, {role_col} FROM {table}")).mappings().all()
    for row in rows:
        raw = str(row[role_col] or "").strip().lower()
        mapped = _ROLE_MAP.get(raw)
        if not mapped:
            continue
        trust, _preset, _ctx = mapped
        bind.execute(
            sa.text(f"UPDATE {table} SET {role_col} = :trust WHERE id = :id"),
            {"trust": trust, "id": row["id"]},
        )


def _remap_users_with_preferences() -> None:
    bind = op.get_bind()
    dialect = _bind_dialect()
    rows = bind.execute(sa.text("SELECT id, role, preferences FROM users")).mappings().all()
    for row in rows:
        raw = str(row["role"] or "").strip().lower()
        mapped = _ROLE_MAP.get(raw)
        if not mapped:
            # still normalize admin/owner aliases if somehow present as enum labels
            continue
        trust, preset, access_ctx = mapped
        prefs = _merge_prefs(row["preferences"], preset, access_ctx)
        if dialect == "postgresql":
            bind.execute(
                sa.text(
                    "UPDATE users SET role = :trust, preferences = CAST(:prefs AS jsonb) WHERE id = :id"
                ),
                {"trust": trust, "prefs": json.dumps(prefs), "id": row["id"]},
            )
        else:
            bind.execute(
                sa.text("UPDATE users SET role = :trust, preferences = :prefs WHERE id = :id"),
                {"trust": trust, "prefs": json.dumps(prefs), "id": row["id"]},
            )


def _remap_invites() -> None:
    bind = op.get_bind()
    dialect = _bind_dialect()
    insp = sa.inspect(bind)
    if not insp.has_table("user_invites"):
        return
    cols = {c["name"] for c in insp.get_columns("user_invites")}
    if "role" not in cols:
        return
    has_meta = "metadata_json" in cols
    select_cols = "id, role" + (", metadata_json" if has_meta else "")
    rows = bind.execute(sa.text(f"SELECT {select_cols} FROM user_invites")).mappings().all()
    for row in rows:
        raw = str(row["role"] or "").strip().lower()
        mapped = _ROLE_MAP.get(raw)
        if not mapped:
            continue
        trust, preset, access_ctx = mapped
        params: dict[str, Any] = {"trust": trust, "id": row["id"]}
        if has_meta and preset:
            meta = row.get("metadata_json")
            if isinstance(meta, str) and meta.strip():
                try:
                    meta_obj = json.loads(meta)
                except Exception:
                    meta_obj = {}
            elif isinstance(meta, dict):
                meta_obj = dict(meta)
            else:
                meta_obj = {}
            if not str(meta_obj.get("preset_id") or "").strip():
                meta_obj["preset_id"] = preset
            if access_ctx:
                meta_obj["access_context"] = access_ctx
            params["meta"] = json.dumps(meta_obj)
            if dialect == "postgresql":
                bind.execute(
                    sa.text(
                        "UPDATE user_invites SET role = :trust, "
                        "metadata_json = CAST(:meta AS jsonb) WHERE id = :id"
                    ),
                    params,
                )
            else:
                bind.execute(
                    sa.text(
                        "UPDATE user_invites SET role = :trust, metadata_json = :meta WHERE id = :id"
                    ),
                    params,
                )
        else:
            bind.execute(
                sa.text("UPDATE user_invites SET role = :trust WHERE id = :id"),
                params,
            )


def _ensure_employee_enum_value() -> None:
    """Postgres native enum ``role`` predates ADR-036 and lacks ``employee``.

    ADD VALUE must commit before the new label can be written (PG rule).
    """
    if _bind_dialect() != "postgresql":
        return
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE role ADD VALUE IF NOT EXISTS 'employee'"))


def _relax_supervisor_check() -> None:
    bind = op.get_bind()
    dialect = _bind_dialect()
    insp = sa.inspect(bind)
    if not insp.has_table("users"):
        return
    ck_names = {c["name"] for c in insp.get_check_constraints("users")}
    if "ck_users_supervisor_role" in ck_names:
        op.drop_constraint("ck_users_supervisor_role", "users", type_="check")
    # Employee (and legacy recruiter during dual-read) may report to a supervisor.
    if dialect == "postgresql":
        op.create_check_constraint(
            "ck_users_supervisor_role",
            "users",
            "(supervisor_id IS NULL) OR (lower(role::text) IN ('recruiter', 'employee'))",
        )
    else:
        op.create_check_constraint(
            "ck_users_supervisor_role",
            "users",
            "(supervisor_id IS NULL) OR (lower(role) IN ('recruiter', 'employee'))",
        )


def upgrade() -> None:
    _ensure_employee_enum_value()
    _relax_supervisor_check()
    _remap_users_with_preferences()
    insp = sa.inspect(op.get_bind())
    if insp.has_table("user_memberships"):
        _remap_table_role_column("user_memberships")
    _remap_invites()


def downgrade() -> None:
    # Irreversible data remap (presets cannot reconstruct exact legacy role strings).
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("users"):
        ck_names = {c["name"] for c in insp.get_check_constraints("users")}
        if "ck_users_supervisor_role" in ck_names:
            op.drop_constraint("ck_users_supervisor_role", "users", type_="check")
        dialect = _bind_dialect()
        if dialect == "postgresql":
            op.create_check_constraint(
                "ck_users_supervisor_role",
                "users",
                "(supervisor_id IS NULL) OR (role::text = 'recruiter')",
            )
        else:
            op.create_check_constraint(
                "ck_users_supervisor_role",
                "users",
                "(supervisor_id IS NULL) OR (role = 'recruiter')",
            )
