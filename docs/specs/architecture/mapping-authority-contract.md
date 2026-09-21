# Mapping Authority Contract

**Status:** **Accepted** (L2 contract — Mapping Authority Contract Gate)  
**Date:** 2026-09-04  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-021`](ADR-021-unified-intake-resolution-model.md) · [`../tasks/mapping-authority.md`](../tasks/mapping-authority.md) · [`mapping-authority-resolution.md`](mapping-authority-resolution.md) · [`mapping-authority-operator.md`](mapping-authority-operator.md) · [`../platform/field-registry-card-configuration.md`](../platform/field-registry-card-configuration.md) · [`../platform/entity-profile-definition-registry.md`](../platform/entity-profile-definition-registry.md) · [`../tasks/entity-field-composition-cl6-flight-map.md`](../tasks/entity-field-composition-cl6-flight-map.md) · [`../tasks/acquisition-ui-cutover-c5-mapping-workspace.md`](../tasks/acquisition-ui-cutover-c5-mapping-workspace.md) · [`../gates/v1-release-dag-dependency-position.md`](../gates/v1-release-dag-dependency-position.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (one owner of this write), **INV-01** (one SoT for the operator question), **INV-16** (contract before a second editor). Does not rewrite L0. Does not mint a fourth mapping store or a Field Registry fork.

> This file is the **SoT** for the operator question and the single write of mapping definition.  
> Field Registry remains destination identity (`qualified_code` + type). Entity Profile remains which codes belong to a role.  
> ADR-021 remains the intake resolution model. This contract names **who may write** source→canonical placement.  
> Machine copy: `mapping_authority.v1` in `backend/app/reference/mapping_authority.py`.  
> Resolver (MA-2): [`mapping-authority-resolution.md`](mapping-authority-resolution.md) · `resolve_mapping_authority`.  
> Operator surface (MA-3): [`mapping-authority-operator.md`](mapping-authority-operator.md) — UX contract; Mapping Operator Gate **PASS**. Consumer cutover (MA-4): Mapping Consumer Cutover Gate **PASS** (`fddadd39`); feat locked.

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
| MA-2 resolver over **that** store (`resolve_mapping_authority`) | `meta_lead_form_mappings.mapping_rules` as a second authority |
| | `meta_lead_settings.field_mapping` as a second authority |
| | A Mapping-owned type picker that mints a local dictionary (Rule 1 — Field Registry owns type) |
| | Provider payload as an evaluation input |

Producer of the current surviving-store write path: `backend/app/entity_profile/mapping_write.py` (`validate_intake_mapping_rules_write`).  
Ingest consults exactly one resolver: `backend/app/entity_profile/mapping_resolve.py` (`resolve_mapping_authority`). This contract forbids a second **write** of the same question. It does not ship the one editor (MA-3).

The other two stores are **read-through / migrated** ([mapping-authority-resolution.md](mapping-authority-resolution.md)). They must not gain new authority writes.

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
| 4 | Silent precedence chain (retired) → one resolver | **Consume** | `backend/app/entity_profile/mapping_resolve.py` |
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
| 3 | One resolver: `resolve_mapping_authority` (MA-2). Evaluation stays on canonical facts. |
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

Reject: a fourth store; renaming C-5 as “the authority” while Meta admin still writes independently; declaring `qualified_code` canonical while this contract blesses legacy `target` as the write vocabulary; collapsing binding and contract health into one scale; treating mapping drift / Unmapped required as candidate `no_fit`; an evaluator that reads provider payload; absorbing Sales convert, OCR, or CL6; opening MA-3 editor in the Resolution Gate PR; starting External Intake / Hiring E2E / min HR; Foundation ✅; a thirteenth write of this question.

---

## Consequences

- MA-2 resolves only this write authority (one store, one resolver). The other two stores are read-through or migrated; the precedence chain is removed. See [mapping-authority-resolution.md](mapping-authority-resolution.md).  
- MA-3 ships one editor over this authority. UX SoT: [mapping-authority-operator.md](mapping-authority-operator.md). Remaining writable surfaces must cease to be editors (deep-link/redirect or separately owned read-only diagnostics).  
- MA-4 makes `qualified_code` the only write vocabulary on the intake path.  
- RPM / evaluators consume canonical facts only. Mapping uncertainty is never `no_fit`.

---

## History
- 2026-09-21: **FP-5 External submission feat opened.** Branch `feat/forms-publish-fp5-external-submit` from `5e2a8f59` ([#384](https://github.com/igortatarynovich/HostFlow/pull/384)). Close path = live public URL → stranger without auth opens it → fills → submit → production intake accepts → real intake/person/application per existing contracts. Browser E2E through that published URL is the later runtime proof, not API composition. External Intake Acceptance Gate **not PASS**. This stamp does not ship runtime. Not Mapping/RS-3. Not leftover-store deletion. Not Hiring. Not embed snippet. Not a new form architecture. Not P4 / P5.
- 2026-09-20: **Operator Publish Gate PASS.** Never published → Publish (`commit_publish`) → Live v1 + public URL → Unpublish (`deactivate_endpoint`) → Inactive + URL absent. After each act the operator surface re-reads backend publication authority. UI does not compute live. Embed snippet is a later product slice. Active Product → **FP-5** (brief; feat locked). Do not start FP-5 / embed in this PR. Not leftover-store deletion. Not Hiring. Not P4 / P5. Mapping Operator Surface inherited red at `54537f00` is not this slice.
- 2026-09-20: **FP-4 Operator Publish Surface feat opened.** Branch `feat/forms-publish-fp4-operator-surface` from `9cc986ce` ([#382](https://github.com/igortatarynovich/HostFlow/pull/382)). Close path = operator opens form → sees current publication state/version → publish or unpublish → sees resulting live state → obtains public URL from product UI. Publish uses closed FP-2 `commit_publish` authority. Live/public URL uses closed FP-3 serve authority. Embed snippet is a later product slice (one serve surface). Operator Publish Gate **not PASS**. This stamp does not ship operator UI. Not leftover-store deletion. Not Hiring. Not P4 / P5. Mapping Operator Surface inherited red at `54537f00` is not this slice.
- 2026-09-20: **Public Serve Gate PASS.** public request → Adapter resolve live publication → frozen `form_publication_versions` snapshot → canonical Form Runtime. Unpublished/inactive not served as live. `form_presentation_runtime_v1` is not HostFlow-form public-serve authority. No second renderer. FP-2 publish-write unchanged. Active Product → **FP-4** (brief; feat locked). Do not start FP-4 in this PR. Not leftover-store deletion. Not Hiring. Not P4 / P5.
- 2026-09-20: **FP-3 Public Serve feat opened.** Branch `feat/forms-publish-fp3-public-serve` from `41be635a`. Public Serve Gate **not PASS**. This stamp does not ship runtime. Mapping program **DONE**.
- 2026-09-20: **FP-2 Publish Action feat opened.** Branch `feat/forms-publish-fp2-publish-action` from `7112279e`. Publish Action Gate **not PASS**. This stamp does not ship runtime. Mapping program **DONE**.
- 2026-09-20: **Forms Publish Contract Gate PASS.** Active Product → **FP-2** (brief; feat locked). Mapping program **DONE**.
- 2026-09-20: Queue amendment names **FP-1** Active Product (brief; feat locked). Mapping program **DONE**.
- 2026-09-20: Mapping program close. Consumer Cutover Gate **PASS** (`fddadd39`; evidence `92206f40`). Product **DONE** with no named successor until amendment.
- 2026-09-19: **Mapping Consumer Cutover Gate PASS.** Cutover code `fddadd39`. Destination vocabulary `qualified_code` is the only intake write. Dual leftover `target` is inference only. Feat locked. Active Product → Mapping program close (brief; feat locked).
- 2026-09-18: **MA-4 Consumer cutover feat opened.** Branch `feat/mapping-authority-ma4-consumer-cutover` from `c20f7987`. Mapping Consumer Cutover Gate **not PASS**. This contract still names destination vocabulary as `qualified_code`; dual `target` remains leftover until MA-4 Gate.
- 2026-09-18: Mapping Operator Gate **PASS**. Active Product → MA-4 (brief; feat locked).
- 2026-09-04: MA-2 Resolution Gate **PASS**. Row 4 retired into the one resolver. Active Product → MA-3 (brief; feat locked).
- 2026-09-04: Accepted as MA-1 Authority contract. Twelve-row classification frozen. Feat locked until a later MA-2 branch. Active Product → MA-2 (brief; feat locked).
