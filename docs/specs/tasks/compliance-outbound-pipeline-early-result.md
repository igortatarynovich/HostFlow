# Compliance outbound via Pipeline — early opaque result + binders

**Status:** READY TO IMPLEMENT — **Engineering / Communication track** (does not steal Acquisition Product Track)  
**Date:** 2026-07-26  
**Canon ADR:** [ADR-031](../architecture/ADR-031-compliance-outbound-requires-opaque-result.md) (**Accepted**)  
**Parents:** INV-17 · C5 · §8.0.1–8.0.2 · [C0.1b migration map](c0-1b-legacy-writers-migration-map.md) · Sales questionnaire binder  
**Trusted base:** `integration/release-product-a-b` (FF only) · `make repo-health` green before branch  
**Non-goals:** temporary SMTP exceptions · Lead as C2 result_type · allowlist growth · L0 constitution edits

> **Product rule:** without Pipeline-delivered art.14 (or `source_provided`), gated intake stays blocked.  
> **Architecture rule:** delivery only after opaque `sales_inquiry` / `application` + confirmed Result Link.

---

## 1. Problem

| Symptom | Cause |
|---------|--------|
| Inbox / freeform send → `communication_pipeline_required` / `missing_result_link` | No confirmed Result Link on most threads |
| Ops emails never send | C5 fail-closed: callers omit thread/purpose/template |
| RODO still “works” via SMTP | Legacy bypass — forbidden for new work; must migrate |
| Deadlock | Art.14 needed **before** Process; Application historically **at** Process |

ADR-031 resolves the deadlock by **early Candidate shell + Application** (Recruitment) and binders (both modules).

---

## 2. Target sequence

```text
Lead created (transport)
    │
    ├─ destination = Sales
    │     ensure SalesInquiry
    │     binder → Thread + Result Link
    │     Intent gdpr_notice / follow_up → Pipeline → SMTP adapter
    │     stamp Lead.normalized.rodo / lead_communication_v1
    │
    └─ destination = Recruitment + intent (vacancy|pool) + outbound required
          ensure Candidate shell + Application (idempotent)
          binder → Thread + Result Link
          Intent gdpr_notice / follow_up → Pipeline → SMTP adapter
          stamp Lead.normalized.rodo / lead_communication_v1
    │
Process / request_info / contacted
    └─ gates read Lead.normalized.rodo only (unchanged)
```

---

## 3. PR slices (one concern each)

No code that reintroduces bypass.

| PR | Scope | Done when |
|----|--------|-----------|
| **PR-0** | ADR-031 Accepted + doc amendments (applications-operating-model §6.3, application-creation-mvp golden rule, §8.0.1–8.0.2 delivery note, c0-1b pointers, module-catalog link) | `make docs-lint` green; this PR |
| **PR-1** | **Sales** RODO + ops binders on SalesInquiry (clone questionnaire binder shape); migrate `lead_rodo` / `lead_communications` for Sales-bound leads only; Intent path; remove those leads from SMTP for migrated events | Tests: SI ensure → authorize → send mock; allowlist does not grow; Sales Meta/webhook RODO via Pipeline |
| **PR-2** | **Recruitment** `ensure_candidate_shell_and_application_for_compliance_outbound` (or extend R4 ensure); idempotent; conflict if SI-bound; stamp `intake_result_link_v1`; **no** SMTP | Unit/API: early Application before Process when §2.4 conditions hold; duplicate_review still blocked |
| **PR-3** | **Recruitment** RODO binder + migrate `lead_rodo` (+ candidate `rodo.py` when result is Application/Candidate post-convert rules); gates unchanged | Art.14 before Process on Meta path without `send_email_for_tenant` from `lead_rodo` |
| **PR-4** | Ops emails (`application_received`, reject, moving_forward`) both destinations via binders; shrink c0-1b rows for `lead_communications` | Fail-closed becomes real send; C5 tests updated |
| **PR-5** | Remove migrated callers from legacy allowlist; harden contract test; optional: inbox Result Link backfill for threads with known opaque result (separate concern OK) | Allowlist smaller; no RODO/ops bypass |

**Do not** combine PR-2 domain creation with PR-1 Sales binders.

---

## 4. Binder contract (normative)

Each binder returns (or raises fail-closed):

| Field | Required |
|-------|----------|
| `thread_id` | yes |
| opaque `result_type` + `result_id` | yes (`sales_inquiry` \| `application`) |
| confirmed Result Link | yes |
| `communication_purpose` | yes |
| `CommunicationTemplateMetadata` | yes |
| `locale` | optional |

Reference implementation: `backend/app/modules/sales/communication/questionnaire_pipeline.py`.

Recruitment binder lives under `backend/app/modules/recruitment/communication/` — **no** Sales imports.

---

## 5. Intent / template notes

- Prefer Intent `gdpr_notice` for art.14 (`intent_registry.py`); add `application` to allowed entity types if missing.
- Template metadata: fixed keys owned by module policy (like questionnaire), or catalog when C2.1 keys exist — **no** ad-hoc template pick in Lead service.
- Auto-send from ingest: DomainEvent / command / outbox — **no** SMTP inside the same sync ingest commit (C0.0).

---

## 6. STOP conditions (block promotion)

| STOP | Remediation |
|------|-------------|
| ADR-031 not Accepted | Accept or revise — no code |
| Early Candidate shell makes Lead UI a Candidate card | UX constraint in same PR as PR-2 |
| Binder imports cross-module internals | Ownership fail — rewrite |
| New `send_email_for_tenant` caller | Reject PR |
| Process still sole Application create for Meta while RODO auto_on_lead_created | PR-2 incomplete |
| Dual SI + Application on one Lead | Conflict errors already in R4 services — keep |

---

## 7. Test plan (minimum)

1. Sales Lead + email + RODO auto → Pipeline delivery attempt; `normalized.rodo.status=sent`; no direct SMTP from `lead_rodo`.
2. Recruitment Lead + vacancy + email + RODO auto → Candidate shell + Application exist **before** Process; Result Link confirmed; Process allowed after sent.
3. `source_provided` → no outbound; Process allowed.
4. No email → `pending_channel`; Process blocked.
5. Sales-bound Lead cannot get Application ensure (conflict).
6. `duplicate_review` Lead → no Application until decision.
7. Ops `application_received` with binder → not `communication_pipeline_required` skip.
8. Allowlist growth contract test green.

---

## 8. Track placement

- **Not** Acquisition UI Cutover Product Track.
- Queue as Communication / Engineering close-out after ADR accept — see [sales-to-comms-sequential-queue.md](sales-to-comms-sequential-queue.md) Communication section.
- Does **not** unblock Stage 5 PR-2; does **not** amend Epic C Complete Gate definition except by shrinking legacy writers.

---

## History

- 2026-07-26: Created with ADR-031 — permanent path only.
