# HostFlow Platform Catalog

**Status:** living index (L1 — **development entry point**).  
**Owner:** Platform UX + Frontend.  
**Constitution (frozen):** [`hostflow-platform-canon-v1.md`](hostflow-platform-canon-v1.md) — Phase 0, change rarely.  
**Build order:** [`ui-primitives-roadmap.md`](ui-primitives-roadmap.md)

> **Development starts here — not with a screen, not with a module.**

Before writing code, answer:

> **Does Platform Catalog already have a Primitive, Composition, or Reference Scenario that solves this?**

| Answer | Action |
|--------|--------|
| **Yes** | Use it. Module supplies config only. |
| **No** | Extend platform first (primitive → scenario validation → module). |

---

## §0.A Entity Model — one source of truth (2026-07-09)

> **At each object type there is exactly one information model. Table, Rail, and Workspace are projections — not separate designs.**

### Dependency (strict — never invert)

```text
                    Entity Model
              (full passport of the object)
          /            |              \
   Data Table     Detail Rail    Entity Workspace
  (compare many)  (decide now)   (edit / deep work)
```

| Surface | Question it answers |
|---------|---------------------|
| **Entity Model** | What does the system know about this object? |
| **Entity Workspace** | Show the full passport — edit where allowed |
| **Detail Rail** | What subset is needed **right now** to decide? |
| **Data Table** | What properties are needed to **compare** many objects? |

**Detail Rail does not store structure.** It requests slices from Entity Model via a **projection composer**. Same for table columns.

**Canon:** [`hostflow-entity-model-v1.md`](hostflow-entity-model-v1.md) · [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md)

### Canonical sections (Entity Model — platform vocabulary)

| Section | Role |
|---------|------|
| `identity` | Who / what is this? |
| `state` | Status, stage, blockers (product language) |
| `ownership` | Who is responsible now |
| `contacts` | How to reach? |
| `actions` | Allowed operations (capabilities) |
| `documents` | Files / requirements |
| `timeline` | Human-meaningful events |
| `relations` | Linked objects |
| `tasks` | Reminders / follow-ups |
| `outcome` | Terminal result |

### Field projection flags

Each field declares **where it may appear** — design the model once:

| Flag | Meaning |
|------|---------|
| `showInTable` | Collection column |
| `showInRail` | Decision Rail block input |
| `showInSearch` | List / global search |
| `showInEntitySummary` | Entity Workspace summary strip |
| `showInContextRail` | Entity Context Rail (right panel) |
| `editable` | Entity Workspace content |
| `filterable` | Table / list facets |
| `searchable` | Text search |

Example: **phone** → table ✓ rail ✓ search ✓ · **rejection reason** → rail ✓ entity ✓ table ✗.

**Code contract:** `hostflow-frontend/src/platform/entity-model/` — `EntityModel`, `EntityFieldProjection`, `toResourceSchemaFromEntityModel()`.

### Build order (DECISION 2026-07-09 — source before projection)

> **Rail is not canon. Entity Workspace is the full object surface; Rail and Table are projections.**

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **1** | Decision Flow audit (layout baseline only) | **Paused** — no new Rail work |
| **2.1** | **[Entity Model Canon](hostflow-entity-model-v1.md)** — `candidatesEntityModel.ts` reference | **Keep** — L1 passport |
| **2.2** | **[Universal Entity Schema](hostflow-entity-workspace-v1.md)** §2 — widgets, layout, registries | **ACTIVE — sole feature work** |
| **2.3** | **Entity Workspace Shell** — schema executor in five zones | **Scaffold** — geometry only |
| **2.4** | **Projections** — `toDetailRailProjection()` · `toResourceSchema()` ← Model + Schema | **Blocked** until 2.2–2.3 |
| **3** | Universal Application Workspace | After Phase 2 |

**Frozen until Phase 2.2 DoD:** Detail Rail adapters, ObjectDecision composers, Application Workspace rail polish, module «card» layouts.

**Transitional debt:** `candidatesDetailRailAdapter.ts`, `candidatesResourceSchema.ts`, `platform/decision-model/` → replace with Entity Model projections after E6.

