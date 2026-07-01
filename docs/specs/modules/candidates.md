# Module: Candidates

## Назначение
Единый источник истины по человеку (водителю): персональные данные, статусы, привязки к документам, вакансиям и клиентам.  
Модуль Candidates объединяет информацию о кандидате, его документах, опыте и текущем статусе в процессе найма.

---

## Ключевые сущности
- **Candidate** (`id`, `tenant_id`, `personal_data`, `contacts`, `experience_eu`, `licenses`, `created_by`, `manager_id`, `status`)
- **CandidateStatus** (`id`, `candidate_id`, `old_status`, `new_status`, `changed_at`, `changed_by`)
- **Relations:** `candidate ↔ documents`, `candidate ↔ vacancy`, `candidate ↔ company`

---

## Поля (минимум)
- ФИО, дата рождения, гражданство, номер телефона, язык общения  
- Документы: CE, Code 95, виза/карта побыта, тахокарта  
- Технические: `tenant_id`, `created_at`, `updated_at`, `is_active`, `manager_id`, `recruiter_id`, `source`, `origin`

---

## Статусы и логика
Используется канонический пайплайн из `core.md`.  
Переходы валидируются по правилам гражданства и статуса пребывания.  
Каждое изменение статуса фиксируется в `CandidateStatus.history`.  
Ручное изменение статуса допускается из любого этапа (включая финальные) через сервис `update_candidate_full`; запись отражается в `CandidateStageHistory`.
Некоторые статусы блокируют переходы при отсутствии документов (см. `rules.md`).
- Дополнительные этапы пайплайна:  
  - `no_answer` — «Не отвечает», фиксируется после шага «Новый» и относится к группе new.  
  - `declined` — «Отказался», финальный статус, отличающийся от `rejected` («Отклонён» работодателем).  
- Для статусов `declined` и `rejected` обязателен массив кодов причин (`status_reason`, JSON array):  
  - `declined`: `schedule`, `salary`, `location`, `trailer_type`, `night_driving`, `bonus_scheme`, `cab_overnight`, `company_reviews`.  
  - `rejected`: `eu_exp_lt_1y`, `eu_exp_lt_6m`, `awaiting_residence`, `language`, `no_visa`, `no_ce_experience`, `no_code95`, `no_chip`, `age`, `blacklist`, `wrong_phone`.  
  Эти коды используются в аналитике и фильтрации; API возвращает и принимает их как список строк.

---

## API (черновой контракт)
| Метод | URL | Назначение |
|--------|-----|-------------|
| `GET /api/v1/candidates?filters=...` | Получить список кандидатов (с учетом ACL) |
| `POST /api/v1/candidates` | Создать нового кандидата (admin/supervisor/recruiter) |
| `PATCH /api/v1/candidates/{id}` | Обновить данные в рамках ACL |
| `POST /api/v1/candidates/{id}/status` | Изменить статус (валидация правил) |
| `GET /api/v1/candidates/{id}/documents` | Получить документы кандидата |
| `POST /api/v1/candidates/{id}/documents` | Загрузить или обновить документ кандидата |
| `POST /api/v1/candidates/{id}/delete-request` | Создать запрос на удаление (рекрутер) |
| `GET /api/v1/delete-requests` | Очередь запросов на удаление | ✅ (Administrator, Supervisor своих рекрутеров) |
| `POST /api/v1/delete-requests/{request_id}/approve` | Одобрить запрос на удаление | ✅ (Administrator, Supervisor) |
| `POST /api/v1/delete-requests/{request_id}/reject` | Отклонить запрос на удаление | ✅ (Administrator, Supervisor) |

Дополнительные query-параметры списка кандидатов:
- `status_reason=<code1,code2>` — фильтрация по причинам отказа/отклонения; допускает CSV или повторяющиеся параметры (`status_reason=awaiting_residence&status_reason=salary`). Совмещается с другими фильтрами.
| `POST /api/v1/recruiters/assign` | Подобрать рекрутёра для вакансии/компании | ✅ (Administrator, Supervisor) |

Фильтры:
- `?status=open`
- `?manager_id=...`
- `?company_id=...`
- `?created_from=2025-01-01`
- `?has_valid_documents=true`

