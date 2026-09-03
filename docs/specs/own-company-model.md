# Own Company Model — `OwnCompany` vs CRM `Company.extra.company_role='operating'`

**Назначение:** один справочник по поводу двух параллельных моделей «моя компания» в HostFlow:

1. **`OwnCompany`** (table `own_companies`) — современный workspace-scope entity (per-tenant юр. сущность; topbar-switcher; используется как scope для leads/vacancies/documents).
2. **CRM `Company` с `extra.company_role='operating'`** (table `companies`) — legacy «operating company» паттерн (используется в quota-счётчике, MyCompanyPage, билдинге).

Эти **две таблицы**, и сегодня они **не синхронизированы автоматически**: новый онбординг создаёт только `OwnCompany`, legacy `POST /companies/` создаёт CRM operating-Company. Это источник несогласованности (My Company page показывает одно, topbar — другое).

**Связанные документы:**

- `docs/HOSTFLOW_AUDIT_AND_PLAN.md` Phase 2 §2.6.B (todo, закрываемый этим документом).
- `docs/specs/tenant-types.md` (`business_type` хранится частично в `OwnCompany.extra`, частично в `Company.extra` — корень проблемы).
- `docs/specs/operations-loop.md` §6 «Гэп: дублирующиеся сущности».

**Краткое решение:** канонизируем `OwnCompany` как **single-source** для «моя юр. сущность». `Company.extra.company_role='operating'` депрекируется через 3 фазы: (1) bootstrap-mirror в `POST /own-companies/` создаёт CRM-row (для совместимости с quota/MyCompanyPage), (2) сторонние читатели переходят на `OwnCompany`, (3) operating-Company оставляется для легаси, но не пишется новыми путями.

---

## 1. Текущее состояние

### 1.1. `OwnCompany` (новая модель)

**Файл:** `backend/app/models/own_company.py:17-77`

```17:77:backend/app/models/own_company.py
class OwnCompany(Base, TimestampMixin):
    __tablename__ = "own_companies"

    id: Mapped[str] = ...
    tenant_id: Mapped[str] = ...
    name: Mapped[str] = ...
    legal_name, tax_id, phone, email, website,
    country_code, country, city, address, notes,
    is_archived: Mapped[bool] = ...
    contacts: Mapped[dict] = ...
    extra: Mapped[dict] = ...
    bank_details: Mapped[dict] = ...
```

**API** (`backend/app/api/v1/own_companies.py`):

| Endpoint | Поведение |
|---|---|
| `GET /own-companies/` | список + `active_own_company_id` (~148-171). |
| `POST /own-companies/` | создаёт OwnCompany; **первый** запрос (`current_count == 0`) дополнительно зовёт `bootstrap_tenant_for_own_company_onboarding` + опциональный demo-seed (~253-274). |
| `PATCH /own-companies/{id}` | редактирует поля (~313-316); **не** синхронизирует с CRM `Company`. |
| `POST /own-companies/active` | сохраняет `active_own_company_id` в user-prefs (~333-389). |
| `DELETE` | **не реализован** (нет hard-delete; только `is_archived` через PATCH). |

`tenant_id` — required; **1:N** per tenant (license `max_companies` в `create_own_company:188-197`).

### 1.2. CRM `Company` с `extra.company_role='operating'` (legacy)

**Файл:** `backend/app/models/company.py:80-85`

```80:85:backend/app/models/company.py
    extra: Mapped[dict] = mapped_column(
        _JSONType,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
```

`extra.company_role` — JSON-ключ, значение `'operating'` маркирует «моя компания» внутри общей таблицы `companies` (которая по умолчанию хранит client-companies — заказчиков агентства).

**Где пишется:**

- `backend/app/modules/companies/crud.py::create_company` (~1266-1308): первая компания в tenant **принудительно** получает `company_role='operating'`. Обычные `POST /companies/` после этого создают client-companies без этого флага.

**Где читается:**

- `backend/app/services/operating_company_slots.py::count_operating_companies` (~71-80) — считает CRM `Company` rows с `extra.company_role == 'operating'`.
- `backend/app/api/v1/onboarding.py` (~142-181) — `/onboarding/status` предпочитает `Company.extra.company_type` для определения `business_type`.
- `backend/app/modules/leads/service/_helpers.py` (~116-137) — fallback при определении `business_type`.

### 1.3. UI: где что показывается

