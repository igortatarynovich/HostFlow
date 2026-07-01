# Модель данных: установки интеграций и включение на company (ADR-006)

Дополняет [`ADR-006`](ADR-006-marketplace-and-integration-platform.md). Реализация **MVP**: две таблицы без отдельной таблицы каталога офферов (каталог ключей — [`../marketplace-catalog-keys.md`](../marketplace-catalog-keys.md) и `backend/app/constants/marketplace_offer_catalog.py`).

---

## Сущности

### 1. `tenant_integration_installations`

**Смысл:** tenant «установил» интеграцию или marketplace-приложение на уровне workspace (креды / подключение к провайдеру в перспективе унифицируются; сейчас часть провайдеров живёт в legacy-таблицах).

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | UUID string (36) | PK |
| `tenant_id` | string (36) | FK → `tenants.id`, `ON DELETE CASCADE` |
| `offer_key` | string (64) | Slug из каталога |
| `offer_kind` | string (32) | `core_integration` \| `marketplace_app` |
| `status` | string (16) | `pending` \| `active` \| `disabled` |
| `settings_json` | JSON | Несекретные настройки (секреты — вне этой строки) |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

**Ограничения:** `UNIQUE (tenant_id, offer_key)`  
**Индекс:** `(tenant_id, offer_key)`

---

### 2. `company_integration_enablements`

**Смысл:** для данной **company** интеграция, установленная на tenant, **включена** и при необходимости ограничена по использованию (например только Recruitment).

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | UUID string (36) | PK |
| `tenant_id` | string (36) | Денормализация для выборок; должен совпадать с `companies.tenant_id` |
| `company_id` | string (36) | FK → `companies.id`, `ON DELETE CASCADE` |
| `offer_key` | string (64) | Тот же slug, что в установке tenant |
| `is_enabled` | boolean | Вкл для этой company |
| `usage_json` | JSON | Опционально: `modules`, маршруты, политики UI |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

**Ограничения:** `UNIQUE (company_id, offer_key)`  
**Индекс:** `(company_id, offer_key)`, `(tenant_id, company_id)`

---

## Инварианты (сервисный слой)

1. Запись в `company_integration_enablements` допустима, если существует строка `tenant_integration_installations` с тем же `(tenant_id, offer_key)` и `status = active` (MVP — мягкая проверка в API).  
2. `company.tenant_id` должен совпадать с `tenant_id` в строке enablement.  
3. Настройки модулей **per company** по-прежнему — [`ADR-005`](ADR-005-three-level-settings-hierarchy.md) (`company_module_settings`).

---

## Эволюция

- Таблица каталога `marketplace_offers` (версии, провайдер, цена, иконки) — отдельная миграция.  
- Таблица секретов / OAuth-токенов с FK на `tenant_integration_installations.id`.  
- Синхронизация с существующими `meta_lead_credentials`, communications — по плану миграции данных.

---

## История

- 2026-05: MVP-таблицы и документ.