**Specs:** [`hostflow-entity-model-v1.md`](hostflow-entity-model-v1.md) · [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md) · `platform/entity-model/`

---

## §0. Reference Scenarios (Phase 1 focus)

> **Reference is ready when continuous flow works — not when components are technically complete, and not by business KPIs (volume, speed).**

A **Reference Scenario** is a finished user job. It is **not** a new Workspace type. It **composes** existing primitives and defines a **Flow**.

### Flows (platform design unit)

The platform is designed around **continuous user movement**, not screens:

| Flow | Path |
|------|------|
| **Decision Flow** | List → Select → Rail → Action → Next object |
| **Entity Flow** | Entity Workspace → Edit → Save → Return to list (same context) |
| **Application Flow** | (Phase 3+) intake → process → outcome |
| **Process Flow** | (Phase 4+) queue → triage → handoff |

**Filter for every change:** *Which Flow does this improve?*  
If the answer is unclear → we are building a component, not the platform. Defer.

### Decision Workspace ← **ACTIVE — Phase 1 exit criterion**

**User job:** непрерывно принимать решения по очереди объектов.

**Decision Flow:**

```text
List → Select → Rail → Action → Next object
         ↑__________________________|
              (context preserved)
```

**Composed from:** Data Table · Selection Model · Detail Rail

**Reference seed:** Candidates list.

**Status:** In Progress — **Phase 1 Audit** (Flow Break elimination).

**Do not** start new primitive work until Candidates Decision Flow passes audit.

#### Reference = continuous flow (not KPI)

Platform validates **behavior**, not throughput. No target counts (not 100, not 30 minutes — those are business metrics, role-dependent).

Flow is Reference when:

```text
Object selected
  → decision made
  → action completed
  → next object available immediately
  → list context preserved (filters, sort, scroll, selection)
  → user does not manually return to the list
  → user does not search for the same object again
  → list remains the main workspace
```

#### Boundary: Decision vs Entity

> **Entity Workspace opens only when Decision Workspace has exhausted its capabilities.**

Test for every action:

> *Can this be done in Decision Flow (list + rail)?*

| Answer | Where it belongs |
|--------|------------------|
| **Yes** | Detail Rail — must not require Entity Workspace |
| **No** | Entity Flow — Primary Entity Link |

#### Product DoD — Decision Workspace Reference

| # | Criterion |
|---|-----------|
| D1 | **Continuous flow:** select → act → next object without manual list recovery |
| D2 | Actions doable in Decision Flow **stay in Rail** — not pushed to Entity Workspace |
| D3 | Entity Workspace **only** when Decision Flow cannot complete the action |
| D4 | After action: rail updates or advances; user never hunts for the same row |
| D5 | **List is the workspace** — rail is companion |
| D6 | Context preserved: filters, sort, scroll, selection, rail target |
| D7 | Interaction Rules: row → rail, link → entity, Esc / Enter / Cmd+Ctrl+Enter |

#### Phase 1 Audit ← **ACTIVE NOW**

> **Flow is verified in real work — not in code review.**

**Team instruction:** not «сделай DataTable» → **«пройди Decision Flow»** on Candidates.

**Method:** one recruiter walks the full Decision Flow on the Candidates list. Every interruption = logged **Flow Break**. Fix breaks until the flow passes clean. Then repeat on Sales.

**Phase 1 is not complete** until Decision Flow passes **without Flow Breaks** on Candidates, then on Sales/Recruitment (≥2 roles), **and** the semantic gate below is satisfied.

##### Phase 1 semantic gate (mandatory — not layout alone)

| # | Criterion |
|---|-----------|
| **S1** | **One mechanics** — every Rail: Fixed Header → Fixed Decision Zone → Scroll Context (independent scroll) |
| **S2** | **State-driven decision** — Fixed Decision Zone from platform `ObjectDecision` (`currentState`, `why`, `primaryAction`) — not a stack of module blocks |
| **S3** | **No Entity duplication** — Context (`requiredContext`) shows only information needed for the *current* decision; full record lives in Entity Workspace |

Spec: [`hostflow-decision-model-v1.md`](hostflow-decision-model-v1.md)

