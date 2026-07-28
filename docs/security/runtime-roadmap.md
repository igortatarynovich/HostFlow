# HostFlow — Runtime Security & Observability Roadmap

**Статус:** evolving operational program (backlog по фазам).  
**Не заменяет** [`security-ssot.md`](./security-ssot.md): SSOT остаётся нормативным каноном принципов и invariants; этот файл — **приоритизируемая реализация** runtime-guarantees, telemetry и detection.

**Аудитория:** platform, backend, SRE, security champion, product (для scope AI/search).

---

## Зачем отдельный документ

| SSOT (`security-ssot.md`) | Этот roadmap |
|---------------------------|----------------|
| Стабильные правила | Часто меняющиеся метрики, дашборды, пороги алертов |
| Invariants «всегда так» | «Сделать к Q…», vendor-выбор, burn-down |
| Компактность | Расширяемые разделы по мере зрелости |

---

## Security-owned infrastructure (наблюдаемость = часть security architecture)

Для HostFlow уже достаточная сложность, чтобы **не** относиться к логам и метрикам как к чистому DevOps-шуму. Нужен слой **security-owned** артефактов — единые для forensics, detection и IR:

- **Security / audit logs** — отдельный контур или чётко помеченный stream (не «кто как залогировал» в произвольных полях).
- **Audit pipeline** — доставка, retention, доступ (кто читает audit в prod).
- **Telemetry schema** — версионируемые JSON-схемы или protobuf/OpenTelemetry semantic conventions (выбор — в реализации).
- **Event taxonomy** — словарь `action`, `entity_type`, `result`; новые значения через review. **Процесс и ownership:** [`security-events-governance.md`](./security-events-governance.md).
- **Anomaly / security events** — нормализованные записи для детекторов (вход тот же канон полей ниже).

Без единой event-модели детекция, расследования инсайдеров и AI-abuse быстро превращаются в хаос.

---

## Canonical security event fields (v1)

Ниже — **минимальный канон** для security-sensitive событий (export, document URL, superadmin, failed auth, mass list, retrieval/prompt context и т.д.). Реализации могут добавлять поля, но **ядро должно быть заполняемым** там, где событие относится к доступу к данным.

| Поле | Тип / смысл | Обязательность |
|------|----------------|-----------------|
| `timestamp` | UTC, RFC3339 / epoch ms + TZ | обязательно |
| `tenant_id` | UUID tenant в контексте события | обязательно, если применимо; иначе явный `null` + `source` |
| `actor_id` | user/service principal; `SYSTEM` для чисто фоновых задач | обязательно |
| `entity_type` | нормализованная строка таксономии (`candidate`, `document`, `export_job`, …) | обязательно для object-bound событий |
| `entity_id` | UUID или стабильный идентификатор | обязательно, если применимо |
| `action` | нормализованное имя (`document.signed_url.generate`, `export.started`, …) | обязательно |
| `access_scope` | OWNER / SHARED_READ / … или эквивалент из SSOT handoff | рекомендуется; обязательно для cross-tenant paths |
| `route` / `source` | HTTP route или `worker:reminders.send` | обязательно |
| `correlation_id` | сквозной ID запроса/джоба | обязательно для цепочек HTTP→worker |
| `ip` | клиентский IP (edge-trusted) | обязательно для наружнего доступа; иначе `null` |
| `user_agent` | заголовок или `null` для non-HTTP | рекомендуется |
| `result` | `success`, `denied`, `error` + при необходимости код причины | обязательно |

**Расширения (по классу события):** `row_count`, `bytes_out`, `duration_ms`, `reason` (superadmin), `ttl_sec` (signed URL), `policy_version` — только в рамках версионируемой схемы, не произвольный JSON без ревью.

**PII / CLASS 3:** значения полей — идентификаторы и таксономия; **не** сырые фрагменты документов, токены целиком, тела запросов. Redaction — часть pipeline, не «надежда на дисциплину».

**Версионирование:** при изменении обязательного набора полей — bump `schema_version` в payload и запись в changelog этого roadmap.

---

