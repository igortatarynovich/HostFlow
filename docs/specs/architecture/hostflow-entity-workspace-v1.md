# Universal Entity Workspace Canon v1

**Status:** canonical (L1 — **supreme object surface**).  
**Active work:** **Universal Entity Schema** (§2) — not Shell layout polish.  
**Owner:** Product + Platform UX + Frontend Architecture.  
**Prerequisite:** [`hostflow-entity-model-v1.md`](hostflow-entity-model-v1.md)  
**Parent:** [`hostflow-platform-canon-v1.md`](hostflow-platform-canon-v1.md)  
**Catalog:** [`hostflow-platform-catalog.md`](hostflow-platform-catalog.md) §0.A  
**Behavior:** [`hostflow-interaction-rules-v1.md`](hostflow-interaction-rules-v1.md)  
**Code (scaffold):** `hostflow-frontend/src/platform/entity-workspace/` — geometry only until §2 is implemented  
**Passport reference:** `hostflow-frontend/src/modules/candidates/candidatesEntityModel.ts`

---

## §0. The supreme rule — source before projection

> **Universal Entity Workspace is the canonical full representation of one business object.  
> Detail Rail and Data Table are projections — not independent designs.**

**Build order (non-negotiable):**

```text
1. Entity Model              — what the system KNOWS (passport slices + field registry)
2. Universal Entity Schema   — how the object is ASSEMBLED for the user (widgets, layout, actions, context)
3. Entity Workspace Shell    — executes schema in five fixed zones (geometry only)
4. Projections               — Detail Rail · Table · Search · Filters (compose from Model + Schema)
```

**Key rule:**

| Layer | Decides |
|-------|---------|
| **Passport (Entity Model)** | What data exists — identity, state, documents, actions, outcome |
| **Universal Entity Schema** | What the user **sees** — which widgets, sections, actions, context blocks, order, role visibility |
| **Entity Workspace Shell** | **Nothing about content** — only mounts zones and renders schema slots |
| **Projections** | Which schema/model signals appear in Collection surfaces |

> **Shell does not decide what to show. Passport does not decide how to show. Schema decides.**

**Forbidden:**

| Do not | Because |
|--------|---------|
| Design Detail Rail as canon | Rail composes from Model + Schema — not ad-hoc adapters |
| Design «карточку кандидата / клиента» | Module-specific cards drift from platform |
| Paint Shell layout before Schema | Produces «JSON on screen» — fields without work mode |
| Add fields to Table or Rail without Entity Model | Creates parallel truth |
| Fix Rail layout/symptoms while Schema is missing | Optimizing consequence, not source |

**When questions arise** («куда смотреть первым?», «почему Summary пустой?», «где custom fields?») — **the answer is in Universal Entity Schema**, backed by passport data from Entity Model.

---

## §1. Definition

> **Universal Entity Workspace is the full operational space for one business object — assembled from schema, not from raw passport fields.**

Same **shell geometry** for every entity type: candidate, client, employee, order, company, vehicle, service order, …

The user always knows where they are:

- same **five zones** (platform-fixed);
- **widgets, sections, navigation, actions, and context** come from **Universal Entity Schema** per resource (+ tenant / role overrides);
- **Section Components** in Content — not key-value dumps.

**Entry:** Primary Entity Link — when Decision Flow is exhausted or user explicitly opens the object passport.

**Forbidden terms:** «карточка кандидата», «client card», «lead detail page layout» → **Entity Workspace**.

**Work mode test:** *Does the screen help the user work on the object — or only read fields?* If the latter → Schema is wrong, not Shell CSS.

---

## §2. Universal Entity Schema

> **Universal Entity Schema is the assembly layer between Entity Model (passport) and Entity Workspace Shell (geometry).**  
> It answers: *what widgets, sections, and actions does this user see in each zone?*

Schema is **not a screen design**. It is a **declarative contract** modules and tenants configure; Shell **executes** it.

### §2.1 Stack

```text
Entity Model (L1)           passport slices + field registry
        │
        ▼
Universal Entity Schema (L2)  widgets · sections · layout · actions · context · visibility
        │
        ▼
Entity Workspace Shell (L3)   five zones — render schema slots only
        │
        ▼
Projections (L4)              Rail · Table · Search · Filters
```

