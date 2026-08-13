# backend/app/db/seeds/dev_full_seed.py
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, text

from backend.app.db.seeds.notifications import seed_notification_templates

# ------------ CONFIG ------------
TENANT_ID = "11111111-1111-1111-1111-111111111111"
NOW = datetime.utcnow()
RND = random.Random(42)  # стабильная "случайность"
DB_URL = os.getenv(
    "SYNC_DATABASE_URL", "sqlite:////Users/victoria_tatarynovich/HostFlow/app.db"
)
# Админ по умолчанию (можно переопределить через переменные окружения)
ADMIN_EMAIL = os.getenv("DEV_ADMIN_EMAIL", "admin@hostflow.dev")
ADMIN_PASSWORD = os.getenv("DEV_ADMIN_PASSWORD", "Admin@025")
ADMIN_FULL_NAME = os.getenv("DEV_ADMIN_FULL_NAME", "HostFlow Admin")
DEFAULT_ADMIN_HASH = os.getenv(
    "DEV_ADMIN_PASSWORD_HASH",
    "$2b$12$w/mzFidqtADH961LuyKsfO5X8iIsduNW6wr1k3utXUeeglyj8hBme",
)
# --------------------------------


# ---------- helpers ----------
def gen_uuid() -> str:
    return str(uuid.uuid4())


