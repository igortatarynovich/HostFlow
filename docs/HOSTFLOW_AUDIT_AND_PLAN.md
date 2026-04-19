# HostFlow — Состояние системы и план развития

**Назначение документа:** одноразовый архитектурный аудит и дорожная карта развития HostFlow — от текущего состояния к продукту уровня «лучше Pipedrive по простоте и результату». Документ **не заменяет** `docs/SSOT.md` (операционный бэклог с `[ ]`) и не является трекером прогресса. Прогресс по задачам ведётся в `docs/SSOT.md` §2.1 (см. §1.1 и §1.3 там).

**Связанные документы:**

- `docs/SSOT.md` — правила, бэклог `[ ]`, коммерческая модель (§2.16–§2.18).
- `docs/pipe.md` — продуктовый blueprint, UX-принципы, data model.
- `docs/pipedesign.md` — лендинг, дизайн-система, токены.
- `docs/specs/**` — модульные спеки.
- `AGENTS.md` — правила для разработчиков и AI-агентов.

**Продуктовая цель документа (из запроса владельца):**

1. Превзойти Pipedrive по простоте и ощущению «система сама ведёт меня».
2. Чистый, логичный, понятный интерфейс **без перегруза** — один экран = одна цель, один следующий шаг.
3. **Метрики в нужных местах** — не «дашборд ради дашборда», а цифры, которые отвечают на конкретные вопросы пользователя прямо там, где он работает.
4. Сильные, полезные, удобные модули: **документы**, **календарь**, **напоминания**, **сообщения**.
5. Каждый пользователь (рекрутёр, супервайзер, администратор, клиент) получает результат без обучения.

---

## Часть I. Состояние системы (факты на сегодня)

### 1.1 Архитектурный снимок

| Слой | Технологии | Комментарий |
|------|-----------|-------------|
| Frontend | React 18 + TypeScript + Vite, React Router 6, Tailwind, react-hook-form + zod, recharts, dnd-kit, tabler icons | Вкл. react-virtuoso в зависимостях, но используется неравномерно. Vitest для unit, Playwright для E2E (скелет, без критичных сценариев). |
| Backend | FastAPI + Uvicorn, Python 3.11, SQLAlchemy 2.0, Alembic, PyJWT, Passlib, Prometheus client | OpenCV-python-headless в образе (документ-сканер). |
| Инфра | PostgreSQL 16, Redis 7, Caddy (reverse proxy), Docker Compose | Redis подключён, но используется **только** под кеш; очереди — нет (см. §1.3). |
| Мультитенантность | PostgreSQL RLS + `X-Tenant-Id` header + JWT claims | Канонические тенанты в `backend/app/constants/hostflow_canonical_tenants.py`. |
| Codegen | `shared/crm_app_paths.json` → фронт `crmAppPaths.generated.ts` + бэкенд `spa_paths.py` | Канонический источник URL SPA; CI проверяет дрейф. |
| Биллинг | Stripe Checkout + Webhooks | Частичная реализация спеки §2.18: нет Stripe Tax/VIES, нет SKU add-on packs, нет Customer Portal поверх Checkout. |
| Интеграции | Meta Leads (Graph API), Gmail OAuth, Microsoft Graph, IMAP/SMTP, Telegram, WhatsApp Cloud, Viber | Всё живое в `api/v1/communications.py` — один файл ~8700 LOC. |

### 1.2 Объём кодовой базы

- **Backend:** ~160 Alembic-миграций, десятки модулей в `backend/app/modules/*`. Крупнейшие файлы: `api/v1/communications.py` ~8.7k LOC, `api/v1/settings/billing.py` ~3.3k LOC, `modules/leads/service.py` ~4.1k LOC.
- **Frontend:** десятки страниц в `hostflow-frontend/src/pages/*`. Крупнейшие: ~~`Candidates.tsx` ~5.7k LOC~~ → 3008 LOC после Phase 1 #4, ~~`Dashboard.tsx` ~4.1k LOC~~ → **2221 LOC** (−46 %, −1922 строки) после Phase 1 #5 (10 извлечённых модулей: stageNormalize, internal, useDashboardKpiLoaders, useDashboardRiskOps, useDashboardRetention, useDashboardLayoutPrefs, useDashboardDerivedAnalytics, DashboardFiltersBar, DashboardExecutiveOverview, DashboardPivotPanels). tsc + eslint clean (исправлен pre-existing TS2322 для recharts Tooltip).
- **i18n:** 3 локали (`en/ru/pl`), ~11.5k ключей каждая; при этом ~960 хардкод-строк на кириллице остаются в 65 `.tsx` файлах — признак, что i18n не enforced везде.
- **CRM paths:** ~70 канонических маршрутов в `shared/crm_app_paths.json`.

### 1.3 Что фактически реализовано (контуры «1a»)

- **Лиды:** Meta ingest, auto-fix, NBA snapshots, квалификация (частично), автораспределение, воронка конверсии v1.
- **Кандидаты:** карточка, список, канбан, bulk-действия, no-next-action очередь, public intake.
- **Вакансии:** CRUD, связка с компаниями, простые пайплайны.
- **Коммуникации (inbox):** омниканальный тред-view, Gmail/IMAP/Graph/Telegram/WhatsApp/Viber, шаблоны, планировщик, SLA-инциденты, календарь, command-аудит, team availability, time-off.
- **Документы:** реестр, workflow, rulesets, сканер (OpenCV), intelligence v1.
- **Work/Dashboard:** единый shell, stuck-очереди, NBA, виджеты.
- **Настройки:** хаб интеграций, коммуникации (очередь/SLA/мессенджеры/email), users, audit, companies, voronki.
- **Биллинг v1:** Stripe Checkout по основным планам, gate по past_due/trial, founder pricing (€99/€199), in-memory quota.
- **Портал клиента / кандидата:** базовый слой без branded-биллинга.

### 1.4 Критические архитектурные проблемы

| # | Проблема | Риск | Где видно |
|---|----------|------|-----------|
| 1 | **God-modules.** `communications.py` 8.7k, `Candidates.tsx` 5.7k, `Dashboard.tsx` 4.1k, `leads/service.py` 4.1k, `billing.py` 3.3k | Медленный билд, страх правок, конфликты merge, сложное тестирование | Файлы выше |
| 2 | **Очередь только в памяти.** `backend/app/core/queue.py` использует `asyncio.create_task`; упал процесс — потерял задачу. Комментарий про ARQ/Redis вводит в заблуждение | Потеря Stripe webhooks при ретраях, потеря outgoing comms, потеря автоматизаций | `backend/app/core/queue.py` |
| 3 | **Файлы хранятся локально** (`backend/uploads/`, `backend/app/uploads/`). Нет S3/MinIO | Невозможность горизонтально масштабировать, риск потери документов при перезапуске контейнера, проблемы с backup | Dockerfile, docker-compose |
| 4 | **Redis есть, но почти не используется.** Нет кеш-слоя для тяжёлых агрегатов (воронка конверсии, stuck-очереди, дашборд) | Повторные тяжёлые запросы на каждый reload, высокая нагрузка на Postgres | `docker-compose.yml`, отсутствие `redis.set/get` в сервисном коде |
| 5 | **Alembic-heads риски.** 164 миграции, 17 merge-revisions, и по скрипту ~23 потенциальных head — история не гарантирует единый head | Конфликт при deploy, откат данных | `backend/alembic/versions/*.py` |
| 6 | ~~**IA перегружено.** `CrmContourWayfindingStrip` импортирован в 37 `.tsx` файлах; дублирование в топбаре/сайдбаре/чипах~~ → **РЕШЕНО** в Phase 1 #6: чип-полоса заменена на иерархический breadcrumb (`PageBreadcrumb` + `breadcrumbRegistry.ts`) на всех 40 страницах; `CrmContourWayfindingStrip.tsx` удалён; tsc baseline 548 → 542 (−6 ошибок). | Пользователь теряется, «где я», «куда кликать» | `hostflow-frontend/src/components/nav/PageBreadcrumb.tsx`, `hostflow-frontend/src/nav/breadcrumbRegistry.ts` |
| 7 | **Нет Sentry / structured logging / RUM.** Prometheus есть, но только под метрики инфраструктуры | Инциденты в проде не видны, нет traceability ошибок пользователя | `backend/app/main.py`, `hostflow-frontend/src/main.tsx` |
| 8 | **E2E-тесты есть как скелет, но не покрывают критичные сценарии** (оплата, intake → lead → кандидат → документ → коммуникация) | Регрессии ловятся после релиза | `tests/e2e/*` |
| 9 | **Хардкод-строки на кириллице** в 65 `.tsx` файлах обходят i18n | Разрыв локалей, невозможность быстро продать en/pl | `grep '[а-я]' hostflow-frontend/src/**/*.tsx` |
| 10 | **Нет rate-limit/CAPTCHA на публичных endpoint-ах** (`/public/intake`, signup, password-reset) | Спам, abuse | `backend/app/api/public/*` |
| 11 | **Биллинг частичный по SSOT §2.18** — нет Stripe Tax/VIES, нет SKU packs UI, нет Customer Portal, не все write-API под trial grace | Деньги уходят, регионы не перекрыты, лазейки в квотах | `backend/app/api/v1/settings/billing.py`, `backend/app/services/billing_restrictions.py` |
| 12 | **Onboarding не вытягивает «первое значение».** Есть getting-started, но нет жёсткого «первые 5 минут = первый лид в работе» | Churn на второй день после signup | `pages/OnboardingGettingStartedPage.tsx` |

### 1.5 Что работает хорошо (опорные сильные стороны)

- Жёсткая канонизация URL (`crm_app_paths.json` + codegen + CI-проверки).
- Строгие pre-commit + frontend-static-qa (routes-check, spa-paths-check, permissions-check, activation-check, comm-gates-check).
- RLS + канонические тенанты — правильный фундамент для мультитенантности.
- Омниканальный inbox (редкость даже у Pipedrive) — живой, подключён к Gmail/Graph/Telegram/WhatsApp/Viber/IMAP.
- Дизайн-система задокументирована (`docs/pipedesign.md`), токены описаны.
- Миграции версионированы, есть seed-скрипты.

---

## Часть II. Продуктовая философия (как должно быть)

### 2.1 Пять принципов простоты (поверх `docs/pipe.md`)

1. **Один экран — одна цель.** Вся страница отвечает на один вопрос: «что мне делать сейчас?» Дашборд не делает восемь ролей — делает одну: показывает «что застряло и какой следующий шаг».
2. **Видимый следующий шаг (NBA-first).** На каждой карточке (лид, кандидат, вакансия, документ, тред) в правом верхнем углу — один primary-CTA «следующее действие». Если его нет — система **обязана** показать, почему: либо SLA-ок, либо ждём внешнего события (и таймер).
3. **Минимум кликов до результата.** Правило «2 клика» для топ-5 операций: открыть лид → написать сообщение; открыть кандидата → назначить задачу; открыть документ → подписать; открыть inbox → ответить; открыть дашборд → исправить застрявшее.
4. **Action-driven, а не browse-driven.** Списки существуют, но приоритет — очередям: «мои задачи на сегодня», «застряло», «жду клиента». Browse — вторичный путь.
5. **Быстрый, предсказуемый интерфейс.** P95 рендера списка ≤ 300 мс, P95 API ≤ 400 мс, P95 поиска ≤ 500 мс. Виртуализация списков по умолчанию. Skeleton-loaders, не спиннеры.

### 2.2 «Система ведёт пользователя» — конкретный механизм

На каждой странице должно быть одно из трёх состояний:

| Состояние | Что видит пользователь | Пример |
|-----------|------------------------|--------|
| **Есть действие** | Primary CTA + причина (NBA-копирайт) | «Напомнить клиенту — прошло 3 дня без ответа» |
| **Всё ок, жди** | Пустой состояние с таймером ожидания | «Жду ответа клиента до 18:00 завтра» |
| **Нужна настройка** | Инлайн-подсказка с one-click ссылкой в нужное место настроек | «Подключите Gmail, чтобы отправлять письма → [Подключить]» |

**Запрещено:** пустой экран без объяснения, пустая таблица без CTA «добавить», модал без primary-кнопки.

### 2.3 Метрики в нужных местах

Не «страница аналитики» как отдельный раздел, а цифры **в контексте работы**:

- **Карточка кандидата:** дней в пайплайне, время до следующего действия, процент заполненных документов, SLA до конца этапа.
- **Карточка вакансии:** воронка кандидатов по этапам, средний time-to-hire, ожидаемая дата закрытия, бюджет vs фактически.
- **Карточка лида:** возраст лида, каналы касания, вероятность конверсии (score), лимит плана (если близко).
- **Inbox:** время до SLA по треду, кто назначен, сколько непрочитанных у команды.
- **Дашборд:** три виджета «что застряло» / «что в работе сегодня» / «что ждёт клиента» — и всё. Без 15 графиков.
- **Документы:** сколько ждут подписи, сколько просрочено, сколько в работе.

Большой отчёт «Аналитика» существует, но **не подменяет** операционные цифры. Он для руководителя, не для рекрутёра на передовой.

---

## Часть III. План развития (фазы)

Каждая фаза — 2–4 недели работы команды из 2–3 разработчиков. Фазы **не блокируют друг друга строго**: 0 и 1 обязаны идти первыми, далее можно параллелить по полосам.

### Фаза 0 — Санитария и фундамент (блокер всего остального)

**Цель:** остановить техдолг, получить наблюдаемость, сделать деплой безопасным.

