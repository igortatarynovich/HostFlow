# ADR-014 §6 Phase 1 — Epic & tasks (import template)

**Purpose:** Copy sections below into your tracker (Linear, Jira, etc.). Keeps Phase 1 from becoming **“resolver partially everywhere”** without acceptance criteria or guardrails. **Execution risks** (thin façade, module leakage, premature generic framework) are **merge blockers** — see dedicated section below.

**Canonical spec:** [ADR-014 — Document Hub — access model](ADR-014-document-hub-access-model.md) (especially **§6 Phase 1**, **§10–§11**, **§12**).

---

## Epic

**Title:** `ADR-014 §6 Phase 1 — Resolver foundation`

**Description:**

Implementation of the minimal `DocumentAccessResolver` foundation from ADR-014 §6 Phase 1.

**Goal:**

Centralize document access resolution and remove duplicated module-specific document authorization logic **without** introducing a full policy engine or Document Hub redesign.

**Out of scope:**

- Hub UI
- Policy graph
- Capabilities engine
- Generic ACL framework
- Versioning redesign
- OCR / signature / KSeF
- Module-specific ACL systems

**Success criteria:**

- All document endpoints pass through the resolver.
- Workspace header alone cannot deny owner access (no **“Candidate not found”** solely from `X-Own-Company-Id` mismatch when the owner entity is otherwise accessible).
- Scenario **A** from ADR-014 **§11** covered by an automated test.
- No new `ensure_*_document_scope` introduced.

**References:**

- [ADR-014](ADR-014-document-hub-access-model.md) §5–§12
- [ADR-009](ADR-009-document-hub-platform-layer.md)
- [Hard invariants: Recruitment, HR, Document Hub](invariants-recruitment-hr-document-hub.md)

**Tracker mapping (optional):** Tasks 1–5 below map to workstreams; **PR-1–PR-4** are the recommended **merge sequence** — see next section.

---

## Suggested PR sequence (pre-implementation control)

**Do not land everything in one PR.** The first merge should be **narrow** so review/CI can validate the **architectural contract** before widening surface area.

### PR-1 — Resolver foundation + `summary` migration + Scenario A test

**Title (suggested):** `ADR-014 Phase 1 — resolver + documents/summary + §11-A test`

#### Команда — PR-1 (канон для реализации)

**Старт:** только **PR-1** — **ADR-014 §6 Phase 1 — Resolver foundation**.

**Scope PR-1:**

1. Ввести **`DocumentAccessResolver`**.
2. Ввести **`DocumentAccessContext`**.
3. Перевести **только** `documents/summary` на resolver.
4. Добавить автотест на **ADR-014 §11-A**:
   - кандидат доступен в карточке (owner access разрешён тем же контрактом, что и для карточки);
   - **`X-Own-Company-Id`** отличается от **`candidate.own_company_id`**;
   - **`documents/summary`** **не** возвращает **Candidate not found**.
5. **Не** добавлять новые **`ensure_*_document_scope`**.

**Не мержить PR-1, если:**

1. Resolver **просто проксирует** старые `ensure_*` (thin façade).
2. Доступ к **owner** решается **только** через **`X-Own-Company-Id`** (workspace — только slice, не единственный gate на кандидата).
3. Появились **HR / transport / finance-specific** ACL для документов.
4. В PR добавлены **policy graph**, **DSL**, **Hub UI**, **versioning redesign**, **OCR / signature / KSeF**.
5. `documents/summary` **по-прежнему** может вернуть **Candidate not found** **только** из-за **workspace mismatch** (при валидном доступе к кандидату).

**Главный результат PR-1:** текущий баг закрыт через архитектурный слой **`DocumentAccessResolver`** (и разделение owner vs workspace + регресс **§11-A**), **а не** через локальный обход в router.

---

**Includes (EN, same scope):**

