# HostFlow UI Platform v1

> **Redirect:** Supreme constitution is **HostFlow Platform Canon v1**.  
> **Read first:** [`hostflow-platform-canon-v1.md`](hostflow-platform-canon-v1.md)  
> **Behavior:** [`hostflow-interaction-rules-v1.md`](hostflow-interaction-rules-v1.md)  
> **Layers:** [`hostflow-interaction-platform-v1.md`](hostflow-interaction-platform-v1.md)  
> **Entity deep work:** [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md)

**Status:** canonical alias (L1 — retained for links and ADR-011 references).  
**Owner:** Product + Platform UX + Frontend Architecture.  
**Audience:** design, frontend, backend (field metadata + facets API), AI agents.

**Sibling L1:** [`ui-constitution-v1.md`](ui-constitution-v1.md) — **product objects**, ownership matrix, Lead ban (domain, not geometry).  
**Build roadmap:** [`ui-primitives-roadmap.md`](ui-primitives-roadmap.md)  
**Parent:** [`hostflow-operational-model.md`](hostflow-operational-model.md)

---

## §0. The two principles

### §0.1 There are no screens

> **In the system there are no screens. There are compositions of primitives.**

Opening «Кандидаты» is not a candidate screen. It is:

```text
AppShell
  + DataTable Engine
  + Detail Rail (row selection)
  + Filter Engine
  + Search Engine
  + Selection Engine
  + Action Panel (bulk / entity actions)
```

Opening «Клиенты» — **the same composition**. Only **data and field configuration** change.

### §0.2 No component knows the module

> **No UI component may know which module it serves. It knows only the data contract.**

Applies to: table, card, documents, timeline, action panel, search, filters, badges, statuses, tags, avatars.

Recruitment, Sales, HR, Fleet, Finance supply **field schemas + configuration**. The platform stays visually and behaviorally one system.

### §0.3 Workspace is not the canon

> **Workspace is a composition of canonical components — not a canon itself.**

Building Application Workspace before Universal Data Table recreates unique tables inside every workspace. **Build bottom-up.**

### §0.4 Two interaction intents (Table vs Entity)

> **Row click never opens a new page. Row click opens Detail Rail only.**  
> **Primary Entity Link always opens Entity Workspace.**

| Intent | Gesture | Result | Mode |
|--------|---------|--------|------|
| **Quick decision** | Click row (not an entity link) | Detail Rail via **Selection Model** | Read-only + quick actions |
| **Deep work** | Click **Primary Entity Link** | Entity Workspace | Full card — edit, save, documents |

**Entity Links** (not field ids): each row declares a **Primary Entity Link** (main card hop) and optional **Secondary Links** (vacancy, order number, avatar, …). Multiple links per row are allowed.

```text
Row click          → Selection Model → Detail Rail
Primary link click → Entity Workspace
```

**Detail Rail is read-only** and **independent of DataTable** — same rail opens from kanban, calendar, search, notifications.

**Table = operational center. Entity Workspace = object management.**

### §0.5 Three platform primitives (Phase 1 canon)

```text
Universal Selection Model  →  which object is active, rail open, pinned, bulk, prev/next
Universal Data Table       →  displays data; emits "open Detail Rail for X"
Universal Detail Rail      →  decision surface for selected object
```

**Selection Model** owns: `activeId`, `railOpen`, `railEntityId`, `pinned`, `bulkIds`, prev/next navigation.  
**DataTable** never embeds Detail Rail. **Detail Rail** never owns table state.

When filters/sort change, if `railEntityId` remains in the current collection — **rail stays open** (one workspace feel).

---

## §1. Four levels (design order)

Design and implement **strictly bottom-up**:

```text
Level 4  Workspace              Application · Entity · Collection · Process
              ↑
Level 3  Composite Components   Application Card · Entity Card · Document Panel · …
              ↑
Level 2  UI Primitives           DataTable · Filter · Search · Badge · Timeline · …
              ↑
Level 1  Layout System           AppShell · Grid · Split View · Breakpoints · …
```

