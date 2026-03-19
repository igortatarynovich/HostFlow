# HostFlow SSOT (Single Source of Truth)

This file is the **only source of truth** for:

- current product readiness status
- remaining work (backlog)
- evidence of completion (kept inline here)

Rules:

- **All** progress updates and status changes go to this file.
- No new “tracker” markdown files should be added elsewhere.
- Supporting docs like specs/blueprints may exist, but they are **not trackers**.

---

## Requirements sources (non-tracker)

- Product blueprint (workflow/UX principles): `docs/pipe.md`
- Landing/SEO/design direction: `docs/pipedesign.md`
- Module specs (reference): `docs/specs/**`

---

## Current status (2026-03-17)

### Product readiness

- **Overall**: **READY**
- **Primary remaining release-pass**: **production scenario A (`services`) on tenant `victoria-services`**

### Evidence (latest)

- **Frontend static gate**: `npm --prefix hostflow-frontend run qa:static` → **PASS**
- **Staging scenario automation (A/B/C)**: Playwright+API run artifacts exist (local evidence used during stabilization).
- **Key fixes implemented** (high-level):
  - module visibility gating enforced via tenant module flags + effective role-module matrix
  - communications readiness verified (inbox, send, templates/signatures, scheduler/worker/audit depth checks)
  - leads path validated (source → lead → assignment → action) + retry semantics
  - SPA fallback for local E2E routing
  - mock email delivery mode for safe staging/local verification

---

## Audit vs requirements docs

### `docs/pipe.md` (product blueprint)

- **Implemented / aligned**
  - Topbar/Sidebar/Workspace layout exists and is used consistently.
  - “Visible next action” is enforced operationally via reminders/next steps, and leads now create follow-up actions on processing.
  - Minimal-click paths and empty-state guidance exist for key modules (measured/verified during stabilization).
  - Global search exists (candidates/companies/documents).
  - Document intelligence + compliance rulesets exist (completeness/expiry/missing, rules engine + ruleset versions).

- **Partial / not yet proven as a first-class UX pattern (needs explicit product sign-off)**
  - Candidate **quick preview side panel** for list workflows (fast context without navigation).
  - A unified, always-available **timeline** for candidate/entity history (single chronological context surface).
  - Explicit performance budgets in the doc (e.g. 200ms/100ms) are not captured as formal perf evidence in this SSOT.

### `docs/pipedesign.md` (landing/SEO/design system)

- **Implemented / aligned**
  - Public surface exists: `/`, `/pricing`, `/signup`, `/login`, feature/use-case/comparison pages.
  - SEO meta system exists (`useSeoMeta`) and sitemap generation is part of the build/static gate.

- **Partial**
  - Design tokens (exact radii/spacing/color specs) need a single verified “tokens source” and a quick visual audit pass to confirm 1:1 alignment.

---

## Backlog (what’s left)

### Release-pass

- [ ] **Production run: Scenario A (`services`) on `victoria-services`**
  - Definition: execute run-sheet for scenario A in production and capture final PASS evidence.
  - Output: inline evidence block in this SSOT (timestamp, tenant, steps, result, and pointers to logs/screens where applicable).

### Product gaps vs blueprint (pipe.md)

- [ ] Implement and sign off **Candidate quick preview** (side panel) to reduce clicks in list workflows.
- [ ] Implement and sign off **Candidate timeline** as a single unified history surface (events/documents/communications/reminders).
- [ ] Add a minimal **performance evidence pack** for key screens (list load, open detail, create/send) to match blueprint expectations.

### Marketing/SEO/design gaps vs `pipedesign.md`

- [x] Confirm **design tokens** (spacing/radius/colors/typography) are implemented as a single source (and remove drift). (aligned Tailwind `brand.*` palette and base typography with `docs/pipedesign.md`: primary `#3FA3A8`, accent `#2E6F74`, section bg `#F4F8F9`; removed competing body font override so Inter is canonical)

### Hygiene / repo policy (must stay enforced)

- [ ] Ensure **no** `.venv/` content is tracked by git
- [ ] Ensure **no** `node_modules/` content is committed
- [ ] Keep artifacts (screenshots/json) out of git; store externally if needed

---

## Change log (SSOT-managed)

- `2026-03-17`: Consolidated SSOT created (`docs/SSOT.md`). Legacy trackers and scattered run-records should be removed; all future updates go here.

---

## System audit report (goal: better than Pipedrive)

### North Star (what “better than Pipedrive” means for HostFlow)

Pipedrive wins because it reduces friction in daily work. HostFlow must **match** that usability baseline and then **surpass** it by being a specialized “Recruitment Operations CRM”:

- **Pipedrive-like**: fast scanning, minimal clicks, clear next action, simple automation, operational visibility.
- **HostFlow advantage**: candidate readiness/compliance, document intelligence, recruitment-specific workflow, and domain automations that generic CRM cannot do without heavy customization.

Success definition:

- A new team can run their core recruitment workflow end-to-end **without training**.
- The system **prevents operational risk** (missing docs, expirations, stuck candidates) rather than merely storing records.
- The system remains **fast** and **predictable** under real load and real team usage.

---

## What is already strong (current strengths)

### Workflow skeleton & readiness gates

- The core modules exist and are connected: candidates/companies/vacancies/leads/documents/communications/reminders/billing.
- Navigation and access governance are hardened (permissions, module gating, role/module matrix).
- Communications workspace is coherent (messages/email/calendar/planner/availability) with operational settings.
- Leads ingestion path is operational (source → lead → assignment → action) with retry semantics.

### Compliance/document engine foundations (differentiator)

- Candidate documents module has:
  - required docs / templates / workflow steps
  - readiness-like meta (completeness, expiring soon threshold, negative statuses)
  - ruleset engine foundations (backend) and versions UI

### Product-led UX scaffolding

- Empty states provide explanation + CTA + next step across key surfaces.
- Global search exists (candidates/companies/documents).
- Static QA gate exists and is kept passing.

---

## Where we are not yet “Pipedrive-level” (gaps & problems)

This list is written as “problem → why it matters → what we do”.

### 1) Candidates screen must become the “daily command center”

**Problem**

