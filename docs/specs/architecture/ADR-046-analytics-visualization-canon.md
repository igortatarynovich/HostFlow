# ADR-046: Analytics, Visualization & Reporting Canon

**Status:** Accepted  
**Date:** 2026-08-13  
**Layer of change:** Experience (Design & Interaction) | Analytics UI language + presentation/shareability  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-043`](ADR-043-ui-component-composition-canon.md) · [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md) · [`ADR-038`](ADR-038-platform-standardization-model.md) · L2 [`../platform/ui-analytics-canon.md`](../platform/ui-analytics-canon.md) · epic [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md)

**Amends (does not supersede):** ADR-043 — composition kit remains the public API for controls. This ADR adds a **sibling analytics language** (grammar + composition + reporting) on top of that kit. ADR-011 Foundation semantic colors remain UI status colors; they are **not** the chart category palette.

**L0 checklist:** No new L0 P-rule; no new capability Passport (UI Platform Standard #11). Applies P-01 / P-03 / INV-05 / INV-07 and AGENTS Rule 4 to **analytical patterns**. Does not rewrite Passport/Manifest shape. Does **not** create a second reporting product.

---

## Context

HostFlow already forbids local semantic colors (ADR-038 area 13, ADR-043). That rule was still being read as “pick nicer dashboard hex.” Recruitment, Sales, HR, Finance, and Marketing efficiency screens each invent KPI cards, pie charts, funnel bars, and one-off palettes (`#f97316`, `#8b5cf6`, `#06b6d4`). The same meaning — conversion, plan vs actual, change over time, categorical mix — looks different in every module.

Analytics is not a color appendix and not an admin widget wall. It is a **visual language of HostFlow data**: operationally useful every day, visually premium enough to screenshot for a client or a board, and architected so sharing does not spawn a second reporting stack.

ADR-044 (ListWorkspace / DataTable — **rule done**, runtime extract = epic P1–P2) and ADR-045 (Layouts) remain the next *operational list* **runtime** / template canons. This ADR is the *analytical + reporting* canon. It may ship in parallel: dashboards do not wait for DataTable extraction.

---

## Decision

### 0. Quality bar (non-negotiable)

> Every key HostFlow analytics view MUST be clear enough for daily decisions **and** visually good enough to use, without redesign, in a presentation or in front of a prospective client.

The user should *want* to screenshot the dashboard and send it. If a view looks like a generic admin kit — twelve identical KPI tiles, a rainbow of charts, no story — it has failed this ADR even if the numbers are correct.

### 1. Four layers of one canon

| Layer | Owns | Does not own |
|-------|------|----------------|
| **Metrics semantics** | What the indicator means; how it is counted (module-owned formula) | Chart type, chrome |
| **Visualization grammar** | Which family shows which meaning; three color spaces | Module queries |
| **Analytics composition** | How blocks tell a story on one screen | Per-widget decoration |
| **Presentation & sharing** | Screenshot-ready chrome, saved Analytics View, presentation mode, share/export path | A parallel BI/reporting product |

Product modules own **metrics and queries**. The platform owns the other three layers.

### 2. One analytics language across modules

> Identical analytical meaning MUST have identical visual representation in every HostFlow module.

A product page **must not** choose a chart type, KPI chrome, or palette for a meaning that already has a canonical family. Conversion is always a funnel. Plan / target is always progress. Change over time is always a trend. Structure by category is always a bar / stacked bar. Status meaning is always the UI semantic scale.

Target: a user opening Recruitment, HR, Sales, Finance, or Marketing already knows how to read the screen.

### 3. Meaning selects the family — not the developer

Closed family set (stable `component_id` in L2):

| Family | Canon | Representation |
|--------|-------|----------------|
| KPI | `KpiCard` / `AnalyticsStoryHero` | value, optional delta, period comparison, optional target; one hero number per story |
| Trends | `TrendChart` | line / area |
| Composition | `BreakdownChart` | bar / stacked bar |
| Funnel | `FunnelChart` | one funnel + conversion between steps |
| Distribution | `BreakdownChart` | categorical distribution |
| Status | semantic fill | success / warning / danger / info / neutral |
| Progress | `TargetProgress` | progress to target / capacity / completion |
| Tables | `AnalyticsTable` | analytical table + totals + deltas |
| Breakdown | `BreakdownChart` + dimension control | recruiter / vacancy / client / source / period |
| Comparison | grouped / overlay in `TrendChart` or `BreakdownChart` | current vs previous / target / benchmark |
| Filters | `AnalyticsFilterBar` | date range + dimensions + saved view |
| Empty states | `AnalyticsEmptyState` | no data / insufficient data / tracking not started |
| Drill-down | href / click → entity list | chart or KPI → source entities |
| Insight | `InsightCard` | Insight → Action |
| Report chrome | `AnalyticsReportHeader` | title, company, period, units — screenshot-ready |
| Presentation | shell `present=1` | hide nav/controls; keep the story |

