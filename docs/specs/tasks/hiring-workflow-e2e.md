# Hiring workflow E2E

**Status:** **ACTIVE** — HE-3. Eligibility Composition Gate **PASS**. SoT: [hiring-eligibility-composition.md](../architecture/hiring-eligibility-composition.md) (`hiring_eligibility_composition.v1`). Parent: [hiring-acceptance-contract.md](../architecture/hiring-acceptance-contract.md) (`hiring_acceptance.v1`). Stage Authority Consumption Gate **PASS**. Hiring Acceptance Contract Gate **PASS**. HE-4 feat locked. External Intake program **DONE**.
**Phase class:** platform
**Branch (docs):** `docs/hiring-acceptance-he1-contract-seal`
**Branch (code):** `feat/hiring-e2e-he3-eligibility-composition`
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) (blocker 4) · [Release Readiness Gate](../gates/release-readiness-gate.md) · [Acceptance suite RS-7](../journeys/release-readiness-acceptance-suite.md) · [Requirement Policy Management](requirement-policy-management.md) · [Lifecycle Identity](lifecycle-identity-l0-contract-seal.md) · [ADR-037](../architecture/ADR-037-lifecycle-identity-canon.md) · [CL7 Engine evaluation](entity-field-composition-cl7-engine-eval.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md)
**Estimate:** 4–6 slices (1 slice = one docs PR + one feat PR)

