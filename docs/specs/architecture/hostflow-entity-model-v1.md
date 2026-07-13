# HostFlow Entity Model v1

**Status:** canonical (L1 — **object passport**; Phase 2.1 entry point).  
**Owner:** Product + Platform UX + Frontend Architecture.  
**Parent:** [`hostflow-platform-canon-v1.md`](hostflow-platform-canon-v1.md)  
**Catalog:** [`hostflow-platform-catalog.md`](hostflow-platform-catalog.md) §0.A · §Phase 2  
**Workspace UI (Phase 2.2):** [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md)  
**Code contract:** `hostflow-frontend/src/platform/entity-model/` · **Reference:** `hostflow-frontend/src/modules/candidates/candidatesEntityModel.ts`

---

## §0. Definition

> **Entity Model is the single source of truth for what HostFlow knows about one business object.**

Not a screen. Not a module DTO. Not a table column list. Not a rail adapter.

**Universal Entity Workspace**, **Universal Data Table**, and **Universal Detail Rail** are **projections** of Entity Model + **Universal Entity Schema** (see [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md) §2).

```text
                 Entity Model (passport)
                        │
                        ▼
              Universal Entity Schema
                        │
       /                |                \
 Data Table        Detail Rail      Entity Workspace
```

**Forbidden:** parallel schemas in `*ResourceSchema.ts`, `*DetailRailAdapter.ts`, and `*Card.tsx` that drift apart.

---

## §1. Canonical sections (every object type)

Fixed vocabulary — modules **enable subset**, never rename or reorder.

| Section id | Question |
|------------|----------|
| `identity` | Who / what is this? |
| `state` | Current status, stage, blockers (product language) |
| `ownership` | Who is responsible / owner role now |
| `contacts` | How to reach? |
| `actions` | What operations are allowed now (capability, not button layout) |
| `documents` | Which documents / requirements |
| `timeline` | What happened (human-meaningful events) |
| `relations` | Linked objects |
| `tasks` | What requires action (reminders, follow-ups) |
| `outcome` | How process ended (when terminal) |

---

## §2. Field projection flags

Each field in the model declares **where it may appear**. Design once; platform routes.

| Flag | Surface |
|------|---------|
| `showInTable` | Collection — mass comparison |
| `showInRail` | Detail Rail — quick decision |
| `showInSearch` | List / global search |
| `showInEntitySummary` | Entity Workspace summary strip |
| `showInContextRail` | Entity Context Rail snippets |
| `editable` | Entity Workspace content area |
| `filterable` | Table / list facets |
| `searchable` | Text search |

Example:

| Field | Table | Rail | Search | Summary | Editable |
|-------|-------|------|--------|---------|----------|
| Phone | ✓ | ✓ | ✓ | — | — |
| Date of birth | — | — | ✓ | — | ✓ |
| Rejection reason | — | ✓ | — | — | ✓ |

---

## §3. Projection rules

### §3.1 Data Table

Exports fields where `showInTable`. Never defines its own field list.

### §3.2 Detail Rail

**Does not decide content.** Receives from Entity Model via **`toDetailRailProjection()`** (Phase 2.3):

- `state` → current decision + why (product labels)
- `actions` → primary / secondary (empty when `outcome` is set for role)
- `outcome` when process closed — **suppresses all work actions**
- `contacts` — compact actions only when `showInRail` and communication is active work
- `documents` / `relations` / `timeline` — only when required for **current** process state

**Forbidden:** parallel decision logic in `*DetailRailAdapter.ts` after Phase 2.3. See Entity Workspace Canon §6.

Composer chooses **which blocks mount** — model supplies **data and lifecycle rules**.

### §3.3 Entity Workspace

Full passport UI — all enabled sections. See Entity Workspace v1 (five zones).

### §3.4 Search & filters

Derived from same model flags — no duplicate field registries.

---

## §4. Process state vs data state

**Data state** = raw fields (stage code, row_status, handoff flags).  
**Process state** = role-specific interpretation («Рекрутинг завершён», «Передан в HR»).

Process state lives in **`state` + `outcome` sections** of the model — not in Rail adapters.

Detail Rail **never** shows internal codes (`ready_for_handoff`) to users.

---

## §5. Module contract

Module provides **one** `EntityModel` per resource type:

```text
modules/{module}/{resource}EntityModel.ts   ← source of truth
  → toResourceSchemaFromEntityModel()
  → toDetailRailProjection(entity, role, processState)
  → toEntityWorkspaceConfig(entity)
```

**Reference implementation:** Candidate (Recruitment) — `modules/candidates/candidatesEntityModel.ts` (`buildCandidatesEntityModelSchema`, `resolveCandidateEntityPassport`).

---

## §6. Terminology (forbidden)

| Do not say | Say |
|------------|-----|
| Карточка кандидата / клиента | **Universal Entity Workspace** |
| Candidate card layout | Entity Workspace **config** |
| Custom documents tab | Universal Document Workspace **embed** |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | v1 — Entity Model Canon; Phase 2.1; projections §3 |
