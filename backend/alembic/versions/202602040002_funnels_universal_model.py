"""Universal Funnel model: funnels, funnel_stages, funnel_id on candidates/leads/vacancies.

Revision ID: 202602040002
Revises: 202602040001_leads_add_stage
Create Date: 2026-02-04

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202602040002_funnels_universal_model"
down_revision = "202602040001_leads_add_stage"
branch_labels = None
depends_on = None

# Default candidate stages from backend.app.constants.stages
DEFAULT_STAGES = [
    ("new", "Новый", 0),
    ("no_answer", "Не отвечает", 1),
    ("contacted", "Контакт установлен", 2),
    ("questionnaire_submitted", "Анкета заполнена", 3),
    ("docs_wait", "Ожидаем документы", 4),
    ("docs_got", "Документы получены", 5),
    ("permit_ordered", "Заказ разрешения на работу", 6),
    ("permit_received", "Разрешение на работу получено", 7),
    ("visa", "Виза", 8),
    ("red_paper", "Красная бумага заказана", 9),
    ("trip_plan", "Планируем приезд", 10),
    ("at_client", "На базе клиента", 11),
    ("on_trip", "Выехал в рейс", 12),
    ("probation_ok", "Прошёл пробный период", 13),
    ("employed", "Трудоустроен", 14),
    ("rejected", "Отклонён", 15),
    ("declined", "Отказался", 16),
    ("ready_for_handoff", "Готов к передаче", 17),
    ("processing_by_client", "Обработка заказчиком", 18),
    ("docs_submitted_permit", "Документы поданы на разрешение", 19),
    ("handoff_returned", "Возвращён", 20),
]
TERMINAL_CODES = {"probation_ok", "rejected", "declined"}


def upgrade() -> None:
    op.create_table(
        "funnels",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("type", sa.String(length=32), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "funnel_stages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "funnel_id",
            sa.String(length=36),
            sa.ForeignKey("funnels.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_terminal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_unique_constraint(
        "uq_funnel_stage_code", "funnel_stages", ["funnel_id", "code"]
    )

    # Add funnel_id to candidates, leads, vacancies
    op.add_column(
        "candidates",
        sa.Column(
            "funnel_id",
            sa.String(length=36),
            sa.ForeignKey("funnels.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    op.add_column(
        "leads",
        sa.Column(
            "funnel_id",
            sa.String(length=36),
            sa.ForeignKey("funnels.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    op.add_column(
        "vacancies",
        sa.Column(
            "funnel_id",
            sa.String(length=36),
            sa.ForeignKey("funnels.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # Seed: create default funnel per tenant and global fallback
    # Use raw SQL to insert without depending on app (tenant-agnostic seed)
    conn = op.get_bind()
    import uuid

    default_funnel_id = str(uuid.uuid4())
    conn.execute(
        sa.text(
            """
            INSERT INTO funnels (id, tenant_id, type, name, is_default)
            VALUES (:id, 'default', 'candidate', 'Driver Recruitment', true)
            """
        ),
        {"id": default_funnel_id},
    )
    for code, label, ord_val in DEFAULT_STAGES:
        conn.execute(
            sa.text(
                """
                INSERT INTO funnel_stages (id, funnel_id, code, label, "order", is_terminal)
                VALUES (:id, :funnel_id, :code, :label, :ord, :is_terminal)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "funnel_id": default_funnel_id,
                "code": code,
                "label": label,
                "ord": ord_val,
                "is_terminal": code in TERMINAL_CODES,
            },
        )


def downgrade() -> None:
    op.drop_column("candidates", "funnel_id")
    op.drop_column("leads", "funnel_id")
    op.drop_column("vacancies", "funnel_id")
    op.drop_constraint("uq_funnel_stage_code", "funnel_stages", type_="unique")
    op.drop_table("funnel_stages")
    op.drop_table("funnels")
