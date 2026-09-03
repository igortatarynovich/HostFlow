# HostFlow — Security SSOT (Single Source of Truth)

**Статус:** канонический инженерный документ.  
**Аудитория:** backend, frontend, platform, QA, product (где касается данных и согласий).

---

## 0. Архитектурный принцип

HostFlow проектируется как **security-first multi-tenant document platform** с recruitment-функциями, а не как «обычный CRM + security сверху».

Причина: сочетание **tenant isolation**, **cross-tenant handoff**, **документов удостоверяющих личность**, **порталов**, **автоматизаций** и **публичных потоков** создаёт класс рисков выше типичного ATS.

---

## 0a. Security Non-Negotiables (останавливаем shortcuts на review)

Нарушение любого пункта ниже требует **явного исключения** в PR (обоснование + security review + план burn-down).

1. **Нет публичного хранения документов** без контроля доступа (только приватный bucket / контролируемый FS + проверка прав на каждый байт).
2. **Нет доверия к `tenant_id` / `X-Tenant-Id` с фронта** как источнику истины для изоляции.
3. **Нет raw cross-tenant analytics** (агрегаты без жёсткого tenant predicate + RLS).
4. **Нет `SECURITY DEFINER` / функций с обходом RLS** без обязательного аудита и явной модели доступа.
5. **Нет support / superadmin impersonation** без justification (reason) в аудите и ограничений по времени (см. §6).
6. **Нет экспорта** без audit trail (actor, scope, row count, channel).
7. **Нет permanent signed URLs** на CLASS 2–3.
8. **Нет auth-логики «только на фронте»** — сервер остаётся источником истины.
9. **Нет фильтрации hidden fields только в UI** — сериализация API обязана respect RBAC/data class.
10. **Нет `text(f"...")` / динамического SQL** без bound parameters (CI: `backend/scripts/check_sql_fstring_text.py`).

---

## 0b. Background execution context (следующий архитектурный bottleneck)

HTTP-запросы часто безопасны, а **фоновые джобы** (automations, async workers, reminders, webhooks, scheduled exports, notifications) — нет: легко потерять tenant context.

**Каждый job / worker message обязан нести минимум:**

- `tenant_id`
- `actor_id` (или явный `SYSTEM` + причина)
- `access_scope` / relationship к сущности (см. ACCESS CONTEXT §5)
- `correlation_id` (trace)

**Worker обязан:**

1. Установить DB tenant context (`set_config('app.tenant_id', ...)`) до любых запросов к tenant-данным.
2. Прокинуть audit context (кто инициировал цепочку).
3. Не выполнять «аналитические» SQL без тех же guardrails, что и HTTP layer.

**Как именно биндится tenant (canon, измерено 2026-08-30 в TI-5):**

1. **Только через `bind_tenant_context_to_session`** (или `tenant_enforced_session` для job-ов). Он и
   объявляет tenant на сессии, и ставит контекст в БД.
2. **Контекст обязан быть transaction-local** — третий аргумент `set_config` равен `true`. Session-local
   binding (`false`) переживает транзакцию, сессию и запрос и остаётся на соединении в пуле; следующий
   заимствователь, который сам tenant не объявил, наследует его и читает чужие строки, считая себя
   без scope. Это единственный известный класс, который **раскрывает** данные, а не отказывает.
   Enforcement: `backend/tests/security/test_tenant_binding_call_sites.py::test_no_session_local_tenant_binding`.
3. **Объявленный scope (`session.info["tenant_id"]`) и контекст в БД — одна истина.** Хук
   `_bind_tenant_on_transaction_begin` переприменяет объявленный scope на каждом `after_begin`, а
   `after_begin` срабатывает и для savepoint-ов. Поэтому любое изменение scope меняет обе стороны —
   иначе первый `begin_nested()` молча возвращает предыдущий tenant.
4. **Cross-tenant операция — только через `acting_for_tenant`** (именованная, ограниченная блоком,
   восстанавливающая scope) либо через privileged соединение (`privileged_session_maker` и две
   названные platform-зависимости). Ручной `set_config` в обход этих путей — нарушение.

Обоснование и измерения: [`tenant-isolation-enforcement.md`](../specs/tasks/tenant-isolation-enforcement.md).

