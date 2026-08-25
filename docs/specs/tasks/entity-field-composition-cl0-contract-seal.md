# Entity Field Composition CL0 — Contract Seal

**Status:** **IN PROGRESS** (brief; feat locked)  
**Phase class:** platform  
**Branch (docs):** `docs/entity-field-composition-cl0-contract-seal`  
**Branch (code):** none this slice — docs only; later CL slices use `feat/entity-field-composition-clN-…`  
**Parents:** [Documents Platform E7](documents-platform-e7-document-requests.md) [#286](https://github.com/igortatarynovich/HostFlow/pull/286)/[#287](https://github.com/igortatarynovich/HostFlow/pull/287) · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) ✅ · [Entity Profile Definition Registry](../platform/entity-profile-definition-registry.md) · [Requirement Rules Engine P0](../platform/requirement-rules-engine-p0.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Forms Public Contract](../architecture/forms-public-contract.md) · [UI constitution](../architecture/ui-constitution-v1.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · [ADR-025](../architecture/ADR-025-standard-adapter-boundary.md)

> E7 sealed Hub outstanding ask as required type + entity ([#287](https://github.com/igortatarynovich/HostFlow/pull/287) · merge `ceafbd48`). Request lives on `document_type_code`, not on an automation row. Full consumer (Engine → Request) is **after** this program, not inside E7.  
> CL0 seals **Page Type + two builder modes + Entity Profile as role manifest + Requirement ownership** (four kinds; Engine is not a boolean). One delta to current P0: `transition` / `handoff` leave the Profile field.  
> CL0 does **not** ship runtime, builder UI, Flight mapping, Q&A, mass D3–D9 bind, Documents E8, Forms P3–P5, or a second Field Registry.

**Naming (do not collapse):** this **Entity Field Composition CL0** is not Documents E8, not Entity D10, not Forms P3 Publish UI, not a Recruitment rail patch, not Card Layout as a second SoT, not Requirement Engine v2. Profile ≠ card JSON. Builder ≠ Field Registry. Engine ≠ `required: true`.

---

## Why this slice

Candidate still composes meaning from `CandidateProfile.config`, `document_configs`, screening-as-required, and extra/UI holes. E7 already consumes Hub types; it must not become the place we invent layout or screening rules.

Without CL0 the next PR will either (a) hang `transition` / `handoff` required on the Profile field (current P0 hole), (b) treat the Engine as a boolean, (c) open one WordPress-style page that is both card and lead form, or (d) start E8 / Forms P3 “while we are here”.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After CL0, an Entity Profile **cannot** be a container of implementations (field definitions, document schemas, funnel stages, automation, Q&A, Flight maps). It is a **role manifest**: membership + baseline presence + refs. Requirement kinds have named owners. The Engine returns a structured evaluation, not `true`/`false`. Page Type is a closed catalog; the builder has exactly two modes (card vs form). `transition` / `handoff` required **cannot** live on a Profile field.

**Completion proof (named consumer):**  
**Candidate Entity Workspace — D4 Information zone** (`CandidateEntityWorkspacePanel` / `/app/candidates/:id` overview / information). Locked; later CL slices (not this docs PR) prove layout runtime there. This brief does **not** choose Recruitment Application (G4), Client card, a new Hub control-center, or Forms builder as the proof.

```text
Catalogs (Field + Document Type + Widget + Page Type)
  → Entity Profile (role manifest + refs)
  → Layouts (presentation)
  → Vacancy (profile + overlay)
  → Flight (deliver + map into profile fields)
  → Requirement Engine (aggregate + explain)
  → Document Runtime / Process / Automation / Workspace
```

**False close (reject):** CL0 as runtime; Profile JSON as SoT; Engine boolean; screening as `required=true` on a field; one saved page that is both card and form; minting page types from admin; Documents E8; Forms P3; D10; mass bind.

---

## Locked: Page Type + two builder modes

| Mode | Saved artifact | Palette | Writes to |
|------|----------------|---------|-----------|
| **Card** | Layout instance of a closed page type (`candidate.card`, …) | Profile fields + allowlisted widgets | Layout registry |
| **Form** | Form definition bound to a page type (`intake.form`, …) | Subset of Profile fields (presentation) | Forms platform (ADR-007) — not field SoT |

Closed catalog: platform / module owns page types. Admin creates **layout instances**, not new page types. Builder does not mint `phone` semantics; it places `recruitment.candidate.contacts.phone`.

Widget allowlist is per page type. Card and form **must not** share one saved template.

---

## Locked: Entity Profile = role manifest

**Entity Profile** = declarative manifest of composition and default configuration for one entity role.  
Code: `recruitment.candidate.driver_ce`.

It **declares and references**. It **does not contain implementations**.

| Contains | Does not contain |
|----------|------------------|
| membership of canonical fields for the role | Field Registry definitions |
| membership of tenant custom fields for this role | candidate field values |
| baseline presence: member / intake / card completion | `transition` / `handoff` required |
| ref `document_pack_code` | Document Type schemas, files |
| ref `screening_pack_code` | qualification thresholds as `required=true` on a field |
| ref `default_layout_code` | section order, widgets |
| ref `process_profile_code` | funnel stages |
| UI may assemble these on one Profile screen | automation, templates, Q&A, Flight mapping, assignment |

**CL0 delta to current P0** ([entity-profile-definition-registry.md](../platform/entity-profile-definition-registry.md)): remove `transition` / `handoff` (and `transition_level`) from Profile field membership. Those belong to Process Profile / Transfer Policy. Add `screening_pack_code` as a **ref**, same class as pack / layout / process.

---

## Locked: Requirement ownership (four kinds)

| Kind | Meaning | Example | Rule owner |
|------|---------|---------|------------|
| **Presence** | value must exist | phone present | Profile (intake / card) **or** Process (funnel point) |
| **Value** | value satisfies a predicate | `years_ce ≥ 2` | Screening Pack + vacancy overlay |
| **Document** | instance present / valid / verified | licence valid | Pack + Document Runtime facts (E7 ask = Hub type + entity) |
| **Process** | at a process point the set above must hold | before handoff: citizenship + licence verified | Process / Transfer Policy |

**Engine is not a boolean.**

```text
evaluate(entity, profile, vacancy, process_point) →
  status: ready | not_ready
  blockers[]: kind, code, owner, message, evidence
```

Screening is **not** written as `required=true` on `years_ce`.  
E7 already matches Document kind: request lives on `document_type_code`. Engine → Request is a **later consumer**, after CL — not E8 and not this brief.

---

## CL ladder (this program)

| Slice | Focus | Status |
|-------|--------|--------|
| **CL0** | Contract seal | ✅ PASS (brief; treated PASS via #289) |
| **CL1** | Inventory current Candidate | ✅ PASS [#299](https://github.com/igortatarynovich/HostFlow/pull/299) — [brief](entity-field-composition-cl1-candidate-inventory.md) |
| **CL2** | Membership runtime | ✅ PASS [#303](https://github.com/igortatarynovich/HostFlow/pull/303) — [brief](entity-field-composition-cl2-membership.md) |
| **CL3** | Layout runtime (proof = D4 Information zone) | ✅ PASS [#304](https://github.com/igortatarynovich/HostFlow/pull/304) — [brief](entity-field-composition-cl3-layout.md) |
| **CL4** | Builder (two modes) | ✅ PASS [#305](https://github.com/igortatarynovich/HostFlow/pull/305) — [brief](entity-field-composition-cl4-builder.md) |
| **CL5** | Q&A | ✅ PASS [#306](https://github.com/igortatarynovich/HostFlow/pull/306) — [brief](entity-field-composition-cl5-qa.md) |
| **CL6** | Flight mapping | ← **active** — [brief](entity-field-composition-cl6-flight-map.md) |

CL1 is classification, **not** runtime. Do not skip to CL3 because “the card already renders”.  
**Product after CL0 Gate:** CL1 → LI-1 → DR1-contract → CL2…. **DR1-runtime** is not a CL slice; it waits on DR1-contract ∧ Reference R5 and does **not** park CL2+. **E8-bind / E8-eval** are Documents slices (unlock ≠ schedule). Do not name Engine→Request as CL7.

---

## In scope (this docs PR)

1. This brief — Page Type / two modes / Profile manifest / four kinds / Engine shape.  
2. Close **Documents Platform E7** as **COMPLETE** after [#286](https://github.com/igortatarynovich/HostFlow/pull/286)/[#287](https://github.com/igortatarynovich/HostFlow/pull/287) (`ceafbd48`).  
3. Point Product Track / queue / roadmap / AGENTS / maturity here. Split CL0 from Documents E8+ (E8 stays locked).  
4. Apply the P0 delta: `transition` / `handoff` off Profile field; Screening Pack as ref; Engine structured result.  
5. Feat locked — no runtime in this PR.

## Out of this slice

| Deferred | Owner |
|----------|--------|
| CL1 inventory of live Candidate config | **next Product brief** after this CL0 Gate |
| CL2–CL6 runtime / builder / Q&A / Flight | later CL (after DR1-contract) |
| **DR1-contract / DR1-runtime** | not a CL slice; contract after CL1+LI-1; runtime after contract ∧ Reference R5 |
| **E8-bind / E8-eval** | locked; unlock ≠ schedule; see queue |
| Forms P3 / P4 / P5 | locked |
| D10 / mass D3–D9 bind | forbidden |
| OCR / packages / Billing / AI | forbidden |

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Platform Entity Profile + Requirement Engine (L2). Documents keep Hub types (ADR-009). Forms keep form definitions (ADR-007). Candidate host **places** only |
| 2 Exists? | Field Registry + Entity Profile P0 + Requirement Engine P0 yes; CL0 **seals** the hole (transition/handoff on Profile field; Engine-as-boolean). New capability name = Entity Field Composition program, not a second registry |
| 3 Adapter | No new Adapter this slice. Later layout runtime uses existing workspace host. Documents stay `documents.hub_adapter_v1` |
| 4 Boundary | Docs contract only. No runtime. No E8. No Forms P3. No D10. No mass bind. No Catalog rewrite |
| 5 Settings | No new Manifest keys in CL0 |
| 6 SoT | Profile = role manifest; Field Registry = field definitions; Layout = presentation; Pack / Screening / Process = refs; Engine = evaluation |
| 7 Events | No new Catalog events |
| 8 Requires | E7 ✅ [#287](https://github.com/igortatarynovich/HostFlow/pull/287) · D4 ✅ · Entity Profile P0 · Requirement Engine P0 |
| 9 License | None new |
| 10 Public contract | No Documents / Forms contract id bump this slice |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- Product Track = this brief (feat locked, docs only). Documents Platform E7 is closed (#287 / `ceafbd48`).  
- Operators / agents cannot treat CandidateProfile.config, Documents E8, Forms P3, D10, or Engine boolean as this seal.  
- `transition` / `handoff` are not Profile-field properties in canon.  
- Documents Foundation stays 🔄. E8-bind / E8-eval stay locked (split-gated; unlock ≠ schedule). Next Product after this brief = **CL1**.

---

## DoD

- [x] Brief sealed with Page Type / two modes / Profile manifest / four kinds + Original Goal → Completion Proof  
- [x] Queue + roadmap + AGENTS + maturity pointed at this brief (this docs PR)  
- [x] E7 marked **COMPLETE** with #287 / `ceafbd48`  
- [x] P0 delta applied (Profile field; Engine shape)  
- [x] No runtime / no E8 / no Forms P3 in this PR

---

## History

- 2026-08-23: Sequence sealed — next Product after CL0 = CL1 → LI-1 → DR1-contract → CL2…; Engine→Request is DR1 (not CL7); E8-bind / E8-eval split.
- 2026-08-23: CL0 brief opened — Entity Field Composition contract seal. Product Track → this brief (feat locked, docs only). E7 ✅ [#287](https://github.com/igortatarynovich/HostFlow/pull/287) (`ceafbd48`). E8 stays locked. Foundation stays 🔄.
