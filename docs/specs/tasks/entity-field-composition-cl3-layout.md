# Entity Field Composition CL3 — Layout runtime

**Status:** **IN PROGRESS** (feat)  
**Phase class:** platform  
**Branch:** `feat/entity-field-composition-cl3-layout`  
**Parents:** [CL0 contract seal](entity-field-composition-cl0-contract-seal.md) · [CL2 membership](entity-field-composition-cl2-membership.md) · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Field Registry card configuration](../platform/field-registry-card-configuration.md)

> CL3 ships **layout runtime** for a closed page type (`candidate.card`) filtered through CL2 membership. Proof consumer = D4 Information zone (`CandidateEntityWorkspacePanel` overview). **Not** builder (CL4). **Not** a shared card+form template. **Not** DR1-runtime. **Not** E8.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After CL2, D4 Information zone still has no named layout producer. The Field Registry card dump includes non-members (`operations.stage`, agreements, …) and `CandidateProfile.config` remains a tempting second SoT. Without CL3, CL4 builder will either mint page types or save one template that is both card and form.

**Completion proof (named consumer):**  
`entity_profile_layout.v1` for `recruitment.candidate.driver_ce` + page type `candidate.card`, **placed** by D4 Information zone (`CandidateInformationLayout` in `CandidateEntityWorkspacePanel` overview). Layout fields ⊆ CL2 members. D4 **places**; it does not own field semantics.

**False close:** CandidateCard re-render; Field Registry dump as layout; resolving `intake.form` from the same artifact; builder UI; Q&A; Flight; dropping `transition_level` columns; Engine evaluation; E8-bind; DR1-runtime.

---

## Scope (layout only)

| In scope | Out of scope |
|----------|--------------|
| Closed page-type catalog (`candidate.card`, `intake.form`) | Admin-minted page types |
| `resolve_layout` for **card** only | Form layout production (Forms / CL4) |
| Membership filter (drop non-members) | Screening evaluation; Engine boolean |
| Widget allowlist = `field` | Extra widgets; builder palette |
| D4 Information zone bind | CandidateCard cutover; ListWorkspace |
| Gate test + boundary guard + named CI | DB column drop; E8; DR1-runtime |

---

## Contract shape

```text
list_page_types() → (candidate.card, intake.form)

resolve_layout(profile_code, candidate.card) →
  contract_id: entity_profile_layout.v1
  page_type / mode=card / layout_code
  fields[]: qualified_code, section_code, sort_order, widget=field,
            presence.card_save   # from CL2, not layout.required
  sections[]

resolve_layout(profile_code, intake.form) → None   # catalogued, not this slice
```

Card writes to layout registry. Form writes to Forms platform. They **must not** share one saved template.

---

## Artifacts

| Artifact | Path |
|----------|------|
| Brief | this file |
| Runtime | `backend/app/entity_profile/layout_runtime.py` |
| D4 bind | `hostflow-frontend/src/platform/entity-workspace/CandidateInformationLayout.tsx` |
| Boundary guard | `scripts/architecture/check_entity_profile_layout_boundary.py` |
| Gate test | `backend/tests/entity_field_composition/test_cl3_layout_gate.py` |

---

## CL3 Gate (named)

PASS when:

1. Brief + layout runtime committed.  
2. `driver_ce` + `candidate.card` fields ⊆ CL2 members; non-members (e.g. `operations.stage`) absent.  
3. `intake.form` is catalogued and **not** resolved; card/form modes differ.  
4. D4 Information zone places `entity_profile_layout.v1` / `candidate.card`.  
5. Boundary guard reports exactly one `resolve_layout` producer.  
6. Named CI job runs `test_cl3_layout_gate.py`.

Unlocks: **CL4** (builder, two modes). Does **not** unlock DR1-runtime or E8.

---

## Queue position

**Depends on:** CL2 Gate ✅ (#303 / `09dfea47`)  
**Unlocks:** CL4  
**Does not:** park on Reference R5; start E8; start DR1-runtime

---

## History

- 2026-08-24: CL3 layout runtime opened — `entity_profile_layout.v1`; D4 Information zone proof; membership-filtered `candidate.card`; no builder / no form template.
