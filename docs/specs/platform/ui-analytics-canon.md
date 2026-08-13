# UI Analytics Canon — catalog

**Hierarchy:** L2 — analytics families, palettes, composition, Analytics View  
**Decision record:** [`ADR-046`](../architecture/ADR-046-analytics-visualization-canon.md)  
**Parent composition:** [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md) · [`ui-component-canon.md`](ui-component-canon.md)  
**Visual / a11y / UI tokens:** [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md)  
**Owner:** Frontend platform  
**Epic:** [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md) (Core Platform Kit / Analytics stream) · [`../architecture/platform-extraction-phase.md`](../architecture/platform-extraction-phase.md)  
**Runtime:** `hostflow-frontend/src/components/analytics/`  
**Canonical implementation:** Recruitment efficiency dashboard

---

## 1. Purpose

HostFlow analytics is an operational **and** presentable UI language on top of the design system. It must be useful every day and good enough to screenshot for a client, a manager, or a sale — without a redesign.

This file does **not** define Recruitment/Sales/HR metrics. Modules own queries. The platform owns grammar, composition, and sharing.

**Quality bar:** every key view is clear for daily decisions and visually fit for a presentation.

---

## 2. Four layers

| Layer | In this file |
|-------|----------------|
| Metrics semantics | Module-owned; only meaning classes (rejected → danger) are listed |
| Visualization grammar | §4 meaning→family, §5 color spaces |
| Analytics composition | §6 story hierarchy, §7 Insight → Action, density |
| Presentation & sharing | §8 Analytics View, screenshot-ready chrome, presentation mode |

---

## 3. Platform law

> Identical analytical meaning MUST have identical visual representation in every HostFlow module.

| Allowed | Forbidden |
|---------|-----------|
| `<KpiCard tone="danger" href={…} />` | page-local `function Kpi` with `accent="#e11d48"` |
| `<FunnelChart>` for conversion | pie / stacked area / custom steps for the same conversion |
| `<BreakdownChart>` for mix / distribution | a new pie because “it looks like a dashboard” |
| `resolveSeriesFill({ space: 'semantic', tone: 'danger' })` for rejected | `#e11d48` in the page because Recruitment used it once |
| `resolveSeriesFill({ space: 'categorical', index })` for sources | `orange` then `violet` then `cyan` as the next unused hue |
| One hero number + supporting KPIs | Twelve identical KPI tiles |
| URL Analytics View + `present=1` | A second Reporting app |

---

## 4. Meaning → family

The developer names the **meaning**, not the Recharts component.

| Meaning | Family | Chart / control | Do not use |
|---------|--------|-----------------|------------|
| Headline number | KPI | `KpiCard` / `AnalyticsStoryHero` | custom tile, gradient hero, KPI mosaic |
| Change over time | Trends | `TrendChart` (line / area) | bar-as-trend, pie-over-time |
| Mix / structure by category | Composition | `BreakdownChart` bar / stacked bar | pie / donut |
| Conversion through ordered steps | Funnel | `FunnelChart` + step conversion | unordered bars, pie |
| Unordered categorical counts | Distribution | `BreakdownChart` | pie |
| Success / warning / danger / idle | Status | semantic fill on KPI / bar / badge | categorical hue for status |
| Plan, capacity, completion | Progress | `TargetProgress` | ad-hoc width `%` bars with random fill |
| Tabular slice + totals | Tables | `AnalyticsTable` | hand-written `<table>` in new analytics |
| Slice by dimension | Breakdown | dimension control + `BreakdownChart` | a second page-specific chart type |
| Current vs previous / target / benchmark | Comparison | delta on `KpiCard` or grouped series | a third palette “for the old period” |
| Date + dimensions + saved view | Filters | `AnalyticsFilterBar` | per-dashboard filter card clones |
| Nothing / not enough / not tracking | Empty | `AnalyticsEmptyState` | blank `ResponsiveContainer` |
| Open the underlying entities | Drill-down | href / click (working mode) | metric with no way through |
| What it means + what to do | Insight | `InsightCard` | warning banner without action |
| Screenshot / share chrome | Report | `AnalyticsReportHeader` | untitled chart dump |

---

## 5. Color spaces

Three spaces. Do not mix them in one series without an explicit rule (e.g. stacked composition where each stack is a status).

### 5.1 UI semantic (status)

Same meaning classes as StatusBadge / SemanticSurface:

`success` · `warning` · `danger` · `info` · `neutral` · `brand` (chrome only)

| Meaning examples | Tone |
|------------------|------|
| rejected, lost, overdue, expired, wrong number, handoff rejected | `danger` |
| declined (candidate withdrawal), no-answer, waiting, approaching limit | `warning` |
| hired / employed / reached / accepted / verified / complete | `success` |
| in progress, attempted, submitted, requested | `info` |
| new, missing, unknown, idle | `neutral` |

If the same meaning appears in Recruitment and Sales, it keeps the same tone. Object kind does not own a color.

### 5.2 Data categorical (`data.01` … `data.12`)

Independent categories **without** status meaning: source, recruiter, vacancy, client, campaign.

Assign by stable index in the current slice (sort then index), not by hashing an entity id to a forever-color.

Never allocate `data.13` on a page. Group remainder as “Other” (`data.12` or `neutral`).

### 5.3 Sequential / diverging