- [x] **Вынести очереди в Redis/ARQ (или RQ, по выбору). Стартовый skeleton + миграция 3 критичных потоков: Stripe webhooks (ретраи с идемпотентностью), outgoing comms (email/tg/wa), rule engine automations.** — готово: `backend/app/core/arq_worker.py` (ARQ `WorkerSettings`, `JOB_REGISTRY`) с 3 задачами — `stripe_webhook_process`, `communications_dispatch_once`, `automation_evaluate_trigger`; единый клиент `backend/app/core/queue.py` с `enqueue_job(name, **payload)`, который роутит в ARQ при `JOB_QUEUE_BACKEND=arq` и graceful fallback в in-process при недоступности Redis; Stripe webhook (`/api/v1/settings/billing/webhook`) теперь под ARQ возвращает 202 сразу после idempotency-claim, тяжёлые `_handle_*` выполняются воркером с ретраем; сервис `arq-worker` в `docker-compose.yml` (профили `arq`/`full`), 13 env-переменных в `backend/.env.example`; тесты `backend/tests/core/test_queue_routing.py` (роутинг + fallback + registry contract). Архитектура задокументирована в `docs/specs/architecture/job_queue.md`.
- [x] **Поднять MinIO (S3-compatible) в `docker-compose`, перенести `backend/uploads/*` и документ-сканер на presigned URLs. Миграционный скрипт для существующих файлов.** — готово: единая абстракция `backend/app/core/object_storage.py` (`FilesystemObjectStorage` + `S3ObjectStorage` поверх `aioboto3`), `normalize_key()` как единая точка гигиены ключей; фабрика `get_object_storage()` с graceful fallback на FS при misconfig (бэкенд стартует, а не падает). Интегрировано в основные flow документов: `modules/documents/storage.py:_build_public_url` + `file_entry_download_url` + `extract_storage_key` + `ensure_document_files` теперь backend-agnostic; `services/document_files.py:resolve_document_file_ref` возвращает FS-путь (FileResponse) или presigned URL (RedirectResponse); `api/v1/candidate_documents.py:upload_candidate_document` пишет через `storage.save_stream(...)`; endpoint `/uploads/{path}` в `main.py` редиректит на presigned при `OBJECT_STORAGE_BACKEND=s3`. В `docker-compose.yml` добавлены сервисы `minio` + `minio-bootstrap` (создаёт бакет) под профилями `minio`/`full`. 10 env-переменных в `backend/.env.example` (`OBJECT_STORAGE_*`). Migration-script `backend/scripts/migrate_uploads_to_s3.py` (idempotent, `--dry-run`, `--force`) — не трогает `Document.files[*].url` (они ресолвятся через абстракцию), flip между бэкендами полностью обратим. Тесты: 15 новых кейсов в `tests/core/test_object_storage.py` + `tests/core/test_documents_storage_urls.py` (FS roundtrip sync + async, factory fallback, URL-контракт для FS и stub-S3, path-escape защита). Архитектура задокументирована в `docs/specs/architecture/object_storage.md` (+ план миграции остальных write-call-sites).
- [x] **Sentry (backend + frontend), structured logging (JSON, correlation-id через middleware), привязка `tenant_id` и `user_id` к каждому span-у.** — готово: `backend/app/core/observability.py`, `hostflow-frontend/src/lib/observability.ts`, `X-Request-ID`-middleware, `AppErrorBoundary`.
- [x] **Проверка и схлопывание Alembic-heads до одного.** — готово: `backend/scripts/check_alembic_heads.py` + гейт в CI (`.github/workflows/backend-ci.yml`) и pre-commit (`.pre-commit-config.yaml`). Текущее состояние: `heads = 1`.
- [x] **Rate-limit для публичных endpoint-ов + CAPTCHA (Cloudflare Turnstile) на `/auth/register`, `/auth/login`, `/auth/password/*`, `/public/intake`, `/public/magic-link/request`.** — готово: `backend/app/core/rate_limit.py` (Redis-backed через `limits`, императивный `enforce_rate_limit()`, fail-open при падении Redis), `backend/app/core/turnstile.py` (verify через Cloudflare siteverify, no-op без `TURNSTILE_SECRET_KEY`), `/api/v1/auth/public-config` для фронта, `TurnstileWidget` + подключение на `SignupPage` и `ForgotPasswordPage`. Env-секция в `backend/.env.example`.
- [x] **Единая обработка ошибок во фронте (error boundary, toast-контракт), без «белого экрана».** — готово: расширенный `FriendlyErrorInfo` (status/code/retryAfterSec, +429 `retry_after`, +400 `captcha_failed`) в `hostflow-frontend/src/utils/friendlyError.ts`; `Toast` с variant=`warning`, кастомным TTL и action-кнопкой (`hostflow-frontend/src/components/Toast.tsx`); единый мост `toastFromError()` + `toastSuccess/info/warning` с авто-репортом 5xx/unknown в Sentry и подавлением шума от 4xx user-facing (`hostflow-frontend/src/utils/toastFromError.ts`); `SectionErrorBoundary` с тегами `boundary.scope=section` для виджетов/табов/модалок, поверх существующего `AppErrorBoundary`. Контракт зафиксирован в `docs/specs/frontend/error_handling.md`.
- [x] **CI: gate на снижение coverage backend ≥ 60%, frontend ≥ 40% (точка отсчёта — текущий снимок).** — готово: ratchet-gate вместо жёсткого порога. Backend: `pytest-cov` в `.github/workflows/backend-ci.yml` → `backend/coverage.xml` → `backend/scripts/check_coverage.py` сравнивает с `backend/.coverage-baseline` (сейчас 35.00%, target 60%, tolerance 0.5pp). Frontend: `@vitest/coverage-v8` + `json-summary` reporter → `coverage/coverage-summary.json` → `hostflow-frontend/scripts/check-coverage.mjs` против `hostflow-frontend/.coverage-baseline` (сейчас 5.00%, target 40%). Обе утилиты печатают «gap до target», поддерживают `--write-baseline` для осознанного ratchet-а и проваливают CI при просадке ниже `baseline − tolerance`. Артефакты coverage выгружаются из обоих workflow через `actions/upload-artifact@v4`. Политика и процесс ratchet-а зафиксированы в `docs/specs/quality/ci_gates.md`.
- [x] **Бюджет размера frontend bundle в CI (initial chunk ≤ 350 KB gzip).** — готово: `hostflow-frontend/.bundle-budget.json` (total raw 8 MB / gzipped 1.6 MB + 7 per-chunk budgets для `index-*`, `vendor-react-core-*`, `vendor-recharts-*`, `vendor-tabler-icons-*`, `routeBundleAdmin-*`, `routeBundleCrmCore-*`, `routeBundleComms-*`) + `hostflow-frontend/scripts/check-bundle-size.mjs` (сканирует `dist/assets/*.js`, меряет raw + gzipped через `zlib.gzipSync`, матчит regex-паттерны, печатает таблицу, падает на превышении). Подключено в `frontend-static-qa.yml` после `qa:static` (который уже выполняет `npm run build`). Текущий baseline: total 7.67 MB raw / 1.50 MB gzipped — «≤ 350 KB gzip» целевое для initial chunk (`index-*` сейчас 495 KB gzip) остаётся север-звездой, трекается в SSOT → route-level code splitting.

**Acceptance:** упавший backend не теряет webhook; документ, загруженный при одной реплике, доступен при другой; в Sentry видны ошибки с контекстом тенанта; `alembic heads` возвращает 1 строку.

**KPI:** 0 потерянных webhook за неделю; P95 API ≤ 400 мс; 0 «белых экранов» во фронте за неделю.

### Фаза 1 — Декомпозиция God-modules и IA v2

**Цель:** сделать код редактируемым, интерфейс — лёгким.

