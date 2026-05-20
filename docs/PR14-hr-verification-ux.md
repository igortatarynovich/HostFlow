# PR14 — HR Verification UX + E2E

**Status:** Planned (after PR13 merge).  
**Depends on:** [PR13 hybrid verification plan](PR13-hybrid-verification-plan.md), [hr-verification-plan spec](specs/workflows/hr-verification-plan.md).

PR13 delivers the **hybrid plan + backend gate**. PR14 delivers **operator UX** and **end-to-end confidence** — no change to tier rules unless bugs are found.

---

## Goal

HR can complete a full review case without reading engine internals: clear steps, document status, explicit actions, ready state before approve.

---

## Scope

### Sequential flow polish

- **Step N / current document** — visible step index and label from `verification_order`.
- **Document status** — pending / opened / verified / needs_correction / rejected (human labels, not raw enums).
- **Confirm this document** — primary CTA copy aligned with action.
- **Request correction** — inline form + success feedback.
- **Waive / exception** — UI for `overridable` tiers only; calls `POST …/waive-requirement`; shows reason in panel.
- **HR-requested document** — UI to add rows into `decision_basis_json.hr_document_requests` (and reflect in plan on rebuild).

### Completion

- **Ready screen** — when `verification_plan.can_approve` and panel gates pass: summary of confirmed docs, open blockers (if any), approve CTA.

### E2E

Full path (API or browser):

1. Handoff / employee HR review opens with `verification_plan`.
2. HR opens document → verifies fields → confirms document.
3. Optional: waive recommended/required with reason.
4. Optional: request correction / HR-requested doc.
5. Approve succeeds only when plan + gates allow; blocked otherwise.

---

## Out of scope (PR14)

- New requirement tiers or ruleset logic (stay in PR13 / rules engine).
- Client-specific legal rule authoring.
- Bulk exception management / admin consoles.

---

## Implementation order

1. **Verification step shell** (in progress on `feat/pr14-hr-verification-ux`)
   - `HrVerificationStepShell` — step header, progress bar, focus, sticky footer
   - Human status labels (`hrDocumentHumanLabels.ts`) — no raw `verification_status` in main UI
   - Exception UI deferred (correction / reject / waive / recommended collapsed lists removed from main flow for now)
2. Decision actions — wire footer actions with clear copy
3. Exception UX — modals, waive, HR-requested
4. Ready screen
5. E2E (last)

### PR14 risk guard

Do **not** surface in HR main flow: `field_code`, blocker ids, raw checklist, `requirement_tier`, verification state machine enums, `technical_details` panel.

HR sees: document name, field **labels**, missing hints, next step, human status, confirm CTA.

## Acceptance criteria

- [x] Step shell: Step N + Verify {document} + progress + sticky footer
- [ ] HR sees step number and document name without opening admin checklist.
- [ ] Recommended docs visible but do not disable approve when incomplete.
- [ ] Waive button hidden/disabled for `hard_blocker` tiers.
- [ ] Waive requires reason; panel shows waiver after rebuild.
- [ ] HR can add an HR-requested document; approve blocked until resolved.
- [ ] Ready screen appears when `can_approve` is true.
- [ ] E2E test covers confirm + waive + approve (or blocked approve).

---

## Key files (starting points)

| Area | Path |
|------|------|
| Sequential UI | `hostflow-frontend/src/components/hr/HrSequentialDocumentVerification.tsx` |
| Approve gate (FE) | `hostflow-frontend/src/utils/hrReviewApprove.ts` |
| Plan (BE) | `backend/app/services/hr_verification_plan.py` |
| Waiver API | `workforce/router.py`, `handoffs.py` |
