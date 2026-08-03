# Meta Intake Completeness

**Status:** **IN PROGRESS** (Phase B — Product Track)  
**Parents:** [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [A2 Governance](../gates/platform-governance-review-a2.md) · Acquisition / Flights / SalesInquiry  
**Branch:** `feat/meta-intake-completeness`

## Problem

Meta intake loses or under-displays data:

- company name not formed;
- some Meta answers not persisted or not shown;
- UI shows a truncated Lead projection instead of the original submission.

## Chain to verify

```text
Meta payload → Lead.payload (raw) → normalized.field_answers → Sales ApplicationOut.extensions → UI
```

Full Meta payload must be stored and viewable even when individual fields are not yet normalized.  
Today raw SoT is **`leads.payload`** (not Forms `FormSubmissionEnvelope` — deferred to Phase C).

## Scope

- Persist complete raw payload (`Lead.payload`)  
- Persist all Meta questions and answers (`normalized.field_answers`)  
- Unknown / unmapped fields → `normalized.additional_answers` (never drop)  
- Show original answers on the Sales inquiry card (`extensions.meta_form_answers`)  
- Normalize company name via **B2B inquiry naming rules** (below)  
- Fixture with a real full Meta payload  
- Contract test: no form answer is dropped  

### B2B inquiry naming rules

Operator title / `ApplicationOut.title` priority (first non-empty wins):

1. `company_profile.name`  
2. `company_name`  
3. `company_name_hint` (from Meta company aliases, e.g. `nazwa_firmy`)  
4. Lead column `company_name`  
5. Fallback literal `Компания`  

Never invent a company title from contact first/last name alone.  
Helper: `backend.app.modules.leads.normalizer.resolve_b2b_inquiry_company_name`.

## Acceptance

Operator can open a Sales inquiry and see every answer from the Meta form; company naming follows the rules above.

## Explicitly deferred

- Moving Meta into Forms `FormSubmissionEnvelope`  
- Persisting answers on `sales_inquiries` columns (R6 SoT)  
- Live Meta Graph form mapping audit / admin verify gate  
- Historical DB backfill job  