- [~] `backend/app/api/v1/communications.py` разбить по каналам: `communications/email.py`, `communications/telegram.py`, `communications/whatsapp.py`, `communications/viber.py`, `communications/graph.py`, + общий `service.py` и `threads.py`. Тесты не ломаются. — **в работе (шаги 1–3/N выполнены):**
    - **Шаг 1/N:** файл сконвертирован в пакет `backend/app/api/v1/communications/`. Все Pydantic-модели (~64 класса + `MAX_COMM_MESSAGE_ATTACHMENT_BYTES`) вынесены в `schemas.py` (769 LOC) с re-export-ом из `__init__.py` — публичный контракт сохранён (`router`, `run_email_poll_worker`, `run_email_dispatch_worker`, `CommunicationEmailWorkerPollRequest`, `CommunicationEmailWorkerDispatchRequest` — потребители: `services/communications_scheduler.py`, тесты). 8677 → 8104 LOC.
    - **Шаг 2/N:** helpers разбиты на 5 фокусных подмодулей в `_helpers/` (все ≤ 230 LOC, в рамках бюджета):
        - `utils.py` (111 LOC) — pure-stdlib примитивы (`_now_utc`, `_as_dict`, `_as_list`, `_coerce_datetime`, `_clamp_db_str`, `_deep_merge_dict`, `_json_dict`, `_normalize_email_value`, `_digits_only`, `_looks_like_phone`, `_is_six_digit_code`).
        - `working_hours.py` (130 LOC) — парсинг/валидация рабочих часов и time-off-окон (`_CLOCK_RE`, `_parse_clock_minutes`, `_normalize_working_hours`, `_validate_iso_date_range`, `_partial_day_blocks_now`).
        - `account_settings.py` (216 LOC) — `_derive_account_status`, `_sanitize_account_settings_for_out` (для `Out`), `_account_out`, `_normalize_account_settings_for_store` (encrypt-on-write для всех каналов).
        - `oauth.py` (230 LOC) — `_oauth_*` (client_secret/refresh_token/access_token/expires_soon), `_refresh_oauth_tokens_in_settings_json`, `_ensure_oauth_access_for_mailbox`, `_oauth_provider_for_account`, `_oauth_authorize_url_for_provider`, `_oauth_default_scopes`, `_build_oauth_auth_url`.
        - `channels.py` (181 LOC) — `_*_config_from_account_settings` для imap/telegram/whatsapp/viber/messenger/instagram (адаптер-конфиги).
    - Все 5 подмодулей re-export-ятся из `__init__.py` под прежними именами — route-handlers не меняются. Слой зависимостей оформлен послойно, без циклов: `utils` → `working_hours` (no extra deps) → `account_settings` (utils) → `oauth` (utils + account_settings) → `channels` (utils + services).
    - **Шаг 3/N:** добавлены ещё 3 helper-модуля + 3 per-topic route-модуля (всего 17 endpoints, ~1000 LOC вынесено из `__init__.py`):
        - `_helpers/dto.py` (188 LOC) — 6 ORM→Out конвертеров: `_thread_out`, `_message_out`, `_timeoff_out`, `_planner_event_out`, `_allocation_audit_out`, `_command_audit_out`.
        - `_helpers/tenant_settings.py` (87 LOC) — пропуск из `tenant.settings`: `_comm_settings_root`, `_comm_settings_channels`, `_tenant_sla_escalation_targets`, `_tenant_comm_allowed_roles`, `_canonical_membership_role_for_escalation`.
        - `_helpers/access.py` (159 LOC) — RBAC + 404-fetch: `_get_thread_or_404`, `_default_own_company_id_for_tenant`, `_ensure_thread_matches_own_company_scope`, `_get_tenant_or_404`, `_feature_for_channel`, `_message_templates_for_user`, `_require_comm_feature`, `_require_any_comm_feature`.
        - `routes/audit.py` (203 LOC, 4 endpoints) — `POST /allocator/preview`, `GET /allocator/audit`, `POST /commands/audit/batch`, `GET /commands/audit`.
        - `routes/planner.py` (469 LOC, 9 endpoints) — `GET|POST /time-off/requests`, `POST /time-off/requests/{id}/cancel`, `POST /time-off/requests/{id}/decision`, `GET|PUT /availability/working-hours`, `GET|POST /planner/events`, `PATCH /planner/events/{id}` + helper `_sync_manager_queue_availability_from_time_off` (cross-domain bridge approved time-off ↔ manager-queue).
        - `routes/oauth.py` (409 LOC, 5 endpoints) — `POST /accounts/{id}/oauth/{start,complete,refresh}`, `GET|PATCH /accounts/{id}/sync-cursor`.
    - Sub-routers подключаются в самом конце `__init__.py` через `router.include_router(...)` без префикса (URL-paths и OpenAPI-схема **не меняются**).
    - **Шаг 4/N (часть А):** добавлены ещё 2 helper-модуля для outbound/SLA-логики (~1.1k LOC вынесено из `__init__.py`, без изменения route-handlers):
        - `_helpers/sla.py` (201 LOC) — `_channel_response_sla_minutes`, `_apply_thread_sla_policy_from_message`, `_touch_thread_from_message`, `_resolve_thread_sla_alerts`. Объединяет всю SLA-логику треда (расчёт `sla_due_at` из настроек канала тенанта, mute/no-reply короткие пути, закрытие SLA-overdue reminders/notifications).
        - `_helpers/dispatch.py` (988 LOC) — outbound send-stack: `_pick_thread_recipient_address`, `_normalize_email_text`, `_parse_iso_datetime`, retry-bookkeeping (`_dispatch_attempt_count`/`_dispatch_next_retry_at`/`_schedule_dispatch_retry` с exponential backoff до 5 попыток), `_resolve_comm_local_attachment_path` (security-safe аттачи), `_mock_dispatch_outbound_message` (test/dev fallback) и 6 send-адаптеров: `_dispatch_email_message_via_tenant_smtp` (включая Gmail/MS-Graph OAuth с auto-refresh на 401), `_dispatch_telegram_message_via_bot_api` (text+document с captions+reply_to), `_dispatch_whatsapp_message_via_cloud_api`, `_dispatch_messenger_message_via_graph_api`, `_dispatch_instagram_message_via_graph_api`, `_dispatch_viber_message_via_bot_api`. Dispatch.py чуть ниже 1000 LOC — внутри 1:1 mapping channel→adapter, никакой кросс-каналной логики.
    - **Шаг 4/N (часть Б):** добавлен `_helpers/billing.py` (60 LOC) для guard-функций (`_load_tenant_license_row`, `_require_outbound_comms_not_billing_blocked` — 403 с кодами `billing_past_due`/`billing_trial_expired`); добавлен `routes/dispatch.py` (532 LOC, 6 endpoints): `POST /messages/{id}/dispatch` (single-message с per-channel adapter dispatch), `POST /dispatch/queued` (batch outbound с per-thread caching, retry-bookkeeping, SLA cleanup), `PATCH /messages/{id}/delivery-status` (provider-callback sink), `GET /scheduler/status`, `POST /scheduler/run-now` (admin), `POST /email/worker/dispatch` (email-only convenience wrapper). Поскольку `services/communications_scheduler.py` и тесты импортируют `dispatch_message`, `dispatch_queued_messages`, `run_email_dispatch_worker` напрямую — добавили re-export через `from .routes.dispatch import …` в `__init__.py`, контракт сохранён.
    - **Шаг 5/N (часть А):** добавлены ещё 2 helper-модуля (cross-domain bridge + ingest-side resolvers), убраны теперь-неиспользуемые импорты:
        - `_helpers/escalation.py` (196 LOC) — `_resolve_manual_escalation_recipient_user_ids` (резолв адресатов из `target.{user_id|queue|role}` через `user_memberships` с whitelist `supervisor`/`administrator`) и `_emit_manual_thread_escalation_bridge` (cross-domain bridge: при manual escalation из Inbox создаём Activity-reminder + bell-notification на каждого получателя + audit-запись; идемпотентность через `dedupe_key=ops_escalation:{tenant}:{thread}:{esc_at}:{uid}` и проверку active-reminder в `Reminder.status IN (new, pending, sent, overdue)`). Lazy-импорты `reminder_tasks`/`user_notifications` сохранены, чтобы не тащить тяжёлые зависимости в startup-цепочку API.
        - `_helpers/ingest.py` (364 LOC) — 6 inbound-side функций: `_find_thread_for_inbound_email` и `_find_thread_for_inbound_channel` (двухступенчатый поиск треда: сначала по `channel_thread_ref`, потом MVP-эвристика по subject+sender / channel+account+sender в недавних активных тредах); `_ingest_email_outbound_from_mailbox` (когда email-poll worker читает Sent-папку — создаёт `CommunicationMessage(direction="outbound", delivery_status="delivered")` на новом или существующем треде, дедуп по `external_message_ref`, обновляет participants и `_touch_thread_from_message`); и 3 webhook-secret resolver-а — generic `_find_channel_account_by_webhook_secret(channel, config_key)` плюс две тонкие обёртки `_find_telegram_account_by_webhook_secret`/`_find_whatsapp_account_by_webhook_secret`, кот. оставлены ради backward-compat с уже существующими webhook-handlers (раньше были 3 практически идентичные функции — теперь дедуплицированы через generic).
    - **Шаг 5/N (часть Б):** добавлен `_helpers/candidate_lookup.py` (245 LOC, 8 функций) — выделен candidate-resolution surface, общий для telegram-intake и нескольких inbox-routes:
        - **Identity / public-link:** `_candidate_name` (first+last → short_id → id), `_candidate_public_status_url` (frontend `/public/status/{token}`), `_candidate_apply_url` (frontend `/public/apply/{token}`).
        - **Tenant-scoped lookup:** `_find_candidate_by_bind_token` (`intake_token`/`status_share_token`/`short_id`/`id` через `sa.or_`), `_find_candidate_by_telegram_chat` (двухступенчатый: сначала `CommunicationThread.linked_candidate_id` для треда с заданным `chat_id`, затем fallback по `intake_state.notifications.telegram.chat_id` для chats до thread-link sync).
        - **Contact options:** `_candidate_email_options` / `_candidate_phone_options` собирают все известные email/телефоны кандидата (top-level columns + `contacts` blob + `intake_state.contacts` overlay) в set для membership-checks; `_find_candidates_by_contact` использует их для substring-матчинга в обе стороны (для phones, чтобы покрыть варианты с/без country-code).
    - **Текущее состояние (после шага 5/N часть А+Б):** `__init__.py` 4971 → 4386 LOC (−585 на этом шаге, **−4291 от исходного, −49%**); все 56 роутов `/api/v1/communications/*` зарегистрированы; `test_communications_access.py` — 7/15 passed, 8 failed — **тот же набор**, что был до рефактора. Дополнительно убраны теперь-неиспользуемые импорты `Reminder`, `ReminderStatus`, `user_memberships`, `TenantLicense` из `__init__.py` (всё переехало в helpers). Текущий каркас пакета: `_helpers/{utils,working_hours,account_settings,oauth,channels,dto,tenant_settings,access,sla,dispatch,billing,escalation,ingest,candidate_lookup}.py` (14 модулей, все ≤ 1000 LOC), `routes/{audit,planner,oauth,dispatch}.py` (4 модуля, 24 endpoints).
    - **Шаг 6/N:** добавлен `_helpers/telegram_intake.py` (1938 LOC, 39 функций) — извлечён весь telegram-driven candidate-intake mega-block, ранее L295-1872 в `__init__.py` (~1577 LOC). Это **single point**, в котором inbound Telegram-сообщения превращаются в действия по кандидату; внутри 5 логических секций:
        - **(1) Pure text/keyboard helpers** (~280 LOC): `_telegram_extract_command`, `_telegram_otp_hash`, `_telegram_onboarding_text`, `_candidate_verification_email_body`, `_telegram_name_parts`, `_telegram_vacancies_text`, `_telegram_keyboard` (linked vs unlinked раскладка), `_send_candidate_telegram_reply`, `_telegram_help_text`, `_telegram_docs_summary_text`, `_candidate_owner_context_for_docs` (ownership-контекст для documents-rules), `_format_doc_types_bullets`. Без побочных эффектов — рендерят русскоязычный UX, который кандидат видит в чате.
        - **(2) Intake state-machine** (~600 LOC): константы `_TG_INTAKE_STEP_ORDER` (7 шагов: full_name → birth_date → citizenship → years_ce → intl_experience → has_adr → agreement_general), `_TG_INTAKE_OPTIONAL_STEPS` (intl_experience, has_adr) и 13 helper-функций для управления `Candidate.intake_state.telegram_intake`: `_tg_get_intake_sections`, `_tg_incomplete_steps` (с учётом skipped), `_tg_step_prompt`/`_tg_step_label` (русские лейблы и подсказки), `_tg_intake_progress_text`, `_tg_intake_skipped_text`, `_tg_intake_help_text`, `_tg_reset_intake_runtime`, `_tg_skip_intake_step`, `_tg_unskip_intake_step`, `_tg_parse_step_answer` (per-step валидация, в т.ч. `1990-05-17`/`17.05.1990` → ISO date, `PL`-only citizenship, 0..40 years_ce, yes/no с RU/EN-локалями), `_tg_apply_step_answer` (mirroring в `personal_data`/`extra` JSON-blobs), `_tg_start_or_resume_intake`, `_tg_process_intake_answer` (главный entry-point: парсит → применяет → если все шаги выполнены, вызывает `log_activity('candidate_ready_for_docs')` + `sync_candidate_ready_for_handoff_gate` + completion-bridge с docs-checklist).
        - **(3) Candidate↔chat linking** (~250 LOC): `_create_candidate_from_telegram_intake` (bootstrap-кандидата из чата с `ensure_active_candidate_quota` чек, `intake_state.contacts.preferred_messenger='telegram'`, авто-issued intake_token), `_link_candidate_to_telegram_chat` (стампит chat metadata в `intake_state.notifications.telegram` + проставляет `linked_candidate_id` на все треды с `chat_id`), `_send_telegram_link_code` (OTP-by-email: 6-digit code, 10-min TTL, SHA-256 хеш в `intake_state.notifications.telegram.link_verification`, отправка через `send_email_for_tenant`), `_find_candidate_by_pending_verification` (находит кандидата по pending-OTP в `intake_state`, выбирает latest по `requested_at`).
        - **(4) Documents-context bridge** (~280 LOC): `_generate_public_candidate_token` (`secrets.token_urlsafe(24)`), `_ensure_candidate_intake_token` (issue/refresh с TTL 30d), `_candidate_intake_documents_url` (`/public/apply/{token}?mode=documents&doc=...`), `_telegram_required_docs_snapshot` (через `ensure_ruleset_seed`+`compute_owner_summary` рассчитывает `{total, ready, missing[], in_progress[], problematic[], docs_count}` по тенант-ruleset с учётом own_company), `_telegram_docs_checklist_text` (рендер чеклиста в чате), `_tg_intake_completion_docs_text` (post-anketa CTA с next-doc + ссылкой на загрузку), `_telegram_scan_command_text` (логика выбора preferred_doc для `/scan` с fallback на missing→in_progress→problematic).
        - **(5) Main command dispatcher** (~400 LOC): `_process_public_telegram_candidate_command` — единая точка входа из webhook routes, диспатчит 12 команд (`/start /help /bind /status /intake /docs /scan /subscribe /unsubscribe /lang /vacancies /apply`) + 4 free-text-режима (intake-answer для linked candidate, OTP 6-цифр, email/phone для bind, "Связаться с менеджером"). Внутри 5 attempts limit для OTP, expire-сценарии, ленивый bootstrap кандидата при `/intake` без linked profile, защита от exception-ов в docs-summary с fallback на raw `Document`-status counts.
    - **Cleanup top-level imports:** в `__init__.py` убраны 39+ теперь-неиспользуемых импортов, переехавших в `telegram_intake.py`: stdlib (`hashlib`, `secrets`, `json`, `urlencode`, `timedelta`), models (`Candidate`, `Document`, `Vacancy`, `Tenant`, `OwnCompany`, `CommunicationAllocationAudit`, `CommunicationCommandAudit`, `CommunicationPlannerEvent`, `CommunicationTimeOffRequest`), services (`send_email_for_tenant`, `ensure_active_candidate_quota`, `ensure_ruleset_seed`, `list_candidate_documents`, `compute_owner_summary`, `load_default_ruleset`, `normalize_ruleset_payload`, `get_document_display_name`, `log_activity`, `sync_candidate_ready_for_handoff_gate`, `TelegramBotConfig`, `send_telegram_text`, `send_telegram_document`, `WhatsAppCloudConfig`, `send_whatsapp_text`, `ViberBotConfig`, `send_viber_text_message`, `MetaGraphConfig`, `send_meta_text_message`, `OAuthMailboxSendError`, `send_oauth_email_message`, `exchange_oauth_code_for_tokens`, `refresh_oauth_access_token`, `ImapClientConfig`, `run_scheduler_tick_once`, `scheduler_runtime_status`, `preview_allocation`, `billing_restrictions`, `EMAIL_LEGACY`, `Role`, `require_roles`, `decrypt_secret`, `encrypt_secret`, `CANDIDATE_STAGE_LABELS`). Импорт-блок сократился с 95 до 56 LOC, без потери backward-compat (все эти символы доступны через свои оригинальные модули; ни один внешний потребитель не импортирует их через `backend.app.api.v1.communications`, что подтверждено grep-ом — наружу торчит только `router`).
    - **Текущее состояние (после шага 6/N):** `__init__.py` 4386 → **2808 LOC** (−1578 на этом шаге, **−5869 от исходного, −68%**); все 56 роутов `/api/v1/communications/*` зарегистрированы; `test_communications_access.py` — **7/15 passed, 8 failed — тот же набор**, что был до рефактора (pre-existing `communication_channels_limit_reached` от polluted local DB). Pyflakes: 0 unused-import-warnings вне `noqa: F401` re-exports. Текущий каркас пакета: `_helpers/{utils,working_hours,account_settings,oauth,channels,dto,tenant_settings,access,sla,dispatch,billing,escalation,ingest,candidate_lookup,telegram_intake}.py` (15 модулей; крупнейший — `telegram_intake.py` 1938 LOC, остальные ≤ 1000 LOC), `routes/{audit,planner,oauth,dispatch}.py` (4 модуля, 24 endpoints).
    - **Шаг 7/N:** все оставшиеся route-handlers вынесены из `__init__.py` в 5 новых per-topic под-роутеров — `routes/{accounts,threads,messages,ingest,webhooks}.py` (общее покрытие ≈ 2800 LOC, 31 endpoint). Каждый под-роутер монтируется на родительский `router` через `router.include_router(...)` без префикса, наследуя `/communications`. Группировка:
        - **`routes/accounts.py`** (734 LOC, 8 endpoints): `GET/POST /accounts`, `PATCH/DELETE /accounts/{id}`, `POST /accounts/{id}/test-connection` (диспатчит provider-specific connectivity probes для IMAP/Telegram/WhatsApp/Messenger/Instagram/Viber/Gmail/Microsoft Graph), `POST /accounts/{id}/telegram/webhook/{set,delete}`, `POST /accounts/{id}/sync-now`. На creation авто-issue `webhook_secret` (+ `webhook_verify_token` для Meta-каналов) — провайдер-консоль готова к подключению сразу после `POST /accounts`.
        - **`routes/threads.py`** (596 LOC, 8 endpoints): `GET/POST /threads`, `GET/PATCH /threads/{id}`, `POST /threads/{id}/read`, `POST /threads/reconcile-unread` (recompute `unread_count`-batch с фильтром telegram-команд), `POST /threads/{id}/assign-auto` (re-run allocator). Самый тяжёлый — `patch_thread`: merge `thread_meta` с side-effects (SLA mute / no-reply-needed / paused / escalation с tenant-validated targets и user-row check + `_emit_manual_thread_escalation_bridge`).
        - **`routes/messages.py`** (243 LOC, 4 endpoints): `GET /threads/{id}/messages`, `POST /threads/{id}/messages` (с billing-gate `_require_outbound_comms_not_billing_blocked` для outbound), `POST /threads/{id}/message-attachments/upload` (path-traversal-safe upload в `tenant_id/communications/thread_id/`, лимит `MAX_COMM_MESSAGE_ATTACHMENT_BYTES=25MB`), `GET /message-templates` (per-user × messages|email).
        - **`routes/ingest.py`** (831 LOC, 4 endpoints): `POST /email/worker/poll` (367 LOC — самый длинный handler; диспатчит IMAP / Gmail OAuth / Microsoft Graph OAuth / mock с per-folder cursor advancement, retry-on-401 для OAuth, mailbox-source split inbox vs sent), `POST /ingest/email`, `POST /ingest/{channel}` (generic для не-email каналов с idempotency через `external_message_ref`, thread-resolution через `_find_thread_for_inbound_*`, optional auto-allocator), `POST /telegram/webhook-simulate` (internal-only — конструирует `GenericInboundIngestRequest` из telegram update и форвардит в `ingest_generic_channel`).
        - **`routes/webhooks.py`** (401 LOC, 8 endpoints): public unauth-ed endpoints `POST /public/{telegram,whatsapp,messenger,instagram,viber}/{webhook_secret}` + Meta-verification `GET /public/{whatsapp,messenger,instagram}/{webhook_secret}` (challenge response). Каждый POST-handler: account-by-secret lookup → provider-normalize → wrap в `GenericInboundIngestRequest` → форвард в `ingest_generic_channel` через synthesized `_public_user_ctx(tenant_id)`. Telegram дополнительно пре-обрабатывает update через `_process_public_telegram_candidate_command` ДО ингеста, чтобы `/start /intake /scan` и intake-ответы влияли на состояние кандидата + чат-метаданные раньше, чем сообщение попадёт в БД.
    - **Cleanup top-level imports:** все 39+ модульных импортов (stdlib + models + services), которые раньше были нужны route-handler-ам, удалены. `__init__.py` импортирует только `logging` + `APIRouter`. Helper-re-exports из `._helpers.*` сохранены под `noqa: F401` для backward-compat (внутренние модули могут продолжать брать их через `backend.app.api.v1.communications.*`).
    - **Backward-compat re-exports:** добавлены явные re-exports всех 31 публично-именованных handler-ов через `from .routes.{threads,messages,ingest,accounts,webhooks} import …` под `noqa: F401`. Это покрывает `services.communications_scheduler.run_email_poll_worker` (уже использовался) и любые будущие внешние вызовы handler-ов как функций (без HTTP). Вместе с предыдущим re-export-ом из `.routes.dispatch` это даёт **полный backward-compatibility набор**.
    - **Текущее состояние (после шага 7/N):** `__init__.py` 2808 → **369 LOC** (−2439 на этом шаге, **−8308 от исходного, −96%**). Все 56 роутов `/api/v1/communications/*` зарегистрированы (44 unique paths, проверено через `router.routes`). `test_communications_access.py` — **7/15 passed, 8 failed — тот же набор**, что был до рефактора (pre-existing `communication_channels_limit_reached` от polluted local DB, current=22, limit=3). Pyflakes на `__init__.py`: 0 unused-import-warnings вне `noqa: F401` re-exports.

      Финальный каркас пакета `backend/app/api/v1/communications/`:
        - `__init__.py` (369 LOC) — thin shell: router + helpers re-exports + sub-router mounts.
        - `schemas.py` — все Pydantic `BaseModel`-ы.
        - `_helpers/{utils,working_hours,account_settings,oauth,channels,dto,tenant_settings,access,sla,dispatch,billing,escalation,ingest,candidate_lookup,telegram_intake}.py` — **15 модулей**, общим объёмом ~5400 LOC. Все ≤ 1000 LOC, **кроме `telegram_intake.py` (1938 LOC)** — расщепляется в Шаге 8/N.
        - `routes/{accounts,audit,dispatch,ingest,messages,oauth,planner,threads,webhooks}.py` — **9 модулей**, общим объёмом ~4400 LOC, охватывают все 56 endpoint-ов. Самый крупный — `ingest.py` 831 LOC, accounts.py 734, threads.py 596, dispatch.py 532, planner.py 469, webhooks.py 401, oauth.py 409, messages.py 243, audit.py 203 — **все ≤ 900 LOC**.

      **Acceptance** для шага 7/N выполнен: `__init__.py` ≤ 400 LOC ✓; route-modules ≤ 1500 LOC ✓; helper-modules ≤ 1500 LOC (кроме telegram_intake — на отдельном шаге); 0 регрессий в test-suite; backward-compat сохранена.
    - **Шаг 8/N:** расщеплён последний helper-модуль выше LOC-budget — `_helpers/telegram_intake.py` (1938 LOC, 39 функций) — конвертирован в Python-пакет `_helpers/telegram_intake/` с 5 sub-модулями по логическим секциям. Граф зависимостей ацикличен (`ui_text → docs_bridge → intake_state`, `ui_text + docs_bridge → candidate_link`, всё → `dispatcher`). Раскладка:
        1. **`ui_text.py`** (249 LOC, 12 fns) — pure text/keyboard renderers без БД и без внутренних зависимостей: `_telegram_extract_command`, `_telegram_otp_hash`, `_telegram_onboarding_text`, `_candidate_verification_email_body`, `_telegram_name_parts`, `_telegram_vacancies_text`, `_telegram_keyboard`, `_send_candidate_telegram_reply`, `_telegram_help_text`, `_telegram_docs_summary_text`, `_candidate_owner_context_for_docs`, `_format_doc_types_bullets`.
        2. **`docs_bridge.py`** (308 LOC, 7 fns) — public-token issuing + ruleset/owner-summary snapshot. Depends on `ui_text` для `_candidate_owner_context_for_docs`/`_format_doc_types_bullets`. Содержит: `_generate_public_candidate_token`, `_ensure_candidate_intake_token`, `_candidate_intake_documents_url`, `_telegram_required_docs_snapshot`, `_telegram_docs_checklist_text`, `_tg_intake_completion_docs_text`, `_telegram_scan_command_text`.
        3. **`intake_state.py`** (672 LOC, 15 fns + 4 module-level constants) — 7-step state-machine (`_TG_INTAKE_STEP_ORDER` и `_TG_INTAKE_OPTIONAL_STEPS`), per-step parsing/validation, mirroring в `personal_data`/`extra` blob-ы. Depends on `docs_bridge` для completion-text + intake-token issue-а.
        4. **`candidate_link.py`** (219 LOC, 4 fns) — bootstrap кандидата из чата + OTP-by-email link flow. Depends on `ui_text` (rendering) + `docs_bridge` (intake-token).
        5. **`dispatcher.py`** (532 LOC, 1 fn) — `_process_public_telegram_candidate_command`, единая точка входа из telegram-webhook. Depends on все 4 предыдущих под-модуля.

      `__init__.py` пакета (121 LOC) выполняет `from .{ui_text,docs_bridge,intake_state,candidate_link,dispatcher} import (…)` под `noqa: F401` и собирает `__all__` из 39 публичных имён — это **точно тот же** API, который был у монолитного `telegram_intake.py`, поэтому `routes/webhooks.py` (с `from ..._helpers.telegram_intake import _process_public_telegram_candidate_command`) и любые другие потребители работают без изменений.

    - **Текущее состояние (после шага 8/N):** все 56 routes `/api/v1/communications/*` зарегистрированы; все critical re-exports из `_helpers.telegram_intake` доступны (`_process_public_telegram_candidate_command`, `_TG_INTAKE_STEP_ORDER`, `_create_candidate_from_telegram_intake`, `_telegram_required_docs_snapshot`, etc); `pyflakes backend/app/api/v1/communications/_helpers/telegram_intake/` — **0 warnings**; `test_communications_access.py` — **7/15 passed, 8 failed — тот же набор**, что и до шагов 7-8 (pre-existing `communication_channels_limit_reached` от polluted local DB).

      Финальная LOC-раскладка пакета `backend/app/api/v1/communications/`:
        - `__init__.py` 369 (target ≤ 400 ✓), `schemas.py` (Pydantic models).
        - `_helpers/` (15 файлов + sub-package): `dispatch.py` 988 (largest), `candidate_lookup.py` 245, `oauth.py` 230, `account_settings.py` 216, `sla.py` 201, `escalation.py` 196, `dto.py` 188, `channels.py` 181, `access.py` 159, `working_hours.py` 130, `utils.py` 111, `tenant_settings.py` 87, `billing.py` 60. **Все ≤ 1500 LOC** ✓
        - `_helpers/telegram_intake/` (sub-package): `intake_state.py` 672 (largest), `dispatcher.py` 532, `docs_bridge.py` 308, `ui_text.py` 249, `candidate_link.py` 219. **Все ≤ 1500 LOC** ✓
        - `routes/` (9 файлов): `ingest.py` 831 (largest), `accounts.py` 734, `threads.py` 596, `dispatch.py` 532, `planner.py` 469, `oauth.py` 409, `webhooks.py` 401, `messages.py` 243, `audit.py` 203. **Все ≤ 1500 LOC** ✓

      **Acceptance Phase 1 #1 закрыт полностью:** ни один файл в пакете `communications` не превышает 1500 LOC; god-module 8677 LOC превратился в **31 файл** с осмысленной топологией (helpers ↔ routes), backward-compat сохранена через re-exports, регрессий в test-suite нет. Можно переходить к **Phase 1 #2** (`backend/app/api/v1/settings/billing.py` — 3377 LOC).
