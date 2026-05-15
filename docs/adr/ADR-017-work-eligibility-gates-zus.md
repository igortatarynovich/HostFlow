# ADR-017: Work eligibility gates ZUS operational tasks

## Status

Accepted (foundation implemented; rules engine and submission UX evolve in follow-ups).

## Context

Automating ZUS workspace tasks before **legal right to work** is established is risky for transport HR (non-EU drivers: legal stay, work permit, red paper, then ZUS).

## Decision

1. Introduce **`WorkforceWorkEligibilityProfile`** (per employee) with lifecycle `eligibility_status` including `ready_for_zus` and `eligible_to_work`.
2. **`workforce_work_eligibility_rules.evaluate_zus_registration_gate`** returns `allow` vs `blocked` plus `blocked_by` keys (`work_permit`, `legal_stay`, `red_paper`, …).
3. **`ensure_zus_registration_task`** consults the gate:
   - If **blocked**: upsert a ZUS **registration** workspace task with `status=blocked` and `checklist_json.blocked_by` so HR sees why ZUS is not actionable yet.
   - If **allow**: create `pending` registration task, or promote an existing `blocked` row to `pending`.
4. Reference table **`work_permit_submission_channels`** holds portal/office metadata (seeded later; no tenant RLS).
5. **PR order**: PR-4 (eligibility + rules + channels schema) before tightening PR-5 (ZUS auto-create); PR-6 extends HR document hub.

## Consequences

- API `PATCH /api/v1/workforce/employees/{id}/work-eligibility` re-runs `ensure_zus_registration_task` so clearing blockers updates the queue.
- `HrBundleOut` exposes `work_eligibility_profile` for employee detail UI.
- Monthly ZUS settlement tasks remain **ungated** in v1 (registration-only gate).
