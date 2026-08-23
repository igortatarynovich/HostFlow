# Entity Field Composition CL1 — Candidate Inventory

**Status:** **IN PROGRESS** (brief; feat locked)  
**Phase class:** platform  
**Branch (docs):** `docs/entity-field-composition-cl1-inventory`  
**Branch (code):** none this slice — docs only; classification, not runtime  
**Parents:** [Entity Field Composition CL0](entity-field-composition-cl0-contract-seal.md) [#289](https://github.com/igortatarynovich/HostFlow/pull/289) · [Documents Platform E7](documents-platform-e7-document-requests.md) ✅ · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) ✅ · [Entity Profile Definition Registry](../platform/entity-profile-definition-registry.md) · [Requirement Rules Engine P0](../platform/requirement-rules-engine-p0.md) · [Sequential queue](sales-to-comms-sequential-queue.md)

> CL0 sealed Page Type, two builder modes, Profile as role manifest, four requirement kinds, and Engine as `ready`/`not_ready` + `blockers[]` ([#289](https://github.com/igortatarynovich/HostFlow/pull/289) · merge `209cc949`).  
> CL1 classifies **how Candidate is composed today** against that contract. It does **not** change runtime, drop columns, start CL2 membership, rewrite D4 Information, open E8, or implement Engine → Request.

**Naming (do not collapse):** this **Entity Field Composition CL1** is not CL0 (already sealed), not CL2 membership runtime, not CL3 layout runtime, not Documents E8, not Forms P3, not D10. Inventory ≠ builder. Classification ≠ Engine v2.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After CL1, operators / agents cannot treat live Candidate meaning as a single `CandidateProfile.config` blob, or skip classification because “the card already renders”. Every requirement-like signal on Candidate is tagged as Presence / Value / Document / Process / Extra, with SoT vs leftover named. Dual paths (Hub `outstanding_asks` vs `document_configs`) are explicit. `transition_level` on Profile fields and screening-as-`required=true` are named as **CL0 gaps in code**, not as the contract.

**Completion proof (named consumer):**  
**Candidate Entity Workspace — D4 Information zone** (`CandidateEntityWorkspacePanel` / `/app/candidates/:id` overview). CL1 proves the zone is the **named classification target** (hardcoded «Основная / Дополнительная информация» today). Layout runtime there is CL3, not this brief.

**False close (reject):** CL1 as runtime; dropping `transition_level`; implementing `screening_pack_code`; rewriting the overview; starting CL2/CL3/E8/Forms P3; treating D4 chrome as composition done.

---

## Locked: four kinds (from CL0)

| Kind | CL0 owner | What CL1 looks for in code |
|------|-----------|----------------------------|
| **Presence** | Profile membership + intake / card_save | `intake_level` / `card_save_level`; `field_configs[].required` |
| **Value** | Screening pack + vacancy overlay | quals encoded as `required=true`; **no** `screening_pack_code` in runtime |
| **Document** | Pack + Hub facts (E7 ask = type + entity) | Pack/engine → Hub `outstanding_asks` **and** leftover `document_configs` |
| **Process** | Process Profile / Transfer Policy | `transition`/`handoff` still compiled from Profile `transition_level` |

Engine contract (CL0): `evaluate → status ready|not_ready` + `blockers[]` `{kind, code, owner, message, evidence}`. Many UI paths still use boolean `required`.

---

## Inventory (live Candidate)

Proof role: `recruitment.candidate.driver_ce` (`DRIVER_CE_PROFILE_CODE`). Legacy twin: `CandidateProfile` `driver_ce_default`.

### A. Sources

| Source | Path | Stores | Kind | SoT vs leftover | E7 Hub asks? |
|--------|------|--------|------|-----------------|--------------|
| Entity Profile manifest | `backend/app/entity_profile/manifests/recruitment.py` | membership; `intake_level` / `card_save_level` / **`transition_level`**; refs `document_pack_code`, `process_profile_code`, `default_layout_code` | Presence · **Process misplaced** · Document/Process via refs | **Emerging SoT** (pre-CL0 shape) | Indirect (pack → engine → Hub) |
| EP schema | `backend/app/models/entity_profile.py` | `transition_level` column | Process misplaced | Keep column (CL0: do not DROP); stop treating as Profile required | No |
| Requirement Engine map | `backend/app/requirement_rules/constants.py` | `CONTEXT_TO_FIELD_LEVEL`: `transition`/`handoff` → `transition_level` | Process from Profile field | **CL0 gap in code** | Document rules feed Hub |
| Document pack | `backend/app/requirement_rules/manifests/recruitment.py` · `recruitment.driver_ce_documents` | required slots/types (passport, licence, code95, tacho, …) | Document | **SoT** for engine document rules | **Yes** via Hub bridge |
| Hub E7 projection | `backend/app/services/document_hub_delivery_contract.py` | `outstanding_asks` on `documents.hub_adapter_v1` | Document | **E7 SoT** | **Yes** |
| Legacy profile JSON | `backend/app/models/candidate_profile.py` · `config` | `field_configs[]`, `document_configs[]`, stages/gates | Mixed | **Leftover runtime SoT** | No (parallel silo) |
| Seed | `backend/app/seed_candidate_profiles.py` | `FULL_FIELD_CONFIGS` / `FULL_DOCUMENT_CONFIGS` | Presence · Document · Process (stages) | Leftover seed | No |
| Admin / API | `backend/app/api/v1/candidate_profiles.py` · `CandidateProfilesPage.tsx` · `profileUtils.ts` | edits `required` + `document_configs` | Presence · Document · Extra | Leftover admin | No |
| Card checklist | `candidate_document_checklist.py` · `CandidateDocuments.tsx` | filter by `document_configs` | Document · Extra | Parallel silo vs D2 Hub slot | No |
| Transfer policy note | `transfer_policy_resolver.py` | cites `candidate_profiles.config.document_configs` | Process · Document | Dual-sourced | Uses engine/Hub when applied |
| Field layout | `backend/app/field_registry/manifests/recruitment.py` | card order/visibility; `required` on name/phone | Presence presentation | Layout ≠ Engine (overlap today) | No |
| Launch-search intake | `launch_search_intake_fields.ts` | `years_ce`, trailer, code95, tacho as required | **Value as Presence** | Local silo | No |
| D4 Information | `CandidateEntityWorkspacePanel.tsx` · `candidateEntityWorkspaceContent.tsx` | hardcoded «Основная / Дополнительная информация» | Extra/UI | **CL3 proof surface**, not layout runtime | No |
| `screening_pack_code` | CL0 docs only | — | Value (intended) | **Missing in code** | N/A |

### B. Presence

- EP: first/last/phone required at intake and card_save; citizenship / address / `years_ce` required at card_save.
- Legacy: `field_configs[].required` still drives CandidateCard via `profileUtils.isFieldRequired`.
- Layout also marks name/phone required (presentation overlap).

### C. Value (screening)

- **No** `screening_pack_code` in `EpEntityProfile` or manifests (docs-only after CL0).
- Qualifications (`years_ce`, trailer types, code95, tacho) encoded as Presence `required` on fields / launch-search intake.
- API purpose may label `experience.years_ce` as `"qualification"` while still exposing boolean `required`.

### D. Document (dual path)

1. **Hub path (E7):** Document pack → Requirement Engine → `project_outstanding_asks_via_contract` → `outstanding_asks` on the same adapter. Ask = Hub type + entity (Document Link). D4 `documents` slot consumes this.
2. **Leftover path:** `document_configs[]` on CandidateProfile (seed, admin, card checklist, transfer_policy storage note). Does **not** write Hub asks.

CL1 does not pick a cutover. It forbids treating the leftover as Hub SoT.

### E. Process (misplaced on Profile)

- Code: `transition_level` on EP fields; address is `REQUIREMENT_REQUIRED` at transition in `recruitment.py`.
- Engine: `transition` and `handoff` contexts both read `transition_level`.
- Legacy bridge copies `required` → intake/card_save and sets `transition_level: "optional"`.
- Correct-ish owners already exist: Process Profile additive rules; Transfer Policy; stage JSON on CandidateProfile (leftover).

CL0 canon: Process lives on Process Profile / Transfer Policy. CL1 does **not** drop the column.

### F. Extra / UI holes

- D4 overview sections are hardcoded — not Field Composition layout.
- `Candidate.extra` / custom fields.
- Local option lists (trailer types, public apply).
- Shell `documents` nav ≠ D2 `documents` slot; CandidateCard checklist ≠ Hub outstanding asks.

---

## Gaps vs CL0 (named, not fixed here)

| CL0 rule | Code today |
|----------|------------|
| Profile = role manifest; baseline presence = member / intake / card | EP still carries `transition_level`; CandidateProfile JSON still mixes layout/docs/stages |
| `screening_pack_code` ref; screening ≠ `required=true` | Missing runtime ref; quals as required flags |
| Document = pack + Hub; E7 ask = type + entity | Dual path: Hub **and** `document_configs` |
| Engine structured result | Engine exists; UI often boolean `required` |
| Process = Process Profile / Transfer Policy | `CONTEXT_TO_FIELD_LEVEL` still binds transition/handoff to Profile |
| Proof later = D4 Information | Overview is hardcoded mockup, not layout-driven |

---

## In scope (this docs PR)

1. This inventory — sources tagged by CL0 kind, SoT vs leftover.  
2. Close **CL0** as **COMPLETE** after [#289](https://github.com/igortatarynovich/HostFlow/pull/289) (`209cc949`).  
3. Point Product Track / queue / AGENTS / roadmap / maturity here. CL2 stays locked. E8 stays locked.  
4. Feat locked — no runtime, no column drops, no pack implementation.

## Out of this slice

| Deferred | Owner |
|----------|--------|
| CL2 membership runtime | next feat (after this brief) |
| CL3 layout runtime on D4 Information | after CL2 |
| Drop `transition_level` / CandidateProfile removal | later CL + migration |
| Implement `screening_pack_code` | later CL |
| Engine → Document Request consumer | after CL, not E8 |
| Documents E8 / Forms P3 / D10 / mass bind | locked / forbidden |

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Platform Entity Profile + Requirement Engine (L2). Documents keep Hub types. Candidate host places only |
| 2 Exists? | CL0 sealed the contract. CL1 classifies live Candidate against it. Not a second registry |
| 3 Adapter | None. Documents stay `documents.hub_adapter_v1` |
| 4 Boundary | Docs only. No runtime. No E8. No Forms P3. No D10. No mass bind. No Catalog rewrite |
| 5 Settings | No new Manifest keys |
| 6 SoT | Same as CL0. This slice **names** leftovers; it does not move SoT |
| 7 Events | No new Catalog events |
| 8 Requires | CL0 ✅ [#289](https://github.com/igortatarynovich/HostFlow/pull/289) · E7 ✅ · D4 ✅ |
| 9 License | None new |
| 10 Public contract | No Documents / Forms contract id bump |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- Product Track = this brief (feat locked, docs only). CL0 is closed (#289 / `209cc949`).  
- Dual document path and `transition_level` / screening-as-required are named.  
- Agents cannot skip to CL3 because the Candidate card renders.  
- Documents Foundation stays 🔄. E8 stays locked. CL2 stays locked until this brief merges.

---

## DoD

- [x] Brief sealed with inventory tables + Original Goal → Completion Proof  
- [x] Queue + roadmap + AGENTS + maturity pointed at this brief (this docs PR)  
- [x] CL0 marked **COMPLETE** with #289 / `209cc949`  
- [x] No runtime / no E8 / no Forms P3 / no column drop in this PR

---

## History

- 2026-08-23: CL1 brief opened — Candidate composition inventory. Product Track → this brief (feat locked, docs only). CL0 ✅ [#289](https://github.com/igortatarynovich/HostFlow/pull/289) (`209cc949`). E8 stays locked. Foundation stays 🔄.
