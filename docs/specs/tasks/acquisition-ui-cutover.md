# Acquisition UI Cutover

**Status:** **ACTIVE — Product Track next** (blocks Stage 5 PR-2)  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) · [acquisition/module-scope.md](../../acquisition/module-scope.md)  
**Depends on:** Stage **4 runtime** DONE (#136 / #148–#151)  
**Parents:** [Stage 4 — Flight Runtime](acquisition-stage-4-flight-runtime.md) · [Stage 5 — Optimization](acquisition-stage-5-optimization.md) (paused)  
**Branch (planned):** `feat/acquisition-ui-cutover`  
**Trusted tip at open:** `integration/release-product-a-b` @ `0d87d377` (docs PR-2 boundaries)

> Stage 4 **runtime** is DONE. Stage 4 **product/UI cutover** is **NOT DONE**.  
> Production still looks “old” because navigation and legacy Подборы surfaces were never retired.

---

## Diagnosis (locked 2026-07-23)

### What is already true in code

| Surface | Path | Role |
|---------|------|------|
| Marketing list / setup / detail | `/app/marketing`, `/app/marketing/new`, `/app/marketing/:campaignId` | Canonical Campaign / Flight operator SPA |
| Sales workplace | `/app/sales` | Client / service sales — **not** Growth owner |
| Form Builder (Forms platform) | `/app/settings/lead-forms`, `…/:formId`, `…/:formId/builder` | Forms SoT (ADR-007); **not** embedded in Marketing setup |
| Legacy Подборы | `/app/recruitment/searches`, `…/new`, inbox | Still registered and nav-visible |
| Legacy launch-from-search | `…/searches/:id/acquisition/*` | Still uses **searchAcquisition** activity API — **not** platform Campaign/Flight |

Nav fact: `SIDEBAR_AGENCY_SALES_ORDER = ['sales', 'marketing', 'clients']` — Marketing route exists, but **sidebar grouping** still nests it under Sales.

Marketing setup (`MarketingCampaignSetupPage`) calls `listLeadForms()` and binds an **existing** form — wizard only, **not** Form Builder.

### What was missed when Stage 4 was closed

Runtime delivered: Campaign/Flight API, commands, monitor, activity, Marketing ops card, deploy/smoke.

**Not** delivered as product cutover:

1. Marketing as top-level nav (not under Sales)  
2. Retire / freeze Подборы as an advertising launch surface  
3. Legacy links → Campaign/Flight (or read-only + reconciliation)  
4. Forms inside Marketing flow (`/app/marketing/forms…`) + create-form-in-setup  
5. Single operator path: Campaign → Form → Source → Target → Flight  
6. Full production navigation acceptance  

### Data / dual-model note (do not overclaim)

There is **no completed cutover** that retired Search as the ad-launch object. Platform Campaign/Flight coexist with:

- Recruitment Searches UI  
- Legacy search-scoped acquisition activities (`search_acquisition_service` / `createAcquisitionActivity`)

Any “подбор → Campaign” mapping must be **audited and reconciled** in this epic — not assumed already done for all rows. Unresolved rows go to a migration reconciliation queue.

**Do not** mechanically equate Подбор = Flight:

| Object | Role after cutover |
|--------|--------------------|
| **Campaign** | Growth initiative / promotion goal |
| **Flight** | Concrete launch wave |
| **Vacancy / hiring need** | Destination / Recruitment process (Operations) |
| **Recruitment inbox** | Processing arrived candidates |
| **Sales** | Client leads, offers, service sales |

---

## Corrected status line

```text
Stage 4 runtime          = DONE
Stage 4 product/UI cutover = NOT DONE  ← this epic
Stage 5 PR-1             = DONE (read-only signals)
Stage 5 PR-2             = PAUSED until this cutover closes
```

---

## Target IA (after cutover)

| Section | Owns |
|---------|------|
| **Marketing** | Campaigns, Flights, Forms, Sources, Activity |
| **Sales** | Client leads, offers, service sales |
| **Recruitment** | Candidates, vacancies/pipeline, inbox — **no** ad-launch “Подборы” object |
| **Settings** | Tenant/admin; Forms may remain Forms SoT but **operator create/edit** must be reachable from Marketing |

---

## PR sequence (initial)

| PR | Scope | Status |
|----|--------|--------|
| **C-1** | Nav: Marketing top-level section; remove from Sales bucket; Activity under Marketing | **DONE** — #157 |
| **C-2** | Stop legacy ad-launch from Подборы (`searchAcquisition`); reconcile to Campaign/Flight; block new dual-write debt | **In progress** — `feat/acquisition-ui-cutover-c2-stop-legacy-launch` |
| **C-3** | Forms under Marketing (`/app/marketing/forms`…) + create-form-in-setup flow | After C-2 |
| **C-4** | Подборы UI decommission: redirect/read-only; unresolved → reconciliation queue | After C-2/C-3 as needed |
| **C-5** | Production nav + smoke acceptance; close Stage 4 product cutover gate | Final |

**Ordering note (2026-07-23):** Form Builder embedding is **after** stopping `searchAcquisition` launch — otherwise new dual-path data keeps growing.

### C-2 locked scope

1. Forbid creating new launches via `searchAcquisition` (POST activities/channels + `duplicate` action).  
2. Inventory all legacy launch call sites (frontend + backend) — enforced by scan tests.  
3. Unambiguous Подбор/vacancy → Marketing setup prefilled (`Campaign → Flight` with `target_type=vacancy`).  
4. Ambiguous / historical activities → `reconciliation` state on acquisition snapshot (`linked` \| `unresolved`).  
5. Подборы acquisition UI stays temporarily as **read-only / legacy** (view + sync + pause/resume/archive of existing rows only).  
6. Where a Campaign is already linked by vacancy target — surface link/redirect to that Campaign.  
7. Do **not** delete legacy JSON/activity data until reconciliation complete.  
8. Do **not** touch Form Builder in C-2.

**C-2 acceptance:** after merge, no user action may create a new acquisition launch outside Campaign/Flight.

### C-2 call-site inventory (enforced by scan tests)

| Surface | Path | C-2 behavior |
|---------|------|----------------|
| API create | `POST …/vacancies/{id}/acquisition/activities\|channels` | **410** `legacy_launch_disabled` + `marketing_setup_path` |
| API duplicate | `POST …/activities/{id}/actions` `action=duplicate` | **410** same |
| FE helper | `createAcquisitionActivity` / `createAcquisitionChannel` | throws client-side; no HTTP |
| Launch page | `…/searches/:id/acquisition/new` | redirect → `/app/marketing/new?target_type=vacancy&…` |
| Acquisition layout CTA | Подборы acquisition header | «Создать в Marketing» + legacy banner + Campaign link when `reconciliation.status=linked` |
| Search workspace pulse | «Запустить рекламу» | Marketing setup href (not legacy create) |
| Snapshot | `GET …/acquisition` | `legacy_mode`, `reconciliation`, `marketing_setup_path` |
| Form Builder | Settings lead-forms builder | **out of scope** (C-3+) |

Scan tests: `backend/tests/api/test_acquisition_c2_legacy_launch_disabled.py`, `hostflow-frontend/src/app/__tests__/acquisitionC2LegacyLaunchScan.test.ts`.

---

## OUT

- Auto-pause / Stage 5 PR-2 explainability (resume only after cutover PASS)  
- Renaming Vacancy/Inbox into Campaign  
- New Marketing product module / `marketing.*` host (ADR-024 anti-scope)  
- Changing Flight Runtime command matrix  

---

## Acceptance (cutover PASS)

- [ ] Marketing is a top-level sidebar section (not under Sales)  
- [ ] Operator can create/edit/publish a form from Marketing without a Settings detour as the only path  
- [ ] Marketing Setup supports select-existing **and** create-new-form-in-flow  
- [ ] New ad launch cannot start from Подборы; legacy URLs redirect or read-only  
- [ ] Reconciliation inventory: migrated / unresolved counts documented  
- [ ] Sales / Recruitment / Marketing IA match the table above  
- [ ] Deploy smoke of full production nav  

---

## History

- 2026-07-23: Opened after owner diagnosis — Stage 4 runtime DONE but product/UI cutover incomplete; Stage 5 PR-2 paused.
- 2026-07-23: **C-1 DONE** (#157) — Marketing top-level nav; Activity under Marketing; Sales = sales+clients only.
- 2026-07-23: Product Track next = **C-2** legacy launch stop + Campaign/Flight reconciliation (Forms C-3 deferred).
