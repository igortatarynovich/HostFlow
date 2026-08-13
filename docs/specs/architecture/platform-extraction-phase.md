# Platform Extraction Phase

**Status:** **NORMATIVE** (L2 operating — development-stage sequencing)  
**Date:** 2026-08-13  
**Trusted base:** `integration/release-product-a-b`  
**Parents:** [Platform Completion Roadmap](platform-completion-roadmap.md) · [ADR-038](ADR-038-platform-standardization-model.md) · [ADR-043](ADR-043-ui-component-composition-canon.md) · [ADR-044](ADR-044-list-workspace-data-presentation-canon.md) · [ADR-046](ADR-046-analytics-visualization-canon.md)  
**Execution:** [Core Platform Kit](../tasks/ui-platform-composition-epic.md)  
**Does not amend L0.** Does **not** add a fifteenth standardization area.

> Vocabulary Canon (ADR-037…047) is **closed**.  
> The next locked stage is **Platform Extraction**, not Product Development.

---

## Why this stage exists

HostFlow now has L1 canons that forbid local invention:

ObjectKind · State · DataType · Relationship · Action · Naming · UI Composition · ListWorkspace · Analytics.

That is enough to **reject** a new entity, rule, table, or chart dialect “on the spot.”

It is **not** enough for a module to **compose** a screen. ADR-044 says every operational list must use `ListWorkspace`, but the public runtime is not the product API yet. ADR-046 describes one analytics language, but dashboards still cannot import a closed kit as the only legal path. Entity pages remain one-off shells.

Without extraction, Phase B (Meta / Stage 3) has two bad options: write another private table, or stop. Both violate the canons just accepted.

**Rule:** turn accepted canons into reusable platform components **before** new product modules assemble screens.

---

## Development stages (honest model)

| Stage | Meaning | Status |
|-------|---------|--------|
| **Architecture** | L0 constitution, Catalog, capability contracts, gates | ✅ (A2 `PASS_WITH_CONSTRAINTS`) |
| **Vocabulary Canon** | Closed map of platform language (ADR-037…047) | ✅ closed 2026-08-13 |
| **Platform Extraction** | Extract repeating UI/runtime into one kit | ← **active** |
| **Product Development** | Phase B Meta → Stage 3 slice 3–4, then C–G | queued until kit gate |
| **Optimization** | migrate-on-touch, ratchets, remaining dashboards | after kit is the only legal import |

This does **not** rewrite Phases A–G on the horizon roadmap. It inserts a **mandatory extraction gate** between Vocabulary Canon and Phase B **code**.

```text
Architecture → Vocabulary Canon → Platform Extraction → Phase B → Phase C → Phase D → …
```

A2 (2026-08-03) opened Phase B. Vocabulary Canon then ran as an architecture track. This document **amends the queue**: Phase B product code waits on the Core Platform Kit gate.

---

## What “done” looks like

Not new product pages. A **public React kit** that modules configure:

| Already extracted (P0) | Must land this phase (kit gate) |
|------------------------|----------------------------------|
| Button, IconButton, Input, Textarea, Checkbox, Radio, Switch, SearchField, Tabs, StatusBadge, Chip, FormField, Modal, EmptyState, Pagination, SemanticSurface, PlatformIcon | **DataTable** (one API) · **ListWorkspace** (search / filters / sort / pagination / bulk / saved views / view switcher) · **EntityWorkspace** (minimal runtime) · **Analytics Kit** (KPI / trend / chart frame / story grid) |

After the gate, Vacancies, Candidates, Documents, Companies, SalesInquiry, and any later module **assemble** these. They do not reimplement tables, filters, cards, or charts.

---

## Four extraction streams (one sprint)

### 1. ListWorkspace runtime (blocker)

Canon: [ADR-044](ADR-044-list-workspace-data-presentation-canon.md).

