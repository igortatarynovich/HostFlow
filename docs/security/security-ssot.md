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

### Канонические спеки

- `docs/specs/architecture/multi_tenant_model.md`
- Миграции RLS в `backend/alembic/versions/`

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

Детали: `docs/specs/architecture/object_storage.md`, `threat-models/document-uploads.md`, `threat-models/public-links.md`.

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

Детали внедрения — в `.github/workflows/*` (отдельные PR).

---

## 19. Security KPIs

| KPI | Target |
|-----|--------|
| Исправление critical vuln | < 24h |
| High vuln | < 7d |
| Security review по PR в perimeter | 100% |
| RLS coverage (tenant tables) | 100% |
| Audit coverage критичных действий | 100% |
| MFA adoption (superadmin + tenant owners) | > 90% |

---

## 20. Ревизии документа

Любое изменение модели доступа, handoff, документов или публичных потоков **обновляет** этот файл или связанный threat model в том же PR.
