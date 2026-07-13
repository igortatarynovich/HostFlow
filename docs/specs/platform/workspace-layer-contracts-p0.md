# Workspace Layer — platform contracts (P0)

**Status:** Accepted (platform canon). **Implementation:** contracts first — **no React, no screens, no shell** until steps 1–5 below are stable.  
**Hierarchy:** L2 platform canon.  
**Owner:** Platform + Architecture.

**Parent:** [`hostflow-operational-model.md`](../architecture/hostflow-operational-model.md)  
**Interaction overview:** [`hostflow-interaction-architecture.md`](../architecture/hostflow-interaction-architecture.md)  
**First section target:** Candidate Requirements (`recruitment.requirements`) — [`a3-requirements-workspace-backlog.md`](../tasks/a3-requirements-workspace-backlog.md)

**Code artifact (P0):** [`shared/workspace/workspace_layer_contracts.ts`](../../../shared/workspace/workspace_layer_contracts.ts) — pure types, zero UI imports.

---

## 1. Purpose

Зафиксировать **минимальные платформенные контракты** для единого **продуктового паттерна** (информация → требования → состояние → действия) — см. ADR-017 §0. Контракты — средство; цель — **один язык работы в каждом модуле**, не один экран для всех ролей.

**Запрещено на шаге P0:**

- React components, routes, shell layout;
- «Candidate Workspace» как monolithic screen;
- бизнес-логика в типах (только shape declarations).

**Цепочка (ADR-017):**

```text
Module declares capabilities  →  Registry collects  →  Presenter displays (later)
```

---

## 2. Minimal types (normative)

Источник истины в коде: `shared/workspace/workspace_layer_contracts.ts`.  
Схема JSON (optional validation): `shared/workspace/workspace_layer_contracts.schema.json`.

### 2.1 `WorkspaceContextKey`

**Смысл:** контекст работы пользователя — **не** тип сущности.

| Value | Когда |
|-------|--------|
| `intake` | Intake / triage / решение по входящему контакту |
| `recruitment` | Сбор требований, документы, handoff readiness |
| `hr` | HR-приём, верификация, оформление |
| `hr_active` | Операционное сопровождение сотрудника |
| `fleet` | Назначения, ТС, водительские операции |
| `finance` | Billing / invoices в контексте записи |
| `services` | Заказы / исполнение услуг |
| `company` | CRM company / client workspace *(reserved)* |
| `vehicle` | Fleet vehicle *(reserved)* |
| `vacancy` | Vacancy demand *(reserved)* |
| `client` | Client relationship *(reserved)* |

Расширение: только через ADR + bump `WORKSPACE_CONTRACTS_SCHEMA_VERSION`.

### 2.2 `WorkspaceCapabilityKey`

**Смысл:** стабильный идентификатор capability, для которой модуль регистрирует **renderer** (позже). Namespace: `{module}.{capability}`.

**P0 seed (Recruitment):**

| Key | Section | Module |
|-----|---------|--------|
| `recruitment.requirements` | Требования к кандидату | Recruitment |
| `recruitment.overview` | Обзор / профиль | Recruitment |
| `recruitment.documents` | Документы (hub view) | Recruitment |
| `recruitment.applications` | Заявки на вакансии | Recruitment |
| `recruitment.activity` | Активности / контакт | Recruitment |

**Reserved (не имплементировать в P0):** `hr.*`, `fleet.*`, `document_hub.viewer`, …

### 2.3 `WorkspacePermission`

**Смысл:** атом RBAC для видимости раздела или действия. Строка в формате `{resource}.{action}` — **не** дублировать матрицу RBAC в Workspace; ссылаться на существующие permission atoms из [`rbac_matrix.md`](../architecture/rbac_matrix.md).

Примеры:

- `candidates.read`
- `candidates.update`
- `leads.read`
- `workforce_employees.read`

Workspace **фильтрует** declarations по permissions пользователя; **enforce** остаётся в module API.

### 2.4 `WorkspaceStatusSeverity`

**Смысл:** визуальная и логическая категория для Workspace Status rail (не доменный статус).