`docs/pipe.md` describes a Candidates screen pattern that creates daily flow: pipeline summary → filter → table → preview → act. Today, we have the parts, but we do not yet have a single “command center” experience that feels inevitable and frictionless.

**Why it matters**

In Pipedrive, the list view is where work happens. If HostFlow forces too many page navigations or hides action context, teams churn.

**Solution direction**

Implement the missing Pipedrive-grade loop:

- **Quick preview side panel** (list → preview without navigation)
- **Inline next action** visibility and editing
- **Fast bulk operations** that remain discoverable but not noisy

**Acceptance (must be measurable)**

- From Candidates list, user can: open preview, see docs + next action + timeline, and perform a key action in **≤ 2 clicks** from the list.

### 2) Unified timeline must be the “truth layer”

**Problem**

We have events scattered across modules: reminders, docs, comms, candidate changes. `pipe.md` expects a single chronological timeline that provides instant context.

**Why it matters**

Pipedrive’s history is a major retention driver. Without it, operational ownership is fragile and team handoffs break.

**Solution direction**

Create a unified timeline surface and event schema:

- normalized event types (created, stage change, doc uploaded/checked/expired, message/email sent/received, reminder created/completed, assignment changes)
- consistent rendering in candidate preview and candidate profile
- link-outs to the object that generated the event

**Acceptance**

- A supervisor can open a candidate and reconstruct the last 14 days of actions in 30 seconds without hunting across tabs.

### 3) “Next action” must be enforced, not optional

**Problem**

`pipe.md` frames “entity without next action = risk”. We partially enforce next action through reminders and lead follow-up, but we do not yet guarantee that candidates always have a next action and that stale/stuck states generate interventions.

**Why it matters**

Pipedrive’s activity enforcement is a key differentiator. HostFlow must do the same, but in a recruitment-native way.

**Solution direction**

- Candidate-level next-action contract:
  - required for certain stages, optional for others
  - SLA for “no next action” and “stuck in stage”
- Automations:
  - create initial tasks on candidate creation
  - generate stage-based checklists/tasks
  - stuck detection (e.g., >7 days) → warning + suggested action + optional auto-reminder

**Acceptance**

- “Candidates without next action” becomes a first-class view and a KPI.

**Implementation (current)**

- Leads-first next action loop:
  - Leads list exposes `next_action_status` (`scheduled` / `overdue` / `no_next_action`) and `next_action_due_at`.
  - Leads list supports drill-down filter via query param `next_action` (e.g. `/app/leads?status=processed&next_action=no_next_action`).
  - Dashboard ops counters include processed leads compliance counters (`leads_no_next_action`, `leads_overdue`, `leads_with_next_action`, `leads_total`).
- Enforcement setting (tenant):
  - `Tenant.settings.next_action_enforcement_v1 = { mode: 'off' | 'warn' | 'block' }`
  - Applied to lead stage changes (`PATCH /api/v1/leads/{id}`): in `warn` logs an ops signal, in `block` rejects stage change when there is no active reminder for the lead.

**SLA nudges (current)**

- Background scheduler runs tenant-scoped SLA checks (same loop as communications SLA/docs deadlines).
- Config:
  - `Tenant.settings.leads_next_action_sla_v1 = { enabled?: bool, noNextActionAfterHours?: number, createNotifications?: bool, createReminders?: bool, limit?: number }`
  - Env kill switch: `COMM_SCHEDULER_LEADS_NEXT_ACTION_SLA_ENABLED=true|false`
- Behavior (Leads-first):
  - For `Lead.status == 'processed'` with **no active reminders** for `N` hours (default 24h), create a best-effort nudge for ops assignee:
    - in-app notification `lead_no_next_action` (deduped daily)
    - internal reminder `type='leads_no_next_action'` assigned to ops recipient (idempotent: only one active per lead+assignee)
- Stuck detection (Leads-first):
  - We log `lead.stage_changed` into `ActivityLog` on stage updates.
  - For `Lead.status == 'processed'` in active stages (default: `new/contacted/qualified`), if **no stage change** for `D` days (default 7d), create:
    - in-app notification `lead_stuck_stage` (deduped daily)
    - internal reminder `type='leads_stuck_stage'` assigned to ops recipient (idempotent per lead+assignee)
  - Config (same namespace): `Tenant.settings.leads_next_action_sla_v1.stuckAfterDays` and optional `stages: string[]`.
- Ops visibility:
  - `GET /api/v1/analytics/ops-counters` includes `leads_sla_no_next_action_reminders` (active assigned SLA reminders).
  - `GET /api/v1/analytics/ops-counters` includes `leads_sla_stuck_stage_reminders` (active assigned stuck-stage reminders).

### 4) Automation must be event-driven and user-visible

**Problem**

We have automations surfaces (queue routing, SLA, rulesets). But Pipedrive-grade automation is:

- event-driven (trigger → action)
- understandable (why did this happen?)
- editable (simple UI)

Today, “why did the system do X?” is not fully transparent.

**Why it matters**

Automation without explainability creates mistrust. Mistrust kills adoption.

**Solution direction**

- Introduce an “Automation log” per candidate/company/thread:
  - what rule fired, input conditions, actions executed, failures
- A minimal “rules builder” scope:
  - start with a narrow set of triggers (candidate created, stage changed, doc missing/expiring, lead processed)
  - actions (assign, create reminder, send template message/email, set tag)

**Acceptance**

- Any automated action has a visible audit entry and a “disable rule / adjust rule” pathway for admins.

### 5) Reporting must become operational (not vanity)

**Problem**

`pipe.md` expects operational visibility: stage conversion, average stage time, drop-off reasons, top recruiter, time to hire. We have some analytics and a TTV report, but we need a coherent operational reporting stack.

**Why it matters**

Pipedrive sells and retains on “see what’s happening”. HostFlow must do this, but for recruitment operations (docs/compliance/time-to-ready).

**Solution direction**

- Define 8–10 canonical widgets and metrics:
  - pipeline counts + stage time
  - “ready drivers” readiness distribution
  - missing docs hotspots (by doc type)
  - expiring soon alerts
  - time-to-ready/time-to-hire
  - recruiter workload and throughput