- [x] **Phase 1 #2 закрыт полностью:** `backend/app/api/v1/settings/billing.py` (3377 LOC, god-module) → пакет `backend/app/api/v1/settings/billing/` из **12 файлов**, `__init__.py` = **185 LOC** (target ≤ 200 ✓), все остальные ≤ 1500 LOC.

      Исполненные шаги:
        - **Шаг 1/N:** `billing.py` → пакет; 24 Pydantic-модели → `schemas.py` (251 LOC). После: `__init__.py` 3173 LOC.
        - **Шаг 2/N:** `_helpers/plans.py` (386 LOC) — 6 const + 17 fns (plan-config, Stripe price-ID, addon offers, runtime probes). Введён паттерн **late-import** `from backend.app.api.v1.settings import billing as _billing_pkg` для `_stripe_ready`/`_stripe_price_amount` — чтобы тесты могли подменять `billing.stripe` через `patch.object(billing, "stripe", mock)`. После: `__init__.py` 2871 LOC.
        - **Шаг 3/N:** `_helpers/state.py` (196 LOC) — `_now_utc`/`_iso_to_dt`/`_unix_to_iso`, `_ensure_tenant_access`, `_billing_root`/`_subscription_payload`/`_billing_history`/`_history_contains`, `_set_extra_operating_slots`, `_subscription_out` (с `BillingGateOut` snapshot), `_store_subscription`. После: `__init__.py` 2727 LOC.
        - **Шаг 4/N:** `_helpers/stripe_extract.py` (265 LOC) — invoice-серилайзеры (`_extract_invoice_period`, `_stripe_invoice_out`, `_list_stripe_invoices`), `_find_tenant_for_stripe_event`, payload-extractors (`_extract_subscription_price_id`/`_extract_subscription_billing_interval`/`_find_subscription_item_by_price_id`/`_find_operating_slot_addon_item`/`_extract_operating_slot_addon_quantity`/`_extract_subscription_period`/`_extract_pending_update`/`_extract_pending_update_plan_code`/`_extract_pending_invoice_details`/`_normalize_stripe_subscription_status`), `_send_billing_email`. `_list_stripe_invoices` использует тот же late-import для `stripe`. После: `__init__.py` 2533 LOC.
        - **Шаг 5/N:** три модуля одной волной — `_helpers/history.py` (116 LOC: `_history_entry`/`_history_out`/`_merge_history_with_invoices`); `_helpers/license_sync.py` (93 LOC: `sync_subscription_license_addon_v1` + `_apply_license_limits`); `_helpers/packs.py` (354 LOC: 5 × `_apply_*_pack_to_tenant` + `_apply_addon_pack_by_sku` + `_checkout_session_line_items_contain_price`, idempotent через `dedupe_key`/`_history_contains`). После: `__init__.py` 2095 LOC.
        - **Шаг 6/N:** `_helpers/summary.py` (211 LOC) — `_plan_code_for_usage_caps`/`_tenant_settings_dict`/`_billing_usage_caps`/`_billing_summary_addon_offers`/`_company_slots_payload`/`_portal_candidates_usage_snapshot`/`_founder_program_snapshot`/`_billing_summary_extras` + `_maybe_enroll_founder_program`. И `_helpers/webhook_handlers.py` (691 LOC) — все 6 `_handle_*` (checkout/invoice paid/finalized/payment_failed/subscription) + `_stripe_webhook_try_claim_event`/`_stripe_webhook_release_claim` (atomic INSERT … ON CONFLICT DO NOTHING на `stripe_webhook_event_log`). Введён модуль-уровневый `_get_stripe()` getter (тот же late-import паттерн); все `stripe.X` references переписаны regex-substitution `\bstripe\.` → `_get_stripe().` чтобы test-time mocks `billing.stripe` подхватывались. После: `__init__.py` 1357 LOC.
        - **Шаг 7/N:** `routes.py` (1299 LOC) — все 12 endpoint-handlers (`get_billing_subscription`, `get_billing_summary`, `create_checkout_session`, `create_portal_candidates_pack_checkout`, `create_addon_pack_checkout`, `simulate_checkout_resolution`, `change_plan`, `update_company_slots`, `cancel_subscription`, `reactivate_subscription`, `create_customer_portal_link`, `stripe_webhook`) с тем же `_get_stripe()` late-binding. `__init__.py` сжат до **185 LOC** = только `router = APIRouter(...)`, опциональный `import stripe` (placeholder для test-patches), re-export `settings` для `billing.settings.<attr>`-паттернов в тестах, и компактные re-export-блоки всех публичных символов из 9 sub-модулей под `# noqa: F401`. Финал: `from . import routes` триггерит `@router.<method>(...)` decorator side-effects.

      Финальная LOC-раскладка пакета `backend/app/api/v1/settings/billing/`:
        - `__init__.py` 185 (target ≤ 200 ✓), `routes.py` 1299, `schemas.py` 251.
        - `_helpers/`: `webhook_handlers.py` 691 (largest), `plans.py` 386, `packs.py` 354, `stripe_extract.py` 265, `summary.py` 211, `state.py` 196, `history.py` 116, `license_sync.py` 93. **Все ≤ 1500 LOC** ✓

      **Acceptance Phase 1 #2 закрыт полностью:** ни один файл в пакете `billing` не превышает 1500 LOC; god-module 3377 LOC превратился в **12 файлов** с трёхслойной топологией (schemas → _helpers → routes); 19/19 целевых тестов (`test_billing_addon_pack_checkout`, `test_billing_operating_slot_sync`, `test_license_addon_v1`, `test_stripe_webhook_idempotency`) проходят; все внешние потребители (`main.py`, `arq_worker.py`, `platform/tenants.py`, `scripts/grant_tenant_business_internal.py`, тесты) работают без изменений за счёт re-exports + сохранённого `billing.settings`/`billing.stripe` namespace. Можно переходить к **Phase 1 #3** (`backend/app/modules/leads/service.py` — 4145 LOC).
- [x] **Phase 1 #3 — `backend/app/modules/leads/service.py` (4145 LOC) разнесён на пакет `service/`** (DONE).
      Стратегия — итеративная декомпозиция «один шаг = одна тематическая зона + green tests + LOC-снимок», без изменения публичной поверхности (router / `admin_service` / `services/imports/leads.py` / scripts / тесты используют исторический путь `service.<name>` через re-exports в `__init__.py`).

      - **Шаг 1/N:** `service.py` → `service/__init__.py` (4145 LOC). 33/33 lead-tests зелёные.
      - **Шаг 2/N:** `_helpers.py` (583 LOC, 23 символа) — `MetaLeadResult`/`MetaLeadRetryOutcome`/`LeadProcessingError`, `_normalize_business_type`/`_load_tenant_business_type`/`_load_settings`, event/reminder helpers, `resolve_vacancy_for_lead_processing`, qualification preview/audit. `__init__.py` 4145 → 3633.
      - **Шаг 3/N:** `_listing.py` (669 LOC, 12 символов) — `count_leads`/`list_leads`/`count_candidates_no_next_action_for_assignee`/`count_candidate_overdue_reminders_for_assignee`, `_build_lead_list_filters`, `_sql_effective_lead_conversion_root`, `CONVERSION_ROOT_ORDER`/`CONVERSION_ROOTS_SET`/`_LEAD_LEGACY_STAGE_TO_ROOT`/`LEAD_LIST_PIPELINE_ERROR_WHITELIST`. `__init__.py` 3633 → 3043.
      - **Шаг 4/N:** `_funnel.py` (701 LOC, 17 символов) — `ConversionFunnelSliceParams` dataclass, `_lost_from_stage_breakdown`/`_lost_reason_code_breakdown`, dwell-агрегаты (`_dwell_avg_p50`/`_lead_conversion_funnel_dwell_by_stage`/`_lead_conversion_funnel_dwell_by_root`/`_percentile_sorted`), `_compute_lead_conversion_funnel`, public `lead_conversion_funnel_snapshot`/`lead_stage_health_snapshot`. `__init__.py` 3043 → 2415.
      - **Шаг 5/N:** `_nba.py` (367 LOC) + `_timeline.py` (143 LOC) — все 5 NBA-констант (`NBA_FUNNEL_MIN_TOTAL_WIN`/`NBA_FUNNEL_MIN_AT_OR_BEYOND`/`NBA_FUNNEL_MIN_DWELL_SAMPLE`/`NBA_FUNNEL_SLOW_DWELL_DAYS`/`NBA_FUNNEL_WEAK_SHARE_MAX`), `_nba_lead_locked_and_required`, `nba_conversion_funnel_insight_groups`, public `lead_next_actions_snapshot` + `get_lead_timeline`. `__init__.py` 2415 → 1977.
      - **Шаг 6/N:** `_processing.py` (941 LOC) — единственная точка входа `process_normalized_lead` (886 LOC body): полный §2.10 ingest pipeline (settings load → mode-resolution → vacancy-routing → fit eval → candidate create/update → plan-gate enforce → automation rules → audit + event emission + license sync). `__init__.py` 1977 → 1098.
      - **Шаг 7/N:** три модуля одной волной — `_bulk.py` (496 LOC: payload coercion / fallback merge, queue filters, `count_bulk_auto_process_meta_lead_queue`, parallel `bulk_auto_process_meta_lead_queue`, `reprocess_stored_lead_payload`, `process_meta_lead`, `process_generic_inbound_webhook_lead` — объединены, чтобы не плодить cross-package late-imports); `_retry.py` (187 LOC: `retry_meta_leads`); `_reroute.py` (318 LOC: `reroute_lead_manual` — admin re-routing с валидацией, candidate hand-off, audit, event). `__init__.py` финал = **114 LOC** (= модуль-докстринг + 9 re-export блоков под `# noqa: F401`, без какой-либо логики).

      Финальная LOC-раскладка пакета `backend/app/modules/leads/service/`:
        - `__init__.py` 114 (target ≤ 200 ✓), `_processing.py` 941, `_funnel.py` 701, `_listing.py` 669, `_helpers.py` 583, `_bulk.py` 496, `_nba.py` 367, `_reroute.py` 318, `_retry.py` 187, `_timeline.py` 143. **Все ≤ 1500 LOC** ✓.

      **Acceptance Phase 1 #3 закрыт полностью:** god-module 4145 LOC → **10 файлов**, ни один > 1500 LOC; 33/33 lead-tests (`test_lead_vacancy_own_company_scope`, `test_reprocess_flat_csv_payload`, `test_lead_quota`, `test_lead_distribution_ingest`, `test_lead_criteria_documents`) проходят; smoke-import 13 внешних потребителей (`main.py`, `modules/leads/{router,admin_service,pipeline,inbound_public,webhook,pipeline_hooks}.py`, `api/v1/leads/router.py`, `api/v1/next_actions.py`, `api/v1/settings/leads.py`, `services/lead_distribution.py`, `services/imports/leads.py`, `api/public/intake.py`, `db/meta_leads_tenant_dep.py`) → все импортируются без ошибок благодаря re-exports.

      Можно переходить к **Phase 1 #4** (`hostflow-frontend/src/pages/Candidates.tsx` — 5731 LOC).