### §2.2 Unit of composition: Widget

> **Widget is the primary unit of user-facing meaning — not a field, not an empty «section».**

A widget answers **one question** at a glance:

| Widget id (examples) | Question |
|----------------------|----------|
| `object_identity` | What is this object? |
| `process_pipeline` | Where in the process? |
| `documents_progress` | Documents ready / blocking? |
| `risk_signal` | Risk or expiry? |
| `fit_score` | How well does it match? |
| `primary_relation` | Linked vacancy / client / order? |
| `waiting_on` | Who or what blocks progress? |
| `next_decision` | What to do **right now**? |
| `owner` | Who is responsible? |
| `last_communication` | Last call / WhatsApp / email? |
| `tasks_compact` | Open tasks blocking work? |
| `finance_snapshot` | Money / orders / advances? |
| `custom_field_group` | Tenant-defined fields |
| `repeatable_group` | Repeating records (employment, equipment, …) |

**Summary** = dashboard of **3–7 widgets** (not a flat field list).  
**Context Rail** = decision widgets first (`next_decision`, tasks, last comm) — not a timeline dump.  
**Content** = **Section Components** (see §2.4), each backed by one or more widgets + fields.

Modules **do not** invent widget types in pages. New widget types enter **Widget Registry** (platform).

### §2.3 Registries (schema contract)

Schema **must** define these registries. No UI work proceeds until v1 shapes exist.

#### Widget Registry

```typescript
type EntityWidgetDescriptor = {
  id: string
  /** Platform component that renders this widget */
  componentId: string
  /** Passport slices + optional computed inputs */
  inputs: readonly EntitySectionId[]
  /** Where this widget may appear */
  allowedZones: ('header' | 'summary' | 'content' | 'context')[]
  /** Visual priority when multiple widgets compete for attention */
  priority: 'primary' | 'secondary' | 'tertiary'
  /** Optional role gates */
  visibleForRoles?: readonly string[]
}
```

#### Section Types

Canonical **Section Components** — not DB table names:

| Section type id | Purpose | Example nav label (locale) |
|-----------------|---------|----------------------------|
| `general_info` | Structured identity + metadata | «Общая информация» |
| `contacts` | Reachability + persons | «Контакты» |
| `documents_workspace` | Requirements, uploads, verification | «Документы» |
| `timeline` | Human-meaningful history | «История» |
| `relations` | Linked objects | «Связанные объекты» |
| `finance` | Orders, invoices, advances | «Финансы» |
| `tasks` | Follow-ups (full list) | «Задачи» |
| `comments` | Notes | «Комментарии» |
| `custom_fields` | Tenant field groups | User-defined |
| `repeatable_group` | Repeating entity groups | «Опыт», «Equipment» |
| `outcome` | Terminal state (when applicable) | «Итог» |

Navigation labels come from **Layout Schema** — not from section type ids.

#### Field Types

Canonical field rendering + validation binding:

`text` · `long_text` · `number` · `date` · `datetime` · `enum` · `multi_enum` · `boolean` · `phone` · `email` · `url` · `entity_link` · `file` · `money` · `percent` · `json` · `computed`

Fields bind to Entity Model field ids. **Field Type** decides edit/display widget inside a Section Component.

#### Layout Schema

Per `resourceId` (+ optional tenant override):

```typescript
type EntityLayoutSchema = {
  resourceId: string
  zones: {
    header: { widgets: EntityWidgetSlot[]; actions?: ActionSlot[] }
    summary: { widgets: EntityWidgetSlot[] }
    navigation: { sections: NavigationSectionSlot[] }
    context: { widgets: EntityWidgetSlot[]; blocks: ContextBlockSlot[] }
  }
  /** Section id → section type + widget/field layout inside Content */
  sections: Record<string, EntitySectionLayout>
}

type EntityWidgetSlot = {
  widgetId: string
  width?: 'full' | 'half' | 'third'
  order: number
  visible?: boolean | RoleVisibility
}

type NavigationSectionSlot = {
  id: string
  sectionType: SectionTypeId
  label: string
  order: number
  visible?: boolean | RoleVisibility
}
```

