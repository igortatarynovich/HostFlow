# HostFlow SSOT (Single Source of Truth)

This file is the **only source of truth** for:

- current product readiness status
- remaining work (backlog)
- evidence of completion (kept inline here)

Rules:

- **All** progress updates and status changes go to this file.
- No new “tracker” markdown files should be added elsewhere.
- Supporting docs like specs/blueprints may exist, but they are **not trackers**.

### Working from any git branch

`docs/SSOT.md` is **one file in the repo** — the same path on **every** branch. Treat it like shared code: edit it on your feature branch, merge/rebase as usual; there is no separate “SSOT branch” or secret tracker.

- **Wording:** describe **product/code state** in branch-neutral terms (what is shipped, what is open, which paths). Avoid “only on `feature/…`” unless you also state whether it is merged to the integration branch you care about.
- **Backlog / checkboxes:** open work is **global** to the product, not owned by a branch. Add or tick items here instead of leaving status only in PR descriptions.
- **Merge conflicts:** resolve by **keeping both** substantive updates when possible (combine backlog lines, preserve distinct `[ ]` items). Do not drop the other side’s factual changelog or open tasks without reading them. Prefer **dated** statements over “latest wins” guessing.
- **Change log:** **append** new dated bullets; do not rewrite or delete historical entries to “clean up” during a merge — that breaks auditability across branches.
- **Code pointers:** use **stable paths** (e.g. `hostflow-frontend/src/...`) so the doc stays valid after merges; avoid line-number-only references when the surrounding section is volatile.

---

## Requirements sources (non-tracker)

- Product blueprint (workflow/UX principles): `docs/pipe.md`
- Landing/SEO/design direction: `docs/pipedesign.md`
- Module specs (reference): `docs/specs/**`

---

## Current status (2026-03-22)

### Product readiness

- **Overall**: **READY**
- **Primary remaining release-pass**: **production scenario A (`services`) on tenant `victoria-services`**

### Evidence (latest)