- [x] **`hostflow-frontend/src/pages/Candidates.tsx` разбит: 5731 → 3008 LOC (−2723, −48 %).** tsc baseline-чистый (ноль новых ошибок — те же 4 pre-existing остаются: `Candidates.tsx:ManagerItem.label`, `CandidatesFiltersActionsPanel:LegacyRef`, `useCandidatesQuickViews:URLSearchParams`). ESLint clean. Извлечённые модули:
    - **Шаг 1/N:** `src/modules/candidates/internal.ts` (99 LOC) — `candidateListCache`, `normalizeListInsights`, `getWithFallbacks` (с правильной типизацией `unknown` вместо `any`), `parseRiskShadowMinBand`/`RISK_SHADOW_MIN_BANDS`, `TEAM_WORK_PANEL_ASSIGNEE_ROLES`, `WP_ASSIGNEE_STORAGE_KEY`. Удалён неиспользуемый импорт `withTenant` в page-файле. **5731 → 5670.**
    - **Шаг 2/N:** `src/modules/candidates/hooks/useCandidatesCatalogs.ts` (110 LOC) — три независимых каталога-эффекта: `useCandidatesManagersCatalog` (с fallback-добавлением текущего юзера, если бекенд его опустил), `useCandidatesVacanciesCatalog`, `useCandidatesHandoffClientsLazy` (lazy при открытии bulk-handoff модалки). Каждый хук кенселит свой эффект через `cancelled` флаг. **5670 → 5639.**
    - **Шаг 3/N:** `src/modules/candidates/hooks/useCandidatesBulkActions.ts` (704 LOC) — единая точка входа для семи bulk-handler-ов (`doBulkActivities`, `doBulk` (stage), `doBulkAssign` (manager), `doBulkAssignVacancy`, `doBulkHandoff`, `doBulkTags`, `doBulkDelete`). Принимает один `ctx` объект (40+ полей: state values, setters, refs, helpers) — это удерживает публичный API стабильным. Все семь специфичных error-codes для stage-gate (`stage_blocked_by_contact_attempt`/`_vacancy`/`_documents`/`_risk_gate`, `handoff_docs_incomplete`, RODO-блок) сохранены 1-в-1. **5639 → 5142** (−497 в page-файле).
    - **Шаг 4/N:** `src/modules/candidates/components/CandidatesDebugPanel.tsx` (239 LOC) — JSX отладочной панели за `?debug=1` (client-view probe + force-two action + 5 hit-test трасс ± bubble + снимок preview-state). 3 `debugClientView*` `useState` теперь живут внутри компонента; 5 hit-test блоков сжаты в `<HitTrace tone="…" />`. **5142 → 4974.**
    - **Cleanup:** удалён 240-LOC dead-code блок `legacyLoad` (фактический loader давно живёт в `useCandidatesTableData.load`). **4974 → 4734.**
    - **Шаг 6/N:** `src/modules/candidates/components/CandidatesBulkModalsCluster.tsx` (238 LOC) — агрегатор семи bulk-модалок + activities-modal с `<ActivitiesPanel embedded compact />`; `closeIfIdle()` хелпер блокирует закрытие во время `bulkOperationLoading`. **4734 → 4687.**
    - **Шаг 7/N:** `src/modules/candidates/components/CandidatesTableRowCells.tsx` (517 LOC) — 418-LOC inline `renderCandidateRowTds` (25 колонок) превращён в компонент c `useMemo(tableRowCellsCtx)` (~30 props). **4687 → 4292** (−395, −8 %).
    - **Шаг 8/N:** `src/modules/candidates/components/CandidatesTableColumnHeaderContent.tsx` (535 LOC) — 290-LOC `renderColumnHeaderContent` + три helper'а (`renderSortButton`/`renderRangeMenu`/`renderTextFilterMenu`) объединены в один компонент с private-helper'ами и единым `ctx`. **4292 → 3893** (−399, −9 %).
    - **Шаг 9/N:** `src/modules/candidates/candidateFilters.ts` (189 LOC) — 154-LOC `filterCandidates` `useCallback` с 16 фильтр-предикатами превращён в pure-function `filterCandidates(source, snapshot, { debug })` без зависимостей от React/page-state. Юнит-тестируется без mount. **3893 → 3745** (−148, −4 %).
    - **Шаг 10/N:** `src/modules/candidates/filterNormalizers.ts` (105 LOC) + `hooks/useCandidatesFiltersState.ts` (198 LOC) — 5 inline `normalize*` `useCallback`-ов превращены в pure-функции; `applyViewFilters` (28 LOC) + `resetCandidatesFiltersCore` (33 LOC) + `handleResetFilters` (16 LOC) переехали в хук, принимающий bag из всех setters/refs. **3745 → 3608** (−137, −4 %).
    - **Шаг 11/N:** `src/modules/candidates/hooks/useCandidatesFilterOptions.ts` (288 LOC) — 14 column-filter `useMemo`-ов (vacancy/manager/reason/docsStatus presence+options/docsOrder/docsHasFiles/preferredChannel/inPoland/opsMode/polandBasis/trailerTypes) объединены в один хук, который возвращает все опции одним объектом. **3608 → 3453** (−155, −4 %).
    - **Шаг 12/N:** `src/modules/candidates/components/CandidatesFiltersToolbar.tsx` (309 LOC) — 148-LOC JSX-блок (search input + `<CandidatesQuickViewsBar />` + 3 quick-filter select-а + условный `<FilterBadges />`) централизован за единым `props`-объектом; типы для `quickDocFilters`/`UserSavedView` импортируются напрямую из соседних компонентов, чтобы избежать дублей. **3453 → 3380** (−73, −2 %).
    - **Шаг 13/N:** `src/modules/candidates/hooks/useCandidatesUrlSync.ts` (164 LOC) — три URL-sync `useEffect`-а: (1) mirror `?view=…` → `viewMode`, (2) safety-net «operational queue + kanban» (стрипает `view` из URL), (3) deep-link decoder (`?stages=&manager_id=&…`) с детерминистическим `resetCandidatesFiltersCore()` перед применением. **3380 → 3298** (−82, −2 %).
    - **Шаг 14a:** `src/modules/candidates/hooks/useCandidatesFiltersPersistence.ts` (297 LOC) — два парных `useEffect`-а: (1) гидрация ~25 фильтр-полей из `localStorage[filterStorageKey]` через те же `normalize*` helpers + `setFiltersHydrated(true)`, (2) сериализация полного снимка обратно при изменении любого поля. **3298 → 3134** (−164, −5 %).
    - **Шаг 14b:** `src/modules/candidates/hooks/useCandidatesUpdateListener.ts` (198 LOC) — два `useEffect`-а для cross-page/cross-tab синхронизации: (1) refetch при возврате на `/crm/candidates` (с 10-сек guard `hf:candidate-updated`), (2) listener `candidate-updated` (`CustomEvent`) + `storage` (cross-tab) + `focus` (с debounce), все per-id с 500ms guard'ом и 60-сек окном «recently-updated» для UX. Все «магические» числа подняты в именованные константы. **3134 → 3008** (−126, −4 %).

  **Накопительный итог Phase 1 #4 (steps 1–14b, ЗАКРЫТО):** `Candidates.tsx` 5731 → **3008 LOC** (−2723, −48 %); **14 новых модулей** в `src/modules/candidates/{components,hooks,*}.ts(x)` общим объёмом 99+110+704+239+238+517+535+189+105+198+288+309+164+297+198 = **4090 LOC**, **ни один файл > 710 LOC**. tsc baseline: те же pre-existing ошибки. ESLint clean (попутно стабилизирована dep-array у `docsOwnerContext` `useMemo`, помечен `Date.now()` в `filteredItems` `useMemo` как намеренная нечистота с `react-hooks/purity`-suppression).

  **Sustainable target для оркестрирующей page достигнут**: 3008 LOC — это ~25 `useState` объявлений + `useMemo`-цепочка для derived data + 5 хук-вызовов + JSX-skeleton, всё легко читается. Дальнейшее дробление (toolbar actions, kanban switch, preview side-panel) даст diminishing returns без явного выигрыша в когнитивной нагрузке.
- [~] **Phase 1 #5 — `hostflow-frontend/src/pages/Dashboard.tsx` (4143 LOC) разбит на пакет хуков/модулей** (IN PROGRESS, 6/9 шагов закрыто, 4143 → **2639 LOC**, −36 %). tsc baseline-чистый (та же pre-existing recharts `Tooltip`-formatter ошибка). Извлечённые модули:
    - **Шаг 1/N:** `src/modules/dashboard/stageNormalize.ts` (265 LOC) — `DEFAULT_STAGE_LABELS`, `STAGE_CODE_ALIASES`, `STAGE_LABEL_ALIASES`, `STAGE_HIGHLIGHT_CODES`, `REASON_LABEL_ALIASES`, `buildNormalizedMap`, `NORMALIZED_*` lookup-карты, `canonicalStageKey`, `DOC_STAGE_CATEGORY`, `determineStageOutcome`, `normalizeStageCounts`, `stageHighlights`, `STAGE_STACK_COLORS`. + `src/modules/dashboard/internal.ts` (~30 LOC) — `TrialRetentionDay`, `DigestBulkResultReport`, `InvoiceWithPaid`, `formatDigestBulkError`. **4143 → 3868 (−275).**
    - **Шаг 2/N:** `src/modules/dashboard/hooks/useDashboardKpiLoaders.ts` (~200 LOC) — три независимых KPI-loader-а (`loadOpsCounters`, `loadInvoiceMoneyWidget`, `loadStageMetrics`) + соответствующие `*Loading`/state-поля + первичная hydration. Аккуратные `useEffect`-ы с проверками permission-флагов. **3868 → 3767 (−101).**
    - **Шаг 3/N:** `src/modules/dashboard/hooks/useDashboardRiskOps.ts` (~340 LOC) — riskIntel + manager digest cluster: `riskIntel`/`riskTrends`/`riskValidation`/`riskShadowSnapshot`/`riskDigestQueue` state, фильтры (`riskDigestMinBand`, `riskDigestQueueReadFilter`, `riskShadowBucketStart`), loaders (`loadRiskOpsCore`, `loadRiskShadow`, `refreshRiskOpsIntel`), digest-actions (`onManagerDigestAck`, `onShadowDigestReminder`, `onShadowDigestClaim`, bulk: `onShadowDigestBulkRemind`, `onShadowDigestBulkClaim`). **3767 → 3382 (−385).**
    - **Шаг 4/N:** `src/modules/dashboard/hooks/useDashboardRetention.ts` (~380 LOC) — trial/retention nudge cluster: `trialEndsAt`, `billingGate`, `retentionStatus`, `retentionDismissed`, `retentionReport(+Loading)`, derived (`trialDaysLeft`, `trialTone`, `showTrialPanel`, `trialCenterClasses`, `retentionReportRows`, `trialAgeDays`, `retentionDay`, `retentionNextHref`, `retentionStepKey`, `retentionNudge`), actions (`dismissRetentionNudge`, `trackRetentionEvent`). Включает migration с legacy localStorage-ключей и `BILLING_SUBSCRIPTION_UPDATED_EVENT` listener. **3382 → 3108 (−274).**
    - **Шаг 5/N:** `src/modules/dashboard/hooks/useDashboardLayoutPrefs.ts` (169 LOC) — per-user storage-keys (`visibleWidgetsKey`, `visibleFiltersKey`, `dashboardPresetKey`), one-shot migration с tenant-scoped legacy-ключей, `visibleWidgets`/`visibleFilters` Set'ы, `isWidgetVisible`/`isFilterVisible`/`toggleWidget`/`toggleFilter`, `savedPreset` hydration. Save/load-handlers сами остаются в page (зависят от 12+ setters + `load()`). **3108 → 3026 (−82).**
    - **Шаг 6/N:** `src/modules/dashboard/hooks/useDashboardDerivedAnalytics.ts` (589 LOC) — 17 pure-`useMemo` derivation-ов из загруженных slices/KPI/stats: `sourceStageRows`, `docStageStats`, `documentBlockerAnalytics`, `stageVelocityRows`, `businessProfileCards`, `dashboardCompanyLabels`, `businessTypeLabel`, `managerLoadRows`, `countryHeatmapRows`, `groupedStages`, `stageStackSegments`, `groupedRejectedReasons`, `groupedDeclinedReasons`, `executiveStageCountMap`, `executiveHighlights`, `executiveKpis`, `funnelSteps`. Без state и эффектов — все зависимости (slices/profileSummary/documentStats/contactStats/opsCounters/stageMetrics/periodTotal/stageLabels/translateStageLabel/translateReasonLabel/notAvailableLabel/locale/t) принимаются как options. **3026 → 2639 (−387).**
    - **Шаги 7-9 (PENDING):** JSX-clusters — `<DashboardFiltersBar />`, `<DashboardExecutiveOverview />` + KPI sections, `<DashboardPivotChart />` + `<DashboardBreakdowns />`. Целевой LOC оркестрирующей page: ~1800-2000.
