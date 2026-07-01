# Lead Types — `Lead.lead_type` (`candidate` vs `client`)

**Назначение:** один справочник по поводу `Lead.lead_type` — нужно ли это поле, что оно реально делает сегодня, и каким должен быть его контракт после канонизации.

**Связанные документы:**

- `docs/HOSTFLOW_AUDIT_AND_PLAN.md` Phase 2 §2.6.C (todo, закрываемый этим документом).
- `docs/specs/operations-loop.md` §2 (lead lifecycle, NBA для leads).
- `docs/specs/personas.md` (роли, видящие leads).
- `docs/specs/tenant-types.md` (`business_type` управляет, имеет ли смысл `client` lead для tenant-а).

**Краткое решение:** `lead_type='client'` **остаётся в схеме**, но требует завершения вертикали. Сегодня `client` лиды создаются только public-intake-ом и демо-сидом, нигде не используются для бизнес-логики (NBA, аналитика, UI-фильтры) и не имеют end-to-end-flow «лид → новая компания». Полный план — §6.

---

## 1. Колонка `Lead.lead_type`

```42:47:backend/app/models/lead.py
    lead_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="candidate",
        server_default=text("'candidate'"),
    )
```

- Тип — `String(16)`, NOT NULL, default `"candidate"` (Python + DB-уровень).
- На уровне БД **enum-а нет** — это свободная строка с принудительной нормализацией к двум значениям в API-слое.

API-слой (`backend/app/modules/leads/schemas.py:12-14`) объявляет литерал:

```
LeadType = Literal["candidate", "client"]
```

`backend/app/modules/leads/crud.py:37-41` — `create_lead` дополнительно нормализует любое чужое значение к `"candidate"`:

```python
def create_lead(..., lead_type: str = "candidate", ...) -> Lead:
    lt = str(lead_type or "candidate").strip().lower()
    if lt not in {"candidate", "client"}:
        lt = "candidate"
```

Соседние поля на `Lead` (важные для семантики типа): `company_id`, `vacancy_id`, `source`, `status`, `stage`, `funnel_id`, `candidate_id`, `own_company_id` — `backend/app/models/lead.py:48-91`.

`recruiter_id` / `client_manager_id` живут на enriched **`LeadOut`**, не на самой модели — это «ownership view», вычисляемый из reminders + candidate.

---

## 2. Семантика двух значений (как заявлено в коде)

| Значение | Что обозначает | Источник создания | Reads / branching |
|---|---|---|---|
| `candidate` | физлицо, рассматривается как потенциальный кандидат на вакансию (наём в рекрутинговом смысле) | дефолт; все основные writers | сегодня — никаких type-specific веток |
| `client` | юрлицо (B2B), потенциальный заказчик услуг / клиент агентства | `_maybe_create_client_lead_from_public_intake` (B2B public intake), `onboarding_demo_seed.py` | сегодня — никаких type-specific веток |

В UI термин «`lead_type`» **не показывается**: фронт оперирует `application_kind=candidate|client` (URL-параметр на public-intake-форме) — `hostflow-frontend/src/pages/PublicIntakeStart.tsx`, `PublicPortalLanding.tsx`, `LeadFormsSettingsPage.tsx`. Маппинг `application_kind → lead_type` происходит на backend-е в `backend/app/api/public/intake.py`.

---

## 3. Текущее использование

### 3.1. Writers

| Точка | Значение | Условие |
|---|---|---|
| `backend/app/modules/leads/service/_processing.py` (через `crud.create_lead` без аргумента) | `candidate` (default) | основной flow ingest-а: Meta / webhook / manual / API |
| `backend/app/api/public/intake.py` — `_maybe_create_client_lead_from_public_intake` | `client` | публичный B2B intake **и** удалось зарезолвить `company_id` (через vacancy / candidate / Meta default) |
| `backend/app/services/onboarding_demo_seed.py` | `client` | демо-данные после `POST /onboarding/demo/seed` |
| `backend/app/modules/leads/crud.py` — `create_lead(lead_type=...)` | по аргументу (default `candidate`) | низкоуровневый writer; вызывается из других сервисов |

Других writers под `backend/` нет.

### 3.2. Readers (branching)

**Сегодня бизнес-логики, ветвящейся на `lead.lead_type == "client"`, в продакшен-коде нет.** Точнее:

- `backend/app/modules/leads/service/_listing.py`, `backend/app/modules/leads/service/global_search_v1.py` — `Lead.lead_type` входит **только в ILIKE-поиск** (комбинация с `coalesce`), не как фильтр.
- `backend/app/modules/leads/router.py`, `backend/app/modules/leads/service/_listing.py`, `backend/app/services/admin/admin_service.py` — `getattr(lead, "lead_type", None) or "candidate"` — fallback при сериализации, не branching.
- `backend/app/services/next_action.py:333-460` — `compute_lead_next_action` использует **только** `stage`, `status`, reminders. **`lead_type` не читается.**
- `backend/app/api/v1/analytics.py` — `lead_type` **не используется** в группировках/счётчиках; все KPI по leads агрегируются без разбивки по типу.

Единственный read, проверяющий конкретное значение — **тест** `backend/tests/test_public_intake.py` (`assert lead.lead_type == "client"` после client-intake-а).

### 3.3. Frontend usage

- Поле `lead_type` объявлено в типах: `hostflow-frontend/src/api/types.ts` и `hostflow-frontend/src/api/types/lead.ts` (опциональное `LeadType`).
- В компонентах `Leads/`, `LeadDetailPage`, `Pipeline`, `LeadsList` — `lead_type` **не отображается**, не фильтруется, не используется для условного рендера.
- B2B-flow (intake клиента) фронт обозначает не через `lead_type`, а через **URL-параметр** `application_kind=client`: `hostflow-frontend/src/pages/PublicIntakeStart.tsx`, `PublicPortalLanding.tsx`, `LeadFormsSettingsPage.tsx`.

### 3.4. Public intake / lead-form schemas

- `backend/app/models/tenant_lead_form.py` — `TenantLeadForm` **не содержит** `lead_type` (только `title`, `public_slug`, `is_active`).
- `backend/app/api/public/intake.py` — `application_kind` приводится к `candidate|client`. Если `client` И удаётся зарезолвить `company_id` (vacancy-default или Meta-default) — создаётся `Lead(..., lead_type="client")` через `_maybe_create_client_lead_from_public_intake`. Если `company_id` зарезолвить нельзя — лид **не создаётся**, эмитится событие `intake_client_lead_skipped_no_company`.

### 3.5. Conversion path

**Не существует** code-path-а вида «`lead.lead_type == 'client'` ⇒ создать новую `Company` в `/app/clients`». Все client-лиды требуют **уже существующую** `company_id` на момент создания, иначе лид теряется (см. §3.4).

---

## 4. Решение: оставляем `client`, канонизируем вертикаль

Удалять `lead_type` нельзя по двум причинам:

1. **B2B intake уже работает** — `application_kind=client` в публичных формах создаёт `client`-лиды (см. §3.4). Удаление `lead_type` сломает этот entry point.
2. **Demo seed** заполняет client-лиды и они видны в `/app/leads/` после demo-seed онбординга (видимый функционал, который рекламируется новым tenant-ам).

Но и текущее состояние **наполовину сломано**: client-лиды создаются → попадают в общий список → не имеют отдельного flow / NBA / аналитики / визуального отличия. Пользователь видит запись в leads, но не понимает, что это другой тип сущности.

**Канонический контракт (target state):**

| Слой | Контракт |
|---|---|
| **DB** | `Lead.lead_type` остаётся `String(16) NOT NULL DEFAULT 'candidate'`. Превратить в Python enum `LeadType` (`backend/app/models/enums.py`) — для type-safety и автодополнения. **Не** мигрировать на postgres ENUM (избежать миграции с downtime). |
| **API schemas** | `LeadType = Literal["candidate", "client"]` уже есть в `schemas.py` — оставить. Добавить exhaustive проверку в `LeadOut` через Pydantic-валидатор. |
| **Visibility** | `client`-вертикаль доступна **только** для tenant-ов, у которых `business_type ∈ {agency, services}`. Для `business_type == employer` — public-form `application_kind=client` отвергается (employer не подбирает клиентов). См. `docs/specs/tenant-types.md` §2. |
| **NBA** | `compute_lead_next_action` ветвится на `lead_type`: для `client` — приоритет «contact decision-maker» вместо «contact candidate»; терминальные стадии те же. См. §5.2. |
| **UI** | Список `/app/leads/` показывает badge `Candidate` / `Client` рядом с именем. Фильтр `Type` добавлен. Карточка ведёт на `LeadDetailPage` с разными секциями (для client — нет vacancy-секции, есть «company snapshot»). |
| **Conversion path** | Для `client`-лидов в `LeadDetailPage` — primary CTA «Convert to client company» (создаёт `Company` в `/app/clients` + переносит payload + закрывает лид как `converted`). См. §5.4. |
| **Analytics** | Дашборд группирует leads по `lead_type` (отдельный счётчик «Client leads» рядом с «Candidate leads»). |