| Экран | Источник |
|---|---|
| **Topbar OwnCompany switcher** | `OwnCompany` (через `getOwnCompanies` + `active_own_company_id`). |
| **`/app/my-company`** (`hostflow-frontend/src/pages/MyCompanyPage.tsx:15-79`) | `listCompanies` (CRM!) + filter `extra.company_role === 'operating'`. **НЕ читает OwnCompany.** |
| **`/app/companies`** (`Companies.tsx`) | `listCompanies` (CRM); **скрывает** operating-rows клиентским фильтром (`filteredItems`, ~309-311). Прямой URL operating-Company → redirect на `/app/my-company` (~1562-1569). |
| **Onboarding company page** (`OnboardingCompanyPage.tsx:295-307`) | создаёт **только OwnCompany** через `createOwnCompany` + `setActiveOwnCompany`. |

**Главный конфликт:** Topbar показывает `OwnCompany.name`, а MyCompanyPage редактирует CRM `Company.name` operating-row-а. Если их имена расходятся, пользователь видит два разных «названия моей компании».

### 1.4. Onboarding — что реально создаётся

`POST /own-companies/` первый раз (`backend/app/api/v1/own_companies.py:252-264`):

1. Создаёт `OwnCompany` row.
2. Зовёт `bootstrap_tenant_for_own_company_onboarding(company_type=bt_norm)`.
3. `bootstrap_tenant_for_own_company_onboarding` (`backend/app/modules/companies/crud.py:758-830`) **обновляет только `Tenant.settings`**:
   - `tenant.settings.business_type = bt_norm`
   - `tenant.settings.modules = _onboarding_module_profile(bt_norm)`
   - дефолтные funnels.
4. **НЕ** создаёт CRM `Company` operating-row.

Legacy `POST /companies/` (`backend/app/modules/companies/crud.py::create_company`, ~1246-1356) — наоборот, **создаёт** operating-row, но не создаёт OwnCompany.

В результате tenant, прошедший новый онбординг, имеет:

- `OwnCompany` ✔
- `Tenant.settings.business_type` ✔
- `Tenant.settings.modules` ✔
- CRM `Company` operating-row ✘ (отсутствует!)

Это значит:

- `MyCompanyPage` ничего не покажет (или покажет «No company yet»).
- `count_operating_companies` вернёт 0.
- Quota по operating slots некорректна.

### 1.5. Sync direction

**Нет.** `PATCH /own-companies/{id}` не зовёт `update_company`. `PATCH /companies/{id}` operating-row-а не зовёт `update_own_company`.

`onboarding.py` (~142-144) явно отмечает: `OwnCompany.extra` может протухнуть; для UI/wizard используется в первую очередь `Company.extra.company_type` (operating).

### 1.6. Операционные слоты / квоты

`backend/app/services/operating_company_slots.py::count_operating_companies` (~71-80) — считает **`Company.extra.company_role == 'operating'`**, не `OwnCompany`. То есть для tenant-а, прошедшего новый онбординг (только `OwnCompany`, без CRM operating-row), `slots.used = 0`.

`backend/app/services/lead_forms_quota.py` — **не** про operating-слоты; этот сервис про активные lead-формы.

---

## 2. Дисбаланс (что ломается сегодня)

| Проблема | Симптом |
|---|---|
| **MyCompanyPage пустая для нового tenant-а** | tenant сделал onboarding (создан только OwnCompany), открыл `/app/my-company` — пусто или плейсхолдер «No company». |
| **Quota operating-slots всегда 0** | `count_operating_companies` не видит OwnCompany. Биллинг `max_companies` гейтит `OwnCompany`-create, но slot-counter показывает «0/N». |
| **Topbar и MyCompanyPage показывают разные имена** | если пользователь legacy-tenant (есть и operating CRM-row, и OwnCompany, имена расходятся). |
| **`business_type` source-of-truth** | onboarding читает с приоритетом из `Company.extra.company_type` → если CRM-row нет, fallback в `Tenant.settings.business_type`. На разных страницах это видно по-разному. |
| **Нет DELETE для OwnCompany** | tenant с 5 brand-ами не может удалить ошибочный — только архивировать через PATCH. |

---

## 3. Канонический контракт (target state)

### 3.1. Single-source: `OwnCompany`

`OwnCompany` — единственный «источник истины» для:

- Юр. имя tenant-а / brand-а.
- Юр. адрес, налоговый ID, банковские реквизиты.
- `business_type` (через `OwnCompany.extra.business_type`, дублируется в `Tenant.settings.business_type` для read-производительности).
- Active workspace switcher (`active_own_company_id` в `User.preferences`).
- Quota `max_companies` (счётчик от `OwnCompany`).

### 3.2. CRM `Company` с `extra.company_role='operating'` — депрекейтед

Перестаёт быть source-of-truth. Остаётся как **deprecated read-mirror** для трёх вещей:

1. `MyCompanyPage` (которая мигрирует на `OwnCompany` в Stage B).
2. `count_operating_companies` (мигрирует на `count(OwnCompany)` в Stage C).
3. Legacy tenant-ы, у которых operating-row уже есть (read-only пока).

После завершения миграции (Stage D) — `extra.company_role='operating'` остаётся в БД как исторический маркер, но новые writers его **не создают**. UI-страницы и сервисы используют `OwnCompany`.

### 3.3. Bootstrap-mirror (transitional)

Чтобы существующие читатели не сломались, в Stage A добавляем:

- `POST /own-companies/` (first call) — после bootstrap создаёт CRM `Company` row с `extra.company_role='operating'`, копируя name/tax_id/address из OwnCompany. Это «mirror», не «source-of-truth».
- `PATCH /own-companies/{id}` — синхронизирует изменения в зеркальный CRM-row (если он есть).
- Bootstrap-mirror помечается feature-flag `OWN_COMPANY_MIRROR_ENABLED=true` (default `true`); после Stage C можно выключить.

### 3.4. Migration path для legacy tenant-ов

Backfill-script (`backend/scripts/backfill_own_companies_from_operating.py`):

1. Для каждого tenant-а, у которого есть CRM operating-row, но нет OwnCompany → создать OwnCompany, скопировать поля.
2. Для каждого tenant-а, у которого есть OwnCompany без CRM operating-row → создать CRM-row через bootstrap-mirror (если flag включён).
3. Если у tenant-а есть несоответствие имён (OwnCompany.name != Company.name operating-row-а) — оставить OwnCompany как master, перезаписать CRM-row.

Логирование всех операций для аудита.

### 3.5. UI унификация

| Экран | Целевое поведение |
|---|---|
| `/app/my-company` | редактирует `OwnCompany` (по `active_own_company_id`); скрывает CRM operating-row (он становится derived). |
| Topbar switcher | `OwnCompany` (как сейчас). |
| `/app/companies` | показывает только client-companies (`extra.company_role != 'operating'`). |
| Onboarding | `OwnCompany` (как сейчас); bootstrap-mirror создаёт CRM-row автоматически. |

---

## 4. План исполнения (4 стадии)

| Стадия | Задача | Зависимости | Риск |
|---|---|---|---|
| **Stage A** | bootstrap-mirror в `POST /own-companies/` (first) — создаёт CRM operating-row автоматически. PATCH-mirror для name/tax/address. Feature-flag `OWN_COMPANY_MIRROR_ENABLED`. | — | средний (затрагивает legacy quota) |
| **Stage B** | `MyCompanyPage` мигрирует на `OwnCompany` (читать через `getOwnCompanies` + `active_own_company_id`, редактировать через `patchOwnCompany`). Legacy CRM operating-row — не показывать в UI. | A | низкий (UI-only) |
| **Stage C** | `count_operating_companies` → считать `OwnCompany` (с фильтром `is_archived=false`). Quota counter обновляется. | A, backfill | средний (биллинг!) |
| **Stage D** | Backfill legacy tenant-ов (script). Депрекация: `POST /companies/` больше не маркирует первую компанию `operating` — это делает только bootstrap-mirror. | A, B, C | высокий (data migration) |

**Отдельные задачи (не в основной последовательности):**

- **DELETE для OwnCompany** — добавить `DELETE /own-companies/{id}` с проверками (нельзя удалить последнюю; нельзя удалить, если есть active leads/vacancies/documents). Phase 2 (low priority).
- **Per-OwnCompany business_type** — сегодня `business_type` всё ещё per-tenant (`Tenant.settings.business_type`); если в будущем понадобится «agency и services в одном tenant-е» — нужно разделение. Откладываем до Phase 6.

---

## 5. Контракты и инварианты (после миграции)

1. **Каждый tenant имеет ≥1 OwnCompany** — `Tenant`-без-OwnCompany считается невалидным состоянием. На Growth-пути первую OwnCompany создаёт атомарный [`ADR-041`](architecture/ADR-041-verified-self-service-signup.md) complete (имя + страна). `POST /own-companies/` остаётся для дополнительных компаний и как fallback, пока legacy `/register` не отрезан.
2. **`OwnCompany.is_archived=true` исключает row из `count_operating_companies`** и из UI-списков (но не из истории leads/vacancies — там soft-link).
3. **CRM operating-row, если существует, всегда отзеркален из OwnCompany** (Stage A). Расхождение имён — баг.
4. **Quota `max_companies` гейтит OwnCompany create**, не CRM operating create.
5. **`business_type` source-of-truth** — `Tenant.settings.business_type` (мастер), `OwnCompany.extra.business_type` — кеш для UI, `Company.extra.company_type` (operating) — deprecated read-mirror.
6. **`active_own_company_id`** — обязательная per-user preference; default = последняя use-d или первая в списке. Не должен указывать на archived OwnCompany.

