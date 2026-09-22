# Hiring Eligibility Composition

**Status:** **Accepted** (L2 contract — Eligibility Composition Gate)  
**Date:** 2026-09-22  
**Trusted base:** `integration/release-product-a-b` @ `28eb0d81`  
**Related:** [`hiring-acceptance-contract.md`](hiring-acceptance-contract.md) (`hiring_acceptance.v1`) · [`hiring-stage-authority-consumption.md`](hiring-stage-authority-consumption.md) · [`requirement-policy-authority.md`](requirement-policy-authority.md) · [`../tasks/hiring-workflow-e2e.md`](../tasks/hiring-workflow-e2e.md) · [`ADR-016`](ADR-016-requirement-evidence-document-separation.md) · [`ADR-018`](ADR-018-requirement-policy-evaluation-model.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (RPM stays the requirement-policy owner), **INV-01** (one eligibility decision), **INV-16** (HE-1 classification before this composition). Does not rewrite L0. Does not mint a Hiring Product or a Hiring-owned policy write. Not a new Hiring Product.

> This file is the **SoT** for HE-3: the eligibility step of the hiring walk is one composed decision.  
> Parent walk classification stays [hiring-acceptance-contract.md](hiring-acceptance-contract.md).  
> Machine copy: `hiring_eligibility_composition.v1` in `backend/app/reference/hiring_eligibility_composition.py`.  
> This slice does **not** execute RS-7, open min HR, or change HE-2 stage authority. Not a new Hiring Product.

---

## Operator question (eligibility step only)

May this candidate transfer, and if not, what **one** reason can an operator read?

Stage existence, occupancy, and transition order stay on [hiring-stage-authority-consumption.md](hiring-stage-authority-consumption.md). `candidate_evidence` ↔ Document Link stays `candidate_evidence_binds_document_link`. Transfer emit stays `ready_for_employment.v1` (HE-4).

---

## One decision

Machine id: `hiring_eligibility_composition.v1`.

```text
allowed: bool
refusal_reason: one operator-readable sentence, or none when allowed
requirement_conjunct.source = rpm_result
requirement_conjunct.api = r5_required_set
```

The ten HE-1 eligibility answerers are **inputs**. They do not each publish a transfer answer.

| Classified answerer | After HE-3 |
|----------------------|------------|
| Transfer policy composer | Replaced by this composer. The resolver calls `compose_hiring_eligibility`. |
| Workforce packs | Non-requirement conjunct (handoff / readiness). Does not answer “must provide type X?”. |
| Package readiness | Non-requirement conjunct (dossier / recruiter confirmation). |
| Field requirements | Non-requirement conjunct (missing candidate data). |
| Requirement rules v1 | **Not an eligibility authority.** Hot path stays; it does not add required types. |
| Requirement rules v2 | **Not an eligibility authority.** Audit / event path stays; the composer does not call it. |
| Operational requirements | Consume conjunct. |
| Handoff routing | Conjunct only for the destination question. Eligibility itself does not wait on a destination. |
| Hiring pipeline gates | Not an eligibility authority. Stage-order rule stays HE-2. |
| Legacy doc-type blockers | Not an eligibility authority. A forward-move document block refuses only for types in the RPM result. |

Engine split, explicit contract: `v1_and_v2_not_eligibility_authorities`. HE-3 does not retire either engine. It stops both from answering the eligibility question.

---

## Requirement conjunct

The requirement-shaped conjunct **is** the RPM result: `r5_required_set` (`requirement_policy_consumer_parity.v1`).

1. Unmet codes must be members of that set. A code outside it is rejected. That is not a new Hiring write of “must provide type X?”.  
2. Pack-only or v1-only document codes do not enter the conjunct and do not produce the requirement refusal.  
3. The refusal, when the conjunct fails, is one sentence: `Required document is missing: <code>` or `Required documents are missing: <codes>`.  
4. If the conjunct passes and another conjunct fails, the operator still sees **one** reason, the first failure in workforce → package → fields → operational requirements.  
5. Candidate Evidence remains the satisfaction authority (HE-1 step 7). This slice does not reopen that disposition.

---

## Hiring-path consumers

- `backend/app/services/transfer_policy_resolver.py` — `transfer_allowed` is the composed decision. `assert_transfer_allowed` returns that `refusal_reason`.  
- `backend/app/process_engine/evaluator_adapter.py` — recruitment transition refusal uses the same reason.  
- `backend/app/services/candidate_doc_pipeline_guard.py` — legacy doc-type forward block calls the composer and refuses only for the RPM intersection. HE-2 `hiring_stage_exists` consumption is unchanged. Requirement-fulfillment blocks stay a satisfaction consume, not a second policy write.

`GET /transfer-readiness` remains a readout. It is not RS-7.

---

## Architecture review (L0 — ten questions)

| # | Answer |
|---|--------|
| 1 | **Owner:** requirement policy stays RPM. The composer consumes that result. Recruitment does not mint a Hiring policy authority. |
| 2 | Not a new capability. Collapses ten classified answerers into one decision. |
| 3 | No new adapter. Requirement API remains `r5_required_set`. |
| 4 | No RS-7, no HE-4 walk, no min HR, no LI-2+, no HE-2 stage-authority edit, no DR1 / Mapping inherited-red fix, no new stage machine. |
| 5 | No new Manifest keys. Pipeline gates stay configuration. |
| 6 | SoT for the eligibility question = this file + `hiring_eligibility_composition.v1`. Parent walk SoT remains `hiring_acceptance.v1`. |
| 7 | No new event family. |
| 8 | **Requires:** HE-1 Gate PASS, HE-2 Gate PASS, RPM program DONE. |
| 9 | No new licence. |
| 10 | Public contract **additive**: transfer refusal carries one `refusal_reason`. No breaking Hub/Passport change. |

**INV-01:** one eligibility decision. **INV-16:** HE-1 classification before this composition.

---

## False close

Reject: a Hiring-owned required-document list; leaving v1 and v2 as parallel eligibility answers; a 409 whose only text is `transfer_blocked`; executing RS-7; opening min HR; editing LI-1 existence or the HE-2 transition-order rule; reopening `candidate_evidence` ↔ Document Link; Foundation ✅.

---

## Consequences

- HE-4 walks RS-7. Feat `feat/hiring-e2e-he4-acceptance-walk` is open. Hiring E2E Acceptance Gate is **not PASS**. This stamp does not execute RS-7.  
- Min HR stays queued until Hiring E2E program close.  
- Inherited DR1 Runtime and Mapping Operator Surface reds stay out of this slice.

---

## History

- 2026-09-22: **HE-4 Acceptance walk feat opened.** Active Product → **HE-4**. Feat `feat/hiring-e2e-he4-acceptance-walk` from `8d5a9fef`. Hiring E2E Acceptance Gate **not PASS**. RS-7 is not executed. min HR remains queued. Not a change to this composition contract.
- 2026-09-22: Eligibility Composition Gate **PASS**. One composed decision. Requirement conjunct = RPM `r5_required_set`. v1 and v2 are not eligibility authorities. Active Product → **HE-3**. HE-4 feat locked. Do not start RS-7 / min HR in this PR. Not a HE-2 stage-authority change. Not inherited DR1 / Mapping reds. Foundation stays 🔄. HostFlow v1 is not release-ready.
