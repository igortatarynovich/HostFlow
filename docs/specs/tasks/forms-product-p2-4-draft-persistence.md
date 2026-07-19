# Forms Product Layer P2.4 — Draft Persistence

**Status:** **COMPLETE**  
**Epic / P2:** [`forms-product-p2-builder.md`](forms-product-p2-builder.md) · Catalog Consumption **ACTIVE**  
**Prerequisite:** P2.3 Composition Commands **COMPLETE** (`e1de9e3e` / #59)  
**Unlocks:** P2.5 Minimal Builder UI — **READY** (UI gate open)  
**Out of scope:** publish side effects · Catalog SoT · intake/domain mapping · UI state  

---

## Goal

Persist and load **only** Builder draft compositions with tenant isolation and optimistic revision pins — without becoming a second publication schema or Catalog source of truth.

```text
FormDraftComposition.to_dict()
  → form_builder_drafts (tip + revision)
  → form_builder_draft_revisions (immutable payload per revision)
```

**Contract:** `forms.builder.draft_persistence.v1`  
**Package:** `backend/app/forms_platform/builder/draft_persistence.py`  
**Tables:** `form_builder_drafts` · `form_builder_draft_revisions`  
**Migration:** `202607190001_forms_p24`

---

## Operations

| Op | Role |
|----|------|
| `create` | New draft tip at revision 1 + immutable rev row |
| `get` | Tenant-scoped tip load |
| `update` | Requires `expected_revision`; bumps revision; freezes new payload |
| `list` | Tenant list (active by default) |
| `archive` | Soft-archive tip (no publication impact) |

Surfaces: `InMemoryDraftStore` (tests/clients) + async SQLAlchemy adapter.

---

## Invariants (held)

1. Draft stores `draft_id` + composition contract payload **without transformation**.  
2. Update requires expected revision; mismatch → typed conflict.  
3. Each saved revision payload is immutable (append-only revision ledger).  
4. Unknown component/version rejected via composition `assert_valid` — never silent replace.  
5. No publish side effects; publication ledger untouched.  
6. No automatic component version upgrade.  
7. No second schema/publication contract; no UI-specific state; no intake/domain mapping.  
8. Draft storage is **not** SoT for Catalog or publication ledger.  
9. Tenant isolation on every operation.

---

## DoD

- [x] create / get / update / list / archive  
- [x] optimistic revision pin + conflict error  
- [x] immutable per-revision composition payload  
- [x] Catalog-backed validity on write  
- [x] Migration + model  
- [x] No publish / UI / intake  
- [x] Contract + gate tests green  
- [x] P2.5 UI gate opened  

---

## History

- 2026-07-19: Opened READY after P2.3 COMPLETE (`e1de9e3e` / #59).  
- 2026-07-19: **COMPLETE** — `forms.builder.draft_persistence.v1`; P2.5 UI gate READY.
