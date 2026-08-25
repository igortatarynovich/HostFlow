# 🧩 Tenant & Client Access Spec (v1)

## Goal
Обеспечить суперадмину и клиентам полный цикл управления доступами:
- Создание и лицензирование тенантов (агентств/компаний).
- Выдача ролей и лимитов (recruiter/supervisor/client_manager/viewer).
- Возможность клиенту самостоятельно приглашать пользователей в рамках лимита.
- Управление ACL (доступ к компаниям, вакансиям, документам) и контроль стоимости лицензии.

---

## Entities & Tables

### tenants
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `name` | text | Отображаемое название |
| `slug` | text | Уникальный идентификатор (`northwind-logistics`) |
| `type` | enum(`agency`,`company`,`platform`) | см. multi_tenant_model |
| `parent_tenant_id` | UUID? | для sub-clients |
| `status` | enum(`active`,`suspended`,`trial`) | Управление доступом |
| `client_portal_enabled` | bool | Быстрое отключение портала |
| `status_sharing_allowed` | bool | Разрешить share-link |
| `workspace_label` | text? | Отображаемое имя воркспейса в UI |
| `logo_url` / `logo_meta` | text / json | Брендированный логотип (макс 32px по высоте) |
| `created_at/updated_at` | timestamptz |  |

### tenant_licenses
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `tenant_id` | FK | tenant |
| `plan` | text (`agency_pro`, `company_basic`) | тариф |
| `max_recruiters` | int |
| `max_supervisors` | int |
| `max_client_managers` | int |
| `max_viewers` | int |
| `max_storage_gb` | int |
| `max_companies` | int |
| `expires_at` | date |
| `auto_renew` | bool |
| `notes` | text | SLA/комментарии |

### tenant_seat_requests
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `tenant_id` | FK | tenant |
| `requested_by` | UUID | пользователь, отправивший запрос |
| `role` | enum (`administrator`,`supervisor`,`recruiter`,`client_manager`,`viewer`) | для какой роли нужны места |
| `requested_count` | int | количество дополнительных слотов |
| `message` | text | комментарий от клиента |
| `status` | enum (`pending`,`approved`,`rejected`) | обработка суперадмином |
| `resolution_notes` | text | ответ супера |
| `resolved_by` | UUID? | супер админ, закрывший запрос |
| `resolved_at` | timestamptz? | когда обработан |
| `created_at/updated_at` | timestamptz |  |

### tenant_usage (materialized or view)
| Field | Type |
|-------|------|
| `tenant_id` | UUID |
| `recruiter_count` | int |
| `supervisor_count` | int |
| `client_manager_count` | int |
| `viewer_count` | int |
| `storage_used_gb` | numeric |

### invitations
| Field | Notes |
| `id` (UUID), `tenant_id`, `email`, `role`, `invited_by`, `token`, `expires_at`, `status` |

---

## Use Cases

### 1. Tenant Provisioning (Superadmin)
1. В разделе “Platform Control Center” супер-админ вызывает `POST /api/v1/platform/tenants`.
2. Заполняет: `name`, `slug`, `type`, `plan`, лимиты.
3. Система создаёт запись в `tenant_licenses`, отправляет письмо суперадмину/клиенту с инструкциями.
4. В UI отображается карточка тенанта с метриками использования и кнопками:
   - `Impersonate tenant`
   - `Invite tenant admin`
   - `Adjust limits`
   - `Suspend / Reactivate`

### 2. Client Admin Onboarding
1. Суперадмин (или существующий tenant admin) отправляет приглашение через `/api/v1/settings/users/invite`.
2. Приглашённый получает email → задаёт пароль → выбирает язык.
3. Tenant Admin может дальше приглашать других пользователей, пока лимит не исчерпан.
4. UI показывает: “3/5 recruiters used”. При попытке превысить лимит — запрет с подсказкой “Request more seats”.

### 3. Self-Service Seat Management
- Tenant Admin видит раздел “Billing & Team”: таблица пользователей + кнопка “Request more seats”.
- `POST /api/v1/settings/team/seat-requests` создаёт запись в `tenant_seat_requests` (статус `pending`) и уведомляет суперадмина.
- Суперадмин в Platform UI может поднять лимиты (изменить `tenant_licenses.*`). Изменение логируется в audit.
- История запросов доступна в `GET /api/v1/settings/team/seat-requests`.

### 4. ACL & Visibility
- Для каждой компании (`companies`) хранится `client_portal_visibility` (enum `none/read_only/full`).
- Tenant Admin назначает `client_manager` → выбирает компании/вакансии через `company_access`.
- Тумблеры видимости модулей (`candidates`, `leads`, `documents`, `services`, `client_portal`) хранятся в `tenants.settings.modules` и управляются через `/api/v1/settings/team/modules`.
- Суперадмин может глобально отключить клиентский доступ (`client_portal_enabled=false`).

### 5. Suspension & Grace Period
- При неоплате или нарушении — суперадмин ставит `status='suspended'` → API блокирует логин, UI показывает баннер “Account suspended, contact support”.
- Grace period: за 7 дней до `expires_at` система шлёт уведомления (tenant admin + superadmin). После `expires_at` можно перевести в `trial` или `suspended`.