- Ensure each widget has a drill-down path (click → filtered list view).

**Acceptance**

- A team lead can start their day on Dashboard and open the top 3 operational issues in ≤ 2 clicks each.

### 6) Performance & UX budgets must be explicit

**Problem**

`pipe.md` gives aggressive performance targets (200ms/100ms). We do not have a formal “perf evidence pack” or budgets in CI.

**Why it matters**

Speed is usability. Usability is retention.

**Solution direction**

- Define performance budgets (realistic web targets):
  - list load p95, detail load p95, search latency, inbox fetch time
- Add lightweight measurements:
  - client-side timing beacons (already have analytics scaffolding)
  - periodic manual profiling on staging

**Acceptance**

- SSOT contains a living perf baseline table (p50/p95) and alerts when regressions happen.

---

## Roadmap (how we evolve HostFlow into “Pipedrive+”)

This roadmap is sequenced to maximize adoption impact and minimize architecture churn.

### Phase R0 — Release-pass (production)

- Production scenario A (`services`) on `victoria-services` with PASS evidence captured inline in this SSOT.

### Phase R1 — Daily command center

- Candidates: quick preview side panel + action loop from list.
- Candidate timeline v1: unify events from docs + reminders + comms.
- “Next action” contract: views and warnings.

### Phase R2 — Explainable automation

- Automation log (“why did it happen?”).
- Small rules builder scope for the most valuable triggers/actions.

### Phase R3 — Operational reporting

- Dashboard widgets + drill-down paths.
- Stage conversion/time-to-hire/readiness reporting.

### Phase R4 — Performance governance

- Perf budgets + baseline capture in SSOT.
- Regression detection and response playbook.

---

## Backlog (expanded, actionable)

### R0

- [ ] **R0.1 Production PASS: scenario A (`services`) on `victoria-services`**

### R1

- [ ] **R1.P0 Preview rail click-blocker (CRITICAL)**  
  **Priority:** P0 / first before any UX polishing in R1.5.  
  **Problem (production):** after opening candidate Preview in `/app/candidates`, UI becomes partially non-interactive (clicks on links, checkboxes, row actions, and column filters are blocked or ignored).  
  **Scope of impact:** breaks core operator flow in Candidates list.  
  **Important observation:** issue appears only after Preview content is opened; opening right menu from topbar alone does not reproduce blocker.  
  **Definition of done:**  
  - No global click interception after Preview open (all table/filter/link actions remain clickable).  
  - Switching Preview between candidates works without page refresh.  
  - Opening full candidate card works while Preview is open.  
  - Verified manually in browser + network (clicks trigger expected requests/actions).  
  **Temporary safeguard accepted:** keep column DnD disabled in Candidates list until blocker is fully resolved.  
  **Mandatory follow-up after fix:** restore and re-validate column DnD behavior (drag, resize, persisted order) without reintroducing click blocking.

- [x] **R1.1 Candidates quick preview side panel** (implemented in Candidates right sidebar: select row → Composer/Focus/History + reminders)
- [x] **R1.2 Candidate unified timeline v1** (Candidates list preview side panel `History` tab: unified view of `ActivityLog` (candidate events) + reminders (created/completed), via `GET /api/v1/candidates/{id}/timeline`)
- [x] **R1.3 Next action contract + “no next action” operational view** (next action = active reminder; added `/api/v1/candidates/no-next-action` + UI page `/app/candidates/no-next-action`)
- [x] **R1.4 Leads qualification “fit-check” v1 (vacancy requirements → lead match)** (see “Vacancy requirements presets + lead fit-check v1” section below)
- [ ] **R1.5 Candidates command center v2 (table + candidate card redesign)** (efficiency-first; remove “Timeline tab” anti-pattern; unify actions + context; see plan below)

#### R1.5 Plan — Candidates command center v2 (efficiency-first)

**Goal**

Turn Candidates into the primary “work surface” (not a registry), with a clear loop: **scan → pick → act → verify**. CandidateCard becomes a “case file” optimized for operations (stage changes, docs readiness, reminders/comms, handoff) with **timeline always visible** and without tab-hopping.

**What’s wrong today (observed)**

- **Candidates table (current)**:
  - Too much control surface at once (many columns + DnD + resize + filters + bulk tools + keyboard shortcuts + side panel) → high cognitive load, slow to find “what to do next”.
  - Column system is powerful but not efficient by default: users must curate; the “best default” isn’t opinionated enough for daily ops.
  - “Preview sidebar” exists, but “work loop” is split: some actions live in preview, others require opening the full card; the transition is not designed as a primary flow.
  - Filters are capable but not structured as **Quick views** (Saved views / KPI drill-down) → users re-build mental context each time.
  - Performance risk: the page is a large monolith (state + localStorage orchestration + virtualization + DnD) → higher chance of regressions and longer time-to-interact.

- **Candidate card (current)**:
  - Information architecture is “tabs first” (Personal / Docs / Timeline / Services). The **Timeline tab** is a dead-end: timeline is context, not a destination.
  - Actions are scattered across places (header + quick panel + per-section UI) and the layout doesn’t reflect the operational priority: stage/docs/next action/comms should dominate the right rail.
  - Timeline is duplicated/fragmented (stage history modal + timeline tab + notes + reminders), which increases “where do I look?” cost.

**Design principles (hard rules)**

- **Timeline is always visible** (right rail / work panel). It should never require a dedicated top-level tab.
- **One primary surface per intent**:
  - list = scanning + triage + bulk
  - card = deep work on one candidate
- **Default beats configurability**: keep power features, but ship a ruthless default layout that works day 1 without customization.
- **Two-click rule** from list to key action (stage change, create reminder, request docs/handoff).

**Target UX (v2)**

- **Candidates list** becomes a 3-part layout:
  - **Left**: table/kanban toggle + search + quick filters + saved views (opinionated).
  - **Center**: virtualized table with a compact, consistent row layout (name + stage + next action + docs readiness + vacancy + assignee/manager).
  - **Right “Work panel”** (persistent): when a row is selected, show:
    - next action editor (create/snooze/complete reminder)
    - docs readiness summary + missing critical docs
    - comms composer (quick message/email entry point)
    - mini-timeline (last 15 events; expandable)
    - quick actions (handoff, stage change, tag, favorite)

