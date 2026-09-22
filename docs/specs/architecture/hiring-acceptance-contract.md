# Hiring Acceptance Contract

**Status:** **Accepted** (L2 contract — Hiring Acceptance Contract Gate)  
**Date:** 2026-09-21  
**Trusted base:** `integration/release-product-a-b` @ `d8d619f1`  
**Related:** [`../tasks/hiring-workflow-e2e.md`](../tasks/hiring-workflow-e2e.md) · [`hiring-eligibility-composition.md`](hiring-eligibility-composition.md) · [`hiring-stage-authority-consumption.md`](hiring-stage-authority-consumption.md) · [`ADR-016`](ADR-016-requirement-evidence-document-separation.md) · [`ADR-037`](ADR-037-lifecycle-identity-canon.md) · [`requirement-policy-authority.md`](requirement-policy-authority.md) · [`ready-for-employment-contract.md`](ready-for-employment-contract.md) · [`../tasks/lifecycle-identity-li1-existence-guard.md`](../tasks/lifecycle-identity-li1-existence-guard.md) · [`../tasks/documents-platform-e4-candidate-document-link.md`](../tasks/documents-platform-e4-candidate-document-link.md) · [`../journeys/release-readiness-acceptance-suite.md`](../journeys/release-readiness-acceptance-suite.md) (RS-7)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (owners stay on existing capabilities), **INV-01** (one SoT per walk step), **INV-16** (contract before HE-2 consumption). Does not rewrite L0. Does not mint a Hiring Product, a second stage registry, or a hiring-owned eligibility rule set.

> This file is the **SoT** for the Hiring acceptance walk.  
> It does **not** implement Hiring. It names which existing authority answers each step.  
> Machine copy: `hiring_acceptance.v1` in `backend/app/reference/hiring_acceptance.py`.  
> [RS-7](../journeys/release-readiness-acceptance-suite.md) remains the named consumer of the **program**. This gate proves the **contract**, not the walk.

---

## Operator question (one)

For one candidate on an operator-configured tenant, **which authority answers each step of `stage → requirements/docs → eligibility → transfer`**, what is the `candidate_evidence` ↔ Document Link disposition, and what evidence is admissible as production proof of that walk?

No second question is this contract. Requirement Policy write, Mapping, External Intake, min HR, LI-2+ Lifecycle cutover, and RS-7 execution are other programs.

---

## Walk (frozen — nine steps)

The four-phase walk is not four authorities. Each phase splits into the questions an operator actually hits. A later HE slice may **consume** or **collapse** a leftover. It may not add a tenth walk step or a second authority for a sealed step.

| # | Step | Phase | Operator question | Authority | Role now | Later |
|---|------|-------|-------------------|-----------|----------|-------|
| 1 | **Stage existence** | stage | Which stages exist for this hiring path? | LI-1 `is_stage_registered` | **authority** | HE-2 consumed — [hiring-stage-authority-consumption.md](hiring-stage-authority-consumption.md) |
| 2 | **Stage occupancy** | stage | Which stage is this candidate on? | Candidate occupancy (`Candidate.stage`) | **authority** | HE-2 consumed; Funnel ≠ occupancy (ADR-037) |
| 3 | **Stage transition** | stage | May this candidate move A→B? | Transition-order rule `forward_moves_guarded_jumps_rejected` | **authority** | HE-2 consumed |
| 4 | **Requirement policy** | requirements/docs | Must this candidate provide type X? | [RPM](requirement-policy-authority.md) `requirement_policy_authority.v1` | **authority** | none — Hiring **consumes**, never writes |
| 5 | **Document request** | requirements/docs | What outstanding ask exists? | Hub outstanding ask (E7 / DR1) | **authority** | no hiring request table |
| 6 | **Document instance** | requirements/docs | Does a document exist, and is it valid? | Document Hub + Document Link (E4) + expiry (E6) | **authority** | not `candidate_id`; not CE as a file store |
| 7 | **Requirement satisfaction** | requirements/docs | Is requirement R satisfied? | Candidate Evidence **bound to** Document Link instance(s) ([ADR-016](ADR-016-requirement-evidence-document-separation.md)) | **authority** | none — disposition sealed here |
| 8 | **Eligibility** | eligibility | May this candidate transfer, and why not if refused? | [HE-3 composer](hiring-eligibility-composition.md) consuming RPM | **consume** | Eligibility Composition Gate **PASS** — one refusal; requirement conjunct = RPM |
| 9 | **Transfer complete** | transfer | Is the Recruitment hire complete? | Recruitment emit of [`ready_for_employment.v1`](ready-for-employment-contract.md) | **authority** | HE-4 proves the walk; min HR (HH) is **not this walk** |

Roles are closed: `authority` · `consume` · `leftover` · `compose_later` · `not_this_walk`.