**Navigation is not fixed globally.** One tenant adds «Авансовые платежи»; another adds «Проверка безопасности» — Workspace does not hardcode those names.

#### Action Registry

Maps Entity Model **capabilities** → placement:

| Placement | Examples |
|-----------|----------|
| `header_primary` | Handoff, open full workspace |
| `header_secondary` | Edit, export, bookmark |
| `context_primary` | Call, request documents, create task |
| `context_secondary` | WhatsApp, email |
| `section` | Upload, verify document (inside documents_workspace) |

Actions reference `actions.capabilities` from passport — **never** invent buttons in Shell.

#### Context Registry

Ordered blocks for Zone 5 — answers: **«What do I do right now?»**

Fixed **priority order** (platform); modules enable subset:

1. `next_decision` — primary capability + why
2. `tasks_blocking` — overdue / mandatory tasks
3. `quick_contacts` — call / messenger / email (when work allowed)
4. `last_communication` — last WhatsApp / call signal
5. `reminders`
6. `automations` — active processes
7. `recent_events` — **at most** 3–5, only if decision-relevant

Context Rail **is not** a second History tab.

#### Custom Fields

- Stored in Entity Model field registry with `section: 'custom'` or tenant group id.
- Rendered via Section type `custom_fields` + Widget `custom_field_group`.
- Layout Schema declares **which groups** appear in which nav section.
- Table/Rail projection flags remain on field descriptors (`showInTable`, `showInRail`, …).

#### Repeatable Groups

- Schema declares `repeatable_group` sections (e.g. employments, equipment).
- Each group: `groupId`, `itemLabel`, field subset, min/max items, add/remove policy.
- Same Section Component for all resources — different layout bindings.

#### Projection Rules

Schema + Model together drive Collection surfaces:

| Surface | Composes from |
|---------|----------------|
| Detail Rail | `showInRail` fields + context widgets marked `railEligible` + `requiredContext` from process state |
| Data Table | `showInTable` fields + primary entity link |
| Search | `searchable` fields |
| Filters | `filterable` fields |
| Summary widgets | Only widgets with `summaryEligible` in registry |

**Forbidden:** parallel `*DetailRailAdapter.ts` field lists after schema migration (Phase 2.4).

### §2.4 Zone purpose (schema fills zones)

| Zone | User question | Schema supplies | Must not be |
|------|---------------|-----------------|-------------|
| **1 Header** | «What object is this?» | identity widget, type, stage, status, outcome, header actions, prev/next | Metadata dump (ID + owner + source + history equal weight) |
| **2 Summary** | «What is happening in 3–5 seconds?» | 3–7 widgets: pipeline, docs, risk, fit, waiting, primary relation | Flat passport field list |
| **3 Navigation** | «Where to work deeper?» | **Layout Schema** `navigation.sections` — user-facing labels | Fixed enum `overview \| contacts \| timeline \| …` |
| **4 Content** | «I work on details here» | Active **Section Component** per nav id | Key-value JSON |
| **5 Context Rail** | «What do I do **right now**?» | Context Registry blocks | Full timeline / duplicate Content |

### §2.5 Schema implementation path (order)

1. **Describe** registries in platform types (`platform/entity-schema/` — TBD).
2. **Candidate Entity Schema** — first reference layout (Recruitment).
3. **Shell executor** — `renderEntityWorkspace(schema, passport)` replaces hardcoded section maps.
4. **Candidate consumer** — via schema only (flag stays off until pass work-mode test).
5. **Detail Rail projection** — compose from Model + Schema.
6. **Table projection** — compose from Model + Schema.

---

## §3. Entity Model ↔ Schema ↔ Workspace

Entity Model defines **passport data**. Universal Entity Schema defines **assembly**. Shell renders zones.

| Entity Model section | Passport data | Typical widgets / sections (schema) |
|----------------------|---------------|-------------------------------------|
| `identity` | Who / what | Header: `object_identity` · Content: `general_info` |
| `state` | Process position | Summary: `process_pipeline`, `waiting_on` · Header: status badges |
| `ownership` | Responsible party | Summary: `owner` |
| `contacts` | Reachability | Content: `contacts` · Context: `quick_contacts`, `last_communication` |
| `actions` | Allowed capabilities | Header + Context: Action Registry → `next_decision` |
| `documents` | Requirements state | Summary: `documents_progress` · Content: `documents_workspace` |
| `timeline` | Events | Content: `timeline` · Context: `recent_events` (trimmed) |
| `relations` | Linked objects | Summary: `primary_relation` · Content: `relations` |
| `tasks` | Follow-ups | Context: `tasks_blocking` · Content: `tasks` |
| `outcome` | Terminal close | Header outcome · Content: `outcome` · suppress actions |

