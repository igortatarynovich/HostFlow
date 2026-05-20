# PR13 — Hybrid HR Verification Plan

## Summary

PR13 introduces a hybrid HR verification plan.

The system now generates a `verification_plan` before HR review, combining hard legal blockers, vacancy/client required documents, recommended documents, and HR-requested documents.

The plan no longer acts as an absolute source of truth. Instead, it guides HR while enforcing non-waivable legal/core blockers through the backend approve gate.

### Requirement tiers

| Tier | Blocks approve | Waivable |
|------|----------------|----------|
| `hard_blocker` | Yes | No |
| `required` | Yes (unless waived with reason) | Yes |
| `recommended` | No | Yes |
| `hr_requested` | Yes until resolved | N/A (HR-defined) |

HR remains the final legal control layer, while the backend prevents critical approval mistakes.

## Pre-merge smoke

```bash
cd backend && python3 -m pytest \
  tests/services/test_hr_verification_plan.py \
  tests/services/test_hr_verification_waiver_gate.py \
  tests/api/test_hr_review_document_sot.py -q
```

### Checklist

1. Hard blockers cannot be waived (Passport / ID, journey legal stay/permit, driver license for driver).
2. Required waiver requires reason; stored in `reviewed_fields_json._requirement_waiver`, `decision_basis_json.requirement_waivers`, and activity audit.
3. Recommended missing does not block approve.
4. HR-requested open items block approve.
5. UI uses `verification_plan` only (`documentsFromPanel`, `isHrApproveAllowed`); backend `finalize_hr_review_can_approve` reads the same plan.

## Critical merge note

In **hybrid** mode, `finalize_hr_review_can_approve` must **not** re-run the legacy `documents_for_approval` loop. Only `verification_plan` (+ checklist / verified-fields / data-verification) gates documents. See spec section “Critical: hybrid mode must not double-gate documents”.

## Out of scope → PR14

See [PR14 HR Verification UX](PR14-hr-verification-ux.md).
