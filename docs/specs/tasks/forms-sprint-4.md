# Forms Sprint 4 — Schema contract & validation runtime

**Status:** READY FOR REVIEW  
**Prerequisite:** Forms Sprint 3 **COMPLETE** ([`forms-sprint-3.md`](forms-sprint-3.md) · merge `f5771df6` / PR #38)  
**Canon:** [`forms-public-contract.md`](../architecture/forms-public-contract.md)  
**Builder:** **LOCKED** — no visual schema editor, drag-and-drop, or dynamic code execution

---

## Goal

Freeze a canonical **field schema** inside each publication version and validate submissions against that frozen schema (version-specific).

```text
commit_publish(+ field_schema) → immutable schema in ledger snapshot
validate_submission(schema, payload) → normalized values | typed errors
pre_schema snapshots → compat mode (no unknown rejection)
```

---

## Scope

### In

- `forms.field_schema.v1` contract (`schema.py`)  
- Immutable schema inside publication version snapshot  
- Field id / type / required / validation bag  
- `validate_submission` — unknown rejection, required, light type checks  
- Normalized payload `{ values: { field_id: value } }`  
- Backward compat: snapshots without schema → `pre_schema`  
- Version-specific validation via ledger snapshot  
- Contract + gates  

### Out

- Visual Builder / schema editor / drag-and-drop  
- Dynamic code execution (`eval`/`exec`)  
- Themes / branching UI  
- Forms Outcome/KPI/routing  
- New Alembic migration (schema lives in existing JSON snapshot)  

---

## DoD

- [x] Canonical field schema builder  
- [x] Schema frozen into publish snapshot / ledger  
- [x] Unknown field rejection  
- [x] Required field validation  
- [x] Type checks (email/phone/integer/…)  
- [x] Version-specific validation  
- [x] Pre-schema compat policy documented  
- [x] Builder locked; no dynamic code  
- [x] No new migration; Alembic single head  

---

## History

- 2026-07-18: Opened after Sprint 3 merge `f5771df6` (#38).
