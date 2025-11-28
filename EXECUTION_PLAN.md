# HostFlow — План реализации (Execution Plan)

**Дата создания:** 2025-01-XX  
**Основа:** Анализ кода, документации, миграций и конфигурации проекта

---

## 1. Project Map

### 1.1 Существующие модули (Core)

| Модуль | Backend | Frontend | Статус | Зависимости |
|--------|---------|----------|--------|-------------|
| **Auth & RBAC** | `app/auth/`, `app/core/rbac.py` | `store/auth.tsx` | ✅ Core | RLS, JWT, tenants |
| **Candidates** | `app/api/v1/candidates/`, `app/models/candidate.py` | `pages/Candidates.tsx`, `pages/CandidateCard.tsx` | ✅ Core | Documents, Vacancies, Companies |
| **Documents** | `app/modules/documents/`, `app/models/document.py` | `pages/DocumentsRegistryPage.tsx`, `modules/documents/` | ✅ Core | Candidates, Ruleset, Reminders |
| **Companies** | `app/modules/companies/`, `app/models/company.py` | `pages/Companies.tsx` | ✅ Core | Tenants, Access |
| **Vacancies** | `app/api/v1/vacancies/`, `app/models/vacancy.py` | `pages/Vacancies.tsx` | ✅ Core | Companies, Candidates |
| **Leads** | `app/modules/leads/`, `app/models/lead.py` | `pages/LeadsPage.tsx` | ✅ Core | Meta webhook, Candidates |
| **Public Intake** | `app/api/public/intake.py` | `pages/public/PublicApplyPage.tsx` | ✅ Core | Documents, Scanner |
| **Scanner** | `app/api/v1/scanner.py`, `app/services/scanner.py` | `pages/public/PublicScanPage.tsx` | ✅ Core | OpenCV, Documents |
| **Tenants** | `app/api/v1/tenants/`, `app/models/tenant.py` | `pages/admin/TenantsPage.tsx` | ✅ Core | Platform API |
| **Notifications** | `app/api/v1/notifications.py`, `app/models/user_notification.py` | - | ✅ Core | Events, Reminders |
| **Reminders** | `app/services/reminders.py`, `app/models/reminder.py` | `pages/RemindersPage.tsx` | ✅ Core | Documents, Scheduler |
| **Additional Services** | `app/api/v1/services.py`, `app/models/additional_service.py` | `pages/ServicesPage.tsx` | ✅ Core | Candidates, Providers |
| **Stages** | `app/api/v1/stages.py`, `app/models/stage.py` | `pages/Pipeline.tsx` | ✅ Core | Candidates |

### 1.2 Модули в разработке (In Progress)

| Модуль | Backend | Frontend | Статус | Блокеры |
|--------|---------|----------|--------|---------|
| **User Profile** | `app/models/user.py` (extra JSONB) | `pages/ProfilePage.tsx` | 🚧 Partial | Preferences schema |
| **Ruleset Versioning** | `app/models/document_ruleset.py` | `pages/admin/RulesetVersionsPage.tsx` | 🚧 Partial | Diff engine, UI |
| **Meta Leads Admin** | `app/modules/leads/admin_service.py` | `pages/admin/MetaLeadsAdminPage.tsx` | 🚧 Partial | Graph API integration |
| **Company Profile** | `app/modules/companies/` (extended) | - | 🚧 Partial | Schema expansion |

### 1.3 Отсутствующие модули (Planned/Missing)

| Модуль | Приоритет | Зависимости | Файлы для создания |
|--------|-----------|------------|-------------------|
| **Invoicing** | 🔥 High | Companies, Services | `app/modules/invoicing/`, `app/models/invoice.py` |
| **Payments** | 🔥 High | Invoicing | `app/modules/payments/`, Stripe/Revolut integration |
| **Candidate Portal (full)** | 🔥 High | Public Intake, Documents | `pages/public/` (enhance) |
| **Providers Network** | ⚙️ Medium | Additional Services | `app/modules/providers/`, `app/models/provider.py` |
| **Scheduler** | ⚙️ Medium | Services, Providers | `app/modules/scheduler/`, calendar integration |
| **E-signature** | ⚙️ Medium | Documents, Contracts | `app/modules/esignature/`, Autenti/DocuSign |
| **Approvals** | ⚙️ Medium | Documents, Contracts | `app/modules/approvals/`, workflow engine |
| **Identity Verification** | 🧩 Low | Documents, OCR | `app/modules/identity_verification/` |
| **Logistics** | 🧩 Low | Candidates, Companies | `app/modules/logistics/` |
| **Training** | 🧩 Low | Candidates, Providers | `app/modules/training/` |
| **Matching Engine** | 🧭 Roadmap | Candidates, Vacancies, ML | `app/modules/matching/` |
| **Tachograph** | 🧭 Roadmap | Documents, Integrations | `app/modules/tachograph/` |

