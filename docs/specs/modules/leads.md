# Module: Leads

## Назначение
Единая точка приёма маркетинговых лидов (Meta/Facebook Ads и другие источники) с автоматической конверсией в кандидатов HostFlow. Модуль отвечает за хранение исходного payload, нормализацию данных, дедупликацию и запуск пайплайна создания кандидата.

---

## Сущности и таблицы

- **leads** — основная таблица с лидами (tenant_scoped). Ключевые поля:
  - `id` (UUID, строка 36) — идентификатор лида;
  - `tenant_id` — владелец данных;
  - `company_id` — компания, от имени которой пришёл лид (определяется по вакансии или хинтам);
  - `vacancy_id` — связанная вакансия, если определена автоматически;
  - `source` — источник (`'meta'`, `'tiktok'`, ...), по умолчанию `'meta'`;
  - `ad_id` — идентификатор объявления в Meta для быстрой стыковки с вакансиями;
  - `payload` — исходный JSON от источника (JSON/JSONB);
  - `normalized` — нормализованные поля (email, phone, vacancy_hint и т.д.);
  - `status` — `new | processed | duplicated | failed | needs_routing`;
  - `candidate_id` — созданный или найденный кандидат;
  - `error` — текстовое описание проблемы (для `failed/needs_routing`);
  - `last_routed_at` — время последней попытки маршрутизации (для SLA мониторинга).

- **meta_ads_map** — справочник соответствий объявлений Meta ↔ вакансия. Поддерживает CRUD из админки:
  - `ad_id` (PK);
  - `tenant_id` — владелец соответствия;
  - `vacancy_id` — целевая вакансия;
  - `note`, `created_at` — служебная информация.

- **meta_lead_credentials** — защищённое хранилище подключений Meta:
  - `id` (UUID, PK);
  - `tenant_id` — владелец данных;
  - `label` — произвольное имя подключения для UI;
  - `encrypted_secret` — зашифрованный `META_WEBHOOK_SECRET`;
  - `access_token`, `ad_account_id`, `page_id` — зашифрованные поля с учётными данными;
  - `status` — `active | disabled | rotation_pending`;
  - `last_verified_at`, `last_rotation_at` — аудита подключения;
  - `created_at`, `updated_at`.

- **meta_lead_settings** — настройки маршрутизации и SLA:
  - `tenant_id` (PK);
  - `default_company_id` — fallback компания, если маппинг не найден;
  - `auto_create_enabled` — флаг автоcоздания кандидатов (Off → лид уходит в `needs_routing`);
  - `fallback_recruiter_id` — рекрутер по умолчанию;
  - `reroute_after_hours` — порог для SLA уведомлений;
  - `mask_pii_in_logs` — флаг маскировки email/phone в UI;
  - `webhook_url` — ожидаемый URL вебхука;
  - `webhook_verify_token` — verify token для handshake Meta (используется для резолва tenant);
  - `last_webhook_check_at`, `last_signature_status` — диагностика подключения.

- **lead_import_jobs** — таблица фоновых CSV‑импортов админки:
  - `id` (UUID, PK), `tenant_id`, `created_by`, `filename`;
  - `status` — `pending | running | completed | failed`;
  - счётчики `total_rows`, `processed_rows`, `success_rows`, `duplicate_rows`, `failed_rows`;
  - таймстемпы `started_at`/`finished_at`, JSON `error_report` с проблемными строками.

Обе таблицы создаются миграцией `202512010310_meta_leads_pipeline`. Для dev/test (SQLite) структура дублируется через `ensure_leads_schema`.

---

## Workspaces & Permissions