Modules **enable a subset** via Layout Schema. They **never fork shell geometry**.

---

## §4. Five fixed zones (Shell — scaffold)

```text
┌─────────────────────────────────────────────────────────────┬──────────────┐
│ ZONE 1 — HEADER                                             │              │
│ title · status · stage · breadcrumbs · header actions · ◀ ▶ │              │
├─────────────────────────────────────────────────────────────┤  ZONE 5      │
│ ZONE 2 — SUMMARY (never scrolls away)                       │  CONTEXT     │
│ critical passport fields only                               │  RAIL        │
├──────────────┬──────────────────────────────────────────────┤              │
│ ZONE 3     │ ZONE 4 — CONTENT (single active section)      │  deep-work   │
│ NAVIGATION │ Overview · Contacts · Documents · History · … │  companion   │
│            │ primitive embeds only                         │              │
└──────────────┴──────────────────────────────────────────────┴──────────────┘
```

| Zone | Shell owns (geometry) | Schema fills (content) |
|------|----------------------|-------------------------|
| **1 Header** | Title row, status strip, action bar, prev/next | Widgets + Action Registry |
| **2 Summary** | Fixed non-scrolling dashboard row | 3–7 summary widgets |
| **3 Navigation** | Tab / section switcher chrome | `navigation.sections` from Layout Schema |
| **4 Content** | Scroll area, one active section | Section Component instance |
| **5 Context Rail** | Fixed right column width | Context Registry blocks |

Platform owns **geometry only**. `EntityWorkspaceShell` is **scaffold** until schema executor lands.

**Forbidden:** Shell hardcoding section ids, field lists, or widget choice per resource type.

---

## §5. Canonical sections — reference (legacy §4.1–§4.9)

> **Note:** §5 describes *semantic purpose* of section types. **Navigation labels and visibility** come from Layout Schema (§2.3), not from this list.

### §5.1 Summary (widget dashboard)

**Purpose:** At-a-glance passport — **without opening a section**.

**Contains:**

- Process state in product language («В работе», «Передан в HR»)
- Owner / assignee (one line)
- Blockers that affect **any** role («Не хватает карты пobyту»)
- At most **3–5** fields flagged `showInEntitySummary`

**Must not contain:**

- Full contact card (phone, email, citizenship, DOB together)
- Document lists
- Timeline
- Anything the user must scroll to find in Entity Workspace — Summary is **fixed strip**

**Test:** *Would a manager understand the object's situation in 3 seconds?*

---

### §5.2 Contacts

**Purpose:** All reachability and contact persons for **this object**.

**Contains:**

- Phones, emails, messengers (with actions)
- Contact persons, roles
- Preferred channel / policy (if applicable)

**Must not appear in:**

- Detail Rail as full card (Rail: icon actions only when `showInRail` + communication is active work)
- Data Table except primary phone/email columns if `showInTable`

---

### §5.3 Documents

**Purpose:** Requirements, uploads, verification state — **source of truth for doc blockers**.

**Contains:**

- Required document types and status
- Upload / verify / reject actions (Entity Workspace is editable)
- Links to Universal Document Workspace primitive

**Detail Rail projection:** only when documents **block the current decision** (`showInRail` + blocker flag from `state`).

---

### §5.4 Timeline (History)

**Purpose:** Human-meaningful **events** — not system logs.

**Contains:**

- Stage changes (product labels)
- Calls, messages, meetings (when recorded)
- Handoffs, decisions, assignments

**Must not contain:**

- Raw API codes (`ready_for_handoff`)
- Duplicate of Summary state without new information

**Detail Rail projection:** last **N** events (typically 3–5) only when context helps the **current** decision.

---

### §5.5 Relations

**Purpose:** Linked business objects (vacancy, client, order, search, vehicle, …).

