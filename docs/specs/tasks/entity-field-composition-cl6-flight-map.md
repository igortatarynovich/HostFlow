# Entity Field Composition CL6 — Flight mapping

**Status:** **IN PROGRESS** (feat)  
**Phase class:** platform  
**Branch:** `feat/entity-field-composition-cl6-flight-map`  
**Parents:** [CL0 contract seal](entity-field-composition-cl0-contract-seal.md) · [CL2 membership](entity-field-composition-cl2-membership.md) · [CL5 Recruiter Q&A](entity-field-composition-cl5-qa.md) · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) · [Sequential queue](sales-to-comms-sequential-queue.md)

> CL6 **executes Map** (`raw` / `source_key` + answer → member `qualified_code`). Mapping is a **Flight/Binding consumer artifact** — Profile may only ref. Snapshot lives on **Binding**. Destination = Profile member fields (`recruitment.candidate.contacts.phone`), not the Flight entity, not `extra`, not question text. Proof consumer = D4 Flight-map zone (`CandidateFlightMapPanel` next to Q&A). **Not** Zapier UX. **Not** Meta ads admin as mapping SoT. **Not** a CL3 layout widget. **Not** Stage 4 Flight status. **Not** P9 `mapping_write.py`. **Not** DR1-runtime. **Not** E8.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After CL5, Map is catalogued (`disposition=map`) but not executed. Without CL6 the next slice will copy mapped values into `candidate.extra`, mint `phone` from «Telefon?», treat Flight as the destination entity, ship Zapier-style mapper UX inside Flight, or treat Meta ads admin as mapping SoT.

**Completion proof (named consumer):**  
`entity_profile_flight_map.v1` for `recruitment.candidate.driver_ce` — `apply_map(profile_code, source_answers, binding)`. Resolve emits **only** `disposition=map` items onto a Binding snapshot (`snapshot_on=binding`). Dest `qualified_code` ⊆ CL2 members. D4 **places** the Flight-map zone (`CandidateFlightMapPanel` next to Q&A). Q&A zone stays `entity_profile_qa.v1` / `lead_application`. Information zone stays `candidate.card` only. D4 **places**; it does not own field semantics.

**False close:** Zapier UX in Flight; dest = Flight entity; Meta admin as mapping SoT; copy into `candidate.extra`; mint fields from question text; fold `qa_only` into the map snapshot; CL3 layout widget; CandidateCard cutover; G4; Client card; Forms P3; P9 intake mapping write as this contract; reopening Acquisition Stage 4 Flight Runtime; dropping `transition_level` columns; Engine evaluation; E8-bind; DR1-runtime.

---

## Scope (Flight mapping only)

| In scope | Out of scope |
|----------|--------------|
| `apply_map` executes `disposition=map` | Zapier mapper canvas / Flight admin rewrite |
| Snapshot on Binding | Dest = Flight entity |
| Dest ⊆ CL2 member `qualified_code` | Meta ads admin as mapping SoT |
| `qa_only` absent; ignore dropped | Folding Q&A into the map snapshot |
| D4 Flight-map zone bind (thin) | Writing into `extra`; minting `phone` |
| Gate test + boundary guard + named CI | Stage 4 Flight status; P9 SoT; E8; DR1-runtime; alembic |

---

## Contract shape

```text
apply_map(profile_code, source_answers, binding) → only disposition=map items:
  contract_id: entity_profile_flight_map.v1
  profile_code
  binding_ref
  snapshot_on: binding
  snapshot[]: source_key, qualified_code, value
```

Reject: dest not a CL2 member; dest = Flight entity; leaf names / question text as `qualified_code`; writing into `extra`; Zapier UX; Meta admin as SoT; missing Binding; `qa_only` forced into the snapshot; P9 `mapping_write` as this producer.

---

## Artifacts

| Artifact | Path |
|----------|------|
| Brief | this file |
| Runtime | `backend/app/entity_profile/flight_map_runtime.py` |
| D4 bind | `hostflow-frontend/src/platform/entity-workspace/CandidateFlightMapPanel.tsx` |
| Boundary guard | `scripts/architecture/check_entity_profile_flight_map_boundary.py` |
| Gate test | `backend/tests/entity_field_composition/test_cl6_flight_map_gate.py` |

---

## CL6 Gate (named)

PASS when:

1. Brief + Flight map runtime committed.  
2. Map executes: raw → member `qualified_code`; snapshot on Binding.  
3. `qa_only` absent from map snapshot; ignore dropped.  
4. Dest ⊆ CL2 members; question text / `phone` is not a qualified field; no write to `extra`.  
5. Dest is Profile, not Flight entity; not Zapier UX; not Meta admin SoT.  
6. Q&A zone still `entity_profile_qa.v1` / `lead_application`; Information zone still `candidate.card` only.  
7. Boundary guard reports exactly one `apply_map` producer.  
8. Named CI job runs `test_cl6_flight_map_gate.py`.

Unlocks: later CL via **queue amendment** (do not invent CL7). Does **not** unlock DR1-runtime or E8.

---

## Queue position

**Depends on:** CL5 Gate ✅ (#306 / `5d8e1ae3`)  
**Unlocks:** later CL via queue amendment  
**Does not:** park on Reference R5 / #298; start E8; start DR1-runtime; reopen Stage 4; promote P9

---

## History

- 2026-08-25: CL6 Flight mapping opened — `entity_profile_flight_map.v1`; Map executes onto Binding; dest = Profile members; D4 places Flight-map zone, not Zapier / not Flight entity / not extra.
