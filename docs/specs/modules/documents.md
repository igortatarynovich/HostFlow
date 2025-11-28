# Module: Documents

## Purpose
Единый модуль для хранения, проверки и сопровождения документов кандидатов и работодателей, включая процессные документы (виза, разрешение на работу, карта pobytu и т.п.). Модуль обеспечивает:
- формирование чек-листов по шаблонам,
- контроль сроков и напоминания,
- отслеживание многошаговых workflow,
- мульти-тенантную изоляцию и связь с кандидатами/компаниями.

### Связанные спецификации
- Контракт workflow — `documents_workflow_contract.md`.
- Матрица напоминаний — `../workflows/reminders_matrix.md`.
- Каталог типов документов — `../db/doc_types_catalog.md`.
- Definition of Done — `../tasks/documents_dod.md`.

## Core Entities

### documents
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `tenant_id` | UUID | Ключ для RLS |
| `candidate_id` | UUID | Привязка к кандидату (обязательно) |
| `company_id` | UUID, nullable | Работодатель, предоставивший документ |
| `kind` | enum(`driver`,`employer`,`process`) | Категория документа и секция в UI |
| `doc_type` | text | Машинное имя документа |
| `custom_name` | text, nullable | Используется для `doc_type = 'other'` |
| `status` | enum(`missing`,`requested`,`in_progress`,`received`,`approved`,`rejected`,`expired`) | Унифицированный жизненный цикл |
| `issue_date` | date, nullable | Дата выдачи |
| `expire_date` | date, nullable | Дата истечения |
| `ordered_at` | date, nullable | Дата, когда документ был заказан/запрошен |
| `valid_from` | date, nullable | Плановая дата, с которой документ должен начать действовать |
| `remind_days_before` | smallint, default 30 | За сколько дней до истечения отправлять напоминание |
| `owner_id` | UUID, nullable | Ответственный рекрутер/менеджер |
| `requested_from` | enum(`driver`,`employer`,`agency`) | Кто должен предоставить документ |
| `process_type` | enum(`none`,`work_permit`,`visa`,`residence_card`,`tachograph_card`,`driver_license_exchange`,`swiadectwo_kierowcy`,`other`) | Для процессных документов выбирается пресет workflow |
| `workflow` | jsonb | Текущее состояние процесса и список шагов (`steps[*].code/title/completed_at/due_at/ordered_at`, `current_step`, `notes`) |
| `files` | jsonb[] | Метаданные загруженных файлов (name/url/mime/size/...), последняя запись — активная версия |
| `meta` | jsonb | Дополнительные атрибуты (номер, страна, issuer, примечания) |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | Аудит и софт-удаление |

> Поля `type`, `issued_at`, `expires_at`, `extra`, `number`, `filename`, `path` и старые статусы сохраняются для обратной совместимости, но считаются устаревшими. Вся новая логика должна использовать `doc_type`, `issue_date/expire_date`, `status`, `workflow` и `meta`.

### document_templates
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `tenant_id` | UUID | RLS |
| `code` | text | Уникальный код (например `driver_ce`, `warehouse`) |
| `name` | text | Отображаемое имя |
| `documents` | jsonb | Массив элементов `{ "doc_type": "...", "kind": "...", "requested_from": "...", "process_type": "...", "meta": { ... } }` |
| `is_active` | bool | Управление доступностью шаблона |
| `created_by` | UUID, nullable | Автор |
| `created_at`, `updated_at` | timestamptz | Аудит |

#### Vacancy-driven bundles
- Каждая вакансия может ссылаться на шаблон документов (`vacancy.required_documents_template_id`).
- При назначении кандидата на вакансию UI предлагает применить связанный шаблон; обязательные документы подсвечиваются.
- Шаблон хранит флаг `is_required` на уровне элемента, что отображается в чек-листе.
- При смене вакансии система сравнивает ранее применённые шаблоны и предлагает merge (уникальные документы добавляются в чек-лист).
- Tenant Admin Console поддерживает конфиг `vacancy → template` в разделе Settings → Documents.

