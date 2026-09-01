# ACQUISITION_MARKETING_IA_V1

**Status:** Locked (presentation contract)  
**Layer:** L2 frontend canon  
**Owner:** Acquisition / Growth  
**Implementation:** **unscheduled** — this file is the product IA contract; it does **not** start a Product slice and does **not** amend [`sales-to-comms-sequential-queue.md`](../tasks/sales-to-comms-sequential-queue.md). Unlock ≠ schedule.  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) · [acquisition/module-scope.md](../../acquisition/module-scope.md) · [HOSTFLOW_UX_NORTH_STAR](HOSTFLOW_UX_NORTH_STAR.md) · [OPERATIONAL_WORKSPACE_MODEL](REF-UI-000-OPERATIONAL_WORKSPACE_MODEL.md) · [ADR-011](../architecture/ADR-011-hostflow-ui-platform-standard.md)

---

## Question answered

> How must `/app/marketing` and `/app/marketing/:campaignId` disclose Acquisition so an inexperienced operator understands **what is happening** and **what to do next**, without replacing the domain model with a Marketing product — and without pretending HostFlow has live Meta Ads Insights?

This contract defines **zones, order, required data, hide-when-empty, two data planes (live HostFlow vs imported ad facts), and where today’s Flight / Source / Ad-binding UI goes**. It does **not** define pixels, new primitives, or new domain entities.

---

## Product framing

`/app/marketing` is a **Recruitment acquisition control center** (Acquisition operator SPA).

It is **not** a Meta Ads dashboard inside HostFlow.

| Layer | Answers |
|-------|---------|
| Meta (and other channels) | Attracts demand: campaigns, forms, ads, inbound leads |
| HostFlow | **What did we get for the advertising money?** — applications, processing, destination Results, qualification, Outcomes |

Live Meta Ads Insights is **absent today**. That is not a blocker for this IA. Manual spend import is a **normal product writer** into the existing spend SoT. When Insights API exists, it becomes another writer; the UI model does not change — the daily «Загрузить данные» affordance can recede.

---

## Original problem this contract must permanently remove

The operator SPA currently paints the **backend graph** on first paint:

```text
Portfolio KPI → Campaign table → Campaign → Flight → Source → Ad ID → routing → cohorts
```

and paints **imported / incomplete ad economics** as if they were live HostFlow truth (four-decimal Spend/CPL, empty CAC/Value/ROI).

The operator thinks in **operations**:

```text
I launched ads → is it working? → how many applications? → have we handled them?
→ who became a candidate? → is there a problem? → what should I do?
→ (then) what did ads cost, as of the last import?
```

First paint must answer the HostFlow-known questions. Ad economics are a **second, dated layer**.

---

## Architecture review (L0 — ten questions)

This is **presentation IA** over an existing capability. It is not a new capability, not a sixth ADR-004 module, and not an L0 change.

| # | Answer |
|---|--------|
| 1 Owner | **Acquisition / Growth** ([ownership card](../../modules/acquisition/module_ownership_card.md)). Destination modules own Results. |
| 2 Existing capability? | Yes — Campaigns / Flight Runtime / Stage 5 signals / Stage 6 analytics / spend entries. No second “Marketing analytics” capability. No live Ads Insights capability. |
| 3 Adapter | None new for live ads. Spend **import** (when implemented) is a **writer** into existing `CampaignFlightSpendEntry` — same SoT Stage 3D already uses. Future Meta Insights API is the same writer class, different `data_source`. Destination objects only via published destination contracts. |
| 4 Boundary | **Forbidden:** `marketing.*` host (ADR-024 anti-scope). **Forbidden:** Campaign owning Candidate / Inquiry. **Forbidden:** third domain synonym for Flight. **Forbidden:** a second spend/KPI ledger (Stage 6 hard ban). **Forbidden:** treating Meta export «leads» as HostFlow submissions. |
| 5 Settings | No new settings tree. Source / Meta / mapping / routing stay on Campaign **Settings**. Import CTA lives on the advertising layer, not a new settings product. |
| 6 SoT | **Two planes** (below). KPI / attribution remain Acquisition read models. Spend SoT remains `acq_flight_spend_entries`. Commercial value remains Sales-declared (`declared_v1`); UI must not invent Value / ROI. Lead remains **intake transport** (ADR-021). |
| 7 Events | None new on GET. Attention cards **read** Stage 5 + Live Intake. Import writes spend entries (upsert per **economic identity**, not per `data_source`) — not Timeline-as-dashboard. |
| 8 Requires | Stage 4 runtime, Live Intake Monitor, Stage 5 optimization read, Stage 6 portfolio / compare / cohorts, existing `record_flight_spend`. Import UI/API is **part of this contract** but **unscheduled** with the rest of the UI. |
| 9 License | No new license class. |
| 10 Public contract | Additive UI. Additive spend-entry fields when import ships (economic identity + provenance — grain section below). No breaking rename of Flight / Endpoint / Source in HTTP. |

**INV-16:** operator convenience must not rewrite ownership, intake spine, or Catalog. Hiding the word “Flight” on first paint is allowed ([ADR-024 §1.2](../architecture/ADR-024-acquisition-campaigns-intake-routing.md)); deleting Flight from the model is not.