| Level | Name | Changes | Build order |
|-------|------|---------|-------------|
| **1** | **Layout System** | Never per module | Foundation (mostly exists: AppShell) |
| **2** | **UI Primitives** | Never per module | **Start development here** (Phase 1) |
| **3** | **Composite Components** | Assembled from primitives only | After primitives v1 |
| **4** | **Workspace** | Zone layout + config | Last — config only |

---

## §2. Level 1 — Layout System

**The geometry of the product.** Fixed across all modules.

| Element | Rule |
|---------|------|
| **AppShell** | Sidebar + main + optional rails |
| **Sidebar** | Nav groups; width tokens fixed |
| **Header** | Page title zone; one primary action slot |
| **Workspace** | Main work area — fills remaining viewport |
| **Split View** | List + detail; breakpoints define stack vs side-by-side |
| **Grid** | Column widths (e.g. work-panel rail 380px), gutters |
| **Spacing** | Platform spacing scale (ADR-011) |
| **Breakpoints** | Mobile / tablet / desktop — one map |

Modules **do not** define layout geometry. They declare **which zones are filled** with which primitive.

**Platform path (target):** `hostflow-frontend/src/platform/layout/`

---

## §3. Level 2 — UI Primitives

**Where all development starts.** Each primitive is **module-agnostic** and driven by **contracts** (§8).

### §3.1 Inventory

| Primitive | Role |
|-----------|------|
| **DataTable Engine** | Universal list / grid — displays data; emits selection events |
| **Selection Model** | Active object, rail open, pin, bulk, prev/next — shared by table/kanban/calendar |
| **Detail Rail** | Fixed-width decision panel — independent primitive |
| **Filter Engine** | Per-field filters; auto-built from field metadata + facets |
| **Search Engine** | Unified index — user does not choose field |
| **Selection Engine** | Row select, bulk bar, select-all |
| **Semantic Color System** | Meaning → color (§4) — not decoration |
| **Badge** | One component; semantic token in, styled chip out |
| **Status** | Five-bucket UI status + adapter |
| **Tags** | One tag chip + tag input |
| **Avatar** | One avatar (person / company / entity) |
| **Timeline** | One activity stream |
| **Action Panel** | One action chrome; plugin actions |
| **Empty State** | No data vs no matches |
| **Loading** | Skeleton / spinner — one pattern |
| **Saved Views** | Persist filter + column layout |

Visual tokens (button radius, typography): [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md).

---

## §4. Semantic Color System (canon)

**Not «brand colors». Semantic encoding — immutable meaning across the platform.**

| Semantic role | Color family | Used for |
|---------------|--------------|----------|
| **Process stage** | Blue | Pipeline step, workflow phase |
| **Success / complete** | Green | Done, ready, converted |
| **Block / reject / error** | Red | Rejected, blocked, critical failure |
| **Attention / waiting** | Amber / yellow | Needs action, overdue, pending review |
| **Source** | Purple | Intake source (Meta, referral, …) |
| **Object type** | Teal | Entity kind, module accent on type |
| **Neutral / idle** | Slate | Unknown, inactive, archived |

**Rules:**

- A given **meaning** always maps to the same semantic role — never a module-local palette.
- Modules register **value → semantic role** (e.g. `stage.docs_wait → process_stage`).
- Primitives render **semantic role → Tailwind token** in one registry: `platform/semantic-colors/`.

Existing seeds to consolidate: `StageTag`, `DOC_READINESS_META`, `NextActionBadge`, `APPLICATION_STATUS_BADGE`.

---

## §5. DataTable Engine

**The most important primitive.** A **data engine**, not a table widget.

### §5.1 Domain blindness

The engine does **not** know «candidate», «client», or «order».

It knows **fields**:

```typescript
type FieldDescriptor = {
  id: string              // stable: 'citizenship', 'vat_id', 'delivery_cost'
  label: string           // i18n key or resolved label
  kind: FieldKind         // text | number | date | enum | ref | user | tags | money | …
  sortable?: boolean
  filterable?: boolean
  defaultWidth?: number
  pinned?: 'left' | 'right' | false
  renderer?: FieldRendererId  // optional override; default from kind
  semanticRole?: SemanticRole  // for Badge / color (§4)
  icon?: string
  searchable?: boolean    // included in unified search index
}
```