Операционная программа runtime-guarantees, telemetry, detection и scorecard ведётся отдельно: [`runtime-roadmap.md`](./runtime-roadmap.md) (не раздувает SSOT).

---

## 1. Угрозы верхнего уровня (summary threat model)

| Категория | Примеры | Приоритет |
|-----------|---------|-----------|
| Cross-tenant data leak | сломанный RLS, поиск/экспорт без контекста, IDOR | P0 |
| Document exposure | публичные URL, длинные signed URL, неверные ACL, CDN-кеш | P0 |
| Неверные права | скрытые поля в API, client видит internal notes, recruiter видит payroll | P0 |
| Account compromise | brute force, reuse, session/JWT theft | P0–P1 |
| Опасные интеграции | поддельные webhooks, SSRF, malicious uploads | P0–P1 |
| Insider abuse | массовый экспорт, массовое скачивание документов | P1 |

Детализация по поверхностям: `docs/security/threat-models/`.

Interactive Growth demo (per-tenant sample pack, no shared guest tenant in Wave-1): [`threat-models/interactive-demo.md`](threat-models/interactive-demo.md).

Verified Growth signup (SignupIntent → verify → complete; trial on TenantLicense only after complete): [`threat-models/verified-self-service-signup.md`](threat-models/verified-self-service-signup.md) · [`ADR-041`](../specs/architecture/ADR-041-verified-self-service-signup.md). Candidate magic-links remain [`threat-models/candidate-portal.md`](threat-models/candidate-portal.md).

Forms Platform C2+C3 (frozen publication Contract Identity; Builder FormDefinition ↔ Draft only, no Adapter publish): [`threat-models/forms-platform.md`](threat-models/forms-platform.md). Public intake tokens remain [`threat-models/public-links.md`](threat-models/public-links.md).

Documents Platform E3–E5 (authenticated Hub metadata resolve via Document Link, not file download; `candidate_id` column dropped): [`threat-models/documents-platform.md`](threat-models/documents-platform.md). Uploads / MIME / storage ACL remain [`threat-models/document-uploads.md`](threat-models/document-uploads.md).

---

## 2. Классификация данных (Data Classification)

Все поля, файлы и события должны быть отнесены к классу. Класс определяет **RBAC**, **аудит**, **экспорт**, **TTL ссылок**, **хранение**.

### CLASS 0 — Public

- Лендинги, маркетинговые тексты, публичные вакансии без персональных данных.

**Правила:** можно кешировать публично; без PII.

### CLASS 1 — Internal

- Операционные заметки внутри тенанта (не для клиента), метаданные вакансий без персональных идентификаторов.

**Правила:** tenant scope + RBAC; не отдавать в client/candidate portal без явного разрешения.

### CLASS 2 — Confidential

- Профили кандидатов, телефон, email, комментарии рекрутера, переписка с клиентом, большинство HR-операционных данных.

**Правила:** RLS + RBAC; аудит на критичные чтения/изменения (см. §8); экспорт ограничен ролью и rate limit.

### CLASS 3 — Highly Sensitive

- Паспорта, карты побыта, визы, разрешения на работу, меддокументы, payroll, PESEL и иные государственные идентификаторы.

**Правила:**

- Строже RBAC (минимальная выдача по умолчанию).
- **Обязательный аудит** на просмотр, скачивание, генерацию ссылки, экспорт.
- Ограничения на экспорт (роль, объём, частота); watermarking — целевое улучшение после baseline.
- **Короткий TTL** signed URL; запрет «вечных» ссылок.
- Логирование **причины доступа** (reason) — обязательное поле в audit trail для действий superadmin и массовых операций (см. §6).

---

## 3. Tenant isolation

### Правила