> Маппинг вакансий и шаблонов используется при импорте лидов: при `vacancy_hint` автоматически подставляется нужный шаблон.

### Reminder (shared module)
Используется для дедлайнов по `expire_date` и промежуточных шагов workflow (`workflow.steps[*].due_at`).

## Document Types & Categories

Категория фиксируется колонкой `kind` и влияет на группировку, фильтры и отчёты.

### Driver (`kind = driver`)
- `identity_document` (паспорт или ID)
- `driver_license`
- `qualification_code95`
- `medical_certificate`
- `criminal_record`
- `photo`
- `bank_account_confirmation`
- `pesel` — всегда включается, даже если не указан в шаблоне
- `other`

### Employer (`kind = employer`)
- `contract`
- `assignment`
- `insurance`
- `bhp`
- `accommodation`
- `other`

### Process (`kind = process`)
- `work_permit`
- `visa`
- `residence_card`
- `swiadectwo_kierowcy`
- `tachograph_card`
- `driver_license_exchange`
- `other`

> Новые doc_type можно добавлять миграциями, но суммарное количество должно оставаться в диапазоне 15–18, чтобы избежать дублирования. Мета-информация (`meta`) используется для уточнения (например, тип визы, серия карты побиту).
> Если для типа документа нет `meta_schema`, UI использует плоский JSON-редактор, чтобы можно было заполнить произвольные пары ключ/значение.

### Canonical doc_type Catalog

| `doc_type`              | Aliases (legacy)                    | `kind`    | `process_type`        | Default Expiry (months) | Notes |
|-------------------------|-------------------------------------|-----------|-----------------------|-------------------------|-------|
| `identity_document`     | `passport`, `id_card`, `national_id`| driver    | none                  | 120                     | Требует серию/номер в `meta`. |
| `driver_license`        | `prawo_jazdy`                       | driver    | none                  | 60                      | Категория хранится в `meta.category`. |
| `qualification_code95`  | `code95`, `code_95`                 | driver    | none                  | 60                      | Проверяется дата повторной аттестации. |
| `medical_certificate`   | `medical`, `badania_lekarskie`      | driver    | none                  | 12                      | `meta.clinic` обязательно. |
| `criminal_record`       | `police_clearance`                  | driver    | none                  | 12                      | Требует страну выдачи. |
| `photo`                 | `photo_id`                          | driver    | none                  | 0 (no expiry)           | Хранится как файл без срока. |
| `bank_account_confirmation` | `bank_account_doc`            | driver    | none                  | 0                       | Номер счета в `meta.iban`. |
| `pesel`                 | `pesel_confirm`                     | driver    | none                  | 0                       | Обязателен всегда. |
| `contract`              | `employment_contract`               | employer  | none                  | 0 (renew per contract)  | Версия договора хранится в шаблонах. |
| `assignment`            | `work_assignment`, `oswiadczenie`   | employer  | none                  | 6                       | Используется для командировок. |
| `insurance`             | `insurance_a1`, `insurance_confirmation` | employer | none              | 12                      | Полис и компания в `meta`. |
| `bhp`                   | `bhp_instruction`                   | employer  | none                  | 12                      | Требует `meta.trainer`. |
| `accommodation`         | `accommodation_declaration`         | employer  | none                  | 12                      | Адрес проживания в `meta.address`. |
| `work_permit`           | `zezwolenie_A`                      | process   | work_permit           | 12                      | Workflow обязательный. |
| `visa`                  | `visa_D`, `entry_permit_or_visa`    | process   | visa                  | 6                       | Контролируется по `expire_date`. |
| `residence_card`        | `karta_pobytu`                      | process   | residence_card        | 24                      | Содержит `meta.card_number`. |
| `swiadectwo_kierowcy`   | `driver_attestation`                | process   | swiadectwo_kierowcy   | 24                      | Workflow: ordered → issued → delivered. |
| `tachograph_card`       | `tachograph_exchange`               | process   | tachograph_card       | 60                      | Хранит `meta.tachograph_id`. |
| `driver_license_exchange` | `prawo_jazdy_exchange`           | process   | driver_license_exchange | 24                    | Шаги как в пресете. |
| `other`                 | —                                   | зависит   | other                 | 0                       | Требует `custom_name` и `meta.description`. |

