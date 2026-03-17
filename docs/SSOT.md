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

- [ ] Confirm **design tokens** (spacing/radius/colors/typography) are implemented as a single source (and remove drift).

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

- [ ] **R1.1 Candidates quick preview side panel**
- [ ] **R1.2 Candidate unified timeline v1**
- [ ] **R1.3 Next action contract + “no next action” operational view**

### R2

- [ ] **R2.1 Automation log (rule fired → actions)**
- [ ] **R2.2 Minimal rules builder (candidate created/stage changed/doc expiring/lead processed)**

### R3

- [ ] **R3.1 Dashboard operational widget set (8–10) + drill-down**
- [ ] **R3.2 Stage time + conversion + readiness analytics**

### R4

- [ ] **R4.1 Perf baseline capture (p50/p95) for key actions**
- [ ] **R4.2 Perf budgets + regression response workflow**

