# Entity Field Composition CL2 — Membership runtime

**Status:** **PASS** — CL2 Gate closed by [#303](https://github.com/igortatarynovich/HostFlow/pull/303) / `09dfea47`; successor CL3 ✅ [#304](https://github.com/igortatarynovich/HostFlow/pull/304)  
**Phase class:** platform  
**Branch:** `feat/entity-field-composition-cl2-membership`  
**Parents:** [CL0 contract seal](entity-field-composition-cl0-contract-seal.md) · [CL1 inventory](entity-field-composition-cl1-candidate-inventory.md) · [DR1-contract](engine-document-request-dr1-contract.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Entity Profile Definition Registry](../platform/entity-profile-definition-registry.md)

> CL2 ships **membership runtime** for Entity Profile as a role manifest: which fields belong to the role, baseline presence (`intake` / `card_save`), and pack/layout/process refs. Proof case = `recruitment.candidate.driver_ce`. **Not** layout (CL3). **Not** builder / Q&A / Flight. **Not** DR1-runtime. **Not** E8.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After CL1, Candidate still has no named runtime that answers “is this field a member of this profile?” with the CL0 shape. Consumers keep reading `CandidateProfile.config`, Field Registry lists, and `transition_level` on Profile rows as if those were membership. Without CL2, CL3 layout will either fork a private field list or treat Engine / screening as `required=true` on a field.

**Completion proof (named consumer):**  
`entity_profile_membership.v1` for `recruitment.candidate.driver_ce` — `is_field_member` / `resolve_membership` / `presence_level`. D4 Information zone **places** this membership; it does not own it. Layout instances stay CL3.

**False close:** D4 card re-render; Field Registry dump as membership; keeping `transition` / `handoff` on Profile fields; screening as `required=true` on `years_ce`; tenant DB sweep; dropping `transition_level` columns; Engine evaluation; DR1-runtime; E8-bind.

---

## Scope (membership only)

| In scope | Out of scope |
|----------|--------------|
| Named producer `membership_runtime.py` | Layout runtime (CL3) / D4 chrome |
| Baseline presence `intake` / `card_save` | `transition` / `handoff` as Profile-field required |
| Refs: layout / document pack / **screening pack** / process | Screening evaluation; Engine boolean |
| Canonical members from platform manifests | Tenant custom overlay persistence (empty list this slice) |
| Gate test + boundary guard + named CI | Dropping DB columns; ingest/frontend cutover |
| `driver_ce` proof | Warehouse/office as additional proof; E8; DR1-runtime |

---

## Contract shape

```text
resolve_membership(profile_code) →
  contract_id: entity_profile_membership.v1
  fields[]: qualified_code, kind=canonical, is_member, sort_order,
            presence: {intake, card_save}
  custom_fields[]: []   # tenant overlay reserved
  refs: default_layout_code, document_pack_code,
        screening_pack_code, process_profile_code

is_field_member(profile_code, qualified_code) → bool
presence_level(profile_code, qualified_code, intake|card_save) → level | None
```

`presence_level(..., transition|handoff)` returns **None**. Manifest/DB may still store `transition_level` until a later migration.

---

## Artifacts

| Artifact | Path |
|----------|------|
| Brief | this file |
| Runtime | `backend/app/entity_profile/membership_runtime.py` |
| Boundary guard | `scripts/architecture/check_entity_profile_membership_boundary.py` |
| Gate test | `backend/tests/entity_field_composition/test_cl2_membership_gate.py` |

---

## CL2 Gate (named)

PASS when:

1. Brief + membership runtime committed.  
2. `driver_ce` membership equals CL1-observed entity-profile field codes.  
3. Projection has no `transition` / `handoff`; screening is a **pack ref**.  
4. Boundary guard reports exactly one producer.  
5. Named CI job runs `test_cl2_membership_gate.py`.

Unlocks: **CL3** (layout runtime). Does **not** unlock DR1-runtime or E8.

---

## Queue position

**Depends on:** DR1-contract Gate ✅ (#302 / `23f5ba6d`)  
**Unlocks:** CL3  
**Does not:** park on Reference R5 / Program Exit; start E8; start DR1-runtime

---

## History

- 2026-08-24: CL2 membership runtime opened — `entity_profile_membership.v1`; driver_ce proof; screening pack as ref; no layout / no column drop.