### 1.4 Архитектурные узлы

| Узел | Реализация | Статус | Риски |
|------|------------|--------|-------|
| **Database (PostgreSQL 16)** | `docker-compose.yml` (postgres:16-alpine) | ✅ | RLS policies, migrations |
| **RLS (Row-Level Security)** | `app/auth/ensure_multitenancy.py` | ✅ | Tenant isolation critical |
| **API Gateway** | FastAPI (`app/main.py`) | ✅ | CORS, middleware |
| **File Storage** | Local `/uploads` (S3-ready) | ✅ | Migration to S3 needed |
| **Observability** | Prometheus (`app/observability/metrics.py`) | ✅ | Metrics coverage gaps |
| **Queue/Events** | In-memory (no Celery/RabbitMQ) | ⚠️ | Background tasks limited |
| **Cache** | None | ❌ Missing | Performance bottleneck |
| **Webhooks** | `app/core/webhooks.py` | ✅ | Retry logic needed |
| **i18n** | JSON files (`hostflow-frontend/src/i18n/`) | ✅ | Registry validation |

### 1.5 Точки риска и технический долг

| Риск | Описание | Критичность | Файлы |
|------|----------|-------------|-------|
| **RLS bypass** | Tenant isolation может быть нарушена | 🔴 Critical | Все модели с `tenant_id` |
| **Migration conflicts** | Множественные heads в Alembic | 🟡 High | `backend/alembic/versions/` |
| **File storage** | Локальное хранилище, нет S3 | 🟡 High | `app/services/document_files.py` |
| **Background tasks** | Нет очереди для async задач | 🟡 High | Reminders, notifications |
| **No cache layer** | Каждый запрос идёт в БД | 🟡 Medium | All API endpoints |
| **Scanner OpenCV** | Тяжёлая зависимость в контейнере | 🟡 Medium | `backend/Dockerfile` |
| **i18n registry** | Нет автоматической валидации | 🟢 Low | `hostflow-frontend/src/i18n/` |
| **Legacy document fields** | Старые поля (`type`, `issued_at`) | 🟢 Low | `app/models/document.py` |
| **No API versioning** | Все эндпоинты под `/api/v1` | 🟢 Low | `app/api/v1/` |

---

## 2. Execution Plan

### 2.1 Шаг 1: Критическая инфраструктура и безопасность

#### 1.1 RLS и Tenant Isolation
- **Задача 1.1.1:** Аудит всех моделей на наличие `tenant_id` и RLS policies
  - Файлы: `backend/app/models/*.py`
  - Действие: Проверить каждую модель, добавить `tenant_id` где отсутствует
- **Задача 1.1.2:** Валидация RLS policies в PostgreSQL
  - Файлы: `backend/app/auth/ensure_multitenancy.py`
  - Действие: Запустить тесты на tenant isolation для всех таблиц
- **Задача 1.1.3:** Middleware проверка `X-Tenant-Id` во всех API endpoints
  - Файлы: `backend/app/auth/deps.py`, `backend/app/main.py`
  - Действие: Убедиться, что все роутеры используют `get_current_tenant()`

#### 1.2 Миграции Alembic
- **Задача 1.2.1:** Разрешить конфликты множественных heads
  - Файлы: `backend/alembic/versions/00bfe5b21d89_merge_all_heads.py`
  - Действие: Создать merge-миграцию, проверить цепочку ревизий
- **Задача 1.2.2:** Синхронизация схем БД с документацией
  - Файлы: `docs/specs/db/*.sql`, `backend/alembic/versions/*.py`
  - Действие: Обновить SQL-схемы после каждой миграции

#### 1.3 Observability и мониторинг
- **Задача 1.3.1:** Расширить Prometheus метрики
  - Файлы: `backend/app/observability/metrics.py`
  - Действие: Добавить `hf_tenant_*`, `hf_documents_*`, `hf_api_*` метрики
- **Задача 1.3.2:** Настроить алерты для критических событий
  - Файлы: `docs/specs/platform/observability.md`
  - Действие: Определить пороги для документов, лицензий, ошибок

### 2.2 Шаг 2: Критические модули (MVP)

