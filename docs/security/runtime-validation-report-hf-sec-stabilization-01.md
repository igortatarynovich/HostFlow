# Runtime validation report — HF-Sec-Stabilization-01

**Sprint:** Security Stabilization & Runtime Validation (HostFlow)  
**Цель:** не расширять security-framework, а **проверить foundation** на кодовой базе + зафиксировать operational follow-ups для реального потока логов.  
**Дата отчёта (аудит репозитория):** 2026-05-12  

---

## 1. Legacy burn-down

### A. Остатки `emit_security_event(`

| Path | Тип | Risk | План |
|------|-----|------|------|
| `backend/app/security/events.py` | Определение legacy shim + внутренние вызовы `emit_security_event_v1` | Низкий (единственный модуль в allowlist) | Оставить до полного отказа от shim; **не добавлять** новые внешние вызовы |
| `backend/app/**/*.py` (остальное) | Raw `emit_security_event(` | — | **Не найдено** (CI `check_no_raw_emit_security_event.py`) |

Внешних импортов `from ...security.events import emit_security_event` в `backend/app` **нет**.

### B. Allowlist

`scripts/security/emit_security_event_allowlist.txt` — **одна** строка (`events.py`). Расширений нет.

### C. Маленькие PR в этом спринте

- Документальная гигиена: в `runtime-roadmap.md` (Phase 1) исправлены формулировки `emit_security_event` → **`emit_security_event_v1`** там, где речь о каноническом elevated/meta-leads пути и о непустых `actor_id`/`correlation_id`.

Дальнейший burn-down: при появлении **любого** нового вызова legacy shim — миграция на v1 в том же PR-серии (1–5 call sites).

---

## 2. Runtime validation (статический аудит кода)

Прод-логи в этом отчёте не анализировались — ниже **что проверено в репо** и что сделать в ops.

### A. `actor_id` / `correlation_id`

| Area | Status | Notes |
|------|--------|--------|
| HTTP (`get_db_with_tenant`, meta leads) | **OK (по коду)** | `set_security_actor_id` при JWT; `emit_security_event_v1` подставляет `actor_id` / `correlation_id` или fallback `system:unknown` / ephemeral correlation |
| Webhooks | **OK (по коду)** | `security_job_context` с явным `actor_id` (`system:meta-leads-webhook`, `system:leads-generic-inbound-webhook`) |
| Workers / schedulers | **OK (по коду)** | `tenant_enforced_session` оборачивает `security_job_context`; явные `actor_id` (напр. `system:communications-scheduler`, `system:automation_evaluate_trigger`) |
| `system:unknown` spikes | **Follow-up** | Нужна выборка из **prod/staging** логов `hostflow.security.events`: доля событий с `actor_id=system:unknown` по `source` / route |

### B. Tenant assertions

| Signal | Status | Notes |
|--------|--------|--------|
| RLS deny (`rls.tenant_context.execute_denied`) | **OK (по тестам)** | `tests/security/test_tenant_rls_session_guard.py` и CI |
| Elevated superadmin | **OK (по коду)** | Заголовки + `emit_security_event_v1` в `deps.py` / `meta_leads_tenant_dep.py` |
| Unusual superadmin volume | **Follow-up** | Метрики / лог-агрегация в окружении с трафиком |

### C. Cardinality / шум событий

| Topic | Status | Notes |
|-------|--------|--------|
| `event_type` distribution | **Follow-up** | Агрегировать в log stack по `event_type` × `source` за 24–72h |
| Тяжёлый `extra` | **OK (по коду)** | `_MAX_EXTRA_JSON_BYTES_DEFAULT` + truncation в `event_redaction.py` |

---

## 3. Telemetry quality

### A. Structured canonical payload

| Check | Status | Notes |
|-------|--------|--------|
| `schema` / `schema_version` | **OK** | `test_canonical_security_emit.py`, продьюсеры v1 |
| `event_id`, `timestamp` | **OK** | Генерация в `canonical_emit.py` |
| `action` vs `event_type` | **OK** | Helpers передают `action=event_type` |

### B. Redaction (ключи)

Ручная сверка с `event_redaction.py`: ключи **`signed_url`**, **`filename`**, **`prompt`**, **`query`**, **`context`**, **`embedding`**, **`export_path`**, **`archive_path`** и родственные — в FORBIDDEN / scrub; тесты: `test_document_security_telemetry.py`, `test_export_security_telemetry.py`, `test_telemetry_extra_redaction_stability.py`, `test_retrieval_security_telemetry.py`.

### C. Oversized `extra`

| Check | Status |
|-------|--------|
| Clipping / truncation | **OK** | Лимит JSON размера + тесты на redaction |

---

## 4. Worker context validation

Проверены использования **`tenant_enforced_session`** / **`security_job_context`** (выборочно по коду):

| Flow | Tenant | Actor | Correlation | Notes |
|------|--------|-------|-------------|--------|
| `communications_scheduler` per-tenant tick | `bind_tenant_context_to_session` внутри helper | `system:communications-scheduler` | опционально (часто не передаётся → генерируется в `security_job_context`) | При необходимости сквозного trace — передавать `correlation_id` из tick id |
| ARQ `job_automation_evaluate_trigger` | да | `system:automation_evaluate_trigger` или параметр job | опционально | то же |
| Inbound webhooks | bind отдельно в handler | фиксированные system actors | `rid` из запроса | OK |

**Acceptance:** критичные пути используют общий helper с RLS enforcement; security-события в этих путях идут через v1 там, где уже подключены продьюсеры.

---

## 5. Security review discipline (процесс)

Статический проход по репозиторию:

| Check | Status |
|-------|--------|
| Raw `emit_security_event(` вне allowlist | **Нет** (CI) |
| Helper-only для document/export/retrieval | **OK** (`check_telemetry_helpers_v1_only.py`) |
| Logger bypass heuristic | **OK** (`check_no_sensitive_logger_bypass.py`) |
| Обзор последних feature PR | **Follow-up** | Выполняется человеком по `security-review-checklist.md` + labeler |

---

## 6. Итоговая таблица (Definition of Done)

| Area | Status | Notes |
|------|--------|--------|
| Legacy paths | **progress** | Allowlist = 1 файл; внешних legacy callers нет; roadmap wording выровнен на v1 |
| Actor propagation | **OK / follow-up** | Код корректен; **prod** — проверить долю `system:unknown` |
| Correlation propagation | **OK / follow-up** | Ephemeral CID есть; **prod** — проверить разрывы цепочек |
| Tenant assertions | **OK** | Тесты + guards в коде |
| Telemetry noise / cardinality | **follow-up** | Только с реальным log volume |
| Redaction | **OK** | Ключи + тесты; prod — spot-check выборки |
| Worker context | **OK** | Явные actors + tenant_enforced_session |
| CI gates | **OK** | `security-gates.yml` + scripts (локально: `pytest backend/tests/security/` зелёный) |
| Governance / drift | **OK** | Новых префиксов/telemetry categories в этом спринте **не** добавлялось |

---

## Следующие шаги (operational, вне этого PR)

1. **Staging/prod:** 24–72h выборка `hostflow.security.events` — `actor_id`, `correlation_id`, топ `event_type`, cardinality `source`.  
2. **Burn-down:** любой новый legacy path — сразу PR на v1 (маленький).  
3. **Feature PRs:** чеклист + явный security reviewer для AI / search / export / portals / automations / integrations.

**Принцип спринта соблюдён:** новый security framework **не** добавлялся; проверено, что существующая архитектура **согласована с кодом и CI**, а рост нагрузки вынесен в честные operational follow-ups.