> v1 blocker 4: **one candidate walks `stage → requirements/docs → eligibility → transfer`.**
> Acceptance **over existing** funnels, gates, policy authority and transfer — explicitly **not a new Hiring Product**, not a funnel builder, not a workflow engine.
> **Not** Requirement Policy Management (consumed). **Not** min HR handoff (that is [the next node](recruitment-hr-minimal-handoff.md)). **Not** LI-2+ Lifecycle cutover. **Not** CL8.
> RPM program close **unlocked** Hiring (policy-authority edge). Queue amendment [#388](https://github.com/igortatarynovich/HostFlow/pull/388) **scheduled** HE-1. Hiring Acceptance Contract Gate **PASS** [#389](https://github.com/igortatarynovich/HostFlow/pull/389) / `34a1db6b`. Stage Authority Consumption Gate **PASS** [#390](https://github.com/igortatarynovich/HostFlow/pull/390) / `28eb0d81`. This slice composes one eligibility decision. The requirement conjunct consumes RPM. Do not start HE-4 / RS-7 / min HR in this PR. MA-4 Cutover Gate PASS. Leftover-store deletion is not this program. min HR remains queued.
>
> **Related (not a schedule):** [Recruitment Spine Orchestrator v1](recruitment-spine-orchestrator-v1.md) (Recruitment → Ready for employment) · [Employment Spine Orchestrator v1](employment-spine-orchestrator-v1.md) (handoff → Started) · [Ready for employment contract](../architecture/ready-for-employment-contract.md) (`ready_for_employment.v1`). Separate module ownership; seamless user handoff — not one mega-orchestrator creating Employee from Recruitment.

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
| **HE-1** | Acceptance contract | `he-contract` | **Hiring Acceptance Contract Gate** ✅ — the walk is defined step by step with the authoritative answerer per step; dual-evidence disposition sealed (`candidate_evidence_binds_document_link`); “not a new Hiring Product” restated as a forbidden-implementation list; test-only seeding declared inadmissible as proof. SoT: [hiring-acceptance-contract.md](../architecture/hiring-acceptance-contract.md) (`hiring_acceptance.v1`). Not HE-2 runtime. Not min HR. Not RS-7 | External Intake program close (queue amendment) | 1 slice (docs) |
| **HE-2** | Stage authority consumption | `he-stages` | **Stage Authority Consumption Gate** ✅ — stage existence comes from the LI-1 producer for every consumer on the hiring path; legacy static list and tenant dictionary stop answering existence; order/allowed-transition semantics stated (`forward_moves_guarded_jumps_rejected`). SoT: [hiring-stage-authority-consumption.md](../architecture/hiring-stage-authority-consumption.md) (`hiring_stage_authority.v1`). Not HE-3. Not min HR. Not RS-7 | HE-1 Gate ∧ LI-1 ✅ | 1–2 slices |
| **HE-3** | Eligibility composition | `he-eligibility` | **Eligibility Composition Gate** ✅ — one composed decision with a single operator-readable reason; v1/v2 explicitly not eligibility authorities; the requirement conjunct is the RPM result (`r5_required_set`). SoT: [hiring-eligibility-composition.md](../architecture/hiring-eligibility-composition.md) (`hiring_eligibility_composition.v1`). Not RS-7. Not min HR. Not a HE-2 stage-authority change | HE-2 Gate ∧ RPM-3 Gate | 1–2 slices |
| **HE-4** | Acceptance walk proof | `he-accept` | **Hiring E2E Acceptance Gate** — RS-7 passes on an operator-configured tenant with no test-only seeding; refusal and success both demonstrated | HE-3 Gate | 1 slice |

---

## HE-1 — Acceptance contract (Gate **PASS**)

Sealed in [hiring-acceptance-contract.md](../architecture/hiring-acceptance-contract.md) (`hiring_acceptance.v1`). Nine walk steps of `stage → requirements/docs → eligibility → transfer` each have an authority or an explicit `compose_later` owner. Dual-evidence disposition: **Candidate Evidence binds Document Link** — CE is the satisfaction fact; Document Link is instance identity; RPM remains the policy write. Test-only seeding (`seed_documents_for_ready_for_handoff`, `candidate_evidence_helpers`) is inadmissible as proof. Forbidden implementation is a closed list.

Hiring Acceptance Contract Gate **PASS**. Stage steps are consumed by HE-2.

Out: new stage machine; funnel builder; workflow automation; auto-progression; HE-3 collapse; RS-7 execution; min HR.

## HE-2 — Stage authority consumption (Gate **PASS**)

Sealed in [hiring-stage-authority-consumption.md](../architecture/hiring-stage-authority-consumption.md) (`hiring_stage_authority.v1`). Production hiring-path consumers ask LI-1 `is_stage_registered` for existence. `Candidate.stage` remains occupancy. Transition-order rule `forward_moves_guarded_jumps_rejected` is production. This slice does not edit that rule.

Out: full Lifecycle cutover (LI-2+), Funnel UI rework, universalizing `FunnelStage.code`, RS-7 execution, min HR.

## HE-3 — Eligibility composition (Active Product; Gate **PASS**)

Sealed in [hiring-eligibility-composition.md](../architecture/hiring-eligibility-composition.md) (`hiring_eligibility_composition.v1`). The ten classified answerers are inputs to one decision and one operator-readable refusal. The requirement conjunct is the RPM result (`r5_required_set`). v1 and v2 are not eligibility authorities. HE-4 feat locked.

Out: re-deciding requirement policy (RPM owns that write); RS-7 / HE-4 acceptance walk; min HR; LI-2+; HE-2 stage-authority change; reopening Candidate Evidence ↔ Document Link; inherited DR1 / Mapping reds.

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

**Depends on:** RPM program close ✅ + HE-1 queue amendment [#388](https://github.com/igortatarynovich/HostFlow/pull/388) + Hiring Acceptance Contract Gate PASS [#389](https://github.com/igortatarynovich/HostFlow/pull/389) / `34a1db6b`  
**Unlocks:** HE-4 after this gate PASS — **not** started here. [Minimal Recruitment → HR handoff](recruitment-hr-minimal-handoff.md) stays behind Hiring E2E program close  
**Does not:** start HE-4 / RS-7 / LI-2+; rebuild funnels; unfreeze C2.4; create a hiring automation plane; start min HR; leftover-store deletion; RS-3; change HE-2 stage authority; inherited DR1 / Mapping reds

---

## Refs

- [Hiring Eligibility Composition](../architecture/hiring-eligibility-composition.md) — HE-3 SoT (`hiring_eligibility_composition.v1`)
- [Hiring Stage Authority Consumption](../architecture/hiring-stage-authority-consumption.md) — HE-2 SoT (`hiring_stage_authority.v1`)
- [Hiring Acceptance Contract](../architecture/hiring-acceptance-contract.md) — HE-1 SoT (`hiring_acceptance.v1`)
- [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) — blocker 4; acceptance edges
- [Acceptance suite RS-7](../journeys/release-readiness-acceptance-suite.md) — the proof this program must satisfy
- [Requirement Policy Management](requirement-policy-management.md) — the authority this program consumes (nine answerers classified there)
- [Lifecycle Identity](lifecycle-identity-l0-contract-seal.md) · [LI-1](lifecycle-identity-li1-existence-guard.md) ✅ — stage existence producer
- [CL7 Engine evaluation](entity-field-composition-cl7-engine-eval.md) ✅ — structured `ready` / `not_ready` + blockers (not boolean)

## History
- 2026-09-22: **Eligibility Composition Gate PASS.** SoT [hiring-eligibility-composition.md](../architecture/hiring-eligibility-composition.md) (`hiring_eligibility_composition.v1`). One composed decision. Requirement conjunct = RPM `r5_required_set`. v1 and v2 are not eligibility authorities. Active Product → **HE-3**. HE-4 feat locked. Do not start RS-7 / min HR in this PR. Not a HE-2 stage-authority change. Not inherited DR1 / Mapping reds. Foundation stays 🔄. HostFlow v1 is not release-ready.
- 2026-09-21: **Stage Authority Consumption Gate PASS.** SoT [hiring-stage-authority-consumption.md](../architecture/hiring-stage-authority-consumption.md) (`hiring_stage_authority.v1`). Hiring-path existence consumes LI-1. Occupancy stays `Candidate.stage`. Transition-order rule `forward_moves_guarded_jumps_rejected` is production. Active Product → **HE-2**. HE-3 feat locked. Do not start HE-3 / min HR / RS-7 in this PR. Not leftover-store deletion. Not RS-3. Not Mapping Operator Surface / DR1 Runtime inherited reds. Foundation stays 🔄. HostFlow v1 is not release-ready.
- 2026-09-21: **Hiring Acceptance Contract Gate PASS.** SoT [hiring-acceptance-contract.md](../architecture/hiring-acceptance-contract.md) (`hiring_acceptance.v1`). Nine-step walk frozen. Dual-evidence disposition = `candidate_evidence_binds_document_link`. Test-only seeding inadmissible. Forbidden-implementation list frozen. Active Product stays **HE-1**. Do not start HE-2 / min HR / RS-7 in this PR. Not leftover-store deletion. Not RS-3. Not Mapping Operator Surface / DR1 Runtime inherited reds. Foundation stays 🔄. HostFlow v1 is not release-ready.
- 2026-09-21: **Queue amendment names HE-1 Active Product.** External Intake program close recorded (`741a4b2e`; [#387](https://github.com/igortatarynovich/HostFlow/pull/387)). External Intake Acceptance Gate **PASS** (`4f454556`; [#386](https://github.com/igortatarynovich/HostFlow/pull/386)). Active Product → **[HE-1](hiring-workflow-e2e.md)** (brief; feat locked this PR). Hiring Acceptance Contract Gate **not PASS**. Do not open HE-1 contract seal in this PR. min HR remains queued. Not leftover-store deletion. Not RS-3. Not Mapping Operator Surface / DR1 Runtime inherited reds. Not P4 / P5. Foundation stays 🔄. HostFlow v1 is not release-ready.