- **Tenant Admin Console**: раздел “LeadHub” содержит настройки интеграций, таблицу соответствий `meta_ads_map`, очередь `needs_routing` и инструменты ретрая. Доступ — `administrator`/`owner` (полный доступ) и `supervisor` (read-only: просмотр настроек, credential'ов, маппинга и import jobs).
- **Supervisor Dashboard**: отдельный вид списка лидов со статусами `needs_routing` и SLA‑нарушениями. Супервизор может распределять лиды вручную, если они не прошли маппинг. Рекрутеры не видят и не обрабатывают эту очередь.
- **Recruiter Workspace**: отображает только лиды в статусах `new`/`processed`/`duplicated` и уведомления о новых назначениях. Нет прав на изменение глобальных настроек и маршрутизацию лидов.
- **CSV Import**: POST `/api/v1/settings/leads/import` (CSV) инициирует фоновый джоб `lead_import_jobs`. Идемпотентность по email/phone (sha256), статусы `pending/running/completed/failed`, прогресс доступен через GET `/api/v1/settings/leads/import/{job_id}`. Стартовать импорт могут только `administrator`/`owner`; `supervisor` имеет read-only доступ к списку и деталям задач. Уведомляется инициатор, вебхуки `lead.received`/`lead.failed` отправляются при успешных/проблемных строках.
- Все операции проверяют RLS по `tenant_id` и дополнительно ACL по роли.

---

## Event Lifecycle

Sequence диаграмма (логический порядок):

1. `received` — лид поступил (webhook, CSV, API). Запись создаётся в `leads` со статусом `new`.
2. `needs_routing` — не удалось назначить вакансию/рекрутера (нет маппинга, отключён auto-create). Лид попадает в очередь супервизора.
3. `assigned` — назначен рекрутер и (опционально) вакансия. Создаётся уведомление `lead.assigned`.
4. `contacted` — рекрутер установил контакт и обновил статус.
5. `converted` — кандидат создан/обновлён и переведён в пайплайн.
6. `rejected` — лид отвергнут (дубликат, спам, некорректные данные).

Каждый переход фиксируется событием в `lead_events` с `event_type`, `payload`, `actor_id`. Используется для наблюдаемости и webhooks.

> Важно: рекрутеры не могут переводить лид из `needs_routing` напрямую в `assigned` — только `administrator`/`supervisor`.

---

## API

- `POST /api/v1/leads/meta` — webhook для Meta/Facebook Ads. Требует заголовок `X-Tenant-Id`; при наличии `META_WEBHOOK_SECRET` проверяет подпись `X-Hub-Signature-256`.
- `GET /api/v1/leads/meta/webhook` — handshake Meta Facebook. Возвращает `hub.challenge` при валидном verify token.
- `POST /api/v1/leads/meta/webhook` — внешний приёмник Meta. Резолвит tenant по verify token или `page_id`, валидирует подпись `X-Hub-Signature-256`, обрабатывает payload идемпотентно.
- `POST /api/v1/admin/meta-leads/leads/retry` — bulk-перезапуск пайплайна для существующих лидов. Поддерживает фильтрацию по статусам/ID и повторно использует Graph‑обогащение. Только `administrator`/`owner`.
- Расширение для других источников планируется через дополнительные endpoints (`/api/v1/leads/<source>`).

### Intake resolution (Slice 2, signed)

Операционный слой intake (отдельно от стадий кандидата): **`POST /api/v1/leads/{id}/intake-decision`**, **`POST /api/v1/leads/{id}/confirm-vacancy`**, гейтинг **`POST /api/v1/leads/{id}/process`** через `manual_process_block_code` (стабильные коды в 422), тот же слой на **bulk/NBA**, **retry**, **CSV reimport** для повторной обработки существующей строки. Детали и smoke-чеклист: [lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md) §8.0.

### Call result (recruitment intake and B2B appeals)

Операторский лог результата звонка:

- `POST /api/v1/leads/{id}/call-result` — body `{ result, note?, next_contact_at?, bump_stage? }`
- `result`: `no_answer` | `answered` | `callback_requested` | `interested` | `not_interested` | `wrong_number` | `unavailable`
- `note` — свободный комментарий (перезвонить / что хотят / думают), до 2000 символов
- `next_contact_at` — дата/время следующего контакта (для перезвонить)
- Persistence: latest → `Lead.normalized.call_result_v1`; history → `Lead.normalized.call_results_v1` (append, max 50); блоки сохраняются при re-normalize
- Audit: `lead.call_result` — activity `call → outcome → note → actor → timestamp → next_contact_at`
- Recruitment: первое сохранение результата переводит intake lifecycle **new → in_progress** (`intake_resolution_v1`). CRM `stage` — только compatibility (`contacted`). «Не дозвонились» не является стадией лида.
- Convert несёт **всю** историю звонков + исходные `field_answers` в `candidate.extra.lead_continuity_v1` / `intake_answers_v1` и глушит повторный «Call candidate»
- Gate: lead RODO (`communication_call`), billing side-effects; terminal rejected client lead → 422
- Список: `GET /leads?intake_lifecycle=new|in_progress|needs_decision|pool|completed` — единственная проекция intake (`intake_resolution_v1`). Legacy `intake_lane` aliases принимаются.

UI: identity bar + answers table + `LeadIntakeCallStep` на intake workspace; карточка client lead (`ClientLeadDetailView`). Для services-tenant заголовок списка — «Обращения» (`app.leads.title_services`).

**Recruitment intake lifecycle (authority):** `LeadOut.intake_lifecycle` = `new | in_progress | converted | rejected | pool | duplicate_review`. Create candidate — терминальное решение (converted), не начало обработки.

### Lead-stage RODO (art. 14)

**Канон политики (ADR-033):** operational SoT — **OwnCompany** `extra.lead_lifecycle_email_v1`; optional client-company overlay + sparse Vacancy override; см. [lead-lifecycle-email-policy.md](../workflows/lead-lifecycle-email-policy.md). Tenant JSON ниже — preset / cutover.

Политика арендатора (preset) в **`Tenant.settings.lead_rodo_v1`**, поля в **`GET/PATCH /api/v1/settings/leads/settings`**:

- `lead_rodo_send_mode` — `manual` | `auto_on_lead_created` | `auto_on_first_action`
- `lead_rodo_channels` — по умолчанию `["email"]`
- `lead_rodo_template_id` — опционально, версия активного `rodo_clause`

Операторские endpoints:

- `POST /api/v1/leads/{id}/compliance/rodo/send`
- `POST /api/v1/leads/{id}/compliance/rodo/source-provided`
- `POST /api/v1/leads/bulk/compliance/rodo/retry` — bulk art.14 re-send (Pipeline; default failed; dry_run)

Состояние: `Lead.normalized.rodo` (`sent`, `source_provided`, `pending_channel`, `failed`). Ingest hook после создания лида — `apply_lead_rodo_on_ingest` в `process_normalized_lead`. Канон: [lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md) §8.0.1.

### Формат ответа
```json
{
  "lead_id": "uuid",
  "status": "processed",
  "vacancy_id": "uuid | null",
  "candidate_id": "uuid | null",
  "recruiter_id": "uuid | null",
  "error": "string | null"
}
```

---

## UI

- Страница `Leads` (`/leads`) в фронтенде отображает таблицу лидов с фильтром по статусу, ссылками на компании/вакансии и переходом в карточку кандидата. На **карточке лида** (`LeadDetailPage`): панель **Intake routing & decisions** (`LeadIntakeResolutionPanel`) — confirm vacancy + intake actions; кнопка Process и панель qualification используют общий **`manualProcessBlockHint`** (без скрытого второго Process).
- Доступна ролям с правом `leads.view` (администратор, супервайзер, рекрутер, viewer-readonly).
- Админка `Админка → Лиды` (`/admin/meta-leads`) предназначена для владельцев интеграции (права `admin.metaLeads`). Разделы:
  - **Подключение** — формы для ввода `META_WEBHOOK_SECRET`, access token, идентификаторов рекламных аккаунтов; статус вебхука, дата последней проверки подписи, кнопка «Перегенерировать секрет», подсказки по настройке Meta.
  - **Маппинг и fallback** — CRUD по `meta_ads_map`, поиск по `ad_id`/вакансии, настройка `default_company_id`, флаг `auto_create_enabled`, назначение рекрутёров по умолчанию, переключатель «Отключить автосоздание», **режим RODO для новых лидов** (`lead_rodo_send_mode`).
  - **Логи и маршрутизация** — список лидов (фильтры `failed`, `needs_routing`), кнопка «Маршрутизировать», ручное назначение вакансии/компании, перезапуск обработки, индикаторы SLA (лиды, висящие > `reroute_after_hours`).
- В логах UI по умолчанию скрывает PII (email/phone) согласно флагу `mask_pii_in_logs`. Администраторы могут раскрыть данные по требованию комплаенса.

---

## Пайплайн обработки Meta-лида

1. **Normalize** — `normalize_meta_payload` извлекает full_name, email, phone, vacancy hints, utm-метки и ad_id.
2. **Resolve vacancy** — поиск вакансии:
   - прямой `vacancy_id` в payload;
   - маппинг по `ad_id` через `meta_ads_map`;
   - fallback → статус `needs_routing`.
3. **Resolve company** — по найденной вакансии, либо по `company_id` из payload, либо первая компания арендатора.
4. **Store lead** — создаётся запись в `leads` со статусом `new`, внешний идентификатор сохраняется в `leads.external_id` (уникально по tenant/source).
4b. **Lead RODO (optional)** — по `lead_rodo_v1`: после sync custom fields на **новом** лиде — `apply_lead_rodo_on_ingest` (auto-send, `source_provided`, или `pending_channel`); см. § Lead-stage RODO.
5. **Deduplicate** — поиск кандидата по email/phone внутри `tenant_id` и компании. При совпадении статус `duplicated`.
6. **Create candidate** — если дубля нет, вызывается `create_candidate_full`:
   - `source='meta'`, `origin={'meta': normalized}`;
   - обязательное заполнение `company_id`, `vacancy_id`, контактов.
7. **Recruiter auto-assignment** — выполняется внутри `create_candidate_full` (least-load по vacancy pool → owner → supervisor/admin).
8. **Lead update** — статус `processed`, ссылка на кандидата; при ошибке `failed` с причиной.

---

## Статусы лида

| Статус | Описание |
|--------|----------|
| `new` | Лид сохранён, обработка началась |
| `processed` | Кандидат создан; ссылка `candidate_id` заполнена |
| `duplicated` | Найден существующий кандидат с тем же email/phone |
| `failed` | Обработка не удалась (например, отсутствуют контакты) |
| `needs_routing` | Не удалось однозначно определить вакансию; требуется ручная обработка |

---

## Кандидаты

- Модель `Candidate` расширена полями `source` (строка) и `origin` (JSON). Для лидов Meta `source='meta'`, а `origin['meta']` содержит нормализованный payload.
- В API кандидатов (`GET/POST /api/v1/candidates`) новые поля отдаются вместе с остальными данными.

---

## Безопасность и изоляция

- Весь поток привязан к `tenant_id` — без корректного заголовка `X-Tenant-Id` запрос отклоняется.
- Нормализация Meta-лидов сохраняет `preferred_contact`, `poland_stay_basis`, `poland_stay_basis_raw`, `in_poland` (по ответу формы, стране или при наличии основания пребывания) и `company_hints`. Значения для `type_of_residence_in_poland` и схожих полей приводятся к каноническим кодам (`visa_d`, `visa_c`, `karta_pobytu`, `eu_citizen`, `other`). Эти данные пробрасываются в `lead.normalized`, а при успешном создании кандидата кладутся в `candidate.extra` — карточка сразу показывает предпочитаемый канал связи и статус пребывания в Польше.
- Логика резолва компании теперь использует подсказки из формы (`company`/`company_name`, UTM-метки) перед fallback на `default_company_id`. Это предотвращает ситуацию, когда все лиды получают одну и ту же компанию по умолчанию.
- Подпись `X-Hub-Signature-256` проверяется, если настроен `META_WEBHOOK_SECRET`. Секреты и токены хранятся в `meta_lead_credentials` в зашифрованном виде (pgcrypto).
- JSON payload хранится как есть; персональные данные маскируются в UI и выгрузках по политикам комплаенса (см. `mask_pii_in_logs`).
- Доступ к админке `Админка → Лиды` ограничен ролями `administrator` и `supervisor`; все операции логируются в `audit_log`.
- CLI `scripts/retry_meta_leads.py` даёт быстрый способ прогнать ретрай из консоли (нужен активный Python env и переменные окружения приложения).

---

## Тесты и валидация

- `backend/tests/api/test_lead_intake_decision.py` — intake-decision, Process gating, bulk/CSV alignment со stable codes.
- `hostflow-frontend/src/utils/__tests__/intakeResolution.test.ts`, `hostflow-frontend/src/components/leads/__tests__/LeadQualificationSuggestionPanel.intake.test.tsx` — клиентский gating (без e2e).
- `backend/tests/api/test_leads_meta.py`
  - создание кандидата при валидном payload;
  - обработка дублей.
- `backend/tests/api/admin/test_meta_leads.py`
  - CRUD настроек и credential’ов;
  - проверка ручной маршрутизации и флагов `auto_create_enabled`.
- Дополнительно рекомендуется покрыть сценарии ошибок (`failed`, `needs_routing`), валидацию подписи вебхука и SLA-триггеры.

---

## Notifications

- `lead.created` → уведомление рекрутеру/супервизору по назначенной вакансии или fallback‑рекрутеру.
- `lead.needs_routing` → уведомление админу и супервизору (email, UI, опционально Slack). Рекрутеры уведомление не получают.
- `lead.routed` → подтверждение назначенному рекрутеру и инициатору ручной маршрутизации.
- Уведомления наследуют язык пользователя; тексты находятся в i18n ресурсах (`en` источник).
- Дополнительные события:
  - `lead.processed` — приходит рекрутеру и его супервизору, содержит ссылки на кандидата и вакансию.
  - `lead.failed` — уведомление администраторам/супервизорам при невозможности обработки вебхука (отсутствие контактов и т.д.).
  - `candidate.created` — рекрутеру и его супервизору сразу после успешного создания карточки кандидата.
- Все уведомления записываются в `user_notifications` и доступны через `GET /api/v1/notifications` (по умолчанию только непрочитанные).
- `POST /api/v1/notifications/read` помечает конкретные уведомления (`ids`) или весь список (`mark_all=true`).
- UI раздел «Уведомления» показывает список, позволяет фильтровать непрочитанные и очищать журнал.

---

### Webhooks for External Systems

| Поле | Значение |
|------|----------|
| Endpoint | `POST https://<tenant-subdomain>/api/v1/settings/webhooks/leads` |
| События | `lead.received`, `lead.assigned`, `lead.needs_routing`, `lead.converted`, `lead.failed`, `lead.rejected` |
| Заголовки | `X-HostFlow-Signature` (HMAC SHA256), `X-Event-Id`, `X-HostFlow-Tenant` |
| Idempotency | Клиент обязан хранить `event_id`; HostFlow повторяет попытки 3 раза (15s / 60s / 300s) |
| Подпись | `signature = base64(hmac_sha256(secret, raw_body))` |
| Retry policy | Повтор до 5xx или timeout; 4xx не ретраится |
| Security | Секрет хранится в `meta_lead_settings` (зашифрованный), доступен только администраторам |

Payload пример:

```json
{
  "event_id": "uuid",
  "event_type": "lead.converted",
  "tenant_id": "uuid",
  "lead_id": "uuid",
  "candidate_id": "uuid",
  "status": "converted",
  "occurred_at": "2025-01-15T12:00:00Z",
  "payload": {
    "source": "meta",
    "vacancy_id": "uuid"
  }
}
```

> Клиент обязан отвечать `200 OK` в течение 5 секунд. Иначе событие будет повторено с тем же `event_id`.

---

## Bulk Import (CSV)

- Endpoint `POST /api/v1/settings/leads/import` принимает CSV (UTF-8, delimiter `,`).
- Обязательные колонки: `first_name`, `last_name`, `phone` **или** `email` (одна из них должна быть заполнена), `source`.
- Опциональные колонки: `vacancy_hint`, `company_hint`, `tags`, `utm_campaign`, `utm_content`, `language`, `notes`.
- Коды языка соответствуют ISO 639-1 (например, `en`, `pl`, `ru`); используется для первичной локализации кандидата.
- Поддерживаемые кодировки: `UTF-8` (default) и `Windows-1250` (авто-конвертация).
- Загруженный файл валидируется асинхронно. Результат импортного job доступен в Tenant Admin Console (успехи/ошибки) через `GET /api/v1/settings/leads/import` и `GET /api/v1/settings/leads/import/{job_id}`.
- Каждая строка создаёт запись в `leads` со статусом `new` и пометкой `import_batch_id`.
- Merge-стратегия: поиск совпадений по `phone` (нормализуется) или `email` в пределах tenant; при совпадении лид помечается как `duplicated` и связывается с существующим `candidate_id` (если есть).
- ACL: только `administrator`/`owner` могут запускать импорт; `supervisor` имеет read-only доступ к статусу импортов; рекрутеры видят итоговые лиды через обычный список.
- Ошибки валидации (например, отсутствует контакт) отправляются инициатору импорта уведомлением и логируются в `audit_log`.

---

## Дальнейшие шаги

- UI для просмотра и ручной маршрутизации лидов (`leads list`, `lead detail`).
- CRUD/админка для `meta_ads_map` и credential’ов — реализовано в `Админка → Лиды`.
- Поддержка дополнительных источников (TikTok, Website) и унифицированный сторож `lead_mapping_rules`.
- Интеграция SLA сигналов с уведомлениями (email/Slack) для лидов, требующих внимания.