Collapse `EntityListShell`, Candidates table behavior, `layout/DataTable`, and `platform/data-table` into **one** product-facing `ListWorkspace` + `DataTable`. Modules pass `ListDefinition`.

**Capability bar:** the API must express Candidates / TABLE_V1. **First page cutover:** Vacancies. Candidates wrap last.

Until this ships, **no new operational `<table>`** in product modules.

### 2. Analytics Kit (public composition)

Canon: [ADR-046](ADR-046-analytics-visualization-canon.md).

Families already exist under `hostflow-frontend/src/components/analytics/` (Recruitment efficiency = reference). This stream makes them the **only** legal analytics import and adds the missing composition pieces: chart frame, story / dashboard grid, filter bar as kit API.

**Not in this phase:** a free Widget Registry / BI constructor (forbidden by ADR-046). The closed `component_id` catalog **is** the registry. Remaining dashboards = migrate-on-touch after the kit gate. Named save / PDF consume Analytics View later.

### 3. EntityWorkspace — minimal runtime (not Phase D)

Fragments exist (`hostflow-frontend/src/platform/entity-workspace`). Promote a **minimal public API**: header, section tabs, summary, action bar, context rail / drawer, content slots (including Timeline as a slot — not a second activity product).

This is **not** [roadmap Phase D](platform-completion-roadmap.md) Universal Entity Workspace (compose Communication + Forms + Documents on one entity). It is the **chrome** product pages must reuse so Stage 3 does not invent a fifth card shell.

**ADR-045** (page templates: `EntityListPage`, `SettingsPage`, …) stays **deferred** until a second real template consumer exists. Do not write it to close a map cell.

### 4. Events runtime — not this sprint

Activity, Domain Events, Communication, Automation, Audit, and Notification remain distinct layers. They need a **runtime Event Contract** (ADR-019 **3A-1**), not another inventory ADR.

Ship Events runtime when Stage 3 / 3A is an actual consumer. Do **not** pre-build the bus.

---

## Out of this phase

- New vocabulary ADRs to fill ADR-038 `gap` cells (Events inventory-only, full CRM relationship graph)
- ADR-045 docs-only layouts
- Phase D Universal Entity Workspace
- Remaining efficiency-dashboard restyles (P4 migrate-on-touch)
- ADR-019 3A-2…3A-7, Action Registry (3A-3)
- DocumentType `integrity=split` alignment; Field/Forms `data_type` adoption (Forms C / Documents E)
- Unfreezing C2.4; L0 Catalog Notifications↔Communication without RFC (A2-F1)
- Marketing `surface.public` tokenisation as a prerequisite

---

## Gate (before Phase B code)

Phase B (Meta Intake Completeness → Stage 3 slice 3–4) may start **after**:

1. `ListWorkspace` + `DataTable` are the public API for **new** operational lists.
2. Analytics families import from `components/analytics` (no new private KPI/chart in product pages).
3. Minimal `EntityWorkspace` is the public API for **new** entity chrome (header / actions / rail).
4. Sequential queue Product Track is amended back to Meta / Stage 3.

Existing pages stay migrate-on-touch. The gate is **no new forks**, not a rewrite of Candidates.

---

## Enforcement

- New operational list without `ListWorkspace` = architecture violation (ADR-044).
- New analytics chart/KPI outside the kit = architecture violation (ADR-046).
- New entity header/action-bar/rail clone = architecture violation once the minimal workspace API exists.
- Docs-only ADR with no second consumer = rejected (same one-concern rule as product slices).

---

## Cross-references

- Horizon: [platform-completion-roadmap.md](platform-completion-roadmap.md)
- Near-term queue: [sales-to-comms-sequential-queue.md](../tasks/sales-to-comms-sequential-queue.md)
- Kit epic: [ui-platform-composition-epic.md](../tasks/ui-platform-composition-epic.md)
- Area map: [platform-standardization-model.md](../platform/platform-standardization-model.md)
- Maturity: [platform-capability-maturity.md](platform-capability-maturity.md)