Layout fixes without S1–S3 do **not** close Phase 1.

##### Flow Break (FB) — unit of work

A **Flow Break** is any interruption of continuous Decision Flow. **It is a platform bug** — not only exceptions and console errors.

| ID | Break type | Example | Fix belongs to |
|----|------------|---------|----------------|
| **FB-1** | Forced Entity Workspace | WhatsApp requires full card — but action fits Decision Flow | Rail + adapter / platform |
| **FB-2** | Lost selection | After action, active row / rail target gone | Selection Model |
| **FB-3** | Manual next object | User must find next candidate after action | Rail advance / keyboard |
| **FB-4** | Cognitive gap | User unsure what to do next | Rail `next_action` block |
| **FB-5** | Screen hop | Left list + rail for another screen mid-flow | Platform / adapter |
| **FB-6** | Click tax | Routine action needs >1 non-obvious click | Action tiers / rail |

**FB-1 test:** *Was Entity Workspace truly required?* If no → platform bug.

**Task format:**

```text
Decision Flow Break #12 (FB-2):
After assigning a task, user must re-select the candidate.
```

Not: «Improve Rail.»

**Living log:** [`decision-flow-breaks-log.md`](decision-flow-breaks-log.md)

**Allowed Phase 1 work:** eliminate **verified** Flow Breaks only. Fixes with code merged but **not UI-verified** do not count.

#### Verification gate (mandatory)

1. **Manual Decision Flow** on Candidates — observe user behavior, not code.  
2. Break **reproduces** → stays **open** (ignore PR status).  
3. Mark **verified** only when break cannot be reproduced.  
4. Re-rank open breaks **P0 → P1 → P2** (flow impact).  
5. Fix highest **P0** next — not next discovery number.

**Log:** [`decision-flow-breaks-log.md`](decision-flow-breaks-log.md)

#### Multi-role validation (after zero breaks on Candidates)

Run the **same scenario** through each pilot role. If any role needs **different table or rail behavior** — platform is not Reference; extend platform, not the module.

| Role | Pilot list | Status |
|------|------------|--------|
| **Recruiter** | Candidates | In Progress |
| **Sales** | Обращения / Applications | Queued |
| **HR** | (TBD) | Queued |
| **Fleet** | (TBD) | Queued |

**Phase 1 complete** when Decision Workspace is Reference on **≥2 roles** with **zero** role-specific table/rail forks.

**Primitives** (§3) are improved **in service of this scenario** — not as an independent goal.

---

## How to use this catalog

1. Open the relevant section below.
2. Check **Status** of the entry.
3. Read **Path** (code) and **Spec** (if any).
4. If status is not **Reference** — that primitive is the current build focus, not your feature.

**Do not** add module UI when the catalog entry is Draft or In Progress.

---

## §1. Foundation

Visual tokens — ADR-011. Change via design token PR only.

| Entry | Path | Status |
|-------|------|--------|
| Color tokens | `src/styles/` · ADR-011 | Exists |
| Typography | ADR-011 | Exists |
| Spacing / grid | ADR-011 | Exists |
| Radius / shadow | ADR-011 | Exists |
| Motion | ADR-011 | Partial |
| Icons | `platform/icons/` | Exists |

---

## §2. Interaction Rules

Platform behavior — not owned by any component.

| Entry | Path | Spec | Status |
|-------|------|------|--------|
| Interaction Rules (all) | `platform/interaction-rules/` | [`hostflow-interaction-rules-v1.md`](hostflow-interaction-rules-v1.md) | **Defined — enforce in code** |
| Selection Model | `platform/selection/` | Interaction Rules §3 | In Progress |
| Entity Links | `platform/entity-links/` | Platform Canon §5 | In Progress |

---

## §3. Primitives

One instance each. Variants only. Improved **until Decision Workspace (§0) passes product DoD** — not in isolation.