---

## 6. Acceptance / тесты

1. **Stage A bootstrap-mirror:**
   - `POST /own-companies/` (first) → existence в `companies` table с `extra.company_role='operating'` и совпадающими name/tax_id.
   - `PATCH /own-companies/{id}` → CRM operating-row name обновляется.
   - Feature-flag OFF → mirror не создаётся (тест на оба пути).
2. **Stage B MyCompanyPage:**
   - UI показывает `OwnCompany.name`, не CRM operating-row.
   - Edit form шлёт `PATCH /own-companies/{id}`, не `PATCH /companies/{id}`.
3. **Stage C count_operating_companies:**
   - Tenant с N OwnCompanies (none archived) → counter = N.
   - Tenant с M archived OwnCompanies → counter = N - M.
   - Legacy tenant с CRM operating-row, но без OwnCompany → counter = 0 (после backfill — = 1).
4. **Stage D backfill:**
   - Dry-run на тестовом dataset → отчёт «N tenants matched, M will be created, K skipped».
   - Идемпотентность: повторный запуск — 0 операций.
5. **Quota integration:**
   - Создание OwnCompany при `count == max_companies` → 402 (или соответствующий код).
6. **DELETE OwnCompany:**
   - Удаление последней OwnCompany → 409 «cannot delete last».
   - Удаление OwnCompany с активными leads → 409 с deep-link на эти leads.
7. **`active_own_company_id` integrity:**
   - Если активная OwnCompany архивируется/удаляется → автоматический switch на первую неархивированную.

---

## 7. Открытые вопросы

- **Feature-flag для bootstrap-mirror:** включаем по умолчанию `true` сразу или сначала dark-launch на test-tenant-ах? **Решение:** dark-launch неделю → проверяем, что quota counter обновляется корректно → раскатываем globally.
- **Депрекация `Company.extra.company_role='operating'`:** оставляем поле в БД навсегда (исторический маркер) или удаляем через миграцию в Phase 6? **Рекомендация:** оставляем; удаление приведёт к потере аудита для legacy tenant-ов.
- **Multi-brand UI:** `OwnCompany` switcher в topbar уже работает (1:N), но большинство страниц (Dashboard, Pipeline, Leads) показывают данные **всех** OwnCompanies сразу. Нужно решить, фильтруется ли UI по `active_own_company_id` (брандированный workspace) или нет (combined view). Сегодня — combined; целевое — settable per-page (Phase 6).
- **`business_type` per-OwnCompany:** связано с предыдущим. Если в будущем `OwnCompany A` = agency, `OwnCompany B` = services в одном tenant-е, нужны разные модули. Сейчас не поддерживается, откладываем до Phase 6.
- **Hard-delete vs soft-delete:** OwnCompany сегодня только архивируется. Hard-delete опасен (есть FK с leads/vacancies). **Решение:** не реализовывать hard-delete; только archive + restore.

---

## 8. Сводка изменений в коде

| Файл | Изменение |
|---|---|
| `backend/app/api/v1/own_companies.py` | Stage A: bootstrap-mirror в `create_own_company`; mirror-PATCH в `patch_own_company`. Stage отдельно: добавить `DELETE` (с защитами). |
| `backend/app/services/operating_company_slots.py` | Stage C: `count_operating_companies` считает `OwnCompany` вместо `Company.extra.company_role`. |
| `backend/app/api/v1/onboarding.py` | Stage A/B: `/onboarding/status` читает `business_type` из `OwnCompany.extra` (master), fallback на `Tenant.settings.business_type`, потом на legacy `Company.extra.company_type`. |
| `backend/app/modules/leads/service/_helpers.py` | Stage A: `_load_tenant_business_type` обновить precedence chain. |
| `backend/app/modules/companies/crud.py::create_company` | Stage D: убрать принудительное `company_role='operating'` для первой company (bootstrap делает mirror). |
| `backend/scripts/backfill_own_companies_from_operating.py` | Stage D: новый script. |
| `hostflow-frontend/src/pages/MyCompanyPage.tsx` | Stage B: переключить с `listCompanies` + filter на `getOwnCompanies` + `active_own_company_id`. |
| `hostflow-frontend/src/pages/Companies.tsx` | Stage B: убрать redirect на operating-row (уже не нужен — operating не показывается). |
| `backend/tests/` | новые: `test_own_company_mirror.py`, `test_own_company_quota.py`, `test_backfill_own_companies.py`. |