**P-01:** Acquisition still talks to Forms / Integrations / Recruitment / Sales only through existing adapters and destination contracts.

---

## Two data planes (mandatory split)

HostFlow does **not** currently receive live spend / CPL from Meta. First paint must never look like a live Ads Insights integration.

| Plane | What | Freshness | Period 7/30/90 |
|-------|------|-----------|----------------|
| **A — HostFlow live** | Campaign / Flight identity, Source/form bindings, inbound submissions (leads), operator processing, destination Result, qualification, Outcomes | As of request time | **Applies fully** — counts are windowed by submission / result / outcome timestamps |
| **B — Ad economics (imported)** | Spend, provider-reported leads, impressions/reach if present, derived CPL / cost-per-result | **As of last successful import** (and each snapshot’s coverage day) | Filters **imported snapshots whose coverage dates intersect the window**. Does **not** make Spend “live for 30 days” |

```text
Plane A (automatic):  Campaign → ads/forms → Lead (transport) → answers → Result / Outcome in HostFlow
Plane B (imported):   Meta export or future API → snapshot → spend / provider metrics → derived ad ratios
```

**Forbidden:** one KPI strip where Spend, applications, CPL, and candidates appear to share one freshness.

Allowed situation summary:

> 38 заявок за 30 дней. Рекламные расходы обновлены по 29 августа.

Forbidden situation summary:

> Реклама работает. 38 заявок за 30 дней, средняя цена $2.57.

when `$2.57` is computed from spend last imported on 29 August and submissions still arriving on 1 September — unless the copy **names** that spend freshness.

### Plane A metrics (authoritative for operations)

Defined only from Live Intake + destination Results + qualification + Outcomes. Zeros are real.

### Plane B metrics (authoritative for cost)

Defined only from `CampaignFlightSpendEntry` (Stage 3D SoT). Empty import → **no cost numbers**, not `$0.0000` pretending to be live.

