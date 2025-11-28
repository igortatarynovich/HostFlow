# 🧱 HostFlow Multi-Tenant Architecture

## 1. Overview

HostFlow is designed as a **multi-tenant SaaS ecosystem** that supports three hierarchical levels of tenancy:

| Level | Entity | Description | Example |
|-------|---------|--------------|----------|
| **L0 – Platform Core** | HostFlow HQ | Master level that manages tenants, licenses, and global configuration. | HostFlow platform |
| **L1 – Tenant (Agency)** | Recruitment or HR agency | Owns its data, manages recruiters and sub-clients (companies). | Work Host, TruckForce |
| **L2 – Sub‑Client (Company)** | Transport company or business client | Has limited access (client portal) to its candidates, documents, and vacancies. | Citronex, OmegaPil |
| **L3 – User / Candidate** | Individual | Limited account for candidate or employee data access. | Driver profile |

This architecture allows HostFlow to operate simultaneously as:
- a **recruitment management system** for agencies,
- a **SaaS product** for transport companies,
- a **white‑label platform** for partner agencies.

---

## 2. Data Isolation and Tenant Hierarchy

### 2.1 Tenant Ownership
Each entity (users, companies, candidates, documents, vacancies, etc.) includes a `tenant_id` field.

```sql
tenant_id UUID NOT NULL
REFERENCES tenants (id)
```

All tenant-scoped tables are protected by PostgreSQL **Row-Level Security (RLS)**.  
Current tenant context is activated via:

```sql
SET LOCAL app.tenant_id = '<tenant_uuid>';
```

### 2.2 Parent–Child Relationship

To support agency → client hierarchy:

```sql
ALTER TABLE tenants
ADD COLUMN parent_tenant_id UUID NULL REFERENCES tenants (id);
```

This allows an agency to have sub‑clients (companies) under its control.

Example hierarchy:

```
HostFlow (SUPERADMIN)
 ├── Tenant: Work Host (type: agency)
 │    ├── Company: Citronex (client portal)
 │    └── Company: Poltrakt
 ├── Tenant: TruckForce (type: agency)
 │    └── Company: EuroTrans
 └── Tenant: Citronex (type: company, independent SaaS license)
```

---

## 3. Tenant Types

```sql
type ENUM('agency', 'company', 'platform')
```

| Type | Purpose |
|------|----------|
| `platform` | HostFlow core platform; manages all tenants and licenses |
| `agency` | Tenant with internal recruiters and external clients |
| `company` | Independent SaaS customer with its own HR processes |

---

## 4. Roles and Permissions

> Полная RBAC-матрица и привязка панелей описаны в `docs/specs/architecture/rbac_matrix.md`. Ниже — обзор на уровне мульти-тенант модели.

| Role | Scope | Доступные панели | Ключевые возможности | Ограничения |
|------|--------|------------------|----------------------|-------------|
| **SUPERADMIN** | Global | Platform Control Center | Управляет лицензиями, глобальными интеграциями, аудитом | Нет прямого доступа к операционным данным без переключения тенанта |
| **ADMINISTRATOR / OWNER** | Tenant | Tenant Admin Console, Supervisor Dashboard | Управление пользователями, локализацией, ruleset, настройками импорта, SLAs | Не видит других тенантов |
| **SUPERVISOR** | Tenant | Supervisor Dashboard, Recruiter Workspace | Контроль пайплайнов, unmatched лидов `needs_routing`, напоминаний, маркировка уведомлений | Не может менять глобальные настройки, не может маршрутизировать лиды без маппинга вручную |
| **RECRUITER** | Tenant | Recruiter Workspace | Работа с лидами/кандидатами/документами, шаблоны в рамках своей роли | Не видит настройки, не распределяет лидов которые не прошли маппинг |
| **CLIENT_MANAGER** | Sub-client (company) | Client Portal | Управляет кандидатами/документами своей компании, создаёт сервис-ордера | Не видит другие компании, ограничения по doc templates |
| **CANDIDATE** | Individual | Candidate Portal | Загружает документы, отслеживает статусы, получает напоминания | Только свои данные |
| **VIEWER** | Tenant | Supervisor Dashboard (read-only) | Просмотр ключевых данных | Нет прав на изменение |

Recruiters и Supervisors не могут самостоятельно распределять лидов, если они не прошли автоматический маппинг — такая операция доступна только администраторам. Все операции выполняются в контексте текущего `tenant_id` (RLS).

---

## 5. Row-Level Security (RLS) Policies

