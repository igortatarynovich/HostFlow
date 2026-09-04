# Hiring workflow E2E

**Status:** **QUEUED** (brief only; feat locked; **not scheduled**) — Active Product is [MA-3](mapping-authority.md)
**Phase class:** platform
**Branch (docs):** `docs/v1-blocker-briefs`
**Branch (code):** none — later slices `feat/hiring-e2e-heN-…`
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) (blocker 4) · [Release Readiness Gate](../gates/release-readiness-gate.md) · [Acceptance suite RS-7](../journeys/release-readiness-acceptance-suite.md) · [Requirement Policy Management](requirement-policy-management.md) · [Lifecycle Identity](lifecycle-identity-l0-contract-seal.md) · [ADR-037](../architecture/ADR-037-lifecycle-identity-canon.md) · [CL7 Engine evaluation](entity-field-composition-cl7-engine-eval.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md)
**Estimate:** 4–6 slices (1 slice = one docs PR + one feat PR)

> v1 blocker 4: **one candidate walks `stage → requirements/docs → eligibility → transfer`.**
> Acceptance **over existing** funnels, gates, policy authority and transfer — explicitly **not a new Hiring Product**, not a funnel builder, not a workflow engine.
> **Not** Requirement Policy Management (consumed). **Not** min HR handoff (that is [the next node](recruitment-hr-minimal-handoff.md)). **Not** LI-2+ Lifecycle cutover. **Not** CL8.
> Opening this brief does **not** schedule it. RPM program close **unlocks** Hiring (policy-authority edge). Unlock ≠ schedule. The queue’s Active Product is [MA-3](mapping-authority.md).

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**
The machinery to hire exists but nobody has ever proven that **one** candidate can be walked through it on a tenant configured by an operator. Three registries answer “which stages exist” (legacy static list, tenant stage dictionary, funnel stages), ten layers answer “is this candidate eligible”, transitions between valid stages are unrestricted (`_validate_stage_transition` rejects only unknown codes), the requirement engine has a v1 hot path and a v2 path that transitions never consult, and the existing integration proof depends on test-only seeding helpers. So “can we hire?” is answered by code archaeology instead of by a scenario.

**Completion proof (named consumer):**
**RS-7 in the [acceptance suite](../journeys/release-readiness-acceptance-suite.md)**: on a tenant configured through product surfaces (RS-1), one candidate progresses through the operator-defined stages; transfer is **refused with a readable reason** while a requirement is unmet, and completes once satisfied — and the refusal comes from the same policy authority the operator manages in RS-4, not from a separate hard-coded rule. What this consumer must **not** fork: a hiring-specific eligibility rule set that answers requirement questions outside the [RPM](requirement-policy-management.md) authority.

**False close (reject):** a green integration test that seeds documents directly (`seed_documents_for_ready_for_handoff`) instead of walking product surfaces; a new stage machine or funnel builder; declaring PASS while the refusal reason is only a 409 code with no operator-readable explanation; treating `GET /transfer-readiness` as the acceptance proof; absorbing the HR handoff blocker.

---

## Starting point (measured, not assumed)

Evidence collected 2026-08-28.

### Already provable today

| Capability | Where |
|------------|-------|
| Funnel-backed stages mapped to process-engine stages | `models/funnel.py` (`stage_contract_v1`, `pe_maps_to_module`, `pe_maps_to_code`), `process_engine/pipeline_mapping.py` |
| Forward-move guards (documents, vacancy, contact attempts) | `services/candidate_doc_pipeline_guard.py` — backward/same-index moves always allowed |
| `ready_for_handoff` entry gate | `api/v1/candidates/service.py` → `TransitionEvaluatorAdapter.assert_transition_allowed` |
| Canonical transfer decision | `services/transfer_policy_resolver.py` — `transfer_allowed = handoff_allowed ∧ readiness_ok ∧ docs_ready ∧ package_ready ∧ no_required_confirmations ∧ ops_ready` |
| Operator-visible readiness | `GET /candidates/{id}/transfer-readiness`; candidate card transfer-readiness section |
| Refusal surfaced in UI | `handoff_docs_incomplete` handled in `CandidateCard.tsx` |

### Structural problems this program must close

