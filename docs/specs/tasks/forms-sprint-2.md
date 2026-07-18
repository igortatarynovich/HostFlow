# Forms Sprint 2 — Runtime contract hardening

**Status:** READY FOR REVIEW  
**Prerequisite:** Forms Sprint 1 **COMPLETE** ([`forms-sprint-1.md`](forms-sprint-1.md) · merge `37b652af` / PR #36)  
**Canon:** [`forms-public-contract.md`](../architecture/forms-public-contract.md) · [`ADR-007`](../architecture/ADR-007-forms-platform-capability.md)  
**Builder:** **LOCKED**

---

## Goal

Укрепить runtime contract HostFlow Form **без** Builder:

```text
publish (immutable version) → activate/deactivate endpoint
→ submission pinned to published_version + consent pin
→ typed adapter errors · idempotent resolve
```

---

## Scope

### In

1. Real **publish** lifecycle (mutation) vs **resolve** (idempotent read)  
2. Immutable **published snapshot** per version (`published_snapshot_v1`)  
3. Endpoint **activate / deactivate** via Adapter  
4. Public slug uniqueness + tenant-scoped resolve (existing global uniqueness retained)  
5. Submission compatibility with pinned `published_version`  
6. Consent-version pinning on publish  
7. Adapter error semantics (`not_found`, `inactive`, `stale_published_version`, …)  
8. Contract tests: deactivate/reactivate, stale publication, idempotent resolve  

### Out (still forbidden)

- Visual Builder; drag-and-drop; themes editor; branching UI  
- In-place edit of an already published version (new publish creates new version)  
- Forms-owned routing / Result / Outcome / KPI  
- Duplicate Shared Intake submit engine  

---

## DoD

- [x] `publish` freezes snapshot + bumps `published_version`  
- [x] `resolve` idempotent; includes version + lifecycle + pin metadata  
- [x] inactive endpoint rejected for public/endpoint ops with typed error  
- [x] activate/deactivate roundtrip green  
- [x] stale `published_version` rejected on submission gate  
- [x] Sprint 1 suites remain green (updated to `resolve` where needed)  
- [x] Builder remains locked  
- [x] Alembic single head (`202607180007_forms_s2`)  

---

## History

- 2026-07-18: Sprint opened after Sprint 1 merge `37b652af` (#36).
