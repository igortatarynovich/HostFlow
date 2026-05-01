# Tenant Types — `Tenant.type`, `business_type`, `Tenant.modules`

**Назначение:** один справочник для трёх параллельных «классификаций» tenant-а в HostFlow, которые сегодня путают пользователей и разработчиков:

1. **`Tenant.type`** — DB enum (`agency` / `company` / `platform`) — **низкоуровневый workspace-режим**, влияющий на cross-tenant видимость, handoff, JWT-роли.
2. **`tenant.settings.business_type`** — JSON-строка (`agency` / `employer` / `services`) — **бизнес-сегмент**, который выбирает пользователь в онбординге; влияет на module visibility, role defaults, аналитический профиль, шаги wizard-а.
3. **`tenant.settings.modules`** — JSON-объект булевых флагов (`candidates`, `companies`, `vacancies`, `documents`, `leads`, `services`, `client_portal`) — **per-tenant feature toggles**.

Эти три понятия **разные**, могут не совпадать, и каждое имеет свою операционную семантику.

**Связанные документы:**

- `docs/HOSTFLOW_AUDIT_AND_PLAN.md` Phase 2 §2.6.A, §2.6.E (todo, закрываемые этим документом).
- `docs/specs/plans-matrix.md` — план-биллинг (ортогонально `business_type`).
- `docs/specs/personas.md` — кто на каком экране что видит (роли × модули).
- `docs/specs/own-company-model.md` — отношение tenant ↔ OwnCompany ↔ CRM operating Company.

---

## 1. `Tenant.type` (DB enum)

### 1.1. Определение

```37:81:backend/app/models/tenant.py
class TenantType(str, Enum):
    agency = "agency"
    company = "company"
    platform = "platform"
...
    type: Mapped[TenantType] = mapped_column(
        SAEnum(TenantType, name="tenant_type_enum", native_enum=False),
        nullable=False,
        default=TenantType.agency,
        server_default=TenantType.agency.value,
    )
```

- Колонка `tenants.type`, NOT NULL, default `agency`.
- Backend-only — **пользователь нигде не выбирает это значение явно** в onboarding wizard / company page.

### 1.2. Кто и когда устанавливает

| Точка | Поведение |
|-------|-----------|
| Signup (`backend/app/auth/router.py:198-206`) | новый tenant создаётся всегда с `type=TenantType.agency`. |
| Bootstrap из первой operating-компании (`backend/app/modules/companies/crud.py:785-788`) | если бизнес-тип компании = `employer`, tenant перепрошивается в `TenantType.company`. Для `services` остаётся `agency` (явный комментарий в коде ~1332-1336). |
| Platform admin (`backend/app/api/v1/platform/tenants.py:77-93`) | при provisioning может явно передать любой из трёх. |

`platform` в продакшен-flow **не выставляется автоматически**; зарезервирован под платформенных супер-tenant-ов.

### 1.3. Что зависит от `Tenant.type`

| Операция | Поведение |
|----------|-----------|
| **Cross-tenant видимость для handoff** (`backend/app/db/deps.py:62-80`) | если `Tenant.type == company` → tenant подтягивает связанные agency-tenant-ы через `tenant_links`. |
| **Создание tenant_link** (`backend/app/api/v1/tenants/router.py:197-198, 255-257`) | client-сторона linka обязана быть `Tenant.type == company`. |
| **Handoff PII scope** (`backend/app/services/handoff.py:191-196`) | `is_client_tenant_for_list` ветвится на `company` vs `agency`. |
| **JWT recruiter → `client_processor` matrix** (`backend/app/api/v1/settings/team.py:356-357`, frontend mirror `hostflow-frontend/src/hooks/usePermissions.ts:189-228`) | роль `client_processor` доступна только в tenant-ах типа `company`. |
| **Fallback `business_type`** (`backend/app/modules/leads/service/_helpers.py:80-85`, `backend/app/api/v1/tenants/service.py:257-266`) | если `tenant.settings.business_type` пуст → `Tenant.type == company` ⇒ `employer`, иначе ⇒ `agency`. |

**Семантика по значению:**

- **`agency`** — мультиклиентский workspace (own-company обслуживает разных клиентов; есть handoff к client-tenant-ам). Также используется для `services` бизнеса.
- **`company`** — single-employer workspace (один работодатель, нанимает в свои вакансии; handoff видит agency-tenant-ы как поставщиков).
- **`platform`** — admin-only super tenant (HostFlow-команда); регулярные пользователи не должны его иметь.

### 1.4. UI surface

`Tenant.type` **не показывается** обычному пользователю и не редактируется через UI. Видна только в platform admin (`hostflow-frontend/src/pages/admin/TenantsPage.tsx`). Frontend type — `TenantType` в `hostflow-frontend/src/api/types.ts:56-57`.