### 5.1 Base Tenant Isolation
```sql
CREATE POLICY tenant_isolation ON candidates
USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

### 5.2 Client Access Restriction
```sql
CREATE POLICY client_own_candidates ON candidates
FOR SELECT USING (
  company_id IN (
    SELECT id FROM companies
    WHERE manager_id = current_user_id()
  )
);
```

### 5.3 Shared Candidates (Future)
Cross‑tenant sharing will use a linking table:

```sql
shared_candidates (
  candidate_id UUID,
  source_tenant_id UUID,
  target_tenant_id UUID,
  permissions JSONB
);
```

---

## 6. Licensing Model

Each tenant must have an associated license entry:

```sql
licenses (
  id UUID PRIMARY KEY,
  tenant_id UUID REFERENCES tenants (id),
  plan TEXT,
  status TEXT,
  seats INT,
  valid_until DATE,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Example License JSON

```json
{
  "plan": "agency_pro",
  "features": {
    "max_users": 25,
    "max_clients": 15,
    "shared_candidates": true,
    "custom_fields": true,
    "api_access": false
  }
}
```

---

## 7. API and Tenant Management

### 7.1 Tenant Creation
```bash
POST /api/v1/platform/tenants
{
  "name": "Citronex",
  "type": "company",
  "plan": "company_basic"
}
```

### 7.2 Tenant Context in Requests
Each API call must include the tenant identifier header:

```
X-Tenant-Id: <uuid>
```

---

## 8. SaaS Scenarios

| Scenario | Tenant Type | Description |
|-----------|--------------|-------------|
| **Agency CRM** | agency | Recruitment agency manages candidates and client companies. |
| **Company SaaS** | company | Transport company operates independently. |
| **Agency Partner License** | agency (reseller) | Partner agency runs its own client ecosystem. |
| **Candidate Portal** | n/a | Individual candidate access to personal profile and documents. |

---

## 9. Future Extensions

- White‑label branding per tenant (logo, colors, subdomain)
- Billing integration (Stripe / Paddle)
- Tenant provisioning automation (`make tenant:create <name>`)
- Audit trail per tenant
- “Convert Company → Tenant” feature for agency clients upgrading to SaaS

---

## 10. Tenant Branding & Localization

- Брендовые параметры (`logo_url`, `primary_color`, `secondary_color`, `font_family`, `default_locale`, `support_contacts`) хранятся в таблице `tenant_branding`.
- Флаги контроля: `is_white_label`, `allow_client_overrides`. Если активирован white-label, по умолчанию скрывается бренд HostFlow во всех порталах.
- Параметры применяются на всех панелях внутри тенанта. Клиентский портал может переопределять подмножество (логотип, приветственный текст), описано в `docs/specs/architecture/rbac_matrix.md`.
- Локализация задаётся на уровне тенанта (`default_locale`) и может быть переопределена на уровне пользователя. Фолбэки и реестр ключей — см. `docs/specs/i18n/index.md`.
- Переключение языка не нарушает RLS: строки переводов кэшируются по `tenant_id` + `locale`.

---

## 11. Разделение настроек и рабочих модулей

- **Platform Control Center** — только супер-администратор. Управляет глобальными настройками, лицензиями и брендингом по умолчанию.
- **Tenant Admin Console** — конфигурация внутри тенанта: импорт CSV, routing, ruleset, локализация, doc templates, webhooks. Представлена отдельным namespace `/api/v1/settings/...`.
- **Рабочие панели (Supervisor, Recruiter)** — только операционные действия: лидами, документами, напоминаниями. Настройки скрыты.
- **Client/Candidate порталы** — отдельные домены/поддомены с темизацией тенанта.

API следует поддерживать разделение на уровне роутов (например, `/api/v1/settings/notifications`, `/api/v1/leads`, `/api/v1/documents`). Cross-panel доступ контролируется RBAC и middleware, которое валидирует роль и панель назначения (см. `docs/specs/architecture/rbac_matrix.md`).

## 10. Role-Based Workspaces

HostFlow UI разделён на рабочие области по ролям. Это исключает смешение служебных настроек с ежедневными задачами.

| Workspace | Кто видит | Содержимое |
|-----------|-----------|------------|
| **Platform Control Center** | SUPERADMIN (L0) | Управление лицензиями, биллингом, глобальными интеграциями, реестром tenants. |
| **Tenant Admin Console** | OWNER / ADMINISTRATOR (L1) | Управление пользователями и ролями, настройки уведомлений и локализации, ruleset политики, маршрутизация лидов, мониторинг SLA. |
| **Supervisor Dashboard** | SUPERVISOR (L1) | Мониторинг пайплайнов рекрутеров, unmatched лидов со статусом `needs_routing`, контроль напоминаний и документов. |
| **Recruiter Workspace** | RECRUITER (L1) | Лиды, кандидаты, вакансии, документы, задачи. Нет доступа к глобальным настройкам и ручной маршрутизации лидов, не прошедших маппинг. |
| **Client Portal** | CLIENT_MANAGER (L2) | Карточки своих кандидатов, документы, статусы заявок. |
| **Candidate Portal** | USER / CANDIDATE (L3) | Просмотр собственных документов, загрузка файлов, отслеживание этапов. |

> Лиды со статусом `needs_routing` видны только администраторам и супервизорам. Рекрутеры получают уведомления о новых лидах/кандидатах, но не могут распределять “неразрешённые” лиды.

Все рабочие области используют единый backend и RLS; UI навигация отделяет “Настройки” от операционных модулей.

---

## 11. Localization Model

- Система работает на трёх языках: **английский (основной)**, русский и польский.
- Тексты интерфейса хранятся в resource-файлах (`en`, `ru`, `pl`) и подгружаются по tenant/пользовательскому выбору.
- Документы и шаблоны поддерживают локализованные названия и описания (`meta.localization`).
- Уведомления отправляются на языке пользователя; при отсутствии перевода используется английский источник.
- Переводы управляются из Tenant Admin Console (роль `OWNER`/`ADMINISTRATOR`), Superadmin может подключать новые локали на уровне платформы.

### 11.1 Registry & Fallback Policy
- Единый реестр ключей (`/i18n/registry.yml`) хранится в репозитории, source-язык — `en`. Формат ключа: `module.page.block.label`, только латиница, цифры и `_`; пробелы и спецсимволы запрещены.
- Обновление переводов выполняется через merge нового набора ключей в `registry.yml`; любые изменения требующий релиза фиксируются в changelog i18n.
- Алгоритм фолбэка: `tenant_locale` → `en` → `{KEY}` (ключ выводится как текст, пустые строки запрещены); все клиенты получают видимое значение даже при отсутствии перевода.
- Версионирование переводов: релиз-кандидат помечает текущий набор ключей «замороженным» (`frozen_at=<revision>`); новые строки после freeze становятся недоступны для релиза до следующего цикла.

---

## 12. Tenant Branding & Theming

- Параметры брендирования на уровне tenant: `logo_url`, `primary_color`, `secondary_color`, `accent_color`, `default_locale`, `date_format`, `time_format`.
- Агентство задаёт тему для базовых панелей; клиентские порталы наследуют оформление, но могут переопределить логотип и вторичный цвет (для отстройки бренда клиента). Основные цвета и шрифты остаются из настроек агентства.
- Candidate Portal использует tenant-настройки; индивидуальные кастомизации запрещены.
- Platform Control Center управляет глобальными темами и white-label шаблонами; применяется только супер-админом.

---

## 13. Migration & Versioning Policy

- Alembic-миграции: только вперёд (no downgrade в проде), отдельная ревизия на каждый модуль; имя ревизии `YYYYMMDDHHMM_<scope>`.
- Перед merge любая миграция проходит dry-run на staging; откаты выполняются через компенсирующие миграции.
- Семантика API: `major.minor.patch`. `minor` релизы сохраняют обратную совместимость (старые поля остаются), `major` могут удалять/переименовывать поля и требуют миграций данных + обновление документации.
- Хранилище схем (`docs/specs/db/*.sql`) синхронизируется после каждой миграции; отклонения блокируют release.

---

## 14. Observability & Metrics

- Метрики по умолчанию:
  - `documents_processing_time` — среднее время между созданием документа и переходом в `approved`.
  - `document_step_overdue_total` — количество просроченных шагов workflow.
  - `lead_conversion_rate` — доля лидов, превращённых в кандидатов (по этапам события).
- Audit log фиксирует: смены статусов документов/шагов, изменения дат `due_at`, отмены напоминаний, ручную маршрутизацию лидов.
- Каждое уведомление (email/UI/webhook) содержит `delivery_status`; ошибки доставки компенсируются ретраем и журналируются.

---

## 15. Summary

HostFlow’s multi‑tenant model ensures:
- **Data isolation** via `tenant_id` and RLS;
- **Role‑based access** within each tenant;
- **Scalability** from agencies to full SaaS companies;
- **Monetization flexibility** through licensing and white‑label options.

This is the canonical architecture enabling HostFlow to function as a multi‑layer recruitment and HR ecosystem for the European transport sector.

---
