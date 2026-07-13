# HostFlow Interaction Platform v1

**Status:** canonical (L1 — platform layer spec: Primitives + Compositions + Workspaces).  
**Owner:** Product + Platform UX + Frontend Architecture.  
**Audience:** design, frontend, backend, AI agents.

**Supreme constitution:** [`hostflow-platform-canon-v1.md`](hostflow-platform-canon-v1.md) — **HostFlow Platform Canon** (entry point).  
**Behavior layer:** [`hostflow-interaction-rules-v1.md`](hostflow-interaction-rules-v1.md) — Interaction Rules (Layer 2).  
**Also known as:** HostFlow Design Platform (foundation + primitives + compositions).  
**Supersedes naming:** «HostFlow UI Platform» — [`hostflow-ui-platform-v1.md`](hostflow-ui-platform-v1.md) redirects here.  
**Sibling L1:** [`ui-constitution-v1.md`](ui-constitution-v1.md) — product objects, ownership, Lead ban.  
**Build roadmap:** [`ui-primitives-roadmap.md`](ui-primitives-roadmap.md)  
**Entity deep work:** [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md)

---

## §0. What this is

> **HostFlow is not a CRM with screens. It is an operational system with one interaction language.**

We do not design «candidate card», «client card», or «order screen».  
We design **primitives** and **compositions**. Workspaces are **config only**.

**Only these change per module:**

- data (fields, entities);
- available actions;
- access rights.

**These never change per module:**

- layout geometry;
- interaction behavior;
- primitive semantics.

---

## §0.1 There are no screens

> **In the system there are no screens. There are compositions of primitives.**

### §0.2 No primitive knows the module

> **No UI primitive may know which module it serves. It knows only the data contract.**

### §0.3 Workspace is not the canon

> **Workspace is a composition of canonical components — not a canon itself.**

---

## §0.4 Two interaction intents

| Intent | Gesture | Surface |
|--------|---------|---------|
| **Quick decision** | Row/card click (not entity link) | **Detail Rail** via Selection Model |
| **Deep work** | **Primary Entity Link** | **Entity Workspace** |

**Entity Links:** Primary (main hop to Entity Workspace) + Secondary (vacancy, order #, avatar, …). Not bound to a single column field.

**Detail Rail** — read-only, quick actions, independent of DataTable.  
**Entity Workspace** — full operational space for one object. Not a «card».

---

## §0.5 Phase 1 primitives (shipped direction)

```text
Universal Selection Model   →  active id, rail, pin, bulk, prev/next
Universal Data Table        →  displays collections; emits selection
Universal Detail Rail       →  decision surface (list context)
```

Platform paths: `platform/selection/`, `platform/data-table/`, `platform/detail-rail/`.

---

## §0.6 Phase 2 primitive (next canon)

```text
Universal Entity Workspace  →  deep work on one entity (all modules)
```

Five **fixed zones** — same for candidate, client, employee, order, vehicle, document:

| Zone | Role |
|------|------|
| **Header** | Title, status, stage, breadcrumbs, quick actions, prev/next |
| **Summary** | Critical fields — always visible, no scroll |
| **Navigation** | Fixed-order **sections** (not ad-hoc tabs per module) |
| **Content** | Single swap area — section body loads here |
| **Context Rail** | Persistent right rail — next actions, tasks, reminders, recent events |

**Context Rail ≠ Detail Rail.** Detail Rail = list decision. Context Rail = entity deep work companion.

Entity Workspace **never invents** Documents, Timeline, Notes, Contacts, Relations — it **embeds** those primitives.

See [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md).

---

## §1. Platform hierarchy (strict)

```text
Foundation          grid, spacing, type, color, radius, motion, icons, shadows
       ↑
Interaction Rules   click, keyboard, selection, navigation, editing, action tiers
       ↑
Primitives          Button, Input, Badge, Table, Detail Rail, Timeline, …
       ↑
Compositions        Entity Header, Summary, Navigation, Context Rail, Toolbar, …
       ↑
Workspaces          Collection · Entity · Application · Process
```

| Layer | Rule |
|-------|------|
| **Foundation** | ADR-011 tokens; never per module |
| **Interaction Rules** | Platform-wide behavior — see [`hostflow-interaction-rules-v1.md`](hostflow-interaction-rules-v1.md); code: `platform/interaction-rules/` |
| **Primitives** | One Button, one Input, one Table — variants only |
| **Compositions** | Assembled from primitives only |
| **Workspaces** | Zone layout + config; zero custom geometry |

### §1.2 Interaction rule extension

> **Forbidden to add module-specific click, keyboard, or selection behavior. Extend Interaction Rules canon first.**

### §1.3 The team rule (primitives)

> **Forbidden to create a new UI element until it is proven an existing Primitive cannot be extended.**

Applies to: buttons, fields, badges, tables, rails, notifications, modals, filters, search, empty states.

---

## §2. Primitives inventory (target)

| Primitive | One instance | Module supplies |
|-----------|--------------|-----------------|
| Button | Primary / Secondary / Ghost / Danger / Icon | label, action |
| Input · Select · Checkbox · Switch | one each | validation, value |
| Badge · Status · Tag · Avatar | one each | semantic role + label |
| Notification · Modal · Tooltip · Dropdown | one each | type + content |
| Search · Filter | one each | field metadata, facets |
| Data Table | one | ResourceSchema, entity links |
| Selection Model | one | ordered ids |
| Detail Rail | one | DetailRailModel |
| Timeline · Notes · Contacts · Relations · Documents | one each | entity id + config |
| Entity Workspace shell | one | section config + slots |

---

## §3. Compositions (Level 3)

Built only from primitives:

- Entity Header
- Entity Summary strip
- Entity Navigation (section list)
- Context Rail (entity mode)
- Action Bar · Toolbar · Table Toolbar
- Document Viewer shell

**Deprecated term:** «Entity Card» → **Entity Workspace**.

---

## §4. Workspaces (Level 4)

| Workspace | Composition |
|-----------|-------------|
| **Collection** | AppShell + DataTable + Selection + Detail Rail |
| **Entity** | AppShell + Entity Workspace (5 zones) |
| **Application** | Entity Workspace patterns + Application Action Bar + stepper |
| **Process** | Process shell + queues + same primitives |

Modules (Recruitment, Sales, HR, Fleet, Finance) supply **config only**.

---

## §5. Semantic Color System

Unchanged — meaning → color, never decoration. See [`hostflow-ui-platform-v1.md`](hostflow-ui-platform-v1.md) §4 (merged reference) and ADR-011.

---

## §6. Data contracts

- **Collection:** `ResourceSchema`, `FieldDescriptor`, `entityLinks`, facets API
- **Detail Rail:** `DetailRailModel`
- **Selection:** `useSelectionModel`
- **Entity Workspace:** `EntityWorkspaceConfig` — see entity workspace spec

---

## §7. Canon documents (discussion unit)

Do not discuss «candidate UI» or «sales screen». Discuss **canons**:

| Canon | Question |
|-------|----------|
| Table | Layout, row behavior, selection |
| Detail Rail | Blocks, read-only, actions tiers |
| Entity Workspace | Zones, section order, Context Rail |
| Documents | Open, link, verify |
| Timeline | Event types, grouping |
| Search | Index, results, open target |
| Filter | Facets, ranges, saved views |
| Navigation | Sidebar, breadcrumbs, back, history |

Workspaces are assembled **after** canons exist.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | v2 — Interaction Rules layer; parent = Platform Canon |
| 2026-07-09 | v1 — Interaction Platform naming; Entity Workspace + Context Rail |