- **Candidate card** becomes a **2-column case file**:
  - **Main column**: structured sections (Personal, Status/Eligibility, Experience, Custom fields, Employer/vacancy).
  - **Right rail (sticky)**: “Work panel” identical to list preview, plus:
    - docs checklist block (embedded, not a separate tab)
    - services/orders/invoices summary (if relevant)
  - Remove top-level **Timeline tab**; timeline exists in the right rail and can expand to a full-height overlay if needed.

**Phased implementation**

- **Phase A — “Timeline tab removal” + unified Work Panel (UI-only, safe refactor)**
  - CandidateCard:
    - Replace tabs with: `Personal`, `Docs` (optional), `Services` (optional). Remove `Timeline` top-level tab.
    - Move unified timeline rendering into the right rail (sticky), default-collapsed with “Show more”.
    - Keep StageHistory modal only if it adds unique value; otherwise merge into timeline.
  - Candidates list:
    - Promote Work panel to first-class: improve selected-row affordance and make “act in panel” the default path.

- **Phase B — Opinionated defaults: Quick Views + KPI drill-down**
  - Introduce “Saved views” as first-class UI (not hidden settings):
    - `My work today`, `Overdue next action`, `No next action`, `Docs incomplete`, `Ready for handoff`, `New this week`.
  - Views must be shareable (URL params) and persist per user (existing `UserSavedView` concept).

- **Phase C — Table v2 row model (efficiency + fewer columns)**
  - Create a **default compact row schema** and relegate niche fields to optional columns.
  - Add “Row quick actions” (stage dropdown, reminder quick add, open card) with hover-only to keep noise low.
  - Keep power features (DnD/resize/custom columns) but make them secondary (via “Customize” mode).

- **Phase D — Data shaping + performance**
  - Add a lightweight “list row payload” on backend (or ensure current endpoint provides) so list does not need heavy joins/extra normalization.
  - Add a single “work panel payload” endpoint that returns: next action, docs readiness summary, recent timeline, and comms pointers in one request.
  - Perf budgets:
    - `candidates.list.load` p95 ≤ 2500ms (already tracked)
    - new: `candidates.work_panel.load` p95 ≤ 800ms (selected row)
    - new: `candidate.card.open` p95 ≤ 1200ms

**Acceptance (measurable)**

- From Candidates list, for a selected candidate:
  - create a reminder OR change stage OR start handoff in **≤ 2 clicks** without leaving the page.
- On CandidateCard:
  - user can see: stage, docs readiness, next action, and last 10 events **without switching tabs**.
- Timeline:
  - no dedicated timeline tab exists; timeline is visible in right rail and expandable.

**Implementation notes (where to change)**

- Frontend:
  - Candidates list: `hostflow-frontend/src/pages/Candidates.tsx` (split into smaller components + a `WorkPanel` module; isolate table state from panel state).
  - Candidate card: `hostflow-frontend/src/pages/CandidateCard.tsx` (remove `timeline` tab; extract timeline renderer into shared component used by list + card).
- Backend:
  - Confirm/extend `GET /api/v1/candidates/{id}/timeline` payload for “recent events” and include enough metadata for inline rendering.
  - Add (or formalize) a “work panel” endpoint (candidate summary + next action + docs readiness + recent timeline) to avoid N+1 fetches.

### R2

- [x] **R2.1 Automation log (rule fired → actions)** (ActivityLog-based; reminders emit `automation.*`; added API `/api/v1/automation-log` + UI `/app/automation-log`)
- [x] **R2.2 Minimal rules builder (candidate created/stage changed/doc expiring/lead processed)** (DB-backed rules + API `/api/v1/automation-rules` + UI `/app/automation-rules`; execution wired for `candidate.created`, `candidate.stage_changed`, `lead.processed`)

### R3

- [x] **R3.1 Dashboard operational widget set (8–10) + drill-down** (added ops counters API + Operational widgets block on Overview with drilldowns)
- [x] **R3.2 Stage time + conversion + readiness analytics** (added `/api/v1/analytics/stage-metrics` + Overview block with readiness/stage-time/transitions)
- [ ] **R3.3 Services module v2 (sell → fulfill → invoice → collect) + analytics** (revamp `/app/services`: simplify flow, add invoice/payment linkage, and actionable KPIs)

### R4

- [x] **R4.1 Perf baseline capture (p50/p95) for key actions** (added `analytics.perf.measured` events via `/api/v1/analytics/events`, baseline report `GET /api/v1/analytics/perf-baseline`, and Overview block “Performance baseline”)
- [x] **R4.2 Perf budgets + regression response workflow** (added `GET /api/v1/analytics/perf-budgets` + budget breach signal `analytics.perf.budget_breached`; Overview highlights p95 regressions vs budget; playbook below)

#### R4.2 Playbook (regression response)

**Signals**
- Baseline table on `/app/overview`: p95 highlighted red when it exceeds budget.
- `ActivityLog` action `analytics.perf.budget_breached` indicates a live budget breach (contains `metric_key`, `duration_ms`, `budget_p95_ms`, `route`).

**Workflow**
- **Triage**: confirm the metric key and route; check if breach is widespread (many samples) vs isolated spike.
- **Reproduce**: open the same route with similar filters/data size; repeat 3–5 times to reduce variance.
- **Profile**: capture a short CPU profile around the action; identify the hottest functions (render loops, expensive selectors, large table work).
- **Fix**: prefer data shaping (compact payloads, pagination), memoization, virtualization, and avoiding repeated fetches.
- **Verify**: re-run the action and ensure p95 is back under budget; keep the budget stable unless product requirements changed.

**Budgets (current, p95 ms)**
- `leads.list.load` ≤ 1500
- `candidates.list.load` ≤ 2500

---

## Vacancy requirements presets + lead fit-check v1 (qualification accelerator)

Goal: speed up Leads Inbox processing by making “requirements” explicit, reusable, and automatically evaluated on incoming leads.

### What we implemented (v1)

