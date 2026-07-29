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
- **Enforcement:** CI job `tenant-bind-auth` (`scripts/security/check_tenant_bind_auth.py`) — fail-closed `get_db_with_tenant` + meta-leads dep; `get_db_with_tenant_public` allowlist; AST scan of FastAPI routes that declare `X-Tenant-Id` without auth (`tenant_header_public_allowlist.txt`). FE `applyAuthIsolationWipeOnce` clears stale per-origin Bearer/tenant once after isolation deploy (cookie session rehydrates).
- Webhooks Meta / generic inbound: `security_job_context` + bind + enforcement (`webhook.py`, `inbound_public.py`).
- Worker helper: `tenant_enforced_session(..., actor_id=..., correlation_id=...)` — используется в `communications_scheduler` (per-tenant tick), ARQ `job_automation_evaluate_trigger`, `job_calendar_sync_ingest`, sweep / risk_intel / HR alerts passes.
- **ARQ SSOT §0b (2026-07-29):** `parse_required_job_tenant_id` fail-closed; calendar enqueue передаёт `tenant_id`; stripe/comms jobs ставят `security_job_context`. CI: `check_arq_worker_tenant.py` / job `arq-worker-tenant`.
- Security event v1: `emit_security_event_v1` — всегда непустые `actor_id` (или `system:unknown`) и `correlation_id`; JWT deps и middleware сбрасывают contextvars через token reset.
- Тесты: `tests/security/test_tenant_rls_session_guard.py`, `test_api_tenant_context_unit.py`, `test_superadmin_elevated_bind.py`, `test_tenant_header_membership_guard.py`; A/B API — `tests/api/test_tenant_isolation.py` (`@pytest.mark.postgres_integration`, Lifespan timeouts увеличены в `conftest`).

---

## Phase 2 — Structured observability

**Цель:** сделать изоляцию и злоупотребления **измеримыми** в рантайме, а не только в статическом анализе.

**Spike (реализовано, узкий scope — не «platform»):**

- **Canonical schema v1** (enforced): `emit_security_event_v1` в `backend/app/security/canonical_emit.py` — поля `schema_version`, `event_id`, `event_type`, `category`, `severity`, `timestamp`, `tenant_id`, `actor_id`, `correlation_id`, `access_kind`, `action`, `entity_type`, `entity_id`, `result`, `source`, `extra`. Transport остаётся только structured log (`hostflow.security.events`); продьюсеры не знают SIEM/queue.
- **Taxonomy:** `backend/app/security/event_taxonomy.py` — allowlist префиксов (`auth.`, `rls.`, `access.`, `superadmin.`, …), константы spike-событий, `validate_event_type`.
- **Redaction:** `backend/app/security/event_redaction.py` — запрещённые/чувствительные ключи, allowlist для `extra`, лимит размера JSON.
- **Legacy shim:** `emit_security_event` в `backend/app/security/events.py` — маппинг старых `action` на v1 + fallback старый payload для неизвестных строк.
- **Call sites (canonical):** `get_db_with_tenant` (superadmin elevated + auth impersonation), `get_db_with_meta_leads_effective_tenant` (operational remap), `TenantEnforcingAsyncSession` (RLS deny).
- **Governance (process):** [`security-events-governance.md`](./security-events-governance.md) — как добавлять `event_type`/prefixes, bump `schema_version`, запрет raw events, rollout без drift; **CI gate** на raw `emit_security_event(` (см. раздел *CI enforcement* там и job `no-raw-emit-security-event` в `security-gates.yml`).

**Golden path list + export (код, 2026-07-29):**

- **List:** prefix `access.*` + helper `access_events.emit_access_security_event_v1` (`query_class`, `route`, `row_count`, `duration_ms`, …). Call site: `GET /api/v1/candidates` (`access.list.completed`).
- **Export:** уже Phase 4 v1 (`export.*` на documents/analytics/org_units export).
- **Search (Phase 6 first call site):** `GET /api/v1/search` → `search.retrieval.completed` via `retrieval_events` (без сырого `q` в `extra`).
- **Runbook (correlation):** HTTP middleware / deps выставляют `correlation_id` в contextvar; ищите цепочку в structured log `hostflow.security.events` по `correlation_id` + `tenant_id` + `actor_id` (list → export / search на том же запросе-сессии).

**Статус фазы:** spike + golden path list/export **started** (list wired; export уже был; dashboards / Prometheus — backlog).

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

**Статус (код):** **started — export telemetry v1 + anomaly detector v1** (per-request thresholds; sliding-window / Slack alerts → Phase 7).

**Цель:** снизить **insider risk** и массовые выгрузки без блокировки легитимной работы.

**Реализовано (v1 telemetry, узкий scope):**

