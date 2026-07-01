---
name: Document access (ADR-014)
about: PRs touching documents-db / resolver / document access tests
---

## Document access (ADR-014)

Use this template when the PR touches **`backend/app/modules/documents/`**, **`document_access_resolver`**, or **ADR-014** contract tests.

**Full checklist (merge blocker criteria):** [`docs/devel/pr-checklist-adr014-document-access.md`](docs/devel/pr-checklist-adr014-document-access.md)

**ADR-014 anchors:** [§10 — Implementation invariants](docs/specs/architecture/ADR-014-document-hub-access-model.md#10-implementation-invariants) · [§11 — Acceptance scenarios](docs/specs/architecture/ADR-014-document-hub-access-model.md#11-acceptance-test-scenarios-implementation-criteria)

### Quick confirm

- [ ] `DocumentAccessContext` before document I/O on touched read/mutation routes
- [ ] Resolver stays orchestration — not policy graph / DSL / lifecycle engine
- [ ] No new module-specific document ACL / `ensure_*_document_scope` patterns in `app/modules/documents/`
- [ ] Workspace = resolved slice, not standalone owner authorization
- [ ] Destructive paths use **`resolve_for_candidate_destructive_document_mutations`** / **`enforce_destructive_process_lock`** on document fetch
- [ ] CI script `backend/scripts/check_adr014_document_access.py` passes (runs in backend-ci)
