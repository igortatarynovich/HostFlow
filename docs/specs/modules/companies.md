# Module: Companies

## Назначение
Модуль хранит два разных класса компаний tenant:
- **Operating Company** — собственная компания/профиль tenant, от лица которой совершаются действия, выставляются счета, подписываются договоры, работают RODO/legal templates и branding.
- **Client Company** — клиент/контрагент tenant, с которым ведётся CRM- и delivery-работа.

Эти классы не должны смешиваться ни в billing, ни в onboarding, ни в subscription limits.

---

## Сущности
- **Company** (`id`, `tenant_id`, `name`, `legal_name`, `tax_id`, `phone`, `email`, `website`, `country_code`, `country`, `city`, `address`, `notes`, `is_archived`, `contacts{}`, `extra{}` — блоки `company_role`, `company_type`, `legal`, `billing`, `operations`, `compliance`, `client_portal`, `integrations`, `contracts[]`, `company_orders[]`)
- **Vacancy** (см. модуль Vacancies)
- **Contact** (вложенный объект: имя, должность, телефон, email)

---

## API
| Метод | URL | Назначение | Доступ |
|--------|-----|-------------|--------|
| `GET /api/v1/companies` | Список компаний с фильтрацией | ✅ (Administrator, Supervisor, Recruiter — в рамках ACL) |
| `POST /api/v1/companies` | Создание компании | ✅ (Owner, Manager) |
| `GET /api/v1/companies/{id}` | Детали компании | ✅ |
| `PUT /api/v1/companies/{id}` | Обновление данных (deep merge `extra`, синхронизация `contacts`) | ✅ (Owner) |
| `GET /api/v1/companies/{id}/vacancies` | Список вакансий компании | ✅ |

### Company ACL (tenant scoped)

| Метод | URL | Назначение | Доступ |
|--------|-----|-------------|--------|
| `GET /api/v1/admin/companies/{id}/access` | Список пользователей с доступом к компании | ✅ (Administrator, Supervisor — свои рекрутеры) |
| `POST /api/v1/admin/companies/{id}/access` | Назначить доступ пользователю (просмотр/редактирование) | ✅ (Administrator, Supervisor для своих рекрутеров) |
| `DELETE /api/v1/admin/companies/{id}/access/{user_id}` | Отозвать доступ пользователя | ✅ (Administrator, Supervisor для своих рекрутеров) |

- Администраторы видят и управляют всем ACL компании.
- Супервайзеры видят только себя и рекрутеров под своей ответственностью; могут выдавать/отзывать доступ лишь этой группе.
- Каждое изменение фиксируется в `company.access_granted` / `company.access_revoked` и в `user`-audit карточки сотрудника.
- Выдача доступа поддерживает флаг `can_edit` (разрешить правки карточки компании).

Фильтры:
- `?country=PL`
- `?include_archived=true`
- `?q=trakt`

### Company role contract

- `extra.company_role = operating`
  - собственная компания tenant;
  - участвует в onboarding bootstrap;
  - может быть `issuer company` в invoicing;
  - считается в license limit `tenant_licenses.max_companies`.
- `extra.company_role = client`
  - клиент/контрагент;
  - не считается в лимит operating profiles;
  - не может использоваться как issuer company.

Правило default creation:
- onboarding создаёт `operating company`;
- workspace `/app/clients` по умолчанию создаёт `client company`.

### Operating company ownership scope

`Operating company` — это основной профиль подписчика и source-of-truth для действий "от лица компании":
- issuer data для invoicing (название, NIP/Tax ID, юридический адрес, банковский счет);
- team ownership (`owner_user_id`, `manager_user_id`) и делегирование доступа;
- привязка рабочих сущностей tenant (`clients`, `leads`, `candidates`, `vacancies`, `service orders`, `invoices`, `presets/automations`).

Важное правило:
- отсутствие части реквизитов не блокирует сам CRM, но блокирует полноценное выставление фактур до заполнения обязательных issuer-полей.

---

## UI
- **CompanyList** — таблица всех компаний с фильтрами (статус, страна, активность).  
- **CompanyCard** — операционная карточка компании/клиента: primary focus на `contacts`, `orders`, `contracts`, `billing/invoice data`, `activity/communications`; не должна превращаться в dump всех secondary sections.  
- **CompanyForm** — форма редактирования; блок «Документы (сводка)» **не показывается**.  
- При архивации компании (`is_archived=true`) — вакансии остаются в текущем статусе, регулирование выполняется вручную по бизнес-правилам.  

---

## Структура карточки

`extra` — основная корзина детализации компании (JSONB), куда складываются тематические секции карточки:

| Блок | Содержимое | Комментарии |
|------|------------|-------------|
| `legal` | Регистрационные и правовые данные (`reg_no`, `vat_eu`, `established_at`, `transport_license_number`, `insurance_policy_no`, `registered_address{}`, `operational_address{}`, `authorized_representatives[]`) | Адреса хранятся как структуры, представители — массив объектов. |
| `billing` | Платёжные настройки (`default_currency`, `payment_terms_days`, `invoice_email`, `billing_address{}`, `einvoice_peppol{participant_id,scheme}`, `bank_accounts[]`) | Счета содержат `bank_name`, `iban`, `swift_bic`, `label`, `is_primary`. |
| `operations` | Производственные параметры (`fleet_tractors`, `fleet_intl_perc`, `fleet_local_perc`, `drivers_total`, `has_adr_operations`, `work_modes[]`, `trailers{}`, `lanes{origins[],destinations[]}`, `cargo_types[]`, `languages[]`, `preferred_nationalities[]`) | Значения чисел приводятся к `int` на backend. |
| `compliance` | Отчёт по проверкам (`fin_check_status`, `aml_required`, `iso9001`, `doc_valid_until`, `last_compliance_check_at`) | `fin_check_status` синхронизируется с модулем `fin_checks`. |
| `client_portal` | Настройки клиентского портала (`enabled`, `url`, `last_sync_at`, `portal_roles[]`, `permissions`) | `portal_roles` — массив объектов `{full_name, email, role}`. |
| `integrations` | Интеграции (`provider_ids[]`, `webhooks[]`, `branding{logo_url,primary_color}`) | Webhooks содержат `event` и `target`. |
| `contracts` | Контракты с клиентом (`title`, `status`, `starts_at`, `ends_at`, `reference`, `code`) | Массив объектов. |
| `company_orders` | Активные/исторические заказы (`title`, `status`, `starts_at`, `ends_at`, `required_drivers`, `client_reference`, `code`) | `required_drivers` — план headcount. Виджет «Нет водителей» / «Трудоустроено X / Y» считает кандидатов со статусом `employed` («Трудоустроен») на вакансиях этой компании (`recruitment_candidates_employed`), а не ручное поле `hired_drivers`. |

Колонка `contacts` также хранится в JSONB и при сохранении карточки синхронизируется в `extra.contacts`. Каждый `PUT /companies/{id}`:

1. Обновляет скалярные поля компании.
2. Выполняет глубокое слияние (`deep_merge`) текущего `extra` с payload, чтобы не потерять существующие блоки.
3. При наличии `contacts` в payload обновляет колонку `contacts` и зеркалирует их в `extra.contacts`.

### Operational card priority

Primary sections:
- `contacts`
- `company_orders`
- `contracts`
- `billing` (как customer invoicing data, не SaaS subscription settings)
- `activity/communications`

Secondary sections:
- `legal`
- `operations`
- `compliance`
- `client_portal`
- `integrations`

Правило:
- secondary sections допустимы, но не должны занимать первичную рабочую поверхность карточки по умолчанию.
- для `services` business type карточка компании/клиента становится одной из главных operational surfaces.

### Business-type preset rule

- `agency`: company/client card по умолчанию поддерживает recruiting customer workflow (`vacancies`, `contacts`, `contracts`, `communications`).
- `employer`: company card по умолчанию ближе к own-company profile и hiring operations; external client-management не должен доминировать.
- `services`: company/client card обязана быть primary CRM surface с акцентом на `orders`, `billing`, `contracts`, `communications`, `invoice actions`.

---

## События
| Событие | Условие | Действие |
|----------|----------|----------|
| `company.created` | Создана новая компания | Добавляется в общий список tenant |
| `company.updated` | Изменены поля | Обновляется кэш и лог изменений |
| `company.deactivated` | is_archived → true | Вакансии остаются в текущем статусе, команды закрывают их вручную |
| `company.reactivated` | is_archived → false | Вакансии остаются закрытыми (требуется ручная активация) |

---

## Безопасность
- Все компании принадлежат `tenant_id` и защищены политикой RLS.  
- Только пользователи текущего tenant имеют доступ к своим компаниям.  
- Рекрутеры видят и редактируют компании только при наличии явного доступа (`user_company_access`); доступ можно выдавать через admin ACL, и он определяет, какие кандидаты и пайплайн-стадии доступны рекрутёру.
- Роль **Viewer** имеет только чтение.  
- Деактивация компании возможна только владельцем tenant.  
- При удалении компании — каскадное удаление вакансий.  

---

## Тесты
- CRUD операции (создание черновика, получение, обновление полной карточки).  
- Проверка RLS и tenant-изоляции.  
- Проверка сохранения `contacts` и deep-merge `extra` после `PUT`.  
- Проверка фильтров по активности и стране, а также `company_id` во вакансиях/кандидатах.  

---

## Mapping (DB ↔ Model ↔ API ↔ UI ↔ Tests)

