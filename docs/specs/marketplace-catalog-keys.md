# Каталог ключей Marketplace / Integrations (ADR-006)

Нормативные **slug** для поля `offer_key` в таблицах `tenant_integration_installations` и `company_integration_enablements`. Источник правды в коде: `backend/app/constants/marketplace_offer_catalog.py` (множества `CORE_INTEGRATION_OFFER_KEYS`, `MARKETPLACE_CATEGORIES`, `OFFER_KIND_*`).

Архитектура слоёв и монетизация — [`ADR-006`](architecture/ADR-006-marketplace-and-integration-platform.md). Модель БД — [`marketplace-integrations-data-model`](architecture/marketplace-integrations-data-model.md).

---

## Категории витрины (`MARKETPLACE_CATEGORIES`)

| Slug | Назначение |
|------|------------|
| `communication` | Мессенджеры, почта, звонки |
| `productivity` | Календари, контакты, совместная работа |
| `hr` | Кадровые и смежные коннекторы |
| `fleet` | TMS, телематика, compliance водителей |
| `accounting` | Учёт, ERP, счета |
| `ai` | AI / LLM инструменты |
| `automation` | Сценарии, интеграционные автоматизации |
| `storage` | Облачные хранилища файлов |
| `compliance` | Регуляторика, аудит, country-specific |

---

## Core integrations (`offer_kind = core_integration`)

Базовые ключи (расширение только через продукт + миграция констант):

| `offer_key` | Типичная категория витрины |
|-------------|----------------------------|
| `whatsapp` | communication |
| `telegram` | communication |
| `viber` | communication |
| `email` | communication |
| `gmail` | communication |
| `google_workspace` | productivity |
| `google_calendar` | productivity |
| `google_contacts` | productivity |
| `microsoft_teams` | communication |
| `outlook` | communication |
| `outlook_calendar` | productivity |
| `slack` | communication |
| `zoom` | communication |
| `meta_leads` | automation / communication |
| `google_drive` | storage |
| `dropbox` | storage |
| `onedrive` | storage |

Детали webhook/API для части из них — [`integration.md`](integration.md).

---

## Marketplace apps (`offer_kind = marketplace_app`)

На старте в константах зафиксированы только **примеры** slug (`*_generic`) для дизайна каталога и тестов. Реальные приложения (Sage, конкретный TMS, …) добавляются в каталог по мере контрактов с провайдерами.

---

## Связь с продуктовыми модулями (ADR-004)

Ключи **`recruitment`**, **`hr`**, **`fleet`**, **`services`**, **`finance`** относятся к **business modules**, не к `offer_key`. В `company_integration_enablements.usage_json` можно ссылаться на них (например `{"modules": ["recruitment"]}`), чтобы выразить «интеграция используется в этом модуле».

---

## История

- 2026-05: первичная фиксация slug, категорий и разделение core vs marketplace app.