## Рекомендуемая последовательность внедрения (практический порядок)

Порядок ниже сознательно **ближе к operational risk**, чем нумерация фаз по документу; маппинг на фазы roadmap указан в скобках.

1. **Runtime tenant assertions** — Phase 1.  
2. **Structured observability** — Phase 2 + канон полей выше (единая event-модель с первого дня).  
3. **Export + document telemetry** — Phase 4 + Phase 3 (можно параллельно после базового логирования).  
4. **Async worker security context** — контракт SSOT §0b + guards в worker entrypoints (Phase 1 / Phase 2).  
5. **Search / AI retrieval enforcement** — Phase 6 (не откладывать до «когда появится AI»: поиск и отчёты — тот же класс риска).  
6. **Detection rules** — Phase 7.  
7. **Scorecard** — Phase 8 (подпитывается метриками из п.2–4).

Observability для HF трактуется как **часть security architecture**, а не только как operational dashboard DevOps.

---

## Phase 1 — Runtime tenant assertions

**Цель:** гарантировать, что в критичном пути к данным **никогда** не выполняется запрос с «потерянным» tenant context (включая workers).

**Направления работ**

- Assertions / invariant checks в repository/session слое: tenant context установлен до первого SQL к tenant-таблицам.
- Middleware или единая точка входа для HTTP: fail-fast или structured error при отсутствии контекста (политика: dev vs prod).
- Документированный контракт для фоновых задач (см. SSOT §0b): `tenant_id`, `actor_id`, `access_scope`, `correlation_id` обязательны в message/job payload.

**Критерии готовности фазы (пример)**

- Единый helper/guard, используемый и в API, и в worker entrypoints.
- Тесты: негативный сценарий «job без tenant» → fail до БД.

**Реализовано (MVP + hardening, код):**

- **Статус фазы:** MVP (session guard) **+ hardening** — superadmin/support elevated bind, `actor_id` в runtime, worker `tenant_enforced_session`, CI для tenant isolation.
- `TenantEnforcingAsyncSession` (`backend/app/db/tenant_session.py`) + `async_sessionmaker(..., class_=...)` в `backend/app/db/session.py`: при `tenant_rls_enforcement=True` на Postgres блокируется `execute`/`stream`, пока не завершён `bind_tenant_context_to_session` (флаги `rls_tenant_bound`, `_binding_tenant_context` на время bind).
- `get_db_with_tenant` / `get_db_with_meta_leads_effective_tenant` выставляют `tenant_rls_enforcement=True` до bind; `bind_tenant_context_to_session` проверяет `set_config` через `current_setting` (без silent pass на Postgres). **Hardening:** superadmin с `X-Tenant-Id` ≠ JWT tenant — обязателен `X-HostFlow-Elevated-Reason` (+ опциональный `X-HostFlow-Elevated-Scope` из allowlist), `emit_security_event_v1`; meta leads remap (`effective` ≠ header) — тот же контракт; `db.info["security_access_kind"]` / `security_elevated_*`. **P0:** для authenticated non-superadmin `get_db_with_tenant` вызывает `ensure_user_can_access_tenant` до RLS bind (JWT match **или** `user_memberships`) — чужой `X-Tenant-Id` без membership → 403.
- **Residual (auth on tenant-bound CRM routes + public token-first):** calendar list/connections/refresh/delete/cursors/reconcile/renew + `token_meta` redaction; `/users/managers` + `/catalogs/managers`; analytics router `dependencies=[get_current_user]`; `/meta/stages` ignores `X-Tenant-Id` when anonymous (membership required when header used); candidate-links GET; public goals/notifications/scanner create resolve tenant from share/intake token (ignore header); FE VacancyList + impersonation backup use `getStoredAccessToken`. Tests: `tests/security/test_residual_auth_isolation.py`.
- **Residual batch 2:** `/documents/templates`, `/legal-documents/active`, `/notifications/templates`, and `/db/*` documents module require auth (`get_current_user`); closes anonymous tenant catalog/template reads via `X-Tenant-Id` alone.
- **Fail-closed tenant bind:** `get_db_with_tenant` requires authenticated user (401 anonymous). Signed webhooks use `get_db_with_tenant_public` (explicit `X-Tenant-Id`, no silent default). Public scan session routes require matching intake `token` (closes UUID IDOR).
- Webhooks Meta / generic inbound: `security_job_context` + bind + enforcement (`webhook.py`, `inbound_public.py`).
- Worker helper: `tenant_enforced_session(..., actor_id=..., correlation_id=...)` — используется в `communications_scheduler` (per-tenant tick), ARQ `job_automation_evaluate_trigger`, sweep / risk_intel passes.
- Security event v1: `emit_security_event_v1` — всегда непустые `actor_id` (или `system:unknown`) и `correlation_id`; JWT deps и middleware сбрасывают contextvars через token reset.
- Тесты: `tests/security/test_tenant_rls_session_guard.py`, `test_api_tenant_context_unit.py`, `test_superadmin_elevated_bind.py`, `test_tenant_header_membership_guard.py`; A/B API — `tests/api/test_tenant_isolation.py` (`@pytest.mark.postgres_integration`, Lifespan timeouts увеличены в `conftest`).