### Расширенные поля списка
`GET /api/v1/candidates` возвращает агрегированные сведения о документах для таблицы кандидатов:

- `docs_readiness_state` — агрегированное состояние документов (`pending`, `ordered`, `in_progress`, `awaiting_review`, `ready`, `problem`).
- `docs_last_ordered_at` — дата последнего заказанного документа (ISO `YYYY-MM-DD`).
- `docs_next_valid_from` — ближайшая дата начала действия активного документа (ISO `YYYY-MM-DD`).
- `docs_has_files` — булево, есть ли загруженные файлы по документам кандидата.
- `docs_readiness_rank` — числовой приоритет для сортировки по состоянию (выше = важнее).

Параметр `documents_ordered=ordered|not_ordered` позволяет фильтровать кандидатов по наличию заказанных документов.

---

## UI
- **CandidatesPage** — канбан-счётчики по статусам и таблица с фильтрами (статус, менеджер, дата создания, компания, статус документов); рекрутер видит только доступные компании/вакансии.  
- **CandidateCard** — вкладки: Overview, Documents, Vacancies, Notes/Tasks.  
- **CandidateForm** — создание и редактирование.  
- Отображается цветовая индикация по срокам действия документов.  
- Канбан-пайплайн и карточка стадий доступны рекрутёру только для кандидатов из его ACL (компания, вакансия или `manager_id`), остальные кандидаты не отображаются.
- Поле "Рекрутёр" отображает `recruiter_id` (подписанное по ФИО/short_id) и автоматически обновляется при смене вакансии.

### Business-type preset rule

- `agency` и `employer` получают candidate-first navigation и candidate pipeline по умолчанию.
- `services` не должен открывать `CandidatesPage` или `CandidateCard` как primary CRM workspace по умолчанию.
- Для `services` candidate workflows допустимы только как explicit optional capability, а не как first-value surface после onboarding.

---

## Автоназначение рекрутёра

- При создании/импорте кандидата сервис подбирает `recruiter_id` автоматически и фиксирует стратегию в журнале `activity_log` (`candidate_assigned`).
- Источники подбора:
  1. `vacancy_recruiters` (вес + наименьшая загрузка, tie-breaker по дате последнего назначения).
  2. `vacancy.manager` (владелец вакансии).
  3. Супервайзеры/администраторы компании (по `user_company_access`).
  4. Администраторы арендатора.
- Endpoint `POST /api/v1/recruiters/assign` предоставляет тот же подбор для внешних сценариев (лиды, импорты, интеграции).
- Поле "Рекрутёр" отображает `recruiter_id` (подписанное по ФИО/short_id) и автоматически обновляется при смене вакансии.

---

## События
| Событие | Условие | Действие |
|----------|----------|----------|
| `candidate.created` | Новый кандидат создан (из лида или вручную) | Добавляется в пайплайн со статусом “Новый” |
| `candidate.updated` | Изменены поля | Обновление отображения в UI |
| `candidate.status_changed` | Переход между этапами пайплайна | Логирование, уведомление менеджера |
| `candidate.document_expired` | Истёк документ | Статус → “Ожидаем документы”, создаётся напоминание |
| `candidate.hired` | Завершение пайплайна | Кандидат помечается как трудоустроенный |
| `candidate.rejected` | Отклонён менеджером | Завершение без найма |
| `candidate.delete_requested` | Рекрутер нажал «Запросить удаление» | Запрос передан супервайзеру |
| `candidate.delete_approved` | Супервайзер/администратор одобрил удаление | Кандидат помечен `deleted_at`, карточка блокируется |
| `candidate.delete_rejected` | Запрос на удаление отклонён | Рекрутер получает уведомление |

---