**Contains:**

- Entity links (Primary / Secondary per Interaction Rules)
- Relation role label («Подбор», «Клиент», «Заказ»)

**Detail Rail projection:** only relations **relevant to next action** (e.g. vacancy during qualify).

---

### §5.6 Outcome

**Purpose:** **Terminal process state** — process closed for a role.

**Contains:**

- Outcome title («Отклонён», «Рекрутинг завершён», «Передан в HR»)
- Why (rejection reason, handoff destination) — product language
- Owner at close, date
- **No next-step actions** for the closed role

**Rules:**

| Process state | Primary actions | Outcome block |
|---------------|-----------------|---------------|
| Active | From `actions` section | Hidden |
| Terminal for role | **None** | **Visible** |
| Handed off (recruiter done) | None for recruiter | «Передан в HR» + owner |

> This is why «Позвонить» must not appear for a rejected candidate: **`actions` is empty when `outcome` is set for that role** — not because Rail hides a button.

---

### §5.7 Tasks & reminders

**Purpose:** Operational follow-ups tied to the object.

**Primary home:** **Context Rail** (Zone 5).

**Summary / Rail:** only when a task **blocks** the pipeline (overdue, mandatory).

---

### §5.8 Overview / general_info

**Purpose:** Default Content section — structured passport fields not better served by a dedicated primitive.

**Contains:**

- Identity fields (`editable` where allowed)
- Outcome block (when terminal)
- Key metadata (source, created, tags)

**Must not become:** a second full card with every field duplicated from other sections.

---

### §5.9 Comments & Activity

**Purpose:**

- **Comments** — human notes (Universal Notes primitive)
- **Activity** — operational / system activity stream (optional, licensed)

Separate from **Timeline** (History): Timeline = business events; Activity = fine-grained ops log.

---

## §6. Context Rail (Zone 5 — schema-driven)

> **Context Rail sustains deep work inside Entity Workspace.  
> It is NOT Detail Rail. Same visual language; different contract.**

| | Detail Rail (Collection) | Context Rail (Entity Workspace) |
|---|--------------------------|----------------------------------|
| **Parent** | Collection / queue | Entity Workspace Zone 5 |
| **Source** | Entity Model projection `showInRail` + decision composer | Entity Model `showInContextRail` + `tasks` |
| **Purpose** | One decision → next object | Ongoing work on one object |
| **Editable** | No | Actions only (no inline field edit in rail) |
| **Typical blocks** | State, why, primary action, compact contacts | Tasks, reminders, process steps, recent events |

**Context Rail never duplicates Content sections in full** (no full document list, no full timeline).

Block order (platform-fixed):

1. `next_actions` — derived from `actions` (Entity Model)
2. `tasks`
3. `reminders`
4. `processes`
5. `recent_events`

---

## §7. Projections — Rail and Table derive from Model + Schema

Detail Rail and Data Table **do not define content**. A **projection composer** reads Entity Model + runtime entity state.

### §6.1 Detail Rail composer (Decision Flow)

```text
Input:  EntityModel + entity instance + role + processState
Output: DetailRailModel (layout only — blocks mount/unmount)

Fixed Header  ← identity + state (product labels) + entity link
Fixed Decision ← state.currentDecision + state.why + actions.primary (if any)
Scroll Context ← requiredContext[] — computed from processState, not fixed globally
```

**`requiredContext` is state-driven** (examples):

| Process state | Scroll blocks |
|---------------|---------------|
| First contact | `timeline` (short) |
| Awaiting documents | `documents`, `timeline` |
| Handoff ready | `documents`, `relations`, `timeline` |
| Terminal / outcome | `outcome` summary only — **no actions** |

**Duplication rule:** if field has `showInEntitySummary` or lives in Contacts section, Rail **must not** repeat it unless `showInRail` is explicitly true **and** needed for the decision (e.g. one-click call).

### §6.2 Data Table composer (Collection)

```text
Input:  EntityModel fields where showInTable
Output: ResourceSchema columns + entity links
```

Comparison columns only — not the passport.

### §6.3 Search & filters

Same model flags — `searchable`, `filterable`. No parallel registries.

---

## §8. Process state vs data state