- Любые новые `doc_type` добавляются через миграцию и обновление таблицы выше.
- Политика `other`: обязательны `custom_name` (до 120 символов) и `meta.description`; UI отображает их отдельным блоком и всегда помечает как «Custom».

## Status Flow

```
missing → requested → in_progress → submitted → received → delivered → approved → completed
```

- Старт процессного документа (кнопка «Заказать», шаг `ordered`/`applied`) переводит статус из `missing` в `requested`.
- Когда выполнен первый этап workflow или заполнены поля, статус становится `in_progress`. Завершение промежуточного шага (`submitted`, `interview`, `fingerprints`) переводит в `submitted`.
- При наличии файлов статус автоматически поднимается минимум до `received`.
- Завершение шагов `delivered`/`received` поднимает статус до `delivered`, шаг `approved` — до `approved`. Полное закрытие всех шагов без явных финальных кодов отмечается как `completed`.
- Если срок шага или документа просрочен, статус становится `overdue`. При истечении `expire_date` — `expired`. `rejected` устанавливается вручную и имеет приоритет.
- Старые статусы мигрируют так: `planned` → `missing`, `pending_validation` → `in_progress`, `verified` → `approved`, `invalid` → `rejected`.

## Workflow JSON

Пример структуры для процессного документа:

```json
{
  "steps": [
    {"code": "ordered", "title": "Ordered", "completed_at": "2025-01-10"},
    {"code": "submitted", "title": "Submitted", "completed_at": "2025-01-18"},
    {"code": "approved", "title": "Approved", "completed_at": null, "due_at": "2025-02-01"},
    {"code": "delivered", "title": "Delivered", "completed_at": null}
  ],
  "current_step": "approved",
  "notes": "Awaiting response from voivodeship office"
}
```

#### Workflow Schema

```json
{
  "steps": [
    {
      "code": "ordered",
      "title": "Ordered",
      "due_at": "2025-01-15T12:00:00Z",
      "due_in_hours": 72,
      "completed_at": "2025-01-10T09:00:00Z",
      "ordered_at": "2025-01-08T12:00:00Z",
      "notes": "Optional free-text",
      "actor_id": "uuid",
      "reminder_id": "uuid"
    }
  ],
  "current_step": "ordered",
  "notes": "Step-level notes"
}
```

- Обязательные поля шага: `code`, `title`.
- Допустимые поля: `due_at`, `due_in_hours`, `completed_at`, `ordered_at`, `notes`, `actor_id`, `reminder_id`.
- `code` (`snake_case`) берётся из справочника (см. базовые пресеты ниже); кастомные значения разрешены только с префиксом `custom_`.
- `due_in_hours` вычисляет `due_at` при создании; при PATCH обновляет напоминания.
- Валидаторы: `due_at` ≥ `now`, `completed_at` ≥ `ordered_at`, `actor_id` принадлежит текущему tenant.

Базовые пресеты шагов:
- `visa`: `applied`, `interview`, `approved`, `received`
- `work_permit`: `ordered`, `submitted`, `approved`, `delivered`
- `residence_card`: `applied`, `fingerprints`, `approved`, `received`
- `tachograph_card`: `applied`, `received`
- `driver_license_exchange`: `submitted`, `approved`, `received`
- `swiadectwo_kierowcy`: `ordered_at`, `issued_at`, `delivered_at`