**HostFlow CPL (canonical — the only formula):** see [Covered-dates cost ratios](#covered-dates-cost-ratios-canonical). Any other spend÷leads wording in this file is superseded by that section.

**CPL (Meta / provider), Analytics only:** spend / **provider-reported** leads from the **same** snapshots **and the same covered-date set C**. Label as provider figure. Never silently substitute Meta leads for HostFlow submissions.

### Spend writer contract (implementation later, locked semantics)

Stage 6 hard ban stands: **no new metrics ledger**; ad-provider sync is **not** a second SoT ([acquisition-stage-6-analytics.md](../tasks/acquisition-stage-6-analytics.md)). Writers add **fields** on `acq_flight_spend_entries`, not a parallel table.

#### Grain

A spend row is one economic fact at one **provider dimension** for one **coverage date**. `data_source` is **provenance**, not identity.

| Field | Role |
|-------|------|
| `provider` | Closed literal, not a new dictionary: `meta` \| `manual` |
| `provider_account_id` | Provider ad account (Meta account id). For `manual` with no account: HostFlow `own_company_id` |
| `dimension_type` | Closed literal: `flight_aggregate` \| `ad_set` \| `ad` |
| `dimension_id` | Provider Campaign / Ad Set / Ad id. For `manual` + `flight_aggregate`: HostFlow `flight_id` |
| `coverage_date` | The advertising **day** the amount describes (UTC date), not `created_at` |
| `data_source` | Provenance only: `manual` \| `meta_import` \| `meta_api` |
| `flight_id` / `campaign_id` | HostFlow attachment after match (`FlightAdBinding` / Flight). Required once matched; unmatched import rows stay in the review list and **do not** enter SoT |

**Economic identity (uniqueness of the current fact):**

```text
tenant_id + provider + provider_account_id + dimension_type + dimension_id + coverage_date
```

**Not** `(flight, coverage_date, data_source)`. That key cannot store five ads on one day and would double-count when CSV and API both exist.

#### Supersession

Re-receiving the same economic identity **updates** the fact; it must not insert a second amount.

| Incoming vs stored | Rule |
|--------------------|------|
| Same identity, same `data_source` | Last write wins (re-import of that day) |
| Same identity, different `data_source` | Precedence: `meta_api` > `meta_import` > `manual`. Higher or equal precedence replaces the amount and provenance. Lower precedence is **ignored** (no second row, no €200) |
| Different `coverage_date` | Insert; never delete other days |
| Different `dimension_id` / `dimension_type` | Different facts (five ads = five rows) |

CSV on 1 Sep for day D then Insights API for day D → **one** €100 row, `data_source=meta_api`. Not €200.

#### Roll-up (no intra-day double count)

For a Flight on coverage date D, Spend used in Flight/Campaign totals is **exactly one grain**:

1. If any `ad` rows exist for that flight’s bindings on D → **sum those `ad` rows only**
2. Else if any `ad_set` rows exist → sum those
3. Else use `flight_aggregate`

**Never** add `flight_aggregate` + `ad` (or ad_set) for the same D. Ad-row Spend is the `ad` dimension row for that `FlightAdBinding` only.

#### Other writer rules

| Rule | Value |
|------|--------|
| SoT | Existing `acq_flight_spend_entries` / `record_flight_spend` (extend, do not fork) |
| Manual import | First-class **writer**, not a temporary hack |
| Future Insights API | Same writer, different provenance |
| Match | Meta Campaign / Ad Set / Ad ID → Campaign / `FlightAdBinding` / Flight. Unmatched → operator review, not silent merge |
| File | CSV/XLSX from Meta Ads Manager. Native `<input type="file">` + `.btn-secondary`. **Not** the lead `csv_import` pipeline |
| Security | Implementation PR **must** extend the Stage 6 analytics threat model. No new producer events on parse-only preview |

UI copy: «Рекламные данные» / «Загрузить свежие данные», not «интеграция Insights».

### Covered-dates cost ratios (canonical)

**The only HostFlow cost formula** in this contract. It applies to HostFlow CPL, cost per Result, cost per qualified, cost per hire, campaign vs portfolio CPL, High-price / Best-result, and ad-row HostFlow CPL (when defined).

Let **C** = the set of `coverage_date` values that have a Plane B fact at the **roll-up grain in force** for the subject (Flight, campaign, or `ad` row) **and** that lie inside the selected period 7/30/90.

**C is a set (union of days), not `[min(C), max(C)]`.** A hole (imported 28 Aug and 30 Aug, not 29 Aug) must **not** pull 29 Aug submissions into the denominator.

```text
numerator   = sum(spend facts at the roll-up grain for dates in C)
denominator = Plane A events whose event-date ∈ C
HostFlow ratio = numerator / denominator   when C ≠ ∅ and denominator > 0
```

| Ratio | Denominator event |
|-------|-------------------|
| HostFlow CPL | Submissions with submission date ∈ C |
| Cost per Result | Result-created with created date ∈ C |
| Cost per qualified | Qualifications with qualified date ∈ C |
| Cost per hire | Completed hiring Outcomes with completed date ∈ C |

**Forbidden:** `sum(spend in period window) / all Plane-A submissions in the period window` when C is a proper subset of the period (e.g. spend through 29 Aug, leads on 30 Aug–1 Sep). That **improves** CPL without cheaper ads.

If C is empty → ratio **undefined** → no number (gating). Always show freshness of C (max coverage date and last write time).

Portfolio CPL uses the same C-construction **per campaign**, then compares those ratios. Do not compare a campaign’s coverage-aligned CPL to a portfolio CPL built from a different day-construction rule. High-price requires each side’s denominator ≥ 5 **on that side’s C**, not on the full period.

**Ad-row HostFlow CPL:** only if Plane A submissions can be attributed to that Ad ID (existing binding/routing). If HostFlow cannot attribute submissions to the ad → **omit** HostFlow CPL on the ad row (Spend from the `ad` fact may still show). Do not divide Flight submissions by one ad’s spend.

---

## Non-goals

- New Marketing product module or `marketing.*` host.
- Meta Ads dashboard clone; live Ads Insights as a prerequisite for this IA.
- New UI primitives, tokens, status semantics, chip behaviors, table standard, or file-drop component.
- New local dictionaries (statuses, channel lists, KPI names, spend-source catalog).
- New metrics ledger, second optimization engine, or auto-pause from this IA.
- Inventing funnel steps HostFlow does not store (e.g. “viewed”).
- Showing CAC proxy / Value / ROI on first paint — and **not** as the primary recruitment cost story even on Analytics while `sales_order_v2` is backlog.
- Reopening Acquisition UI cutover C-1…C-7, Forms P3 Publish, Mapping Authority, or R6 Lead cutover.
- Scheduling implementation on the Product Track.

---

## Design-system bind (mandatory)

Implementation **must** reuse locked surfaces. Local “marketing design” is a defect.

| Need | Use |
|------|-----|
| Page chrome | `PageHeader` ([page_header.md](page_header.md)) + `PageShell` / `PageShellHeader` |
| Status | `StatusBadge` ([STATUS_BADGE_V1.md](STATUS_BADGE_V1.md)) — semantics `success` / `warning` / `danger` / `info` / `neutral` / `brand` only |
| Filters / view chips | `Chip` `behavior="selectable"` ([CHIP_V1.md](CHIP_V1.md)) — roster filters below the header |
| Campaign detail / list view switch | existing `.tabs` / `.tab` / `.tab-active` in `components.css` |
| Buttons | `.btn-*` / `Button` ([BUTTON_V1.md](BUTTON_V1.md)) — **one** primary in `PageHeader` (Create / Launch / Pause). Import is **secondary** on the advertising block |
| Fields | `.input` / `.label` ([INPUT_V1.md](INPUT_V1.md), [SELECT_V1.md](SELECT_V1.md)); file = native `input type="file"` triggered by `.btn-secondary` |
| Surfaces | `.card` / `.app-surface` / `.alert-*` — no new card primitive |
| Analytics table | [TABLE_V1.md](TABLE_V1.md) + `.table` when a table is the right control |
| Type / color / spacing | [FOUNDATION_V1.md](FOUNDATION_V1.md) · [ADR-011](../architecture/ADR-011-hostflow-ui-platform-standard.md) |
| Dates / money | locale helpers (`Intl`); ADR-011 §9 |
| Copy | i18n keys `app.marketing.*` — no JSX-only strings |

**Forbidden in this surface:** inline status palettes (today’s `statusTone()` Tailwind rings), four-decimal money on Overview, raw Meta / Ad / Form IDs as the primary label, a parallel KPI-card CSS kit, presenting Plane B numbers without a freshness timestamp.

North star ([HOSTFLOW_UX_NORTH_STAR.md](HOSTFLOW_UX_NORTH_STAR.md)): in ≤3 seconds the operator sees (1) what is happening, (2) whether there is a problem, (3) what to do next. Workflow beats extra columns. Signals beat navigation. Summary beats details.

Workspace split ([OPERATIONAL_WORKSPACE_MODEL](REF-UI-000-OPERATIONAL_WORKSPACE_MODEL.md)): `/app/marketing` is an **operational workspace**, not an entity-structure dump.

ADR-024 §12 five screens remain the **capability map**. This file is **how they are disclosed**.

---

## Domain vs operator copy

API, tables, and docs keep ADR-024 names. Operator copy may use the **already-canonical Russian gloss**, not a third entity.

| Domain / API | Operator copy (ru) | Rule |
|--------------|--------------------|------|
| Campaign | Кампания | Unchanged |
| Flight / `CampaignRun` | **Запуск** (волна) | HTTP still `/flights/{flight_id}`. Hide «Flight» on Overview while V1 has one current run (ADR-024 §1.2) |
| Endpoint / Source | Откуда приходят заявки | IDs → Settings |
| `FlightAdBinding` | Объявления | Ad ID → overflow «Техническая информация» |
| Submission / Lead (transport) | Заявка | Not a product entity (ADR-021) |
| Result | **Locked by `route_intent`** (next section) | Owned by destination module |
| Outcome | Цель / (hiring) наняты — only when Goal Type is `hiring` **and** Outcome is completed | Do not relabel Sales outcomes as hires |
| `cost_per_lead` | Цена заявки | Plane B + freshness; not a live Meta insight |
| `cost_per_outcome` / `outcome_value` / `roi` | CAC proxy / ценность / ROI | **Not** on Overview. Analytics: **omit the whole block** if compose is null (not `0`, not `—`, not a disabled card) |

---

## Result KPI by `route_intent` (not a free choice)

The fourth HostFlow KPI and the Result funnel step **must** follow the campaign’s primary `route_intent` from [`shared/campaign_registries.json`](../../../shared/campaign_registries.json). Implementers must not pick «кандидаты или обращения» per screen.

| `route_intent` | Result step label (ru) | Count SoT |
|----------------|------------------------|-----------|
| `candidate_application` | Создано кандидатов | Live Intake `candidates` (`candidate_id` set) — Recruitment owns the Candidate |
| `sales_inquiry` | Создано обращений | Destination Sales inquiry Result via attribution — **not** `candidates` |
| `service_request` | Создано заявок на услугу | Destination service Result via attribution |
| `partner_inquiry` | Создано обращений | Destination Result via attribution |

Workspace-level roll-up: **sum only campaigns that share the same Result label**. If the visible set mixes hiring and sales intents, **split** the Result cell (two labeled numbers) or omit a single mixed «кандидаты» total. Never add inquiries into «кандидаты».

**Conversion %** = Result count / submissions in the same window, only when submissions > 0. Label: «в кандидата» only for `candidate_application`; otherwise «в обращение» / matching Result label.

---

## HostFlow processing buckets (Plane A, existing fields only)

Do not mint a new lead-status dictionary. Compose from Live Intake `applicants` (`lead_status`, `candidate_id`, `status_label`, `disposition`).

**Awaiting (только это называется «новые» / «ждут обработки»)** — no destination Result (`candidate_id` empty **and** no dest result id) **and** `lead_status` not in `{processed, rejected, duplicated, failed, lost, archived}`.

**Заявки (period total)** — all submissions in the period. This is **not** Awaiting. Operator copy «новые» is **forbidden** for this total.

**Rejected** — `lead_status = rejected`.

**Result created** — `candidate_id` set (hiring) or attributed destination Result (other intents).

**Acted / обработано** — not Awaiting. Includes Result created, rejected, processed-without-result, duplicated, failed.

Period KPI «Обработано» = count of submissions in the window whose **current** bucket is Acted.

Campaign queue strip may show a **partition** of applicants in the window (omit a bucket if count = 0 **and** that is just empty, not a missing capability):

`{n} новых → {n} обработано → {n} {Result label} → {n} отклонено`

«Новых» here is **Awaiting only**. Those four are mutually exclusive operator-facing buckets of the same set (Acted-without-result folds into «обработано» so the four numbers sum to **Заявки**). Do not add a fifth synthetic bucket. Do not label the period total as «новые заявки».

---

## Disclosure layers

```text
MARKETING (workspace)
  L1 Overview     фильтр → живые заявки → (dated) рекламные данные → проблемы → кампании
       ↓
  Campaign
  L2 Overview     состояние → живая очередь/воронка → dated spend → действие
  L2 Leads        кто пришёл → статус → действие
  L2 Analytics    почему такой результат (HostFlow funnel + imported spend)
  L2 Settings     как подключено (Flight, Source, routing, Ad bindings, IDs)
```

Ops rails stay in the Marketing nav: Sources, Forms, Diagnostics, Acquisition Activity.

Progressive disclosure: **status and HostFlow facts → dated ad economics → causes → technical detail on request**.

---

## Global period

One control. **Two applications.**

| Rule | Value |
|------|--------|
| Default | Last **30** days |
| Control | `PageHeader` `secondaryActions` — native `<select className="input">` or Combobox ([SELECT_V1](SELECT_V1.md)) |
| Presets | 7 / 30 / 90 days |
| Plane A | Window `date_from`/`date_to` on submissions / results / outcomes. Portfolio GET **must** pass dates |
| Plane B | Same calendar window **intersected with imported coverage dates**. If the last import ends 29 Aug and today is 1 Sep, Spend/CPL in a «30 days» view cover only imported days, and the UI **must** say so |
| Deltas | Previous window of the **same plane** only. Never delta Spend against live submissions. Omit delta if either window lacks that plane’s data |
| Mixed freshness | Any strip that shows both planes must show **two** time contexts (period for A, «обновлено …» for B) |

---

## Capability gating (hide vs zero)

| Kind | If missing | If present and count is 0 |
|------|------------|---------------------------|
| Plane A operational counts (submissions, processed, results) | n/a — always in-scope for a campaign with intake | Show `0` |
| Funnel step whose **capability is absent** (e.g. no qualification rows exist for this campaign; Goal Type has no hire Outcome) | **Omit the step** — not `0` | — |
| Funnel step in-scope | — | Show `0` (real empty) |
| Plane B numbers (Spend, CPL, cost per result) | **No numbers**. Empty advertising zone + import CTA | Show `0` only if a snapshot exists with amount 0 |
| Analytics blocks: CAC proxy, Value, ROI, provider CPL, cost-per-hire | **Omit the entire block** if compose is null | Show `0` only when the formula denominator exists and the numerator is a real zero |
| Attention | Omit whole block if no rows | — |
| «Viewed» | **Always omit** — no capability | Never `0` |

**Not allowed:** disabled card, em-dash grid, `$0.0000` Spend with no import, ROI `—` as a column on Overview.

---

## `/app/marketing` — workspace home

**Role:** acquisition **operations** center.  
**PageHeader:** title «Маркетинг»; **one** primary CTA «Создать кампанию»; period as secondary.  
**Do not** put «Обновить данные» in `PageHeader` primary.

### Roster filter (below header)

`Chip` selectable, exactly four values:

| Chip | Membership (lifecycle of current Flight, else Campaign) |
|------|---------|
| Все кампании | Default. **All** statuses: active + paused + draft/planned + completed + archived + failed |
| Активные | **Only** `active`. Paused are **not** here |
| Требуют внимания | Attention compose match, **independent of lifecycle** (paused/active/draft may appear if the compose allows that status) |
| Завершённые | `completed` **or** `archived` only. Paused are **not** here |

On chip **Все** the roster is groups, in this order: (1) `active`, then `draft`/`planned`, then `failed` if any; (2) **paused — collapsed** `<details>` after the first group; (3) completed/archived — third collapsed group so Все is complete.

**Paused** never use a «still operable» test. Resume remains a row action wherever the campaign is visible (Все or Требуют внимания).

### Block order (mandatory)

| # | Zone | Hide when |
|---|------|-----------|
| 1 | Header + period + Create | never |
| 2 | Roster filter chips | never |
| 3 | Situation summary (Plane A; Plane B only as dated clause) | never |
| 4 | HostFlow KPI (four cells, Plane A) | never on the home |
| 5 | Advertising metrics (Plane B) | never as a **zone**; **numbers** hide until a snapshot exists |
| 6 | Needs attention | no items — whole block absent |
| 7 | Campaign roster (filtered) | empty copy + Create |
| 8 | Analytics disclosure | tab «Аналитика» — not a table above the list |

**Remove from first paint as a concept:** Portfolio KPI table as the lead block.

### 3. Situation summary (required)

Plane-A first. Plane-B only with freshness.

- With submissions: «{n} заявок за {period}.» + if attention: action clause. + if Plane B present: «Рекламные расходы обновлены {freshness}.»
- No campaigns: «Кампаний пока нет. Создайте кампанию, чтобы запускать рекламу.»
- All paused: «Реклама на паузе. {n} кампаний остановлены.»
- **Do not** lead with CPL when spend freshness ≠ period end.

Workspace StatusBadge: `brand` = ≥1 active Flight; `warning` = attention; `neutral` = all paused/completed; `danger` = routing/delivery failures (Stage 5 or `routing_failed`).

### 4. HostFlow KPI (required, Plane A only)

Exactly these four cells. **No Spend, no CPL here.**

| Cell (ru) | SoT | Empty |
|-----------|-----|--------|
| Заявки | All submissions in the period (not Awaiting) | `0` |
| Обработано | Acted bucket in the period | `0` |
| Result cell | Per `route_intent` table | `0`; mixed intents → split or omit combined total |
| Конверсия в {Result} | Result / **Заявки** (period submissions) | **Omit the % cell content** (not `0%`) if submissions = 0 |

Previous-window % only against Plane A.

### 5. Advertising metrics (required zone, Plane B)

Second row, visually secondary (existing `.card` / `.app-surface`, not a new kit).

When **no** snapshots:

```text
Рекламные данные
Ещё не загружались
[Загрузить свежие данные]   ← .btn-secondary + file input
```

When snapshots exist:

```text
Рекламные данные                    Обновлено: {date, time}
Расходы          Цена заявки        Данные обновлены
€428.50          €11.28             {coverage / imported_at}
[Загрузить свежие данные]
```

CPL here = **only** the [canonical HostFlow CPL](#covered-dates-cost-ratios-canonical) (spend on C / submissions with date ∈ C). If submissions continue after last coverage day, those later leads are **not** in the denominator.

**Forbidden in this row:** CAC, Value, ROI, impressions, reach as headlines.

### 6. Needs attention

Presentation compose, not a new SoT. Max 5 rows; overflow «Показать все» → filter «Требуют внимания».

| Kind | When | Copy | CTA | Semantic |
|------|------|------|-----|----------|
| Unprocessed | Awaiting > 0 in period | «{n} заявок получено, но {m} ещё не обработаны» | Campaign **Leads** | `warning` |
| Routing / delivery | `routing_failed` > 0 or Stage 5 delivery-error pause signal | «Ошибки маршрута: {n}» | Leads or Diagnostics | `danger` |
| Suggest pause | Stage 5 `recommended_action === suggest_pause` (locked thresholds) | Existing explainability copy | Campaign Overview | `warning` |
| High price | Canonical HostFlow CPL ≥ **2×** portfolio canonical CPL; **each** side’s coverage-aligned submission count ≥ 5; both sides have non-empty C | «Цена заявки {cpl} — значительно выше средней» | Campaign | `warning` |
| Silent | Active Flight, **0** Plane-A submissions in last **7** days, active ≥ 7 days | «Не получали заявок последние 7 дней» | Settings / Diagnostics | `warning` |
| Best result | Canonical HostFlow CPL defined and lowest among campaigns that also have defined canonical CPL in the same view | «Цена заявки {cpl} — лучший результат» | Campaign | `success` |

**Do not** emit High price / Best result when Plane B is missing or stale relative to the comparison window.

No pause/launch from this list. No row whose only evidence is null Value/ROI. Identical Silent rows may group («3 кампании…»).

### 7. Campaigns — Overview roster

| Column | Content |
|--------|---------|
| Кампания | Name only |
| Статус | `StatusBadge`: Active `brand` «Работает»; Paused `warning` «На паузе»; Planned/Draft `neutral`; Completed `info`; Failed `danger`. If in attention list, overlay `warning` «Требует внимания» **instead of** «Работает» |
| Результат | `{n} заявок` (Plane A period **total**, not Awaiting) |
| Цена | See **Price column** below — never “omit one cell” in a table row |
| Что происходит | **One** phrase from the locked priority list below |

**Price column (table structure):**

- If **no** campaign in the **current filtered roster** has a defined canonical HostFlow CPL → the **column is absent** for that view.
- If **at least one** has it → the column exists for every row. Rows without Plane B / undefined ratio show the i18n string **«Не загружено»** (`neutral` text). Forbidden in that cell: `—`, `0`, `$0.00`, blank.

Row actions: Open; Pause/Resume as Stage 4 commands on the current Flight (campaign-labeled).

### «Что происходит» — locked priority

Exactly one phrase. Evaluate **top to bottom**; first match wins. Frontend must not invent another ranking.

| Priority | When | Phrase (ru) |
|----------|------|-------------|
| 1 | Awaiting > 0 | «{n} ждут обработки» |
| 2 | Routing/delivery problem | «Проблема доставки» / «Ошибка маршрута» |
| 3 | Stage 5 `suggest_pause` | «Рекомендуется пауза» |
| 4 | High-price rule (Plane B) | «Высокая цена» |
| 5 | Silent (0 leads, 7 days) | «Нет заявок» |
| 6 | Best-result rule (Plane B) | «Лучший результат» |
| 7 | Paused, no 1–5 | «На паузе» |
| 8 | Else | «Нормально» |

---

## `/app/marketing/:campaignId` — campaign workspace

**Role:** run one initiative: handle people, then understand dated cost.  
**Not:** integration admin on first paint. **Not:** Meta Ads manager.

### Tabs (mandatory)

`.tabs` + `/:id/:tab`. Default omitted or `overview`.

| Tab | Path suffix | Question |
|-----|-------------|----------|
| Обзор | *(default)* | Is it working? Who is waiting? What did ads cost **as of import**? |
| Заявки | `leads` | Who arrived? What do I do? |
| Аналитика | `analytics` | Why this result? |
| Настройки | `settings` | How is it wired? |

`PageHeader`: campaign name; one primary by state (Launch / Pause / Resume / Connect source). Period inherited. Import is **not** the header primary.

### Overview tab — block order

| # | Zone | Required data | Hide when |
|---|------|---------------|-----------|
| 1 | Context | Name, one StatusBadge, destination **title** (vacancy/service) | never |
| 2 | HostFlow queue / funnel | Plane A only — see allowed steps | never (empty copy if zero submissions) |
| 3 | Next action | e.g. «12 заявок ждут обработки → Обработать» | no awaiting and no other attention |
| 4 | Advertising data | Plane B numbers + freshness + import CTA | zone always; numbers per gating |
| 5 | Ads (human) | Binding rows | no bindings — empty + Settings CTA |
| 6 | Source (short) | Provider + human form name + count | IDs behind «Настроить» |
| 7 | Launch history | Flights as **запуски** | single V1 run → one line, no Flight code |
| 8 | Recent applications | Last 5 Live Intake | zero — empty copy, no table |

**Forbidden on Overview:** Endpoint `forms 0/0`, raw `route_intent` headline, Ad ID list, cohort day table, commercial-value form, CAC/Value/ROI, `client_account`.

Example first paint (illustrative, not a layout spec):

```text
Kierowcy Rock Cargo
StatusBadge brand  Кампания активна

38 заявок получено
12 новых → 16 обработано → 7 кандидатов → 3 отклонено

Рекламные данные
Расходы: €412    Цена заявки: €10.84    Обновлено сегодня в 09:15
[Загрузить свежие данные]

12 заявок ждут обработки  →  Обработать
```

### Allowed Overview funnel steps (closed set)

Order is fixed. **Skip a step if that capability is absent for this campaign.** Do not insert synthetic steps. Do not show «просмотрено».

| Step | Capability present when | SoT |
|------|-------------------------|-----|
| 1 Заявки | Campaign has intake (always if Overview exists) | `submissions` / KPI `leads` |
| 2 Обработано | Live Intake applicants exist **or** submissions > 0 | Acted bucket |
| 3 Result | Primary `route_intent` as locked above | `candidates` or attributed dest Result |
| 4 Квалифицированы | ≥1 `CampaignResultQualification` linked to this campaign (ever), **or** Goal/KPI uses qualification | KPI `qualified` |
| 5 Outcome / наняты | Goal Type `hiring` **and** ≥1 CampaignOutcome on the campaign (ever) | `outcomes_completed`. Label «наняты» only for hiring completed Outcomes. Sales: «цель» / Outcome label, never «наняты» |

Routing failed is **not** a funnel step; it is attention / StatusBadge `danger`.

When Plane B exists, Analytics (not Overview) may show cost-per-step using **only** [Covered-dates cost ratios](#covered-dates-cost-ratios-canonical). These ratios are the **primary economic story** — above CAC/Value/ROI. Undefined ratio → omit the cell/block, not `0`.

### Ads

Human row: name from Integrations if present, else «Объявление» + last 4 of Ad ID. Thumbnail only if Integrations already returns a URL.

Spend on an ad row: the `ad` dimension fact for that `FlightAdBinding` (dates in C). HostFlow CPL on that row: canonical formula **only** with submissions attributed to that Ad ID. Else omit HostFlow CPL (not Flight CPL).

Overflow: today’s `MarketingAdBindingsPanel` actions.

«Лучшее объявление»: lowest defined HostFlow CPL among bindings with Plane-A leads ≥ 1 and Plane B present. Hide if fewer than two comparable ads.

### Source (short)

Human form/page name (`sourceCardPresentation`). Not `Meta form {id}` as the title.

### Launch history

Stage 6 flight compare, operator copy «запуск». CPL on a past launch only with that launch’s Plane B snapshots.

### Leads tab

Live Intake `applicants`. Filters only from existing `status_label` / buckets above. Actions: existing destination actions. Not R6. Empty: «Заявок за период нет» + Settings if no source.

### Analytics tab

HostFlow funnel + dated Plane B + power-user tables. **Gating applies.**

May include, each as its own block, **only if compose non-null**:

- Cost per submission / Result / qualified / hire (hiring) — canonical covered-dates ratios only
- Provider CPL (Meta-reported leads), labeled
- Flight compare
- Day/week/month cohorts **of Plane A** always; spend columns in those tables only for days with snapshots
- Commercial-value declaration (Stage 6 PR-6a)
- CAC proxy / Value / ROI — **last**, and **only** when `declared_v1` value exists; otherwise **no block** (no em-dash table)

Default chart window = global period. Day table allowed here only.

### Settings tab

Current technical UI: source cards, Ad ID bindings, runtime/endpoints, targets, complete/archive, mapping/test-lead links, diagnostics, provider IDs. `.settings-panel`, max three visual levels.

---

## Interpretation contract

| Data | Information | Action |
|------|-------------|--------|
| 38 submissions, 12 awaiting | «38 заявок за период, 12 ещё никто не обработал.» | «Обработать» → Leads |
| Spend €412, imported today 09:15 | «Расходы €412 по данным на сегодня, 09:15.» | Import again |
| HostFlow CPL €10.84 with spend through 29 Aug | «€10.84 за заявку по расходам до 29 августа.» | not “live CPL” |
| Value / ROI null | *(no block)* | declare value on Analytics only if Outcomes exist |

---

## Relocation map (current → contract)

| Current first-paint | Goes to |
|---------------------|---------|
| Portfolio KPI table (Spend/Leads/CPL/CAC/Value/ROI) | HostFlow four cells + dated advertising row; CAC/Value/ROI gated on Analytics |
| Campaign list with 4-decimal economics | Roster; CPL only with Plane B |
| Flight + Endpoint counters on detail header | Settings |
| Source card + Form ID | Overview short + Settings |
| Ad ID list | Overview ads (human) + Settings |
| Flight compare + cohorts + day table | Campaign **Analytics** |
| Commercial value form | Analytics, gated |
| Live Intake full table | **Leads**; Overview last 5 |
| Optimization banner | Overview attention |
| Nav ops rails | Unchanged |

No capability deleted. Live Insights not required to ship this disclosure.

---

## Data honesty (implementation notes)

| Wanted | Already exists? | Rule |
|--------|-----------------|------|
| Windowed Plane A | Portfolio `date_from`/`date_to`; Live Intake | Must pass the period |
| Spend | `CampaignFlightSpendEntry` (append via `record_flight_spend`) | Import writes here; do not mint a ledger |
| Spend grain / provenance | Amount only on the row today | Additive identity + `data_source` as provenance; upsert by economic identity; `meta_api` supersedes `meta_import` |
| Unprocessed / processed | Live Intake applicant fields | Compose; no new status enum |
| Result by intent | `candidates` vs attributions | Locked table — no screen-local choice |
| Viewed | **No** | Omit |
| Ad creative name | Integrations optional | last-4 fallback |
| Value / ROI | `declared_v1` often null | Omit blocks |
| Previous-period delta | No dedicated field | Same plane only; omit if incomplete |

Do not mint Acquisition-owned commercial value. Do not treat Meta export lead counts as HostFlow submissions.

---

## Empty and error states

- No campaigns: summary + Create; no empty 8-column table.
- No source: `warning` «Заявки ещё некуда принимать» + Connect source (existing primary-slot gate).
- No spend import: advertising **empty state** + file CTA; HostFlow KPIs still render.
- Load failure: existing `ErrorRecoveryBanner`.
- Partial Plane B failure: Plane A still renders; advertising zone shows the error + retry import.
- Unmatched Meta IDs on import: review list, not silent merge.

---

## Tests (when implemented)

Do not add tests in a contract-only PR. Future UI PR must prove:

1. First paint: no portfolio table as lead block; no CAC/Value/ROI on Overview; no live Insights chrome.
2. Four HostFlow cells have no Spend/CPL; advertising row shows freshness or empty import CTA.
3. Period applies to Plane A; Plane B copy names import/coverage time when both shown.
4. Result KPI follows `route_intent`; mixed hiring+sales does not sum into «кандидаты».
5. «Что происходит» uses the locked priority order (fixture: awaiting beats high CPL).
6. Funnel has no «просмотрено»; qualification/hire steps absent when capability absent.
7. Analytics: null ROI → block absent (query `—` / `0` / disabled card must fail).
8. Attention and High-price/Best-result do not fire without Plane B where required.
9. `StatusBadge` / `.btn-*` / `.tabs` / `Chip` / `PageHeader` — no `statusTone` palette; import is not header primary.
10. Stage 4 commands, C-3 sources, Ad-ID bind, Stage 5 banner, Stage 6 reads remain reachable.
11. Home KPI label is **Заявки** (period submissions), not «Новые заявки». «Новые» appears only on Awaiting (queue / attention).
12. HostFlow CPL fixture: spend covering {28,30} Aug, submissions on 29 Aug → those 29 Aug leads **must not** enter the denominator.
13. When import ships: five ads on one day → five `ad` rows, not one flight+day+source row; re-import of day D does not delete D−1; `meta_api` then `meta_import` for the same identity does **not** double spend; unmatched IDs stay in review.
14. Chip Активные excludes paused; paused are a collapsed group on Все; Завершённые is completed/archived only.
15. Roster Цена: column absent if no row has CPL; else «Не загружено» on rows without it — never a missing `<td>`.

---

## Cross-references

- Domain: [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §1.2, §12, §14.1
- Scope: [acquisition/module-scope.md](../../acquisition/module-scope.md)
- Ownership: [module_ownership_card.md](../../modules/acquisition/module_ownership_card.md) · [outcome-commercial-value-ownership.md](../../modules/acquisition/outcome-commercial-value-ownership.md)
- Spend SoT: [acquisition-epic-p-stage-3d.md](../tasks/acquisition-epic-p-stage-3d.md) (`acq_flight_spend_entries`)
- Shipped UI: [acquisition-ui-cutover.md](../tasks/acquisition-ui-cutover.md) (C-1…C-7 PASS — not reopened)
- Signals / KPI: [acquisition-stage-5-optimization.md](../tasks/acquisition-stage-5-optimization.md) · [acquisition-stage-6-analytics.md](../tasks/acquisition-stage-6-analytics.md) (hard ban on a second ledger)
- Registries: [`shared/campaign_registries.json`](../../../shared/campaign_registries.json)
- UI platform: [ADR-011](../architecture/ADR-011-hostflow-ui-platform-standard.md) · [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md)
- Security: extend [acquisition-stage-6-analytics.md threat model](../../security/threat-models/acquisition-stage-6-analytics.md) when the import write path ships — this contract adds no producer events by itself

---

## History

| Date | Change |
|------|--------|
| 2026-09-01 | Locked operator IA: progressive disclosure over Acquisition; implementation unscheduled |
| 2026-09-01 | Two data planes (live HostFlow vs imported ad economics); manual import as spend writer; Result KPI locked by `route_intent`; funnel/gating/attention priority closed; freshness required on Plane B |
| 2026-09-01 | Closed contradictions: Заявки vs Awaiting «новые»; canonical covered-dates cost ratios (union of days); spend grain + supersession (provenance ≠ identity); paused filters; roster Цена column |
