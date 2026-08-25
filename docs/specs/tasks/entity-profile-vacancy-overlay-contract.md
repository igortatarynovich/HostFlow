# Entity Profile — Vacancy Overlay Contract

**Status:** **IN PROGRESS** (brief; feat locked)  
**Phase class:** platform  
**Branch (docs):** `docs/queue-post-cl7-amendment`  
**Branch (code):** none this slice — docs only; later feat uses `feat/entity-profile-vacancy-overlay-contract`  
**Parents:** [CL0 contract seal](entity-field-composition-cl0-contract-seal.md) · [CL2 membership](entity-field-composition-cl2-membership.md) · [CL7 Engine evaluation](entity-field-composition-cl7-engine-eval.md) · [Requirement Rules Engine P0](../platform/requirement-rules-engine-p0.md) · [Entity Profile Definition Registry](../platform/entity-profile-definition-registry.md) · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) · [Sequential queue](sales-to-comms-sequential-queue.md)

> Vacancy Overlay is **SoT + merge semantics** for a vacancy-specific requirement **delta** over Entity Profile / Screening Pack. After this contract, CL7 `evaluate(entity, profile, vacancy, process_point)` consumes a **defined** overlay input — not an ad-hoc `years_ce_min` bag. Overlay is **not** an Entity Profile implementation — Profile may only ref. **Not** CL8. **Not** Engine v2. **Not** Hub ask write (`engine_to_hub_outstanding_ask.v1`). **Not** DR1-runtime. **Not** E8. **Not** vacancy UI. **Not** Reference R5 `merge(pack, tenant_delta)`.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
CL7 runtime is closed, but `vacancy` on `evaluate(...)` is still a conceptually undefined input. Without a named Overlay contract the next slice will treat Overlay as CL8, fold overlay predicates onto Profile membership, reuse R5 pack / `tenant_delta` merge, write Hub outstanding asks, ship vacancy card UI as this producer, or keep `years_ce_min` as an ad-hoc dict key with no merge SoT.

**Completion proof (named consumer):**  
`entity_profile_vacancy_overlay.v1` for `recruitment.candidate.driver_ce` — `resolve_overlay(profile, vacancy)` returns a vacancy-specific requirement **delta** over Profile / Screening Pack; `merge(profile, screening_pack, overlay)` is the defined input to CL7 `evaluate`. D4 **places** the Engine-eval zone that already exists (`CandidateEngineEvalPanel`; host region `engine-eval`). D4 **places**; it does not own Overlay merge semantics. Proof is a later feat — this PR is docs only.

**False close:** numbering Overlay as CL8; Engine v2; writing `engine_to_hub_outstanding_ask.v1`; starting DR1-runtime or E8; vacancy UI as this producer; Overlay implementation on Profile membership; Overlay = R5 `merge(pack, tenant_delta)`; screening as `required=true` on a field; minting fields from question text; copying overlay into `extra`.

---

## Scope (contract only this PR)

| In scope | Out of scope |
|----------|--------------|
| Overlay SoT + merge semantics (docs) | Overlay runtime / feat (later PR) |
| Vacancy-specific **delta** over Profile / Screening Pack | Fork of Profile or Screening Pack identity |
| Defined input to CL7 `evaluate(..., vacancy, ...)` | Ad-hoc `years_ce_min` as the contract |
| Profile may only **ref** Overlay | Overlay implementation on Profile membership |
| Named leftover of the original CL0 chain | CL8; Engine v2; Hub ask write; DR1-runtime; E8; vacancy UI; R5 pack merge |

---

## Contract shape

```text
resolve_overlay(profile, vacancy) →
  contract_id: entity_profile_vacancy_overlay.v1
  profile_code
  vacancy_ref
  base: screening_pack_code | profile refs
  delta[]: kind, code, owner, op, predicate

merge(profile, screening_pack, overlay) → effective requirement set
  → CL7 evaluate(entity, profile, overlay, process_point)
```

`kind` ∈ {presence, value, document, process} — same four CL0 kinds.  
Overlay may **tighten or add** vacancy-specific predicates on top of Profile / Screening Pack. Overlay **must not** fork pack identity. Overlay **must not** be the R5 `merge(pack, tenant_delta)` producer (that is tenant document-policy merge, a different write-set).

Reject: Overlay as CL8; Overlay on Profile membership; Overlay = R5 pack / `tenant_delta`; boolean Engine; screening as `required=true` on a field; writing Hub asks; vacancy UI as this producer; minting Engine v2.

This slice **does not** mint Requirement Engine v2 and **does not** implement `engine_to_hub_outstanding_ask.v1` writes. Evaluation remains [CL7](entity-field-composition-cl7-engine-eval.md). Hub ask persistence remains [DR1-runtime](engine-document-request-dr1-contract.md) after Reference R5.

---

## Artifacts

| Artifact | Path |
|----------|------|
| Brief | this file (this docs PR) |
| Overlay runtime | later feat — not this PR |
| D4 bind | existing Engine-eval zone consumes overlay as defined input (feat-locked) |
| Boundary guard / named CI | later feat — not this PR |

---

## Vacancy Overlay Gate (named)

PASS when (later feat — **not** this docs PR):

1. Brief + overlay contract committed.  
2. Overlay is SoT for vacancy-specific requirement delta over Profile / Screening Pack.  
3. Merge: base = Profile + Screening Pack; overlay ≠ fork; overlay ≠ R5 `tenant_delta`.  
4. CL7 `evaluate` consumes overlay as a defined input (not ad-hoc `years_ce_min`).  
5. Profile does not contain Overlay implementation (ref only).  
6. No Hub ask persistence; no Engine v2; no vacancy UI as this producer.  
7. D4 still places Engine-eval zone; Information / Q&A / Flight-map zones unchanged.  
8. Named CI job exists for the Overlay Gate.

Unlocks: later Product via **queue amendment**. Does **not** unlock DR1-runtime or E8. Do **not** invent CL8.

---

## Queue position

**Depends on:** CL7 Gate ✅ (#309 / `6f2289f1`)  
**Unlocks:** later Product via queue amendment  
**Does not:** park on Reference R5 / #298; start E8; start DR1-runtime; invent CL8; mint Engine v2; write Hub asks; ship vacancy UI

---

## History

- 2026-08-25: Vacancy Overlay Contract opened (feat locked) after CL7 Gate PASS [#309](https://github.com/igortatarynovich/HostFlow/pull/309) / `6f2289f1`. Named leftover of the original CL0 chain (Vacancy = profile + overlay). Not CL8. Not DR1-runtime. Not E8.