---

## 5. Стадия канонизации

### 5.1. Stage A — модель + типы (lowest risk)

- [ ] Превратить строку в Python enum `LeadType` (`backend/app/models/enums.py`), импортировать в `models/lead.py`. БД-колонка остаётся `String(16)`.
- [ ] В `LeadOut` (Pydantic) — добавить валидатор, отвергающий незнакомые значения.
- [ ] Обновить `crud.create_lead` — использовать enum вместо `lt not in {...}`.
- [ ] Frontend: `LeadType` в `hostflow-frontend/src/api/types.ts` сделать `'candidate' | 'client'` (без опциональности).

### 5.2. Stage B — NBA branching

- [ ] `compute_lead_next_action` (`backend/app/services/next_action.py`):
  - Если `lead.lead_type == 'client'` И `lead.stage == 'new'` → suggestion `client_lead_contact_decision_maker` (текст «Reach out to decision-maker at {company.name}»).
  - Если `lead.lead_type == 'client'` И `lead.stage == 'qualified'` → suggestion `client_lead_convert_to_company` (текст «Convert to client company», deep-link `/app/clients/new?from_lead={id}`).
  - Терминальные стадии (`converted`, `lost`) — те же `_LEAD_TERMINAL_STAGES`.
- [ ] `NextActionExplainabilityPopover.tsx`: добавить reason_codes `client_lead_contact_decision_maker`, `client_lead_convert_to_company`.
- [ ] Тесты: новые кейсы в `backend/tests/test_lead_next_action.py` для обоих client-стадий.

### 5.3. Stage C — UI surface

- [ ] `LeadsList` / `Pipeline`: badge «Client» (отличительный цвет от «Candidate»). i18n-ключ `app.leads.type.client`, `app.leads.type.candidate`.
- [ ] Фильтр `Type` в leads-списке: `All / Candidate / Client`. Параметр `lead_type` уже принимается backend-ом? Если нет — добавить в `list_leads` query.
- [ ] `LeadDetailPage`: для `client` скрыть секцию «Vacancy», добавить «Company snapshot» (имя компании, отрасль, размер, контакты — берётся из `payload`).
- [ ] `LeadDetailPage` primary CTA: для `client` лидов — «Convert to client company» (deep-link на §5.4).

### 5.4. Stage D — Conversion path «client lead → new client company»

- [ ] Новый endpoint `POST /api/v1/leads/{id}/convert-to-company` (`backend/app/modules/leads/router.py`):
  - Проверки: `lead.lead_type == 'client'`, `lead.stage != 'converted'`, `lead.stage != 'lost'`.
  - Создаёт `Company` (тип CRM-client, `extra.company_role` НЕ `operating`) с данными из `lead.payload`.
  - Привязывает `lead.company_id = new_company.id`.
  - Меняет `lead.stage = 'converted'`, `lead.status = 'processed'`.
  - Создаёт reminder «Onboard new client {company.name}» для `client_manager`-а.
  - Эмитит событие `lead_converted_to_company` (для аудита).
- [ ] Frontend: модалка подтверждения с превью данных компании, после успеха — redirect на `/app/clients/{new_id}`.
- [ ] Тесты: `backend/tests/test_lead_convert_to_company.py` — позитивный, валидации, идемпотентность.

### 5.5. Stage E — Analytics

- [ ] `backend/app/api/v1/analytics.py` — `leads_summary`: добавить разбивку `by_lead_type` (`{ candidate: int, client: int }`).
- [ ] Дашборд (`hostflow-frontend/src/pages/Dashboard.tsx`): отдельный счётчик «Client leads» с deep-link на `/app/leads/?lead_type=client`.

### 5.6. Stage F — Public intake hardening