```text
stage existence (LI-1)
  → occupancy (candidate)
  → transition order (HE-2)
  → RPM policy (must provide type X?)
  → Hub outstanding ask
  → Document Link instance + Hub validity
  → Candidate Evidence bound to that link
  → eligibility (RPM result in; HE-3 composes one readable refusal)
  → transfer emit ready_for_employment.v1
```

**Existence ≠ occupancy ≠ allowed transition.** Funnel stages, the static `new → hired` list, and the tenant `candidate_stages` dictionary are **leftover existence answerers**. HE-2 cut hiring-path consumers over to LI-1 and stated the order rule (`forward_moves_guarded_jumps_rejected`). This contract forbids treating any leftover as existence SoT.

---

## Disposition: `candidate_evidence` ↔ Document Link

This is the decision [ADR-016](ADR-016-requirement-evidence-document-separation.md) left open for the hiring path. It is **not** “pick one store”. RS-5 and RS-7 both depend on the split.

| Layer | Answers | Does not answer |
|-------|---------|-----------------|
| **RPM** | Must this candidate provide type X? | Whether a file exists |
| **Hub outstanding ask** | What is requested | Whether the requirement is satisfied |
| **Document Link** (`document_entity_links`) | Instance identity: this Hub document is linked to this candidate | Requirement policy; satisfaction |
| **Candidate Evidence** | Satisfaction fact: requirement R is fulfilled via variant V using Document Link instance(s) D | File storage; “must provide X?” |

Machine id: `candidate_evidence_binds_document_link`.

**Normative rules:**

1. For a **document-kind** requirement on the hiring path, production satisfaction is a Candidate Evidence row that **names** Hub Document Link instance(s).  
2. A Document Link row without Candidate Evidence is instance existence, not requirement satisfaction.  
3. Candidate Evidence without a Document Link is **not** admissible production evidence for a document-kind requirement.  
4. Candidate Evidence is **not** a second document store. Document Link is **not** requirement policy and **not** the eligibility composer.  
5. Hub / pack paths that still read `documents` + `document_entity_links` without the CE bind are leftover **consume** paths, not a second satisfaction SoT.

False close: declaring Document Link “the evidence model”; declaring `candidate_evidence` “the document store”; leaving RS-5 and RS-7 on different stores.

---

## Eligibility leftovers (frozen — ten rows)

HE-3 collapses these into one composed decision with one operator-readable reason. HE-1 **classifies** them. It does not retire them and does not mint an eleventh answerer.

The requirement-shaped conjunct of eligibility **is** the RPM authority’s result. A hiring-specific rule that re-answers “must provide type X?” is forbidden.

| # | Live answerer | HE role | Evidence (paths) |
|---|---------------|---------|------------------|
| 1 | Transfer policy composer | **Leftover** (today’s aggregator; not the sealed composer) | `backend/app/services/transfer_policy_resolver.py` |
| 2 | Workforce packs | **Leftover** | `backend/app/services/workforce_eligibility_delivery_contract.py` |
| 3 | Package readiness | **Leftover** | `backend/app/services/recruitment_package_readiness.py` |
| 4 | Field requirements | **Leftover** | `backend/app/field_registry/requirement_evaluator.py` |
| 5 | Requirement rules v1 (transition hot path) | **Leftover** | `backend/app/requirement_rules/evaluator.py` |
| 6 | Requirement rules v2 (audit / event path) | **Leftover** | `backend/app/requirement_rules/evaluation/candidate_bridge.py` |
| 7 | Operational requirements | **Consume** | `transfer_policy_resolver.py` |
| 8 | Handoff routing / tenant link | **Leftover** | `transfer_policy_resolver.py` |
| 9 | Hiring pipeline gates | **Leftover** | `backend/app/services/hiring_pipeline_gates.py` |
| 10 | Legacy doc-type blockers | **Leftover** | `backend/app/services/candidate_doc_pipeline_guard.py` |

The v1 / v2 engine split is **classified**, not resolved. HE-3 either retires one path or writes an explicit contract. Candidate Evidence is the **satisfaction** authority (step 7), not an eleventh eligibility writer.

`GET /candidates/{id}/transfer-readiness` is an operator-visible readout of the leftover composer. It is **not** the acceptance proof.

---

## Admissible production evidence

RS-7 (HE-4) may only cite evidence that an operator produced on product surfaces of an RS-1 tenant.

| Admissible | Meaning |
|------------|---------|
| RS-1 operator-configured tenant | No developer participated in setup |
| Product-surface stage moves | Stage history the operator created |
| Product-surface document request → provide → accept | RS-5 path; Hub ask + Link + CE bind |
| Document Link row | Instance identity |
| Candidate Evidence bound to that link | Satisfaction fact |
| Operator-readable refusal from RPM | Same policy the operator manages in RS-4 — not a bare 409 |
| Stage history | Occupancy trail |
| Transfer completion record | `ready_for_employment.v1` emit / hire complete |

