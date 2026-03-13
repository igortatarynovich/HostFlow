# HostFlow — Living Spec (Core Canon)

**Основные модули:** [Candidates](modules/candidates.md) · [Documents](modules/documents.md) · [Vacancies](modules/vacancies.md) · [Companies](modules/companies.md) · [Leads](modules/leads.md) · [Public Intake / Candidate Portal](../platform/webhooks.md)

---

## North Star
- HostFlow — мульти-тенант HR/ATS для транспорта. Платформа объединяет агентства, клиентские компании и кандидатов (водителей).
- Система должна обслуживать агентство HostFlow и white-label клиентов вроде Northwind Logistics: один суперадмин управляет тенантами и лицензиями, у каждого тенанта — собственные рекрутёры, ACL и правила документов.
- Кандидат всегда имеет единое рабочее место: публичная анкета + чек-лист документов + таймлайн статусов. Никаких сторонних файловых рассылок.

---

## Архитектура и техстек

### Данные и backend
- **PostgreSQL 16** с включённым RLS. Каждая таблица содержит `tenant_id`, контекст выставляется middleware `SET LOCAL app.tenant_id`.
- **FastAPI + SQLAlchemy 2.x + Alembic.** Миграции лежат в `backend/alembic/versions`, формат `YYYYMMDDHHMM_<slug>.py`.
- **Документы**: модели `document_types`, `documents`, `document_attachments`, `document_checks`, `scan_sessions`, `scan_pages`. См. `docs/spec-documents.md`.
- **Публичные API**: `/api/v1/public/apply/{token}` (анкета и документы), `/api/v1/public/scan-sessions` (камерные сессии), `/api/v1/public/status/{token}` (шаринг для клиента).
- **Обработка изображений**: сервис `scanner.py` использует Python+OpenCV внутри backend-контейнера (opencv-python-headless). Браузерный wasm-сканер исключён; камера → upload → серверная обработка.

### Frontend
- **React + Vite + TypeScript + Tailwind**. Структура feature-based (см. `src/pages`, `src/modules`).
- **Public intake**: мастера шагов (контакты, персональные данные, опыт, работодатели, документы, согласия). Документы — radio «Есть/Нет?», загрузка файлов, прогресс/таймлайн.
- **Кандидатский портал** работает на том же SPA: публичные руты `/public`, приватные `/app`.
- **i18n**: JSON-файлы `src/i18n/{en,ru,pl}.json`, обязательные локали `en/ru/pl`, правила см. `docs/specs/i18n/index.md`.

### Хранилище файлов и интеграции
- Файлы документов хранятся в S3-совместимом бакете; presign выполняется через backend (`presignPublicDocument`).
- Интеграции Leads — webhooks + CSV импорт (см. `docs/specs/modules/leads.md`).
- Webhooks и внешние сервисы документированы в `docs/specs/platform/webhooks.md`.

### Observability
- Prometheus-метрики (`hf_documents_*`, `hf_api_request_duration_seconds` и т.д.) и audit log описаны в `docs/specs/platform/observability.md`.
- Каждый tenant видит свои метрики, суперадмин — агрегированные дашборды.

---

## Multitenancy & RBAC (кратко)

Полная модель описана в `docs/specs/architecture/multi_tenant_model.md` и `docs/specs/architecture/rbac_matrix.md`. Конспект:

- **Уровни:** `platform (HostFlow HQ)` → `tenant agency` → `sub-client (company)` → `end user / candidate`.
- **Роли:**
  - `superadmin` — управляет лицензиями, создаёт тенанты, может импёрсонировать.
  - `administrator/owner` — рулит всем в рамках тенанта (пользователи, ruleset, ACL, импорт).
  - `supervisor` — контролирует рекрутёров, подтверждает soft-delete кандидатов.
  - `recruiter` — работает с лидами/кандидатами/доками в пределах ACL; может инициировать soft-delete.
  - `viewer` — read-only внутри тенанта.
  - `client_manager` — менеджер компании в клиентском портале.
  - `candidate` — пользователь публичного портала.