| | Data state | Process state |
|---|------------|---------------|
| **What** | Raw fields (`stage`, `row_status`, flags) | Role-specific meaning |
| **Where defined** | Entity Model `state` section | Entity Model — computed labels + `outcome` |
| **User sees** | Never raw codes in Workspace / Rail | «Передан в HR», «Ожидает документы» |

**Module adapters** map API → process state **once**, in Entity Model layer — not in Rail.

---

## §9. Configuration contract (schema-driven)

```typescript
/** Target contract — replaces ad-hoc EntityWorkspaceConfig */
type EntityWorkspaceRenderInput = {
  resourceId: string
  entityId: string
  passport: EntityPassport
  layout: EntityLayoutSchema
  widgetRegistry: EntityWidgetRegistry
  actionRegistry: EntityActionRegistry
  contextRegistry: EntityContextRegistry
}
```

Module implements **`build{Resource}EntityLayoutSchema(...)`** + passport via Entity Model — **not a page layout**.

Navigation sections come from `layout.zones.navigation.sections` — **not** a platform-fixed enum in Shell.

---

## §10. Work freeze & artifact status (2026-07-09)

| Artifact | Status | Notes |
|----------|--------|-------|
| **Entity Model / passport** | **Keep** | L1 — [`candidatesEntityModel.ts`](../../../hostflow-frontend/src/modules/candidates/candidatesEntityModel.ts) |
| **Universal Entity Schema** | **ACTIVE** | §2 — design + platform types; sole feature work |
| **EntityWorkspaceShell** | **Scaffold** | Five zones only — not Reference |
| **Candidate consumer** | **Frozen** | No production route until schema executor passes work-mode test |
| **Detail Rail projection** | **Blocked** | After Candidate schema |
| **Table projection** | **Blocked** | After Candidate schema |
| **Layout polish** | **Stop** | No CSS/tabs/cards without schema |
| **Production flag** `VITE_FEATURE_CANDIDATE_ENTITY_WORKSPACE` | **Off** | Legacy `CandidateCard` remains path |

| Surface | Status |
|---------|--------|
| Detail Rail adapters / layout | **FROZEN** — P0 bugfix only |
| ObjectDecision composers | **FROZEN** |
| Application Workspace rail polish | **FROZEN** |
| Candidate / Client legacy page layouts | Bugfix only |

**Next allowed implementation (strict order):**

1. Platform Entity Schema types + registries (§2.3)
2. **Candidate Entity Schema** — reference layout
3. Shell schema executor (replace hardcoded section maps)
4. Candidate workspace via schema (flag on only after work-mode review)
5. `toDetailRailProjection()` from Model + Schema
6. `toResourceSchema()` from Model + Schema

---

## §11. Phase 2 Definition of Done (revised)

| # | Criterion |
|---|-----------|
| E1 | Entity Model reference — Candidate passport |
| E2 | Universal Entity Schema §2 — registries in platform |
| E3 | Candidate Entity Schema — reference layout |
| E4 | Shell executes schema — five zones, no resource-specific branches |
| E5 | Summary = widget dashboard; Context = decision registry |
| E6 | Custom fields + repeatable groups — schema paths exist |
| E7 | Outcome suppresses actions (passport rules) |
| E8 | Rail + Table composers read Model + Schema |
| E9 | Second entity pilot (client) — schema config only |

**Phase 2 complete** → Collection projections migrated; legacy card retired per resource.

---

## §12. Relationship to Collection Workspace

```text
Collection Workspace                         Entity Workspace
────────────────────                         ─────────────────
Data Table ← projection                      Header + Summary + Nav + Content
Selection Model                              Context Rail (Zone 5)
Detail Rail ← toDetailRailProjection()       (schema-assembled)
     ↑                                              ↑
     └──── Entity Model (passport) + Entity Schema ─┘
```

Returning to list preserves Selection Model (filters, sort, scroll, rail target if entity still in view).

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | v2 — **Universal Entity Schema** §2; Shell = scaffold; widget layer; freeze layout polish; flag off |
| 2026-07-09 | v1 — Universal Entity Workspace Canon; section definitions; projections; Rail freeze |
| 2026-07-09 | v0 — five zones (prior doc) merged into this canon |