- **Vacancy requirements stored explicitly**: `Vacancy.extra.lead_criteria_v1` (no schema migration; rides on existing `extra` JSON field).
- **Lead list returns match result**:
  - `LeadOut.fit_status`: `fit | no_fit | needs_info | no_criteria`
  - `LeadOut.fit_reasons`: list of strings explaining what’s missing / failing
- **UI**:
  - Vacancy detail now has a criteria editor (MVP) for:
    - min EU experience years
    - required documents (comma-separated codes)
  - Leads list shows a **Fit** badge with tooltip (reasons)
- **Presets (reusable requirements)**:
  - stored in `Tenant.settings["vacancy_requirements_presets_v1"]`
  - API (team settings):
    - `GET /api/v1/settings/team/vacancy-requirements-presets`
    - `PUT /api/v1/settings/team/vacancy-requirements-presets/{preset_id}`
    - `DELETE /api/v1/settings/team/vacancy-requirements-presets/{preset_id}`
  - Vacancy UI can select a preset and **Apply** it (copies criteria into vacancy form fields; then save vacancy).

### Criteria schema (v1, stored in `lead_criteria_v1`)

Current MVP supports:
- `min_experience_eu_years: int` → compared against `lead.normalized.experience_eu_years`
- `requires_documents: string[]` → compared against `lead.normalized.documents[]` (if present)

Fit semantics:
- **fit**: all criteria satisfied
- **no_fit**: hard mismatch (e.g. experience below minimum, missing required doc)
- **needs_info**: cannot evaluate because required lead data is missing (e.g. experience/documents not provided)
- **no_criteria**: vacancy has no requirements configured

### Design decisions (why this shape)

- **Copy-on-apply presets (MVP)**: vacancy “Apply preset → save” is intentionally simple and stable.
  - Pros: requirements always visible on vacancy; no hidden indirection; fit-check uses only vacancy row → fast.
  - Later: add “linked preset” mode if we need global edits to propagate.
- **No hard dependency on Documents module yet**: v1 reads `lead.normalized` only.
  - Next: integrate with Documents to compute `documents[]` from real candidate/lead evidence.

### Next steps (v2+)

- **Preset manager UI**: create/edit/delete presets from UI (not only via API).
- **Expand criteria**:
  - nationality/citizenship (from `lead.normalized.country` and/or dedicated field mapping)
  - location / in Poland (`lead.normalized.in_poland`)
  - language (requires lead field mapping + normalization)
  - document policies: integrate with Documents module (real document statuses vs free-form codes)
- **Automation: auto-convert lead→candidate** (opt-in / feature-flagged):
  - trigger: on lead ingestion or manual processing when `fit_status=fit`
  - safeguards: rate limits, idempotency, audit log “why”, ability to disable per vacancy/preset

---

## Multi-own-companies inside one tenant (own vs client) — v1

Goal: allow **multiple “my companies” (legal entities/brands)** inside a single tenant, with a **global context switch** (no re-login), while keeping **client companies** separate.

### What we implemented (v1)

- **New entities**:
  - `own_companies` (our legal entities / brands)
  - `client_companies` (client/employer entities; kept separate to avoid mixing semantics)
- **Scoping for ops data**: added `own_company_id` and backfilled existing rows (default own-company per tenant) for:
  - `vacancies`, `candidates`, `leads`, `documents`, `invoices`, `communication_threads`, `communication_messages`
- **Active own-company resolution** (backend):
  - `X-Own-Company-Id` header → `User.preferences.active_own_company_id` → first own-company
  - if no own-company exists: APIs that require scope respond with `OWN_COMPANY_REQUIRED`
- **API**:
  - `GET /api/v1/own-companies`
  - `POST /api/v1/own-companies` (enforces `TenantLicense.max_companies`)
  - `PATCH /api/v1/own-companies/{id}`
  - `POST /api/v1/own-companies/active` (stores `active_own_company_id` in user preferences)
- **Frontend switcher**:
  - topbar dropdown to switch active own-company
  - persists to localStorage and sends `X-Own-Company-Id` automatically on requests
- **Onboarding (updated)**:
  - “Create company” now creates an **own-company** and sets it active
  - onboarding status now uses **own-companies** as the “company_created” step (legacy `companies` remains for now)
- **Alembic**:
  - heads were merged into a single head revision; migrations are now upgradeable with `alembic upgrade head`

### Next steps (v2+)

- [ ] **Legacy `companies` migration plan**:
  - [ ] define mapping rules: which legacy rows become `client_companies` (and which remain as legacy until removed)
  - [ ] migrate references: replace usage of legacy “operating company” semantics in invoicing/billing to use `own_companies`
  - [ ] add read-only compatibility layer if needed during transition
- [ ] **Complete scoping coverage**:
  - [ ] audit remaining modules and ensure list/get/update endpoints filter by `own_company_id` consistently
  - [ ] tighten writes: enforce `own_company_id` set on create for all ops entities (no silent nulls)
- [ ] **Permissions & safety**:
  - [ ] decide whether recruiters/managers can be restricted to a subset of own-companies (optional ACL)
  - [ ] add audit events for switching active own-company (who/when/from/to)
- [ ] **UX polish**:
  - [ ] “Create new own-company” action in switcher (respect plan limit; show upsell path when limit reached)
  - [ ] show active own-company label in key screens (Vacancies, Leads, Candidates)
- [ ] **Requirements/fit-check integration**:
  - [ ] ensure vacancy requirements + fit-check remain correct under scoping
  - [ ] optional: feature-flag `leads_auto_convert_on_fit_v1` (auto lead→candidate) per tenant (+ per vacancy override)

---

## Services module v2 (Catalog → Sell → Fulfill → Invoice → Collect → Analytics)

Goal: make `/app/services` a **fast operational workspace** for selling services (to clients or candidates), fulfilling them, and collecting payments via invoices — with **clear analytics** (revenue, margin, paid, overdue, pipeline).

### Current problems (why it feels “сложно и перегружено”)

- **One mega-page**: catalog + order creation + fulfillment + attachments + schedules + analytics are mixed in one screen and one mental model.
- **No clear “money loop”**: users can create orders but the **invoice/payment** connection is not first-class inside Services (even though invoices exist).
- **Analytics is partially placeholder**: labels like “Company ab12cd34”, manager labels are not human; no paid/overdue picture.
- **Hero blocks are decorative/huge**: large gradient panels take space but do not drive next action.