UI позволяет редактировать даты шагов напрямую (например, `ordered_at`, `submitted_at`, `fingerprints_at`) — значения сохраняются в `workflow.steps[*].completed_at` или `workflow.steps[*].ordered_at` и используются для контроля сроков.

Право изменять `due_at`/`due_in_hours`: `administrator`, `supervisor`, а также `recruiter`, если он владелец документа (`owner_id`). Любые изменения триггерят пересоздание напоминаний и запись в `audit_log`.

При заполнении первого шага документ становится `in_progress`. Заполнение финального шага — `received` (или `approved`, если требуется валидация работодателем). Workflow меняется через PATCH API либо сервисный слой и хранится в `meta.workflow_history` при необходимости аудита.

#### Автопродвижение статуса (`compute_auto_status`)

Полная таблица комбинаций находится в `documents_workflow_contract.md`. Кратко:
- Если ни один шаг не выполнен → `requested`.
- Промежуточные шаги (`ordered`, `submitted`, `approved`, `delivered`) задают статус `in_progress` / `submitted` / `approved` / `delivered`.
- Просроченные шаги (`due_at < now` без `completed_at`) переводят документ в статус `overdue`.
- Когда все шаги закрыты → `completed`.
- Отдельно контролируется `expire_date` (`expired`), который имеет приоритет над `completed`.

## Templates & Checklist Generation

- Шаблон выбирается в UI (dropdown “Select template”) и фиксируется в документном модуле. Если у кандидата есть активная вакансия, привязанная к шаблону (`vacancy.required_documents_template_id`), UI автоподставляет его и помечает обязательные элементы.
- Применение шаблона:
  1. Активные документы кандидата синхронизируются с шаблоном (PESEL добавляется всегда).
  2. Для отсутствующих записей создаются документы со статусом `missing`.
  3. Custom-документы (`doc_type = other`) не удаляются, но выводятся отдельным блоком.
- Пользователь может добавить документ вручную (кнопка «Add custom document»): выбирается `kind`, `requested_from`, вводится `custom_name`, создаётся запись с `doc_type='other'`.
- Базовые шаблоны (`driver_ce`, `warehouse` и др.) публикует админ тенанта через консоль; они могут редактироваться и версионироваться без сидов.
- Поля `documents[*].title` и подсказки поддерживают локализации (`en` — источник, `ru`/`pl` — переводы), UI подставляет язык пользователя или дефолтный английский.

## Reminders & Automation

- Фоновые задачи ежедневно:
  - обновляют статус `expired`,
  - создают/обновляют напоминания за `remind_days_before` дней до `expire_date`,
  - проверяют `workflow.steps[*].due_at`/`ordered_at` и запускают напоминания/таски на ответственных,
  - эскалируют просрочки процессных документов супервизору и администратору tenant.
- SLA напоминаний: единая матрица T-24/T-4/T+0/T+N (повтор каждые 24 часа) для всех типов документов, `schedule_key="document_expiry:<offset>"`, а локализуемые шаблоны для каналов (in-app/email/webhook) отдаются через `channel_templates`; повторное расписание переиспользует существующие записи и исключает дубли.
- Изменение документа пересчитывает напоминания (`schedule_document_expiry_reminders`).
- Сводка кандидата отображает счётчики по категориям и статусам (например, `Driver 5/9`, `Process 1/2`).

## API Expectations

- `GET /api/v1/documents?candidate_id=...` возвращает расширенную схему (добавлены `ordered_at`, `valid_from`, `has_files`, `readiness_state`, `status_rank` помимо `kind`, `doc_type`, `custom_name`, `process_type`, `workflow`, `meta`); поддерживает фильтр `ordered=true|false` для быстрого поиска заказанных, но ещё не полученных документов.
  - См. `docs/specs/frontend/documents_readiness.md` для UI-деталей (колонки, сортировки, фильтры).
  - `readiness_state` принимает значения `pending`, `requested`, `ordered`, `in_progress`, `awaiting_review`, `ready`, `problem`.