| Value | Meaning |
|-------|---------|
| `ready` | Блокирующих препятствий нет для этого contribution |
| `blocked` | Есть blocking item — пользователь не может перейти дальше |
| `warning` | Рекомендуется действие, но не hard block |
| `not_applicable` | Contribution не применим в текущем context |
| `info` | Нейтральная информация |

### 2.5 `SectionDeclaration`

**Смысл:** модуль **объявляет раздел** — не UI-экран.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `section_id` | string | yes | Stable id, e.g. `requirements` |
| `module_key` | `ModuleKey` | yes | `recruitment` \| `hr` \| … (ADR-004) |
| `capability_key` | `WorkspaceCapabilityKey` | yes | Renderer registry key |
| `label_key` | string | yes | i18n key |
| `icon` | string | no | Icon token (ADR-011) |
| `order` | number | yes | Navigation sort (lower = higher) |
| `contexts` | `WorkspaceContextKey[]` | yes | When section is visible |
| `permissions` | `WorkspacePermission[]` | yes | All required to show (AND) |
| `readiness_contribution` | boolean | no | Default false; if true, module may emit ReadinessContribution for this section |
| `actions` | `ActionDeclaration[]` | no | Quick actions in section header / rail |

**Invariant:** `section_id` unique per `(module_key, context)` registration; `capability_key` references renderer owned by declaring module.

### 2.6 `ReadinessContribution`

**Смысл:** модуль сообщает **состояние готовности** для Workspace Status aggregation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `module_key` | `ModuleKey` | yes | Source module |
| `context` | `WorkspaceContextKey` | yes | Active context |
| `priority` | number | yes | Aggregation order (blockers: lower = more urgent) |
| `severity` | `WorkspaceStatusSeverity` | yes | Overall contribution severity |
| `summary_key` | string | yes | i18n summary, e.g. «7 из 12 требований» |
| `blockers` | `ReadinessBlock[]` | no | Module-owned semantics |
| `next_action` | `NextActionDeclaration \| null` | no | Module-owned next step |

**Invariant:** семантика blockers и readiness — **только в модуле**. Workspace не интерпретирует `requirement_code`, `document_type`, etc.

### 2.7 `NextActionDeclaration`

**Смысл:** модуль **решает** следующее действие; Workspace **отображает** по display policy.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action_id` | string | yes | Stable id within module |
| `module_key` | `ModuleKey` | yes | Owner |
| `label_key` | string | yes | i18n CTA label |
| `permission` | `WorkspacePermission` | yes | Required to show/execute |
| `priority` | number | yes | For cross-module display policy (lower = prefer) |
| `capability_key` | `WorkspaceCapabilityKey` | no | Navigate/focus section |
| `section_id` | string | no | Target section within capability |
| `handler_kind` | `api` \| `navigation` \| `custom` | yes | How execution is dispatched |
| `handler_ref` | string | yes | API route, path template, or registered handler id |

**Forbidden:** Workspace computing next action from domain heuristics.

### 2.8 Supporting types

```typescript
interface ReadinessBlock {
  block_id: string
  label_key: string
  severity: WorkspaceStatusSeverity
  capability_key?: WorkspaceCapabilityKey
  section_id?: string
}

interface ActionDeclaration {
  action_id: string
  label_key: string
  permission: WorkspacePermission
  handler_kind: 'api' | 'navigation' | 'custom'
  handler_ref: string
}

interface WorkspaceAnchor {
  /** Primary entity the workspace is opened for — module interprets */
  anchor_kind: 'lead' | 'candidate' | 'workforce_employee' | 'company' | 'vehicle' | 'vacancy'
  anchor_id: string
  tenant_id: string
  own_company_id?: string
}

