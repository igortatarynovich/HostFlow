"""Create client-facing funnel for Citronex tenant and attach to driver_ce_default profile.

Revision ID: 202602100900
Revises: 202602080006
Create Date: 2026-02-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202602100900"
# Важно: цепляемся к последней существующей голове, чтобы не создавать новую ветку.
# На момент разработки это 202608090001_remove_citronex_company_name.
down_revision: Union[str, Sequence[str], None] = "202608090001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return getattr(bind.dialect, "name", None) == "postgresql"


def upgrade() -> None:
    """Ensure Citronex has a client funnel with client stages and attach it to driver_ce_default profile.

    ВАЖНО:
    - Используем существующий client-tenant Citronex (по известному UUID и/или имени).
    - Создаём отдельную воронку только для клиента, не трогая агентскую.
    - Воронка включает только клиентские этапы (после handoff) с уже используемыми system codes.
    - Привязываем воронку к профилю driver_ce_default, чтобы карточка брала этапы из этой воронки.
    """
    bind = op.get_bind()

    # Идентификаторы Citronex tenant / company уже фиксируются в миграциях handoff'ов
    CITRONEX_TENANT_ID = "517319d0-b53e-493d-9ac8-40f23091a35d"

    funnels = sa.table(
        "funnels",
        sa.column("id", sa.String),
        sa.column("tenant_id", sa.String),
        sa.column("type", sa.String),
        sa.column("name", sa.String),
        sa.column("is_default", sa.Boolean),
    )
    stages = sa.table(
        "funnel_stages",
        sa.column("id", sa.String),
        sa.column("funnel_id", sa.String),
        sa.column("code", sa.String),
        sa.column("label", sa.String),
        sa.column("order", sa.Integer),
        sa.column("is_terminal", sa.Boolean),
    )
    candidate_profiles = sa.table(
        "candidate_profiles",
        sa.column("id", sa.String),
        sa.column("tenant_id", sa.String),
        sa.column("code", sa.String),
        sa.column("funnel_id", sa.String),
    )

    # Проверяем, что tenant существует и это действительно Citronex
    tenant_row = bind.execute(
        sa.text(
            "SELECT id, name FROM tenants WHERE id = :tid OR LOWER(name) LIKE '%citronex%' LIMIT 1"
        ),
        {"tid": CITRONEX_TENANT_ID},
    ).fetchone()
    if not tenant_row:
        # Ничего не делаем, если этого клиента нет в инсталляции
        return

    tenant_id = str(tenant_row[0])

    # Ищем уже существующую клиентскую воронку для Citronex
    existing_funnel = bind.execute(
        sa.select(funnels.c.id)
        .where(
            sa.and_(
                funnels.c.tenant_id == tenant_id,
                funnels.c.type == "candidate",
                funnels.c.name == "Citronex – client",
            )
        )
        .limit(1)
    ).fetchone()

    import uuid

    if existing_funnel:
        funnel_id = str(existing_funnel[0])
    else:
        funnel_id = str(uuid.uuid4())
        bind.execute(
            funnels.insert().values(
                id=funnel_id,
                tenant_id=tenant_id,
                type="candidate",
                name="Citronex – client",
                is_default=False,
            )
        )

        # Клиентские этапы после handoff — только коды, которые уже существуют в STAGES/метаданных
        client_stages = [
            # code, label, order, is_terminal
            ("processing_by_client", "Procesowany przez zleceniodawcę", 0, False),
            ("docs_submitted_permit", "Złożono dokumenty na zezwolenie", 1, False),
            ("permit_received", "Otrzymano zezwolenie", 2, False),
            ("on_trip", "W trakcie zatrudnienia", 3, False),
            ("handoff_returned", "Zwrócono", 4, False),
            ("rejected", "Odrzucony (powód)", 5, True),
            ("declined", "Kandydat zrezygnował (powód)", 6, True),
            ("employed", "Zatrudniony", 7, True),
        ]

        # На всякий случай не дублируем коды внутри воронки
        seen_codes: set[str] = set()
        order_idx = 0
        for code, label, ord_val, is_terminal in client_stages:
            if code in seen_codes:
                continue
            seen_codes.add(code)
            bind.execute(
                stages.insert().values(
                    id=str(uuid.uuid4()),
                    funnel_id=funnel_id,
                    code=code,
                    label=label,
                    order=ord_val if ord_val is not None else order_idx,
                    is_terminal=is_terminal,
                )
            )
            order_idx += 1

    # Привязываем воронку к профилю driver_ce_default для этого tenant'а.
    DRIVER_CE_DEFAULT_CODE = "driver_ce_default"
    profile_row = bind.execute(
        sa.select(candidate_profiles.c.id, candidate_profiles.c.funnel_id)
        .where(
            sa.and_(
                candidate_profiles.c.tenant_id == tenant_id,
                candidate_profiles.c.code == DRIVER_CE_DEFAULT_CODE,
            )
        )
        .limit(1)
    ).fetchone()

    if profile_row:
        current_funnel_id = profile_row[1]
        if not current_funnel_id:
            # Только если профиль ещё не привязан к другой воронке — не трогаем кастомные настройки.
            bind.execute(
                candidate_profiles.update()
                .where(
                    sa.and_(
                        candidate_profiles.c.tenant_id == tenant_id,
                        candidate_profiles.c.code == DRIVER_CE_DEFAULT_CODE,
                    )
                )
                .values(funnel_id=funnel_id)
            )


def downgrade() -> None:
    # Откатывать не обязательно: воронка и ссылка на неё безвредны.
    # Но на всякий случай можно оставить как есть.
    pass

