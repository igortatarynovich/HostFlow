# Entity Field Composition CL7 — Requirement Engine evaluation

**Status:** **PASS** [#309](https://github.com/igortatarynovich/HostFlow/pull/309) / `6f2289f1`  
**Phase class:** platform  
**Branch (docs):** `docs/queue-post-cl6-amendment`  
**Branch (code):** `feat/entity-field-composition-cl7-engine-eval`  
**Parents:** [CL0 contract seal](entity-field-composition-cl0-contract-seal.md) · [CL2 membership](entity-field-composition-cl2-membership.md) · [CL6 Flight mapping](entity-field-composition-cl6-flight-map.md) · [Requirement Rules Engine P0](../platform/requirement-rules-engine-p0.md) · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) · [Sequential queue](sales-to-comms-sequential-queue.md)

> CL7 **evaluates** (`evaluate(entity, profile, vacancy, process_point)` → structured `ready` | `not_ready` + `blockers[]`). Engine is **not** an Entity Profile implementation — Profile may only ref. Four kinds stay: Presence / Value / Document / Process. Proof consumer = D4 Engine-eval zone (`CandidateEngineEvalPanel` next to Information / Q&A / Flight-map). **Not** a boolean. **Not** Hub ask generation (that is DR1-runtime). **Not** Vacancy overlay catch-up. **Not** Engine v2. **Not** E8.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After CL6, mapped member values exist on Binding, but nothing named answers “ready or not, and why” with the CL0 Engine shape. Without CL7 the next slice will treat Engine as `true`/`false`, write screening as `required=true` on a field, generate Hub outstanding asks (DR1-runtime), fold Vacancy overlay into this PR, or hide blockers behind a green check.

**Completion proof (named consumer):**  
`entity_profile_engine_eval.v1` for `recruitment.candidate.driver_ce` — `evaluate(entity, profile, vacancy, process_point)` returns `status: ready | not_ready` and `blockers[]: kind, code, owner, message, evidence`. D4 **places** the Engine-eval zone (`CandidateEngineEvalPanel`; host region `engine-eval`, distinct from `information` / `qa` / `flight-map`). D4 **places**; it does not own Engine semantics. Vacancy overlay, if passed, is an input — this slice does not mint overlay SoT.

**False close:** Engine boolean; screening as `required=true` on a field; Hub ask generation / DR1-runtime write; Vacancy overlay catch-up in this PR; Profile contains Engine implementation; CandidateCard cutover; G4; Client card; Forms P3; E8-bind; E8-eval; minting fields from question text; copying mapped values into `extra`.

---

## Scope (evaluation only)

| In scope | Out of scope |
|----------|--------------|
| Structured `ready` / `not_ready` + `blockers[]` | Boolean / green-check substitute |
| Four kinds: Presence / Value / Document / Process | Hub outstanding-ask generation (DR1-runtime) |
| Profile may only **ref** Engine | Engine implementation on Profile membership |
| D4 Engine-eval zone bind (thin; feat) | Vacancy overlay SoT / catch-up |
| Gate test + boundary guard + named CI (feat) | Engine v2; E8-bind / E8-eval; alembic |

---

## Contract shape

```text
evaluate(entity, profile, vacancy, process_point) →
  contract_id: entity_profile_engine_eval.v1
  profile_code
  status: ready | not_ready
  blockers[]: kind, code, owner, message, evidence
```

`kind` ∈ {presence, value, document, process}.  
Reject: boolean result; missing `blockers` on `not_ready`; screening as `required=true` on a field; writing Engine onto Profile membership; generating Hub asks; treating Vacancy overlay as this producer.

This slice **does not** mint Requirement Engine v2 and **does not** implement `engine_to_hub_outstanding_ask.v1` writes. Evaluation refs [Requirement Rules Engine P0](../platform/requirement-rules-engine-p0.md). Hub ask persistence remains [DR1-runtime](engine-document-request-dr1-contract.md) after Reference R5.

---

## Artifacts

| Artifact | Path |
|----------|------|
| Brief | this file |
| Runtime | `backend/app/entity_profile/engine_eval_runtime.py` |
| D4 bind | `hostflow-frontend/src/platform/entity-workspace/CandidateEngineEvalPanel.tsx` |
| Boundary guard | `scripts/architecture/check_entity_profile_engine_eval_boundary.py` |
| Gate test | `backend/tests/entity_field_composition/test_cl7_engine_eval_gate.py` |

---

## CL7 Gate (named)

PASS when:

1. Brief + Engine-eval runtime committed.  
2. `evaluate` returns `ready` | `not_ready` + `blockers[]` (not a boolean).  
3. Four kinds appear in blockers; screening is not `required=true` on a field.  
4. Profile does not contain Engine implementation (ref only).  
5. No Hub ask persistence / mass generation in this producer.  
6. D4 places Engine-eval zone; Information / Q&A / Flight-map zones unchanged.  
7. Boundary guard reports exactly one `evaluate` producer for this contract.  
8. Named CI job runs `test_cl7_engine_eval_gate.py`.

Unlocks: **Vacancy Overlay Contract** (named leftover of the original CL0 chain; not CL8) ✅ [#311](https://github.com/igortatarynovich/HostFlow/pull/311). Overlay unlocks **DR1-runtime**. Does **not** auto-start E8.

---

## Queue position

**Depends on:** CL6 Gate ✅ (#307 / `8e2372db`)  
**Unlocks:** [Vacancy Overlay Contract](entity-profile-vacancy-overlay-contract.md) ✅; Overlay unlocks [DR1-runtime](engine-document-request-dr1-runtime.md) ✅ [#313](https://github.com/igortatarynovich/HostFlow/pull/313); DR1-runtime unlocks [E8-bind](documents-platform-e8-bind.md) ✅ [#321](https://github.com/igortatarynovich/HostFlow/pull/321); E8-bind unlocks [E8-eval](documents-platform-e8-eval.md)  
**Does not:** start E8; invent CL8; mint Engine v2

---

## History

- 2026-08-25: Queue amendment after E8-bind Gate PASS names E8-eval Active Product (not OCR auto-start).
- 2026-08-25: CL7 Requirement Engine evaluation opened (feat locked) after CL6 Gate PASS [#307](https://github.com/igortatarynovich/HostFlow/pull/307) / `8e2372db`. Structured `ready`/`not_ready` + blockers. Not DR1-runtime. Not E8. Vacancy overlay leftover.
- 2026-08-25: CL7 feat — `entity_profile_engine_eval.v1`; D4 places Engine-eval zone; named CL7 Engine Eval Gate.
- 2026-08-25: CL7 Gate **PASS** [#309](https://github.com/igortatarynovich/HostFlow/pull/309) / `6f2289f1`. Unlocks Vacancy Overlay Contract (not CL8). Overlay later PASS [#311](https://github.com/igortatarynovich/HostFlow/pull/311) → DR1-runtime.