**Prohibited as a default:** pie / donut for composition or status mix; a new chart type for a meaning that already has a family; module-local KPI tiles; a wall of 12 equal KPI cards; a rainbow of unrelated hues.

Pie charts in existing dashboards are inventory debt. The Recruitment reference implementation replaces them with the canonical family for that meaning.

### 4. Three independent color spaces

| Space | Tokens | Use |
|-------|--------|-----|
| **UI semantic** | `success` / `warning` / `danger` / `info` / `neutral` (+ `brand` for chrome) | Interface status. Same map as StatusBadge / SemanticSurface. |
| **Data categorical** | `data.01` … `data.12` | Independent categories with **no** status meaning (sources, recruiters, clients). |
| **Data sequential / diverging** | intensity scale; `negative ← neutral → positive` | Magnitude and deviation, not identity. |

Rules:

- A dashboard MUST NOT invent a 13th hue because it needed another series.
- A business meaning MUST NOT receive a random durable color. If `rejected` is `danger` in Recruitment, it stays `danger` wherever that meaning appears (Sales lost, HR handoff rejected, document rejected).
- Categorical tokens are **not** Foundation UI colors. They live in the analytics kit.
- Semantic meaning always wins over categorical index.

### 5. Five presentation principles

#### Screenshot-ready by default

KPI, funnel, trend, recruiter/client performance MUST look finished without extra prep: labels, period, units, a readable legend, no visual junk (debug chips, raw ids, overlapping ticks, orphan toolbars).

#### Living analytics

Not a static grid of identical cards. Hierarchy of scale: one large headline number, supporting KPIs, then denser operational breakdowns. Soft transitions on period/filter change. Hover/tap details. Animated value changes only when they aid perception. No decoration-for-decoration motion.

#### Story first

The first screen tells: **result → change → cause → problem/opportunity**. Not a BI constructor of twenty equal widgets.

1. What is happening? (hero number)
2. Is it good or bad? (delta / target / insight)
3. Why? (funnel + primary breakdown)
4. Where? (anomalies, bottlenecks)
5. What sits behind it? (drill-down — hidden in presentation mode)

#### Shareable views

The user can keep a concrete analytics state — period, filters, breakdown, selected client/vacancy/recruiter — and share *that* view, not “the dashboard in general.”

#### Presentation mode

The same screen can drop from a working UI into a clean presentation: no sidebar, no extra buttons, no technical controls; HostFlow / company, period, report title, and a composed layout.

### 6. Analytics View / Report View (sharing architecture)

Sharing is **not** “a Screenshot button.” The platform object is an **Analytics View**:

| Field | Role |
|-------|------|
| `view_kind` | module analytics surface (`recruitment.efficiency`, …) |
| `title` | report name |
| `period` | preset and/or `from`/`to` |
| `dimensions` | client, vacancy, recruiter, source, … |
| `breakdown` | active slice |
| `layout` | story composition id (not a free widget grid) |
| `presentation` | working vs presentation mode |
| `permissions` | who may open (follow-on; tenant RBAC first) |

**Now:** the view is encoded in the URL (query) so copy-link works.  
**Next on the same model (not a new product):** named saved view, read-only link, PDF/export, scheduled report, client-facing report.

Do **not** build a second reporting system. Export and schedule consume Analytics View.

### 7. Recognizable visual language (not an admin kit)

HostFlow analytics is identified by:

- large typography on the **one** story number;
- air in strategic blocks (`density=story`);
- denser operational breakdowns (`density=operational`);
- a limited palette (the three spaces above);
- one strong composition per screen — not twelve equal cards and a rainbow of charts.

### 8. Insight → Action (working mode)

A metric without a next step is a BI showcase. Required shape in working mode:

`Conversion 4.2% ↓ 1.3 pp vs previous period` plus an action (view rejected, break down by source, …).