#### 2.1 Documents Module (финализация)
- **Задача 2.1.1:** Миграция legacy полей (`type` → `doc_type`, `issued_at` → `issue_date`)
  - Файлы: `backend/app/models/document.py`, миграция
  - Действие: Создать миграцию, обновить все сервисы
- **Задача 2.1.2:** Реализовать `compute_auto_status` для workflow
  - Файлы: `backend/app/services/document_workflow.py`
  - Действие: Логика автопродвижения статусов по шагам
- **Задача 2.1.3:** Интеграция reminders с workflow steps
  - Файлы: `backend/app/services/reminders.py`
  - Действие: Напоминания по `workflow.steps[*].due_at`
- **Задача 2.1.4:** UI для workflow редактирования
  - Файлы: `hostflow-frontend/src/modules/documents/`
  - Действие: Компонент редактирования шагов, дат, статусов

#### 2.2 Candidate Portal (полная реализация)
- **Задача 2.2.1:** Завершить публичную анкету (все шаги)
  - Файлы: `hostflow-frontend/src/pages/public/PublicApplyPage.tsx`
  - Действие: Шаги: Contacts → Personal → Experience → Employment → Documents → Agreements
- **Задача 2.2.2:** Таймлайн статусов с локализацией
  - Файлы: `hostflow-frontend/src/pages/public/PublicTimeline.tsx`
  - Действие: Отображение `intake_created`, `profile_data`, `documents_upload`, `submitted`
- **Задача 2.2.3:** Share-link для клиентов (`status_share_token`)
  - Файлы: `backend/app/api/public/intake.py`, `hostflow-frontend/src/pages/public/PublicStatusPage.tsx`
  - Действие: Генерация токена, публичная страница без авторизации

#### 2.3 Ruleset Versioning
- **Задача 2.3.1:** Backend для версионирования ruleset
  - Файлы: `backend/app/services/ruleset_versioning.py`
  - Действие: CRUD версий, diff между версиями
- **Задача 2.3.2:** UI для просмотра и применения версий
  - Файлы: `hostflow-frontend/src/pages/admin/RulesetVersionsPage.tsx`
  - Действие: Таблица версий, кнопка "Apply version", diff view

### 2.3 Шаг 3: Высокоприоритетные модули

#### 3.1 Invoicing Module
- **Задача 3.1.1:** Модели и схемы БД
  - Файлы: `backend/app/models/invoice.py`, миграция `*_invoicing.py`
  - Действие: Таблицы `invoices`, `invoice_items`, `invoice_payments`
- **Задача 3.1.2:** API для создания и управления счетами
  - Файлы: `backend/app/api/v1/invoicing/`, `backend/app/modules/invoicing/`
  - Действие: CRUD, генерация PDF, нумерация счетов
- **Задача 3.1.3:** UI для просмотра и создания счетов
  - Файлы: `hostflow-frontend/src/pages/admin/BillingTeamPage.tsx` (extend)
  - Действие: Таблица счетов, форма создания, экспорт PDF

#### 3.2 Payments Module
- **Задача 3.2.1:** Интеграция Stripe/Revolut/Przelewy24
  - Файлы: `backend/app/modules/payments/`, `backend/app/services/payments.py`
  - Действие: Webhook handlers, payment intents, статусы
- **Задача 3.2.2:** UI для оплаты счетов
  - Файлы: `hostflow-frontend/src/pages/public/PaymentPage.tsx`
  - Действие: Форма оплаты, редирект на платежный шлюз

#### 3.3 Tenant Management (Platform API)
- **Задача 3.3.1:** API для управления лицензиями
  - Файлы: `backend/app/api/v1/platform/tenants.py` (extend)
  - Действие: `POST /platform/tenants`, `PATCH /platform/tenants/{id}/license`
- **Задача 3.3.2:** Self-service seat requests
  - Файлы: `backend/app/models/tenant_seat_request.py`, `backend/app/api/v1/settings/team.py`
  - Действие: Модель, API для запросов, approval workflow
- **Задача 3.3.3:** Platform Control Center UI
  - Файлы: `hostflow-frontend/src/pages/admin/TenantsPage.tsx` (extend)
  - Действие: Таблица тенантов, управление лицензиями, seat requests

### 2.4 Шаг 4: Среднеприоритетные модули

#### 4.1 Providers Network
- **Задача 4.1.1:** Модели провайдеров (медцентры, школы, etc.)
  - Файлы: `backend/app/models/provider.py`, миграция
  - Действие: Таблица `providers`, связи с services
