# Core Platform Kit (Platform Extraction)

**Status:** Active — **Platform Extraction** execution (not Product Development)  
**Phase:** [`../architecture/platform-extraction-phase.md`](../architecture/platform-extraction-phase.md)  
**Canon:** [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md) · [`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md) · [`ADR-046`](../architecture/ADR-046-analytics-visualization-canon.md) · L2 [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md)  
**Does not amend L0.** Visual tokens remain [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md).

This epic **extracts** repeating UI into one public kit. It is not a restyle, not Forms Builder, not Phase D Universal Entity Workspace, and not a new vocabulary ADR.

Former name: “UI Platform composition epic.” Same file; the work is now the **Core Platform Kit** gate before Phase B.

---

## P0 — Control layer (CRM first) ✅

Wrap current CSS where it exists. Product pages gain a React API; pixels stay.

- [x] Button  
- [x] IconButton  
- [x] Checkbox  
- [x] Radio  
- [x] Switch  
- [x] SearchField  
- [x] Tabs  
- [x] StatusBadge  
- [x] Chip  
- [x] PlatformIcon (only legal new icon import path — re-exported from the kit barrel)  
- [x] Modal  
- [x] EmptyState  
- [x] Pagination  
- [x] FormField  
- [x] SemanticSurface (`success` / `warning` / `danger` / `info` / `neutral` / `brand`)  
- [x] Input / Textarea (wrappers)

- [x] Baseline CI ratchets (hex, Tabler, intrinsic button, gradients, rounded) — **lower-only** (`npm run ui:kit:check`).  
- [x] Remove `.app-ui` descendant `border-radius: 0 !important` in favor of `--hf-radius-control` / `--hf-radius-surface`.

Public import: `hostflow-frontend/src/components/ui`. CSS className in product modules remains legal until migrate-on-touch.

Avatar, Dropdown, Toast, DateField remain wrap/gap — **not** kit-gate blockers.

---

## Kit gate — four streams (this phase)

Ship as **one platform sprint**. Do not wait for ADR-045. Do not start Meta / Stage 3 code until the gate in the [phase doc](../architecture/platform-extraction-phase.md) passes.

### 1. DataTable + ListWorkspace (blocker)

Canon: [`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md) · L2 [`../platform/ui-list-workspace-canon.md`](../platform/ui-list-workspace-canon.md). **Rule: done.** Runtime: **this stream.**

Product-facing API: one `ListWorkspace` hosting one `DataTable`. Modules pass `ListDefinition` (columns, cell kinds, filters, sort, actions, bulk, data source, saved views, permissions, empty, view switcher). They do not fork a table.

Zones of the same pattern (not a second ADR): Search + Filters + Sort + Pagination / infinite + Bulk + persisted views.

**Capability bar:** Candidates / TABLE_V1 (the API must express that list). **Page cutover:** Vacancies → Leads → Employees → Companies → Admin / remaining → Candidates in-place wrap last.

Collapse: `EntityListShell` + Candidates table behavior + `layout/DataTable` + `platform/data-table`. New operational `<table>` in `pages/` / `modules/` is forbidden once the public API exists.

### 2. Analytics Kit (public composition)

Canon: [`ADR-046`](../architecture/ADR-046-analytics-visualization-canon.md) · L2 [`../platform/ui-analytics-canon.md`](../platform/ui-analytics-canon.md).

Four layers: metrics semantics → visualization grammar → analytics composition → presentation & sharing.

**Reference (done):** Recruitment efficiency — story composition, URL Analytics View, copy-link, `present=1`.

**This stream:** kit is the only legal import for **new** analytics UI. Add missing composition: `ChartFrame`, story / dashboard grid (`AnalyticsSection` density). Closed `component_id` catalog = registry.

**Forbidden:** free Widget Registry / BI constructor; pie-as-default; module-local KPI tiles; a second reporting product.

**After gate:** Sales, HR, Finance, Fleet, Marketing, Overview — migrate-on-touch. Named save / PDF / schedule = same Analytics View later.

### 3. EntityWorkspace — minimal runtime

Fragments: `hostflow-frontend/src/platform/entity-workspace`. Promote a public API: header, section tabs, summary strip, action bar, context rail / drawer, content slots (Timeline is a **slot**).

**Not** roadmap Phase D (full platform composition on one entity). **Not** ADR-045 page templates (`EntityListPage`, `SettingsPage`, …).

New entity chrome after this stream must use the kit. Existing candidate/HR cards migrate-on-touch.

### 4. Events runtime — queued, not this epic

ADR-019 **3A-1** Event Contract when a real consumer (Stage 3 / automation) needs the bus. Not an inventory ADR. Not a kit-gate blocker.

---

## Explicitly deferred

- **ADR-045** layouts / page templates — wait for a second real template consumer.  
- Marketing `surface.public` tokenisation of `#0B0E14` / pipedesign radii — after CRM kit gate.  
- Remaining dashboard migrations as a dedicated restyle queue.  
- DocumentType alignment, Field/Forms `data_type` adoption.

---

## Success bar

A second module that needs a list, entity chrome, or chart **configures the kit**. It does not copy Tailwind from Candidates or Recruitment efficiency.

Kit gate → sequential queue returns Product Track to Meta Intake Completeness → Stage 3 slice 3–4.
