"""Seed driver_ce_default candidate profile per tenant and assign to vacancies without profile.

Revision ID: 202602080002
Revises: 202602080001
Create Date: 2026-02-08

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "202602080002"
down_revision: Union[str, Sequence[str], None] = "202602080001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DRIVER_CE_DEFAULT_CODE = "driver_ce_default"


def upgrade() -> None:
    """For each tenant: create driver_ce_default profile if missing, set vacancy.candidate_profile_id where null."""
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"
    now = sa.func.current_timestamp() if not is_sqlite else sa.text("(datetime('now'))")

    # Get all tenant ids
    if is_sqlite:
        r = conn.execute(sa.text("SELECT id FROM tenants WHERE is_active = 1"))
    else:
        r = conn.execute(sa.text("SELECT id FROM tenants WHERE is_active = true"))
    tenant_ids = [row[0] for row in r]

    for tenant_id in tenant_ids:
        # Check if driver_ce_default already exists
        if is_sqlite:
            check = conn.execute(
                sa.text(
                    "SELECT id FROM candidate_profiles WHERE tenant_id = :tid AND code = :code"
                ),
                {"tid": tenant_id, "code": DRIVER_CE_DEFAULT_CODE},
            )
        else:
            check = conn.execute(
                sa.text(
                    "SELECT id FROM candidate_profiles WHERE tenant_id = :tid AND code = :code"
                ),
                {"tid": tenant_id, "code": DRIVER_CE_DEFAULT_CODE},
            )
        row = check.fetchone()
        if row:
            profile_id = row[0]
        else:
            profile_id = str(uuid.uuid4())
            # Full config: all card fields + driver docs (same as "no profile" behavior)
            config_json = (
                '{"field_configs":['
                '{"field_key":"first_name","field_type":"text","label":"Имя","required":false,"visible":true,"order":1},'
                '{"field_key":"last_name","field_type":"text","label":"Фамилия","required":false,"visible":true,"order":2},'
                '{"field_key":"email","field_type":"text","label":"Email","required":false,"visible":true,"order":3},'
                '{"field_key":"phone","field_type":"text","label":"Телефон","required":false,"visible":true,"order":4},'
                '{"field_key":"preferred_contact","field_type":"text","label":"Предпочитаемый контакт","required":false,"visible":true,"order":5},'
                '{"field_key":"birth_date","field_type":"date","label":"Дата рождения","required":false,"visible":true,"order":6},'
                '{"field_key":"citizenship","field_type":"text","label":"Гражданство","required":false,"visible":true,"order":7},'
                '{"field_key":"country_code","field_type":"text","label":"Страна","required":false,"visible":true,"order":8},'
                '{"field_key":"languages","field_type":"text","label":"Языки","required":false,"visible":true,"order":9},'
                '{"field_key":"current_location","field_type":"text","label":"Текущее местоположение","required":false,"visible":true,"order":10},'
                '{"field_key":"experience_eu_years","field_type":"number","label":"Опыт в ЕС (лет)","required":false,"visible":true,"order":11},'
                '{"field_key":"experience_non_eu_years","field_type":"number","label":"Опыт вне ЕС (лет)","required":false,"visible":true,"order":12},'
                '{"field_key":"intl_experience","field_type":"boolean","label":"Международный опыт","required":false,"visible":true,"order":13},'
                '{"field_key":"trailer_types","field_type":"text","label":"Типы прицепов","required":false,"visible":true,"order":14},'
                '{"field_key":"route_types","field_type":"text","label":"Типы маршрутов","required":false,"visible":true,"order":15},'
                '{"field_key":"employment_history","field_type":"text","label":"История занятости","required":false,"visible":true,"order":16},'
                '{"field_key":"poland_stay_basis","field_type":"text","label":"Основание пребывания в Польше","required":false,"visible":true,"order":17},'
                '{"field_key":"eu_routes","field_type":"boolean","label":"Маршруты ЕС","required":false,"visible":true,"order":18},'
                '{"field_key":"frigo_experience","field_type":"boolean","label":"Опыт с холодильниками","required":false,"visible":true,"order":19},'
                '{"field_key":"has_adr","field_type":"boolean","label":"ADR","required":false,"visible":true,"order":20}'
                '],"document_configs":['
                '{"document_type_id":"identity_document","required":true},'
                '{"document_type_id":"qualification_code95","required":true},'
                '{"document_type_id":"tachograph_card","required":false},'
                '{"document_type_id":"driver_license","required":false},'
                '{"document_type_id":"swiadectwo_kierowcy","required":false},'
                '{"document_type_id":"medical_certificate","required":false}'
                '],"stage_configs":[]}'
            )
            if is_sqlite:
                conn.execute(
                    sa.text("""
                        INSERT INTO candidate_profiles
                        (id, tenant_id, code, name, description, client_id, funnel_id, config, is_active, is_system, owner_user_id, notes, created_at, updated_at)
                        VALUES (:id, :tid, :code, :name, :desc, NULL, NULL, :config, 1, 1, NULL, :notes, datetime('now'), datetime('now'))
                    """),
                    {
                        "id": profile_id,
                        "tid": tenant_id,
                        "code": DRIVER_CE_DEFAULT_CODE,
                        "name": "Driver CE (default)",
                        "desc": "Профиль по умолчанию для водителей CE. Нельзя редактировать; можно создать копию.",
                        "config": config_json,
                        "notes": "Системный профиль по умолчанию.",
                    },
                )
            else:
                conn.execute(
                    sa.text("""
                        INSERT INTO candidate_profiles
                        (id, tenant_id, code, name, description, client_id, funnel_id, config, is_active, is_system, owner_user_id, notes, created_at, updated_at)
                        VALUES (:id, :tid, :code, :name, :desc, NULL, NULL, CAST(:config AS jsonb), true, true, NULL, :notes, now(), now())
                    """),
                    {
                        "id": profile_id,
                        "tid": tenant_id,
                        "code": DRIVER_CE_DEFAULT_CODE,
                        "name": "Driver CE (default)",
                        "desc": "Профиль по умолчанию для водителей CE. Нельзя редактировать; можно создать копию.",
                        "config": config_json,
                        "notes": "Системный профиль по умолчанию.",
                    },
                )

        # Update vacancies without profile
        if is_sqlite:
            conn.execute(
                sa.text(
                    "UPDATE vacancies SET candidate_profile_id = :pid WHERE tenant_id = :tid AND candidate_profile_id IS NULL"
                ),
                {"pid": profile_id, "tid": tenant_id},
            )
        else:
            conn.execute(
                sa.text(
                    "UPDATE vacancies SET candidate_profile_id = :pid WHERE tenant_id = :tid AND candidate_profile_id IS NULL"
                ),
                {"pid": profile_id, "tid": tenant_id},
            )


def downgrade() -> None:
    """Unset candidate_profile_id for vacancies using driver_ce_default; delete profile."""
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE vacancies SET candidate_profile_id = NULL "
            "WHERE candidate_profile_id IN (SELECT id FROM candidate_profiles WHERE code = :code)"
        ),
        {"code": DRIVER_CE_DEFAULT_CODE},
    )
    conn.execute(
        sa.text("DELETE FROM candidate_profiles WHERE code = :code"),
        {"code": DRIVER_CE_DEFAULT_CODE},
    )