### Target UX (v2)

#### IA / navigation

- `/app/services` becomes a workspace with 4 focused areas:
  - **Overview**: KPIs + alerts + quick actions
  - **Orders**: list + filters + drill-down + fulfillment actions (schedule, deliver, attach)
  - **Catalog**: service definitions (pricing/costs/SLA/required docs)
  - **Billing**: invoices linked to service orders (issue → send → paid → overdue)

#### Primary workflows

- **Sell**:
  - select owner (client company / candidate / vacancy)
  - pick catalog item(s), qty, price, cost source (estimated/confirmed)
  - result: **Service order** (quote/approved)
- **Fulfill**:
  - schedule (if needed), collect attachments/docs, mark delivered
  - result: ready to invoice (or auto-create invoice if enabled)
- **Invoice & collect**:
  - create invoice from order (line items), send, track paid/overdue
- **Analyze**:
  - revenue / profit / margin
  - paid vs invoiced vs outstanding
  - top clients / top services
  - pipeline by status and aging

### Implementation plan (phased)

#### Phase A — Make analytics real and connected to money (fast win)

- [x] Improve `/api/v1/analytics/services-overview`:
  - real labels for client/candidate/vacancy + manager (no placeholders)
  - include invoice aggregates: invoiced / paid / outstanding / overdue
  - add trends: revenue vs paid, conversion to delivered, cancellation rate
  - fixed overdue-invoice aggregation bug (timezone `now` was referenced before initialization in the pre-aggregation pass)

#### Phase B — UI v2 shell + compact functional hero

- [x] Replace huge hero with compact header + KPI strip:
  - 4–6 KPIs max; each KPI is clickable (filter/drill-down)
  - quick actions: “New order”, “New service”, “Create invoice”
- [x] Split Services UI into smaller components (Overview/Orders/Catalog/Billing tabs)
- [ ] Keep existing endpoints; focus on UX and clarity first

#### Phase C — Billing inside Services (invoice-first integration)

- [x] “Create invoice from order” (1-click):
  - prefill invoice items from order items, set `service_order_id`
  - enforce recipient rules (client vs candidate) depending on business type
- [x] Payment tracking: show invoice status & paid amount inside Orders
- [x] Overdue automation: reminder + notification for overdue invoices (optional)  
  Implemented via communications scheduler invoice SLA pass:
  - env kill switch: `COMM_SCHEDULER_INVOICES_OVERDUE_SLA_ENABLED=true|false`
  - tenant settings: `Tenant.settings.invoice_overdue_sla_v1 = { enabled?: bool, overdueAfterDays?: number, createNotifications?: bool, createReminders?: bool, limit?: number }`
  - creates in-app notification `invoice_overdue` and internal reminder `type='invoice_overdue_payment'` (idempotent per invoice+assignee active reminder)

#### Phase D — Productization & analytics depth

- [x] Roles: agency vs services vs employer terminology and defaults
- [x] Data quality guidance:
  - cost coverage warnings (estimated vs confirmed)
  - missing docs/schedule alerts
- [x] Reporting exports (CSV) + saved filters

### Acceptance criteria

- Services feels like a **sales+delivery pipeline** (not a form dump).
- User can: **create catalog → sell → fulfill → invoice → mark paid** without hunting UI.
- Analytics answers in 10 seconds:
  - “How much revenue/profit last 30/90 days?”
  - “What’s paid vs outstanding?”
  - “Which services/clients drive revenue?”

---

## Live audit: Pipedrive (public sources, 2025–2026)

This section is based on Pipedrive’s official public documentation and feature pages (not guesses). It is here to make our plan implementable: we must know exactly which “Pipedrive-grade” mechanics we’re competing with.

### 1) Activities are the operational backbone (not “tasks” on the side)

Source: Pipedrive KB “Activities” (updated **Mar 11, 2026**) `https://support.pipedrive.com/en/article/activities`

What matters (patterns to copy):

- **Activities are first-class** and can be created from many contexts: pipeline cards, detail views, Leads Inbox, calendar/list, contacts timeline, mobile.
- **Linking model**: activities link to person/org/lead/deal/project; visibility depends on visibility into linked items.
- **Scheduling UX**: “Schedule an activity” shows calendar context to prevent double booking; supports guests, location, busy/free semantics.
- **Fields that power “next”**:
  - “Next activity date”, “Last activity date”
  - “Update time” used as an operational signal
- **Bulk activity creation** from list views (deals/contacts/leads/sent).
- **Emails can be added as activities automatically**, reducing reporting gaps.

HostFlow takeaway:

- We must treat “next action” as a **core entity contract**, not a reminders-only feature.
- Our recruitment equivalent must cover candidate-centric actions (call, docs request, verify doc, schedule interview, permit check, arrival planning).

### 2) Leads Inbox is a separate qualification space (pipeline stays clean)

Source: Pipedrive KB “Leads Inbox” (updated **Feb 26, 2026**) `https://support.pipedrive.com/en/article/leads-inbox`

What matters:

- Leads Inbox exists to store **unqualified leads**; conversion moves to pipeline later.
- **Lead detail is a panel**, not a full page jump: left = structured data (org/person/lead fields); right = work surfaces.
- Right side includes:
  - **Composer** (notes/activities/email/files)
  - **Focus** (upcoming activities, pinned notes, drafts, scheduled emails)
  - **History** (notes, completed activities, sent emails, files)
- Lead lifecycle features:
  - archive vs delete
  - merge duplicates
  - convert single or bulk to deals
  - bulk edit key lead fields

HostFlow takeaway:

- Our “Leads” should behave like an operational inbox with an embedded work panel and explicit conversion outcomes (services: lead→company; agency/employer: lead→candidate/vacancy context).

### 3) Email is centralized as “Sales Inbox” with visibility controls + AI helpers

Source: Pipedrive KB “Email sync” (updated **Feb 9, 2026**) `https://support.pipedrive.com/en/article/email-sync`

What matters:

- Central **Sales Inbox** to view/send/reply without app switching.
- **Linking**: conversations auto-link or can be manually linked to deals/leads/projects.
- **Visibility model**: private/shared; team account vs personal account rules.
- Inbox organization via labels/filters.
- AI helpers: suggested replies, email creation, summarization.
- Automation templates exist specifically for email (action or date based).

HostFlow takeaway:

- We already have inbox + templates/signatures, but we need the Pipedrive-grade combination of:
  - reliable linking and visibility semantics
  - “focus” layer (upcoming + drafts + scheduled)
  - explainable automation around outreach
  - optional AI layer (later phase)

### 4) Detail view: progress bar, changelog, hovercards reduce navigation cost

Source: Pipedrive KB “Detail view” (updated **Feb 9, 2026**) `https://support.pipedrive.com/en/article/detail-view`

What matters:

- Deal detail has a **progress bar** showing current stage and days spent per stage.
- **Changelog**: chronological list of all changes (default + custom fields) since creation.
- **Hovercards** for owners/people/orgs/deals reduce context switching.

HostFlow takeaway:

- For recruitment, we need stage-time visibility and a changelog/timeline that is not “optional”.
- Hovercards are a cheap but high-impact speed feature for daily ops.

### 5) Insights: dashboards + goals + reports (with sharing and AI report generation)

Source: Pipedrive KB “Insights feature” (updated **Jul 15, 2025**) `https://support.pipedrive.com/en/article/insights-feature`

What matters:

- Three pillars:
  - **Reports** (visual builder + filters)
  - **Dashboards** (drag/drop of reports/goals)
  - **Goals** (deal/activity/forecast)
- Share dashboards via public link (view-only).
- AI-assisted report generation exists (prompt → report).
- Visibility/permissions are explicit and tied to data visibility.

HostFlow takeaway:

- Our reporting must become operational and drill-down capable; goals should include “activity/next action compliance” and “readiness/compliance” metrics.

### 6) LeadBooster: lead-gen is a product surface, not an integration footnote

Source: Pipedrive KB “LeadBooster add-on” (updated **Dec 11, 2025**) `https://support.pipedrive.com/en/article/leadbooster-add-on`

What matters:

- Lead generation is packaged: web forms, chatbot, live chat, prospector.
- All feeds into Leads Inbox.

HostFlow takeaway:

- We don’t need to copy Prospector, but we must treat “lead source → inbox → qualification → conversion” as a coherent product surface.

---

## How HostFlow becomes “Pipedrive+” (explicit deltas)

### Copy (parity) targets

- **Activities system**: unified activity types + schedule UX + bulk creation + link/visibility semantics.
- **Inbox panels**: lead/candidate/communications side panel with Composer/Focus/History structure.
- **Detail view utilities**: changelog + hovercards + stage-time visualization.
- **Reporting shell**: dashboards + reports + goals (with drill-down).

### Surpass (recruitment-native advantages)

- **Readiness/compliance-first** reporting and automation:
  - missing docs, expiring soon, compliance blockers
  - time-to-ready and readiness score distribution
- **Next action enforcement** tied to stage requirements:
  - “no next action” is a managed operational risk
  - stuck detection and recruitment-specific playbooks
- **Document intelligence** integrated into the daily command center, not a separate module.

---

## Backlog additions (from live Pipedrive audit)

- [x] **R1.4 Lead/Candidate side panel: Composer + Focus + History** (Pipedrive Leads Inbox pattern — implemented for Leads list with reminders-based Composer/Focus and metadata History)
- [x] **R1.5 Hovercards** for candidate/company/user to reduce navigation cost
- [x] **R1.6 Stage-time visualization** (days in stage) on candidate/vacancy pipeline entities
- [x] **R1.7 Candidate card documents UX v2 (two-layer model)**  
  Implemented in candidate card as:
  - Right-rail **Quick Documents** panel for fast status + blockers + one-click upload/open.
  - Preserved full **Document Center** access (not removed): opens full candidate documents workspace for approve/reject/edit/replace/delete, upload link generation, and profile export.
  - Document Center drawer header now exposes explicit quick actions: `Upload link`, `Download candidate profile`, `Refresh`, plus inline display of the latest generated upload link + expiry.
  - Pipeline gating tightened: candidate stage progression is blocked not only for missing/problematic docs, but also for uploaded-yet-unverified (`in_progress`) required docs.
  - `Request documents` next action now also generates candidate upload link; once candidate has uploaded required docs and they remain unverified (`in_progress`), system auto-creates follow-up verification activity (`Verify uploaded documents`).
  - Candidate card rail rebalanced for operators: activity moved to right rail (up to 5 visible with scroll), messages isolated into its own widget, edit control paired with red delete action, edit action auto-scrolls to candidate data section, and override reason switched to predefined dropdown options.
- [x] **R2.3 Activities bulk creation** from list views (Candidates bulk action “Create activity” → creates reminders in bulk via `POST /api/v1/reminders/bulk`)
- [x] **R3.3 Goals system** (activity compliance + readiness) and dashboard sharing (added `/api/v1/analytics/goals` + Overview block; public share endpoint `/api/v1/public/goals/{share_token}` when tenant sharing is enabled)
- [x] **Activity templates/types** (Call, Email, Document request, Follow-up): quick-type buttons in bulk-activity modal (Candidates + Leads); reminder `type` sent to API; defaults for title and reminder offset per template

---

## Implementation plan (next milestones to reach “Pipedrive+”)

This is the concrete plan that turns the “deltas” above into shippable increments. It is written to be executable: each item has a result, scope boundaries, and acceptance signals.

### Milestone M1 — Activities become first-class (beyond reminders)

**Goal**

Make “activities” a core operational surface like in Pipedrive: schedule UX + calendar/list views + consistent linking, so “next action” is not a special-case reminder.

**Scope**

- Introduce an `Activity` entity (or evolve `Reminder` into an activity model) with:
  - `type`, `title`, `due_at`, `duration_minutes`, `status` (planned/done/canceled), `owner_id`
  - linking: `entity_type` + `entity_id` (lead/candidate/company/vacancy) and optional `company_id`
  - source: manual / automation / communication-sync