def dt_ago(days: int) -> str:
    return (NOW - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

def dt_in_hours(hours: int) -> str:
    return (NOW + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")


def rand_choice(seq):
    return RND.choice(seq)


def has_column(conn, table: str, column: str) -> bool:
    # SQLite / generic способ
    # для SQLite работает PRAGMA; для PG — information_schema
    dialect = conn.engine.dialect.name
    if dialect == "sqlite":
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        return any(r[1] == column for r in rows)
    else:
        res = conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = :t AND column_name = :c
                """
            ),
            {"t": table, "c": column},
        ).fetchone()
        return res is not None


def has_table(conn, table: str) -> bool:
    dialect = conn.engine.dialect.name
    if dialect == "sqlite":
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchall()
        return bool(rows)
    row = conn.exec_driver_sql(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = %s
    """,
        (table,),
    ).fetchone()
    return bool(row)


def select_one(conn, sql: str, params: dict):
    return conn.execute(text(sql), params).fetchone()


def ensure_meta_lead_settings(conn):
    if not has_table(conn, "meta_lead_settings"):
        return

    existing = select_one(
        conn,
        "SELECT tenant_id FROM meta_lead_settings WHERE tenant_id = :tenant_id",
        {"tenant_id": TENANT_ID},
    )
    if not existing:
        conn.execute(
            text(
                """
                INSERT INTO meta_lead_settings
                (tenant_id, auto_create_enabled, mask_pii_in_logs, pull_field_data_from_graph, reroute_after_hours, webhook_url, webhook_verify_token, created_at, updated_at)
                VALUES
                (:tenant_id, :auto_create_enabled, :mask_pii_in_logs, :pull_field_data_from_graph, :reroute_after_hours, :webhook_url, :webhook_verify_token, :created_at, :updated_at)
                """
            ),
            {
                "tenant_id": TENANT_ID,
                "auto_create_enabled": True,
                "mask_pii_in_logs": True,
                "pull_field_data_from_graph": True,
                "reroute_after_hours": 6,
                "webhook_url": "https://api.hostflow.dev/api/v1/leads/meta/webhook",
                "webhook_verify_token": "hostflow123",
                "created_at": dt_ago(1),
                "updated_at": dt_ago(1),
            },
        )

        if has_table(conn, "meta_ads_map"):
            mapped = select_one(
                conn,
                "SELECT ad_id FROM meta_ads_map WHERE tenant_id = :tenant_id LIMIT 1",
                {"tenant_id": TENANT_ID},
            )
            if not mapped:
                vacancy = select_one(
                    conn,
                    """
                    SELECT id
                    FROM vacancies
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at ASC
                    LIMIT 1
                    """,
                    {"tenant_id": TENANT_ID},
                )
                if vacancy:
                    conn.execute(
                        text(
                            """
                            INSERT INTO meta_ads_map (ad_id, tenant_id, vacancy_id, note, created_at)
                            VALUES (:ad_id, :tenant_id, :vacancy_id, :note, :created_at)
                            """
                        ),
                        {
                            "ad_id": 987654321,
                            "tenant_id": TENANT_ID,
                            "vacancy_id": vacancy[0],
                            "note": "Dev seed mapping",
                            "created_at": dt_ago(1),
                        },
                    )


# ---------- seeds: users/recruiters ----------
def seeded_users():
    # рекрутёры
    full_names = [
        "Anna Kowalska",
        "Piotr Nowak",
        "Viktoria Tatarynovich",
        "Marek Zieliński",
    ]
    emails = [
        "anna.k@hostflow.dev",
        "piotr.n@hostflow.dev",
        "viktoria.t@hostflow.dev",
        "marek.z@hostflow.dev",
    ]
    out = []
    for i in range(4):
        uid = gen_uuid()
        out.append(
            {
                "id": uid,
                "email": emails[i],
                "password_hash": f"dev-seed-{uid.replace('-', '')[:8]}",  # заглушка
                "role": "employee",
                "created_at": dt_ago(RND.randint(10, 60)),
                "updated_at": dt_ago(RND.randint(1, 10)),
                "short_id": uid.replace("-", "")[:8],
                "full_name": full_names[i],
                "tenant_id": TENANT_ID,
                "is_active": True,
                "extra": json.dumps(
                    {
                        "timezone": "Europe/Warsaw",
                        "phone_code": "48",
                        "phone_local": f"5{RND.randint(0, 9)}{RND.randint(1000000, 9999999)}",
                        "tags": ["recruiter", "dev-seed"],
                        "note": "Seed user for development",
                    }
                ),
                "preferences": json.dumps(
                    {
                        "language": "pl",
                        "notifications": {"email": True, "sms": False},
                        "ui": {"theme": "system", "density": "comfortable"},
                        "preset_id": "recruiter",
                    }
                ),
                "supervisor_id": None,
                "deleted_at": None,
            }
        )
    return out


def ensure_document_templates(conn):
    if not has_table(conn, "document_templates"):
        return

    templates = [
        {
            "code": "driver_ce",
            "name": "Driver CE Poland",
            "documents": [
                {"doc_type": "pesel", "required": True},  # PESEL always required
                {"doc_type": "identity_document", "required": True},
                {"doc_type": "driver_license", "required": True},
                {"doc_type": "qualification_code95", "required": True},
                {"doc_type": "tachograph_card", "process_type": "tachograph_card", "requested_from": "agency"},
                {"doc_type": "medical_certificate", "required": True},
                {"doc_type": "criminal_record", "required": True},
                {"doc_type": "insurance", "requested_from": "employer", "required": True},
                {"doc_type": "photo", "meta": {"title": "Profile photo"}},
                {"doc_type": "bank_account_confirmation"},
                {"doc_type": "contract", "requested_from": "employer", "required": True},
                {"doc_type": "assignment", "requested_from": "employer"},
                {"doc_type": "bhp", "requested_from": "employer"},
                {"doc_type": "accommodation", "requested_from": "employer"},
                {"doc_type": "work_permit", "process_type": "work_permit", "requested_from": "agency"},
                {"doc_type": "visa", "process_type": "visa", "requested_from": "driver"},
                {"doc_type": "residence_card", "process_type": "residence_card"},
                {"doc_type": "driver_license_exchange", "process_type": "driver_license_exchange", "requested_from": "agency"},
                {"doc_type": "swiadectwo_kierowcy", "process_type": "swiadectwo_kierowcy", "requested_from": "agency"},
            ],
        },
        {
            "code": "warehouse",
            "name": "Warehouse Worker",
            "documents": [
                {"doc_type": "pesel", "required": True},  # PESEL always required
                {"doc_type": "identity_document", "required": True},
                {"doc_type": "medical_certificate", "required": True},
                {"doc_type": "criminal_record", "required": True},
                {"doc_type": "photo", "meta": {"title": "Profile photo"}},
                {"doc_type": "bank_account_confirmation"},
                {"doc_type": "contract", "requested_from": "employer", "required": True},
                {"doc_type": "insurance", "requested_from": "employer"},
                {"doc_type": "bhp", "requested_from": "employer", "required": True},
                {"doc_type": "accommodation", "requested_from": "employer"},
            ],
        },
    ]

    for tpl in templates:
        payload = {
            "tenant_id": TENANT_ID,
            "code": tpl["code"],
            "name": tpl["name"],
            "documents": json.dumps(tpl["documents"], ensure_ascii=False),
            "is_active": True,
            "created_by": None,
            "created_at": dt_ago(1),
            "updated_at": dt_ago(0),
        }

        existing = select_one(
            conn,
            "SELECT id FROM document_templates WHERE tenant_id=:tenant_id AND code=:code",
            {"tenant_id": TENANT_ID, "code": tpl["code"]},
        )

        if existing:
            conn.execute(
                text(
                    """
                    UPDATE document_templates
                    SET name=:name,
                        documents=:documents,
                        is_active=:is_active,
                        updated_at=:updated_at
                    WHERE id=:id
                """
                ),
                {
                    "id": existing[0],
                    **payload,
                },
            )
        else:
            tpl_id = gen_uuid()
            conn.execute(
                text(
                    """
                    INSERT INTO document_templates
                    (id, tenant_id, code, name, documents, is_active, created_by, created_at, updated_at)
                    VALUES
                    (:id, :tenant_id, :code, :name, :documents, :is_active, :created_by, :created_at, :updated_at)
                """
                ),
                {
                    "id": tpl_id,
                    **payload,
                },
            )


def ensure_users(conn, users):
    # не трогаем других пользователей (например, admin@hostflow.dev)
    for u in users:
        found = select_one(
            conn, "SELECT id FROM users WHERE email=:email", {"email": u["email"]}
        )
        if found:
            # обновим основные поля
            conn.execute(
                text("""
                UPDATE users
                SET role=:role,
                    short_id=:short_id,
                    full_name=:full_name,
                    extra=:extra,
                    preferences=:preferences,
                    tenant_id=:tenant_id,
                    is_active=:is_active,
                    updated_at=:updated_at
                WHERE email=:email
            """),
                {
                    "role": u["role"],
                    "short_id": u["short_id"],
                    "full_name": u["full_name"],
                    "extra": u["extra"],
                    "preferences": u["preferences"],
                    "tenant_id": u["tenant_id"],
                    "is_active": True if u.get("is_active") else False,
                    "updated_at": u["updated_at"],
                    "email": u["email"],
                },
            )
            u["id"] = found[0]
        else:
            conn.execute(
                text("""
                INSERT INTO users (id, email, password_hash, role, created_at, updated_at, short_id, full_name, extra, preferences, tenant_id, is_active, supervisor_id, deleted_at)
                VALUES (:id, :email, :password_hash, :role, :created_at, :updated_at, :short_id, :full_name, :extra, :preferences, :tenant_id, :is_active, :supervisor_id, :deleted_at)
            """),
                u,
            )


def _hash_admin_password(password: str) -> str:
    try:
        from passlib.context import CryptContext
    except Exception:
        if password != "Admin@025" and not os.getenv("DEV_ADMIN_PASSWORD_HASH"):
            print("[seed] passlib не установлен — использую дефолтный хеш для администратора")
        return DEFAULT_ADMIN_HASH
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return ctx.hash(password)


def ensure_admin_account(conn):
    if not has_table(conn, "users"):
        return None

    now_dt = datetime.utcnow()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    password_hash = _hash_admin_password(ADMIN_PASSWORD)

    existing = select_one(
        conn,
        "SELECT id FROM users WHERE email = :email",
        {"email": ADMIN_EMAIL},
    )

    base_payload = {
        "email": ADMIN_EMAIL,
        "password_hash": password_hash,
        "role": "administrator",
        "tenant_id": TENANT_ID,
        "is_active": True,
        "updated_at": now_str,
    }

    if existing:
        user_id = existing[0]
        conn.execute(
            text(
                """
                UPDATE users
                SET role=:role,
                    password_hash=:password_hash,
                    tenant_id=:tenant_id,
                    is_active=:is_active,
                    full_name=COALESCE(full_name, :full_name),
                    updated_at=:updated_at
                WHERE id=:id
                """
            ),
            {
                **base_payload,
                "full_name": ADMIN_FULL_NAME,
                "id": user_id,
            },
        )
    else:
        user_id = gen_uuid()
        payload = {
            **base_payload,
            "id": user_id,
            "created_at": now_str,
            "short_id": user_id.replace("-", "")[:8],
            "full_name": ADMIN_FULL_NAME,
            "extra": json.dumps({"seed": "admin"}),
            "preferences": json.dumps({"language": "en"}),
            "supervisor_id": None,
            "deleted_at": None,
        }
        conn.execute(
            text(
                """
                INSERT INTO users
                (id, email, password_hash, role, created_at, updated_at, short_id,
                 full_name, extra, preferences, tenant_id, is_active, supervisor_id, deleted_at)
                VALUES
                (:id, :email, :password_hash, :role, :created_at, :updated_at, :short_id,
                 :full_name, :extra, :preferences, :tenant_id, :is_active, :supervisor_id, :deleted_at)
                """
            ),
            payload,
        )

    return {"id": user_id, "email": ADMIN_EMAIL}


# ---------- seeds: memberships ----------
def seed_memberships(conn, users, extra_memberships=None):
    # очистим только свои членства в этом тенанте
    conn.execute(
        text("DELETE FROM user_memberships WHERE tenant_id = :t"), {"t": TENANT_ID}
    )
    memberships = [
        {"user_id": u["id"], "role": "employee"}
        for u in users
        if u.get("id")
    ]
    for extra in extra_memberships or []:
        if extra and extra.get("user_id"):
            memberships.append(extra)
    for m in memberships:
        conn.execute(
            text("""
            INSERT INTO user_memberships (id, user_id, tenant_id, role)
            VALUES (:id, :user_id, :tenant_id, :role)
            ON CONFLICT(user_id, tenant_id) DO UPDATE SET role=excluded.role
        """),
            {
                "id": m.get("id") or gen_uuid(),
                "user_id": m["user_id"],
                "tenant_id": TENANT_ID,
                "role": m.get("role", "employee"),
            },
        )


# ---------- seeds: companies ----------
def seeded_companies():
    companies = [
        {
            "name": "TransLogix Sp. z o.o.",
            "country": "PL",
            "city": "Poznań",
            "address": "ul. Logistyczna 12, 60-101 Poznań",
            "contacts": {
                "main": {
                    "name": "Katarzyna Borkowska",
                    "email": "k.borkowska@translogix.pl",
                    "phone_code": "48",
                    "phone_local": "602111222",
                },
                "accounting": {"email": "faktury@translogix.pl"},
            },
            "extra": {
                "fleet": 120,
                "segments": ["FTL", "international"],
                "note": "IRU partner",
            },
        },
        {
            "name": "EuroFreight S.A.",
            "country": "PL",
            "city": "Wrocław",
            "address": "ul. Transportowa 5, 50-300 Wrocław",
            "contacts": {
                "main": {
                    "name": "Tomasz Król",
                    "email": "t.krol@eurofreight.eu",
                    "phone_code": "48",
                    "phone_local": "603222333",
                },
                "hr": {"email": "hr@eurofreight.eu"},
            },
            "extra": {"fleet": 75, "segments": ["LTL", "pharma"], "certs": ["GDP"]},
        },
        {
            "name": "Baltic Cargo sp.k.",
            "country": "PL",
            "city": "Gdańsk",
            "address": "al. Grunwaldzka 101, 80-244 Gdańsk",
            "contacts": {
                "main": {
                    "name": "Marta Lewandowska",
                    "email": "m.lewandowska@balticcargo.pl",
                    "phone_code": "48",
                    "phone_local": "604333444",
                },
            },
            "extra": {
                "fleet": 40,
                "segments": ["container", "sea-road"],
                "ports": ["Gdansk", "Gdynia"],
            },
        },
        {
            "name": "Vistula Transport LLC",
            "country": "PL",
            "city": "Warszawa",
            "address": "ul. Prosta 70, 00-838 Warszawa",
            "contacts": {
                "main": {
                    "name": "Aleksander Maj",
                    "email": "a.maj@vistula-transport.com",
                    "phone_code": "48",
                    "phone_local": "605444555",
                },
                "ops": {"email": "ops@vistula-transport.com"},
            },
            "extra": {
                "fleet": 200,
                "segments": ["FTL", "automotive"],
                "note": "fast onboarding",
            },
        },
    ]
    out = []
    for c in companies:
        cid = gen_uuid()
        out.append(
            {
                "id": cid,
                "tenant_id": TENANT_ID,
                "name": c["name"],
                "country": c["country"],
                "city": c["city"],
                "address": c["address"],
                "contacts": json.dumps(c["contacts"]),
                "extra": json.dumps(c["extra"]),
                "created_at": dt_ago(RND.randint(5, 40)),
                "updated_at": dt_ago(RND.randint(1, 5)),
                "deleted_at": None,
            }
        )
    return out


# ---------- seeds: vacancies ----------
def seeded_vacancies(companies, recruiters):
    titles = [
        "Kierowca C+E — trasy międzynarodowe (plandeka)",
        "Kierowca C+E — chłodnia, UE",
        "Kierowca C+E — kontenery morskie (Trójmiasto)",
        "Kierowca C+E — auto-laweta, DE/PL",
        "Kierowca C+E — ADR, Europa Zachodnia",
        "Spedytor międzynarodowy — junior",
        "Spedytor międzynarodowy — mid/senior",
    ]
    currency = "PLN"
    locations = [
        "Poznań",
        "Wrocław",
        "Gdańsk",
        "Warszawa",
        "Szczecin",
        "Łódź",
        "Katowice",
    ]
    out = []
    employment_types = ["full_time", "part_time", "b2b"]
    for i in range(7):
        vid = gen_uuid()
        company = companies[i % len(companies)]
        manager = recruiters[i % len(recruiters)]
        salary_from = RND.choice([8500, 9000, 9500, 10000, 10500, 11000])
        salary_to = salary_from + RND.choice([500, 800, 1000, 1200, 1500])
        employment_type = RND.choice(employment_types)
        out.append(
            {
                "id": vid,
                "tenant_id": TENANT_ID,
                "company_id": company["id"],
                "manager": manager["id"],
                "title": titles[i],
                "description": f"{titles[i]} — pełny etat, system 3/1 lub 2/1. Doświadczenie mile widziane.",
                "location": locations[i],
                "salary_from": salary_from,
                "salary_to": salary_to,
                "currency": currency,
                "status": "open",
                "is_active": True,
                "is_archived": False,
                "employment_type": employment_type,
                "extra": json.dumps(
                    {
                        "shift": RND.choice(["2/1", "3/1", "2/2"]),
                        "fleet": RND.choice(["Scania", "Volvo", "DAF", "MAN"]),
                        "requirements": [
                            "prawo jazdy C+E",
                            "karta kierowcy",
                            "kwalifikacja wstępna",
                        ],
                        "benefits": ["premie", "nowa flota", "dedykowany spedytor"],
                    }
                ),
                "created_at": dt_ago(RND.randint(2, 30)),
                "updated_at": dt_ago(RND.randint(1, 2)),
            }
        )
    return out


# ---------- seeds: additional services ----------
def seeded_service_catalog() -> list[dict[str, object]]:
    seeds = [
        {
            "code": "medical",
            "name": "Медосмотр",
            "description": "Обязательный медицинский осмотр водителя",
            "category": "medical",
            "unit": "person",
            "base_price": Decimal("350.00"),
            "currency": "PLN",
            "vat_rate": Decimal("8.00"),
            "requires_schedule": True,
            "requires_candidate": True,
            "result_document_type": "medical",
            "requires_documents": ["identity_document"],
            "sla_hours": 48,
            "meta": {"blocking": False},
        },
        {
            "code": "psychotest",
            "name": "Психотест водителя",
            "description": "Психологическое тестирование перед рейсом",
            "category": "medical",
            "unit": "person",
            "base_price": Decimal("180.00"),
            "currency": "PLN",
            "vat_rate": Decimal("8.00"),
            "requires_schedule": True,
            "requires_candidate": True,
            "result_document_type": "psychotest",
            "requires_documents": ["identity_document"],
            "sla_hours": 24,
            "meta": {"blocking": False},
        },
        {
            "code": "code95_training",
            "name": "Курс Code 95",
            "description": "Обновление квалификации Code 95",
            "category": "training",
            "unit": "person",
            "base_price": Decimal("950.00"),
            "currency": "PLN",
            "vat_rate": Decimal("23.00"),
            "requires_schedule": True,
            "requires_candidate": True,
            "result_document_type": "qualification_code95",
            "requires_documents": ["driver_license"],
            "sla_hours": 72,
            "meta": {"blocking": False},
        },
        {
            "code": "adr_training",
            "name": "ADR тренинг",
            "description": "Специализированный курс ADR. Блокирующий этап выхода в рейс.",
            "category": "training",
            "unit": "person",
            "base_price": Decimal("1250.00"),
            "currency": "PLN",
            "vat_rate": Decimal("23.00"),
            "requires_schedule": True,
            "requires_candidate": True,
            "result_document_type": "adr_certificate",
            "requires_documents": ["driver_license", "psychotest"],
            "sla_hours": 96,
            "meta": {"blocking": True},
        },
        {
            "code": "visa_support",
            "name": "Поддержка по визе/ŚK",
            "description": "Комплексное сопровождение визовой процедуры",
            "category": "legal",
            "unit": "package",
            "base_price": Decimal("650.00"),
            "currency": "PLN",
            "vat_rate": Decimal("23.00"),
            "requires_schedule": False,
            "requires_candidate": False,
            "result_document_type": "visa_or_title",
            "requires_documents": ["identity_document", "assignment"],
            "sla_hours": 168,
            "meta": {"blocking": False},
        },
        {
            "code": "attestation_support",
            "name": "Świadectwo kierowcy",
            "description": "Получение свидетельства водителя для граждан третьих стран",
            "category": "legal",
            "unit": "package",
            "base_price": Decimal("420.00"),
            "currency": "PLN",
            "vat_rate": Decimal("23.00"),
            "requires_schedule": False,
            "requires_candidate": True,
            "result_document_type": "attestation",
            "requires_documents": ["identity_document", "work_permit"],
            "sla_hours": 240,
            "meta": {"blocking": False},
        },
        {
            "code": "work_permit_support",
            "name": "Разрешение на работу",
            "description": "Подготовка и подача заявления на разрешение",
            "category": "legal",
            "unit": "package",
            "base_price": Decimal("550.00"),
            "currency": "PLN",
            "vat_rate": Decimal("23.00"),
            "requires_schedule": False,
            "requires_candidate": True,
            "result_document_type": "work_permit",
            "requires_documents": ["identity_document"],
            "sla_hours": 336,
            "meta": {"blocking": False},
        },
        {
            "code": "translation",
            "name": "Нотариальный перевод документов",
            "description": "Перевод паспорта, водительских прав и других документов",
            "category": "legal",
            "unit": "piece",
            "base_price": Decimal("90.00"),
            "currency": "PLN",
            "vat_rate": Decimal("23.00"),
            "requires_schedule": False,
            "requires_candidate": False,
            "result_document_type": None,
            "requires_documents": None,
            "sla_hours": 48,
            "meta": {"blocking": False},
        },
        {
            "code": "airport_transfer",
            "name": "Трансфер из аэропорта",
            "description": "Организация трансфера для прибытия кандидата",
            "category": "logistics",
            "unit": "person",
            "base_price": Decimal("250.00"),
            "currency": "PLN",
            "vat_rate": Decimal("8.00"),
            "requires_schedule": True,
            "requires_candidate": True,
            "result_document_type": None,
            "requires_documents": None,
            "sla_hours": 12,
            "meta": {"blocking": False},
        },
        {
            "code": "accommodation",
            "name": "Организация проживания",
            "description": "Бронирование жилья для кандидата",
            "category": "logistics",
            "unit": "package",
            "base_price": Decimal("780.00"),
            "currency": "PLN",
            "vat_rate": Decimal("8.00"),
            "requires_schedule": True,
            "requires_candidate": True,
            "result_document_type": None,
            "requires_documents": None,
            "sla_hours": 72,
            "meta": {"blocking": False},
        },
    ]

    out: list[dict[str, object]] = []
    for seed in seeds:
        sid = gen_uuid()
        out.append(
            {
                "id": sid,
                "tenant_id": TENANT_ID,
                "code": seed["code"],
                "name": seed["name"],
                "description": seed["description"],
                "category": seed["category"],
                "unit": seed["unit"],
                "base_price": float(seed["base_price"]),
                "currency": seed["currency"],
                "vat_rate": float(seed["vat_rate"]),
                "requires_schedule": bool(seed["requires_schedule"]),
                "requires_candidate": bool(seed["requires_candidate"]),
                "result_document_type": seed["result_document_type"],
                "requires_documents": json.dumps(seed["requires_documents"])
                if seed["requires_documents"]
                else None,
                "sla_hours": seed["sla_hours"],
                "is_active": True,
                "meta": json.dumps(seed["meta"] or {}),
                "created_at": dt_ago(RND.randint(3, 15)),
                "updated_at": dt_ago(RND.randint(1, 3)),
            }
        )
    return out


def seeded_service_orders(
    services: list[dict[str, object]],
    candidates: list[dict[str, object]],
    companies: list[dict[str, object]],
    users: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    if not services:
        return [], [], [], []

    service_by_code = {s["code"]: s for s in services}
    if not service_by_code:
        return [], [], [], []

    orders: list[dict[str, object]] = []
    items: list[dict[str, object]] = []
    schedules: list[dict[str, object]] = []
    attachments: list[dict[str, object]] = []

    def _to_amount(value: Decimal) -> float:
        return float(value.quantize(Decimal("0.01")))

    # Order 1: medical & psychotest for first candidate
    if candidates:
        candidate = candidates[0]
        requester = users[0]
        assignee = users[1] if len(users) > 1 else requester
        order_id = gen_uuid()
        created_at = dt_ago(7)
        updated_at = dt_ago(5)

        order_items: list[dict[str, object]] = []
        total = Decimal("0.00")
        vat_total = Decimal("0.00")

        for svc_code, status, hours_offset in [
            ("medical", "scheduled", 24),
            ("psychotest", "scheduled", 30),
        ]:
            svc = service_by_code[svc_code]
            item_id = gen_uuid()
            qty = Decimal("1")
            unit_price = Decimal(str(svc["base_price"]))
            vat_rate = Decimal(str(svc["vat_rate"]))
            amount = qty * unit_price
            total += amount
            vat_total += amount * vat_rate / Decimal("100")
            order_items.append(
                {
                    "id": item_id,
                    "tenant_id": TENANT_ID,
                    "order_id": order_id,
                    "service_id": svc["id"],
                    "qty": float(qty),
                    "unit_price": float(unit_price),
                    "vat_rate": float(vat_rate),
                    "amount": float(amount),
                    "status": status,
                    "required_documents": svc.get("requires_documents"),
                    "result_document_type": svc.get("result_document_type"),
                    "meta": svc.get("meta"),
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            )
            schedules.append(
                {
                    "id": gen_uuid(),
                    "tenant_id": TENANT_ID,
                    "item_id": item_id,
                    "provider": "Medicover Poznań",
                    "slot_start": dt_in_hours(hours_offset),
                    "slot_end": dt_in_hours(hours_offset + 2),
                    "location": "Poznań, ul. Zdrowia 5",
                    "status": "confirmed",
                    "meta": json.dumps({"room": "203"}),
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            )

        orders.append(
            {
                "id": order_id,
                "tenant_id": TENANT_ID,
                "candidate_id": candidate["id"],
                "vacancy_id": None,
                "company_id": None,
                "status": "in_progress",
                "total_amount": _to_amount(total),
                "currency": "PLN",
                "vat_total": _to_amount(vat_total),
                "requested_by": requester["id"],
                "assigned_to": assignee["id"],
                "notes": "Стартовый пакет медицинских услуг",
                "audit": json.dumps(
                    {"events": [{"action": "created", "actor": requester["id"], "at": created_at}]}
                ),
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        items.extend(order_items)

    # Order 2: ADR training package for second candidate with attachment (delivered)
    if len(candidates) > 1:
        candidate = candidates[1]
        requester = users[1] if len(users) > 1 else users[0]
        assignee = users[2] if len(users) > 2 else requester
        order_id = gen_uuid()
        created_at = dt_ago(14)
        updated_at = dt_ago(2)

        order_items: list[dict[str, object]] = []
        total = Decimal("0.00")
        vat_total = Decimal("0.00")

        for svc_code, status in [
            ("code95_training", "delivered"),
            ("adr_training", "in_progress"),
        ]:
            svc = service_by_code[svc_code]
            item_id = gen_uuid()
            qty = Decimal("1")
            unit_price = Decimal(str(svc["base_price"]))
            vat_rate = Decimal(str(svc["vat_rate"]))
            amount = qty * unit_price
            total += amount
            vat_total += amount * vat_rate / Decimal("100")

            meta_payload = json.dumps({"blocking": svc_code == "adr_training"})

            order_items.append(
                {
                    "id": item_id,
                    "tenant_id": TENANT_ID,
                    "order_id": order_id,
                    "service_id": svc["id"],
                    "qty": float(qty),
                    "unit_price": float(unit_price),
                    "vat_rate": float(vat_rate),
                    "amount": float(amount),
                    "status": status,
                    "required_documents": svc.get("requires_documents"),
                    "result_document_type": svc.get("result_document_type"),
                    "meta": meta_payload,
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            )

            if svc_code == "adr_training":
                schedules.append(
                    {
                        "id": gen_uuid(),
                        "tenant_id": TENANT_ID,
                        "item_id": item_id,
                        "provider": "Centrum ADR Wrocław",
                        "slot_start": dt_in_hours(72),
                        "slot_end": dt_in_hours(72 + 8),
                        "location": "Wrocław, ul. Bezpieczna 10",
                        "status": "reserved",
                        "meta": json.dumps({"instructor": "mgr Piotr Radwan"}),
                        "created_at": created_at,
                        "updated_at": created_at,
                    }
                )
            else:
                attachments.append(
                    {
                        "id": gen_uuid(),
                        "tenant_id": TENANT_ID,
                        "item_id": item_id,
                        "file_id": gen_uuid(),
                        "label": "Скан сертификата Code95",
                        "created_at": dt_ago(4),
                    }
                )

        orders.append(
            {
                "id": order_id,
                "tenant_id": TENANT_ID,
                "candidate_id": candidate["id"],
                "vacancy_id": None,
                "company_id": None,
                "status": "in_progress",
                "total_amount": _to_amount(total),
                "currency": "PLN",
                "vat_total": _to_amount(vat_total),
                "requested_by": requester["id"],
                "assigned_to": assignee["id"],
                "notes": "Подготовка к ADR рейсам",
                "audit": json.dumps(
                    {
                        "events": [
                            {"action": "created", "actor": requester["id"], "at": created_at},
                            {"action": "approved", "actor": assignee["id"], "at": dt_ago(10)},
                        ]
                    }
                ),
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        items.extend(order_items)

    # Order 3: Company-level visa support package
    if companies:
        company = companies[0]
        requester = users[0]
        assignee = users[3] if len(users) > 3 else requester
        order_id = gen_uuid()
        created_at = dt_ago(20)
        updated_at = dt_ago(15)

        svc = service_by_code.get("visa_support")
        if svc:
            qty = Decimal("1")
            unit_price = Decimal(str(svc["base_price"])) * Decimal("5")
            vat_rate = Decimal(str(svc["vat_rate"]))
            amount = qty * unit_price
            total = amount
            vat_total = amount * vat_rate / Decimal("100")

            item_id = gen_uuid()
            items.append(
                {
                    "id": item_id,
                    "tenant_id": TENANT_ID,
                    "order_id": order_id,
                    "service_id": svc["id"],
                    "qty": float(qty),
                    "unit_price": float(unit_price),
                    "vat_rate": float(vat_rate),
                    "amount": float(amount),
                    "status": "pending",
                    "required_documents": svc.get("requires_documents"),
                    "result_document_type": svc.get("result_document_type"),
                    "meta": svc.get("meta"),
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            )

            orders.append(
                {
                    "id": order_id,
                    "tenant_id": TENANT_ID,
                    "candidate_id": None,
                    "vacancy_id": None,
                    "company_id": company["id"],
                    "status": "confirmed",
                    "total_amount": _to_amount(total),
                    "currency": "PLN",
                    "vat_total": _to_amount(vat_total),
                    "requested_by": requester["id"],
                    "assigned_to": assignee["id"],
                    "notes": "Пакет визовой поддержки для новой группы водителей",
                    "audit": json.dumps(
                        {"events": [{"action": "quote_created", "actor": requester["id"], "at": created_at}]}
                    ),
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            )

    return orders, items, schedules, attachments



# ---------- seeds: candidates ----------
def seeded_candidates(conn, companies, vacancies, recruiters):
    stages = [
        "new",
        "contacted",
        "awaiting_documents",
        "documents_received",
        "work_permit_ordered",
        "work_permit_received",
        "visa",
        "red_paper_ordered",
        "planning_arrival",
        "at_client_base",
        "started_trip",
        "probation_passed",
        "employed",
        "rejected",
    ]
    langs_pool = [
        ["pl"],
        ["pl", "en"],
        ["pl", "ru"],
        ["pl", "uk"],
        ["en"],
        ["ru", "uk"],
        ["pl", "en", "ru"],
    ]
    citizenships = ["UA", "BY", "KZ", "UZ", "GE", "PL", "LT", "LV", "AM", "AZ"]
    sources = [
        "facebook_ads",
        "tiktok_ads",
        "website_form",
        "referral",
        "linkedin",
        "organic_youtube",
    ]
    cats = ["C", "C+E"]
    exp_years = [0, 0.5, 1, 2, 3, 5, 7, 10]

    have_phone_code_col = has_column(conn, "candidates", "phone_code")
    have_country_col = has_column(conn, "candidates", "country")
    have_city_col = has_column(conn, "candidates", "city")
    have_address_col = has_column(conn, "candidates", "address")

    out = []
    seq = 1  # для CND-******
    streets = [
        ("PL", "Poznań", "ul. Długa 12, 60-001 Poznań"),
        ("PL", "Wrocław", "ul. Słoneczna 45, 50-301 Wrocław"),
        ("PL", "Gdańsk", "al. Zwycięstwa 33, 80-219 Gdańsk"),
        ("PL", "Warszawa", "ul. Prosta 70, 00-838 Warszawa"),
        ("PL", "Szczecin", "ul. Portowa 5, 70-010 Szczecin"),
        ("PL", "Łódź", "ul. Piotrkowska 120, 90-006 Łódź"),
        ("PL", "Katowice", "ul. Chorzowska 25, 40-101 Katowice"),
    ]

    for i in range(30):
        cid = gen_uuid()
        company = companies[i % len(companies)]
        vacancy = vacancies[i % len(vacancies)]
        manager = recruiters[i % len(recruiters)]

        first = rand_choice(
            [
                "Andrii",
                "Maksym",
                "Oleksii",
                "Pavel",
                "Yurii",
                "Dmytro",
                "Volodymyr",
                "Serhii",
                "Artem",
                "Ivan",
                "Denys",
                "Oleh",
                "Vitalii",
                "Mykhailo",
                "Roman",
            ]
        )
        last = rand_choice(
            [
                "Kovalenko",
                "Shevchenko",
                "Melnyk",
                "Tkachenko",
                "Kravchenko",
                "Bondarenko",
                "Klymenko",
                "Mazur",
                "Chernyk",
                "Stepanenko",
            ]
        )
        phone_code = "48"
        phone_local = f"7{RND.randint(0, 9)}{RND.randint(1000000, 9999999)}"
        email = f"{first.lower()}.{last.lower()}{RND.randint(1, 999)}@example.com"
        langs = rand_choice(langs_pool)
        stage = rand_choice(stages[:-1])  # реже rejected
        street = streets[i % len(streets)]
        country, city, address = street

        docs = {
            "identity_document": {
                "status": rand_choice(["missing", "received"]),
                "expires_at": (
                    NOW + timedelta(days=365 + RND.randint(0, 400))
                ).strftime("%Y-%m-%d"),
            },
            "driver_license": {
                "category": rand_choice(cats),
                "expires_at": (NOW + timedelta(days=700)).strftime("%Y-%m-%d"),
            },
            "qualification_code95": {
                "has": rand_choice([True, False]),
                "provider": rand_choice(["PL", "LT", "LV", ""]),
            },
            "work_permit": {
                "status": rand_choice(["not_needed", "ordered", "received"])
            },
            "visa": {
                "type": rand_choice(["none", "D", "C"]),
                "status": rand_choice(["none", "in_progress", "issued"]),
            },
            "medical_certificate": {
                "status": rand_choice(["scheduled", "passed", "not_required"])
            },
        }
        extra = {
            "citizenship": rand_choice(citizenships),
            "experience_years": rand_choice(exp_years),
            "last_employer": rand_choice(
                ["DPD", "Raben", "DHL", "InPost", "Nova Poshta", "—"]
            ),
            "source": rand_choice(sources),
            "utm": {
                "campaign": "dev_seed",
                "adset": rand_choice(["broad", "retargeting", "lookalike"]),
            },
            "notes": rand_choice(
                [
                    "Готов к выезду через 2 недели",
                    "Нужна поддержка с визой D",
                    "Есть опыт ADR",
                    "Нужна помощь с жильём",
                    "Ищет смену 3/1",
                ]
            ),
            "tags": ["seed", "driver", "pipeline"],
            "preferred_routes": rand_choice(
                [
                    ["DE", "NL", "BE"],
                    ["IT", "FR"],
                    ["ES", "PT"],
                    ["CZ", "SK", "HU"],
                    ["SE", "NO", "DK"],
                ]
            ),
        }

        model = {
            "id": cid,
            "tenant_id": TENANT_ID,
            "short_id": f"CND-{seq:06d}",
            "first_name": first,
            "last_name": last,
            "phone": phone_local,  # только локальный номер
            "email": email,
            "languages": json.dumps(langs),
            "stage": stage,
            "note": rand_choice(
                [
                    "",
                    "Позвонить после 18:00",
                    "Просит оплату по диете",
                    "Хочет Volvo",
                    "Нужен аванс",
                ]
            ),
            "manager": manager["id"],
            "company_id": company["id"],
            "vacancy_id": vacancy["id"],
            "docs_progress": json.dumps(docs),
            "extra": json.dumps(extra),
            "created_at": dt_ago(RND.randint(1, 25)),
            "updated_at": dt_ago(RND.randint(0, 1)),
            "deleted_at": None,
        }

        # опциональные колонки
        if have_phone_code_col:
            model["phone_code"] = phone_code
        else:
            # положим код в extra, если отдельной колонки нет
            extra_obj = json.loads(model["extra"])
            extra_obj["phone_code"] = phone_code
            model["extra"] = json.dumps(extra_obj)

        if have_country_col:
            model["country"] = country
        else:
            extra_obj = json.loads(model["extra"])
            extra_obj["country"] = country
            model["extra"] = json.dumps(extra_obj)
        if have_city_col:
            model["city"] = city
        else:
            extra_obj = json.loads(model["extra"])
            extra_obj["city"] = city
            model["extra"] = json.dumps(extra_obj)
        if have_address_col:
            model["address"] = address
        else:
            extra_obj = json.loads(model["extra"])
            extra_obj["address"] = address
            model["extra"] = json.dumps(extra_obj)

        out.append(model)
        seq += 1
    return out


# ---------- main ----------
def main():
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        # чистим dev-данные, но не удаляем других users
        for sql in (
            "DELETE FROM documents WHERE tenant_id=:t",
            "DELETE FROM service_attachments WHERE tenant_id=:t",
            "DELETE FROM service_schedule WHERE tenant_id=:t",
            "DELETE FROM service_items WHERE tenant_id=:t",
            "DELETE FROM service_orders WHERE tenant_id=:t",
            "DELETE FROM services WHERE tenant_id=:t",
        ):
            try:
                conn.execute(text(sql), {"t": TENANT_ID})
            except Exception:
                pass
        conn.execute(
            text("DELETE FROM candidates WHERE tenant_id=:t"), {"t": TENANT_ID}
        )
        conn.execute(
            text("DELETE FROM vacancies  WHERE tenant_id=:t"), {"t": TENANT_ID}
        )
        conn.execute(
            text("DELETE FROM companies  WHERE tenant_id=:t"), {"t": TENANT_ID}
        )
        if has_table(conn, "document_templates"):
            conn.execute(
                text("DELETE FROM document_templates WHERE tenant_id=:t"),
                {"t": TENANT_ID},
            )
        # user_memberships чистим для нашего тенанта
        try:
            conn.execute(
                text("DELETE FROM user_memberships WHERE tenant_id=:t"),
                {"t": TENANT_ID},
            )
        except Exception:
            pass

        admin_user = ensure_admin_account(conn)

        # USERS (ensure)
        users = seeded_users()
        ensure_users(conn, users)

        # MEMBERSHIPS
        extra_memberships = []
        if admin_user:
            extra_memberships.append({"user_id": admin_user["id"], "role": "administrator"})
        seed_memberships(conn, users, extra_memberships=extra_memberships)

        services_catalog: list[dict[str, object]] = []

        # COMPANIES
        companies = seeded_companies()
        for c in companies:
            conn.execute(
                text("""
                INSERT INTO companies
                (id, tenant_id, name, country, city, address, contacts, extra, created_at, updated_at, deleted_at)
                VALUES
                (:id, :tenant_id, :name, :country, :city, :address, :contacts, :extra, :created_at, :updated_at, :deleted_at)
            """),
                c,
            )

        if has_table(conn, "services"):
            services_catalog = seeded_service_catalog()
            for svc in services_catalog:
                conn.execute(
                    text("""
                    INSERT INTO services
                    (id, tenant_id, code, name, description, category, unit, base_price,
                     currency, vat_rate, requires_schedule, requires_candidate, result_document_type,
                     requires_documents, sla_hours, is_active, meta, created_at, updated_at)
                    VALUES
                    (:id, :tenant_id, :code, :name, :description, :category, :unit, :base_price,
                     :currency, :vat_rate, :requires_schedule, :requires_candidate, :result_document_type,
                     :requires_documents, :sla_hours, :is_active, :meta, :created_at, :updated_at)
                """),
                    svc,
                )

        # VACANCIES
        vacancies = seeded_vacancies(companies, users)
        for v in vacancies:
            conn.execute(
                text("""
                INSERT INTO vacancies
                (id, tenant_id, company_id, manager, title, description, location,
                 salary_from, salary_to, currency, status, employment_type, is_active, is_archived, extra, created_at, updated_at)
                VALUES
                (:id, :tenant_id, :company_id, :manager, :title, :description, :location,
                 :salary_from, :salary_to, :currency, :status, :employment_type, :is_active, :is_archived, :extra, :created_at, :updated_at)
            """),
                v,
            )

        # CANDIDATES
        candidates = seeded_candidates(conn, companies, vacancies, users)

        # динамически собираем INSERT под доступные колонки
        cols = [
            "id",
            "tenant_id",
            "short_id",
            "first_name",
            "last_name",
            "phone",
            "email",
            "languages",
            "stage",
            "note",
            "manager",
            "company_id",
            "vacancy_id",
            "docs_progress",
            "extra",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        # опциональные
        if has_column(conn, "candidates", "phone_code"):
            cols.insert(cols.index("email") + 1, "phone_code")
        for opt in ("country", "city", "address"):
            if has_column(conn, "candidates", opt):
                cols.insert(cols.index("docs_progress"), opt)

        cols_sql = ", ".join(cols)
        vals_sql = ", ".join([f":{c}" for c in cols])

        insert_sql = f"INSERT INTO candidates ({cols_sql}) VALUES ({vals_sql})"
        for c in candidates:
            conn.execute(text(insert_sql), c)

        if services_catalog and has_table(conn, "service_orders"):
            orders, service_items, schedules, attachments = seeded_service_orders(
                services_catalog, candidates, companies, users
            )

            for order in orders:
                conn.execute(
                    text("""
                    INSERT INTO service_orders
                    (id, tenant_id, candidate_id, vacancy_id, company_id, status,
                     total_amount, currency, vat_total, requested_by, assigned_to,
                     notes, audit, created_at, updated_at)
                    VALUES
                    (:id, :tenant_id, :candidate_id, :vacancy_id, :company_id, :status,
                     :total_amount, :currency, :vat_total, :requested_by, :assigned_to,
                     :notes, :audit, :created_at, :updated_at)
                """),
                    order,
                )

            for item in service_items:
                conn.execute(
                    text("""
                    INSERT INTO service_items
                    (id, tenant_id, order_id, service_id, qty, unit_price, vat_rate,
                     amount, status, required_documents, result_document_type, meta, created_at, updated_at)
                    VALUES
                    (:id, :tenant_id, :order_id, :service_id, :qty, :unit_price, :vat_rate,
                     :amount, :status, :required_documents, :result_document_type, :meta, :created_at, :updated_at)
                """),
                    item,
                )

            if schedules and has_table(conn, "service_schedule"):
                for sched in schedules:
                    conn.execute(
                        text("""
                        INSERT INTO service_schedule
                        (id, tenant_id, item_id, provider, slot_start, slot_end, location,
                         status, meta, created_at, updated_at)
                        VALUES
                        (:id, :tenant_id, :item_id, :provider, :slot_start, :slot_end, :location,
                         :status, :meta, :created_at, :updated_at)
                    """),
                        sched,
                    )

            if attachments and has_table(conn, "service_attachments"):
                for attach in attachments:
                    conn.execute(
                        text("""
                        INSERT INTO service_attachments
                        (id, tenant_id, item_id, file_id, label, created_at)
                        VALUES
                        (:id, :tenant_id, :item_id, :file_id, :label, :created_at)
                    """),
                        attach,
                    )

        if admin_user and has_table(conn, "user_notifications"):
            seed_notification_templates(
                conn, tenant_id=TENANT_ID, user_id=admin_user["id"]
            )

        ensure_meta_lead_settings(conn)
        ensure_document_templates(conn)

    print(
        "✅ Dev seed completed: 4 users (+memberships), 4 companies, 7 vacancies, 30 candidates (CND-******, адреса, phone_code отдельно), 10 services, 3 service orders, Meta leads settings, document templates."
    )


if __name__ == "__main__":
    main()