### 6. Audit & Observability
- Любое изменение лицензии/лимита/статуса фиксируется в `audit_log` (`action=tenant.license_update`).
- Метрики:
  - `hf_tenant_seats_used{tenant_id,role}`
  - `hf_tenant_license_expiry_days{tenant_id}`
- Alerts:
  - 80% лимита → email tenant admin.
  - Лицензия истекает через 7 дней → письмо + Slack.

---

## API Overview

### Platform (Superadmin)
- `POST /api/v1/platform/tenants`
- `GET /api/v1/platform/tenants?status=` (фильтры по плану, статусу)
- `PATCH /api/v1/platform/tenants/{id}` — обновление описания/label/флагов
- `POST /api/v1/platform/tenants/{id}/logo` — загрузка логотипа (PNG, ограничение по высоте)
- `PATCH /api/v1/platform/tenants/{id}/license` (изменение лимитов)
- `POST /api/v1/platform/tenants/{id}/suspend`
- `POST /api/v1/platform/tenants/{id}/impersonate` — body `{ "reason": "…" }` required (Phase 5 / SSOT §6); returns time-bound JWT (`type=impersonation`, TTL 30m) + emits `superadmin.impersonation.started`.
- `GET /api/v1/platform/tenants/{id}/modules` — просмотр текущих ACL‑тогглов модулей
- `PATCH /api/v1/platform/tenants/{id}/modules` — включение/выключение модулей без входа в тенант
- `GET /api/v1/platform/tenants/{id}/seat-requests` — список self-service запросов на дополнительные места
- `POST /api/v1/platform/tenants/{id}/seat-requests/{request_id}/decision` — утверждение/отклонение запросов с комментариями

### Tenant Admin
- `GET /api/v1/settings/team` (список пользователей + usage)
- `GET /api/v1/settings/team/modules` — текущие ACL-тогглы модулей (кандидаты, лиды, документы, client_portal)
- `PATCH /api/v1/settings/team/modules` — включить/отключить модули
- `GET /api/v1/settings/team/seat-requests` — история self-service запросов
- `POST /api/v1/settings/team/seat-requests` — запросить дополнительные места
- `PATCH /api/v1/settings/team/branding` (workspace label)
- `POST /api/v1/settings/team/branding/logo` (загрузка логотипа тенанта)
- `POST /api/v1/settings/users/invite`
- `PATCH /api/v1/settings/users/{id}` (смена роли, блокировка)
- `GET /api/v1/settings/license` (показывать лимиты и тариф)

### Client Portal
- `client_manager` и `viewer` логинятся через тот же `/api/v1/auth/login`, но видят только Client Dashboard.
- Tenant Admin управляет видимостью модулей: флаги `allow_candidates`, `allow_documents`, `allow_orders`.

---

## UX Highlights

- **Platform > Tenants list**: таблица с колонками `Name`, `Plan`, `Users used/limit`, `Companies`, `Status`, `Actions`.
- **Tenant Admin > Billing & Team**: карточка лицензии + лимиты + usage графики.
- **Invitations UI**: список pending invites, кнопка “Resend”, “Copy invite link”.
- **Seat Request Modal**: форма “Сколько дополнительных слотов и какой роли? Комментарий.” → создаёт тикет/notification.
- **Suspended state**: баннер и только read-only доступ к данным плюс кнопка “Contact support”.
- **Platform > Tenant detail**: блок с тогглами модулей (Candidates/Leads/Documents/etc) и виджет seat-requests с кнопками “Approve/Reject” + поле комментария.

## Business-Type Routing Rule

- `tenants.settings.business_type` должен влиять на default workspace routing после signup и company bootstrap.
- После обязательного шага `/app/onboarding/company` tenant получает business-aware first working route:
  - `agency` -> recruiting-first workspace (`/app/candidates` или `/app/vacancies`)
  - `employer` -> hiring-first workspace (`/app/vacancies` или `/app/candidates`)
  - `services` -> client-first workspace (`/app/clients`)
- Orientation-mode onboarding не должен блокировать рабочие разделы после создания первой компании.
- Retention CTA, empty states и dashboard shortcuts обязаны использовать тот же route-map, а не локальные hardcoded пути.

---

## Security & Controls

- SSO-ready: возможность подключения SAML/OIDC для крупных клиентов (план `enterprise`).
- MFA (email/SMS/app) опционально — флаг в лицензии.
- Rate limits на invitations (например, 20/день).
- Data export: Tenant Admin может запросить выгрузку (готовим `/api/v1/settings/data-export`).
- Everything is tenant-scoped; superadmin impersonation устанавливает `SET LOCAL app.tenant_id`.

---

## Rollout Plan
1. **Phase 1** – Backend модели и API (`tenants`, `tenant_licenses`, invitations, seat usage).
2. **Phase 2** – Platform UI (список тенантов, карточка, управление лицензиями).
3. **Phase 3** – Tenant Admin Team UI, self-service seat management, клиентский портал toggle.
4. **Phase 4** – Billing integration, SSO/MFA options, data export.

Каждая фаза сопровождается тестами (API + e2e), обновлением `docs/specs/core.md` и инструкциями по деплою.