| # | Primitive | Path | Status | Serves |
|---|-----------|------|--------|--------|
| 0 | **Entity Model** | `platform/entity-model/` | **Phase 2.1 — [spec](../hostflow-entity-model-v1.md)** | All projections |
| 1 | **Data Table** | `platform/data-table/` | Phase 1 — migrate to Entity Model | Collection |
| 2 | **Detail Rail** | `platform/detail-rail/` | **FROZEN** — P0 bugfix only; projection from Entity Model §2.3 | Decision Flow |
| — | **Entity Workspace** | `platform/entity-workspace/` | **Scaffold** — [canon §2 Schema](hostflow-entity-workspace-v1.md) | Entity Flow |
| — | **Selection Model** | `platform/selection/` | In Progress | Decision Workspace |
| 3 | **Button** | `components/ui/Button.tsx` | Draft | All scenarios (Phase 2+) |
| 4 | **Form Field** | `components/ui/` (scattered) | Not started | Input, Select, Checkbox, Switch — one family |
| 5 | **Badge** | `platform/data-table/SemanticBadge.tsx` | Partial | Generalize to platform primitive |
| 6 | **Status** | semantic roles in `platform/data-table/` | Partial | Unify with Badge |
| 7 | **Filter** | `platform/data-table/FacetFilterMenu.tsx` | Partial | Part of Table canon |
| 8 | **Search** | toolbar patterns | Partial | Part of Table canon |
| 9 | **Timeline** | — | Not started | |
| 10 | **Notes** | — | Not started | |
| 11 | **Contacts** | — | Not started | |
| 12 | **Relations** | — | Not started | |
| 13 | **Documents** | — | Not started | |
| 14 | **Notification** | — | Not started | |
| 15 | **Modal** | — | Partial (scattered) | |
| 16 | **Empty State** | — | Partial | |
| 17 | **Skeleton** | — | Partial | |
| 18 | **Avatar** | — | Partial | |
| 19 | **Tag** | — | Partial | |

**Do not** polish primitives for their own sake. Every change must move Decision Workspace (§0) toward Reference.

---

## §4. Compositions

**Assembled from primitives — never designed in isolation.**

| Composition | Built from | Path | Status | Blocked until |
|-------------|------------|------|--------|---------------|
| Entity Header | Button, Badge, Status, Avatar, Breadcrumb, Action Menu | — | **Not started** | Button, Badge, Status Reference |
| Summary strip | Field display, Badge, Status | — | Not started | Form Field, Badge |
| Context Rail | Detail Rail patterns, action tiers | `platform/entity-workspace/types.ts` | Types only | Detail Rail Reference |
| Navigation (sections) | — | — | Not started | — |
| Toolbar | Button, Search, Filter | `platform/data-table/ListWorkspaceToolbar.tsx` | Partial | Table Reference |
| Table Toolbar | same | same | Partial | Table Reference |

### Composition rule (strict)

> **Forbidden to create a new Composition if it requires creating a new Primitive.**

If Entity Header needs a new button variant → extend **Button** primitive first.  
Not Entity Header. Not the candidate module.

---

## §5. Workspaces (config only — do not design)

Workspaces **assemble** when compositions exist. Not built directly.

| Workspace | Assembled from | Status |
|-----------|----------------|--------|
| **Collection** | Data Table + Selection + Detail Rail | Phase 1 — Decision Flow |
| **Entity** | Header + Summary + Nav + Content + **Context Rail** | **Phase 2.2** |
| **Application** | Same compositions + Action Bar + queue | Phase 3 (after Entity) |
| **Process** | Process shell + same primitives | Frozen |

Application Workspace in Phase 3 **does not invent layout** — it composes Header, Summary, Action Bar, Timeline, Documents, Context Rail already defined in Phase 2.

**Prerequisite for Entity UI:** [`hostflow-entity-model-v1.md`](hostflow-entity-model-v1.md). Geometry: [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md).

---

## §6. Adding a catalog entry

When a new primitive is approved:

1. Add one row to §3 or §4 in this file.
2. Set status **Draft**.
3. Implement in `platform/` — not in a module.
4. Move to **Reference** only when roadmap DoD passes.
5. Update Platform Canon child spec **only if behavior changes** — not for every primitive polish.

**Do not** create a new architecture document per primitive. This catalog row is enough.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | v4 — Phase 1 Audit; Flow Break taxonomy; operational verification |
| 2026-07-09 | v3 — Flow terminology; continuous flow DoD |