Module provides **`ResourceSchema`**:

```typescript
type ResourceSchema = {
  resourceId: string       // 'candidates' | 'clients' | …
  fields: FieldDescriptor[]
  defaultVisibleFieldIds: string[]
  defaultFieldOrder: string[]
  primaryFieldId: string   // deprecated → use entityLinks
  entityLinks: EntityLinkDescriptor[]  // primary + secondary workspace links
}
```

**Any field on the entity card must be addable as a column** — if «Рост» exists on candidate card, it appears in column picker without code change.

### §5.2 Column capabilities

| Capability | Required |
|------------|----------|
| Add / remove column (any field from schema) | yes |
| Reorder (drag) | yes |
| Pin left / right | yes |
| Resize | yes |
| Persist (user prefs + Saved View) | yes |

### §5.3 Filter Engine — facet law

Filters are **built automatically** from field `kind` + server **facets**.

> **Show only values that exist in the current result set, with counts.**

```text
▼ Источник
  Facebook (34)
  WhatsApp (19)
  Telegram (8)
```

If Email has zero rows — **Email is not in the menu**.

API contract:

```json
{
  "items": [...],
  "total": 42,
  "facets": {
    "source": [{ "value": "facebook", "label": "Facebook", "count": 34 }]
  }
}
```

### §5.4 Search Engine — unified index

User does **not** choose «search by name» vs «search by phone».

One input. System searches all fields marked `searchable: true`:

```text
Иван · +48501234567 · work-host · VAT · ABC-123
```

Backend: single query param `q` → OR across indexed fields (name, phone, email, short_id, company, vat, order_no, …).

### §5.5 Sort, group, bulk, views

| Feature | Contract |
|---------|----------|
| Sort | Per field where `sortable: true` |
| Group | By any enum/ref field (stage, assignee, company) |
| Bulk actions | Selection Engine + action slots in schema |
| Saved Views | Name + filter state + optional column layout |

**Reference seed:** `modules/candidates/*` → extract to `platform/data-table/`.  
**Presentation layer:** `components/layout/DataTable.tsx` (visual shell).

### §5.6 Universal Detail Rail (canon)

**Every large list screen = exactly two zones:**

```text
┌─────────────────────────────┬──────────────┐
│  Universal Data Table       │ Detail Rail  │
│  (flex, full remaining width)│ (fixed width)│
└─────────────────────────────┴──────────────┘
```

| Rule | Detail |
|------|--------|
| Row click | Opens Detail Rail — **no navigation**, no modal card (§0.4) |
| Entity link click | Opens Entity Workspace — Primary / Secondary links in `entityLinks` |
| Active row | Distinct background; row stays visible in table |
| Switch row | Rail content swaps instantly |
| Detail Rail ≠ Entity Card | Rail = **decision surface**; deep work in Entity Workspace |
| Detail Rail read-only | Quick actions only — no inline edit of entity fields (§0.4) |
| Domain blindness | Rail receives `DetailRailModel` only — same 9 blocks for every resource |

**Fixed block order:** header → contacts → next_action → quick_actions → summary → history → documents → relations → more_actions.

**Platform path:** `hostflow-frontend/src/platform/data-table/DetailRail.tsx`, `DataTableWithDetailRail.tsx`.

**Module adapter:** `buildXDetailRailModel(entity, previewBundle) → DetailRailModel`.

**Architecture violation:** a module-specific Detail Rail or list layout without UDT + Detail Rail requires **platform change**, not a one-off component.

---

## §6. Other primitives (summary contracts)

### §6.1 Badge

One component. Input: `{ label, semanticRole, icon? }`. No `CandidateBadge`.

### §6.2 Status

Five UI buckets + `toUiStatus(backendValue, statusMap) → bucket`. One adapter pattern.

### §6.3 Tags

One chip, one multi-select filter kind, one inline editor.

### §6.4 Avatar

Person / company / fallback initial. One component.

### §6.5 Timeline

Event: `{ id, at, actor, kind, summary, links? }`. Kind → renderer plugin. One shell.

### §6.6 Action Panel

Action: `{ id, label, variant, when?, run }`. Zones: Contact · Progress · Outcome · Custom. One chrome.