---

## Phase 2 — Structured observability

**Цель:** сделать изоляцию и злоупотребления **измеримыми** в рантайме, а не только в статическом анализе.

**Spike (реализовано, узкий scope — не «platform»):**

- **Canonical schema v1** (enforced): `emit_security_event_v1` в `backend/app/security/canonical_emit.py` — поля `schema_version`, `event_id`, `event_type`, `category`, `severity`, `timestamp`, `tenant_id`, `actor_id`, `correlation_id`, `access_kind`, `action`, `entity_type`, `entity_id`, `result`, `source`, `extra`. Transport остаётся только structured log (`hostflow.security.events`); продьюсеры не знают SIEM/queue.
- **Taxonomy:** `backend/app/security/event_taxonomy.py` — allowlist префиксов (`auth.`, `rls.`, `superadmin.`, …), константы spike-событий, `validate_event_type`.
- **Redaction:** `backend/app/security/event_redaction.py` — запрещённые/чувствительные ключи, allowlist для `extra`, лимит размера JSON.
- **Legacy shim:** `emit_security_event` в `backend/app/security/events.py` — маппинг старых `action` на v1 + fallback старый payload для неизвестных строк.
- **Call sites (canonical):** `get_db_with_tenant` (superadmin elevated + auth impersonation), `get_db_with_meta_leads_effective_tenant` (operational remap), `TenantEnforcingAsyncSession` (RLS deny).
- **Governance (process):** [`security-events-governance.md`](./security-events-governance.md) — как добавлять `event_type`/prefixes, bump `schema_version`, запрет raw events, rollout без drift; **CI gate** на raw `emit_security_event(` (см. раздел *CI enforcement* там и job `no-raw-emit-security-event` в `security-gates.yml`).

**Направления работ**

- Structured logs (JSON), **совместимые с каноном полей** (см. раздел *Canonical security event fields* выше): в том числе `tenant_id`, `actor_id`, `route` / `job_type`, `query_class` (list/search/export), `row_count`, `duration_ms`, `bytes_out` (где применимо), `correlation_id`.
- Метрики (Prometheus или аналог): rate/latency по endpoint × tenant (агрегации с ограничением кардинальности).
- Политика PII в логах: никаких сырьевых тел документов и чувствительных полей в debug.

**Критерии готовности фазы (пример)**

- Минимальный «golden path» для list + export покрыт единым форматом логов.
- Runbook: как по correlation_id пройти цепочку от HTTP до worker.

---

## Phase 3 — Signed URL telemetry

**Статус (код):** **started — document telemetry v1** (`emit_security_event_v1` на read/presign/download путях документов; Phase 3 в целом остаётся в backlog для дашбордов/алертов).

**Цель:** после архитектурной защиты (короткий TTL, private storage) добавить **доказуемость** доступа к байтам.

**События (audit / security log)**