- Sequential: weak → strong intensity (volume, density).
- Diverging: negative ← neutral → positive (delta vs target / previous).

### 5.4 Resolution order

1. If the datum has a status meaning → semantic tone.
2. Else if the series is a magnitude / delta → sequential or diverging.
3. Else → categorical `data.01`…`data.12`.

Runtime: `resolveSeriesFill` in `hostflow-frontend/src/components/analytics/palette.ts`.

---

## 6. Composition — story first

Not a BI constructor. One strong composition per screen:

1. **Result** — `AnalyticsStoryHero` (one large number, period, units).
2. **Change / judgment** — delta on the hero or `InsightCard`.
3. **Cause** — `FunnelChart` and primary `BreakdownChart` (`density=story`).
4. **Where** — bottlenecks (`density=operational`).
5. **What exactly** — `AnalyticsTable` + drill-down (working mode only).

**Density:** `story` = air, large type; `operational` = compact breakdowns. Do not apply story density to every card.

Recruitment reference: hero volume → close-rate insight → contact funnel → outcome/stage → reasons → documents.

Living analytics: opacity/layout transition on filter change; Recharts hover details; no decorative count-up.

---

## 7. Insight → Action

Working mode: `InsightCard` and KPI/chart points carry a path to the source list.

Presentation mode: actions hide; the sentence and numbers stay.

Href targets are existing list routes (`?stages=rejected`), not a parallel BI dump.

---

## 8. Analytics View (shareability)

Canonical query keys (preserve `module` on the Overview hub):

| Key | Meaning |
|-----|---------|
| `range` | preset (`7d`, `30d`, `all`, …) |
| `from` / `to` | ISO dates |
| `company_id` / `vacancy_id` / `recruiter_id` | dimensions |
| `present` | `1` = presentation mode |

Copy-link shares this URL. Named save, read-only token, PDF, schedule **consume the same shape** later — they do not invent a reporting module.

Screenshot-ready checklist (every key view):

- Report title
- Company / HostFlow mark
- Period + units
- Legend or labeled axes
- No raw ids, debug, or overlapping controls in the frame

Presentation mode hides: sidebar, topbar, module tabs, filter bar, refresh, Insight actions, load errors. Keeps: header, story, charts, tables. Report controls (exit) are hover/focus-only and `print:hidden`. Escape returns to working mode. Shell chrome hides only on `/app/overview` so `present=1` cannot strip unrelated pages.

---

## 9. Catalog (component IDs)

`status`: `exists` (kit usable) · `wrap` (legacy screen still private) · `gap` (family defined, no runtime yet).

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `KpiCard` | exists | `KpiCard.tsx` | `size=hero` for the story number |
| `AnalyticsStoryHero` | exists | `AnalyticsStoryHero.tsx` | Result block; not a mosaic |
| `TrendChart` | exists | `TrendChart.tsx` | Line / area |
| `FunnelChart` | exists | `FunnelChart.tsx` | Ordered conversion |
| `BreakdownChart` | exists | `BreakdownChart.tsx` | Composition + distribution + breakdown |
| `TargetProgress` | exists | `TargetProgress.tsx` | Plan / capacity / completion |
| `AnalyticsTable` | exists | `AnalyticsTable.tsx` | Totals; not ADR-044 DataTable |
| `InsightCard` | exists | `InsightCard.tsx` | Actions hidden when `present` |
| `AnalyticsFilterBar` | exists | `AnalyticsFilterBar.tsx` | Hidden in presentation mode |
| `AnalyticsEmptyState` | exists | `AnalyticsEmptyState.tsx` | three empty kinds |
| `AnalyticsSection` | exists | `AnalyticsSection.tsx` | `density=story \| operational` |
| `AnalyticsReportHeader` | exists | `AnalyticsReportHeader.tsx` | Screenshot chrome + copy link + present |

ChartHost / Recharts stay **implementation** inside these IDs.

---

## 10. Inventory — existing efficiency surfaces

Do not restyle. Map to families, then replace.

| Surface | Today | Canonical blocks |
|---------|-------|------------------|
| `RecruitmentEfficiencyDashboard` | **reference** | ReportHeader, StoryHero, FilterBar, InsightCard, FunnelChart, BreakdownChart, AnalyticsTable, TargetProgress, URL view, `present=1` |
| `SalesEfficiencyDashboard` | local `Kpi`, pie | same kit + URL view on touch |
| `HrEfficiencyDashboard` | local `Kpi` | same |
| `FinanceEfficiencyDashboard` | local `Kpi` | same |
| `FleetEfficiencyDashboard` | local `Kpi` | same |
| `MarketingEfficiencyPanel` | private panel | same |
| Overview / widgets | tile soup | StoryHero + KpiCard; no new palette |
| `AnalyticsLeadConversionFunnelPage` | dedicated funnel | `FunnelChart` + ReportHeader |

---

## 11. Empty states

| kind | When |
|------|------|
| `no_data` | Slice is valid; counts are zero |
| `insufficient_data` | Too few points for a trend / conversion |
| `tracking_not_started` | Source instrumentation missing (e.g. no contact attempts logged) |

---

## 12. History

- 2026-08-13: Presentation & sharing layer (Analytics View URL, report header, presentation mode, story hero).
- 2026-08-13: Initial catalog under ADR-046. Recruitment efficiency is the canonical implementation. Other dashboards migrate-on-touch.