## Безопасность
- Все кандидаты принадлежат конкретному `tenant_id` (RLS включён).  
- Пользователи видят только кандидатов своего tenant.  
- Доступ:
- **Owner / Administrator** — полный CRUD.
- **Supervisor** — CRUD по кандидатам своей команды, подтверждение/отклонение delete-request.
- **Recruiter** — CRUD по кандидатам, связанным с назначенными компаниями/вакансиями (через ACL или `manager_id`), может инициировать delete-request, управлять стадиями пайплайна и задачами только внутри своего ACL, загружать документы. Прямой `DELETE` запрещён.
- **Viewer** — только чтение.
- REST вводит отдельный workflow: `POST /api/v1/candidates/{id}/delete-request` (рекрутер) → `/api/v1/delete-requests` (просмотр очереди) → `approve/reject` (супервайзер/администратор).  
- Данные кандидата (дата рождения, паспорт и т.п.) не возвращаются без флага `include_sensitive=true` и соответствующих прав.  
- При попытке изменить статус без разрешения система возвращает `403 Forbidden`.

---

## Тестирование
- Проверка RLS: кандидаты недоступны пользователям других tenant.  
- Проверка переходов статусов (валидные/невалидные сценарии).  
- CRUD операции и фильтры.  
- Проверка связей с документами и вакансиями.  
- Проверка генерации событий (`candidate.created`, `status_changed`, `document_expired`).  
- Проверка бизнес-правил гражданства и блокировок по документам.  

---

## Mapping (DB ↔ Model ↔ API ↔ UI ↔ Tests)

| Уровень | Что описывает | Источник | Правила/валидация | Эндпоинты/операции | Тесты |
|----------|----------------|-----------|--------------------|--------------------|--------|
| **DB** | Таблица `candidates` (`id`, `tenant_id`, `personal_data`, `contacts`, `experience_eu`, `licenses`, `created_by`, `manager_id`, `status`, `status_reason`, `created_at`, `updated_at`) | `backend/alembic/versions/*_candidate_*.py` | NOT NULL поля; FK `manager_id`, `tenant_id`; уникальность `id` | Миграции `make mig-rev` → `make mig` | Проверка миграций, FK, RLS |
| **Model** | SQLAlchemy модель `Candidate` и `CandidateStatus` | `backend/app/models/candidate.py` | типы полей, Enum статусов, relationships | CRUD и бизнес-логика в `backend/app/services/candidates.py` | Unit-тесты CRUD и переходов |
| **API Schemas** | Pydantic-схемы `CandidateCreate`, `CandidateUpdate`, `CandidateOut` | `backend/app/schemas/candidate.py` | обязательные поля: `personal_data`, `contacts`; Enum `status`; ISO-даты | `/api/v1/candidates*` | Тесты API CRUD и фильтров |
| **UI / Form** | Компоненты `CandidatesTable`, `CandidateCard`, `CandidateForm` | `hostflow-frontend/src/modules/candidates` | обязательные поля; enum для статусов; фильтры | CRUD через `/api/v1/candidates*` | RTL/юнит-тесты таблицы и формы |
| **Business Rules** | Канонический пайплайн кандидата | `docs/specs/core.md` | Статусы, переходы, блокировки | POST `/api/v1/candidates/{id}/status` | Проверка переходов и событий |
| **Events/Reminders** | Напоминания по срокам документов | сервис напоминаний | триггеры `document.expired`, `candidate.status_changed` | планировщик уведомлений | Тесты уведомлений |
| **RLS / Security** | Изоляция по `tenant_id` | Alembic + политики RLS | enforce tenant_id | Все `/api/v1/candidates*` | Проверка tenant-изоляции и ролей |

---

## AI Agent Notes
- Все операции с кандидатами должны выполняться в контексте tenant и с соблюдением RLS.  
- Нельзя изменять статус кандидата напрямую в БД — только через сервис `change_status()`.  
- При создании кандидата агент должен проверять наличие документов и гражданство.  
- Любые изменения в пайплайне требуют обновления `core.md` и `rules.md`.  
- Перевод кандидата в `declined` или `rejected` должен сопровождаться заполнением `status_reason` (массив кодов причин).
- Поддерживайте в актуальном состоянии фильтр `status_reason` в `/api/v1/candidates` и соответствующий UI (список кодов синхронизирован с `meta.reason_choices`).
- При генерации тестов учитывать статусы, события и изоляцию tenant.  
- Все эндпоинты должны быть синхронизированы с API схемами и тестами.
