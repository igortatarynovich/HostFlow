# Forms Sprint 3 — Publication version ledger

**Status:** READY FOR REVIEW  
**Prerequisite:** Forms Sprint 2 **COMPLETE** ([`forms-sprint-2.md`](forms-sprint-2.md) · merge `ec5fcd86` / PR #37)  
**Canon:** [`forms-public-contract.md`](../architecture/forms-public-contract.md)  
**Builder:** **LOCKED**

---

## Goal

Replace “current-only snapshot” with an **append-only publication version ledger**, still without Builder.

```text
commit_publish → INSERT form_publication_versions (immutable)
               → update TenantLeadForm current pointer
submission pin → ledger version row (forbid delete)
audit read → list/get historical versions
```

`published_snapshot_v1` remains a **denormalized current pointer**, not history.

---

## Scope

### In

- Table `form_publication_versions` (append-only)  
- Unique `(tenant_id, form_id, version)`  
- Partial unique idempotency key (Postgres)  
- `submission_pin_count` — block delete/mutate when > 0  
- Current pointer on `TenantLeadForm` unchanged in role  
- Adapter: list/get version, pin registration, idempotent `commit_publish`  
- Migration `202607180008_forms_s3` + backfill from current snapshots  
- Contract + gates + Sprint 1–2 regression  

### Out

- Builder / visual schema / themes  
- New submission engine  
- Forms Outcome/KPI/routing  

---

## DoD

- [x] Append-only ledger row per `commit_publish`  
- [x] Unique `(tenant_id, form_id, version)`  
- [x] Current pointer still on form  
- [x] Submission pin blocks delete  
- [x] Historical versions audit/read only  
- [x] Tenant isolation  
- [x] Idempotent publish  
- [x] Alembic single head + roundtrip  
- [x] Builder locked  

---

## History

- 2026-07-18: Opened after Sprint 2 merge `ec5fcd86` (#37).
