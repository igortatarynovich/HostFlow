# Ready for employment contract

**Status:** **Accepted** (L2 contract — Recruitment Orchestrator Contract Gate / RSO-1)  
**Date:** 2026-09-09  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`../tasks/recruitment-spine-orchestrator-v1.md`](../tasks/recruitment-spine-orchestrator-v1.md) · [`../tasks/employment-spine-orchestrator-v1.md`](../tasks/employment-spine-orchestrator-v1.md) · [`../tasks/recruitment-hr-minimal-handoff.md`](../tasks/recruitment-hr-minimal-handoff.md) · [`../tasks/hiring-workflow-e2e.md`](../tasks/hiring-workflow-e2e.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (Recruitment owns emit; Employment owns accept/employ) and **INV-16** (contract before a second handoff shape). Does not rewrite L0. Does not mint Employee from Recruitment.

> This file is the **SoT** for the inter-module handoff package between Recruitment and Employment.  
> Machine copy: `ready_for_employment.v1` in `backend/app/reference/ready_for_employment.py`.  
> Legacy `build_handoff_snapshot_payload_v1` is **not** this contract; cutover is a later runtime slice.  
> Gate tests: `backend/tests/platform/test_ready_for_employment_contract_gate.py`.

---

## Operator question (one)

When Recruitment decides a person **fits** this vacancy/employer context, **what immutable package** must be emitted so Employment can continue without re-running Recruitment — and without the operator servicing the module boundary?

No second question is this contract. Employability / legalization pathway, Employee create, Started, Mapping Authority, and Forms Publish are other programs.

---

## Three acceptance gates (every subsequent change)

These gates bind **all** RSO/ESO work. A change that passes module ownership but fails UX reuse is still a FAIL.

1. **RSO does not know how to employ.**  
   Recruitment’s terminal result is a **valid** Ready for employment handoff package (`ready_for_employment.v1`). It does not create Employee, accept handoff, choose legalization pathway, or own employment missing.

2. **ESO does not re-ask Recruitment.**  
   Facts and evidence already authoritative in the package are **reused**. Additional prompts are **employment missing** only. Re-prompting citizenship, employer/vacancy, or documents that the package already carries — without a documented conflict reason — is a product FAIL.  
   Domain boundary splits **responsibility**, not data for the user.

3. **Operator does not service the boundary.**  
   The operator presses **Передать на трудоустройство** and continues with the **same person**. Package emit, audit transition, owner switch, and Employment initialization are **internal**. Ritual Accept / re-entry screens are forbidden when gates already pass.

Machine ids: `rso_terminal_is_package` · `eso_reuses_package_no_reask` · `operator_does_not_service_boundary`.

---

## Write / emit authority

| May emit | Must not emit / must not do |
|----------|-----------------------------|
| Recruitment builds and emits `ready_for_employment.v1` | Recruitment creates Employee |
| Audit: Recruitment completed for this application | Recruitment calls Employment accept as its own completion |
| Package carries recruitment facts + evidence refs | Package carries employment missing shopping lists or legalization SoT |
| Employment **reads** the package as input | Employment re-asks package facts without conflict reason |

Accept / reject / auto-accept after emit is **Employment policy** (ESO-1+), not Recruitment.

---

## Package shape (frozen logical blocks)

`contract_id` MUST be `ready_for_employment.v1`.

| Block | Required | Contents |
|-------|----------|----------|
| `tenant_id` | yes | Tenant scope |
| `person` | yes | Stable person/candidate id + identity facts already used for fit |
| `target_work` | yes | Vacancy and/or employer (+ optional role label) the person was selected for |
| `recruitment_facts` | yes | Facts confirmed for **fit / qualification** only (object; may be empty `{}` only if fit needed none) |
| `evidence` | yes | Provenance refs (source, documents already on Person, call outcomes, etc.) |
| `fits_decision` | yes | `decision=fits`, `decided_at`, `actor_id` |
| `context_refs` | yes | At least `application_id`; optional source/recruiter ids |

### Forbidden top-level keys (Recruitment must not place these on the package)

`employee_id`, `employment_missing`, `legalization_pathway`, `zus_journey`, `create_employee`, `accept_handoff`

These belong to Employment runtime or later Employment contracts.

### Missing-data split (hard)

| Kind | Owner | Allowed |
|------|-------|---------|
| **Recruitment missing** | Recruitment | Only what is required to decide Fits and assemble a **correct** package |
| **Employment missing** | Employment | Employability, legalization, contract, formalize |

**Forbidden:** Recruitment collecting the full employment/legalization document set “just in case”.

---

## Delivery UX constraint (gate 3)

Operator-visible action: **Передать на трудоустройство**.

Internal (not operator chores): validate + emit package → audit Recruitment completed → Employment init under Employment policy → continue same person surface.

False closes: status-only “ready” without package; operator copy-paste between modules; Create candidate / Bind / ritual Accept as the handoff path.

---

## Non-goals

- Runtime emit cutover from legacy handoff snapshot (later slice).  
- Employment accept policy / early employability SoT (ESO).  
- Mapping Authority.  
- Merging Recruitment + Employment into one orchestrator.

---

## Completion of RSO-1

**PASS** when this document + `ready_for_employment.v1` + gate tests exist, and both RSO/ESO briefs name the three acceptance gates. Runtime happy path is **RSO-2**, not this gate.
