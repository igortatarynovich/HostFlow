# PR14 — HR Verification UX + E2E

**Status:** UX integrated into employee card (case mode) after PR17.  
**Branch:** `feat/pr14-hr-verification-ux` (when active).  
**Depends on:** [PR13 hybrid verification plan](PR13-hybrid-verification-plan.md).  
**Backend approve alignment:** [PR15](PR15-unify-hr-approve-readiness.md) (not part of PR14).

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

1. **Verification step shell** ✅
   - `HrVerificationStepShell` — step header, progress bar, focus, sticky footer
   - Human status labels (`hrDocumentHumanLabels.ts`) — no raw `verification_status` in main UI
2. **Decision actions** ✅ (on `feat/pr14-hr-verification-ux`)
   - `HrDocumentDecisionFooter` — Confirm · Request correction · Reject candidate (+ nav)
   - `HrDocumentCorrectionForm` — quick suggestions + textarea; sends doc correction + return to recruitment
   - `HrDocumentRejectForm` — case-level reject (rose panel, separate copy)
   - Frozen read-only when `returned_to_recruitment` / `rejected_by_hr` / `approved_for_employment`
3. Exception UX — progressive disclosure, waive, HR-requested ✅
4. Ready screen ✅
5. E2E ✅ (API — `tests/api/test_hr_verification_pr14_e2e.py`)

### PR14 risk guard

Do **not** surface in HR main flow: `field_code`, blocker ids, raw checklist, `requirement_tier`, verification state machine enums, `technical_details` panel.

HR sees: document name, field **labels**, missing hints, next step, human status, confirm CTA.

## Note

PR14 is **not** coupled to PR15/PR16 merge order. Backend approve alignment is [PR15](PR15-unify-hr-approve-readiness.md).

---

## Manual UI smoke (required before merge)

One full case on staging/dev:

1. Open HR case (employee or handoff).
2. Walk documents: open → verify fields → confirm each required doc.
3. Confirm required docs batch if shown.
4. **Correction path:** request correction → verify frozen read-only state; approve disabled.
5. **Ready path (separate case):** reach ready screen when plan allows → approve from ready screen only.
6. **No raw engine in main flow:** no `field_code`, blocker ids, tiers, checklist engine labels in primary HR UI.

---

## Acceptance criteria

- [x] Step shell: Step N + Verify {document} + progress + sticky footer
- [x] HR sees step number and document name without opening admin checklist.
- [x] Recommended docs visible but do not disable approve when incomplete (hybrid plan; PR13 gate).
- [x] Waive link hidden for `hard_blocker` / non-`overridable` tiers (not merely disabled).
- [x] Waive requires reason; secondary styling; warning copy.
- [x] HR can request additional document; appears in plan as `hr_requested`; blocks approve until resolved.
- [x] Ready screen appears when `verification_plan.can_approve` is true.
- [x] Human blocking hints on step view (no raw `blocking_reasons`).
- [x] Approve CTA on ready screen; hidden from decision panel when plan ready.
- [x] API E2E: EU non-driver ready + approve, non-EU driver gating, waiver, HR-requested, correction return.
- [x] Optional Playwright UI smoke (`e2e/hr-verification-pr14.api.spec.ts` with env credentials).

### Regression smoke (pre-merge)

```bash
./scripts/hr-verification-pr14-regression.sh
```

Expected: **22 passed, 1 skipped** (waiver test when fixture has no waivable required doc).

Or:

```bash
cd backend && python3 -m pytest \
  tests/services/test_hr_verification_plan.py \
  tests/services/test_hr_verification_waiver_gate.py \
  tests/api/test_hr_review_document_sot.py \
  tests/api/test_hr_verification_pr14_e2e.py -q
```

### Known backend debt (PR15)

E2E `test_eu_non_driver_ready_then_approve` may assert `422 HR_REVIEW_BLOCKED` after `verification_plan.can_approve === true` because `finalize_hr_review_can_approve` still applies legacy checklist / verified-fields SoT. Frontend ready screen is correct; unify gates in [PR15](PR15-unify-hr-approve-readiness.md).

---

## Key files (starting points)

| Area | Path |
|------|------|
| Sequential UI | `hostflow-frontend/src/components/hr/HrSequentialDocumentVerification.tsx` |
| Approve gate (FE) | `hostflow-frontend/src/utils/hrReviewApprove.ts` |
| Plan (BE) | `backend/app/services/hr_verification_plan.py` |
| Waiver API | `workforce/router.py`, `handoffs.py` |
| Ready screen | `HrVerificationReadyScreen.tsx`, `hrVerificationReadySummary.ts` |
| Exceptions | `HrVerificationExceptionsPanel.tsx`, waive / HR-requested forms |
| PR14 E2E | `backend/tests/api/test_hr_verification_pr14_e2e.py` |
| Regression script | `scripts/hr-verification-pr14-regression.sh` |