1. **PostgreSQL RLS** на всех tenant-scoped таблицах; новые таблицы с `tenant_id` не мержатся без политики.
2. **Ни одного запроса** к tenant-данным без установленного контекста сессии (`current_setting('app.tenant_id')` и согласованные доп. ключи, если введены в политиках).
3. **Backend не доверяет** `tenant_id` / `X-Tenant-Id` с клиента как источнику истины — только проверенная связка пользователь ↔ тенант (JWT/session + membership).
4. Любые пути: **list, search, export, bulk, reports, WebSocket, notifications, attachments, uploads, audit logs** — подчиняются тем же правилам.
5. **Runtime guard на границе SQLAlchemy-сессии:** для сессий с `tenant_rls_enforcement=True` любой `execute`/`stream` в Postgres блокируется, пока не выполнен `bind_tenant_context_to_session` (см. `backend/app/db/tenant_session.py`, `backend/app/db/deps.py`). Детали и backlog — `docs/security/runtime-roadmap.md` §Phase 1.

### Измеренное состояние (2026-08-28) — правило 1 не выполняется

Правила выше остаются **нормативными**. Ниже — факт, измеренный на dev-кластере (схема на head `202608250002_merge_e5_drop_and_adr036_heads`), чтобы канон не утверждал непроверенное:

| Факт | Значение |
|------|----------|
| Таблиц с `tenant_id` | **226** |
| Из них с включённым RLS | **124** |
| Из них **без политики вовсе** | **102** |
| Таблиц с `FORCE ROW LEVEL SECURITY` | **0** |
| Роль приложения `hostflow` | суперпользователь, `rolbypassrls = true`, владелец всех таблиц |
| Провижининг ограниченной роли в репозитории | отсутствует |

Следствие: для роли, под которой работает приложение, RLS обходится дважды — по `BYPASSRLS` и по владению таблицами без `FORCE`. Изоляцию сегодня фактически обеспечивает только фильтрация на уровне приложения (правила 2, 3, 5 — они реализованы и работают: `backend/app/db/deps.py`). Тесты `backend/tests/api/test_tenant_isolation.py` падают именно по этой причине.

KPI §19 «RLS coverage (tenant tables) 100%» — это **цель**, а не текущее состояние: измеренное покрытие 124/226 ≈ 55%.

**Решение (2026-08-28):** разрыв закрывается **до RC** — правило 1 и KPI §19 остаются как есть, runtime подтягивается к ним. Владелец работ: [tenant-isolation-enforcement.md](../specs/tasks/tenant-isolation-enforcement.md) TI-1…TI-4 (было [U-6](../specs/gates/v1-unowned-work-register.md)). До этого [Release Readiness Gate](../specs/gates/release-readiness-gate.md) **RR5** не может быть отвечен `PASS`, а доказательство изоляции должно быть получено **под ролью производственного вида**, не под суперпользователем.

**Состояние на 2026-08-30 — покрытие закрыто с одним названным исключением.** Формулировка от 2026-08-29 («все 226 таблиц несут политику») была верна относительно того, что измерял guard, и неверна как утверждение: guard узнавал tenant-скоуп по буквальному имени колонки `tenant_id`, поэтому три таблицы со скоупом через `agency_tenant_id` / `client_tenant_id` никогда не попадали в измерение. Две из них — `candidate_handoffs` и `candidate_handoff_snapshots`, где лежат кросс-тенантные представления кандидатов и их персональные данные — были **без RLS вообще**. Закрыты миграцией `202608290009_rls_handoff_dual_leg`; guard теперь узнаёт любую колонку, оканчивающуюся на `tenant_id`, и дополнительно требует политику, допускающую запись (у `tenant_links` политики покрывали только чтение, из-за чего любая вставка отклонялась по умолчанию).

**Состояние на 2026-08-30 (TI-5 закрыт) — покрытие закрыто полностью, без исключений.** `tenants`
закрыта политикой (`202608300001_rls_tenants`) после того, как появился именованный privileged путь для
superadmin-поверхности; `rls_uncovered_tables.txt` пуст. Измерено на БД, собранной с нуля до head
(`scripts/security/measure_policy_coverage.sql`):

| Что измерено | Значение |
|---|---|
| Tenant-scoped таблиц (любая колонка, оканчивающаяся на `tenant_id`, плюс `tenants`) | **230** |
| RLS включён | **230 / 230** |
| Покрытие чтения / записи политиками (по глаголам) | **230 / 230** |
| `FORCE ROW LEVEL SECURITY` | 213 / 230; **17** названных исключений, объявленный список (`scripts/security/rls_force_exceptions.txt`) совпадает с измеренным |
| Роль приложения `hostflow_app` | не суперпользователь, `rolbypassrls = false`, не владелец таблиц |

