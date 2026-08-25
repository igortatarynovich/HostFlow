# Entity Field Composition CL4 — Builder (two modes)

**Status:** **PASS** [#305](https://github.com/igortatarynovich/HostFlow/pull/305) / `c49716e3`  
**Phase class:** platform  
**Branch:** `feat/entity-field-composition-cl4-builder`  
**Parents:** [CL0 contract seal](entity-field-composition-cl0-contract-seal.md) · [CL2 membership](entity-field-composition-cl2-membership.md) · [CL3 layout](entity-field-composition-cl3-layout.md) · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md)

> CL4 ships a **two-mode builder** over the closed page-type catalog: card compiles a layout instance into the layout registry; form compiles a form definition into the Forms platform. Proof consumer = D4 Information zone (`CandidateEntityWorkspacePanel` overview). **Not** Q&A (CL5). **Not** Flight (CL6). **Not** a shared card+form template. **Not** DR1-runtime. **Not** E8.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After CL3, D4 can place a membership-filtered `candidate.card`, but there is no named producer that compiles a builder draft into **one** of two artifacts. Without CL4 the next slice will mint page types from admin, save one template that is both card and form, or treat `phone` as field SoT instead of `recruitment.candidate.contacts.phone`.

**Completion proof (named consumer):**  
`entity_profile_builder.v1` for `recruitment.candidate.driver_ce` — `list_builder_modes` / `palette` / `compile_draft`. Card compile is **placed** by D4 Information zone (`CandidateCompositionBuilder` next to `CandidateInformationLayout`). Form compile is a separate Forms-platform artifact and is **not** rendered as the D4 card. D4 **places**; it does not own field semantics.

**False close:** WordPress canvas; minting page types; one saved card+form template; resolving `intake.form` via `resolve_layout`; Q&A; Flight; CandidateCard cutover; dropping `transition_level` columns; Engine evaluation; E8-bind; DR1-runtime.

---

## Scope (builder only)

| In scope | Out of scope |
|----------|--------------|
| Two modes: `card` / `form` | Admin-minted page types |
| Palette = CL2 members + CL3 widget allowlist | New widgets; Q&A blocks (CL5) |
| Card compile → `layout_instance` / layout registry | Shared card+form template |
| Form compile → `form_definition` / Forms platform (in-memory) | Forms C3 persistence / alembic |
| Closed catalog (`candidate.card`, `intake.form`) | Flight mapping (CL6) |
| D4 Information zone bind (thin) | CandidateCard cutover; G4; Client card |
| Gate test + boundary guard + named CI | DB column drop; E8; DR1-runtime |

---

## Contract shape

```text
list_builder_modes() → (card, form)

palette(profile_code, page_type) →
  CL2 members + widgets from PAGE_TYPE_CATALOG

compile_draft(draft) → one artifact, never both:
  card → artifact_kind=layout_instance, writes_to=layout_registry
         (shape compatible with entity_profile_layout.v1)
  form → artifact_kind=form_definition, writes_to=forms_platform
         (in-memory; not resolve_layout)
```

Reject: unknown / minted page types; `mode ≠ page_type.mode`; mixed card+form in one draft; non-member fields; disallowed widgets; minted field semantics (`phone` vs `recruitment.candidate.contacts.phone`).

---

## Artifacts

| Artifact | Path |
|----------|------|
| Brief | this file |
| Runtime | `backend/app/entity_profile/builder_runtime.py` |
| D4 bind | `hostflow-frontend/src/platform/entity-workspace/CandidateCompositionBuilder.tsx` |
| Boundary guard | `scripts/architecture/check_entity_profile_builder_boundary.py` |
| Gate test | `backend/tests/entity_field_composition/test_cl4_builder_gate.py` |

---

## CL4 Gate (named)

PASS when:

1. Brief + builder runtime committed.  
2. Two modes; closed page-type catalog (cannot mint).  
3. Card compile → `layout_registry` / `layout_instance`; fields ⊆ CL2 members.  
4. Form compile → `forms_platform` / `form_definition`; not `resolve_layout`.  
5. Mixed draft rejected; non-members / bad widgets / minted leaf names rejected.  
6. Card and form are different artifacts (not one saved template).  
7. D4 places card, not form.  
8. Boundary guard reports exactly one `compile_draft` producer.  
9. Named CI job runs `test_cl4_builder_gate.py`.

Unlocks: **CL5** (Q&A). Does **not** unlock DR1-runtime or E8.

---

## Queue position

**Depends on:** CL3 Gate ✅ (#304 / `8c04d696`)  
**Unlocks:** CL5  
**Does not:** park on Reference R5; start E8; start DR1-runtime; start Q&A

---

## History

- 2026-08-24: CL4 builder runtime opened — `entity_profile_builder.v1`; two modes; closed page types; D4 places card, not form.
- 2026-08-24: CL4 Gate **PASS** [#305](https://github.com/igortatarynovich/HostFlow/pull/305) / `c49716e3`. Unlocks CL5.