### Создание клиента / пользователей
1. **Суперадмин** через Platform Control Center вызывает `POST /api/v1/platform/tenants` (или CLI `make tenant:create`). Указывает тип (`agency` или `company`), план, лимиты.
2. В Tenant Admin Console создаёт компании (`companies`), вакансии и локальных админов.
3. **Пользователи клиента Northwind Logistics** создаются из Tenant Admin Console или API `/api/v1/settings/users`: указываем email, роль (`client_manager`, `viewer`, и т.д.). Приглашения отправляются почтой, пароль задаётся по ссылке.
4. ACL к компаниям и вакансиям выдаётся админу/супервизору через `/api/v1/admin/companies/{id}/access`.
5. Лимиты лицензии и usage тенанта проверяются через `/api/v1/settings/team` (см. `docs/specs/modules/tenants.md`), запросы на доп. места отправляются из того же раздела.

RLS и middleware блокируют любые запросы вне текущего tenant. Реальность спецификации RBAC проверяется интеграционными тестами (`tests/api/test_auth_rbac.py`).

---

## Module Map (source of truth)

| Модуль | Основная таблица / модель | Ключевые API | UI / панели | Примечания |
|--------|---------------------------|--------------|-------------|------------|
| Candidates | `candidates`, `candidate_status_history` | `/api/v1/candidates*` | CandidatesTable, CandidateCard | Статусы, причины отказа, ACL по компаниям |
| Documents | `documents`, `document_types`, `scan_sessions` | `/api/v1/documents*`, `/api/v1/scanner*`, `/api/v1/public/scan-sessions*` | DocumentsTab, checklist на портале | Ruleset per tenant, напоминания, timeline |
| Vacancies | `vacancies` | `/api/v1/vacancies*` | VacanciesList, VacancyDetail | Привязка к компаниям, экспорт |
| Companies | `companies`, `company_access` | `/api/v1/companies*` | Companies page, Client portal | ACL выдаётся администраторами/супервизорами |
| Leads | `leads`, `lead_sources`, `lead_imports` | `/api/v1/leads*`, webhooks | Leads board, Supervisor dashboard | Webhook создаёт кандидата или лидер |
| Public Intake | `public_intake_links`, `documents` | `/api/v1/public/apply/{token}`, `/api/v1/public/status/{token}` | Candidate portal (контакты → документы → таймлайн) | Локали en/ru/pl, автосохранение, share link |

---

## Канонический пайплайн кандидата

1. Новый  
2. Не отвечает  
3. Контакт установлен  
4. Ожидаем документы  
5. Документы получены  
6. Заказ разрешения на работу  
7. Разрешение получено  
8. Виза  
9. Красная бумага заказана  
10. Планируем приезд  
11. На базе клиента  
12. Выехал в рейс  
13. Пробный пройден  
14. Трудоустроен  
15. Отклонён  
16. Отказался  

Правила переходов зависят от гражданства, статуса проживания, требований клиента и наличия обязательных документов (см. Ruleset). Для “Отклонён”/“Отказался” обязательны коды причин (`status_reason`), перечисленные в `modules/candidates.md`.

---

## Документы, правила и захват изображений

### Типы и статусы
- `DocumentType`: код, владельцы (`candidate/company/vacancy`), обязательность, meta-schema, регексы, срок действия.
- Статусы файла: `missing`, `requested`, `in_progress`, `submitted`, `received`, `delivered`, `completed`, `approved`, `expired`, `overdue`, `rejected`.
- Сводка владельца: процент готовности, блокеры (`missing_types`, `problems`), напоминания. См. `docs/spec-documents.md`.

### Ruleset
- JSON per tenant. Параметры: `citizenship`, `residency_status`, `vacancy.requires_visa`, `country_of_work`, кастомные условия.
- Приоритет: vacancy → company → tenant → global.
- Сервер генерирует чек-лист, портал показывает те же коды, используя локализацию.

### Захват
- Мастер загрузки документов в портале: радио “Есть документ?” → загрузить файл → серверная обработка → статус.
- Если документ требует фотозахвата, рекрутер создаёт `scan_session`. Пользователь открывает `/public/scan-sessions/{id}`: камера, подсказки, сервер режет контур OpenCV и сохраняет `scan_pages`.
- Фронтенд больше не использует `opencv.js`/wasm — CSP упрощён, нет COOP/COEP.

