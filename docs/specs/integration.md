
# Integrations — HostFlow External Systems

Этот документ описывает все внешние интеграции и каналы обмена данными HostFlow. Здесь зафиксированы типы подключений, контракты webhook’ов, ключи API, обработчики и правила безопасности.

---

## 1. Advertising & Lead Intake

### Meta / Facebook Leads
- **Тип:** Webhook POST  
- **URL:** `/api/v1/leads/meta`
- **Формат:** JSON (raw payload Meta Graph API).  
- **Идентификация:** `X-Hub-Signature-256` + `X-Tenant-Id`. Подпись проверяется по секрету, хранимому в `meta_lead_credentials`.  
- **Админка:** `Админка → Лиды` позволяет:
  - указать/ротационировать `META_WEBHOOK_SECRET`, access token, `ad_account_id`, `page_id`;
  - видеть целевой URL вебхука, дату последней успешной подписи, статистику входящих событий;
  - управлять маппингом `ad_id → vacancy`, fallback-компанией, автоcозданием кандидатов;
  - просматривать лог лидов, reroute/assign вручную, следить за SLA (лиды без обработки > N часов).
- **Ретрай:** `POST /api/v1/admin/meta-leads/leads/retry` перезапускает пайплайн для существующих лидов (использует ту же нормализацию и Graph‑обогащение). Скрипт `scripts/retry_meta_leads.py` предоставляет CLI-обёртку для массового прогона.
- **Правила:**  
  - **POST** `/api/v1/leads/meta/webhook`: сначала тенант по `page_id` из события и строке `meta_lead_credentials` (владелец Page Access Token и app secret), иначе fallback на `webhook_verify_token` в query; при дубликате только verify token в `meta_lead_settings` приоритет у не‑legacy тенанта. Чтобы Poltrakt шёл в Focus, перенесите credentials на Focus и держите один владелец токена (см. `scripts/meta_poltrakt_to_focus_personnel.sql`).  
  - **Платформа (только API):** **superadmin** в bootstrap-тенанте (`11111111-…`) в UI/API по умолчанию видит и меняет Meta в контексте **Focus Personnel** (канонический UUID `FOCUS_PERSONNEL_TENANT_ID`). Это **не копирует** уже сохранённые строки в БД: чтобы перенести креды и verify token **с суперадмина на Focus**, один раз выполните SQL `scripts/migrate_superadmin_meta_connection_to_focus.sql` (бэкап перед запуском). Переменная `META_LEADS_OPERATIONAL_TENANT_ID` — другой UUID; `off` / `disable` / `none` / `false` / `0` отключают ремап. Обычные администраторы клиентских тенантов не затрагиваются.  
  - Идемпотентная обработка по `leadgen_id`/`event_id`.  
  - При отключённом `auto_create` лиды переходят в `needs_routing` и требуют ручного действия.  
  - Маскировка PII в UI включена по умолчанию; доступ к полным данным только у `administrator`.  
  - Ошибки и редкие события фиксируются в `integration_log` и `audit_log`.  
- **Мониторинг:** сохранение `last_webhook_check_at` и `last_signature_status` для health-дэшборда.

Подробная инструкция по настройке Meta → HostFlow доступна в `docs/specs/integrations/meta_leads_setup.md`.

### TikTok Ads
- **Тип:** Webhook POST  
- **URL:** `/api/v1/leads/webhook/tiktok`
- **Поддержка параметров:** `campaign_id`, `ad_name`, `form_name`.  
- **Валидация:** HMAC подпись, TTL ≤ 60 сек.  
- **Назначение:** автоматическая генерация лида, сохранение рекламных метаданных в `Lead.payload`.

### Website / Landing Forms
- **Тип:** Webhook или REST API.  
- **URL:** `/api/v1/leads/webhook/website`  
- **Описание:** принимает лиды с корпоративных лендингов или партнерских страниц.  
- **Требования:**  
  - Поля `name`, `phone`, `source="website"`.  
  - Идентификация по ключу tenant.  
  - Возможен ручной триггер через админку.

---

## 2. Communication Channels

### WhatsApp Business API
- **Провайдер:** 360Dialog / Twilio  
- **Назначение:** коммуникация с кандидатами и клиентами.  
- **Методы:**  
  - Исходящие сообщения через `/api/v1/messages/send`  
  - Входящие через `/api/v1/messages/incoming` (webhook).  
- **Формат:** JSON, idempotent event_id.  
- **Пример входящего:**  
  ```json
  {
    "event_id": "uuid",
    "from": "+48500111222",
    "text": "Добрый день, есть работа?",
    "tenant": "11111111-1111-1111-1111-111111111111"
  }
  ```
- **Особенности:**  
  - Автоматическая маршрутизация сообщений менеджеру кандидата.  
  - Автоответ при нерабочем времени.  
  - Все сообщения логируются в `message_log`.

### Email Gateway
- **Назначение:** отправка системных уведомлений (напоминания, отчёты, сбои).  
- **Интерфейс:** SMTP + REST API (`/api/v1/notifications/email`).  
- **Формат шаблонов:** Jinja2 (`backend/app/templates/email/`).  
- **Отправитель:** `noreply@hostflow.io`.  
- **Безопасность:** TLS, API key per tenant.  

---

## 3. External Systems & APIs

### Google Sheets / Drive
- **Назначение:** экспорт отчётов по кандидатам и вакансиям.  
- **Интеграция:** через MCP Server (`mcp-google-sheets`).  
- **Права:** OAuth 2.0, доступ на запись к выбранным таблицам tenant.  
- **Пример:** выгрузка `vacancies_active` раз в сутки.

### Slack / Discord Alerts
- **Назначение:** уведомления о событиях (`lead.created`, `document.expired`, `deployment.complete`).  
- **Механизм:** MCP сервер `slack-mcp-server`.  
- **Параметры:** канал, tenant_id, тип события.  
- **Формат:** markdown или plain text.

### Grafana / Prometheus
- **Назначение:** метрики и мониторинг системных компонентов.  
- **Метрики:** количество кандидатов, ошибок API, напоминаний, отклонённых лидов.  
- **Экспорт:** `/metrics` endpoint в backend, scrape interval 30 сек.  
- **Визуализация:** дашборды по tenant и общие тренды.

---

## 4. Authentication & API Keys

- Каждый tenant имеет собственный `api_key`, хранящийся в таблице `tenants`.
- Все внешние вызовы (webhook, интеграции) требуют заголовок:
  ```
  X-Tenant-Key: <api_key>
  ```
- Ключи выдаются только `Owner` через панель администратора.
- Ключи имеют TTL и могут быть отозваны.

---

## 5. Безопасность и аудит
- Все внешние запросы логируются в `integration_log` с `event_id`, временем, IP и статусом.
- Любая ошибка > 400 сохраняется с полным payload.
- Повторные события обрабатываются идемпотентно.
- Поддерживаются retry и DLQ (Dead Letter Queue) для отложенной доставки.
- Любая интеграция должна иметь тестовый sandbox-режим перед production.

---

## AI Agent Notes
- Этот документ описывает все внешние зависимости системы.  
- При работе с API агент должен проверять ключи, форматы данных и источники.  
- Любое новое подключение должно быть зарегистрировано здесь и отражено в `core.md` и `rules.md`.  
- В коде все интеграции должны реализовываться в отдельных сервисах под `backend/app/integrations/`.  
- Все webhook-и должны быть идемпотентными и безопасными (tenant-aware, без утечек данных).
