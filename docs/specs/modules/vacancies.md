# Module: Vacancies

## Назначение
Управление вакансиями клиентов, их связью с компаниями и кандидатами.  
Модуль определяет структуру вакансий, правила публикации, статусы активности и фильтрацию.

---

## Сущности
- **Vacancy** (`id`, `tenant_id`, `company_id`, `title`, `description`, `employment_type`, `is_open`, `is_active`)
- **VacancyCandidateLink** (`vacancy_id`, `candidate_id`, `status`, `notes`)
- **VacancyRecruiter** (`vacancy_id`, `user_id`, `tenant_id`, `weight`, `is_active`, `last_assigned_at`)
- **Company** (FK на работодателя)
- **Candidate** (FK на водителя/соискателя)

---

## Логика
- `employment_type`: `'full_time' | 'part_time' | 'b2b'` (enum, общий для backend и frontend).  
- Вакансия активна (`is_active=true`) → разрешено назначать кандидатов.  
- Вакансия закрыта (`is_open=false`) → доступна только для чтения.  
- При деактивации компании все её вакансии автоматически закрываются.  
- При повторной активации компании вакансии остаются закрытыми до ручного открытия.  

---

## API
| Метод | URL | Назначение | Доступ |
|--------|-----|-------------|--------|
| `GET /api/v1/vacancies` | Список вакансий с фильтрами | ✅ |
| `GET /api/v1/vacancies/{id}` | Детали вакансии | ✅ |
| `POST /api/v1/vacancies` | Создание вакансии | ✅ (Owner, Manager) |
| `PATCH /api/v1/vacancies/{id}` | Обновление данных | ✅ (Owner, Manager) |
| `PATCH /api/v1/vacancies/{id}/toggle-active` | Переключение статуса активности | ✅ (Owner) |
| `GET /api/v1/vacancies?company_id={id}` | Получить вакансии конкретной компании | ✅ |

Фильтры:
- `?company_id=...`
- `?is_active=true`
- `?employment_type=b2b`
- `?search=driver` (поиск по названию и описанию)
- `?status=archived` — выводит вакансии из архива (автоматически включает soft-delete пометки)

---

## UI
- **VacancyList** — таблица, аналогичная Candidates, с фильтрацией по статусу, компании, типу занятости.  
- **VacancyCard** — вкладки:
  - **Candidates** — список связанных кандидатов (канбан-счётчики + таблица).  
  - **Details** — поля вакансии, редактирование.  
- **VacancyForm** — форма создания/редактирования с валидацией enum и обязательного поля `title`.  
- Кнопка `Toggle Active` переключает `is_open` и `is_active` с подтверждением.  

---

## События
| Событие | Условие | Действие |
|----------|----------|----------|
| `vacancy.created` | Создана новая вакансия | Добавляется в список активных вакансий |
| `vacancy.updated` | Изменено описание или статус | Обновляется кеш и индексация |
| `vacancy.closed` | Вакансия закрыта вручную или через деактивацию компании | Все активные связи кандидатов архивируются |
| `vacancy.reopened` | Вакансия снова активна | Разрешено добавлять новых кандидатов |
| `vacancy.deleted` | (только Owner, soft-delete) | Вакансия скрывается из списков |

---

## Безопасность
- Все вакансии принадлежат конкретному `tenant_id`.  
- Любые запросы фильтруются политиками RLS.  
- Только `Owner` может переключать статус активности и удалять.  
- Роль `Manager` может редактировать описание, `Viewer` — только читать.  
- Вакансия не может быть создана без связанной компании (`company_id`).  
- Проверка `tenant_id` обязательна на всех уровнях (DB, Model, API).

---

## Связи
- **Company ↔ Vacancy** — связь один-ко-многим.  
- **Vacancy ↔ Candidate** — связь многие-ко-многим через `VacancyCandidateLink`.  
- **Vacancy ↔ Tenant** — все вакансии изолированы по tenant.  
- **Vacancy ↔ Reminder** — при закрытии вакансии активные напоминания снимаются.
- **Vacancy ↔ VacancyRecruiter** — список доступных рекрутёров с весами и историей назначения.

---

## Рекрутёры вакансии

- Таблица `vacancy_recruiters` хранит активных рекрутёров, допущенных к работе с вакансией.
- Поля:
  - `weight` — приоритет в алгоритме назначения (чем выше, тем чаще выбирается при равной загрузке).
  - `last_assigned_at` — временная метка последнего распределения (для round-robin).
  - `is_active` — позволяет временно выключить рекрутёра из пула без удаления записи.
- При закрытии или архивировании вакансии её активные записи не удаляются, но в алгоритме учитывается только `is_active=true`.

---

## Тестирование
- CRUD операций, фильтрации и RLS.  
- Проверка CHECK-constraint для `employment_type`.  
- Проверка `default='full_time'`.  
- Проверка каскада при деактивации компании.  
- Проверка ручного переключения `toggle-active`.  
- Проверка недопустимых операций (редактирование закрытой вакансии).  
- Тесты UI (RTL) на форму и поведение при разных ролях.  