Исключения `FORCE` — это исключения из обхода политики **владельцем**, а не из самой политики:
ограниченная роль подчиняется политике на всех 230 таблицах. Двухролевой прогон полного набора тестов
даёт **0 падений, специфичных для ограниченной роли** (и 11 падений, специфичных для владельца — это и
есть доказательство, что изоляционные тесты не вакуумны). Остаётся не разработка, а переключение
`ASYNC_DATABASE_URL` в деплое и прогон изоляционного набора под этой ролью в CI (зависит от **OL-2**).

| Факт | Значение |
|------|----------|
| Таблиц с `tenant_id` без политики | **0** (было 102) |
| Таблиц со скоупом через `*_tenant_id` без политики | **0** (было 2, обе без RLS) |
| Таблиц с политиками только на чтение (запись запрещена по умолчанию) | **0** (была 1 — `tenant_links`) |
| Tenant-скоуп таблиц, оставленных без политики намеренно | **1** — `tenants`, владелец TI-5 |
| Политик, способных упасть с ошибкой вместо отказа | **0** (было 126) |
| Таблиц с политикой и `FORCE ROW LEVEL SECURITY` | все, кроме **15** названных исключений |
| Роль приложения для запросов | `hostflow_app` — не суперпользователь, без `BYPASSRLS`, не владелец (`scripts/security/provision_app_role.sql`) |

**Именованное исключение из `FORCE` (2026-08-29).** `FORCE ROW LEVEL SECURITY` распространяет политики и на владельца таблицы, поэтому его нельзя применить к 2 identity-таблицам (`users`, `user_memberships`) и 13 платформенным справочникам (`ep_*`, `fr_*`, `pe_*`): аутентификация ищет пользователя по e-mail до того, как тенант известен, а платформенные строки (`tenant_id = ''`) сеет владелец. Обход изоляции сведён к одному аудируемому соединению — `backend/app/auth/identity_session.py` — и набор исключений проверяется тестом `backend/tests/security/test_rls_force_exceptions.py`, который падает и при росте набора, и когда исключение стало ненужным.

**Роль в окружениях ещё не переключена, и условие переключения изменилось (2026-08-30).** Решение от 2026-08-29 — «переключаем после TI-4» — не выдержало измерения: вся superadmin-поверхность `/api/v1/platform` (за `require_superadmin()`) работает на непривязанной сессии и по замыслу читает и пишет любой тенант, поэтому под ограниченной ролью она отказывает не только на `tenants`. Условие переключения — **после TI-5**: названное привилегированное соединение для платформенного администрирования (аудируемое, как identity-путь), два публичных резолвера тенанта на общий примитив, проверка уникальности slug и перечисление тенантов на соединение владельца, и только затем политика на `tenants`. См. [tenant-isolation-enforcement.md](../specs/tasks/tenant-isolation-enforcement.md) § TI-5.

### Канонические спеки

- `docs/specs/architecture/multi_tenant_model.md`
- Миграции RLS в `backend/alembic/versions/`
- Разрыв enforcement: [tenant-isolation-enforcement.md](../specs/tasks/tenant-isolation-enforcement.md)

---

## 4. RBAC и policy layer

### Роли (сопоставление с кодом)

Каноническая матрица: `docs/specs/architecture/rbac_matrix.md`  
(роли вида `superadmin`, `administrator`, `supervisor`, `recruiter`, `client_manager`, `candidate`, `viewer` — не дублировать ad-hoc ветвлениями в handlers.)

### Запрещено

- Разбросанные `if user.role == ...` как единственная защита для write/read чувствительных данных.

### Требуется

- **Централизованный policy layer**: переиспользуемые guards, permission service, единые точки проверки для API, экспорта, поиска, вложений.
- Проверка **скрытых полей** в сериализации ответов (не полагаться только на UI).

---

## 5. Handoff и cross-tenant visibility (ACCESS CONTEXT)

Handoff — **контролируемая** видимость между тенантами, а не «общий кандидат».

### Модель доступа

Каноническая формулировка: не только «tenant владеет кандидатом», а **«tenant имеет отношение доступа к сущности (кандидат/документ/процесс)»**.

