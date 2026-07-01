# PR12 — Sequential Document Verification Flow

This PR replaces the previous engine-facing HR verification surface with a document-first verification flow.

Instead of exposing field-level checklist items, blockers, and internal verification tables, HR now verifies one document at a time:

- document viewer / open document action on the left
- recruiter-provided data with inline editing on the right
- single document-level confirmation action
- sequential navigation through required documents
- progress indicator with next document context

The backend verification engine remains unchanged. The UI now sends reviewed fields for the current document, while the backend continues to synchronize verified fields, identity readiness, checklist state, and blockers internally.

Internal/system layers are hidden from the main HR workflow:

- `data_verification_items` table removed from primary UI
- checklist moved into collapsed system section
- technical details moved into admin-only details
- decision panel simplified around employment readiness

This aligns the HR workspace with the intended user flow: open document → compare data → edit if needed → confirm document → continue → approve employment.

## Pre-merge smoke checklist

| Check | Result |
|-------|--------|
| Confirm calls `POST …/verify` → `verification_status=verified` on row + context | Code: `verify_document()` sets `VERIFICATION_VERIFIED` + `sync_from_document_verification` |
| Inline edits included in `reviewed_fields` on verify | Code: `buildConfirmedReviewedPayload(fieldEdits)` before `postHrDocumentVerify` |
| Unconfirmed required doc blocks approve | Backend: `verification_blocks_approval` + checklist; API test `test_approve_with_blockers_returns_hr_review_blocked` |
| Optional transport docs (non-driver) do not block | Backend: `required=False` + `VERIFICATION_NOT_REQUIRED`; test `test_verification_blocks_approval_skips_optional_missing` |
| Empty recruiter values show human copy | UI: "Missing — enter from document" |
| Checklist/system in collapsed sections only | `caseDecisionMode` + `<details>` |
| Rail → `#hr-document-verification` | `HrNextActionRail` + BFF anchors updated |

## Next: PR13 — Make Verification Visually Obvious

- Step title: "Step 2: Verify Driver License"
- Document status labels: Not checked / Confirmed / Needs correction
- Primary CTA: "Confirm this document"
- Secondary: "Mark as needs correction"
- Completion screen before approve