---

## 2. `tenant.settings.business_type` (JSON)

### 2.1. Определение

JSON-ключ в `Tenant.settings`, значения — `agency | employer | services` (нормализуется в `backend/app/api/v1/onboarding.py:173-179`, `backend/app/api/v1/own_companies.py:202-206`).

Frontend type — **inline union** (нет именованного экспорта `BusinessType`); ближайший аналог — `ActivationBusinessType` в `hostflow-frontend/src/app/activationRoutes.ts:32-35`.

### 2.2. Кто и когда устанавливает

| Точка | Поведение |
|-------|-----------|
| Onboarding company page (`hostflow-frontend/src/pages/OnboardingCompanyPage.tsx:295-304`) | пользователь выбирает карточку (`agency` / `employer` / `services`); фронт зовёт `createOwnCompany({ business_type, extra: { business_type } })`. |
| `POST /api/v1/own-companies/` (`backend/app/api/v1/own_companies.py:252-264`) | при первом own-company вызывает `bootstrap_tenant_for_own_company_onboarding(company_type=bt_norm)`. |
| `_bootstrap_tenant_settings_for_company_type` (`backend/app/modules/companies/crud.py:626-636`) | мерджит `tenant.settings.business_type = bt_norm` + дефолтный module-профиль. |

После онбординга значение в общем случае не меняется (нет явного UI «сменить бизнес-сегмент»).

### 2.3. Что зависит от `business_type`

| Операция | Поведение |
|----------|-----------|
| **Дефолтные module-флаги** (`_onboarding_module_profile`, `backend/app/modules/companies/crud.py:591-635`) | `employer` → выключает `leads`, `services`, `client_portal`; `services` → выключает `candidates`, `vacancies`; `agency` → всё включено. |
| **Role-module defaults** (`backend/app/api/v1/tenants/service.py:257-287`, `_role_defaults_for_tenant`) | дефолтная матрица ролей × модулей формируется из `business_type`. |
| **Lead processing / outcomes** (`backend/app/modules/leads/service/_helpers.py:80-163`, router `backend/app/modules/leads/router.py:532-565`) | `_load_tenant_business_type` определяет, как auto-fill выводит outcome (candidate vs client). |
| **Analytics profile-summary** (`backend/app/api/v1/analytics.py:782-793, 1099-1128`) | KPI-набор и ярлыки на дашборде зависят от сегмента. |
| **Onboarding wizard branching** (`hostflow-frontend/src/pages/OnboardingWizardPage.tsx:58-76, 163-168`) | `employer` пропускает шаг **client**, `services` пропускает шаг **vacancy**. |
| **Activation routing** (`hostflow-frontend/src/app/activationRoutes.ts:69-92`) | следующий-шаг URL после wizard-а зависит от сегмента. |
| **`/onboarding/status`** (`backend/app/api/v1/onboarding.py:142-200`) | предпочитает `Company.extra.company_type` (operating CRM-row) над `tenant.settings.business_type`, если первое заполнено — см. §3 ниже. |

**Семантика по значению:**

- **`agency`** — рекрутинговое агентство, работающее с разными клиентами. Включены leads, vacancies, candidates, documents, client_portal, companies, services (полный набор).
- **`employer`** — работодатель, нанимающий в свои собственные вакансии. Выключены leads/services/client_portal, основной flow — vacancies + candidates + documents.
- **`services`** — компания, продающая услуги (например, услуги релокации/жилья). Выключены candidates/vacancies, упор на companies + leads + services + documents.

### 2.4. Source-of-truth конфликт между OwnCompany и operating Company

Сегодня `business_type` хранится **в трёх местах** одновременно:

1. `Tenant.settings.business_type` (записывается при первом `POST /own-companies/`).
2. `OwnCompany.extra.business_type` (записывается тем же запросом из onboarding).
3. `Company.extra.company_type` (записывается при legacy `POST /companies/` с первой operating-компанией).

`backend/app/api/v1/onboarding.py:142-144` явно отмечает: `OwnCompany.extra` может протухнуть; для UI/билдинга wizard-а используется в первую очередь `Company.extra.company_type` (operating). Канонизация single-source — задача §3 в `docs/specs/own-company-model.md`.

---

## 3. `tenant.settings.modules` (per-tenant feature flags)

### 3.1. Определение

**Не SQL-колонка.** Хранится как JSON-объект в `Tenant.settings.modules`. Канонические ключи задаются в `_MODULE_DEFAULTS` (`backend/app/api/v1/tenants/service.py:177-186`):

```
candidates, companies, vacancies, documents, leads, services, client_portal
```

