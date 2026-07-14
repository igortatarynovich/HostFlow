# PR15 — Unify HR approve readiness after verification_plan

**Status:** Active — backend-only (after PR-INFRA merge recommended for safe pytest).  
**Branch:** `feat/pr15-hr-approve-readiness`  
**Depends on:** PR13 hybrid plan. **Not in scope:** PR14 UX, PR16, email mock (branch `feat/pr-infra-pytest-email-mock`).

---

## Goal

Single readiness source in **hybrid** mode: `verification_plan.can_approve` matches approve API and `panel.can_approve`.

---

## Changes

- `finalize_hr_review_can_approve` — hybrid uses `plan_blocks_approve` only
- `_assert_can_approve` — hybrid rebuilds panel via `build_hr_review_panel` (same as UI)
- Non-hybrid — legacy checklist + verified-fields unchanged

---

## Pre-merge

1. Merge **PR-INFRA** first (or export `EMAIL_DELIVERY_MODE=mock`)
2. `./scripts/hr-verification-pr15-regression.sh`

---

## Acceptance criteria

- [x] Hybrid plan-only finalize gate
- [x] Approve API aligned with panel pipeline
- [x] Unit tests (waiver gate hybrid cases)
- [ ] E2E: ready → 200, blocked → 422 (needs PR-INFRA + DB)