- **Party + client workspace + services scoped URLs** (see section *Party model + client workspace + services deep links* below): shipped in app code; treat as canonical CRM/services UX for client companies until SSOT says otherwise.
- **Frontend static gate**: `npm --prefix hostflow-frontend run qa:static` → **PASS**
- **Production `vite build`**: default `npm run build` sets **`HOSTFLOW_LOW_MEM_BUILD=1`** + **`NODE_OPTIONS=--max-old-space-size=2048`**, no `experimentalMinChunkSize`. **`manualChunks`** only isolates **`@tabler/icons*`** (safe for React). Lazy bundles: CRM split into **`routeBundleCrmCore` / `routeBundleServices` / `routeBundleCrmMore`** plus other `src/app/routeBundles/*` — снижает пик RAM при `rendering chunks`. Для мощной машины: `npm run build:fast` (без low-mem I/O cap).
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
  - Shell layout (Topbar/Sidebar/Workspace); empty states; global search (candidates/companies/documents).
  - Next action: reminders + leads follow-up; candidates **list preview** (work panel) with Composer/Focus/**History** (`GET /candidates/{id}/timeline`); **`/app/candidates/no-next-action`** view.
  - Document intelligence + compliance rulesets; stage-aware pipeline gates and overrides (see **§3) Stage-based pipeline blockers** below).
- **Still open vs pipe.md (tracked in Backlog)**
  - **Command center v2** (R1.5): opinionated list defaults, tab-less card timeline, work-panel API — preview is triage, not full card parity.
  - **Perf evidence** vs aggressive numeric targets in `pipe.md` (baseline exists; formal budgets — see R4).

### `docs/pipedesign.md` (landing/SEO/design system)

- **Implemented / aligned**
  - Public routes, SEO meta (`useSeoMeta`), sitemap in static gate.
  - **Tokens:** Tailwind `brand.*` + typography aligned to `pipedesign.md` (primary `#3FA3A8`, accent `#2E6F74`, section bg `#F4F8F9`; Inter canonical). Further drift checks = optional visual regression pass.

---

## Backlog (what’s left)

### Release-pass

- [ ] **Production run: Scenario A (`services`) on `victoria-services`**
  - Definition: execute run-sheet for scenario A in production and capture final PASS evidence.
  - Output: inline evidence block in this SSOT (timestamp, tenant, steps, result, and pointers to logs/screens where applicable).

### Product / architecture gaps (summary)

- [ ] **UOS / IA:** close gaps in *Operating model* + *Screen-by-screen* (unified Inbox incl. email, Unlinked queue, Tasks sort-by-SLA, escalation, client pipeline auto-activities, notification badge tiers, optional default **Tasks** landing, full target sidebar) — see gap table under **Unified Operations System**.
- [ ] **Candidates command center v2** (R1.5 below): efficiency-first table + card; product sign-off on “daily loop” vs `pipe.md`.
- [ ] **Services module v2** (R3.3): sell → fulfill → invoice → collect + analytics.
- [ ] **Performance:** extend evidence beyond current baseline (R4) if `pipe.md` numeric targets become contractual.

### Marketing/SEO/design vs `pipedesign.md`

- [x] **Design tokens** baseline aligned (see Audit section).

### Hygiene / repo policy (must stay enforced)

- [ ] Ensure **no** `.venv/` content is tracked by git
- [ ] Ensure **no** `node_modules/` content is committed
- [ ] Keep artifacts (screenshots/json) out of git; store externally if needed

**Detailed tickets:** *Expanded backlog (R0–R4)* later in this file.

---

## Change log (SSOT-managed)

- `2026-03-22` (**Product / engineering**): Party + client workspace + services deep links; **UOS v1** — Tasks hub, Inbox context rail + linking, `/activities` + SLA projection, Topbar notification groups, `uos_auto_activities` + inbound reply task (+ refresh/dedupe). SSOT: Operating model + Screen-by-screen architecture. **Email:** `incomingEnabled` wired from setup; inbox banner + sync; threads `channel=email` → `/app/email` (not Messages); IMAP default `UNSEEN`.
- `2026-03-22` (**SSOT maintenance**): Deduplicated UOS (single nav/UX pointer to Screen-by-screen), compressed shipped Steps 1–7 + M1–M4 into snapshots, merged contradictory pipe.md/preview backlog items, collapsed stage-gate implementation treatise into shipped summary + code pointers, removed duplicate Pipedrive-audit checklist, aligned Roadmap with Expanded backlog.
- `2026-03-22` (**SSOT policy**): Added **Working from any git branch** — same `docs/SSOT.md` on all branches; neutral wording; merge-conflict + append-only changelog rules.
- `2026-03-17`: Consolidated SSOT created; single tracker policy.

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

- **Core CRM loop:** candidates, companies, vacancies, leads, documents, communications, Tasks (`/app/tasks`), billing — wired with permissions and module gating.
- **Differentiator:** document/requirements engine, readiness meta, rulesets + versions UI.
- **Operator UX:** empty states, global search, `qa:static` gate; many Pipedrive-parity items shipped — see **Expanded backlog** `[x]` rows and **Party model** section.

---

## Where we are not yet “Pipedrive-level” (gaps & problems)

This list is written as “problem → why it matters → what we do”.

### 1) Candidates “command center” vs `pipe.md`

**Shipped (v1):** list **work panel** (preview) with next action, docs summary, **History** = unified **timeline** API (`GET /candidates/{id}/timeline`), handoff shortcuts; **`/app/candidates/no-next-action`**.

**Remaining:** **R1.5** — v2 table + card (timeline in rail, no tab dead-end, opinionated quick views, optional work-panel API). **P0:** preview **click-blocker** fix (see R1).

### 2) Next action + SLA (leads + candidates)

**Partially shipped:**

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

### 3) Stage-based pipeline blockers (documents & gates) — **shipped**

**Principle:** stage-scoped requirements (not global doc blocking on `new`); overrides with approval + audit; non-overridable legal types; vacancy + contact-attempt gates; soft vs hard doc stages.

**Code entry points:** `candidateStageDocPolicy.ts`, `stageOperationalHints.ts`, `candidate_doc_pipeline_guard.py`, `pipeline_overrides_*`, `hiring_pipeline_gates`, **`GET/PATCH .../hiring-pipeline-gates`**.

| Hiring OS plan area | Status |
|---------------------|--------|
| §1–2 Stage-based doc blockers | Done |
| §3 Gates in data (`hiring_stage_gates_v1`) | Done; hints still mostly code (`stageOperationalHints.ts`) |
| §4–6 Stage panel + next action | Done |
| §7–11 Overrides / audit / badges | Done |
| §12–13 Non-overridable + soft stages | Done |

**Stretch:** tenant-editable **stage → hints** matrix; richer custom requirements beyond gates.

### 4) Automation explainability

**Shipped:** automation log API/UI + DB rules builder + triggers (see R2.1–R2.2). **Remaining:** deeper “why” on every surface (e.g. comms threads), richer actions, guardrails.

### 5) Operational reporting

**Shipped:** ops counters + drilldowns, stage metrics, goals/share (Overview + public share). **Remaining:** **R3.3** Services v2 analytics; optional extra widgets per `pipe.md`.

### 6) Performance governance

**Shipped:** perf events, baseline + budgets on Overview, breach signals (R4). **Remaining:** expand coverage / CI if product requires stricter `pipe.md` numbers.

---

## Roadmap (phases R0–R4)

Phases map 1:1 to **Expanded backlog** below. **R1** preview/timeline/next-action v1 items are largely **done**; focus shifts to **R1.5**, **R3.3**, **release-pass R0**.

---

## Expanded backlog (R0–R4)

`[x]` = shipped; `[ ]` = open. (Pipedrive-audit extras — hovercards, stage-time, documents rail v2, bulk activities, templates — are covered by the `[x]` rows in **R1–R2** and candidate modules.)

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
 **Implemented so far:** gated `pointer-events` on the right preview rail (off-screen click-through), ensured the table reserves space for the fixed rail, and removed horizontal negative margins when the rail is open to prevent any visual/hit overlap.

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
  - Add “Row quick actions” (stage dropdown, reminder quick add, open card) with hover-only where appropriate; list row currently ships **Open / Preview** under the name (see implementation notes).
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
  - create a reminder OR start handoff in **≤ 2 clicks** without leaving the page; **stage / journey** on the **full card** (preview stays lightweight by design).
- On CandidateCard:
  - user can see: stage, docs readiness, next action, and last 10 events **without switching tabs**.
- Timeline:
  - no dedicated timeline tab exists; timeline is visible in right rail and expandable.

**Implementation notes (where to change)**

- **Frontend:** `Candidates.tsx` + `hostflow-frontend/src/modules/candidates/components/*` — work panel hooks (`useCandidatesWorkPanel*`), left rail (`CandidatesLeftRailPanel`), keyboard nav, insights hero; list preview = **triage only** (no stage **PATCH** from rail — `app.candidates.preview.stage_scope_hint`). **Candidate card:** `CandidateCard.tsx` — remove dedicated **Timeline** tab when v2 ships; share timeline component with rail.
- **Backend:** list insights aggregate `GET /candidates?include_insights=true`; extend **`/candidates/{id}/timeline`**; optional single **work panel** payload to cut N+1.

### R2

- [x] **R2.1 Automation log (rule fired → actions)** (ActivityLog-based; reminders emit `automation.*`; added API `/api/v1/automation-log` + UI `/app/automation-log`)
- [x] **R2.2 Minimal rules builder (candidate created/stage changed/doc expiring/lead processed)** (DB-backed rules + API `/api/v1/automation-rules` + UI `/app/automation-rules`; execution wired for `candidate.created`, `candidate.stage_changed`, `lead.processed`)
  - Operational hardening:
    - `GET /api/v1/automation-rules` now degrades safely to empty list if `automation_rules` table is missing (no 500 on page open).
    - Added deploy/dev command: `make ensure-automation-schema` to bootstrap `automation_rules` in environments where Alembic is unavailable.
    - Recommended rollout order:
      1) `make upg` (preferred, full migrations),
      2) fallback `make ensure-automation-schema` (SQLite/dev safety net),
      3) smoke check `GET /api/v1/automation-rules` returns `200` with `items`.

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
- [x] Deep links on Services: URL sync for `tab`, `order_id`, `company_id` (scoped orders + banner + client card round-trip)
- [ ] Keep existing endpoints; focus on UX and clarity first (endpoints extended where needed: `include_metrics`, company filters — see Party section)

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

#### Catalog usage metrics (API + UI)

- `GET /api/v1/services?include_metrics=true` adds per–catalog-row aggregates from `service_items` ⨝ `service_orders`:
  - **`metrics_orders_count`**: `COUNT(DISTINCT order_id)` where order status ≠ `cancelled` and line status ≠ `cancelled`
  - **`metrics_revenue_completed`**: `SUM(line.amount)` where order status = `completed` and line status ≠ `cancelled`  
  (numeric sum only; mixed currencies on one tenant are summed as numbers — documented on the schema.)
- HostFlow UI: **Services → Catalog** requests metrics by default; table columns **Orders** / **Revenue (completed)**.

---

## Party model + client workspace + services deep links (implemented 2026-03-22)

Single **Party** record for a client lives in **`companies`** (no duplicate client/employer tables). Recruiting and **additional services** revenue attach to the same company where applicable.

### Data model (Alembic / ORM)

- **`companies`**: `party_entity_type` (`company` | `person`), `party_business_roles` (`employer` | `service_client` | `both`), `client_stage` (pipeline codes, e.g. `new_lead` … `lost`), `client_source` (free text).
- **`leads`**: `lead_type`; `company_id` required when type implies candidate-employer link (validated in API).
- **`service_orders`**: canonical statuses `draft`, `confirmed`, `in_progress`, `completed`, `cancelled`, `on_hold`; optional `start_date` / `end_date`; legacy status values normalized at API boundary where needed.
- **`invoices`**: optional `service_order_id` → `service_orders` (when present).

### API — companies list & metrics

- `GET /api/v1/companies` supports filters: `party_business_roles`, `client_stage`, `owner_user_id`, plus existing list filters.
- `GET /api/v1/companies?include_service_metrics=true` adds per company (where implemented): **`service_active_orders`**, **`service_revenue_completed`** (from service orders for that `company_id`).

### Frontend — client company card (`/app/clients/:id`, not operating profile)

- **Workspace tabs** (query param **`ctab`**; default = overview when omitted):
  - **`overview`**: relationship summary, vacancies widget, blocking service orders widget.
  - **`orders`**: **Additional services** orders for this company (`GET /service-orders?company_id=`) + legacy **CRM / staffing order lines** editor (stored on company profile).
  - **`invoices`**: `ClientInvoicesBlock` (list/create for this `company_id`).
  - **`activity`**: created/updated metadata + shortcuts (invoices list with `company_id`, **Services** with `company_id`, vacancies list with `company` filter).
  - **`profile`**: full company editor — base & Party fields, billing, contacts, legal, contracts, document policies, system block, etc.
- Deep links **`?section=legal|billing|bank_accounts|branding`** force **`ctab=profile`** and scroll to matching `section-*` anchors.
- i18n: `app.companies.party.*`, `app.companies.client_stage.*`, `app.companies.detail.workspace.*`, catalog metric labels under `app.services.catalog.table.*`.

### Frontend — Services workspace (`/app/services`)

- **`?tab=`** (`overview` | `orders` | `catalog` | `analytics` | `billing`) and **`?order_id=`** are read from the URL on load so shared links open the right tab and selected order.
- **`?company_id=<uuid>`** (with **`tab=orders`** in links from CRM):
  - applies **client drilldown** (company-scoped order list),
  - prefills **new order** owner as that company,
  - shows a **scope banner** (name from `GET /companies/:id`) with link back to **`/app/clients/:id`** and **Clear filter** (removes `company_id` from the query),
  - clearing order-list drilldown to “all” while `company_id` is present also strips **`company_id`** from the URL to avoid hidden filters.
- Client card **Orders** panel and **Activity → Services** use these query params consistently.

### Spec cross-reference

- Additional services domain tables and flows: `docs/specs/modules/additional_services.md` (status enum names in prose may lag; **SSOT + migration + API** win for canonical enums).

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

## Unified Operations System (target architecture)

**Status:** product north star — not fully implemented in navigation/data model yet.  
**Intent:** one operational center for attention, actions, and money — not a pile of disconnected screens.

### Core model (three primitives)

1. **Activity** — what must be done (SLA is a property of Activity, not a separate domain object).
2. **Conversation** — where the interaction lives (replaces fragmented “Messages” + “Email” mentally; may remain multiple channels technically).
3. **Notification** — what demands attention now (no full-page module; top bar: badge + grouped dropdown).

**Calendar** is a **view** over Activities (meetings, calls, deadlines), not a second source of truth.

### Navigation (shipped vs target)

- **Target IA** (full sidebar: Dashboard, Core work, Business incl. Vacancies/Invoices/Documents/Leads, System Automations, unified Inbox, …): **Screen-by-screen system architecture** → § *Target sidebar + shell* + consolidation table.
- **Shipped (v1):** **Tasks** `/app/tasks`; **Inbox** → `/app/messages`; **email** still **`/app/email`**; `/app/planner`, `/app/reminders`, `/app/activities` → redirects; **Calendar** `/app/calendar`; **SLA** incidents page; **Overview** + **Leads** remain in nav; Topbar **notification groups**.
- **Still target:** one **Communication Center** shell for messages+email; availability/time-off not top-level daily modules.

### Activity types (canonical)

`call` | `message` | `email` | `meeting` | `task` | `follow_up` | `document_request`

**Fields (target):** `related_to` (candidate | client | order), `assigned_to`, `status`, `due_date`, `sla_due_at`, `sla_status`, `priority`, plus provenance (manual / automation / comms).

### Per-surface UX

Target contracts (filters, columns, control room): **Screen-by-screen** § *Screen contracts (summary)*. **v1:** Messages page matches a **subset** (3-col + link rail); Tasks = my/team + SLA chip + filters; SLA page not yet full “Activity-derived control room” (see gap table).

### Quick actions (everywhere)

On Candidate / Client / Order surfaces: Call, Message, Request document, Create task, Schedule meeting — **all create Activities** (same pipeline as Tasks).

### Automation (critical)

System-generated Activities examples:

- Candidate created → task: call candidate.
- Inbound message → task: reply.
- Order created → task: confirm.
- Invoice created → task: follow payment.

### UOS Steps 1–7 — v1 shipped (2026-03-22)

**Reminder** = persisted Activity; **`GET /activities`** + **`assignee_scope`**; Inbox **3-column** + link company/order; IA **redirects** (planner/reminders/activities → calendar/tasks); **Tasks** hub; **`sla_due_at` / `sla_status`** + UI chip; Topbar **notification groups**; **`uos_auto_activities`** + inbound **`uos_inbound_reply`** (dedupe/refresh). **Remaining work** = *Honest gap* table + Screen-by-screen rollout (not re-listing steps here).

### Current code pointers (today)

- Nav items: `hostflow-frontend/src/app/routes.tsx` (`NAV_ITEMS`), shell grouping: `hostflow-frontend/src/components/nav/Sidebar.tsx`.
- Messages / email pages: `CommunicationsMessagesPage`, `CommunicationsEmailInboxPage`; work queue: `RemindersPage` mounted at **`/app/tasks`**; legacy `ActivitiesPage` component unused by router (redirect only); `CommunicationsPlannerPage` retained in bundle, route redirects to calendar.
- SLA: `CommunicationsSlaIncidentsPage`, settings `CommunicationsSlaSettingsPage`.

### Relationship to Pipedrive+ milestones

**M1–M4** are reference labels; much of **M1/M2/M3** scope is already in production (see **Expanded backlog** `[x]`). **M4** import/prefs/dedupe still open in places — see milestone snapshot below.

### Operating model — full system interaction logic (target, production-ready)

**How work is driven** and **how revenue path ties together**. **UOS Steps 1–7 v1** shipped; gaps = table below + IA in *Screen-by-screen*.

**North-star principle:** the system is judged by **actions enforced**, not only by data stored. The baseline chain:

`Event → Activity → SLA → Notification → Action → Outcome → Money`

**Four cores (conceptual):**

1. **Entity** — Candidate, Client (company), Order, Invoice, …
2. **Conversation** — thread + channel (messages, email as integrated surface over time)
3. **Activity** — persisted work item with owner, due, provenance (today: **`Reminder`** / activities API)
4. **Control** — SLA + notifications + escalation policies

**Event → Activity (target rule):** meaningful events (message, new candidate/client, order, invoice, stage change, …) should **materialize or refresh** an Activity so the queue never depends on the manager “remembering”.

**Activity (target invariant):** always has **assignee**, **deadline**, and **SLA projection** (OK / warning / breach) where the type is time-bound.

**If Activity is not completed:** SLA warning → breach → **notification** → **escalation** (per tenant policy); surfaced in **Tasks**, **SLA dashboard**, and **bell**.

**Reference workflows (targets):**

- **Lead / candidate:** create entity → auto Activities (e.g. call, intro) with **short SLA**; breach surfaces in Tasks + notifications.
- **Manager opens Tasks:** sees overdue, SLA risk, today — **work is assigned**, not discovered by browsing Candidates/Clients/Orders (those screens support execution, not queue discovery).
- **Completion:** mark Activity done → **next Activity** / pipeline update where rules apply.
- **Inbox:** not “just chat”; each dialog should be **linked** to an entity, have **ops/SLA state**; message → conversation → **reply Activity**. **Unlinked** conversations are a **first-class queue** until linked (target UX).
- **Order → money:** order → Activities (confirm, assign, schedule, …) → delivery → invoice → payment follow-up Activity; unpaid → SLA → notification → escalation.
- **Client:** not only a directory — **pipeline + Activities + SLA** (e.g. “offer sent” → follow-up in N days).

**SLA (target):** levels **OK / warning / breach** drive **sort order** (hotter = higher), notifications, escalation — not only color.

**Notifications (target attention model):** tiered **CRITICAL** (SLA breach, unpaid invoice) / **HIGH** (overdue tasks, waiting reply) / **NORMAL** (new lead, new message); **badge** emphasizes critical+high; dropdown shows full feed.

**Automation (target):** prefer **behavior** over screens — rule engine expresses: if *event* then *create/update Activity* with *SLA* (today: **`uos_auto_activities`**, communications scheduler, `automation_rules`, comms SLA — **converge** toward one explicit policy model).

**Honest gap — target vs shipped (snapshot 2026-03-22):**

| Target | Today |
|--------|--------|
| Every meaningful event → Activity | **Partial:** candidate, service order, invoice, inbound message (thread) via **`uos_auto_activities`**; not exhaustive (e.g. arbitrary stage changes, all email-only flows). |
| Unified Inbox including email | **Partial:** **Messages** = non-email; **email** = `/app/email` (by design until unified thread list). |
| Inbox “Unlinked” queue + mandatory link | **Partial:** linking panel **v1** (candidate, company, order meta); no dedicated **Unlinked** filter/work queue. |
| Tasks sorted by SLA severity first | **Partial:** SLA **chip** + groups; not full **global sort-by-breach** as primary UX. |
| SLA breach → unified escalation from Activities | **Partial:** comms SLA + reminders; **one** cross-domain escalation story still **M1/M4**. |
| Client pipeline auto Activities | **Light / missing** as a systematic layer (vs candidate/order/invoice hooks). |
| Notification badge = critical+high only | **Partial:** Topbar groups **v1**; badge policy not fully aligned to CRITICAL/HIGH spec. |
| Default post-login = Tasks | **Not yet** (still `/app/overview` optional). |

**Intended shift:** from “screens for each module” to **operations control** — the system proposes and pressures work; the manager **executes** the queue.

### Screen-by-screen system architecture (target, final)

This subsection is the **IA + screen contract** companion to *Operating model* above: same north star (**process engine** for recruitment, clients, services, money), but **route-by-route** so engineering and design do not ship unrelated pages.

**Principle:** HostFlow is not a CRM directory or a pile of forms — it is a **process engine**. The universal spine:

`Event → Activity → owner → due / SLA → surfaces in Tasks / Inbox / Calendar → pipeline advances`

**Four cores (IA-facing names):**

1. **Entity** — Candidate, Client/employer (party), Vacancy, Order, Invoice (and related).
2. **Process** — pipeline stage, blockers, next action, overrides/approvals.
3. **Work** — Activities, Inbox, Tasks, Calendar (Calendar = **view** over timed work, not a second truth).
4. **Control** — SLA, notifications, approvals, automation.

#### Consolidation — remove duplicate “daily” modules

**Problem (to eliminate):** Messages, Email, Planner, Reminders, Availability, Time off, Activity, and Calendar partially duplicating planner each feel like separate products.

**Target:** absorb into **Inbox**, **Tasks**, **Calendar**, **SLA**, and **settings** (user/team scheduling context). Standalone routes may remain technically but **must not** be first-class daily nav.

| Remove as first-class module | Becomes part of |
|-----------------------------|-----------------|
| Planner, Reminders, Activity list | **Tasks** (+ Calendar as time view) |
| Messages + Email as peers | **Inbox** (Communication Center) |
| My / team availability, time off | **User profile**, **Calendar** filters, team workload — not top-level ops nav |
| Weak standalone “SLA incidents” feel | **SLA dashboard** as **control room** over Activities |

#### Target sidebar + shell (canonical)

**Sidebar — Core workspace**

1. Dashboard  
2. Inbox  
3. Tasks  
4. Calendar  
5. SLA  

**Sidebar — Business**

6. Candidates  
7. Clients  
8. Vacancies  
9. Orders  
10. Services  
11. Invoices  
12. Documents  
13. Leads  

**Sidebar — System**

14. Automations  
15. Settings (sub-areas: communication, workspace, users/roles; profile entry)

**Top bar:** global search, notifications, **quick create**, workspace switcher, user menu.

**Quick create (top bar):** Candidate, Client, Vacancy, Order, Task, Meeting, Invoice.

**Reconciliation:** § *Navigation (shipped vs target)* above is the **minimal shipped slice**; this subsection is the **full target IA**. Until shipped, some routes stay combined (e.g. **Finance** vs **Invoices**) — track in top **Backlog**.

#### Screen contracts (summary)

- **Dashboard** — operational summary in ~5s: what is on fire, where money is, bottlenecks, first action. Sections: my urgent work (overdue, SLA breach, waiting replies, unpaid due), recruitment + client/revenue pipeline summaries, KPI cards, quick actions, recent activity / approvals / expiring docs / overdue invoices.
- **Inbox** — single **Communication Center** (replaces separate Messages vs Email mental model). Three columns: list + filters (**Unassigned**, **Waiting reply**, **New**, **SLA risk**, **Closed**, **Linked / Unlinked**), thread + notes, **control panel** (linked entity, owner, status, SLA, quick actions: link, task, docs, order, schedule, escalate, close). No separate “email app” vs “messages app” for daily work.
- **Tasks** — **primary execution engine** (not “reminders”). Filters: My, Team, Today, Overdue, Upcoming, High priority, SLA risk. Table: type, title, entity, stage/context, assignee, due, SLA, priority, status (`planned` / `in_progress` / `waiting` / `done` / `cancelled`). Actions: complete, reassign, snooze, open entity, escalate; optional drawer for quick creates.
- **Calendar** — **only** a view of Activities (meetings, calls, deadlines, timed tasks, time off). Filters by user, type, entity, priority; scheduling respects availability. **Does not** duplicate Tasks as a second queue.
- **SLA dashboard** — **control room** for ops/leads: overdue, at-risk, breached conversations, unassigned urgent, ignored critical; KPIs; table with actions (assign, reassign, escalate, resolve, open entity).
- **Candidates list** — flow control, not a dumb table: table + pipeline counters + saved filters; columns include next action, blocking, docs, time in stage; **right preview** with summary, blockers, quick actions.
- **Candidate card** — hero (stage, next step, move forward/back, override blocker); main: key info, timeline; sticky rail: next action, documents, blockers, quick actions, notes, related comms; tabs Overview / Documents / Services·Orders / History; stage-aware blockers and **approval** for overrides.
- **Vacancies list & card** — same **operational** bar as candidates (vacancy = recruitment container): columns for pipeline distribution, blockers, last activity; card links candidates scoped to vacancy, headcount, bottleneck, next action.
- **Clients list & card** — **party** with roles (employer, service client, both); pipeline + money signals; card emphasizes vacancies+candidates for employers, orders+invoices for service clients, both when mixed.
- **Leads** — strong standalone **qualification** before Candidates/Clients; types candidate vs client; convert / reject / assign.
- **Services catalog** — **templates** only (code, price, margin, usage, scheduling/VAT); not the execution surface.
- **Orders** — full **process module** (status draft → confirmed → in progress → completed / cancelled); list + card with next action, invoice/payment blocks, SLA.
- **Invoices** — **money control**: amounts, due, delay, follow-ups; Activities + SLA on overdue; quick actions (send, mark paid, follow-up, escalate).
- **Documents** — **center** across candidate, client/legal, and generated service/invoice docs; expiring/missing filters; approve/reject/replace.
- **Automations** — system **spine**: rules, hiring gates/stage requirements, notification rules, SLA policies, templates — not a peripheral screen.
- **Communication settings** — under **Settings**: channels, accounts, templates, signatures, routing, assignment, SLA policies (not daily nav).
- **Availability / time off** — **profile** + calendar/scheduling consumption; optional HR-lite requests — not top-level modules.
- **Notifications** — **center only** (top bar): groups Urgent, Tasks, Messages, System, Finance; priority critical/high/normal; actions open, read, snooze, assign.
- **Global search** — grouped results: candidates, clients, vacancies, orders, invoices, conversations, documents, tasks.

#### Global next-action rule

Every entity surface (table, preview, card) should expose **state, blockers, next action, owner, deadline/SLA** consistently.

#### Reference scenarios (cross-screen)

1. **Candidate path:** Lead → convert → auto call task → SLA → notification → stage/doc gates → Activities.  
2. **Client + money path:** Lead → client → qualify → offer → contract → order → invoice → payment follow-up + SLA if overdue.  
3. **Inbound comms:** thread in Inbox → unlinked queue → link + assign → Activity + SLA → escalate if stuck.

#### Rollout order (IA / product)

1. Lock **sidebar architecture** (this doc).  
2. **Unified Inbox** (messages + email one center).  
3. **Tasks** as execution hub (behaviors + sort/priority).  
4. **Calendar** strictly as Activity view.  
5. Strong **Vacancy** list + card.  
6. **Clients** around pipeline + money.  
7. **Orders + Invoices** as process + money control.  
8. **Automations** as dedicated system module.  
9. Remove **availability / time off** from first-level nav (absorb per above).

---

## Milestones M1–M4 (reference snapshot)

Original milestone specs are archived in git history if needed. **Current truth:**

| Milestone | Intent | Status |
|-----------|--------|--------|
| **M1** Activities | Pipedrive-grade activity spine + calendar/list | **Largely shipped** via **Reminder** + `/activities` + Tasks + calendar + bulk/templates; optional future rename/evolve model. |
| **M2** Leads inbox | Qualification workspace + convert + SLA | **Partially shipped** — side panel, fit-check, enforcement/SLA nudges; **duplicate merge** / heavy bulk still open. |
| **M3** Reporting | Operational dashboards + drill-down | **Largely shipped** — ops counters, stage metrics, goals/share; **open:** Services analytics = **R3.3**. |
| **M4** Hygiene | Import/export, dedupe, notification prefs | **Partial** — taxonomy/groups v1; **CSV import**, dedupe UX, digests/mute prefs TBD. |

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

---

## Risk intelligence v1 (response-delay decay model)

### Why this matters now

HostFlow already enforces next action and SLA nudges, but we still mostly answer "what is overdue?" and not "what is likely to fail soon?".  
For recruitment and sales-like workflows, delay itself is a strong predictive signal:

- if a candidate was not contacted on day 0/1, motivation and conversion probability decay each day;
- if a client did not receive a timely response, deal-close probability drops and cycle length increases.

The goal of this section is to define a practical, rollout-safe way to move from rule-based alerts to risk-aware operations.

### Conceptual model (simple and useful)

Treat risk as a probability of negative outcome over a time horizon, updated whenever key events happen.

- For candidates: risk of "won't reach target stage in X days" (e.g., not hired/not ready).
- For leads/clients: risk of "won't close/won't advance to next milestone in X days".

Minimum viable framing:

- `p_success_now`: estimated probability to reach target outcome from current state.
- `risk_score`: normalized urgency score 0..100 where higher means "intervene now".
- `risk_drivers`: human-readable top reasons (e.g., "no first response for 36h", "7d in stage without movement", "2 overdue actions").

### Core metric family (start here)

Use a small metrics set first; each metric must be explainable and actionable.

1. **Response latency metrics**
   - `first_response_minutes`: time from entity creation/inbound event to first human response.
   - `last_response_gap_hours`: now - last meaningful outbound/bi-directional touch.
   - `inbound_unanswered_hours`: unanswered inbound age.

2. **Action discipline metrics**
   - `has_next_action` (bool)
   - `next_action_overdue_hours`
   - `overdue_actions_count_7d`

3. **Flow stagnation metrics**
   - `days_in_stage`
   - `days_since_stage_change`
   - `stage_reopen_count_30d` (stage ping-pong as friction signal)

4. **Outcome context metrics**
   - `current_stage` / `funnel_position`
   - `owner_workload_open_items`
   - `interaction_count_7d` (too low can indicate cold process)

5. **Quality metrics (later, optional)**
   - communication sentiment/quality proxy (if available)
   - profile/data completeness index

### Time-decay logic (the heart of the model)

Use explicit decay curves so the system "understands" that each day of silence hurts odds.

For each delay-sensitive signal, define a half-life:

- `candidate_first_response_half_life_hours` (example: 24-36h)
- `client_inbound_reply_half_life_hours` (example: 8-24h)
- `stage_stagnation_half_life_days` (example: 5-10d depending on stage)

Apply decay factor:

- `decay(t, h) = 0.5^(t / h)` where `t` is delay and `h` is half-life.
- As `t` grows, contribution to success falls smoothly and predictably.

Practical interpretation:

- at `t = h`: signal contribution drops by 50%;
- at `t = 2h`: by 75%;
- the model encodes "each day late reduces chance" without hard cliffs.

### Risk score design (v1 transparent scoring, not black box)

Start with weighted scoring instead of a complex ML model.

Example v1 score:

- `risk_score = clamp(0..100, w1*response_risk + w2*stagnation_risk + w3*action_risk + w4*context_risk)`
- each component is normalized 0..100 and uses decay/time thresholds.
- initial weights can be expert-defined, then calibrated on historical outcomes.

Severity bands:

- `0-34`: low (normal monitoring)
- `35-64`: medium (show warning + suggested next best action)
- `65-84`: high (escalate to owner + manager digest)
- `85-100`: critical (immediate intervention workflow)

### Suggested initial thresholds (to be tuned)

These are rollout defaults, not final truth:

- Candidate first response:
  - medium risk after 24h
  - high risk after 48h
  - critical after 72h
- Client inbound unanswered:
  - medium after 4h (working hours)
  - high after 12h
  - critical after 24h
- Stage stagnation:
  - per-stage baseline SLA (e.g., qualified max 5d, interview max 7d, offer max 3d)
  - risk grows after baseline breach, then accelerates with decay

### Validation strategy when metrics are not finalized yet

You can start now without perfect schema by using an iterative evidence loop.

1. **Define target outcomes**
   - Candidate: reached target stage/hired within horizon.
   - Client/lead: advanced/closed-won within horizon.

2. **Backfill baseline from existing logs**
   - Use `ActivityLog`, reminders, stage changes, communication timestamps.
   - Build a retrospective dataset for last 60-180 days.

3. **Measure signal power**
   - For each candidate signal, compute success rate by delay buckets:
     - 0-24h, 24-48h, 48-72h, 72h+.
   - If success declines monotonically with delay, keep the signal.

4. **Calibrate thresholds and weights**
   - Choose cutoffs that separate "healthy" vs "at risk" cohorts.
   - Prefer stable, interpretable settings over overfitted precision.

5. **Run shadow mode**
   - Compute risk silently for 2-4 weeks.
   - Compare predicted high-risk cohorts vs real outcomes before enforcement.

### Product integration (where risk must appear)

1. **List surfaces (Candidates/Leads/Services)**
   - Add `risk_badge` (Low/Med/High/Critical) and sortable `risk_score`.
   - Provide quick filter: `risk>=high`.

2. **Work panel / Candidate card**
   - Show top 3 `risk_drivers` with plain language.
   - Add "recommended next action" generated from strongest driver.

3. **Dashboard widgets**
   - "Critical risk entities now"
   - "Risk trend 7d/30d"
   - "Intervention success rate" (high-risk rescued after action)

4. **Automation log linkage**
   - Every risk escalation must create a visible audit entry:
     - why score changed,
     - what rule triggered,
     - what action was suggested/executed.

### Automation policy (graduated response)

Map risk bands to interventions:

- Medium:
  - owner notification + suggested playbook action
- High:
  - auto-create reminder with due soon + manager visibility
- Critical:
  - escalation to backup owner / team lead queue
  - optional SLA breach incident counter

Guardrails:

- strict deduping windows to avoid alert spam;
- cooldown after manual action;
- "snooze with reason" to capture operator intent and improve model later.

### Data contract additions (minimal)

Add risk fields to key API outputs:

- `risk_score: number (0..100)`
- `risk_band: low|medium|high|critical`
- `risk_updated_at: datetime`
- `risk_drivers: string[]` (max 3-5)
- `risk_version: string` (for traceability)

Analytics additions:

- `risk_distribution_by_stage`
- `high_risk_volume`
- `high_risk_success_rate` (rescued vs not rescued)
- `time_to_first_response_distribution`

### Governance and quality controls

- **Versioned model configs** per tenant or segment (`risk_model_v1`, `risk_model_v1.1`).
- **Explainability required**: no score without drivers.
- **Fairness checks**: ensure risk is not proxying protected attributes.
- **Operational KPI coupling**:
  - `% entities with first response within SLA`
  - `% high-risk touched within 24h`
  - conversion uplift on previously high-risk cohort.

### Phased rollout plan

Phase A (2-3 weeks): instrumentation and baseline

- unify timestamps/events needed for response and stage-gap metrics;
- build retrospective risk table/job;
- publish read-only analytics (no user-facing alerts yet).

Phase B (2 weeks): shadow scoring + dashboard

- calculate `risk_score` daily/hourly;
- show risk widgets to ops leads only;
- validate precision/recall on recent outcomes.

Phase C (2-4 weeks): assisted operations

- expose risk badge + drivers in list/card;
- enable medium/high nudges and recommended next action;
- no hard blocking yet.

Phase D (after confidence): controlled enforcement

- enable critical escalation automations;
- optionally block sensitive stage transitions when risk is critical and no mitigation action exists (tenant-configurable).

### Acceptance criteria (must be measurable)

- For high-risk cohorts, median time-to-first-intervention improves by at least 30%.
- `first_response_within_target` improves by at least 20% in pilot teams.
- Conversion for previously high-risk entities improves vs pre-rollout baseline.
- Less than 10% of risk alerts are marked as "noise" by operators after tuning period.

### Immediate next step (this week)

Run a focused discovery sprint and produce a one-page evidence table:

- top 5 delay signals,
- their bucketized success curves,
- proposed half-lives and initial thresholds,
- expected intervention policy per signal.

After this, lock `risk_model_v1` config and start Phase A instrumentation.

### Operational matrix: risk → signals → thresholds → automation (v1 draft)

Use this matrix as the implementation-ready source for analytics, API fields, dashboard widgets, and automation rules.

#### 1) Candidate engagement decay risk

- **Risk definition**: candidate is losing motivation and likely to drop off before target stage.
- **Primary signals**:
  - `first_response_minutes`
  - `last_response_gap_hours`
  - `inbound_unanswered_hours`
  - `interaction_count_7d`
- **Initial thresholds**:
  - medium: first response > 24h
  - high: first response > 48h OR unanswered inbound > 24h
  - critical: first response > 72h OR unanswered inbound > 48h
- **Automation**:
  - medium: notify owner + suggest "contact now with template X"
  - high: auto-reminder due in 2h + manager digest entry
  - critical: escalate to backup owner queue + incident tag `risk_engagement_critical`
- **Success KPI**:
  - `% first response within 24h`
  - conversion from high-risk cohort vs baseline

#### 2) Stage stagnation / bottleneck risk

- **Risk definition**: entity is stuck in stage beyond healthy cycle and unlikely to progress without intervention.
- **Primary signals**:
  - `days_in_stage`
  - `days_since_stage_change`
  - `stage_reopen_count_30d`
- **Initial thresholds**:
  - stage baseline breach (per-stage SLA map) = medium
  - baseline * 1.5 = high
  - baseline * 2.0 = critical
- **Automation**:
  - medium: owner prompt with "next best action by stage"
  - high: require overdue reason code (`waiting_client`, `waiting_docs`, `no_response`, `internal_block`)
  - critical: auto-escalate to team lead board + force review task in 24h
- **Success KPI**:
  - median `days_in_stage` by stage
  - stage transition rate after intervention

#### 3) Next-action discipline risk

- **Risk definition**: work is not operationally controlled; no clear next step exists.
- **Primary signals**:
  - `has_next_action`
  - `next_action_overdue_hours`
  - `overdue_actions_count_7d`
- **Initial thresholds**:
  - no next action for > 24h = medium
  - overdue next action > 24h or 2+ overdue actions in 7d = high
  - overdue next action > 72h = critical
- **Automation**:
  - medium: one-click quick-create next action panel
  - high: auto-create fallback reminder and pin in work panel
  - critical: block non-terminal stage change until mitigation action exists (tenant-configurable)
- **Success KPI**:
  - `% entities with active next action`
  - `% high-risk touched within 24h`

#### 4) Owner capacity / overload risk

- **Risk definition**: assigned owner load is too high; SLA and quality degrade.
- **Primary signals**:
  - `owner_open_entities_count`
  - `owner_overdue_actions_count`
  - `owner_high_risk_entities_count`
- **Initial thresholds** (team-relative, percentile-based):
  - medium: owner above P75 on any 2 load signals
  - high: owner above P90 on any 2 load signals
  - critical: above P95 + rising overdue trend 7d
- **Automation**:
  - medium: recommend rebalance candidates/leads
  - high: notify manager with "reassign shortlist"
  - critical: auto-route new assignments away from overloaded owner until recovered
- **Success KPI**:
  - owner SLA compliance variance
  - overdue ratio before/after rebalancing

#### 5) Handoff failure risk

- **Risk definition**: ownership handoff happened, but new owner did not establish control quickly.
- **Primary signals**:
  - `hours_since_reassignment`
  - `first_action_after_reassignment_hours`
  - `messages_after_reassignment_24h`
- **Initial thresholds**:
  - no action within 8h after reassignment = medium
  - no action within 24h = high
  - no action within 48h = critical
- **Automation**:
  - medium: remind new owner to acknowledge handoff
  - high: notify previous owner + manager
  - critical: re-open handoff checklist and escalate
- **Success KPI**:
  - `% handoffs with first action < 8h`
  - post-handoff conversion vs baseline

#### 6) Readiness / document failure risk

- **Risk definition**: candidate cannot progress due to critical missing/expiring documents.
- **Primary signals**:
  - `missing_critical_docs_count`
  - `expiring_docs_count_14d`
  - `readiness_score`
- **Initial thresholds**:
  - medium: 1 critical missing doc OR >=2 expiring in 14d
  - high: >=2 critical missing docs OR any doc expiring in <=7d at active stage
  - critical: blocking document missing at decision/offer/onboarding stage
- **Automation**:
  - medium: trigger request-docs template flow
  - high: owner + compliance role notification
  - critical: prevent stage progression to dependent stages until resolved
- **Success KPI**:
  - readiness completion rate
  - delay caused by document blockers

#### 7) Communication quality risk

- **Risk definition**: communication exists but is ineffective (no progress signals).
- **Primary signals**:
  - `outbound_without_reply_count_7d`
  - `thread_age_open_days`
  - `resolution_event_absent` (bool)
- **Initial thresholds**:
  - medium: 3 outbound touches without reply in 7d
  - high: 5 touches without reply OR open thread > 10d
  - critical: open thread > 14d without resolution in active funnel stage
- **Automation**:
  - medium: suggest channel switch (email -> call/whatsapp/etc.)
  - high: suggest escalation template / manager outreach
  - critical: mark as "recovery playbook required" and queue specialized intervention
- **Success KPI**:
  - reply rate per channel after suggested switch
  - resolution time per thread

#### 8) Deal health / financial risk (services)

- **Risk definition**: service pipeline advances but commercial outcome degrades.
- **Primary signals**:
  - `invoice_overdue_amount`
  - `invoice_overdue_days_p95`
  - `margin_delta_vs_quote`
  - `delivered_not_invoiced_count`
- **Initial thresholds**:
  - medium: overdue amount > tenant threshold OR margin drop > 10%
  - high: overdue > 30d OR margin drop > 20%
  - critical: overdue > 60d OR negative margin forecast
- **Automation**:
  - medium: finance reminder + owner nudge
  - high: manager review task and payment recovery workflow
  - critical: freeze new discretionary work for account until review
- **Success KPI**:
  - outstanding-to-paid ratio
  - recovery rate for overdue cohort

### Cross-risk prioritization logic

When one entity has multiple risks, show a single priority queue score:

- `priority_score = 0.45*risk_score + 0.25*business_impact + 0.20*urgency + 0.10*recovery_potential`

Where:

- `business_impact` reflects expected value (revenue/hiring impact);
- `urgency` reflects time-to-deadline proximity;
- `recovery_potential` estimates chance to rescue if touched now.

### Implementation notes (v1)

- Keep all thresholds tenant-configurable in one namespace: `Tenant.settings.risk_model_v1`.
- Log every automated intervention with `risk_rule_id`, old/new band, and selected driver.
- Add operator feedback actions: `helpful`, `not_helpful`, `wrong_reason`; use this for monthly tuning.

### Suggested rollout order (lowest complexity to highest value)

1. Candidate engagement decay risk
2. Next-action discipline risk
3. Stage stagnation risk
4. Readiness/document failure risk
5. Owner overload risk
6. Handoff failure risk
7. Communication quality risk
8. Deal health/financial risk