- **Задача 4.1.2:** API для управления провайдерами
  - Файлы: `backend/app/api/v1/providers/`, `backend/app/modules/providers/`
  - Действие: CRUD, поиск, рейтинги

#### 4.2 Scheduler Module
- **Задача 4.2.1:** Модели расписаний и бронирований
  - Файлы: `backend/app/models/schedule.py`, миграция
  - Действие: Таблицы `schedules`, `bookings`, интеграция с календарями
- **Задача 4.2.2:** API для создания и управления расписаниями
  - Файлы: `backend/app/api/v1/scheduler/`, `backend/app/modules/scheduler/`
  - Действие: CRUD, конфликты, уведомления

#### 4.3 E-signature Integration
- **Задача 4.3.1:** Интеграция с Autenti/DocuSign
  - Файлы: `backend/app/modules/esignature/`, `backend/app/services/esignature.py`
  - Действие: API клиенты, webhook handlers, статусы подписей
- **Задача 4.3.2:** UI для отправки на подпись
  - Файлы: `hostflow-frontend/src/modules/documents/` (extend)
  - Действие: Кнопка "Send for signature", статус подписи

### 2.5 Шаг 5: Низкоприоритетные модули и оптимизация

#### 5.1 Identity Verification
- **Задача 5.1.1:** OCR и selfie verification
  - Файлы: `backend/app/modules/identity_verification/`
  - Действие: Интеграция с внешними сервисами, валидация документов

#### 5.2 Logistics Module
- **Задача 5.2.1:** Модели для билетов, трансферов, проживания
  - Файлы: `backend/app/models/logistics.py`, миграция
  - Действие: Таблицы `bookings`, `transfers`, `accommodations`

#### 5.3 Performance Optimization
- **Задача 5.3.1:** Внедрить кэширование (Redis)
  - Файлы: `backend/app/core/cache.py`, `docker-compose.yml`
  - Действие: Redis контейнер, cache decorators для API
- **Задача 5.3.2:** Оптимизация запросов к БД
  - Файлы: Все `crud.py`, `repo.py`
  - Действие: Eager loading, индексы, query optimization

#### 5.4 File Storage Migration
- **Задача 5.4.1:** Миграция на S3-совместимое хранилище
  - Файлы: `backend/app/services/document_files.py`
  - Действие: S3 клиент, presign URLs, миграция существующих файлов

---

## 3. Prioritization Table

| Приоритет | Задачи | Обоснование | Блокеры |
|-----------|--------|-------------|---------|
| **🔴 Critical** | RLS audit, Migration conflicts, Tenant isolation | Безопасность данных, стабильность БД | Все остальные модули |
| **🟠 High** | Documents workflow, Candidate Portal, Invoicing, Payments | Ключевой функционал SaaS, монетизация | Tenant management |
| **🟡 Medium** | Providers Network, Scheduler, E-signature, Ruleset versioning | Улучшение UX, автоматизация | Core modules stable |
| **🟢 Low** | Identity Verification, Logistics, Cache, File storage migration | Оптимизация, расширенный функционал | No blockers |

### Детализация по модулям

| Модуль | Приоритет | Зависимости | Критичность для MVP |
|--------|-----------|-------------|---------------------|
| RLS & Security | 🔴 Critical | - | Блокирует всё |
| Documents (workflow) | 🟠 High | RLS | Блокирует Candidate Portal |
| Candidate Portal | 🟠 High | Documents | Блокирует SaaS цикл |
| Invoicing | 🟠 High | Companies, Services | Блокирует монетизацию |
| Payments | 🟠 High | Invoicing | Блокирует завершение цикла |
| Tenant Management | 🟠 High | RLS | Блокирует multi-tenant SaaS |
| Providers Network | 🟡 Medium | Services | Улучшает UX |
| Scheduler | 🟡 Medium | Providers, Services | Автоматизация |
| E-signature | 🟡 Medium | Documents | Compliance |
| Cache & Performance | 🟢 Low | All modules | Масштабирование |

---

## 4. Execution Order

### Фаза 1: Фундамент (Week 1-2)
1. ✅ RLS audit и исправления (`backend/app/models/`, `backend/app/auth/`)
2. ✅ Разрешение миграционных конфликтов (`backend/alembic/versions/`)
3. ✅ Расширение observability метрик (`backend/app/observability/`)
4. ✅ Тесты на tenant isolation (`backend/tests/api/test_auth_rbac.py`)