- UI surfaces:
  - Create activity from list row, side panel, and detail pages
  - Activity list view with filters (type, owner, status, due window)
  - Calendar view (week/day) with conflict hints (at least for same owner)
- Bulk creation uses templates as defaults (already done) and writes activities

**Acceptance**

- “Next action” is derived from the next planned activity (not a reminders-only shortcut).
- Activity surfaces exist for Leads and Candidates and are consistent (same filters, same quick-create).
- We can reliably answer: “what’s next”, “what’s overdue”, “what got done last week” per owner and per entity.

### Milestone M2 — Leads inbox becomes a true qualification workspace

**Goal**

Match the Pipedrive Leads Inbox pattern: left = structured lead fields; right = Composer/Focus/History, with explicit conversion outcomes and bulk ops.

**Scope**

- Leads UI parity upgrades:
  - Side panel “Focus” that highlights: next activity, overdue count, last activity, owner, SLA nudges
  - Bulk edit key lead fields + bulk status change (keep enforcement on stage change only)
  - “Convert” actions: lead → company/client + optionally create first vacancy/candidate context (per tenant mode)
  - Duplicate detection and merge (basic: email/phone + name heuristic; ops review UI)
- Backend:
  - conversion endpoints with audit logs and idempotency
  - duplicate candidates/companies/leads resolution strategy documented here

**Acceptance**

- Qualification loop is fast: lead → next activity → convert/archive with minimal navigation.
- Conversions are audited and reversible where safe (soft delete / archive, not hard delete).

### Milestone M3 — Reporting: operational + drill-down + benchmarks

**Goal**

Reach “Insights-grade” reporting: operational dashboards that answer “what’s broken now?” and “what changed over time?”, with drill-down and shareable views where appropriate.

**Scope**

- Add report primitives:
  - saved filters (shareable internally)
  - time-series for: created, converted, stage transitions, activity completion rate, SLA incidents
  - cohort-style funnels for recruitment: lead→processed→candidate stages, time-to-ready distributions
- Drill-down paths:
  - every top KPI widget links to an item list filtered to the underlying cohort
- Goals:
  - per-team/per-owner activity compliance + readiness compliance goals
  - weekly progress and alerting (in-app)

**Acceptance**

- Every “red widget” can be explained by a list of items (no dead-end dashboards).
- Ops can answer in < 60 seconds: “why did our throughput drop this week?” using built-in slices.

### Milestone M4 — Integrations & lifecycle hygiene (minimum viable “real CRM”)

**Goal**

Cover the boring-but-critical CRM mechanics that drive retention: import, dedupe, auditability, and operational guardrails.

**Scope**

- Import/export:
  - CSV import for leads/candidates with mapping and validation
  - export current filtered lists (CSV)
- Lifecycle hygiene:
  - archive vs delete semantics for all major entities
  - strict audit log coverage for critical mutations (owner/stage/status/links)
- Notifications:
  - consistent notification taxonomy and user preferences (mute types, digests)

**Acceptance**

- A team can migrate in and keep data clean over months without “manual spreadsheets”.

---

## Landing (public) audit + plan (make it a selling landing)

Current public entry is `hostflow-frontend/src/pages/public/CrmLandingPage.tsx` (routes `/` and `/pricing` for non-auth users). It already has hero, pricing, comparison, objections, FAQ, audience, final CTA, and CTA tracking, but it is missing key conversion mechanics: strong proof, product visualization, a focused narrative per persona, and a measurable funnel.

### Landing vNext — positioning & narrative

- **Clarify 1 primary ICP per page**: keep `/` focused on “recruitment operations CRM” (managers + ops); move secondary narratives to dedicated use-case pages (already present) and link them with stronger “choose your path” blocks.
- **Make the promise measurable**: replace generic “Launch in minutes” with quantified outcomes we can defend (e.g. “reduce ‘no next action’ to < 5%”, “cut time-to-ready by X%”) once reporting is in place.
- **Differentiate vs Pipedrive** (recruitment-native): readiness/compliance + document control + SLA nudges as primary differentiators.

### Landing vNext — sections to add/upgrade (UI/UX)

- **Hero**
  - Add 1–2 product visuals (screenshots / short looping video) showing: Leads inbox panel + next action + ops dashboard drill-down
  - Add trust strip (logos / “used by” once available) or “early access” proof alternative (numbers, case study snippets)
- **Problem → solution**
  - Insert a short “Before/After” block: chaos (spreadsheets, missed follow-ups) → HostFlow command center (next action, SLA, compliance)
- **Feature proof blocks (3–5)**
  - Each with: headline, 1 sentence outcome, visual, and “See example” link to existing guide pages
- **Social proof**
  - Testimonials/case studies section + lightweight “results cards”
- **Pricing**
  - Add FAQ below pricing that answers purchase friction: migration, seats, security, cancellation
  - Make CTA consistent: primary CTA = “Start trial”, secondary = “Book demo” (if we support it)
- **Conversion surface**
  - Add sticky CTA on scroll (desktop) + bottom mobile CTA
  - Add “Request demo”/“Talk to us” capture (email) if self-serve is not enough

### Landing vNext — tracking, experimentation, and SEO

- **Funnel tracking**
  - Define events: `landing.view`, `cta.click` (already), `signup.view`, `signup.submit`, `onboarding.complete`
  - Track CTA placement keys: hero/pricing/final/sticky; and page variants `/` vs `/pricing`
- **A/B readiness**
  - Simple variant flag (query param or remote config) to test hero copy + CTA + visual
- **SEO**
  - Ensure each public page has: unique title/description, canonical, structured data (already), internal linking map, and keyword-targeted headings
  - Add comparison pages into a “Learn” hub section and improve cross-linking with clear next steps

### Landing vNext — acceptance (what “better landing” means)

- **Conversion metrics**
  - Baseline and target: \(CVR_{landing \to signup}\), \(CVR_{signup \to onboarding\_complete}\)
  - Track by source/UTM and by locale
- **Performance**
  - p95 LCP < 2.5s on mid-tier mobile (or explicit budget we set) and no heavy JS regressions
- **Quality**
  - Content is consistent with product truth (no claims we can’t demonstrate inside the app)
