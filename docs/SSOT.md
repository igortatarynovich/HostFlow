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