## Inadmissible as proof

| Inadmissible | Why |
|--------------|-----|
| `seed_documents_for_ready_for_handoff` | Test-only seeding; skips product surfaces |
| `candidate_evidence_helpers` | Test-only satisfaction; skips Document Link bind |
| SQL / fixture document inserts | Not an operator walk |
| `GET /transfer-readiness` as the proof | Readout of a leftover composer, not RS-7 |
| HTTP 409 without a readable reason | Operator cannot act |

Paths named so the gate can refuse them: `backend/tests/test_support/candidate_handoff_gate.py`, `backend/tests/test_support/candidate_evidence_helpers.py`.

---

## Forbidden implementation

This restates “not a new Hiring Product” as a closed list. A later HE slice may not do any of these “while we are here”.

- New Hiring Product, funnel builder, workflow engine, or auto-progression  
- New stage machine (LI-1 already produces existence)  
- Min HR / HH handoff (that is [the next node](../tasks/recruitment-hr-minimal-handoff.md))  
- HE-2 runtime, HE-3 collapse, or RS-7 execution in this PR  
- Fixing inherited DR1 Runtime / Mapping Operator Surface reds  
- A hiring-specific eligibility rule set outside RPM  
- A tenth write of the RPM operator question  
- Treating Candidate Evidence as a file store  
- Treating Document Link as requirement policy  
- Declaring PASS on a 409 with no operator-readable explanation  
- Treating `GET /transfer-readiness` as the acceptance proof  

---

## Architecture review (L0 — ten questions)

| # | Answer |
|---|--------|
| 1 | **Owner:** this contract names the walk. Stage existence stays LI-1. Requirement policy stays RPM. Document instance stays Document Hub / E4. Satisfaction stays Candidate Evidence bound to Document Link. Transfer emit stays Recruitment `ready_for_employment.v1`. Recruitment **consumes**; it does not mint a Hiring Product. |
| 2 | Not a new capability. Collapses “who answers the walk?” into one SoT. Does not mint a workflow engine. |
| 3 | No new adapter. Documents stay `documents.hub_adapter_v1`. Transfer package stays `ready_for_employment.v1`. |
| 4 | No HE-2 cutover, no HE-3 collapse, no RS-7 execution, no min HR, no new stage machine, no CL8, no Catalog rewrite. |
| 5 | No new Manifest keys. Hiring pipeline gates remain leftover, not a second overlay product. |
| 6 | SoT for the walk = this file + `hiring_acceptance.v1`. Leftover answerers are classified, not blessed. |
| 7 | No new event family. |
| 8 | **Requires:** LI-1 ✅, RPM program DONE, E4 Document Link ✅, E7 outstanding ask ✅, `ready_for_employment.v1`. **Optional:** HE-2 / HE-3 / HE-4 as later slices. |
| 9 | No new licence. |
| 10 | Public contract **additive**: walk classification + evidence disposition. No breaking Hub/Passport change. |

**INV-01:** one SoT per walk-step question. **INV-16:** this contract before HE-2 consumption.

---

## False close

Reject: a new Hiring Product; sealing the walk while leaving `candidate_evidence` vs Document Link open; treating test seeding as RS-7; collapsing eligibility in this PR; starting HE-2 runtime; absorbing min HR; declaring `GET /transfer-readiness` the proof; a tenth RPM write; Foundation ✅; a tenth walk step.

---

## Consequences

- HE-2 consumes LI-1 on every hiring-path existence reader and states the transition-order rule — [hiring-stage-authority-consumption.md](hiring-stage-authority-consumption.md) (**PASS**).  
- HE-3 composes one eligibility decision with one operator-readable reason; the requirement conjunct is RPM — [hiring-eligibility-composition.md](hiring-eligibility-composition.md) (**PASS**).  
- HE-4 walks RS-7 on an RS-1 tenant with no inadmissible seeding.  
- Min HR stays queued until Hiring E2E program close.

---

## History

- 2026-09-22: Eligibility Composition Gate **PASS**. Eligibility step consumes `hiring_eligibility_composition.v1`. Requirement conjunct = RPM. Active Product → **HE-3**. HE-4 feat locked. min HR remains queued.
- 2026-09-21: Stage Authority Consumption Gate **PASS**. Hiring-path existence consumes LI-1. Occupancy stays `Candidate.stage`. Transition-order rule is production. Active Product → **HE-2**. HE-3 feat locked. min HR remains queued.
- 2026-09-21: Accepted as HE-1 Acceptance contract. Nine-step walk frozen. Dual-evidence disposition = `candidate_evidence_binds_document_link`. Named CI + boundary. Feat locked for HE-2. Active Product stays **HE-1**. min HR remains queued.