- Таксономия `export.*`: `export.requested`, `export.generated`, `export.downloaded`, `export.denied`, `export.anomaly.detected`, плейсхолдер `export.expired` (на будущее для TTL/async).
- `export_events.py`: `emit_export_security_event_v1` + allowlist `extra` с полями `export_type`, `row_count`, `byte_size`, `filter_scope`, `async_job_id`, **`export_scope`**, **`contains_class3`**, **`bulk_operation`**, `reason`, `response_mode`, **`anomaly_codes`**, **`threshold_*`**.
- Call sites: `modules/documents/router` (export.json / export.csv / export.zip bundle), `api/v1/admin/org_units` (`/export` snapshot). Detector runs automatically on every successful `export.generated`.
- Redaction: доп. запрет ключей `rows`, `records`, `archive_path`, `export_path`, `attachment_filename` в security `extra`.
- **Stabilization (Phase 3+4):** таблица обязательных событий и анти-drift gates — [`telemetry-phase3-4-mandatory-events.md`](./telemetry-phase3-4-mandatory-events.md), job `telemetry-phase34-stability` в `security-gates.yml`.

**Пороги anomaly v1 (per-request, не блокируют):**

| Код | Условие | Значение |
|-----|---------|----------|
| `row_count_threshold` | `row_count >= N` | **500** |
| `byte_size_threshold` | `byte_size >= N` | **5_000_000** (≈5 MiB) |
| `class3_bulk` | `contains_class3` и `bulk_operation` | boolean |
| `class3_row_count` | CLASS 3 и `row_count >= N` | **50** |

Ложноположительные: крупные org-structure snapshots, легитимные bulk CSV. Triage по `export_type` + `anomaly_codes`; auto-block — **не** в v1.

**Сигналы (ещё backlog / Phase 7)**

- Резкий рост числа экспортов на пользователя / tenant / сутки (sliding window).
- Нетипичное время (after-hours) + большой объём.
- Алерт в Slack / admin center на `export.anomaly.detected`.

**Критерии готовности фазы (пример)**

- ~~Пороги v1 задокументированы; ложноположительные сценарии известны.~~ **done (таблица выше).**
- Связка с audit trail export (SSOT): каждый экспорт уже имеет запись → детектор читает те же поля `export.generated`.
- Sliding-window + paging alerts — Phase 7.

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

**Нормативный контракт:** [`retrieval-audit-governance.md`](./retrieval-audit-governance.md) + `retrieval_events.py` (taxonomy + helper + redaction keys).

**Реализовано (call sites, 2026-07-29):**

- `GET /api/v1/search` — `search.retrieval.requested` / `.completed` / `.denied` (scope membership fail); counters `returned_count` / `filtered_count`; без сырого `q`.
- `GET /api/v1/tenants/{id}/links/search-companies` — тот же triad; `retrieval_scope=cross_tenant_company_directory`.
- Threat model: [`threat-models/global-search.md`](./threat-models/global-search.md).
- CI: `scripts/security/check_retrieval_call_sites.py` (job в `security-gates`).

**Направления работ (остаток Phase 6)**

- Контракт на «retrieval»: максимальный scope, redaction, запрет на склейку несвязанных кандидатов.
- Запрет неявного «global search» по всем tenant’ам без platform-only режима с отдельным audit и rate limit.
- Оценка RAG/vector: кто может писать в индекс, как удаляются вектора при delete/anonymize (GDPR).
- Analytics drill-down как retrieval — только если появится отдельный слой (не агрегаты).

**Критерии готовности фазы (пример)**

- ~~Threat model обновлён под search~~ — `threat-models/global-search.md`.
- ~~Негативные тесты: чужой scope → denied event~~ — unit `test_retrieval_global_search_audit.py`.
- AI context assembly call sites — backlog до появления продукта.

---

## Phase 7 — Detection & alerting

**Статус (код):** **started — detection engine v1** (in-process rules + `detection.alert.raised` + optional webhook).

**Цель:** превратить сигналы фаз 2–4 (и Phase 6 retrieval denies) в **реакцию** (Slack webhook / log), с обязательным runbook.

**Реализовано (v1):**

- Taxonomy prefix `detection.` · `detection.alert.raised`.
- Rules registry: `backend/app/security/detection_rules.py` (owner + runbook required).
- Engine hook from `emit_security_event_v1` → `maybe_raise_detection_alerts` (skips `detection.*` recursion).
- Rules: `export_anomaly_v1` (immediate), `retrieval_denied_burst_v1` (5/10m), `document_signed_url_denied_burst_v1` (10/10m). Burst counters are **process-local** (multi-replica → shared store backlog).
- Optional sink: `SECURITY_ALERT_WEBHOOK_URL` / `settings.security_alert_webhook_url`.
- Runbooks: [`detection-runbooks.md`](./detection-runbooks.md).
- CI: `scripts/security/check_detection_rules.py`.

**Примеры правил (ещё backlog)**

- Brute force / всплеск 401/403 (auth path metrics).
- Sliding-window export count per actor/day (needs shared store).
- Tenant enumeration on public endpoints.

**Критерии готовности фазы (пример)**

- ~~Каждое правило имеет owner, порог и процедуру triage.~~ **v1 done.**
- ~~Нет «алерта без runbook».~~ **enforced by CI.**
- Shared-store burst + PagerDuty — backlog.

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