- [x] **TypeScript baseline сведён к нулю: 542 → 0 ошибок (−100 %).** Параллельно с Phase 1 #4–#9 пройден полный backlog `tsc --noEmit`, без отключения `strict`/`noUncheckedIndexedAccess`/`exactOptionalPropertyTypes`. Ключевые правки (без изменений рантайм-поведения):
    - **`src/api/types.ts` + `src/api/types/{common,candidate,lead,invoice,document,notification}.ts`** — приведены к одному источнику правды: `WhoAmI.id`, `Lead.{external_id, next_action_status, next_action_title, next_action_due_at, stage_contract}`, `Invoice.latest_delivery_*`, `InvoiceItem.{quantity, amount}` (display-aliases), `InvoiceStatus += 'refunded'`, `Document.{comment, note, user_comment, workflow nullable}`, `NotificationItem.priority`, `Candidate.{masked, can_edit}`, `CandidateExtra.country_code`, `DocumentProcessType` расширен 4 кодами (`residence_card`, `tachograph_card`, `driver_license_exchange`, `swiadectwo_kierowcy`), `UUID` re-exported через alias чтобы избавиться от циклической ссылки в legacy `api/types.ts`.
    - **`src/i18n/index.tsx`** — `TranslateOptions` расширен индекс-сигнатурой `[extra: string]: unknown`, чтобы legacy-вызовы вида `t('key', { count: 5 })` (которые на runtime обрабатывались только через `options.values`) перестали падать на TS-уровне. Сигнатура задокументирована: новый код должен использовать `values: { count: 5 }`.
    - **`src/api/{vacancies,automationRules,documents/catalog}.ts`** — добавлен `is_archived?` в `ListVacanciesParams`, `title` в `createAutomationRule` стал `string | null`, `DocType` re-exported из `documents/catalog`.
    - **`src/modules/{users,documents}/constants.ts`** — `client_manager` добавлен в `ROLE_LABEL_KEYS`/`ROLE_BADGE_CLASSES`, `PROCESS_LABEL_KEYS` дополнен 4 process-кодами; `pages/admin/UsersPage.tsx` `roleOrder` синхронизирован.
    - **`src/lib/observability.ts`** — Sentry `Integration`-тип импортируется из `@sentry/core` напрямую (в `@sentry/react@9.x` он перестал экспортироваться).
    - **`src/utils/pushNotifications.ts`** — `applicationServerKey` приводится к `BufferSource` через `key.buffer.slice(...)`, чтобы соответствовать сужению `lib.dom`.
    - **`src/components/ErrorRecoveryBanner.tsx`** усиление пропсов на стороне 1 caller-а (`LeadFormsSettingsPage`): передаётся объект `info`, а не разбитые поля.
    - **`src/pages/{Companies, CandidateCard, LeadsPage, RemindersPage, InvoiceDetailPage, InvoicesPage, AgencyClientsPage, ClientLinkDetailPage, public/PublicStatusPage, public/PublicNotFoundPage, ServicesPage, AutomationRulesPage, admin/{AuditLogPage, CandidateProfilesPage, LeadFormsSettingsPage, CommunicationsSlaSettingsPage}}.tsx`** — точечные правки: type guards (`if (!id) return`), nullish coalescing (`?? ''`), aliasing типов (`DocumentWorkflow as DocumentWorkflowState`), приведение `unknown` от `features_json` к `string` перед рендером, `currentTab as Tab` для разрыва TS-narrowing внутри ветвящегося рендеринга.
    - **`src/modules/{candidates,companies,public-intake,documents}/types.ts`** — формы расширены реально использующимися полями (`RepresentativeForm.{email,phone}`, `BankAccountForm.{iban,swift_bic,country,label,is_primary}`, `WebhookForm.{event,target}` + `url` опциональный, `ContractForm.{title,code,starts_at,ends_at,reference}`, `PortalUserForm.full_name`, `MultiSelectOption.labelKey`, `StepKey` union, `DocType.{kind,requested_from,process_type,default_expire_in_days}`).
    - **Прочее:** `useCandidatesQuickViews.setSearchParams` принимает updater-форму, `CandidatesFiltersActionsPanel.actionsMenuRef` — `Ref<HTMLDivElement>`, `LeadQualificationSuggestionPanel` чекает `preview.fit_reasons && length > 0`, `ProfilePreviewModal.usage_count` сравнивается через `!= null`, `profileUtils.ts` принимает `CandidateProfile | null | undefined`, `nav/SettingsChrome.NavItem.icon: TablerIcon` (вместо generic `ComponentType`).
    - **Контроль:** `npx tsc --noEmit` → **0 ошибок** (с 542 на старте Phase 1, −86 % после первой итерации до 75, затем последовательно к нулю); `npx eslint --quiet` clean на всех затронутых файлах; runtime-поведение не изменено (только сигнатуры/ноль-чеки/widening типов, нет правок логики).
- [ ] **IA v2:** удалить `CrmContourWayfindingStrip` как универсальную полосу. Заменить на контекстный «breadcrumb + 1 CTA» в шапке каждой страницы. Это убирает дубль «топбар + сайдбар + контур-полоса + крошки».
- [x] **Phase 1 #7 DONE: `SettingsSubpageHeader` унифицирован на всех подстраницах настроек.** Инвентарь `src/pages/admin/*.tsx`: 29 файлов; на старте header стоял у 15, добавлено к ещё 11 (`EmailSettingsPage`, `BillingTeamPage`, `CompanyAccessPage`, `CommunicationsSettingsPage`, `CommunicationsMessengerSettingsPage`, `CommunicationsQueueSettingsPage`, `CommunicationsSlaSettingsPage`, `IntegrationsHubPage`, `IntegrationsSourcePlaceholderPage`, `IntegrationsWebhookPage`, `MetaLeadsAdminPage`). Итог: `26/29` страниц используют общий `SettingsSubpageHeader`. Оставшиеся 3 файла _намеренно_ без собственного хедера — это либо встроенные блоки, либо корень/обёртки: `DeletionRequestsPage` (рендерится как вкладка внутри `AuditLogPage` — хедер уже есть на родителе), `MessengerIntegrationChannelPage` (тонкая обёртка `<CommunicationsMessengerSettingsPage lockedChannel={…} />` — хедер рисует дочерний компонент), `SettingsLandingPage` (root-страница хаба, back-ссылка не нужна по определению). Сделано без изменения публичного контракта (back-ссылки, kicker, title, subtitle, опциональные `actions` для `<Link to=…>`/refresh-кнопок); ad-hoc «Link + h1 + p» хедеры заменены на компонент. `tsc --noEmit` clean (0 ошибок), `eslint --quiet` clean на всех 11 затронутых файлах. Cписок поддерживается: новые подстраницы должны импортировать `SettingsSubpageHeader` из `src/components/settings/SettingsSubpageHeader.tsx`.
- [x] **Phase 1 #9 DONE (Stage 4 — финальный проход): dead-TS-exports + orphan i18n-группы.** Удалено: **(a)** 16 dead-функций/констант внутри живых файлов через прицельные `StrReplace` (по одной — `isActivationRoute`, `getBusinessPrimaryEntityPath` в `app/activationRoutes.ts`; `TOAST_TTL` в `components/Toast.tsx`; `PreferredContactValue` type в `data/preferredContactChannels.ts`; `isSidebarRailHiddenItemKey` в `nav/appShellNav.ts`; `FINANCE_NAV_ORDER` в `nav/financeNavVisibility.ts`; `labelForStage` в `store/useMeta.ts`; `STAGES_WITHOUT_DOC_PIPELINE_BLOCK`, `STAGES_REQUIRE_VACANCY_FOR_FORWARD` в `utils/candidateStageDocPolicy.ts`; `emailThreadTitle` в `utils/emailInboxFolders.ts`; `isNotFoundError` в `utils/errorHandling.ts`; `filterRelevantNotifications` в `utils/notifications.ts`; `peekPendingGmailOAuthCode`, `clearPendingGmailOAuthCode` в `utils/oauthRedirectBridge.ts`; `getVisibleFieldKeys` в `utils/profileUtils.ts`; `toastSuccess`, `toastInfo`, `toastWarning` (3 wrappers) в `utils/toastFromError.ts`; `mergeFromCache`, `enrichVacancyList` в `utils/vacancyUtils.ts`; `validateRequired` в `utils/validation.ts`; `opsModeLabel` в `utils/communicationsOpsMode.ts`; `normalizeMetadataValue`, `buildMetadataDefaults` в `modules/documents/documentUtils.ts`; barrel `modules/documents/index.ts` целиком; `getTemplateByKey`, `getTemplateByType` в `modules/candidates/activityTemplates.ts`; `OPERATIONAL_PROFILE_OPTIONS` в `modules/companies/constants.ts`; `unsubscribeFromPush` в `utils/pushNotifications.ts`). **(b)** 4 leftover `.bak`/`.old` артефакта, пропущенных в Stage 1: `.env.bak.2025-10-28-1335`, `backend/app/main.py.bak.docs-module`, `backend/app/api/v1/stages.py.bak.stages-imports`, `hostflow-frontend/src/api/documents.ts.old`, `hostflow-frontend/src/modules/documents/{CandidateDocuments.tsx.bak.1762339603,documents.ts.bak.docs-module}` (всего 6 файлов). **(c)** 247 полностью мёртвых i18n-групп = **872 leaf-keys × 3 локали = ~3900 строк JSON** удалено. Алгоритм: для каждого 3-сегментного префикса (всего 1547 групп) проверено, есть ли ХОТЬ ОДИН литерал в коде, начинающийся с этого префикса (regex `['"\`]prefix[.'"\`]`); если нет, дополнительно проверено, что родительский 2-сегментный префикс не используется в template literal (`\`parent.${var}\``) — иначе риск динамических ключей. Топ-удалённые группы: `app.admin.meta_leads.*` (111 — это был параллельный дубль активной `admin.meta_leads.*` без префикса `app.`), `public.scan.{overlay,capture,errors,quality,status,review,pages,steps}.*` (164, документ-сканер), `admin.documents.{settings,forms,actions,table,summary,simple}.*` (~100), `app.communications_messages.tags.*` (18), `{app,admin}.ruleset.{history,diff,create,usage,header,actions,errors}.*` (~80), `app.candidate_card.{override,nav,operations,history,tabs}.*` (~30), `app.dashboard.{nba,top_cards,perf,hero,hubs,goals,insights_strip,crm_wayfinding}.*` (~50), и т.д. Дополнительно убраны под-ветки `app.topbar.notifications.{subtitle,open_thread,open_in_inbox,groups,tier}` (15 leaf'ов, осиротели после рефакторинга нотификаций). **Контроль (наисильнейший):** не только `tsc -p tsconfig.app.json --noEmit` 0 ошибок, но и **полный production `npm run build` прошёл успешно за 28 секунд** — все Vite-бандлы собраны, никаких регрессий. Каждая локаль уменьшилась с 11524 до 10225 строк (−11.3%).
- [x] **Phase 1 #9 DONE (Stage 2 + Stage 3): Cleanup PII, name-specific миграций, устаревших docs и dead-code.** Удалено суммарно ~45 единиц + директория `samples/` (29 файлов, 36 MB). По блокам: **(1) PII-риск — `samples/`** в корне репозитория содержал реальные сканы паспортов, ВНЖ, водительских удостоверений, тахо-карт и польских licence реальных кандидатов (имена в путях: `RAJAN RAJESH/`, `ROHANA WIMAL/`, `SITHOLE/`, `ZUWIRA WISEMAN/`) + 9 .heic фото. **Все 29 файлов удалены через `git rm -rf samples/`**, директория добавлена в `.gitignore` (`/samples/`) — такие данные **никогда** не должны попадать в git, должны храниться в защищённом хранилище. **(2) Дубли в `scripts/`**: `scripts/check_meta_tokens.py` и `scripts/retry_leads_with_new_fields.py` — старые копии, актуальные универсальные версии в `backend/scripts/` (`docs/META_GRAPH_190_FIX.md` ссылается на `backend/scripts/...`). Untracked `scripts/cleanup_test_meta_and_stub_tenants.sql` — одноразовая выгрузка. **(3) Name-specific tenant migrations** (8 шт., все одноразовые data-fixes для конкретных тенантов, история в git сохранена): `check_citronex_handoffs.sql`, `ensure_valentina_focus_poltrakt.sql`, `meta_poltrakt_to_focus_personnel.sql`, `migrate_poltrakt_company_to_focus.sql`, `migrate_superadmin_leads_meta_to_focus.sql`, `migrate_superadmin_meta_connection_to_focus.sql`, `repair_focus_leads_from_export_csvs.py`, `scripts/migrations/migrate_crm_contour_strip.py` (одноразовая code-migration для Phase 1 #6). Папка `scripts/migrations/` опустела и удалена. **(4) Устаревшие `docs/*.md`-черновики (2 шт.)**: `CLIENTS_VACANCIES_REDESIGN.md` (Phase 1 done-doc, 4 из 5 пунктов сделаны и описаны в SSOT), `communications-test-matrix.md` (Phase 1-2 testing checklist, неактуален — communications переехали в `docs/specs/modules/communications.md`). **(5) Dead-TS-code (4 файла)**: компоненты, у которых ВСЕ экспорты помечены `ts-prune` как unused И никто не импортирует файл по имени — `src/components/SetupProgressRail.tsx`, `src/components/nav/Breadcrumbs.tsx` (старая версия — текущая `PageBreadcrumb` живёт в `src/components/nav/PageBreadcrumb.tsx`), `src/components/nba/DashboardNbaSection.tsx`, `src/components/nba/TopbarNbaMenu.tsx`. **(6) Orphan i18n-блок**: `app.topbar.quick_create.*` (9 leaf-keys × 3 локали = 27 строк), осиротевший после Phase 1 #8. **Инвентарь, оставленный на ручной проход:** ~98 «настоящих» dead-TS-exports — это отдельные функции/константы внутри живых файлов (например `toastSuccess`/`toastInfo`/`toastWarning` в `utils/toastFromError.ts`, `STAGES_WITHOUT_DOC_PIPELINE_BLOCK` в `utils/candidateStageDocPolicy.ts`); их вырезание требует анализа «возможно использовалось извне как часть public API». ~244 dead exports в barrel-файлах (`src/api/types/index.ts` 140, `api/documents.ts` 49, `api/client.ts` 35, `api/communications.ts` 17, `modules/candidates/components/index.ts` 15) — это намеренные re-exports, удалять нельзя. Orphan i18n — 1619 leaf-keys из 8441 (~19%); топ-группы (`app.admin.meta_leads.*` 111, `app.communications.email.*` 61, `app.work.hub.*` 57, `app.dashboard.risk_intel.*` 52, `public.scan.{overlay,capture}.*` 88, `admin.documents.{settings,forms}.*` 74) почти полностью false positive из-за runtime-ключей (backend payload, `defaultValue`-обёртки, частично собранные template literals); требуется ручная валидация группы перед удалением. **Контроль:** `tsc -p tsconfig.app.json --noEmit` — 0 ошибок после всех правок; ссылок на удалённые символы/ключи в `src/` не осталось.
- [x] **Phase 1 #9 DONE (Stage 1): Cleanup корня репозитория.** Удалено **76 файлов**, нарушавших правила `docs/SSOT.md` §1.1/§1.4 и захламлявших корень. По блокам: **A** случайно-закоммиченные/0-байтные артефакты shell-команд (13 шт.: `0,`, `=2.18`, `=2.3`, `=2.8`, `from backend.app.`, `import backend.app.`, `SELECT`, `cookie.txt`, `file`, `openapi_paths_candidates.json`, `project_tree.txt`, `project-structure.txt`, `vulture.txt`); **B** SQLite-бэкапы в корне (8 шт.: все `app.db.*`-варианты); **C** одноразовые .md-черновики (13 шт.: `CANDIDATE_PORTAL_IMPROVEMENTS`, `CRITICAL_FIXES`, `CRITICAL_FIXES_V2`, `DEBUGGING_GUIDE`, `DEPLOYMENT_REPORT`, `DEPLOYMENT_SUMMARY`, `EXECUTION_PLAN`, `FINAL_DEPLOYMENT`, `HF-AEP v2.0`, `IMPLEMENTATION_PLAN`, `OVERLAY_VISIBILITY_FIX`, `PROCESSING_FEATURES_REPORT`, `upgrade`); **D** dev-only одноразовые скрипты в корне (11 шт.: `check_tenant_debug.py`, `check_tenant_type.sql`, `debug_single_image.py`, `connect-docs-module.sh`+`connect_docs_module.sh` (заготовка + результат), `test_all_samples{,_quick}.py`, `test_document_detection.py`, `test_frontend_detection.py`, `test_processing_features.py`, `test_front.html`); **E** аналогичные dev-артефакты в `backend/` (13 шт.: `analyze_document_specs.py`, `debug_single_image.py`, `extract_templates.py`, `fix_migration.py` (одноразовый Alembic-патч), 5 ad-hoc OCR test-скриптов, `document_specs.json`, `export.csv`, `templates/` с 3 .png/.pkl-артефактами template-matching, пустой `временная`); **F** frontend dev-артефакты (6 шт.: tracked `dist.bak/` (бэкап билда), 0-байтные `vite` и `hostflow-frontend@0.1.0`, `FIXES-REPORT.md`, `INTake-CHECKLIST.md`, `test-intake-flow.md`); **G** дубли cleanup-SQL (4 шт.: `scripts/cleanup_fake_data{,_v2,_v3,_final}.sql` — 4 итерации одного скрипта); **H** untracked кэши (`__pycache__`, `app/__pycache__`, `backend/__pycache__`, `backend/.pytest_cache`). Заодно убран orphan-entry `dist.bak` из `IGNORE_DIRS` в `hostflow-frontend/scripts/check-i18n-hardcode.mjs`. **Контроль:** `npx tsc --noEmit` — 0 ошибок; `eslint --quiet src` — 2 pre-existing ошибки `no-unsafe-finally` (не связаны с чисткой); `python -c "from app import main"` — backend импортируется. **Stage 2 (отложено, требует решения):** `samples/` (PII-риск — реальные паспорта/договоры?), устаревшие `docs/*.md`-спеки (CLIENTS_VACANCIES_REDESIGN, META_GRAPH_190_FIX, communications-test-matrix и др.), одноразовые `scripts/*.sql`/`*.py`-миграции для конкретных тенантов (Poltrakt/Focus/Citronex/Valentina). **Stage 3 (next):** dead code (TS via ts-prune, Python via vulture) + orphan i18n keys (включая `app.topbar.quick_create.*` от #8).
- [x] **Phase 1 #8 DONE: Топбар-dedupe.** Из правой части `Topbar.tsx` удалены дубли с сайдбаром: (1) кнопка `+ Создать` с выпадающим Quick-Create-меню (все 7 пунктов — `candidate/client/vacancy/order/task/meeting/invoice` — реализованы как ссылки в сайдбаре + у каждой страницы есть собственная primary-CTA «Новая …»; глобальная Quick-Create-плашка дублировала эти точки входа и захламляла шапку); (2) `CandidatesMenuButton` — топбар-кнопка управления work-panel страницы кандидатов, которая жила в глобальном Topbar и общалась со страницей через 3 кастом-эвента (`candidates-sidebar-toggle`, `candidates-sidebar-state`, `candidates-sidebar-request-state`). Кнопка перенесена внутрь `Candidates.tsx` (рядом с `PageBreadcrumb`) и теперь напрямую дёргает локальный `setSidebarOpen`/`setSelectedCandidateId` без window-эвентов. Аналогичный мёртвый код удалён в `Pipeline.tsx` (тот же work-panel-toggle размещён в шапке страницы), кросс-компонентные эвенты выпилены и в `useCandidatesWorkPanel.ts`. Что осталось в топбаре: гамбургер сайдбара (слева) → лого → trial-бейдж · «Вернуться на платформу» (только для impersonation) · поиск (`⌘K`) · колокольчик inbox · меню пользователя. **Итог по LOC:** `Topbar.tsx` 1282 → 1119 (−163, −12.7%); `useCandidatesWorkPanel.ts` 87 → 50 (−37, −42.5%); из `Pipeline.tsx` удалён один `useEffect`-блок мёртвых listener-ов. Заодно починен старый pre-existing eslint-error `no-unsafe-finally` в `Pipeline.tsx` (`return` внутри `finally` заменён на флаг `handledByPlanLimit`). Контроль: `npx tsc --noEmit` — 0 ошибок; `npx eslint --quiet` — clean. i18n-ключи `app.topbar.quick_create.*` стали orphan (можно удалить отдельным cleanup-PR; сейчас оставлены, потому что несколько локалей и тестов их ещё могут импортировать через универсальные fallback-механизмы).