- Генерация URL: кто, какой объект, TTL, scope, tenant.
- Успешный доступ / отказ: IP, user-agent, причина отказа (expired, wrong tenant, signature mismatch, replay).
- Попытки reuse / scan паттернов (массовый перебор ключей).

**Реализовано (v1 telemetry, узкий scope):**

- Таксономия `document.*` (`document.metadata.read`, `document.file.access_requested`, `document.file.downloaded`, `document.signed_url.generated` / `.denied`, плейсхолдеры `.expired` / `.replay_denied` на будущее), helper `emit_document_security_event_v1` + строгий allowlist `extra`.
- Call sites: `modules/documents/router` (metadata, file-url, download, presign-upload), `api/v1/candidate_documents` (скачивание/redirect), `api/public/intake` (public presign + download), `/uploads/…` redirect presign в `main` при распознавании UUID в ключе `documents/{id}/…`.
- Redaction: запрет ключей `url` / `signed_url` / `filename` и scrub URL-подстрок с подписью/token в значениях.
- **Stabilization:** см. общий артефакт [`telemetry-phase3-4-mandatory-events.md`](./telemetry-phase3-4-mandatory-events.md) и job `telemetry-phase34-stability` в `security-gates.yml`.

**Критерии готовности фазы (пример)**

- Отчёт или дашборд: топ генераций и топ отказов по причине.
- Алерт на аномальный рост denied/expired для одного tenant или IP (см. Phase 7).

---

## Phase 4 — Export anomaly detection

**Статус (код):** **started — export telemetry v1** (`emit_security_event_v1` на синхронных export-путях; детекторы / пороги / bulk — по-прежнему backlog этой фазы).

**Цель:** снизить **insider risk** и массовые выгрузки без блокировки легитимной работы.

**Реализовано (v1 telemetry, узкий scope):**

- Таксономия `export.*`: `export.requested`, `export.generated`, `export.downloaded`, `export.denied`, плейсхолдер `export.expired` (на будущее для TTL/async).
- `export_events.py`: `emit_export_security_event_v1` + allowlist `extra` с полями `export_type`, `row_count`, `byte_size`, `filter_scope`, `async_job_id`, **`export_scope`**, **`contains_class3`**, **`bulk_operation`**, `reason`, `response_mode`.
- Call sites: `modules/documents/router` (export.json / export.csv / export.zip bundle), `api/v1/analytics` (`/analytics/export`), `api/v1/admin/org_units` (`/export` snapshot).
- Redaction: доп. запрет ключей `rows`, `records`, `archive_path`, `export_path`, `attachment_filename` в security `extra`.
- **Stabilization (Phase 3+4):** таблица обязательных событий и анти-drift gates — [`telemetry-phase3-4-mandatory-events.md`](./telemetry-phase3-4-mandatory-events.md), job `telemetry-phase34-stability` в `security-gates.yml`.

**Сигналы (примеры)**

- Резкий рост `row_count` или числа экспортов на пользователя / tenant / сутки.
- Много скачиваний CLASS 3 за короткий интервал.
- Нетипичное время (after-hours) + большой объём (политика по юрисдикции и культуре компании).

**Критерии готовности фазы (пример)**

- Пороги v1 задокументированы; ложноположительные сценарии известны.
- Связка с audit trail export (SSOT): каждый экспорт уже имеет запись → детектор читает те же данные.

---

## Phase 5 — SUPERADMIN operational controls

**Цель:** перевести описанные в SSOT требования в **операционные** контроли, а не только в архитектуру.

**Направления работ**

- Обязательное поле **reason** (и при необходимости ссылка на ticket/incident) при impersonation / elevated session.
- Time-bound elevation (например 30 мин) в продукте, не только в тексте спеки.
- Audit trail: **append-only** или эквивалент (WORM / immutable store / crypto-hashing цепочки событий) для superadmin-действий — выбор реализации в backlog.
- UI banner «SUPERADMIN ACCESS ACTIVE» (или эквивалент) для снижения социального риска.

**Критерии готовности фазы (пример)**

- Невозможно начать impersonation без reason в production-конфигурации.
- Выборка superadmin-событий за период — один запрос / один отчёт.