- `POST /api/v1/documents` — создание документа; при `doc_type='other'` обязательны `custom_name` и `kind`.
- `PATCH /api/v1/documents/{id}` — обновление статуса, workflow, дат и файлов.
- `POST /api/v1/candidates/{id}/documents/apply-template` — накладывает шаблон на кандидата и возвращает обновлённый чек-лист.
- Старые значения статусов допускаются, но нормализуются к новой шкале на сервисном уровне.

## Integrations & Dependencies

- **Candidates**: прогресс документов влияет на pipeline и eligibility.
- **Companies**: `company_id` заполняется для документов, предоставляемых работодателем.
- **Vacancies**: vacancy может подсказать рекомендуемый шаблон, но выбор делается внутри модуля документов.
- **Reminders / Scheduler**: используют `remind_days_before`, `expire_date` и workflow.
- **RLS**: каждая операция устанавливает `current_setting('app.tenant_id')`; политики охватывают `documents` и `document_templates`.

## Testing Guidelines

- Юнит-тесты на применение шаблонов и авто-добавление PESEL.
- Интеграционные тесты workflow: заполнение шагов меняет статус и ставит напоминания.
- Проверка фильтров и счётчиков по категориям и статусам.
- Миграционные тесты: данные из старой схемы корректно мапятся в новые поля.
- RLS: операции выполняются только внутри текущего tenant.

## Migration Notes

- Alembic-миграция добавляет новые enum-типы и колонки к `documents`, создаёт таблицу `document_templates`.
- Данные переносятся: `type` → `doc_type`, `issued_at/expires_at` → `issue_date/expire_date`, `extra/meta_json` → `meta`.
- Статусы мапятся в новую шкалу; `kind` вычисляется по `doc_type` (см. таблицу категорий).
- Каскадные обновления: триггеры и вьюхи, завязанные на старые статусы/колонки, адаптируются.
- Базовые шаблоны и справочник doc_type управляются через Tenant Admin Console либо сервисные скрипты; требуется лог аудит для всех изменений.

## UI Guidelines

- Документы группируются по `kind`; внутри группы сортировка по статусу и дате истечения.
- В заголовке списка — селектор шаблона и счётчики (`missing`, `in_progress`, `expired`).
- Процессные документы показывают прогресс-бар на основе `workflow.steps`.
- Кнопка «Add custom document» создаёт запись `other` и открывает форму указания имени/категории.
- PESEL отображается как обязательный элемент и не может быть удалён.

---

## Definition of Done
- Юнит-тесты: `owner_summary`, `rules_engine`, `workflow_reminders`, `i18n` для ключевых уведомлений.
- Интеграционные тесты API: `POST /documents`, `PATCH /documents/{id}`, `apply-template`, `compute_auto_status`.
- Проверка i18n: отсутствующий ключ на `pl` корректно фолбэкится на `en`.
- Автотест `owner_summary` учитывает просрочки по шагам и выводит температуру документа.
- Локализация шаблонов уведомлений проходит проверку на наличие всех placeholders.
- Миграции и схема синхронизированы (Alembic + `schema_documents.sql`).

### Acceptance Checklist
- `POST /documents` валидирует `doc_type/kind/requested_from/process_type`, для `other` требует `custom_name`.
- `workflow.steps[].code/title/due_in_hours` создают напоминания; при `completed_at` напоминания отменяются.
- `PATCH /documents` со сдвигом `due_at` пересоздаёт напоминания без дублей.
- `compute_auto_status` соответствует таблице из раздела «Автопродвижение статуса».
- При отсутствии ключа в `pl` используется английский текст (без пустых строк).
- Общий `owner_summary` считает просрочки по шагам и агрегированные статусы.
- Лиды в статусе `needs_routing` видны только в админском контуре, уведомления соответствуют RBAC.

---

Эта спецификация описывает целевое устройство модуля документов после реструктуризации. Все новые изменения и миграции должны соответствовать указанным моделям и потокам.