### Типы отношения (логические; реализация — в policy + БД + audit)

| Тип | Смысл |
|-----|--------|
| `OWNER` | Полный контроль в рамках политики роли. |
| `SHARED_READ` | Клиент/партнёр видит согласованный срез: статус, документы по allowlist, timeline — **без** internal notes, source data, других вакансий. |
| `SHARED_PROCESSING` | Продолжение процесса у работодателя/клиента в рамках контракта handoff. |
| `TRANSFERRED` | Смена ownership по правилам продукта; старый и новый владелец явно отражаются в аудите. |

### Требования

- Отражено в **policy layer**, **audit**, **RLS / представлениях или предикатах**, **export rules**, **notifications** (не утекать в чужой тенант).
- Отдельный threat model: `threat-models/handoff.md`.

---

## 6. SUPERADMIN и platform-доступ

`superadmin` — **отдельный класс риска** (insider + полный обход изоляции при ошибке).

### Запрещено

- «God mode» в одну строку: `if user.is_superadmin: return True` без контекста, аудита и ограничений.

### Обязательно

- **Mandatory audit:** кто, зачем (reason), что открыл/изменил, длительность сессии elevation, экспорты.
- **UI banner:** явная индикация elevated / impersonation (например `SUPERADMIN ACCESS ACTIVE`).
- **Time-limited elevation** (целевое значение, например 30 минут) — проектировать в сессии/claims; до внедрения в код — требование к дизайну фич.
- Dual authorization для enterprise — backlog, не блокер MVP при сильном аудите.

---

## 7. Документы и object storage

Принципы:

- Приватное хранилище; **нет** предсказуемых публичных URL и прямого доступа обходом API.
- **Signed URL** с коротким TTL; проверка права **до** выдачи URL.
- MIME/extension validation, лимиты размера, antivirus — по политике upload (§9).
- PDF/image sanitization — по мере внедрения; до этого — минимизация поверхности (запрет SVG/HTML как «документ»).

Детали: `docs/specs/architecture/object_storage.md`, `threat-models/document-uploads.md`, `threat-models/public-links.md`, `threat-models/documents-platform.md` (E3–E5 metadata resolve, not bytes).

---

## 8. Аутентификация и сессии

Минимальный baseline:

- Хэширование паролей (argon2/bcrypt), rate limiting на login/password reset/public intake.
- Refresh rotation, инвалидация сессий при смене пароля/компрометации.
- Secure cookies: `HttpOnly`, `Secure`, `SameSite` (Lax/Strict по контексту).
- **MFA** для `superadmin` и владельцев тенанта (administrator/owner) — целевое требование; до включения — фиксировать в backlog с датой.

---

## 9. Политика загрузки файлов (Upload policy)

1. Квоты на пользователя/тенант/кандидата.
2. Запрет исполняемых и двойных расширений; проверка magic bytes, не только `Content-Type`.
3. Лимит размера; защита от zip-bomb на уровне распаковки (если применимо).
4. Изолированный upload flow для candidate portal: **upload token ≠ auth token** (см. `threat-models/candidate-portal.md`).
5. Malware scan — обязателен для production с CLASS 3; для staging — предупреждение в CI.

---

## 10. Экспорт данных

Экспорт — **высокий insider risk**.

Обязательно:

- Audit: кто, что (тип отчёта), сколько строк, когда, канал (UI/API).
- Rate limits и batch limits.
- RBAC: client/candidate — по умолчанию без массового экспорта чужих данных.

Опционально позже: watermarking, honey rows, anomaly alerts.

---

## 11. Интеграции и webhooks

- Подпись webhook (HMAC + secret rotation), replay protection (timestamp/nonce), allowlist исходящих URL против SSRF.
- Входящие загрузки и парсинг — в sandboxed expectations (см. `threat-models/webhooks.md`, `threat-models/automations.md`).

---

## 12. Security headers (HTTP)

Обязательный baseline для edge (Nginx/Caddy) и приложения (где уместно):