---

## Mapping (DB ↔ Model ↔ API ↔ UI ↔ Tests)

| Уровень | Что описывает | Источник | Правила/валидация | Эндпоинты/операции | Тесты |
|----------|----------------|-----------|--------------------|--------------------|--------|
| **DB** | Таблица `vacancies` (`id`, `tenant_id`, `company_id`, `title`, `description`, `employment_type`, `is_open`, `is_active`) | `backend/alembic/versions/*_vacancy_*.py` | `tenant_id` обязателен; CHECK для `employment_type` ('full_time','part_time','b2b'); default `'full_time'` | `make mig-rev` → `make mig` | Проверка корректности миграции и rollback |
| **Model** | SQLAlchemy модель `Vacancy` | `backend/app/models/vacancy.py` | Типы полей, Enum `employment_type`; FK на `Company` | CRUD-операции в `backend/app/services/vacancies.py` | Unit-тесты сервисного слоя |
| **API Schemas** | Pydantic-схемы `VacancyCreate`, `VacancyUpdate`, `VacancyOut` | `backend/app/schemas/vacancy.py` | Обязательные поля: `title`, `employment_type`; Enum для `employment_type` | `/api/v1/vacancies*` | Тесты API: создание, обновление, фильтрация |
| **UI / Form** | Компоненты `VacancyForm`, `VacancyDetail` | `hostflow-frontend/src/pages/VacancyDetail.tsx` | Enum ('full_time','part_time','b2b'); обязательность title; disable если `is_open=false` | PATCH `/api/v1/vacancies/{id}` | RTL-тесты формы и поведения |
| **Business Rules** | Активная вакансия допускает линковку кандидатов | `docs/specs/modules/vacancies.md` | `is_open=true` → разрешено; иначе только чтение | `/api/v1/vacancies/{id}/toggle-active` | Проверка позитив/негатив сценариев |
| **RLS / Security** | Изоляция данных между tenant | Alembic и FastAPI policies | `tenant_id` enforced | Все `/api/v1/vacancies*` | Проверка tenant-изоляции и FK |

---


---

## Integration & Sync

Модуль **Vacancies** интегрируется с другими частями HostFlow и внешними системами для синхронизации вакансий и кандидатов.

### Внутренние интеграции
- **Companies:** все вакансии принадлежат компании; при изменении `company.is_active=false` вакансии закрываются автоматически.  
- **Candidates:** кандидаты могут быть привязаны к одной или нескольким вакансиям через `VacancyCandidateLink`.  
- **Reminders:** при длительной неактивности вакансии (более 30 дней) создаётся напоминание менеджеру проверить актуальность.  
- **Leads:** лиды могут автоматически связываться с вакансиями, если передан параметр `vacancy_id` при webhook-заявке.  
- **Documents:** используются для фильтрации кандидатов, подходящих для вакансии (по типу разрешения на работу, визе и т.д.).  

### Внешние интеграции
| Сервис | Назначение | Метод |
|---------|-------------|--------|
| **WorkHost API (партнёрские компании)** | Обмен активными вакансиями между агентствами | REST API `/sync/vacancies` |
| **CRM / ERP клиентов** | Импорт вакансий с корпоративных порталов | JSON webhook или CSV upload |
| **Job Boards (Jooble, OLX, Indeed)** | Публикация вакансий внешне | Пакетная выгрузка в формате XML/JSON |
| **Google Sheets / Meta Forms** | Сбор лидов с указанием вакансии | через `vacancy_id` в webhook payload |
| **Slack / Telegram Bots** | Оповещения о новых вакансиях или закрытии позиций | Webhook через Notification Engine |

### Поля для синхронизации
- `external_id` — идентификатор вакансии во внешней системе.  
- `source` — источник импорта (`crm`, `partner`, `manual`).  
- `synced_at` — дата последней синхронизации.  
- `is_published` — флаг публикации на внешних платформах.  
- `external_link` — ссылка на вакансию на внешнем сайте.

### Логика обновления
1. При импорте по `external_id` → обновить запись, если она существует.  
2. Если вакансии нет — создать новую и отметить `imported=true`.  
3. После успешного обновления создать событие `vacancy.synced`.  
4. Ошибки импорта записывать в `integration_logs` с контекстом (`source`, `payload`).  
5. При удалении вакансии во внешней системе → пометить `is_active=false` (soft-delete).

### AI Agent Notes
- Агент должен использовать `external_id` и `tenant_id` для синхронизации вакансий.  
- Все операции импорта должны быть идемпотентными.  
- Нельзя автоматически публиковать вакансию без флага `approved=true`.  
- При создании вакансии из внешнего источника необходимо проверить наличие `company_id`.  
- Агент должен логировать все операции синхронизации и обновления статусов в `integration_logs`.  
- Любое добавление новых источников интеграции требует обновления `integration.md` и `rules.md`.
