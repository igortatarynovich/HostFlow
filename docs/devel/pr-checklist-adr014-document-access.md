# PR review checklist — ADR-014 document access (documents-db)

**Normative architecture:** [ADR-014 — Document Hub access model](../specs/architecture/ADR-014-document-hub-access-model.md)  
**Primary invariants:** [§10 — Implementation invariants](../specs/architecture/ADR-014-document-hub-access-model.md#10-implementation-invariants) · [§11 — Acceptance scenarios](../specs/architecture/ADR-014-document-hub-access-model.md#11-acceptance-test-scenarios-implementation-criteria)  
**Phase 1 tracker:** [ADR-014 phase 1 implementation epic](../specs/architecture/ADR-014-phase1-implementation-epic.md)

---

## Merge blocker

If this PR touches **candidate documents-db** surfaces (`backend/app/modules/documents/`, resolver contract, or ADR-014 tests), the items below are **required** unless an ADR / invariants update explicitly supersedes them.

Violations are a **merge blocker** (same class as failing CI).

---

## Reviewer checklist

- [ ] **ADR-014 §10–§11** read for this change set (links above).
- [ ] **Read and mutation** endpoints that read or persist document rows obtain a **`DocumentAccessContext`** (via `DocumentAccessResolver` / the router helpers) **before** I/O on those rows.
- [ ] **`DocumentAccessResolver`** is **not** a thin façade that only proxies legacy `ensure_*` / header-only owner ACL; owner access stays on the shared owner path, workspace on the resolved slice leg.
- [ ] Resolver is **not** expanded into a **policy graph**, **DSL**, or generic **capabilities engine** (Phase 1 boundary).
- [ ] **No new module-specific document ACL** in the documents-db module (no parallel `ensure_*_document_scope` / HR / transport / finance forks; CI enforces a baseline — see `backend/scripts/check_adr014_document_access.py`).
- [ ] **Workspace** (`X-Own-Company-Id` / `own_company_id`) is used as a **resolved slice** for placement and filtering, **not** as the sole authorization source for owner access (no **“Candidate not found”** solely from workspace mismatch when the card is valid — §11-A).
- [ ] **Destructive** mutations use **`DocumentAccessResolver.resolve_for_candidate_destructive_document_mutations`** (or `_get_document_with_mutation_access(..., enforce_destructive_process_lock=True)`) so the **process lock** hook runs inside the resolver contract, not only ad hoc in handlers.

---

## Phase 2 (owner provider + decoupling)

- [ ] **`DocumentAccessResolver`** does **not** import **`backend.app.modules.documents.router`** (owner access lives in **`candidate_document_owner_access.py`**).
- [ ] **`load_candidate_documents_owner_context`** is not called from handlers or random modules — only **`candidate_document_owner_access`** (definition) and **`document_access_resolver`** (orchestration). CI enforces this.
- [ ] **`DocumentAccessContext.access_policy`** reflects **read** / **mutate** / **destructive_mutate** where applicable; visibility remains a **stub** unless ADR extends Phase 2 scope.
- [ ] **Viewer channel** — `X-Document-Viewer-Channel` contract (supported values, 422 on invalid, read filter by scope + `shared`, 404 on invisible single-doc, recruitment-only mutations unless ADR says otherwise). Optional **`document_access_trace`** / DEBUG logs only behind **`HOSTFLOW_DOCUMENT_ACCESS_DEBUG`** — see ADR-014 Phase 2 (viewer channel).

---

## Legacy / out-of-module routes

`backend/app/api/v1/candidate_documents.py` and related legacy stacks are **not** scanned by the CI script today. If this PR changes them, apply the **same** principles manually until those routes are migrated or covered by an expanded guardrail.

---

## Automation

`backend/scripts/check_adr014_document_access.py` runs in **backend-ci** on every change under `backend/**`. It scans **`app/modules/documents/`** for ACL/header anti-patterns, **resolver → router imports**, and **owner-load call sites** outside the provider + resolver. Fixing or bypassing the script without an architecture decision is **not** acceptable for merge.