### §6.7 Empty State / Loading

Two empty variants (no data / no matches). One skeleton pattern for tables and cards.

---

## §7. Level 3 — Composite Components

**Assembled only from primitives.** No new layout or color systems.

| Composite | Primitives used |
|-----------|-----------------|
| **Application Card** | Header, Summary, Timeline, Action Panel, Badge, Status |
| **Entity Card** | Header, Summary, Tabs, Timeline, Documents, Activity, Relations, Action Panel |
| **Document Panel** | Documents primitive + Badge (readiness) |
| **Document Viewer** | Viewer chrome + Timeline events |
| **Activity Feed** | Timeline + Avatar |
| **Communication Panel** | Action Panel (contact) + Activity |

Composites expose **slot configs**, not JSX forks per module.

---

## §8. Level 4 — Workspace

**Zone maps only.** Each workspace type declares which composites appear where.

| Workspace | Typical composition |
|-----------|---------------------|
| **Collection** | Layout + DataTable + Filter + Search + Selection + (Detail rail) |
| **Application** | Layout + DataTable (queue) + Application Card + Hero CTA + Work session |
| **Entity** | Layout + Entity Card (full) |
| **Process** | Layout + progress header + scoped DataTable + stats + tools |

Product meaning of workspaces: [`ui-constitution-v1.md`](ui-constitution-v1.md) §3.

---

## §9. Module integration

Modules deliver **configuration**, not UI:

| Deliverable | Example |
|-------------|---------|
| `ResourceSchema` | field list for candidates |
| `statusMap` | backend stage → UI bucket |
| `semanticMaps` | enum value → semantic role |
| `actionDefs` | Action Panel plugins |
| `facet API` | list + facets endpoint |
| Data adapters | fetch rows, fetch detail |

**Forbidden:** `CandidatesTable.tsx` with custom filter UI. **Required:** `candidates.resource.ts` exporting schema + adapters.

---

## §10. Platform directory (target)

```text
hostflow-frontend/src/platform/
  layout/           # Level 1
  data-table/       # DataTable Engine + Filter + Selection
  search/           # Search Engine
  semantic-colors/  # Semantic Color System registry
  badge/            # Badge, Status, Tags
  avatar/
  timeline/
  action-panel/
  empty-state/
  loading/
  saved-views/
  composites/       # Level 3 — ApplicationCard, EntityCard, …
  workspace/        # Level 4 — zone composer
```

---

## §11. Build phases

See [`ui-primitives-roadmap.md`](ui-primitives-roadmap.md).

| Phase | Focus |
|-------|-------|
| **1 ← now** | DataTable Engine + Filter + Search + Selection + Saved Views |
| 2 | Entity Card composite (primitives inside) |
| 3 | Documents primitive |
| 4 | Timeline |
| 5 | Action Panel |
| 6 | Workspace composer |
| 7–10 | Workspace configs (Application → Entity → Process → Collection) |

Layout System: stabilize during Phase 1; no pixel-perfect sidebar epic before Phase 6.

---

## §12. PR gate

1. Which **level** (1–4)? Build bottom-up only.  
2. Does the component import module-specific types or routes? → reject  
3. New list column — from `FieldDescriptor`, not hardcoded JSX?  
4. New color — `semanticRole`, not raw Tailwind in page?  
5. Filter — facet API with counts?  
6. New page — composition declaration, not new screen type?

---

## §13. Related documents

| Document | Role |
|----------|------|
| [`ui-constitution-v1.md`](ui-constitution-v1.md) | Product objects, ownership, Lead ban |
| [`ui-primitives-roadmap.md`](ui-primitives-roadmap.md) | Phase checklist |
| [`design-system-constitution-v1.md`](design-system-constitution-v1.md) | **Superseded** — merged into this doc |
| [`ADR-010`](ADR-010-unified-resource-list-shell.md) | Field kinds (feeds FieldDescriptor) |
| [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md) | Visual tokens |
| [`ADR-017`](ADR-017-workspace-layer.md) | Entity zones → Entity Card composite |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | **HostFlow UI Platform v1** — four levels, FieldDescriptor, Semantic Color System; terminology shift from UI Constitution |
