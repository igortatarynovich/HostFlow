# Forms Sprint 6 — Submission persistence envelope

**Status:** READY FOR REVIEW  
**Prerequisite:** Forms Sprint 5 **COMPLETE** ([`forms-sprint-5.md`](forms-sprint-5.md) · merge `a6df02f0` / PR #40)  
**Canon:** [`forms-public-contract.md`](../architecture/forms-public-contract.md)  
**Builder:** **LOCKED**

---

## Goal

Append-only persistence of Forms answers as an immutable **submission envelope**, with processing status separate from content — without a second intake engine or domain mapping.

```text
validate/normalize → persist_submission_envelope
  raw_values + normalized_values + schema/publication pins
  processing_status (mutable)
→ audit get/list
→ Shared Intake consumes intake_handoff
```

---

## Scope

### In

- Table `form_submission_envelopes`  
- Append-only raw + normalized answers  
- Refs: `form_id`, `published_version`, `schema_contract`, `answer_contract`  
- Idempotency key (partial unique)  
- Immutable content; mutable `processing_status` only  
- Audit get/list + tenant isolation  
- Pin publication version on accepted persist  
- Migration `202607180009_forms_s6`  

### Out

- Builder / UI  
- Domain mapping  
- Second intake / routing engine  
- Forms Outcome/KPI  

---

## DoD

- [x] Append-only envelope persistence  
- [x] Idempotent replay by key  
- [x] Content immutable; status separate  
- [x] Audit read + tenant isolation  
- [x] Alembic chain + roundtrip  
- [x] Builder locked; Sprint 1–5 regression  

---

## History

- 2026-07-18: Opened after Sprint 5 merge `a6df02f0` (#40).