Дополнительные ключи рядом: `tenant.settings.role_matrix` (роль → разрешённые модули) и `tenant.settings.user_overrides` (per-user фильтр) — `backend/app/api/v1/tenants/service.py:676-684, 885-889, 953-956, 1029-1032`.

### 3.2. Кто и когда устанавливает

| Точка | Поведение |
|-------|-----------|
| `_bootstrap_tenant_settings_for_company_type` (`backend/app/modules/companies/crud.py:591-635`) | при первом own-company записывает дефолтный профиль модулей по `business_type`. |
| `PATCH /api/v1/settings/team/modules` (`backend/app/api/v1/settings/team.py:341-363`) | админ tenant-а может вручную включать/выключать модули; так же редактируется role_matrix и user_overrides. |
| Platform admin (`hostflow-frontend/src/pages/admin/TenantsPage.tsx`) | супер-админ HostFlow может править tenant.modules вручную. |

### 3.3. Что зависит от `modules`

| Операция | Поведение |
|----------|-----------|
| **Backend permission snapshot** (`get_module_settings_snapshot`, `get_effective_role_module_permissions`, `backend/app/api/v1/settings/team.py:341-363`) | определяет «у этого user-а есть доступ к модулю X». |
| **Frontend gate** (`hostflow-frontend/src/hooks/usePermissions.ts:157-211`) | `getTenantModules` + `getTenantEffectiveRoleModules`; `usePermissions` гейтит навигацию, кнопки, страницы. |
| **Лейблы модулей** | `hostflow-frontend/src/modules/tenants/constants.ts:20-26`. |

### 3.4. Scope: per-tenant, **не** per-OwnCompany

Сегодня модули включены/выключены на уровне **tenant**, не на уровне отдельной own-company. Это означает: если tenant имеет несколько own-companies (multi-brand сценарий, потенциально появится в Phase 6), то одни и те же модули видны во всех brand-ах.

**Расширение до per-OwnCompany override** (если в будущем понадобится «branded portal per workspace»):

- Добавить `OwnCompany.extra.modules_override?: Record<ModuleKey, boolean>`.
- В `usePermissions` мерджить с базовым `tenant.modules` (override побеждает).
- В UI добавить отдельный экран «Modules per brand».
- Текущий KPI: **этого нет в Phase 2; задача отложена до Phase 6**, если сценарий вообще подтвердится.

---

## 4. Combination matrix (что встречается в коде)

| `Tenant.type` | `business_type` | Происхождение | Ключевое поведение |
|---|---|---|---|
| `agency` | `agency` | signup default + первая operating-компания типа agency | полный набор модулей (leads + candidates + vacancies + documents + services + companies + client_portal); дефолтный multi-client workspace. |
| `company` | `employer` | первая operating-компания типа employer ⇒ `Tenant.type → company` (`backend/app/modules/companies/crud.py:785-788`) | модули `candidates + vacancies + documents + companies` включены; `leads/services/client_portal` выключены; роль `client_processor` доступна; cross-tenant видимость через handoff. |
| `agency` | `services` | первая operating-компания типа services оставляет `Tenant.type = agency` (явный комментарий в коде ~1332-1336) | модули `companies + leads + services + documents` включены; `candidates/vacancies` выключены. |
| `company` | *(пусто)* | legacy / частично заполненный onboarding | `_business_type_for_tenant` нормализует к `employer`. |
| `agency` | *(пусто)* | legacy / частично заполненный onboarding | нормализуется к `agency`. |
| `platform` | *(пусто)* | platform admin provisioning | super-admin контекст; обычные пользователи не должны попадать сюда. |

**Невалидные комбинации (не должны существовать в проде):**

- `Tenant.type == company` + `business_type == agency` — противоречие (single-employer workspace, маркированный как агентство). Если встречается, это data-corruption, нужен ручной fix.
- `Tenant.type == company` + `business_type == services` — аналогично; `services` явно выбрал `Tenant.type = agency` в bootstrap.
- `Tenant.type == platform` для обычного tenant-а — security risk, должен быть только у платформенных супер-tenant-ов.

---

## 5. Onboarding wizard implications

| Шаг wizard-а | Зависимость |
|---|---|
| Step 1 (Type) | подтверждает `business_type` (выбран на `OnboardingCompanyPage`); не меняет `Tenant.type`. |
| Step 2 (Channel) | не зависит от типа; всегда есть. |
| Step 3 (Client) | **скрыт для `business_type == employer`** (employer не подбирает клиентов). |
| Step 4 (Vacancy) | **скрыт для `business_type == services`** (услуги не имеют вакансий). |
| Step 5 (First lead) | всегда есть; deep-link зависит от того, какие шаги уже выполнены. |