### Фаза 2: Documents & Portal (Week 3-4)
5. ✅ Documents workflow (`backend/app/services/document_workflow.py`)
6. ✅ Миграция legacy полей документов (Alembic)
7. ✅ Candidate Portal UI (`hostflow-frontend/src/pages/public/`)
8. ✅ Share-link для статусов (`backend/app/api/public/`)

### Фаза 3: Монетизация (Week 5-6)
9. ✅ Invoicing module (`backend/app/modules/invoicing/`)
10. ✅ Payments integration (`backend/app/modules/payments/`)
11. ✅ Tenant license management (`backend/app/api/v1/platform/`)
12. ✅ Self-service seat requests (`backend/app/models/tenant_seat_request.py`)

### Фаза 4: Автоматизация (Week 7-8)
13. ✅ Providers Network (`backend/app/modules/providers/`)
14. ✅ Scheduler module (`backend/app/modules/scheduler/`)
15. ✅ E-signature integration (`backend/app/modules/esignature/`)
16. ✅ Ruleset versioning UI (`hostflow-frontend/src/pages/admin/`)

### Фаза 5: Оптимизация (Week 9-10)
17. ✅ Cache layer (Redis) (`backend/app/core/cache.py`)
18. ✅ File storage migration (S3) (`backend/app/services/document_files.py`)
19. ✅ Performance optimization (queries, indexes)
20. ✅ Identity Verification (если требуется)

---

## 5. Key Risks & Missing Pieces

### 5.1 Критические риски

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| **RLS bypass** | Средняя | Критическое (утечка данных) | Аудит всех запросов, тесты на isolation |
| **Migration conflicts** | Высокая | Высокое (блокирует деплой) | Merge-миграции, проверка перед merge |
| **File storage limits** | Высокая | Среднее (рост данных) | Миграция на S3, cleanup старых файлов |
| **Background tasks** | Средняя | Среднее (задержки) | Внедрить Celery/RQ или async tasks |
| **Performance degradation** | Средняя | Среднее (UX) | Кэширование, оптимизация запросов |

### 5.2 Отсутствующие компоненты

| Компонент | Статус | Приоритет | Файлы для создания |
|-----------|--------|-----------|-------------------|
| **Queue system** | ❌ Missing | 🟡 High | `backend/app/core/queue.py`, Celery/RQ |
| **Cache layer** | ❌ Missing | 🟡 Medium | `backend/app/core/cache.py`, Redis |
| **S3 storage** | ❌ Missing | 🟡 High | `backend/app/services/s3_storage.py` |
| **API versioning** | ❌ Missing | 🟢 Low | `backend/app/api/v2/` |
| **Webhook retry** | ⚠️ Partial | 🟡 Medium | `backend/app/core/webhooks.py` (enhance) |
| **i18n validation** | ⚠️ Partial | 🟢 Low | `hostflow-frontend/scripts/check-i18n.ts` (enhance) |
| **Audit log UI** | ❌ Missing | 🟡 Medium | `hostflow-frontend/src/pages/admin/AuditLogPage.tsx` |
| **Bulk operations** | ⚠️ Partial | 🟡 Medium | `backend/app/models/document_reporting.py` (extend) |

### 5.3 Технический долг

| Проблема | Файлы | Приоритет | Действие |
|----------|-------|-----------|----------|
| Legacy document fields | `app/models/document.py` | 🟢 Low | Deprecate, миграция данных |
| No API versioning | `app/api/v1/` | 🟢 Low | Планировать v2 |
| Hardcoded constants | `app/constants/` | 🟢 Low | Вынести в конфиг/БД |
| Incomplete i18n | `hostflow-frontend/src/i18n/` | 🟡 Medium | Валидация, заполнение пробелов |
| No rate limiting | `app/main.py` | 🟡 Medium | Добавить middleware |

---

## 6. Success Criteria

### Минимальный рабочий продукт (MVP)
- ✅ Все модули Core работают стабильно
- ✅ RLS и tenant isolation протестированы
- ✅ Candidate Portal полностью функционален
- ✅ Documents workflow реализован
- ✅ Invoicing и Payments интегрированы
- ✅ Tenant management работает для суперадмина

### Полная версия (v1.0)
- ✅ Все модули из Roadmap Phase 2 реализованы
- ✅ Performance оптимизирован (cache, queries)
- ✅ File storage на S3
- ✅ Background tasks через очередь
- ✅ Полное покрытие тестами (>80%)
- ✅ Документация API обновлена

---

**Примечание:** Этот план основан на фактическом анализе кода и документации. Все задачи привязаны к конкретным файлам и директориям. Приоритизация учитывает зависимости между модулями и критичность для бизнеса.