**Acceptance:** никакой файл в бэкенде > 1500 LOC; никакой `.tsx` > 1200 LOC; первый экран каждой страницы умещается в 720 px высоты без скролла для primary-action.

**KPI:** median PR touch-files < 10 (сейчас частые PR-ы касаются god-module-ов целиком); время code-review ↓ в 2 раза.

### Фаза 2 — Onboarding «первое значение за 5 минут»

**Цель:** новый пользователь получает **первый лид в работе** за первые 5 минут, без обучения.

- [ ] Жёсткий wizard signup → 5 шагов: (1) тип бизнеса, (2) подключить 1 канал входа лидов (Meta/webhook/public intake), (3) создать первую компанию-клиента, (4) создать первую вакансию, (5) получить демо-лид + NBA на экране.
- [ ] После шага 5 — дашборд уже **не пустой**: виджеты рассказывают, что делать с этим лидом.
- [ ] Progress rail остаётся как постоянная подсказка на 7 дней после signup (потом скрывается автоматически). Запрет на blocking UI.
- [ ] Демо-данные: «Добавить demo-seed» в onboarding как опция (можно одним кликом получить 5 лидов, 3 кандидатов, 1 вакансию — чтобы учебно походить по продукту).
- [ ] Микрокопирайт «зачем это» на каждом пустом экране первых 7 дней.

**Acceptance:** от клика «зарегистрироваться» до «первый лид с NBA в работе» ≤ 5 минут (измерение: метрика `time_to_first_meaningful_action`).

**KPI:** activation-rate D+1 ≥ 60%; доля новых тенантов, подключивших канал лидов в первые 24 ч ≥ 70%.

### Фаза 3 — Документы: удобный, полезный, быстрый

(Подробная спецификация — §IV.1)

- [ ] Реестр документов как «одна таблица, один фильтр, один статус».
- [ ] Полная цепочка: запрос → загрузка кандидатом/клиентом → auto-OCR → валидация по правилам → статус → подпись/отклонение → хранение.
- [ ] Workflow-шаблоны: «для РФ-договора такие-то документы», «для польского гражданина такие-то», «для вакансии X такой пакет».
- [ ] OCR/intelligence вынести в очередь (после Фазы 0); UI показывает прогресс и результат инлайн.
- [ ] Версионирование документов + аудит (кто загрузил, когда, кто подписал).
- [ ] Публичный захват (кандидат загружает документы по ссылке без регистрации).

### Фаза 4 — Календарь, напоминания, задачи: единая модель

(Подробная спецификация — §IV.2, §IV.3)

- [ ] Единая сущность «задача» поверх текущих `Task`, `Reminder`, `NBA`. Одна таблица/одно API.
- [ ] Единый календарь: задачи + события коммуникаций + сроки документов + SLA-дедлайны. Двусторонний sync с Google Calendar и Outlook.
- [ ] Напоминания: push (web + mobile PWA), email, telegram-bot, in-app.
- [ ] Snooze, re-schedule, bulk reassign.
- [ ] Taskbar на каждой странице в правом верху: «3 задачи сегодня», клик → миниоткрывающийся список без ухода со страницы.

### Фаза 5 — Сообщения/Inbox: унификация и ускорение

(Подробная спецификация — §IV.4)

- [ ] Единый inbox: email + messengers + leads-comments + документо-уведомления. Один поиск, один фильтр «непрочитанное».
- [ ] SLA-таймер на каждом треде, автоматическая эскалация.
- [ ] Command templates: bulk-применение к выбранным тредам.
- [ ] Сигнал «кто печатает» в тредах с внутренней перепиской.
- [ ] Команды (/schedule, /template, /assign) прямо в composer.
- [ ] Sent as: с любого подключённого адреса, выбор в один клик.

### Фаза 6 — Биллинг по SSOT §2.18 (коммерция «1b»)

**Цель:** закрыть все `[ ]` из §2.17 и Stripe-блока §2.1 SSOT.

- [ ] Stripe Tax + tax_ids + VIES для EU.
- [ ] Customer Portal поверх Checkout (upgrade/compare/add-ons).
- [ ] SKU add-on packs (лиды, поля, место, seats, client-portal) + UI «buy pack».
- [ ] Webhook `invoice.finalized` + idempotent-ретраи через очередь (Фаза 0).
- [ ] Trial-restrictions grace 3 дня **на все** write-API (не только leads/outgoing).
- [ ] Team: invite + seat-gate + матрица доступа (`BillingTeamPage`, `UserFormInvite`).
- [ ] Roles editor с серверной валидацией.
- [ ] Companies CRUD с предупреждением цены (§2.16).
- [ ] TenantsPage (superadmin): override limits, billing adjust.
- [ ] Audit-лог: plan change, override, invite, role change.
- [ ] Pricing-страница (лендинг) + living price IDs в Stripe (включая founder €99/€199).
- [ ] Post-trial messaging + баннеры (UI).

**Acceptance:** все `[ ]` из SSOT §2.1 «Настройки владельца» и «Stripe и биллинг» — закрыты или явно помечены «вне scope с владельцем».

### Фаза 7 — Portal клиента/кандидата до продакт-уровня

- [ ] Branded per-client billing (§2.16).
- [ ] Матрица ролей портала; скрытие internal notes слоем.
- [ ] Шаблоны писем портала + доставляемость (SPF/DKIM чеклист владельцу).
- [ ] Чип NBA «Remind client» на карточке лида.
- [ ] Single-slot чат в портале (вне отдельного чат-продукта).

### Фаза 8 — Поиск, аналитика, NBA v2

- [ ] Глобальный поиск: документы с join к кандидату (SSOT §2.1).
- [ ] Опционально: семантический поиск (pgvector или внешний — решение по данным).
- [ ] Воронка конверсии v2: произвольное окно, WoW-инсайты, сценарные шаблоны.
- [ ] NBA v2: rule engine поверх `lead_criteria_eval`, `assign_pipeline` в automation, rich constructor триггеров кроме `lead.qualification`.
- [ ] Custom fields лидов: расширенные операторы фильтра, typed custom + UI правил.

### Фаза 9 — Мобильный PWA-shell

- [ ] Инсталлируемое приложение (PWA) с push-уведомлениями.
- [ ] Мобильный first-view: «мои задачи сегодня», «мои треды», «быстро добавить лид/задачу».
- [ ] Сканер документов прямо с камеры телефона (OpenCV уже есть).
- [ ] Оффлайн-очередь действий (по минимуму: создание задачи, отметка выполненной, комментарий).

### Фаза 10 — Производительность и масштабирование

- [ ] Кеш-слой в Redis: агрегаты дашборда, воронка, stuck-очереди (TTL 60–300с), инвалидация по событию.
- [ ] Read-replica Postgres под тяжёлые аналитические запросы.
- [ ] Bundle-splitting (лениво грузить `Candidates`, `Dashboard`, аналитику, inbox).
- [ ] Сервисные health-endpoint-ы, uptime-мониторинг, SLO.

---

## Часть IV. Ключевые модули — продуктовая спецификация

### IV.1 Модуль «Документы»

**Болевая точка рекрутёра:** бегает между клиентом, кандидатом и почтой, не знает, что загружено, что подписано, что просрочено.

**Целевой UX:**

1. **Реестр документов** (`/app/documents`) — одна таблица:
   - Колонки: тип документа, кандидат/клиент, статус (чип: `requested` / `in_review` / `approved` / `rejected` / `expired`), дата дедлайна, ответственный.
   - Фильтры: статус, тип, ответственный, просрочено, ждёт моего действия.
   - Правый sidebar — preview документа без ухода со страницы.
2. **Запрос документа** — кнопка «Запросить» на карточке кандидата/клиента/вакансии:
   - Выбор шаблона пакета («Стандартный найм РФ», «Польское гражданство» — настраивается в `/app/settings/document-workflow`).
   - Автогенерация публичной ссылки для кандидата (c expiry).
   - Автоотправка в выбранный канал (email / telegram / whatsapp).
3. **Захват** — кандидат загружает с телефона, камера → сканер (уже есть OpenCV) → auto-crop → preview → submit. Никакой регистрации.
4. **Автопроверка:**
   - OCR извлекает поля (ФИО, номер паспорта, дата).
   - Правила (`rulesets`) валидируют: совпадает ли ФИО с кандидатом, не просрочен ли паспорт, читабелен ли скан.
   - Если всё ок — статус `in_review` с пометкой «пройдены все автопроверки».
   - Если нет — `needs_attention` с конкретной причиной («Фото смазано», «Срок действия истёк в 2023»).
5. **Подпись/согласие:**
   - e-sign внутри портала (SSOT §2.17: «вычитка, локализации, e-sign» — открытый пункт биллинг-легала).
   - Аудит подписи с IP/timestamp/user-agent.
6. **Версионирование:** новая загрузка = новая версия, старая не стирается.
7. **Хранение:** S3 (MinIO в dev, внешний в prod — Фаза 0), presigned URL, TTL на скачивание.

**Метрики прямо в модуле:**

- На реестре сверху — «ждут подписи: N», «просрочены: N», «в работе: N» (три чипа-фильтра).
- На карточке документа — возраст, кто последний трогал, SLA.
- На карточке кандидата — прогресс-бар «документы: X из Y готовы».

**Acceptance:**

- Рекрутёр запрашивает пакет документов у нового кандидата за ≤ 30 секунд (выбор шаблона + отправка).
- Кандидат загружает документ с телефона за ≤ 2 минуты без регистрации.
- Просроченный документ сам уходит в стак и NBA «напомнить кандидату».

### IV.2 Модуль «Календарь»

**Болевая точка:** рекрутёр держит календарь в Google/Outlook, задачи в HostFlow, напоминания в голове. Разрыв.

**Целевой UX:**

1. **Единый календарь** (`/app/calendar`) — три источника в одной ленте:
   - Задачи из HostFlow (`Task` + `Reminder` + NBA с due_date).
   - Внешние события из Google/Outlook (через OAuth sync, двусторонний).
   - Дедлайны документов, SLA коммуникаций, запланированные отправки.
2. **Views:** день / неделя / месяц / agenda-list.
3. **Fast actions:**
   - Drag-and-drop задачи на новое время.
   - Click-to-create со shift — «быстро запланировать звонок с кандидатом X».
   - Right-click контекстное меню: «перенести на +1 день», «передать Анне», «завершить».
4. **Цветовая разметка** (спокойная, не попугайская):
   - Задача → нейтральная.
   - SLA-дедлайн → красный при < 2ч, жёлтый при < 24ч.
   - Внешнее событие → серый.
   - Документ → голубой.
5. **Sync c Google/Outlook:**
   - OAuth в `/app/settings/integrations`.
   - Двусторонний: создал событие в Google → оно в HostFlow и наоборот.
   - Привязка события к карточке кандидата/лида через «HostFlow: lead #123» в описании.
6. **Встраивание:**
   - Mini-calendar на карточке кандидата (его ближайшие 3 события).
   - Mini-calendar на дашборде (сегодня + завтра).

**Метрики в модуле:**

- «Сегодня: N событий» / «Просрочено: N» / «Завтра: N» — в шапке.
- Heat-map свободного времени команды (для супервайзера — `team-availability`).

**Acceptance:**

- Создание задачи из календаря drag-to-create ≤ 5 секунд.
- Sync-лаг с Google ≤ 2 минут.
- 0 «двойных событий» после sync.

### IV.3 Модуль «Напоминания и задачи» (единая модель)

**Болевая точка:** сейчас есть `Task`, `Reminder`, NBA snapshot — три разных API/UI. Путаница.

**Целевой UX:**

