# REF-UI-000 — UI Standardization Roadmap

Status: Active  
Date: 2026-05-29  
Owner: Frontend Architecture + Product Design

## Scope Separation (Locked)

| Stream | Location | Purpose |
|---|---|---|
| UI Standardization Program | `docs/specs/frontend/REF-UI-*` | audit, standards, canonical models, governance |
| Product Improvements | `docs/specs/tasks/*` | local product improvements and feature work |

## Governance Rule (Locked)

Product task does not change UI canon automatically.
Any impact on canon is allowed only via explicit governance decision in `REF-UI-*`.

## Artifact Creation Rule (Locked)

Each new artifact must answer one concrete unknown question.
If a document does not introduce a new question/answer pair and only restates known information, it must not be created.

Current Foundation chain questions:

1. `FOUNDATION_AUDIT.md` -> What is actually used now? ✅
2. `FOUNDATION_TOKEN_INVENTORY.md` -> Which tokens are unique vs duplicates? ✅
3. `FOUNDATION_BENCHMARK.md` -> What do we keep, legacy, or deprecate? ✅
4. `FOUNDATION_V1` -> What is officially allowed? ✅ Locked
5. `FOUNDATION_ENFORCEMENT_AND_MIGRATION_PLAN.md` -> How does V1 become real? ✅

Current Primitives chain questions:

1. `PRIMITIVES_AUDIT.md` -> What primitive components exist now? ✅
2. `PRIMITIVES_INVENTORY.md` -> Which variants are unique vs duplicates? ✅
3. `PRIMITIVES_BENCHMARK.md` -> Badge/Chip: keep, legacy, or deprecate? ✅
4. `STATUS_BADGE_V1` / `CHIP_V1` / `SELECT_V1` / `BUTTON_V1` / `INPUT_V1` / `CHECKBOX_V1` -> What is allowed? ✅ Locked
5. `PRIMITIVES_ENFORCEMENT_AND_MIGRATION_PLAN.md` -> How does V1 become real? ✅
6. `PRIMITIVES_V1.md` -> Official allow-list (Layer 2) ✅ **Locked**

Current Layer 3 chain questions (TABLE_V1 first):

1. Per-table audits + Sprint 1 benchmark -> Best baseline? ✅
2. `TABLE_V1_ADAPTATION_BACKLOG.md` -> What must adapt before lock? ✅
3. `TABLE_V1_DRAFT` -> What is allowed? ✅ Superseded by lock
4. Governance triage + manual validation -> Backlog approved? ✅ Triage; validation before M1
5. `TABLE_V1.md` lock -> Operational list standard ✅

## Execution Model (Layered)

### Step 1 (Current): TABLE_V1

1. Tables

### Layer 1: Foundation

After `TABLE_V1` lock:

Mandatory pre-canonical steps:

1. `FOUNDATION_AUDIT.md`
2. Token Inventory
3. Foundation Benchmark
4. `FOUNDATION_V1.md`

Only after these steps:

1. Typography
2. Spacing
3. Colors
4. Radius
5. Borders
6. Shadows
7. Z-index
8. Breakpoints

Output:

- `FOUNDATION_V1.md` (locked)

### Layer 2: Primitive Components

Mandatory pre-canonical steps (same discipline as Foundation):

1. `PRIMITIVES_AUDIT.md`
2. Primitives Inventory
3. Primitives Benchmark
4. `PRIMITIVES_V1_DRAFT`
5. Enforcement + Migration Plan
6. `PRIMITIVES_V1` lock

Families:

1. Buttons
2. Inputs
3. Selects
4. Checkboxes / Radios / Toggles
5. Badges
6. Chips
7. Tags

Output:

- `PRIMITIVES_V1.md` (locked)

### Layer 3: Composite Components

1. FILTER_BAR_V1
2. STATUS_BADGE_V1
3. TAB_BAR_V1
4. MODAL_V1
5. PANEL_V1
6. TABLE_V1

### Layer 4: Layout Components

1. LIST_LAYOUT_V1
2. ENTITY_LAYOUT_V1
3. SETTINGS_LAYOUT_V1

### Layer 5: Page Templates

1. Candidates
2. Employees
3. Companies
4. Vacancies

### Finalization

- `REF-UI-001` final standard

## Current Step

Layer 1 (Foundation) is **locked**.  
Layer 2 (Primitives) is **locked** — all five families.

| Gate | Status |
|---|---|
| Audit | ✅ |
| Token Inventory | ✅ |
| Benchmark | ✅ |
| V1 Draft | ✅ |
| Migration Plan | ✅ |
| Diff-based CI enforcement | ✅ |
| `foundation-allow` protected | ✅ |
| Full scan non-blocking | ✅ |
| PR base branch handled | ✅ |
| **FOUNDATION_V1 lock** | ✅ |

### Primitives (Layer 2 — complete)

| Gate | Status |
|---|---|
| Audit | ✅ |
| Inventory | ✅ |
| Benchmark (per family) | ✅ |
| V1 Draft / Wrapper decision (Input) | ✅ |
| Enforcement plan | ✅ |
| Governance approval | ✅ |
| **`STATUS_BADGE_V1` lock** | ✅ |
| **`CHIP_V1` lock** | ✅ |
| **`SELECT_V1` lock** | ✅ |
| **`BUTTON_V1` lock** | ✅ |
| **`INPUT_V1` lock** | ✅ (CSS-only, no wrapper) |
| **`PRIMITIVES_V1` lock** | ✅ |

### Layer 3 — TABLE_V1

| Gate | Status |
|---|---|
| Sprint 1 + per-table audits | ✅ |
| Adaptation backlog | ✅ |
| Governance triage (A1–A5) | ✅ |
| **`TABLE_V1` lock** | ✅ |
| Enforcement plan | ✅ |
| Manual validation (before M1) | ⬜ |
| M1 vacancies migration | ⬜ |

Next step (Layer 3):

- Manual validation checklist → **M1 vacancies** migration
- Next composite: `FILTER_BAR_V1` (after table frame stable)

Done: **`TABLE_V1` lock**; triage A1–A5; enforcement plan; manual validation checklist

## Operating Constraint

From this point, frontend standardization discussion and outputs must stay in this roadmap sequence.
Parallel product improvements are allowed, but they do not redefine canon without governance approval.