| Уровень | Что описывает | Источник | Правила/валидация | Эндпоинты/операции | Тесты |
|----------|----------------|-----------|--------------------|--------------------|--------|
| **DB** | Таблица `companies` (`id`, `tenant_id`, `name`, `legal_name`, `tax_id`, `phone`, `email`, `website`, `country_code`, `country`, `city`, `address`, `notes`, `is_archived`, `contacts` JSONB, `extra` JSONB, `created_at`, `updated_at`) | `backend/alembic/versions/202512120001_company_profile_expansion.py` (+ старые `202512090001*`) | `tenant_id` обязателен; `contacts`/`extra` NOT NULL; FK на `vacancies` (`CASCADE`) | `make mig-rev` → `make mig` | Проверка миграций, FK, RLS |
| **Model** | SQLAlchemy-модель `Company` | `backend/app/models/company.py` | `MutableDict` JSON для `contacts`/`extra`, UTC `updated_at`, `relationship` с `Vacancy` | CRUD в `backend/app/modules/companies/crud.py` | Юнит-тесты CRUD, каскады, deep merge |
| **API Schemas** | `CompanyCreate`, `CompanyUpdate`, `CompanyOut`, `LegalProfile`, `BillingProfile`, `OperationsProfile`, `ComplianceProfile`, `PortalProfile`, `IntegrationsProfile`, `Contact`, `BankAccount`, `CompanyReadiness` | `backend/app/modules/companies/schemas.py` | Строгая валидация IBAN/BIC, ролей контактов, рабочих режимов, статусов комплаенса | `/api/v1/companies` (GET, POST, PATCH) + секционные эндпоинты профиля | API-тесты: CRUD, профиль, банк/контакты, readiness |
| **UI / Form** | Страница карточки компаний | `hostflow-frontend/src/pages/Companies.tsx` | Редактор секций профиля, readiness-индикаторы, синхронизация `contacts` ⇄ `extra` | REST через `/api/v1/companies*` + эндпоинты секций | RTL/интеграционные тесты формы (при наличии) |
| **Business Rules** | Связь компаний ↔ вакансии ↔ кандидаты | `docs/specs/modules/companies.md` | Архивация не закрывает вакансии автоматически; deep merge `extra`; зеркалирование `contacts` → `extra.contacts` | `PUT /api/v1/companies/{id}`, `/api/v1/vacancies*`, `/api/v1/candidates*` | Сквозные тесты фильтров и связей |
| **RLS / Security** | Изоляция данных по `tenant_id` | Alembic + `backend/app/db/deps.py` | `set_config('app.tenant_id')`, RLS политики, ACL | Все `/api/v1/companies*` | Проверка tenant-изоляции и ACL |

---


## AI Agent Notes
- Агент должен использовать `tenant_id` при любой операции с компаниями.  
- При архивации компании нужно явно проверить/инициировать закрытие вакансий (автоматически не закрываются).  
- Нельзя физически удалять компании — используем `is_archived=true`.  
- Любые изменения компании должны публиковать событие (`company.updated`).  
- Агенту запрещено автоматически активировать вакансии при `company.reactivated`.  
- В тестах необходимо проверять RLS, фильтры, каскады и уведомления.

---

## Integration & Sync
Модуль **Companies** взаимодействует с другими системами и внешними источниками, чтобы поддерживать актуальность данных о клиентах.

### Внутренние связи
- **Vacancies:** синхронизируется через `company_id`; при изменении компании обновляются все связанные вакансии.  
- **Candidates:** кандидаты наследуют ссылку на компанию через вакансию.  
- **Documents:** не имеют прямой связи, но могут использовать данные компании для метаданных (например, при экспорте отчетов).  
- **Reminders:** напоминания по компаниям (например, обновить контакт или продлить контракт) создаются вручную или через планировщик.

### Внешние интеграции
| Источник | Назначение | Метод |
|-----------|-------------|--------|
| **CRM (Zoho, HubSpot, Bitrix)** | Импорт/экспорт компаний и контактов | API или webhook |
| **ERP клиента** | Проверка статуса сотрудничества (активен/приостановлен) | Синхронизация по `slug` или `api_key` |
| **Email/WhatsApp** | Автоматизация коммуникации с контактами | через Notification Engine |
| **Meta / Google Sheets** | Импорт новых компаний из рекламных лидов | webhooks и `lead_to_company` pipeline (опционально) |

### Поля для внешней синхронизации
- `external_id` — идентификатор во внешней CRM.  
- `source` — строка с названием системы-источника.  
- `synced_at` — время последней синхронизации.  

### Логика обновления
1. Если компания существует (по `external_id` или `slug`) — обновляется.  
2. Если не существует — создаётся с `source` и меткой `imported=true`.  
3. Обновления фиксируются в `company.updated` и записываются в audit log.  
4. Ошибки синхронизации записываются в `integration_logs`.

### AI Agent Notes
- При импорте компаний агент должен проверять уникальность `slug` и `external_id`.  
- Нельзя перезаписывать данные tenant без подтверждения.  
- При внешних интеграциях использовать sandbox для тестов.  
- Все операции импорта должны быть идемпотентными.
