# Forms Sprint 5 — Normalized answer contract

**Status:** READY FOR REVIEW  
**Prerequisite:** Forms Sprint 4 **COMPLETE** ([`forms-sprint-4.md`](forms-sprint-4.md) · merge `779cffd3` / PR #39)  
**Canon:** [`forms-public-contract.md`](../architecture/forms-public-contract.md)  
**Builder:** **LOCKED**

---

## Goal

Stable answer format by `field_id` with raw/normalized split, canonical type normalization, and Shared Intake handoff — **without** domain mapping or Builder.

```text
raw payload → flat field map → canonicalize by frozen schema
→ forms.normalized_answers.v1
→ intake_handoff (presentation_values_v1 + version pins)
```

---

## Scope

### In

- `forms.normalized_answers.v1`  
- `raw_values` vs `normalized_values`  
- Canonical normalization: string, number, boolean, date, email, phone  
- Error contract: `field_id`, `code`, `message_key`, `message`  
- Unknown fields rejected **after** flat extraction / before accept  
- `schema_contract` + `published_version` (+ `form_id`) stored with answers  
- `intake_handoff` for Shared Intake (no Forms domain mapping)  
- Contract + gates  

### Out

- Builder / visual schema editor / drag-and-drop  
- Domain mapping (Candidate/Lead field ownership) inside Forms  
- New submission engine  
- New Alembic migration  

---

## DoD

- [x] Answer contract with raw + normalized  
- [x] Canonical normalizers for core types  
- [x] Validation errors include `message_key`  
- [x] Unknown rejected post-normalization extract  
- [x] Schema + publication version on answer  
- [x] Shared Intake handoff without domain mapping  
- [x] Builder locked; Sprint 1–4 regression green  

---

## History

- 2026-07-18: Opened after Sprint 4 merge `779cffd3` (#39).