`/onboarding/status` (`backend/app/api/v1/onboarding.py:142-200`) определяет `business_type` следующим образом:

1. Если `Company.extra.company_type` (operating CRM-row) есть — берёт оттуда.
2. Иначе — `Tenant.settings.business_type`.
3. Иначе — fallback из `Tenant.type` (`company` ⇒ `employer`, иначе ⇒ `agency`).

---

## 6. Контракты и инварианты

1. **`Tenant.type` set-once** — после первого signup и bootstrap не должен меняться без миграции. Изменение требует пересмотра handoff, JWT, role matrix.
2. **`business_type` set-once-per-onboarding** — пользователь выбирает один раз; смена сегмента после онбординга не поддерживается UI и почти не поддерживается backend (часть автоматики не пересчитывает `tenant.modules` при смене).
3. **`Tenant.modules` редактируется свободно** — admin может toggle любого модуля; нет inverse-зависимости (frontend не блокирует включение модуля, недоступного по `business_type`).
4. **Single-source business_type** — целевое состояние (`docs/specs/own-company-model.md`): один источник, либо `OwnCompany.extra.business_type`, либо `Tenant.settings.business_type`. До завершения миграции читатели должны использовать `_load_tenant_business_type` (с fallback chain), писатели — обновлять оба места.
5. **`platform` tenant** — никогда не должен возвращаться в `GET /tenants/me` для обычного user-а; защищается guard-ами в `backend/app/api/v1/platform/`.

---

## 7. UI / копирайт ловушки

Сегодня в UI слова **«компания»**, **«работодатель»**, **«агентство»** используются непоследовательно:

- **`OnboardingCompanyPage`**: «Are you an agency / employer / services company?» — выбор `business_type`.
- **`MyCompanyPage`** (`hostflow-frontend/src/pages/MyCompanyPage.tsx:256-257`): показывает `Company.extra.company_type` (а не `tenant.settings.business_type`) — это другая запись.
- **Topbar / breadcrumbs**: `OwnCompany.name` называется просто «Company».

**Действия для UAT (Phase 2.2):**

- Зафиксировать в копирайте, что **«моя компания»** = `OwnCompany` (юр. сущность), **«сегмент бизнеса»** = `business_type` (операционная классификация), **«workspace mode»** = `Tenant.type` (admin-only, не показываем).
- В `OnboardingCompanyPage` добавить tooltip к выбору сегмента: «Это влияет на то, какие модули будут включены и как настраивается дашборд».

---

## 8. Acceptance / тесты

1. **`Tenant.type` enum миграции** — alembic-миграция должна сохранять `agency|company|platform`; добавление новых значений (если когда-то понадобятся) требует обновления handoff/JWT логики.
2. **Bootstrap-консистентность** — после `POST /own-companies/` (первый) проверить:
   - `Tenant.settings.business_type` совпадает с `OwnCompany.extra.business_type`.
   - `Tenant.settings.modules` соответствует `_onboarding_module_profile(business_type)`.
   - Если `business_type == employer` ⇒ `Tenant.type == company`.
   - Если `business_type == services` ⇒ `Tenant.type == agency`.
3. **Wizard step skipping** — для каждого `business_type` проверить, что нужные шаги скрыты в `OnboardingWizardPage`.
4. **`/onboarding/status` precedence** — последовательно подменять три источника `business_type` и проверять порядок (Company.extra → tenant.settings → Tenant.type fallback).
5. **`Tenant.modules` writable / readable** — `PATCH /api/v1/settings/team/modules` должен корректно мутировать только указанные ключи, не затирая `role_matrix` / `user_overrides`.
6. **`platform` isolation** — обычный JWT не должен принимать `Tenant.type == platform` (тест: попытка login-а в platform-tenant с обычным паролем).

---

## 9. Открытые вопросы

- **Ребрендинг копирайта:** «agency / employer / services» в UI — это термины из позднего bootstrap. Возможно, в первой версии продукта стоило бы заменить на «recruitment agency / direct hire / services provider» для ясности (UX-задача).
- **Миграция legacy data:** существуют tenant-ы, созданные до канонизации `business_type`, у которых ключ может отсутствовать. Нужен one-time backfill (см. §6.4) — но без UI-смены сегмента, чтобы не разорвать дашборды.
- **Per-OwnCompany модули** — отложено до Phase 6 (см. §3.4); проектное решение нужно, только если HostFlow начнёт продавать «multi-brand workspace» как отдельный SKU.
- **`platform` provisioning UI** — сейчас только через скрипты; в Phase 7 (admin console) понадобится UI для создания/удаления platform-tenant-ов.
