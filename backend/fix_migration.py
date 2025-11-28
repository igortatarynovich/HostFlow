from pathlib import Path

VERS = Path("/app/alembic/versions")

# ---------- 1) merge-heads ----------
merge = """\"\"\"merge heads\"\"\"

from alembic import op
import sqlalchemy as sa

revision = "86f07bc7ad35"
down_revision = ("19712a57289c", "d65aef96810d")
branch_labels = None
depends_on = None

def upgrade() -> None:
    # merge-only revision
    pass

def downgrade() -> None:
    pass
"""
(VERS / "86f07bc7ad35_merge_heads.py").write_text(merge, encoding="utf-8")

# ---------- 2) enum migration ----------
mig = """\"\"\"migrate candidate stage to long labels\"\"\"

from alembic import op
import sqlalchemy as sa

revision = "d65aef96810d"
down_revision = "3647bac7d477"
branch_labels = None
depends_on = None

TABLE = "candidates"
COLUMN = "stage"

OLD_ENUM = "candidatestage"
ALL_ENUM = "candidatestage_all"
NEW_ENUM = "candidatestage_new"

OLD_SHORT_VALUES = [
    "Новый",
    "Контакт установлен",
    "Ожидаем документы",
    "Документы получены",
    "Заказ разрешения",
    "Виза",
    "Красная бумага",
    "Готов к выезду",
    "Планируем приезд",
    "На базе клиента",
    "Трудоустроен",
    "Отклонён",
]

NEW_LONG_VALUES = [
    "Новый",
    "Контакт установлен",
    "Ожидаем документы",
    "Документы получены",
    "Заказ разрешения на работу",
    "Виза",
    "Красная бумага заказана",
    "Готов к выезду",
    "Выехал в рейс",
    "Планируем приезд",
    "На базе клиента",
    "Прошел пробный период",
    "Трудоустроен",
    "Отклонён",
]

ALL_VALUES = []
_seen = set()
for v in OLD_SHORT_VALUES + NEW_LONG_VALUES:
    if v not in _seen:
        _seen.add(v)
        ALL_VALUES.append(v)

def upgrade() -> None:
    bind = op.get_bind()

    # 1) временный тип: старые+новые
    sa.Enum(*ALL_VALUES, name=ALL_ENUM).create(bind)

    # 2) привести колонку к временному типу через ::text
    op.execute(sa.text(
        f"ALTER TABLE \\"{TABLE}\\" ALTER COLUMN \\"{COLUMN}\\" "
        f"TYPE {ALL_ENUM} USING \\"{COLUMN}\\"::text::{ALL_ENUM}"
    ))

    # 3) обновить старые значения на длинные (через сравнение по ::text)
    op.execute(sa.text(
        f"UPDATE \\"{TABLE}\\" SET \\"{COLUMN}\\" = CAST(:new AS {ALL_ENUM}) "
        f"WHERE \\"{COLUMN}\\"::text = :old"
    ).bindparams(old="Красная бумага", new="Красная бумага заказана"))

    op.execute(sa.text(
        f"UPDATE \\"{TABLE}\\" SET \\"{COLUMN}\\" = CAST(:new AS {ALL_ENUM}) "
        f"WHERE \\"{COLUMN}\\"::text = :old"
    ).bindparams(old="Заказ разрешения", new="Заказ разрешения на работу"))

    # 4) финальный тип: только новые
    sa.Enum(*NEW_LONG_VALUES, name=NEW_ENUM).create(bind)

    # 5) перевести колонку на финальный тип
    op.execute(sa.text(
        f"ALTER TABLE \\"{TABLE}\\" ALTER COLUMN \\"{COLUMN}\\" "
        f"TYPE {NEW_ENUM} USING \\"{COLUMN}\\"::text::{NEW_ENUM}"
    ))

    # 6) убрать старый тип, переименовать финальный в рабочий, удалить временный
    op.execute(sa.text(f"DROP TYPE {OLD_ENUM}"))
    op.execute(sa.text(f"ALTER TYPE {NEW_ENUM} RENAME TO {OLD_ENUM}"))
    op.execute(sa.text(f"DROP TYPE {ALL_ENUM}"))

def downgrade() -> None:
    pass
"""
(VERS / "d65aef96810d_migrate_candidate_stage_to_long_labels.py").write_text(
    mig, encoding="utf-8"
)

print("OK: files written")
