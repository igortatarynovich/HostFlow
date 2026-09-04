# Mapping Authority Contract

**Status:** **Accepted** (L2 contract — Mapping Authority Contract Gate)  
**Date:** 2026-09-04  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-021`](ADR-021-unified-intake-resolution-model.md) · [`../tasks/mapping-authority.md`](../tasks/mapping-authority.md) · [`../platform/field-registry-card-configuration.md`](../platform/field-registry-card-configuration.md) · [`../platform/entity-profile-definition-registry.md`](../platform/entity-profile-definition-registry.md) · [`../tasks/entity-field-composition-cl6-flight-map.md`](../tasks/entity-field-composition-cl6-flight-map.md) · [`../tasks/acquisition-ui-cutover-c5-mapping-workspace.md`](../tasks/acquisition-ui-cutover-c5-mapping-workspace.md) · [`../gates/v1-release-dag-dependency-position.md`](../gates/v1-release-dag-dependency-position.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (one owner of this write), **INV-01** (one SoT for the operator question), **INV-16** (contract before a second editor). Does not rewrite L0. Does not mint a fourth mapping store or a Field Registry fork.

> This file is the **SoT** for the operator question and the single write of mapping definition.  
> Field Registry remains destination identity (`qualified_code` + type). Entity Profile remains which codes belong to a role.  
> ADR-021 remains the intake resolution model. This contract names **who may write** source→canonical placement.  
> Machine copy: `mapping_authority.v1` in `backend/app/reference/mapping_authority.py`.

---

## Operator question (one)

For this source (Meta form, public form, import file, flight), **which incoming answer writes which canonical entity field** — including which source **option** writes which canonical **option** when the destination is choice-typed — and what happens when the binding is unset or the contract cannot compute a fact?

No second question is this contract. Requirement Policy, External Intake publish, Hiring E2E, min HR, Sales convert mapping, OCR, CL6 Flight map, and **intake qualification** (`lead_criteria_v1`) are other programs.

---

## Write authority (one)

**Intake source profile mapping rules** — the `intake_source_profiles.mapping_rules` lineage. One mapping contract per intake source. Destination vocabulary is Field Registry `qualified_code`.

| May write | Must not write |
|-----------|----------------|
| `intake_source_profiles.mapping_rules` as the surviving store | A fourth mapping store |
| MA-2 resolver over **that** store (not started this gate) | `meta_lead_form_mappings.mapping_rules` as a second authority |
| | `meta_lead_settings.field_mapping` as a second authority |
| | A Mapping-owned type picker that mints a local dictionary (Rule 1 — Field Registry owns type) |
| | Provider payload as an evaluation input |

Producer of the current surviving-store write path: `backend/app/entity_profile/mapping_write.py` (`validate_intake_mapping_rules_write`).  
Today ingest still consults a silent precedence chain. MA-1 **classifies** that chain as leftover. MA-2 removes it so ingest consults exactly one resolver. This contract forbids a second **write** of the same question. It does not collapse the fallback chain (MA-2) and does not ship the one editor (MA-3).

The other two stores are **read-through until MA-2**. They must not gain new authority writes.

---

## Contract shape (frozen)

The mapping object is a **versioned contract** between an external intake schema and the Field Registry. It is not a convenience table of `source → target` strings.

### Destination and option map

- Destination is a Field Registry `qualified_code`. Legacy flat `target` is leftover vocabulary (MA-4).
- Destination **type is inherited**. Mapping onto an existing HostFlow field must not let the operator change `select` / `boolean` / `date` into free text.
- Creating a new field is a **Field Registry** write, not a Mapping-owned type picker.
- Field map is not enough for choice-typed destinations. The contract must also hold **source option → canonical option** (the option map). Evaluation and Requirement Policy never see the provider label.
- Today’s rules (`source` / `target` / `format`) have **no option map**. Hardcoded normalizer aliases are leftovers, not a substitute.

### Schema ≠ sample

- **Schema** (provider questions and options, when the API exposes them) is the structure the operator maps. Mapping must be configurable with **no lead yet**.
- **Sample** (test lead, latest lead, or equivalent) is evidence of a real payload. It helps the operator recognise the field; it is not the schema SoT.
- Missing sample is shown as “no sample yet”. It does not block binding and does not imply Unmapped.

### Two status scales (do not collapse)

| Scale | Applies to | Values | Meaning |
|-------|------------|--------|---------|
| **Source-field binding** | each inbound field | `Mapped` \| `Ignored` \| `Unmapped` | Operator decision: import, consciously drop, or not yet decided. A new provider field must not disappear. |
| **Contract health** | the mapping contract (and the bindings it contains) | `Valid` \| `Needs review` \| `Invalid` | Technical fitness of the saved version vs current provider schema. Independent of whether a given submission has a value. |

A field may be `Mapped` while the contract is `Needs review` (form drifted after a valid binding). Binding `Unmapped` is not the same as contract `Invalid`. `Ignored` is a decision. `Unmapped` is unfinished work.

Existing diagnostics (`mapping_applied_v1` fingerprint) prove a rule was applied. They are **not** contract health SoT.

### Version, drift, mapping uncertainty ≠ candidate failure

The contract is versioned. A later provider sync that adds a field, removes a field, or changes an option does not keep running as if nothing happened. Health becomes `Needs review` or `Invalid`.

**Contract validity is not the presence of a value.**

| Situation | Meaning | Evaluation |
|-----------|---------|------------|
| Canonical fact is absent on the person / submission | Candidate did not provide it. Mapping contract is `Valid`. | Ordinary policy result: missing / `no_fit` when the requirement is mandatory and the fact is evaluable. |
| Canonical fact cannot be computed | Binding `Unmapped`, contract `Needs review` / `Invalid`, option map missing, or schema drift on a required field. | **Only** `needs_info` / `review_required`. **Never** `no_fit`. |

**Mapping uncertainty ≠ candidate failure.** Guessing Qualified / Not Qualified from unreviewed mapping is forbidden.

### Evaluator isolation

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

Evaluation **never** reads provider payload (Meta field names, question text, raw option labels). Policy knows only canonical HostFlow fields.

---

## Answerer classification (frozen — twelve rows)

A later MA slice may **retire** a leftover. It may not add a thirteenth write of this question.

| # | Live answerer | MA role | Evidence (paths) |
|---|---------------|---------|------------------|
| 1 | `intake_source_profiles.mapping_rules` | **Write authority** | `backend/app/models/intake_routing.py` · `backend/app/entity_profile/mapping_write.py` |
| 2 | `meta_lead_form_mappings.mapping_rules` | **Leftover** | `backend/app/models/lead.py` · `backend/app/modules/leads/field_mapping_resolve.py` |
| 3 | `meta_lead_settings.field_mapping` | **Leftover** | `backend/app/models/lead.py` |
| 4 | Silent precedence chain (profile → Meta form → tenant default) | **Leftover** | `backend/app/entity_profile/ingest_runtime.py` · `backend/app/modules/leads/field_mapping_resolve.py` |
| 5 | Meta Leads admin UI | **Leftover** | `hostflow-frontend/src/pages/admin/MetaLeadsAdminPage.tsx` |
| 6 | C-5 Marketing mapping workspace + Intake form mapping editor | **Consume or fold** into the MA-3 one editor | `hostflow-frontend/src/pages/marketing/MarketingSourceMappingPage.tsx` · `hostflow-frontend/src/components/admin/IntakeFormMappingEditor.tsx` |
| 7 | `mapping_applied_v1` diagnostics fingerprint | **Consume** (applied-rule evidence, not health SoT) | `backend/app/acquisition/mapping_applied_stamp.py` |
| 8 | CL6 Flight map | **Not this write** | `backend/app/entity_profile/flight_map_runtime.py` |
| 9 | Sales `convert_mapping_v1` | **Not this write** | `backend/app/modules/sales/services/convert_mapping.py` |
| 10 | OCR mapping + Telegram intake bootstrap | **Leftover** | `backend/app/modules/documents/mapping_candidate.py` · `backend/app/api/v1/communications/_helpers/telegram_intake/candidate_link.py` |
| 11 | Dual vocabulary + hardcoded extractors + CandidateProfile bridge | **Leftover** | `backend/app/field_registry/intake_mapping.py` · `backend/app/entity_profile/ingest_runtime.py` · `backend/app/entity_profile/public_intake_draft_session.py` · `backend/app/entity_profile/facade.py` |
| 12 | `lead_criteria_v1` + `forms.normalized_answers.v1` | **Not this write** | `backend/app/modules/leads/lead_criteria_eval.py` · `backend/app/forms_platform/answers.py` |

Roles are closed: `write_authority` · `not_this_write` · `leftover` · `consume` · `consume_or_fold` · `consume_or_retire`. Exactly one row is `write_authority`.

---

## Architecture review (L0 — ten questions)

| # | Answer |
|---|--------|
| 1 | **Owner:** Mapping Authority (this contract) writes source→canonical placement. Field Registry owns destination identity and type. Entity Profile owns role membership. Acquisition C-5 is a current editor over the surviving store, not a second authority. |
| 2 | Not a new capability. Collapses three stores answering the same question. Does not mint a fourth editor or a Zapier product. |
| 3 | No new adapter this gate. MA-2 is the one resolver. Evaluation stays on canonical facts. |
| 4 | CL6 stays CL6. Sales convert stays Sales. OCR stays later. Forms answers stay Forms (no domain mapping). No Field Registry fork. |
| 5 | Settings that edit tenant `field_mapping` or per-form Meta rules are leftover writers, not a second overlay product. |
| 6 | SoT for the operator question = this file + `mapping_authority.v1`. Parallel leftover writers are classified, not blessed. |
| 7 | No new event family. Diagnostics `mapping_applied_v1` remains applied-rule evidence. |
| 8 | **Requires:** Field Registry `qualified_code`, Entity Profile role membership, ADR-021 intake source. **Optional:** Graph/schema sync as sample/schema input (not SoT). |
| 9 | No new licence. |
| 10 | Public contract **additive**: authority classification + contract shape. No breaking Hub/Passport change. |

**INV-01:** one SoT for “which answer writes which canonical field?”. **INV-16:** this contract before a second mapping editor.

---

## False close

Reject: a fourth store; renaming C-5 as “the authority” while Meta admin still writes independently; declaring `qualified_code` canonical while this contract blesses legacy `target` as the write vocabulary; collapsing binding and contract health into one scale; treating mapping drift / Unmapped required as candidate `no_fit`; an evaluator that reads provider payload; absorbing Sales convert, OCR, or CL6; opening Mapping feat / MA-2 runtime in this PR; starting External Intake / Hiring E2E / min HR; Foundation ✅; a thirteenth write of this question.

---

## Consequences

- MA-2 resolves only this write authority (one store, one resolver). The other two stores are read-through or migrated; the precedence chain is removed, not documented.  
- MA-3 ships one editor over this authority. Remaining surfaces become views or are retired.  
- MA-4 makes `qualified_code` the only write vocabulary on the intake path.  
- RPM / evaluators consume canonical facts only. Mapping uncertainty is never `no_fit`.

---

## History

- 2026-09-04: Accepted as MA-1 Authority contract. Twelve-row classification frozen. Feat locked until a later MA-2 branch. Active Product → MA-2 (brief; feat locked).
