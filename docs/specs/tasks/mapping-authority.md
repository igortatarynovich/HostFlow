# Mapping Authority

**Status:** **ACTIVE** — MA-1 Contract Gate **PASS**. Mapping Resolution Gate **PASS**. Active Product = **MA-3** (UX contract **Accepted**; Mapping Operator Gate **not PASS**; feat open).  
**Phase class:** platform
**Branch (docs):** `docs/mapping-authority-ma3-operator-brief`  
**Branch (code):** `feat/mapping-authority-ma3-operator-gate`. Mapping Operator Gate not PASS. Close path: source → schema → explicit bindings/options → Ready → projection → real submission → applied evidence, plus leftover writer retirement.
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) (blocker 2) · [Release Readiness Gate](../gates/release-readiness-gate.md) · [Acceptance suite RS-3](../journeys/release-readiness-acceptance-suite.md) · [v1 Release DAG dependency-position](../gates/v1-release-dag-dependency-position.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [ADR-021](../architecture/ADR-021-unified-intake-resolution-model.md) · [Entity Profile Definition Registry](../platform/entity-profile-definition-registry.md) · [Field Registry](../platform/field-registry-card-configuration.md) · [CL6 Flight map](entity-field-composition-cl6-flight-map.md) · [C-5 mapping workspace](acquisition-ui-cutover-c5-mapping-workspace.md)
**Estimate:** 4–6 slices (1 slice = one docs PR + one feat PR)

> v1 blocker 2: **one operator-visible model from source answers to canonical entity fields.**
> Not “build another mapping editor” — there are already three editors writing three stores.
> **Not** Forms Publish (that is [External Intake](external-intake-forms-publish.md), which consumes this). **Not** Requirement Policy. **Not** CL8. **Not** OCR. **Not** a Zapier product.
> Zapier is a **UX reference** (schema + sample → pick destination). HostFlow adds what Zapier is not required to solve: typed Field Registry destinations, option maps, binding vs contract-health scales, versioning, drift, and evaluator isolation.
> [RPM program close](requirement-policy-management.md) named MA-1 Active Product. MA-1 sealed the [Mapping Authority Contract](../architecture/mapping-authority-contract.md) (`mapping_authority.v1`). MA-2 sealed the [one resolver](../architecture/mapping-authority-resolution.md). [#350](https://github.com/igortatarynovich/HostFlow/pull/350) **Accepted** the [MA-3 UX contract](../architecture/mapping-authority-operator.md). Feat `feat/mapping-authority-ma3-operator-gate` is open. Mapping Operator Gate stays **not PASS**. External Intake / Hiring E2E / min HR remain queued.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**
An operator cannot answer “where does this incoming answer end up, and how do I change that?” in one place. Today the same class of decision is written in **three stores** with a silent fallback chain (`intake_source_profiles.mapping_rules` → `meta_lead_form_mappings.mapping_rules` → `meta_lead_settings.field_mapping`), edited from **three UIs**, expressed in **two vocabularies** (legacy flat `target` vs canonical `qualified_field_code` with a partial bridge), and executed by **three unrelated runtimes** plus several hardcoded extractors. Every new intake source therefore adds another private answer, and no acceptance scenario can prove that changing a mapping changes the next submission.

**Completion proof (named consumer):**
**RS-3 in the [acceptance suite](../journeys/release-readiness-acceptance-suite.md)** on the public intake path: an operator inspects how one named answer reached (or failed to reach) a canonical entity field, changes it in **one** surface, submits the public form again, and observes the new placement — without being asked which of several editors is authoritative. The consumer that must **not** fork: External Intake / Forms Publish acceptance (`publish → … → mapping → canonical entity`) must consume this authority instead of adding a fourth path.

**False close (reject):** a fourth editor; renaming C-5 Marketing mapping workspace as “the authority” while Meta admin still writes independently; declaring the qualified-code vocabulary canonical while the runtime keeps writing legacy flat keys; proving the goal with a dry-run normalize preview instead of a real submission; folding Sales convert mapping or OCR extraction into this write to inflate scope; one status scale that mixes operator binding with contract health; treating mapping drift / unmapped-required as candidate `no_fit`; an evaluator that reads provider payload (Meta questions, raw option labels) instead of canonical facts.

---

## Starting point (measured, not assumed)

Evidence collected 2026-08-28 over `backend/app` and `hostflow-frontend/src`.

### Canonical destinations already exist

`fr_canonical_fields` defines `qualified_code` + `storage.path`; Entity Profile (`ep_entity_profiles`, `ep_entity_profile_fields`) defines which codes belong to a role. **Destinations are not the gap** — the write path to them is.

### Where the same decision is stored three times

| Store | Used when |
|-------|-----------|
| `intake_source_profiles.mapping_rules` | Preferred at ingest when non-empty |
| `meta_lead_form_mappings.mapping_rules` | Per Meta form fallback |
| `meta_lead_settings.field_mapping` | Tenant default fallback |

Resolution is a silent precedence chain in `backend/app/modules/leads/field_mapping_resolve.py` and `backend/app/entity_profile/ingest_runtime.py`. An operator editing the “wrong” one sees no effect and no warning.

### Three operator UIs over overlapping rules

| Route | Writes |
|-------|--------|
| `/app/settings/integrations/meta` (`MetaLeadsAdminPage`) | tenant `field_mapping`, per-form `mapping_rules`, ad→vacancy routing |
| `/app/marketing/sources/:id/mapping` (`MarketingSourceMappingPage`) | `intake_source_profiles.mapping_rules` |
| `/app/marketing/forms/:id` (`IntakeFormMappingEditor`) | same profile rules via intake-form admin API |

Plus read-only diagnostics at `/app/marketing/diagnostics` (mapping health / drift vs `mapping_applied_v1` fingerprint) and a **read-only** CL6 panel in the candidate workspace.

### Two vocabularies, one partial bridge

Rules carry both `target` (legacy flat key) and `qualified_field_code`. `backend/app/field_registry/intake_mapping.py` maps qualified → legacy through a **hardcoded partial dict** (`LEAD_INTAKE_QUALIFIED_TO_NORMALIZED`) and falls through to dot-path targets when unmapped. So a canonical-looking rule may still write a legacy bucket.

### Hardcoded extractors on the public path

Four parallel ways answers become entity-shaped data: Forms answers (`forms.normalized_answers.v1`, explicitly “no domain mapping”), the presentation ↔ legacy bucket bridge, `PUBLIC_INTAKE_FIELD_TO_QUALIFIED` pseudo-rules, and `build_candidate_payload_from_intake_state` (which reads legacy buckets and ignores `presentation_values_v1`).

### Adjacent models that are *not* this write

| Model | Source → destination | Disposition |
|-------|----------------------|-------------|
| CL6 Flight map (`entity_profile_flight_map.v1`) ✅ [#307](https://github.com/igortatarynovich/HostFlow/pull/307) | Flight answer → Profile member on Binding snapshot | **Consume** — already gated; must not be re-forked |
| Sales convert mapping (`convert_mapping_v1`) | SalesInquiry → ClientAccount projection | **Not this write** — different source/destination pair; must be declared, not absorbed |
| Documents OCR mapping (`mapping_candidate.py`) | OCR fields → candidate keys | **Out of v1** (OCR is later); named leftover |
| Telegram intake bootstrap | sender label → candidate name/phone | **Leftover** with owner + expiry |
| Legacy `CandidateProfile` bridge | legacy config keys → qualified codes | **Consume or retire** in MA-4 |

---

## Internal ladder (this program only)

One Active Product slice at a time. RPM program is **DONE**. **MA-1 Contract Gate PASS**. **Mapping Resolution Gate PASS**. **MA-3 is Active Product** (UX contract Accepted; Mapping Operator Gate not PASS; feat open).

```text
MA-1 Authority contract
  → MA-2 Resolution runtime (one store, one resolver)
  → MA-3 Operator surface (one editor)
  → MA-4 Consumer cutover (one vocabulary)
  → Mapping program close (outcome + release delta)
```

| # | Slice | Machine id | Named gate (PASS =) | Depends on | Estimate |
|---|-------|------------|---------------------|------------|----------|
| **MA-1** | Authority contract | `map-authority` | **Mapping Authority Contract Gate** ✅ — one operator question; one write authority named; twelve answerers classified; contract shape (option map, schema ≠ sample, binding vs health, version/drift, evaluator isolation, uncertainty ≠ failure) is SoT; no fourth store. SoT: [mapping-authority-contract.md](../architecture/mapping-authority-contract.md) (`mapping_authority.v1`) | RPM program close (queue amendment) | 1 slice (docs) |
| **MA-2** | Resolution runtime | `map-resolve` | **Mapping Resolution Gate** ✅ — exactly one store answers “which rule applies to this source?”; leftover stores are read-through or migrated; precedence chain removed. SoT: [mapping-authority-resolution.md](../architecture/mapping-authority-resolution.md) (`resolve_mapping_authority`) | MA-1 Gate | 1–2 slices |
| **MA-3** | Operator surface | `map-operator` | **Mapping Operator Gate** — UX SoT: [mapping-authority-operator.md](../architecture/mapping-authority-operator.md). PASS only when an untrained operator connects a source, sees schema, maps every answer, reaches **ready**, and can explain the next submission — on **one** editor (many entry points). Remaining writable surfaces must cease to be editors. | MA-2 Gate | 1 slice (docs this PR + later feat) |
| **MA-4** | Consumer cutover | `map-cutover` | **Mapping Consumer Cutover Gate** — canonical `qualified_code` is the only write vocabulary on the intake path; hardcoded extractors read the authority or are named leftovers with owner + expiry | MA-3 Gate | 1–2 slices |

---

## MA-1 — Authority contract (**PASS**)

**SoT:** [mapping-authority-contract.md](../architecture/mapping-authority-contract.md) · machine id `mapping_authority.v1`.

**Operator question (one):** for this source (Meta form, public form, import file, flight), which incoming answer writes which canonical entity field — including which source **option** writes which canonical **option** when the destination is choice-typed — and what happens when the binding is unset or the contract cannot compute a fact?

**Write authority (one):** `intake_source_profiles.mapping_rules` (per-source lineage). Field Registry `qualified_code` is the destination vocabulary. `meta_lead_form_mappings.mapping_rules` and `meta_lead_settings.field_mapping` are leftover read-through stores. MA-2 removed the silent precedence chain: ingest consults `resolve_mapping_authority` only.

MA-1 ships no runtime and no UI. It forbids a second write authority for the same question. The shape below is **docs SoT**; it does not unlock `feat/mapping-authority-maN-…`.

### Contract shape (normative for MA-1)

The mapping object is a **versioned contract** between an external intake schema and the Field Registry. It is not a convenience table of `source → target` strings.

#### Destination and option map

- Destination is a Field Registry `qualified_code` (legacy flat `target` is not the write vocabulary after MA-4).
- Destination **type is inherited**. Mapping onto an existing HostFlow field must not let the operator change `select` / `boolean` / `date` into free text.
- Creating a new field is a **Field Registry** write (Rule 1), not a Mapping-owned type picker that mints a local dictionary.
- Field map is not enough for choice-typed destinations. The contract must also hold **source option → canonical option**. Example: `Более 8 месяцев` and `Powyżej 8 miesięcy` both become `document_validity = GT_8_MONTHS`. Evaluation and [Requirement Policy](requirement-policy-management.md) never see the provider label.
- Today’s rules (`source` / `target` / `format`) have **no option map**. Hardcoded normalizer aliases (including locale-specific question text) are leftovers to classify in MA-1, not a substitute for option maps.

#### Schema ≠ sample

- **Schema** (provider questions and options, when the API exposes them) is the structure the operator maps. Mapping must be configurable with **no lead yet**.
- **Sample** (test lead, latest lead, or equivalent) is evidence of a real payload. It helps the operator recognise the field; it is not the schema SoT.
- Missing sample is shown as “no sample yet”. It does not block binding and does not imply Unmapped.
- Today’s `last_sample_lead_id` / Graph questions are a starting point, not this contract.

#### Two status scales (do not collapse)

Operator decision and technical fitness are different questions. One scale must not describe both.

| Scale | Applies to | Values | Meaning |
|-------|------------|--------|---------|
| **Source-field binding** | each inbound field | `Mapped` \| `Ignored` \| `Unmapped` | Operator decision: import into a canonical field, consciously drop, or not yet decided. A new provider field must not disappear. |
| **Contract health** | the mapping contract (and the bindings it contains) | `Valid` \| `Needs review` \| `Invalid` | Technical fitness of the saved version vs current provider schema. Independent of whether a given submission has a value. |

A field may be `Mapped` while the contract is `Needs review` (form drifted after a valid binding). Binding `Unmapped` is not the same as contract `Invalid`.

`Ignored` is a decision. `Unmapped` is unfinished work. If an `Unmapped` or drifted `Mapped` field is required by a downstream policy, that must be **visible** on the mapping surface and must not silently skip.

Existing diagnostics (`mapping_applied_v1` fingerprint) prove a rule was applied. They are **not** contract health SoT. C-4 / C-5 preview copy uses a single **Needs review** for “new field or sample changed.” That mixed signal is leftover UI vocabulary: new field → binding `Unmapped`; schema change against a saved version → contract `Needs review` / `Invalid`. Do not reuse the C-5 enum as both scales.

#### Version, drift, contract validity ≠ missing value

The contract is versioned. A later provider sync that adds a field, removes a field, or changes an option does not keep running as if nothing happened. Health becomes `Needs review` or `Invalid` — especially when the affected field feeds Requirement Policy or intake qualification.

**Contract validity is not the presence of a value.** The evaluator must distinguish:

| Situation | Meaning | Evaluation |
|-----------|---------|------------|
| Canonical fact is absent on the person / submission | Candidate did not provide it (or provided a mapped empty). Mapping contract is `Valid`. | Ordinary policy result: missing / `no_fit` when the requirement is mandatory and the fact is evaluable. |
| Canonical fact cannot be computed | Binding `Unmapped`, contract `Needs review` / `Invalid`, option map missing, or schema drift on a required field. | **Only** `needs_info` / `review_required`. **Never** `no_fit`. |

**Mapping uncertainty ≠ candidate failure.** Guessing Qualified / Not Qualified from unreviewed mapping is forbidden.

#### Evaluator isolation

```text
Source field
  → binding: Mapped | Ignored | Unmapped
  → contract health: Valid | Needs review | Invalid
  → canonical fact
  → policy evaluation
  → fit | no_fit | needs_info / review_required
     (existing evaluation vocabulary — do not mint a fourth dictionary)
  → Result / Why / Facts / Source evidence
```

- Evaluation **never** reads provider payload (Meta field names, question text, raw option labels).
- Policy knows only canonical HostFlow fields. Provider, public form, CSV, and recruiter entry are Mapping’s problem, not the evaluator’s.
- Recruiter primary object after this program is consumed: **Result**, then Why / Facts, then source answers as evidence — not the raw questionnaire. That recruiter screen is **not** this program’s named consumer (RS-3 remains placement proof). Intake qualification / `lead_criteria_v1` is **not** Mapping’s write and **not** [RPM-1](requirement-policy-management.md).

#### Mapping Authority Contract Gate

**Outcome:** **PASS**. Named CI: `backend/tests/platform/test_mapping_authority_contract_gate.py`. Boundary: `scripts/architecture/check_mapping_authority_boundary.py`.

PASS when:

1. This brief is merged and the queue Active Product is **MA-1** (or a later MA slice after this gate).  
2. The operator question and write authority above are the SoT — [mapping-authority-contract.md](../architecture/mapping-authority-contract.md).  
3. The contract shape in this section is unchanged except by a later MA slice that **implements** it — not by dropping option maps, collapsing the two scales, or allowing evaluators to read provider payload. Frozen in `mapping_authority.v1`.  
4. No fourth store; no Zapier product; Sales convert / OCR / CL6 not absorbed.  
5. RPM / Intake / Hiring E2E / min HR are not this slice.

This slice **closes** the Contract Gate. Feat remained locked until **MA-2**. Do not start MA-3 editor in a Contract Gate PR (queue invariant 6).

---

## MA-2 — Resolution runtime (**PASS**)

**SoT:** [mapping-authority-resolution.md](../architecture/mapping-authority-resolution.md) · `resolve_mapping_authority`.

Collapse the fallback chain. Success is that a rule saved anywhere the operator can reach lands in the authority, and ingest consults exactly one resolver. Drift diagnostics (`mapping_applied_v1`) keep working as **applied-rule evidence**; contract health / version from MA-1 is the SoT for Valid / Needs review / Invalid.

Out: transformation DSL; Zapier-style conditions. Option maps, binding states, and contract health are **MA-1 contract**, executed here — not new MA-2 semantics.

#### Mapping Resolution Gate

**Outcome:** **PASS**. Named CI: `backend/tests/platform/test_mapping_authority_resolution_gate.py` + `backend/tests/entity_profile/test_mapping_resolve.py`.

PASS when:

1. This brief is merged and the queue Active Product is **MA-2** (or a later MA slice after this gate).  
2. Ingest consults exactly one resolver over `intake_source_profiles.mapping_rules`.  
3. Leftover Meta form / tenant stores are read-through or migrated, not a second ingest answerer.  
4. The silent precedence chain is removed, not documented.  
5. RPM / Intake / Hiring E2E / min HR / MA-3 editor are not this slice.

This slice **closes** the Resolution Gate. Feat remains locked until **MA-3**. Do not start MA-3 editor in this PR (queue invariant 6).

---

## MA-3 — Operator surface (UX contract Accepted; feat open; Operator Gate not PASS)

**SoT:** [mapping-authority-operator.md](../architecture/mapping-authority-operator.md).

The operator object is the **source** (“what will HostFlow do with this form?”), not a mapping-rules table. Mapping is configured from source schema before submissions may exist. At submission runtime, source answers are resolved through the saved Mapping contract into canonical facts before any business evaluation. **Direct runtime caller (one boundary):** Shared Intake / ingestion runtime. Business modules never call Mapping Authority directly. Recruitment / Hiring / RPM / External Intake / routing consume **canonical facts only**. Sales convert, OCR, and CL6 stay adjacent — not this editor.

**Invariant:** one editing surface, many entry points. Connect, form, diagnostics, and “1 field is not configured” may open Mapping; editing always lands in the same workspace. Existing writable surfaces must cease to be editors (deep-link/redirect or separately owned read-only diagnostics).

**Main screen (human language):** “All set — 8 of 8 questions” is the **Ready** projection (not a third status). Binding (`Mapped` / `Ignored` / `Unmapped`) and contract health (`Valid` / `Needs review` / `Invalid`) stay two scales. **Ignored** is always an explicit operator decision; absence of a destination is `Unmapped`. Choice destinations open option map in-row; a choice binding is not Ready while a known source option lacks a canonical binding or explicit ignore. Unknown runtime options must not pass through as raw text. Type belongs to Field Registry. Sample is an example, not schema SoT. Missing sample is “no example answers yet”, not a dead end. Preview is a projection from the saved contract + Field Registry via the same resolver as ingestion — not a second evaluator.

Measured gap (2026-09-04): three writable screens (C-5, Meta Settings, Intake form admin); Connect returns to the campaign; C-5 rows are rules ∪ sample, not schema; health is `ready` / `needs_review` / `broken`; diagnostics drift is a fingerprint boolean; save does not project “next application writes Code 95 = Yes”.

Out: themes, analytics, bulk rule import, a fourth editor, Zapier-style conditions.

#### Mapping Operator Gate

**Outcome:** not PASS. UX contract **Accepted**. Feat `feat/mapping-authority-ma3-operator-gate` is open. An existing mapping page is not Mapping Operator Gate PASS.

PASS when:

1. This UX contract is merged and the queue Active Product is **MA-3** (or a later MA slice after this gate).  
2. An untrained operator connects a source, sees its **schema**, understands where each answer will land, brings mapping to **ready**, and can explain what the next submission will write — without switching between several Settings / admin screens. This is the MA-3 acceptance statement. Preview is a projection through the same resolver as ingestion, not a second evaluator.  
3. One editor writes the authority. Remaining writable surfaces must cease to be editors. Entry points (Connect, form, diagnostics, “1 field is not configured”) open that same workspace.  
4. Schema ≠ sample; no-sample is not a dead end; drift uses the minimum taxonomy (field/option added or removed, type changed, destination no longer valid) and keeps removed fields as historical bindings; save shows a canonical-fact projection; a real submission shows applied evidence (RS-3 remains program proof). Ready, complete option-map, and explicit Ignore follow [mapping-authority-operator.md](../architecture/mapping-authority-operator.md).  
5. RPM / Intake / Hiring E2E / min HR / MA-4 vocabulary cutover are not this slice.

This feat **does not** PASS Mapping Operator Gate because a page exists. PASS requires the close path on a real source: source → schema → explicit bindings/options → Ready → projection → real submission → applied evidence, plus leftover mapping surfaces ceasing to be writers. MA-4 / External Intake / Forms Publish / Hiring are not this feat.

---

## MA-4 — Consumer cutover (queued)

Retire the dual vocabulary on the intake path and make the hardcoded extractors consume the authority. Evaluators and intake consumers read **canonical facts only**; provider payload stays evidence under the contract, not an evaluation input. Anything that cannot be cut over in this slice (OCR mapping, Telegram bootstrap) must be listed with owner and expiry — silent leftovers make the gate STOP.

Out: Sales convert mapping rewrite; CL6 re-fork; a canonical-write refactor of modules outside intake.

---

## Program close = two results

| Field | Meaning |
|-------|---------|
| **Program outcome** | One authority answers source answer (+ option) → canonical entity field; one editor writes it; intake consumers and evaluators read canonical facts only; binding and contract health stay separate scales |
| **Release delta** | Mapping Authority four-checks PASS. External Intake acceptance becomes provable (its acceptance edge is satisfied). Hiring E2E and min HR handoff remain **OPEN** unless separately closed. HostFlow v1 is not release-ready until the [Release Readiness Gate](../gates/release-readiness-gate.md) passes |

---

## Queue position

**Depends on:** [RPM program close](requirement-policy-management.md). The [DAG](../gates/hostflow-v1-release-goal.md) does **not** make RPM a predecessor of Mapping — one-Active-Product serialized them.  
**Unlocks:** Mapping Operator Gate after this feat (not PASS yet); [External Intake / Forms Publish](external-intake-forms-publish.md) acceptance remains a later edge — **not** scheduled here  
**Does not:** mark Mapping Operator Gate PASS; absorb Forms Publish; reopen CL6 / ADR-021; mint a new reference dictionary (Rule 1 — canonical fields stay in Field Registry); open intake qualification / `lead_criteria_v1` as a Mapping write; collapse mapping uncertainty into candidate `no_fit`; start Hiring E2E / min HR; MA-4 vocabulary cutover

---

## Refs

- [Mapping Authority Operator Surface](../architecture/mapping-authority-operator.md) — one editor, many entry points; Mapping Operator Gate criterion
- [Mapping Authority Resolution](../architecture/mapping-authority-resolution.md) — one resolver (`resolve_mapping_authority`)
- [Mapping Authority Contract](../architecture/mapping-authority-contract.md) — operator question + write + twelve-row classification (`mapping_authority.v1`)
- [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) — blocker 2 and the four checks
- [Acceptance suite RS-3](../journeys/release-readiness-acceptance-suite.md) — the proof this program must satisfy
- [Dependency-position review](../gates/v1-release-dag-dependency-position.md) — “three mapping models answer different source→dest pairs”
- [C-5 mapping workspace](acquisition-ui-cutover-c5-mapping-workspace.md) — the profile-rules surface that exists today
- [Source diagnostics](acquisition-source-diagnostics.md) — mapping health / drift evidence to preserve
- [CL6 Flight map](entity-field-composition-cl6-flight-map.md) — adjacent gated mapping runtime (consume, do not fork)
- [Requirement Policy Management](requirement-policy-management.md) — consumes canonical facts; screening / `lead_criteria_v1` is not RPM-1 and not this write

---

## History

- 2026-09-04: Meta form mapping PUT and tenant `field_mapping` PATCH return 410; leftover Meta stores stay read-through. Legacy SPA write clients removed. Intake leftover PUT returns 410. Intake leftover preview over pasted `mapping_rules` is rejected (second algorithm); preview over the saved contract remains a read-only diagnostic. Routing preview is off the operator workspace. Mapping Operator Gate **not PASS**. Leftover writers are not retired as a product claim. Not MA-4 / External Intake / Forms Publish / Hiring.
- 2026-09-04: Feat `feat/mapping-authority-ma3-operator-gate` opened from `4073f3a7` ([#350](https://github.com/igortatarynovich/HostFlow/pull/350)). Close path = source → schema → explicit bindings/options → Ready → projection → real submission → applied evidence, plus leftover writer retirement. Mapping Operator Gate **not PASS**. Not MA-4 / External Intake / Forms Publish / Hiring.
- 2026-09-04: MA-3 UX contract sealed. SoT = [mapping-authority-operator.md](../architecture/mapping-authority-operator.md). Mapping Operator Gate not PASS. Feat still locked. External Intake / Hiring E2E / min HR remain queued.
- 2026-09-04: Mapping Resolution Gate **PASS**. SoT = [mapping-authority-resolution.md](../architecture/mapping-authority-resolution.md) (`resolve_mapping_authority`). One store at ingest. Leftover Meta stores read-through / migrated. Active Product → **MA-3** (brief; feat locked). External Intake / Hiring E2E / min HR remain queued. Not CL8. Foundation stays 🔄.
- 2026-09-04: Mapping Authority Contract Gate **PASS**. SoT = [mapping-authority-contract.md](../architecture/mapping-authority-contract.md) (`mapping_authority.v1`). Named CI + boundary. Active Product → **MA-2** (brief; feat locked). Mapping feat not opened. External Intake / Hiring E2E / min HR remain queued. Not CL8. Foundation stays 🔄.