| # | Problem | Evidence |
|---|---------|----------|
| **1** | **Three stage registries.** Static `new → hired` list, tenant `candidate_stages` dictionary, funnel `funnel_stages` | `api/v1/stages.py`, `models/candidate_stage.py`, `models/funnel.py` — LI-1 ✅ [#300](https://github.com/igortatarynovich/HostFlow/pull/300) established one existence producer; consumers were not cut over |
| **2** | **Ten eligibility answerers** on the transfer path (transfer policy, workforce packs, package readiness, field requirements, requirement rules v1 + document runtime, operational requirements, handoff routing, pipeline gates, candidate evidence, legacy doc-type blockers) | `transfer_policy_resolver.py` and the services it composes |
| **3** | **Requirement engine v1 / v2 split.** `evaluate_candidate_requirements_v2` runs in migration/audit and event paths; transitions use v1 | `requirement_rules/evaluation/candidate_bridge.py` vs `requirement_rules/evaluator.py` |
| **4** | **Arbitrary stage jumps allowed** between valid codes; only a subset of forward moves is guarded | `api/v1/candidates/helpers.py` — “Любые переходы между валидными стадиями разрешены” |
| **5** | **Dual evidence model.** Requirement slots read `candidate_evidence`; Hub / pack paths read `documents` + `document_entity_links` | `services/candidate_evidence_service.py` vs `models/document_entity_link.py` |
| **6** | **No proof without test helpers** — the existing E2E depends on seeding shortcuts | `tests/…/test_handoff_internal_hr.py`, `candidate_evidence_helpers` |

Problems 2, 3 and 5 are **partly RPM’s write authority**: RPM-3 classifies and cuts over requirement-policy consumers. This program must **consume** that outcome and prove the walk — it must not re-answer requirement policy.

---

## Internal ladder (this program only)

```text
HE-1 Acceptance contract (which authority answers which step)
  → HE-2 Stage authority consumption (three registries → one)
  → HE-3 Eligibility answer collapse (one readable refusal)
  → HE-4 Acceptance walk proof (RS-7, no test-only helpers)
  → Hiring E2E program close (outcome + release delta)
```

| # | Slice | Machine id | Named gate (PASS =) | Depends on | Estimate |
|---|-------|------------|---------------------|------------|----------|
| **HE-1** | Acceptance contract | `he-contract` | **Hiring Acceptance Contract Gate** — the walk is defined step by step with the authoritative answerer per step; “not a new Hiring Product” restated as a forbidden-implementation list; test-only seeding declared inadmissible as proof | RPM program close (queue amendment) | 1 slice (docs) |
| **HE-2** | Stage authority consumption | `he-stages` | **Stage Authority Consumption Gate** — stage existence comes from the LI-1 producer for every consumer on the hiring path; legacy static list and tenant dictionary stop answering existence; order/allowed-transition semantics stated (even if “all forward moves guarded, jumps rejected”) | HE-1 Gate ∧ LI-1 ✅ | 1–2 slices |
| **HE-3** | Eligibility answer collapse | `he-eligibility` | **Eligibility Answer Gate** — one composed decision with a single operator-readable reason; v1/v2 engine split resolved or explicitly contracted; the answer is the RPM authority’s result, not a parallel rule set | HE-2 Gate ∧ RPM-3 Gate | 1–2 slices |
| **HE-4** | Acceptance walk proof | `he-accept` | **Hiring E2E Acceptance Gate** — RS-7 passes on an operator-configured tenant with no test-only seeding; refusal and success both demonstrated | HE-3 Gate | 1 slice |

---

## HE-1 — Acceptance contract (queued, docs only)

Defines, per step of `stage → requirements/docs → eligibility → transfer`, which component is the authority and which components are consumers. Also fixes the dual-evidence disposition for the hiring path: whether requirement satisfaction is answered by `candidate_evidence`, by Document Link, or by an explicit contract between them — a decision this program **must not** leave open, because RS-5 and RS-7 both depend on it.

Out: new stage machine; funnel builder; workflow automation; auto-progression.

## HE-2 — Stage authority consumption (queued)

LI-1 created one existence producer; this slice makes the hiring path consume it and states the transition-order rule. Out: full Lifecycle cutover (LI-2+), Funnel UI rework, universalizing `FunnelStage.code`.

## HE-3 — Eligibility answer collapse (queued)

Ten answerers must produce one decision with one reason an operator can read. Anything that remains a separate answerer must be named with owner and expiry. Out: re-deciding requirement policy (RPM owns that write).

## HE-4 — Acceptance walk proof (queued)

The proof is a walk, not a suite. If a step still needs a developer, the gate is STOP.

---

## Program close = two results

| Field | Meaning |
|-------|---------|
| **Program outcome** | One candidate can be walked from intake stage to completed transfer on operator-configured stages, with one eligibility decision and one readable refusal |
| **Release delta** | Hiring workflow E2E four-checks PASS. Minimal Recruitment → HR handoff becomes provable (its acceptance edge — a completed hire — is satisfied). HostFlow v1 is not release-ready until the [Release Readiness Gate](../gates/release-readiness-gate.md) passes |

---

## Queue position

**Depends on:** RPM program close ✅ (known acceptance edge: Hiring acceptance walks against policy authority) + a later queue amendment  
**Unlocks:** [Minimal Recruitment → HR handoff](recruitment-hr-minimal-handoff.md) acceptance  
**Does not:** schedule itself this amendment; start LI-2+; rebuild funnels; unfreeze C2.4; create a hiring automation plane

---

## Refs

- [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) — blocker 4; acceptance edges
- [Acceptance suite RS-7](../journeys/release-readiness-acceptance-suite.md) — the proof this program must satisfy
- [Requirement Policy Management](requirement-policy-management.md) — the authority this program consumes (nine answerers classified there)
- [Lifecycle Identity](lifecycle-identity-l0-contract-seal.md) · [LI-1](lifecycle-identity-li1-existence-guard.md) ✅ — stage existence producer
- [CL7 Engine evaluation](entity-field-composition-cl7-engine-eval.md) ✅ — structured `ready` / `not_ready` + blockers (not boolean)