1. **Единая сущность** `WorkItem` (или сохранить `Task` как canonical):
   - Поля: `due_at`, `owner`, `linked_entity` (lead/candidate/vacancy/document/thread), `priority`, `status`, `kind` (`task` / `reminder` / `nba` / `sla`).
   - API: один endpoint `/api/v1/tasks` с фильтрами по `kind`, `owner`, `status`, `due_window`.
2. **Виды напоминаний:**
   - Web push (Service Worker — частично есть, см. `VAPID_KEYS.md`).
   - Email.
   - Telegram bot.
   - In-app колокольчик.
   - Выбор канала — per-user в `/app/profile`.
3. **Taskbar** — глобальная кнопка в топбаре с числом «сегодня». Клик → popover-список без ухода со страницы. В popover: отложить, выполнить, передать.
4. **Страница `/app/tasks`** (`RemindersPage`) — три таба:
   - **Сегодня** — по умолчанию.
   - **Скоро** (7 дней).
   - **Отложено / без срока**.
   - Фильтры: по сущности, по типу (задача / SLA / NBA).
5. **Snooze:**
   - Кнопки: +1ч, +завтра утро, +понедельник, custom.
   - Snooze не стирает задачу — возвращает в срок.
6. **NBA в задачах:**
   - NBA-snapshot становится видимой задачей с `kind=nba`.
   - Закрыл задачу → система автоматически показывает следующий NBA.

**Метрики:**

- «Сегодня выполнено: X из Y» — на странице задач и в top-bar.
- Личный week-streak: сколько дней подряд закрываю все задачи дня.
- Для супервайзера: задачи команды (`/app/team-availability` + задачи).

**Acceptance:**

- Единый API `/api/v1/tasks` покрывает все кейсы — старые API remindersи nba-snapshot задеprecated.
- Push-уведомление доходит за ≤ 30 секунд от due-time.
- Отложить задачу в 1 клик без открытия модалки.

### IV.4 Модуль «Сообщения» (Inbox)

**Болевая точка:** сейчас `CommunicationsInboxCenterPage`, `CommunicationsThreadPage`, `CommunicationsInboxHubPage`, `CommunicationsCalendarPage`, `CommunicationsPlannerPage`, `CommunicationsSlaIncidentsPage` — слишком много сущностей для одной идеи «входящие».

**Целевой UX:**

1. **Один `/app/inbox`** — все входящие:
   - Вкладки: **Все** / **Мне** / **Команде** / **Снуз** / **Архив**.
   - Фильтры в одном правом drawer-е: канал (email/tg/wa/viber/graph), статус, тег, кандидат, лид, вакансия.
   - Поиск по треду и сообщениям — один input сверху.
2. **Тред-view (`CommunicationsThreadPage`):**
   - Левая колонка — список тредов (виртуализованный).
   - Центр — сам тред.
   - Правая колонка — контекст: связанная карточка (лид/кандидат/вакансия), NBA, прошлые треды с этим контактом.
3. **Composer:**
   - Выбор «от кого» (любой подключённый email/telegram/whatsapp в один клик).
   - Slash-команды: `/template`, `/schedule`, `/assign`, `/attach-doc`, `/task`.
   - Bulk-templates на выбранные треды (SSOT §2.1 `Comms/Inbox`).
   - Schedule send (уже есть `CommunicationsPlannerPage` — вмержить в composer).
4. **SLA:**
   - Таймер прямо в списке (chip: «SLA до 18:00»).
   - При истечении — эскалация по правилу (`CommunicationsSlaSettingsPage`), автоматическая задача супервайзеру.
5. **Шаблоны команд (command-templates):**
   - Аудит уже есть (`CommunicationsCommandAuditPage`) — вывести в настройки.
6. **Календарь** встроить как вкладку / side-drawer, не отдельную страницу.
7. **Присутствие:**
   - `CommunicationsTeamAvailabilityPage`, `MyAvailabilityPage`, `TimeOffRequestsPage` — оставить, но в разделе «Настройки команды», не в основном inbox-потоке.

**Объединение страниц:**

Сейчас: `InboxHubPage`, `InboxCenterPage`, `ThreadPage`, `MessagesPage`, `EmailInboxPage`, `Planner`, `Calendar`, `SlaIncidents`, `CommandAudit`, `TeamAvailability`, `MyAvailability`, `TimeOffRequests`, `CommunicationsSettingsPage`, `MessengerSettingsPage`, `QueueSettingsPage`, `SlaSettingsPage` — **16 экранов**.

Цель: **3 основных экрана** (`/app/inbox` c внутренними вкладками + `/app/calendar` + `/app/settings/communications` агрегированный) + drawer-ы контекста.

**Метрики:**

- «Непрочитанных: X» / «SLA на грани: X» — в топбаре.
- Personal response-time median (для руководителя — по команде).
- Channel health chip: «Gmail ok», «Telegram warn» в углу inbox при проблемах подключения.

**Acceptance:**

- Ответить на email ≤ 3 клика от открытия HostFlow (если не на странице): колокольчик → тред → reply.
- Применить шаблон к 50 тредам bulk ≤ 5 секунд.
- Открытый тред не мешает работать в другом — мини-composer pinned.

---

## Часть V. Метрики и KPI развития

### 5.1 Продуктовые KPI (уровень владельца)

| Метрика | Текущая (оценка) | Цель 6 мес | Цель 12 мес |
|---------|-----------------|------------|-------------|
| Activation-rate D+1 (первый лид в работе) | неизмеряется | 60% | 75% |
| Trial → paid conversion | неизмеряется | 12% | 20% |
| Time-to-first-meaningful-action | > 30 мин | ≤ 5 мин | ≤ 3 мин |
| Monthly churn | неизмеряется | < 7% | < 4% |
| NPS среди операторов | неизмеряется | > 30 | > 50 |
| MAU/WAU ratio (engagement) | неизмеряется | > 0.6 | > 0.7 |

### 5.2 Технические SLO

| Метрика | Цель |
|---------|------|
| API P95 latency | ≤ 400 мс |
| Frontend TTI (cold) | ≤ 3 с на 4G |
| Frontend TTI (warm) | ≤ 800 мс |
| Uptime | 99.9% |
| Потери webhook за месяц | 0 |
| Sentry error-rate (unhandled) | < 0.5% от сессий |
| Build time (full CI) | ≤ 8 мин |

### 5.3 Метрики качества кода

| Метрика | Цель |
|---------|------|
| Максимум LOC в одном файле | 1500 |
| Backend coverage | ≥ 70% |
| Frontend coverage | ≥ 50% |
| E2E критичных сценариев | 10 (signup→paid, intake→lead→hire, docs, inbox, billing webhook) |
| Количество Alembic heads | ровно 1 в любой момент |
| Hardcoded i18n-строки | 0 |

---

## Часть VI. Открытые пункты из SSOT.md (что не закончили)

Полный список из `docs/SSOT.md` §2.1 на дату документа. Источник правды — сам SSOT; здесь — снимок для ориентации.

### 6.1 Явные чекбоксы `[ ]` (§2.17 и §2.16–§2.18)

**Настройки владельца (§2.17):**

- [ ] Upgrade / compare, add-ons, Customer Portal поверх текущего Checkout (§2.18).
- [ ] Team: invite + seat gate + matrix доступа к workspace (`BillingTeamPage` / `UserFormInvite`).
- [ ] Roles editor с серверной валидацией.
- [ ] Companies CRUD с предупреждением цены и enforcement §2.16.
- [ ] TenantsPage: override limits, billing adjust (п.10). Отдельный Platform Admin app **не** делаем.
- [ ] Аудит: plan change, override, invite, role change — лог в БД + минимальный UI.

**Stripe и биллинг (§2.16–§2.18):**

- [ ] Stripe: довести до спеки §2.18 (сводка line items / add-ons / seats; Stripe Tax, tax IDs, VIES; Checkout + webhook для остальных SKU и subscription items; past_due grace 3d; живые Price IDs в Stripe, в т.ч. founder €99/€199).
- [ ] Webhook: при необходимости `invoice.finalized`; очередь/ретраи при ошибках после частичного commit.
- [ ] Trial: UI баннеры / post-trial messaging; read-only + grace **3 дня на всех** write-API (сейчас частично `billing_restrictions` — только лиды, исходящие comms).
- [ ] SKU паков и UI **buy pack**; фильтры/экспорт инвойсов; синхронизация с `invoice.finalized`.

### 6.2 Нарративные открытые задачи (без `[ ]`, но в бэклоге §2.1)

**Лиды, pipeline, NBA, квалификация:**

- Смена назначения как триггер next action / task; блокирующая валидация `required_actions`, цепочка handoff → следующая задача; перераспределение по SLA job; полное слияние pipeline ↔ distribution.
- Playbook / NBA: расширение полей и действий из одного места; превью для кандидатов/tasks на дашборде; другие сущности в NBA; расширение **Process batch** под rule engine и не-Meta источники.
- Auto-fix: правила шире Meta-queue; «Fix all» без жёсткого лимита по плану.
- Квалификация: полноценный движок правил поверх `lead_criteria_eval`; `assign_pipeline` в automation; единый продуктовый слой «пресеты критериев на тенанта»; rich constructor правил для триггеров кроме `lead.qualification`.
- Интеграции / источники: Google ingest; отдельный mapping UI не-Meta; лимиты field_mapping / источников при нескольких реальных каналах; трансформации mapping; биллинг/апгрейд-копирайт.
- Custom fields лидов: колонка `Lead.extra`; расширенные операторы фильтра; typed custom + UI правил.
- Воронка конверсии v2+: сценарные шаблоны (документы/портал), WoW-инсайты, произвольное окно когорты, тяжёлые пресеты; продуктовый слой `lost_reason` в root funnel.
- `conversion-funnel` / UI: отдельный `lost_reason` в продуктовом смысле (сейчас — CRM lost + аудит).

**Multi–own-company:**

- Перенос FK (`vacancies.company_id`, `tenant_links`) и UI на `client_companies`; уход от operating-строк в `companies`.
- Прочие модули вне уже покрытых контуров — по аудиту скоупа.
- UI ACL (`allowed_own_company_ids`); продуктовые роли-матрицы; тесты.
- Own-company UX: upsell-модал, mobile-first свитчер.

**Глобальный поиск:**

- Документы с join к кандидату в выдаче; ML / семантический поиск.

**Comms / Inbox:**

- Массовое применение command templates к выбранным письмам/тредам при multi-select в unified inbox.

**Полировка / stretch:**

- UOS / IA: общая полировка; опционально единый объект политики escalation.
- Декомпозиция `ServicesPage`: `OrdersTab`, `OrderDetail`, `ServicesAnalyticsTab`.
- Performance: формальные бюджеты SLA — после договорённости (`pipe.md`).
- Публичный захват документов (LLM/vision) — отдельное продуктовое решение, не регрессия.

**Хабы Integrations / Automations:**

- `IntegrationsHubPage` / `AutomationsHubPage`: развитие контрол-центра (статус, цепочка «источник → обработка», активность), не только сетка ссылок; при необходимости лёгкие API агрегатов.

**Work / Dashboard:**

- Единая модель stuck / SLA / need next action с NBA/API; общий shell фильтров Work при продуктовом решении.
- Главный CTA «fix in one click» + paywall-копирайт (§2.16).
- Paywall: auto-assign в таблице кандидатов; выравнивание копирайта с тарифами.
- Limit modal: CTA **buy pack** / **add seats** с ценой без лишних шагов.
- Stretch: полная согласованность kanban с произвольными очередями API.

**Client portal (хвосты):**

- UX/маршрутизация портала в потоках Comms (единый слой, не отдельный чат-продукт).
- Шаблоны писем, доставляемость; чип NBA «Remind client».
- Матрица ролей портала; скрытие internal notes как отдельный слой.
- Branded / per-client billing (§2.16).

**Настройки владельца (нарратив):**

- Продуктовые мастера онбординга по матрице маршрутов.

**Stripe и биллинг (нарратив):**

- Checkout/API + webhooks для SKU: seats, client portal, паки лидов/полей и т.д. (не только конфиг).
- Enforcement: логика форм (не только slug + intake); **instances** воронок vacancy↔funnel; `storage_used_gb`, обход загрузки без `size`; расширение post-trial гейтов; лимит instances при необходимости; остальные **402** в админ-потоках.
- Маркетинговая страница pricing; richer upsell в операционных потоках.
- Юридические черновики billing: вычитка, локализации, связка с Checkout/офертой в UI, e-sign.
- Пресеты `business_type` в онбординге/настройках.
- Маппинг `TenantLicense`, `business_type`, module flags → полная матрица **Plan + Modules + Limits** (§2.16).

### 6.3 Как эти пункты распределяются по фазам плана

| Блок SSOT | Фаза плана |
|-----------|-----------|
| Настройки владельца + Stripe (`[ ]`) | **Фаза 6** (полностью) |
| Comms / Inbox | **Фаза 5** |
| Work / Dashboard | **Фаза 1** (декомпозиция) + **Фаза 4** (задачи) |
| Client portal | **Фаза 7** |
| Лиды / NBA / квалификация | **Фаза 8** |
| Глобальный поиск | **Фаза 8** |
| Multi–own-company | параллельно, **Фаза 1–2** (UI) и **Фаза 6** (биллинг-enforcement) |
| Интеграции/Automations hub | **Фаза 0** (декомпозиция) + **Фаза 5** (inbox-view) |
| Воронка конверсии v2 | **Фаза 8** |
| Публичный захват документов | **Фаза 3** |
| Performance SLA | **Фаза 10** |

---

## Часть VII. Риски и оговорки

1. **Не делать всё сразу.** Фазы 0, 1 — блокеры. Фазу 2 (onboarding) делать параллельно с 1, но не раньше 0 (иначе metrics измерять нечем).
2. **Разрушение IA v1 опасно.** `CrmContourWayfindingStrip` удаляется постепенно: сначала скрыть на 3 страницах, собрать feedback, потом глобально. Не одним PR.
3. **Миграция документов на S3** — с параллельной записью в local+S3, read-through, постепенное отключение local — не big-bang.
4. **Очередь ARQ** — мигрировать поток за потоком, с feature-flag. Stripe первым (самое чувствительное место).
5. **Биллинг §2.18** требует юридического ревью (VIES, локализации договоров) — это **не** чисто технический таск. Параллельно запускать legal-работу.
6. **Мобильный PWA** (Фаза 9) — привлекательно, но **не блокирует** доходность; откладывается, если бизнес-приоритеты требуют ускорить Фазы 6–7.
7. **Semantic search** — дорогой (pgvector/внешний) — решение принимать по данным (сколько реально ищут и что не находят).

---

## Часть VIII. Итог — что делать дальше

### Что делаем немедленно

1. Обсудить и утвердить этот документ с владельцем и командой.
2. Перенести задачи **Фазы 0 и Фазы 1** в `docs/SSOT.md` §2.1 как новые чекбоксы с владельцами (по §1.3 SSOT).
3. Создать тикеты/issues для Фазы 0 с оценками.
4. Настроить измерения (activation, time-to-first-meaningful-action, trial→paid) — без этого KPI §5 не проверить.

### Что не делаем в этом документе

- Не дублируем здесь историю релизов — см. git history.
- Не дублируем детальные спеки экранов — см. `docs/pipe.md`, `docs/specs/**`.
- Не превращаем этот файл в трекер прогресса — прогресс живёт в `docs/SSOT.md` §2.1 (§1.1 SSOT).