---

## Public Intake & Candidate Portal

- Публичная анкета (`/public/apply/{token}`) состоит из шагов: Overview → Contacts → Personal → Experience → Employment → Documents → Agreements. Автосохранение.
- Документы: общий блок `Document requirements`, список карточек с прогрессом, статусами и ссылкой «Открыть файл» (если уже загружено). Есть fallback «загрузить файл» даже на ПК без камеры.
- Таймлайн и share-link:
  - Портал показывает таймлайн `Review status`: `intake_created`, `profile_data`, `documents_upload`, `submitted`. Значения локализованы.
  - Пользователь может запросить новый share-токен для клиента. `/api/v1/public/status/{token}` показывает прогресс без авторизации.
- Локализация: все ключи обязаны существовать в `en/ru/pl`. i18n правила — см. `docs/specs/i18n/index.md`.

---

## Leads & Integrations

- Любой входящий лид создаёт запись в `leads`. Вебхук (Meta Ads и др.) описан в `docs/specs/modules/leads.md`.
- Supervisor/Administrator обрабатывают `needs_routing`, рекрутеры получают только распределённые лиды.
- Client portal и Candidate portal используют отдельные токены (`status_share_token`, `public_token`). Хранение токена и аудит — обязательны.

---

## Observability & Audit (TL;DR)

- Метрики: перечислены в `docs/specs/platform/observability.md`. Минимум — `hf_documents_workflow_duration_seconds`, `hf_documents_overdue_total`, `hf_api_request_duration_seconds`.
- Логи: JSON, уровень INFO/ERROR по событиям `lead.*`, `document.*`, `notification.*`. Ошибки i18n логируются с указанием ключа/локали.
- Audit log (`audit_log`): все изменения ролей, ACL, soft-delete кандидатов, изменения настроек напоминаний/вебхуков.
- Алёрты: просроченные документы, сбои вебхуков, лаги очередей, ошибки миграций.

---

## Definition of Done (обновлённая)

- ✅ RLS и RBAC соответствуют матрице. Любая операция проверяется на `tenant_id`, роль и ACL.
- ✅ CRUD + фильтры для Candidates/Companies/Vacancies/Documents/Leads.
- ✅ Лид-вебхук создаёт кандидата или оформляет лид с привязкой к тенанту.
- ✅ Документы: ruleset, статусы, напоминания, share-link, публичная анкета.
- ✅ Публичный портал / анкета: автосохранение, таймлайн, локализация en/ru/pl, fallback загрузки без сканера.
- ✅ Observability: Prometheus метрики, audit log, alert правила.
- ✅ Тесты: `pytest` (auth/RLS/CRUD/documents), Playwright smoke (портал/документы), `npm run test` для UI критичных компонентов.
- ✅ Dockerized deploy (`docker compose`), миграции Alembic, фикстуры (`backend/app/db/seeds`).

---

## Tooling, Deploy & Ops

- **Backend**: `docker compose up -d backend db`, `docker compose exec backend alembic upgrade head`, `pytest`.
- **Frontend**: `cd hostflow-frontend && npm ci && npm run build` (Vite). Статический билд монтируется как volume `/app/public`. Нельзя перезапускать backend до выкладки свежего `dist`.
- **Lints**: `ruff`, `mypy`, `eslint`, `pre-commit`. i18n валидация — `npm run i18n:check` (сравнение `en/ru/pl`).
- **Scanner/OpenCV**: при обновлении зависимостей rebuild backend образа (`docker compose build backend`), поскольку wheel ставится в контейнер.
- **Manual checklist**: для критических релизов использовать `docs/manual-checklist/README.md`.

---

## Ссылки
- Multitenancy: `docs/specs/architecture/multi_tenant_model.md`
- RBAC Matrix: `docs/specs/architecture/rbac_matrix.md`
- Documents: `docs/spec-documents.md`
- Observability: `docs/specs/platform/observability.md`
- i18n Registry: `docs/specs/i18n/index.md`
- Roadmap: `docs/specs/roadmap.md`