- `DocumentAccessResolver` + `DocumentAccessContext`
- Migration of **`documents/summary`** only — resolve context **before** reads
- Automated test for **ADR-014 §11 scenario A**
- **No new** `ensure_*_document_scope`

**Excludes:**

- `list` / `checklist` / `export` / CRUD
- HR / transport / finance-specific policy products
- `DocumentFile` / versioning redesign
- Hub UI
- Generic policy engine / DSL / graph executor

**Why this shape:**

- Validates the **contract** quickly (resolver is real, not decorative).
- Closes the **current production pain** (summary) with a **small** diff.
- Establishes the **first test anchor** for the rest of the migration.

---

## After PR-1 — drift control (PR-2 / PR-3)

Review guidance so Phase 1 does not slide into accidental refactors or resolver explosion.

1. **`_load_candidate_context` inside the resolver** — **acceptable transitional** dependency on `router` for PR-1 (orchestration is centralized; no ACL duplication). **Do not** add more router-layer imports per new endpoint. **Target:** move owner loading to a **shared access service / owner provider**, not the HTTP router. Not a merge-blocker for PR-2 if PR-2 does not deepen this coupling.

2. **Avoid `resolve_for_candidate_list`, `resolve_for_candidate_create`, …`** — that pattern is the start of **module/service explosion** (then employee/finance/transport resolvers). **Next convergence:** one **generic document-access entrypoint** with **owner-type loaders** inside a policy/provider layer. `resolve_for_candidate_summary` is a **migration seam**, not the final public API shape.

3. **Visibility / process-lock fields stay boring stubs** through PR-2–PR-3 — migrate read/mutation endpoints through the **same** context object; **do not** fill stubs with ad-hoc logic “just for this endpoint”. Policy comes **after** migration surface is wired.

4. **Viewer channel (read visibility)** — HTTP header **`X-Document-Viewer-Channel`** (`recruitment` \| `hr` \| `transport` \| `finance`; default `recruitment`; invalid → **422**). Read responses filter by **viewer scope + `shared`**; single-doc read for an invisible type → **404**; mutations stay **recruitment-only** until an ADR explicitly widens them. Optional diagnostics: **`HOSTFLOW_DOCUMENT_ACCESS_DEBUG`** adds **`document_access_trace`** to summary/export JSON and **DEBUG** logs (`document_access_visibility`) — see ADR-014 Phase 2 — *Viewer channel read visibility*.

5. **ADR-014 §11-A test** is a **canonical contract** (policy + migration invariant + future guardrail). Keep it green when touching `summary` / shared resolver code; do not weaken assertions without an ADR/invariants update.

---

### PR-2 — Remaining **read** endpoints

#### Команда — PR-2 (канон для реализации)

**Старт:** **PR-2** — миграция **только read**-эндпоинтов.

**Scope PR-2:**

- `documents/list` (`GET …/candidate/{id}/documents` и ветка `GET …/documents?candidate_id=`)
- `documents/checklist` (`GET …/candidate/{id}/checklist`)
- `documents/export` (`export.json`, `export.csv`, `export.zip`)

**Цель:** все **read**-операции получают **`DocumentAccessContext`** до чтения данных (единый контракт resolver).

**Не делать в PR-2:**

- mutations (create/update/delete/upload);
- вынесение owner-loader из router (отдельный рефакторинг);
- HR / transport / finance policies;
- логика visibility / locks кроме **stub**;
- generic policy framework;
- Hub UI.

**Не мержить PR-2, если:**

1. Новые **`ensure_*_document_scope`**.
2. Новые **локальные ACL** в handlers.
3. Новые **`resolve_for_candidate_*`** на каждый endpoint, если достаточно **общего read-context** (`resolve_for_candidate_documents` + `_candidate_documents_read_access` в router).
4. **Усиление** зависимости resolver от router (кроме уже оговоренного transitional `_load_candidate_context`).
5. **Ослабление** теста **§11-A** (регресс остаётся каноническим).
6. **`X-Own-Company-Id`** снова становится причиной **Candidate not found** при валидном owner.

**Главный результат PR-2:** все **document read flows** используют **единый resolver contract**, без расширения платформенной модели (policy graph / Hub).

---

**Endpoints (EN checklist):**

- `list`
- `checklist`
- `export` (JSON / CSV / zip as applicable)

---

### PR-3 — **Mutations**

#### Mutation access contract

**Смысл:**

- mutation flow **не** использует read helper как shortcut;
- mutation получает **`DocumentAccessContext`** до записи / удаления / замены файла;
- resolver отвечает **только** за access / context / lock stub;
- upload, validation, lifecycle, persistence остаются в **существующих** сервисах / handlers;
- workspace mismatch **не может** сам по себе давать ложный **Candidate not found**;
- destructive actions должны быть **совместимы** с future process locks;
- **никаких** module-specific mutation ACL.

#### Команда на PR-3 (канон для реализации)

**Старт:** **PR-3** — migrate document mutations to resolver.

**Scope PR-3:**

- create / upload;
- update;
- delete;
- replace / re-upload, если есть отдельный endpoint.

**Цель:** все **mutation** endpoints получают **mutation-oriented** `DocumentAccessContext` до изменения данных.

**Не делать:**

- Hub UI;
- DocumentFile / versioning redesign;
- реальный policy graph;
- полноценные HR / transport / finance policies;
- перенос lifecycle в resolver;
- owner-provider refactor, если он **раздувает** PR.

**Не мержить PR-3, если:**

1. POST / PUT / DELETE используют **read helper** как semantic shortcut.
2. resolver начинает **валидировать** upload / lifecycle **вместо** access.
3. Появляются новые **local ACL** в mutation handlers.
4. **`X-Own-Company-Id`** снова даёт ложный **Candidate not found**.
5. **process lock stub** игнорируется для **destructive** path.
6. PR **расширяется** до versioning или Hub модели.

**Главный результат PR-3:** все document **read + mutation** flows проходят через **единый resolver contract**, но resolver остаётся **access / context layer**, а не business lifecycle engine.

---

**Migrate to resolver before persisting changes (EN checklist):**

- `create` / upload
- `update`
- `delete`
- replace / re-upload flows where applicable

---

### PR-4 — Guardrails

#### Команда — PR-4 (канон для реализации)

**Старт:** **PR-4** — guardrails для ADR-014 document access.

**Scope PR-4:**

1. **CI / script** — lightweight проверка запрещённых паттернов под `backend/app/modules/documents/`:
   - `ensure_*_document_scope`, `ensure_hr_document_scope`, `ensure_transport_document_scope`, finance-specific document ACL helpers (substring list + regex);
   - `ensure_candidate_own_company_scope` (candidate-only shortcut в documents-db модуле);
   - прямые чтения `X-Own-Company-Id` из `headers` / `request.headers` (authorization anti-pattern);
   - `await _load_candidate_context` (legacy; removed — use owner provider via resolver);
   - `load_candidate_documents_owner_context` / `await load_candidate_documents_owner_context` вне **`candidate_document_owner_access.py`** и **`document_access_resolver.py`**;
   - импорт **`documents.router`** / **`.router`** в **`document_access_resolver.py`**.
2. **PR-review checklist** — ссылки на **ADR-014 §10–§11**, критерии resolver / workspace / process lock; зафиксировать **merge blocker**.
3. **Optional PR template** — GitHub: `.github/PULL_REQUEST_TEMPLATE/document_access_adr014.md` → полный чеклист в `docs/devel/pr-checklist-adr014-document-access.md`.

**Реализовано в репозитории:**

- Скрипт: `backend/scripts/check_adr014_document_access.py` (запуск в **backend-ci** после Ruff).
- Чеклист: `docs/devel/pr-checklist-adr014-document-access.md`.
- Шаблон PR: `.github/PULL_REQUEST_TEMPLATE/document_access_adr014.md`.

**Не делать в PR-4:**

- не расширять resolver;
- не мигрировать новые endpoints;
- не добавлять policy engine;
- не делать owner-provider refactor;
- не трогать Hub UI.

**Не мержить PR-4, если:**

- guardrail-скрипт удалён / ослаблен без ADR / invariants;
- чеклист противоречит ADR-014 §10–§11.

**Главный результат PR-4:** ADR-014 становится **проверяемым** стандартом (CI + review), а не только текстом.

---

**Task 4 (EN tracker) — architecture guardrails:**

- Lint / CI blocking forbidden ACL patterns under **app/modules/documents/**
- PR checklist linking **ADR-014 §10–§11**
- Explicit rejection of new **module-specific** document ACL forks in that module

---

## Phase 1 completion gate (before Phase 2)

**Done with Phase 1 when:**

1. **Every** candidate **documents-db** endpoint obtains a **`DocumentAccessContext`** (via resolver) **before** reading or mutating persisted document data.
2. The resolver remains:
   - **not** a thin wrapper around legacy `ensure_*` in handlers;
   - **not** forked per module;
   - **not** a generic policy framework (see **Execution risks** below and [ADR-014 §12](ADR-014-document-hub-access-model.md)).

Only then proceed to **product Phase 2** (deeper policy behavior per ADR-014 §6).

---

## Phase 2 — Owner access provider + resolver decoupling (structural)

**Implemented (this milestone, separate from ADR-014 §6 “Phase 2” product work):**

1. **`candidate_document_owner_access.py`** — `CandidateDocsContext`, `load_candidate_documents_owner_context`, `candidate_visible_for_tenant_documents` (shared visibility for `_fetch_document_with_visibility`).
2. **`DocumentAccessResolver`** imports **only** the owner provider (no `router`).
3. **`DocumentAccessContext.access_policy`** — `read` | `mutate` | `destructive_mutate`; **`resolve_for_candidate_destructive_document_mutations`** runs process-lock hook before return.
4. **Router** — delete / mock-upload use `_get_document_with_mutation_access(..., enforce_destructive_process_lock=True)`.
5. **CI** — `check_adr014_document_access.py` extended: forbid `documents.router` / `.router` imports in resolver; forbid `load_candidate_documents_owner_context` / `await load_...` outside owner provider + resolver; forbid legacy `await _load_candidate_context`.
6. **Tests** — destructive resolver entrypoint + default `access_policy`; existing §11-A read + mutation mismatch coverage retained.

**Closure criteria:** resolver has no router import; owner load lives in provider; destructive mutations obtain context via `resolve_for_candidate_destructive_document_mutations`; CI enforces the above.

---

## Task 1 — Introduce `DocumentAccessResolver` and `DocumentAccessContext`

**Parent:** Epic above.

**Do:**

- Central resolver entrypoint.
- Owner access resolution.
- Resolved workspace slice.
- Visibility / process-lock **stubs** (explicit extension points).
- Policy-driven extension structure (hooks / rule list — **no** per-module resolver forks).

**Reject (thin-wrapper failure mode):**

- Resolver that only **proxies** into legacy `ensure_*` / header ACL — **forbidden**. Owner and workspace legs must be **orchestrated here**, not re-hidden behind old helpers.

**Done when:**

- Resolver can be called with `(tenant, user, owner entity, operation)` (or equivalent) and returns a populated `DocumentAccessContext` suitable for documents-db handlers.

---

## Task 2 — Migrate document endpoints to resolver

**Parent:** Epic above.

**Migrate:**

- `summary`
- `list`
- `checklist`
- `export`
- `create` / `update` / `delete`

**Remove:**

- Local ad-hoc checks that re-derive owner authorization from headers alone.

**Reject (leakage):**

- “Temporary” local ownership checks in HR/transport/finance routes — **forbidden**; route through resolver/policy hooks or open an ADR/invariants change.

**Done when:**

- Every migrated route invokes the resolver **before** reading or mutating document rows (stubs acceptable where §6 Phase 1 allows).

---

## Task 3 — Acceptance coverage for ADR-014 §11 Scenario A

**Parent:** Epic above.

**Verify:**

- Candidate visible in scope + **mismatched** `X-Own-Company-Id` → **documents summary (and list if in scope)** do **not** return **“Candidate not found”** solely due to workspace mismatch.

**Done when:**

- Automated test (or CI-equivalent) exists and is required for merge on touched paths.

---

## Task 4 — Architecture guardrails (document ACL)

**Parent:** Epic above.

**Type:** Guardrail / process (can be labeled `architecture` or `chore`).

**Do:**

- **CI script** `backend/scripts/check_adr014_document_access.py` (runs in **backend-ci** after Ruff) — forbids patterns documented in **`docs/devel/pr-checklist-adr014-document-access.md`** under **`app/modules/documents/`** (module ACL forks, header-only owner gates, bypassing resolver owner path).
- **PR checklist** `docs/devel/pr-checklist-adr014-document-access.md` — links **ADR-014 §10–§11** (implementation invariants + acceptance scenarios); violations are a **merge blocker** for touched surfaces.
- **Optional GitHub PR template** `.github/PULL_REQUEST_TEMPLATE/document_access_adr014.md` — quick confirm + link to full checklist.

**Done when:**

- Contributors and AI agents have a **single visible** gate (CI + checklist), not only tribal knowledge.

---

## Task 5 (optional) — Document resolver integration contract

**Parent:** Epic above.

**Deliverable:** Short tech doc (e.g. under `docs/specs/` or module `README`):

- How endpoints must call the resolver.
- Expected `DocumentAccessContext` shape (fields, nullability, stub semantics).
- Migration guidance for future modules (HR / transport / finance).

**Done when:**

- New handlers can integrate without reverse-engineering the router.

---

## Execution risks (Phase 1 — what to reject in review / CI)

These are the **main execution failures** for Phase 1. Treat violations as **block merge**, not “tech debt later”.

### 1. Resolver becomes a thin façade

**Bad pattern:** endpoints “formally” call the resolver; resolver **internally** calls old `ensure_*`; ad-hoc logic survives; ACL only **moves**.

**Required:** resolver is the **single orchestration point** for owner access + workspace slice + (stub) visibility + (stub) locks — **call existing shared primitives** (e.g. candidate repo / ACL) **from inside** the resolver, **do not** re-expose `ensure_*` to HTTP handlers.

### 2. Leakage back into modules

**Bad pattern:** “just this once” local check in HR/transport/finance; “quick” ownership guard on one endpoint.

**Required:** **no** parallel recruitment/HR/finance/transport document ACL — extend **policies** on the **same** resolver or update ADR/invariants in the same PR. Otherwise the resolver loses authority and multi-engine ACL returns in ~3 months.

### 3. Resolver becomes a generic framework

**Bad pattern:** DSL, runtime expression language, graph executor, dynamic policy compiler — “so we’re ready for everything”.

**Required for this phase:** resolver stays **boring**, **explicit**, **business-oriented**, **policy-ready** — **concrete** policies, contexts, owner types, tests. **No** universal authorization platform in Phase 1 (align with [ADR-014 §12](ADR-014-document-hub-access-model.md) — directional only).

---

## Import hints

| Tracker | Suggestion |
|--------|------------|
| **Linear** | Create **Project** or **Label** `ADR-014-phase1`; Epic = **Initiative** or parent **Issue**; Tasks 1–5 as child issues with **blocked-by** / **related** links to ADR URLs. |
| **Jira** | Epic Issue Type for parent; Tasks as Stories/Tasks; link Confluence or repo paths in **References**. |

**Dependency sketch:** Task 1 → Task 2 → Task 3; Task 4 in parallel from Task 1 start; Task 5 after Task 1 (or parallel to Task 2).