---

## Phase 6 — Search, analytics & AI isolation (выделенный high-risk track)

**Почему отдельно:** для HostFlow с высокой вероятностью именно **global search**, **отчёты/дашборды**, **embeddings** и **AI context assembly** станут следующим слоем обхода изоляции после «сырых» экспортов и документов. Этот слой соединяет данные из разных сущностей и упрощает **слишком широкий контекст** для модели или пользователя.

**Инвариант (должен попасть в реализацию каждой фичи этого класса)**

Любая инфраструктура поиска, аналитики или AI **обязана** быть одновременно:

1. **Tenant-scoped** — никаких cross-tenant индексов/кэшей без явной модели handoff.
2. **RBAC-scoped** — тот же policy layer, что и для API; никаких «admin search sees all fields».
3. **Audit-scoped** — логируемые запросы контекста (что включили в prompt / retrieval, какой индекс, какой фильтр), без утечки CLASS 3 в логах.

**Нормативный контракт (начало Phase 6, без call sites):** [`retrieval-audit-governance.md`](./retrieval-audit-governance.md) + `retrieval_events.py` (taxonomy + helper + redaction keys).

**Направления работ**

- Контракт на «retrieval»: максимальный scope, redaction, запрет на склейку несвязанных кандидатов.
- Запрет неявного «global search» по всем tenant’ам без platform-only режима с отдельным audit и rate limit.
- Оценка RAG/vector: кто может писать в индекс, как удаляются вектора при delete/anonymize (GDPR).

**Критерии готовности фазы (пример)**

- Threat model обновлён под конкретную AI/search фичу (отдельный файл в `threat-models/` при появлении продукта).
- Негативные тесты: запрос контекста с чужим `tenant_id` / чужим кандидатом → отказ.

---

## Phase 7 — Detection & alerting

**Цель:** превратить сигналы фаз 2–4 в **реакцию** (Slack, email, admin center, PagerDuty по критичности).

**Примеры правил**

- Brute force / всплеск 401/403.
- Массовые экспорты / скачивания документов (см. Phase 4).
- Аномалии signed URL (см. Phase 3).
- Tenant enumeration (паттерны запросов к публичным endpoint).

**Критерии готовности фазы (пример)**

- Каждое правило имеет owner, порог и процедуру triage.
- Нет «алерта без runbook» (ссылка на IR в SSOT / security-review-checklist).

---

## Phase 8 — Security scorecard

**Цель:** сделать security **измеримой системой** для leadership и ретроспектив, без превращения в SOC2-theater.

**Примеры строк scorecard**

| Area | Metric | Target / note |
|------|--------|-----------------|
| RLS | % tenant-таблиц с политикой | 100% |
| CI gates | security-gates workflow | green on main |
| Security tests | `backend/tests/security/` + tenant API tests | pass |
| Threat models | актуальность при изменении surface | по gate |
| MFA | adoption superadmin + owners | > 90% (цель SSOT) |
| Vulns | critical / high (sensitive deps) | 0 / по политике |

**Критерии готовности фазы (пример)**

- Единый источник цифр (дашборд + ссылка из этого файла).
- Ежемесячный или квартальный review с фиксацией в changelog roadmap.

---

## Как вести этот документ

1. **Не дублировать** SSOT: сюда — сроки, метрики, vendor, пороги; в SSOT — только неизменные правила.  
2. При конфликте с SSOT **побеждает SSOT**; roadmap корректируется.  
3. Закрытые фазы можно помечать статусом `Done` и датой, не удаляя текст (audit trail документа).  
4. Новые AI/search возможности **обязаны** получать запись минимум в Phase 6 и в `threat-models/`.

---

## Связанные артефакты

- [`security-ssot.md`](./security-ssot.md) — принципы, классификация данных, invariants.  
- [`security-review-checklist.md`](./security-review-checklist.md) — PR gate.  
- [`threat-models/`](./threat-models/) — уточнение по поверхностям.  
- CI: `.github/workflows/security-gates.yml`.