In **presentation mode**, actions and technical controls hide; the story, period, and legend remain.

### 9. Existing efficiency dashboards are inventory, not a restyle queue

Do **not** recolor `RecruitmentEfficiencyPanel` and siblings in place. Decompose onto canonical blocks, then assemble.

**Canonical implementation:** Recruitment efficiency is rebuilt on the kit **and** carries report chrome, URL Analytics View, copy-link, and presentation mode. Other efficiency screens migrate on touch; they MUST NOT add a new private chart, palette, or share mechanism.

### 10. Runtime — not docs-only

This ADR ships:

- L2 catalog [`../platform/ui-analytics-canon.md`](../platform/ui-analytics-canon.md)
- React kit `hostflow-frontend/src/components/analytics/`
- Reference: Recruitment efficiency — grammar + story composition + URL view + presentation mode

Follow-on (epic P4): remaining dashboards; persisted Analytics View; PDF/export/schedule on the same model.

### 11. Enforcement

- New analytics UI MUST import kit families; local `PieChart` / hex series / private `Kpi` helpers are prohibited in **new** code.
- New analytics screens MUST be screenshot-ready (header with period + title) and MUST encode view state in the URL.
- Recolor-only PRs and “twelve equal KPI tiles” layouts are rejected.
- Existing screens: migrate-on-touch.

---

## Out of scope (explicit)

- ADR-044 DataTable / list contract
- ADR-045 page templates
- Shipping Sales / HR / Finance / Marketing migrations in this PR
- A new L0 P-rule, analytics Passport, or standalone Reporting module
- PDF / scheduled email / public read-only token (same Analytics View later)
- Pixel restyle of Foundation / marketing

---

## Explicit next

1. [Platform Extraction](platform-extraction-phase.md): kit is the only legal import for **new** analytics; story/dashboard grid as composition (not a Widget Registry).
2. Remaining efficiency dashboards migrate-on-touch after the kit gate (not a restyle queue).
3. Persist Analytics View (named save) later — **not** a new BI app.
4. **ADR-045** only when a second template consumer exists. ListWorkspace runtime is the same extraction sprint ([`ADR-044`](ADR-044-list-workspace-data-presentation-canon.md)).

---

## Architecture Review Checklist (L0)

- [x] P-01…P-05 respected — composes UI Platform capability; no new Passport
- [x] INV-05 — Recharts / CSS inside the kit is not the public API
- [x] INV-07 / two-module rule — second dashboard promotes the pattern; it does not copy Recruitment Tailwind
- [x] ADR-011 / ADR-043 not superseded; analytics + reporting language added
- [x] L0 freeze untouched; no second reporting capability invented
- [x] Area 13 visualization + presentation/shareability closed as a canon + Recruitment reference

---

## Consequences

- Positive: HostFlow standardizes how the business is *read* and *shown*; analytics becomes part of the product and of the sale; share/export can grow on one view model.
- Negative: Recruitment layout changes (hero story, pies gone, presentation mode); other dashboards remain mixed until migrate-on-touch; named save / PDF still follow.
- Follow-on: Platform Extraction kit gate; remaining dashboards migrate-on-touch; persisted Analytics View later. ADR-045 deferred.

---

## Alternatives considered

1. **Keep visualization as “dashboard colors” under ADR-043 §5** — rejected; colors without grammar recreate five dialects.
2. **Docs-only ADR, migrate later** — rejected; reference implementation is mandatory.
3. **Allow each module to pick pie vs bar for the same meaning** — rejected.
4. **Screenshot button only, no view model** — rejected; that cannot grow into share / PDF / schedule.
5. **A separate Reporting / BI module** — rejected; second system. Analytics View is the report.
6. **Wait for ADR-044 / ADR-045** — rejected; dashboards do not need DataTable extraction to stop looking like an admin kit.

---

## Cross-references (updated in same change set)

- [`../platform/ui-analytics-canon.md`](../platform/ui-analytics-canon.md) — L2 families, palettes, Analytics View, inventory
- [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md) — Analytics layer IDs
- [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md) — P4
- [`ADR-043-ui-component-composition-canon.md`](ADR-043-ui-component-composition-canon.md)
- [`ADR-038-platform-standardization-model.md`](ADR-038-platform-standardization-model.md) · [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md)
- [`architecture-guide.md`](architecture-guide.md) · [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) · [`platform-architecture-principles.md`](platform-architecture-principles.md)
- [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md)