interface WorkspaceSession {
  context: WorkspaceContextKey
  anchor: WorkspaceAnchor
  enabled_modules: ModuleKey[]
}
```

### 2.9 Aggregation output (Workspace platform — step 3)

```typescript
interface WorkspaceStatusSnapshot {
  schema_version: typeof WORKSPACE_CONTRACTS_SCHEMA_VERSION
  session: WorkspaceSession
  contributions: ReadinessContribution[]
  displayed_next_action: NextActionDeclaration | null
  aggregated_severity: WorkspaceStatusSeverity
}
```

Display policy for `displayed_next_action`: **lowest `priority` among contributions where `next_action != null` and permission satisfied** — fixed in platform, not per-module.

---

## 3. Registry contracts (step 2)

```typescript
interface SectionRegistry {
  register(declaration: SectionDeclaration): void
  unregister(module_key: ModuleKey, section_id: string): void
  listSections(session: WorkspaceSession, userPermissions: WorkspacePermission[]): SectionDeclaration[]
}

interface ReadinessRegistry {
  registerContributor(module_key: ModuleKey, fetch: ReadinessContributorFn): void
}

type ReadinessContributorFn = (
  session: WorkspaceSession,
) => Promise<ReadinessContribution | null>
```

**Rules:**

- Registry lives in **platform** package — modules call `register` at bootstrap.
- Modules **never** import registry implementation from each other.
- Disabled module → no registrations → sections absent.

---

## 4. Implementation order (mandatory)

| Step | Artifact | React? | Done when |
|------|----------|--------|-----------|
| **1** | Platform types (`workspace_layer_contracts.ts`) | No | Types compile; schema version constant |
| **2** | Section registry (in-memory P0) | No | `listSections()` filters by context + permissions |
| **3** | Workspace status aggregation | No | `aggregateStatus()` returns `WorkspaceStatusSnapshot` |
| **4** | `recruitment.requirements` **SectionDeclaration** only | No | ✅ Registered for `context=recruitment` |
| **5** | Requirements **capability renderer** (integration spike) | Yes | ✅ Renderer + adapter proven on legacy route `/candidates/:id/requirements` — **not target UX** |
| **6** | **Workspace Refactoring (Candidate)** | Yes | ⏳ Evolve existing Candidate Card — not a new Shell wrapper |

**Explicitly deferred:** greenfield «Workspace Shell» route, full Lead/HR card replacement in one PR.

### Step 5 — architectural proof, UX lesson (2026-07-03)

Step 5 **succeeded** as a technical spike:

- `SectionDeclaration` + registry filter by context/permissions;
- `ReadinessContribution` adapter from Recruitment runtime;
- status aggregation + `RecruitmentRequirementsCapabilityRenderer`;
- permission gate (section hidden without `candidates.view`).

Step 5 **failed** as product UX — and that was expected once viewed through ADR-017:

| What users saw | Why it feels wrong |
|----------------|-------------------|
| Candidate card with status rail (blockers, next action, requirements KPI) | Already a partial Workspace surface |
| Button «Открыть workspace» → `/requirements` | Implies leaving Workspace to open Workspace |
| Second screen repeats status + requirements + readiness | **Duplicate aggregation** — «card inside card» |

**Conclusion:** standalone `/app/candidates/:id/requirements` must **not** evolve. Step 6 **does not** build a new container — it **refactors Candidate Card** into declarative composition.

### Step 6 — Workspace Refactoring (Candidate) — strategy

**Not:** build Shell → migrate card inside.

**Instead:** take existing Candidate Card → remove duplication → one Status Rail → section providers from registry → retire `/requirements`.

| Phase | Change | User-visible? |
|-------|--------|---------------|
| 6a | Single aggregated Status Rail on card (platform aggregation) | Subtle — less duplicate KPIs |
| 6b | Requirements section = capability renderer in card work area (in-place or tab) | No new screen |
| 6c | Retire `/requirements` route → same card + `?section=requirements` or tab | No «second workspace» |
| 6d+ | Migrate timeline, documents, profile blocks → section declarations (incremental) | «Card got better» |

```text
Candidate Card (same route /app/candidates/:id)
┌──────────────────────────────────────────────────────────────┐
│ Header · actions · stage chain          (unchanged surface)  │
├─────────────┬────────────────────────────┬───────────────────┤
│ sections    │  work area                 │ Status Rail       │
│ (registry)  │  Requirements renderer     │ (one aggregation) │
│             │  or Overview / Documents … │                   │
└─────────────┴────────────────────────────┴───────────────────┘
```

- User **never** sees «Open Workspace» — already in workspace.
- Status rail: **singleton** on card — not per section, not on spike route.
- Section renderer mounts **work area body only**.
- Navigation: existing card tabs/sections wired to `SectionRegistry`; click Requirements block in rail → switch section.

### Why Candidate Requirements first (step 4–5)

| Criterion | Requirements section |
|-----------|---------------------|
| Runtime readiness | ✅ `requirements/workspace` API + transfer_readiness |
| Blockers | ✅ `pipeline_blockers`, field requirements |
| Next actions | ✅ Mappable from open requirements |
| Shows Workspace value | ✅ Proved contracts; **product value** = card refactoring (step 6), not new screen |
| Module independence | ✅ Recruitment-only declaration; HR/Fleet untouched |

### Mapping: Recruitment → ReadinessContribution (step 3–4)

From `GET /api/v1/candidates/{id}/requirements/workspace` (`requirements_workspace_v1`):

| API field | Maps to |
|-----------|---------|
| `summary.blocking_open_count > 0` | `severity: blocked` |
| `summary.handoff_ready` | `severity: ready` |
| `transfer_readiness.blocking_reasons[]` | `blockers[]` |
| First open blocking requirement | `next_action` (module adapter — **not** workspace logic) |

Adapter lives in **Recruitment module** (`recruitmentWorkspaceAdapter.ts` or backend serializer) — produces `ReadinessContribution`, not raw API in Workspace.

---

## 5. Forbidden on P0 PRs

| Forbidden | Why |
|-----------|-----|
| Greenfield **Workspace Shell** wrapping Candidate Card | Same «container inside container» risk as Step 5 |
| Evolving `/requirements` as standalone product screen | Duplicate status rail |
| Second status rail inside section renderer | One aggregation on card only |
| CTA «Открыть workspace» on candidate screen | User already in workspace |
| Big-bang card rewrite | Evolutionary refactoring — section by section |
| Workspace imports `handoff.py` / requirement engine | Reverse dependency |
| Next action computed in aggregator from requirement codes | Business logic in platform |
| `LeadWorkspace` / `CandidateWorkspace` classes | Entity coupling |
| Shell/refactoring before requirements renderer spike | **Step 5 complete; step 6 unblocked** |

---

## 6. Acceptance

### P0 contracts (steps 1–5) — complete

- [x] `shared/workspace/workspace_layer_contracts.ts` exists; **zero** imports from `react` / `hostflow-frontend/src/components`
- [x] Section registry unit tests: context filter, permission filter, module disabled
- [x] Status aggregation unit tests: multi-module contributions, next action priority
- [x] `recruitment.requirements` declaration registered in tests
- [x] Capability renderer + adapter wired (legacy route spike)
- [x] ADR-017 + this doc linked from `module-catalog-and-routing-map.md`

### Step 6 — Workspace Refactoring (Candidate) — next PR(s)

- [ ] **Same route** `/app/candidates/:id` — no new «workspace» product surface
- [ ] One Status Rail on card (platform `aggregateWorkspaceStatusFromContributors`)
- [ ] Requirements = section provider in card work area — renderer **without** its own rail
- [ ] Retire `/requirements` → redirect or in-card section switch
- [ ] Remove duplicate blockers/next-action between card rail and requirements spike
- [ ] Section navigation wired to registry (tabs or sidebar — reuse existing card chrome)
- [ ] No user-facing «new Workspace» — regression: card flow green

Optional sub-PRs: 6a rail unification → 6b requirements in-card → 6c route retirement → 6d+ other sections.

---

## 7. Changelog

| Date | Change |
|------|--------|
| 2026-07-03 | Step 6 reframed: Workspace Refactoring (Candidate), not new Shell |
| 2026-07-03 | Step 5 UX lesson: `/requirements` spike only |
| 2026-07-03 | P0 contracts spec + implementation order |