- `Content-Security-Policy`
- `X-Frame-Options` или CSP `frame-ancestors`
- `Referrer-Policy`
- `Permissions-Policy`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security` (production)

Конфиг деплоя: `deploy/nginx/hostflow.conf` и аналоги — поддерживать в согласовании с этим списком.

---

## 13. Наблюдаемость и детекция

Минимум сигналов:

- Brute force / failed auth spikes.
- Необычные экспорты и массовые скачивания документов.
- Попытки tenant enumeration.
- Пики отказов в авторизации (403) по пользователю/IP.

Алерты: Slack/email/admin center — по мере появления централизованного логирования.

---

## 14. Управление секретами

- Нет секретов в git; отдельные prod/dev; ротация webhook secrets.
- Нет «секретов» во frontend bundle.

---

## 15. Retention и GDPR/RODO (high level)

- Consent: время, источник, версия текста.
- Right to delete: soft delete, анонимизация, политика хранения по классам данных.
- Экспорт субъекта данных — с audit.

Юридические формулировки и DPA — вне этого файла; инженерная реализация должна быть **трассируема** к требованиям legal.

---

## 16. Incident Response (IR)

Операционные шаги для команды: раздел **Incident Response runbooks** в `docs/security/security-review-checklist.md`. Ниже — краткая выжимка для triage.

### A. Утечка данных

1. Отозвать/инвалидировать URLs и сессии затронутого scope.  
2. Ротировать секреты, если есть риск ключа.  
3. Изолировать тенант (feature flag / read-only).  
4. Post-mortem + тикеты на предотвращение.

### B. Компрометация учётных данных

- Force logout, сброс refresh, аудит последних действий.

### C. Malware upload

- Карантин файла, ретро-скан, аудит касаний файла.

---

## 17. Security Test Matrix (автоматизация)

Обязательные классы тестов в CI (инкрементально покрывать новые endpoint-ы):

### A. Tenant isolation

| Сценарий | Ожидание |
|----------|----------|
| Same tenant | 200 (или бизнес-ошибка, но не утечка) |
| Different tenant | 403/404 без leak в теле |
| Missing tenant context | fail closed |
| Bulk export / search cross-tenant | fail |

### B. RBAC

Матрица действий по ролям согласована с `rbac_matrix.md`; для каждого нового write — негативные тесты.

### C. Upload

| Файл | Ожидание |
|------|----------|
| Валидный PDF | pass по политике |
| EXE переименованный в `.pdf` | blocked |
| Zip bomb / oversized | blocked |
| SVG с JS | blocked |

### D. Signed URL

| Сценарий | Ожидание |
|----------|----------|
| Expired | denied |
| Другой tenant | denied |
| Replay / guessing | denied |

---

## 18. Dependency security

- **Python:** pin dependencies; `pip-audit` (или аналог) в CI; критические CVE → блок merge.
- **Docker:** минимальные образы; сканирование (Trivy и т.п.).
- **Frontend:** `npm audit` / dependency review в CI.

### 18.1 Known constraint — Starlette vs FastAPI pin

Runtime pin: `fastapi==0.115.6` + `prometheus-fastapi-instrumentator==7.0.0` (see `AGENTS.md`).
That FastAPI release resolves `starlette` into the `0.41.x` band. Several advisory fix versions require
`starlette>=0.47` / `1.x`, which is incompatible without a coordinated FastAPI + instrumentator upgrade.

Until that upgrade lands as its own dependency PR, `security-gates` pip-audit may ignore the listed
Starlette advisory IDs in `.github/workflows/security-gates.yml` (commented next to `--ignore-vuln`).
New **critical** findings outside that allowlist remain merge-blocking.

Детали внедрения — в `.github/workflows/*` (отдельные PR).

---

## 19. Security KPIs

| KPI | Target |
|-----|--------|
| Исправление critical vuln | < 24h |
| High vuln | < 7d |
| Security review по PR в perimeter | 100% |
| RLS coverage (tenant tables) | 100% — **измерено 2026-08-30 после TI-5: 230 / 230, чтение и запись, без исключений**; было «все, кроме `tenants`» и 124/226 ≈ 55% на 2026-08-28, см. §3 «Измеренное состояние» |
| Audit coverage критичных действий | 100% |
| MFA adoption (superadmin + tenant owners) | > 90% |

---

## 20. Ревизии документа

Любое изменение модели доступа, handoff, документов или публичных потоков **обновляет** этот файл или связанный threat model в том же PR.