- [ ] Если `application_kind=client` И `business_type == employer` → 422 с понятным сообщением «This tenant does not accept B2B leads».
- [ ] Если `company_id` нельзя зарезолвить → создавать **draft client-lead** (новое значение `Lead.stage = 'pending_company'`) и показывать в `/app/leads/?stage=pending_company` для ручного дозаполнения. Сегодня лид теряется (event-only).

---

## 6. План исполнения

| Стадия | Зависимости | Риск | Объём (примерно) |
|---|---|---|---|
| Stage A — модель + типы | — | низкий | ½ дня |
| Stage B — NBA branching | A | низкий | ~1 день |
| Stage C — UI surface | A | средний (UAT с UX) | ~2 дня |
| Stage D — conversion path | A, C | **средний/высокий** (новая backend-вертикаль + миграции) | ~3 дня |
| Stage E — analytics | A | низкий | ½ дня |
| Stage F — intake hardening | A, D | низкий | ~1 день |

**Recommended порядок:** A → B → C → E → D → F. Conversion path (D) самый рискованный — после A/B/C/E можно решать, нужен ли он сейчас или после Phase 4.

---

## 7. Контракты и инварианты

1. **`Lead.lead_type` — set-once.** После создания не меняется (нет UI / API для смены типа). Если нужно конвертировать — это отдельная операция (Stage D), создающая новую запись.
2. **`client` лид всегда имеет `company_id` после §5.6.** До завершения Stage F — может быть NULL, но в pipeline такой лид не должен попадать (фильтр `WHERE company_id IS NOT NULL` для client-stages).
3. **Визуальное различие в UI обязательно.** Не скрывать `lead_type` от пользователя — показ badge во всех местах (list, pipeline, detail).
4. **NBA `client_lead_*` не должны прорастать на `candidate` лиды** и наоборот — exhaustive switch в `compute_lead_next_action`.
5. **Public intake — единственный публичный writer** для `client`-лидов. Никакие другие endpoint-ы не должны принимать `lead_type` от user-input-а.

---

## 8. Acceptance / тесты

1. **Schema-level** — `LeadType` enum, exhaustive coverage в Pydantic.
2. **Writers** — `crud.create_lead` отвергает невалидные значения (тест на «`other`», «`null`», «`Candidate`»).
3. **NBA per type** — для `lead_type='client'` в каждой стадии возвращается ожидаемый `kind` / `reason_code`.
4. **UI badge** — snapshot-тест компонента `LeadCard` для обоих типов.
5. **Conversion** — `POST /leads/{id}/convert-to-company`:
   - 200 + создание Company + переход стадии → `converted`.
   - 409 если уже `converted`.
   - 422 если `lead_type != 'client'`.
   - Идемпотентность (двойной POST не создаёт двух Company).
6. **Public intake** — `application_kind=client` без company_id → лид НЕ создаётся, событие эмитится; с company_id → создаётся `lead_type='client'` (regression-тест уже есть в `test_public_intake.py`).
7. **Visibility per `business_type`** — для `business_type=employer` public-intake `application_kind=client` отвергается с понятной ошибкой.
8. **Analytics** — `leads_summary` возвращает `by_lead_type` с правильными счётчиками.

---

## 9. Открытые вопросы

- **Стадии для client-лидов.** Сейчас `Lead.stage` (`new|contacted|qualified|converted|lost`) одинаков для обоих типов. Для client может потребоваться добавить `pending_company` (см. §5.6) и `proposal_sent`. Решение: отложить до Stage D — может оказаться, что хватает существующих стадий.
- **Иммутабельность `lead_type`.** Обсудить с UX — нужна ли возможность «переклассифицировать» лид (например, candidate, который оказался B2B-клиентом). Вероятно нет: это разные операционные потоки, конвертация через Stage D — корректнее.
- **Quota по client-лидам.** Сейчас `tenant_quota.py` считает все leads общим лимитом. Возможно, в Phase 6 (плановые лимиты) понадобится отдельный лимит для B2B (особенно если HostFlow продаёт «B2B portal» как up-sell).
- **Cleanup demo-seed.** `onboarding_demo_seed.py` создаёт client-лиды без вертикали — после §5 их видно, но действия по ним не имеют осмысленного смысла. Решение: после Stage D — обновить демо-сид, чтобы client-лиды были связаны с CRM-companies.
