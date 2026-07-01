# Requirement Document Slots — platform capability canon (P0)

> **Status: Superseded (terminology & layering).** Canon is [ADR-016](../architecture/ADR-016-requirement-evidence-document-separation.md) + [`requirement-evidence-model-p0.md`](requirement-evidence-model-p0.md).  
> This file documents the **Phase 0–1 bridge** (`slot_code`, `satisfaction_alternatives`) mapped to **Requirement / Accepted Evidence**. Do not extend “slot” naming in new product copy or APIs.

**Status (bridge):** Accepted for migration only. **Implementation:** evaluator exists; **Candidate Evidence table — not started**.

**Hierarchy:** L2 — transitional; superseded by `requirement-evidence-model-p0.md`.

**Bridge mapping:**

| Bridge term | Target term |
|-------------|-------------|
| `slot_code` | `requirement_code` |
| `satisfaction_alternatives` | `accepted_evidence_variants` |
| `alternative_code` | `evidence_variant_code` |
| Chosen variant in `Document.meta` | **`candidate_evidence` row** (required) |

---

## Historical purpose (bridge)

> When several document types satisfy the same compliance need (e.g. legal stay proof), what does the platform require — and how does it know the requirement is met?

Today HostFlow often lists **flat `document_type_code` rows** (e.g. both `visa` and `residence_card` as separate required items). That is wrong for product semantics and blocks handoff clarity.

| Responsibility | Detail |
|----------------|--------|
| **Slot definition** | Named requirement (`legal_stay_confirmation`) with `one_of[]` variant types |
| **Slot evaluation** | Satisfied when **any** approved variant instance satisfies runtime rules |
| **Variant selection** | Recruiter (or system inference) records **which variant applies** to this candidate |
| **Cross-satisfaction** | Eligibility, readiness, and PE gates use **slot** status, not per-variant duplication |
| **Handoff projection** | Snapshot exports resolved slot → chosen variant + extracted fields |

**Main canon (non-negotiable):**

| Layer | Question |
|-------|------------|
| **Requirement Rules Engine** | Which **slots** are required / blocking for this entity profile, stage, and context? |
| **Document Runtime Engine** | Does a **concrete instance** of variant type X satisfy lifecycle + expiry rules? |
| **Slot evaluator (this extension)** | Is slot S satisfied given all candidate document instances? |

Presentation Rules (P10A) and Form Builder **must not** define slots.

---

## 2. Problem (current state)

| Symptom | Root cause |
|---------|------------|
| Non-EU candidate blocked for missing `visa` even with approved `residence_card` | Eligibility resolver matches flat `document_code` only |
| Recruitment checklist shows two blocking rows for legal stay | Pack lists variants as separate required types |
| HR receives documents but not “recruiter chose visa, not karta pobytu” | Handoff snapshot lacks slot resolution + field payload |
| Three equivalence mechanisms (UI groups, `EQUIVALENT_SATISFACTION`, HR `VERIFICATION_SLOT_DEFS`) | No single platform slot registry |

**Target:** one slot registry, one evaluator, all consumers (Recruitment UI, PE transition, HR plan) read the same result.

---

## 3. Core concepts

### 3.1 Requirement slot

A **requirement slot** is a platform object representing one compliance need.

| Field | Type | Description |
|-------|------|-------------|
| `slot_code` | string | Stable id, e.g. `legal_stay_confirmation`, `identity_document` |
| `public_name` | i18n | UI label for recruiters |
| `business_purpose` | enum | Aligns with document type standard, e.g. `legal_stay`, `identification` |
| `satisfaction_alternatives` | array | **OR** of ways to satisfy the slot (see §3.2) |
| `variant_type_codes` | string[] | **Deprecated** — flat `one_of` shorthand; migrate to `satisfaction_alternatives` |
| `level` | enum | `blocking` \| `recommended` \| `optional` |
| `verification` | enum | `none` \| `optional` \| `required` |
| `expiry_required` | bool | Slot unsatisfied if chosen variant lacks valid expiry when required |
| `stage_rules` | object | When slot applies (e.g. `before_hr_handoff`) |
| `applicability` | condition AST | citizenship, work_country, position_category, … |

**Hard rule:** A slot is **never** a row in `documents`. Only variant types are stored instances.

### 3.2 Satisfaction alternatives (OR of clauses)

A slot is satisfied when **any one alternative** is fully satisfied. Each alternative is one of:

| Clause shape | Meaning | Example |
|--------------|---------|---------|
| `{ "any_of": ["visa", "residence_card"] }` | **One** document of any listed type | Legal stay |
| `{ "any_of": ["driver_license_code95"] }` | Single combined document type | EU license with Code 95 |
| `{ "all_of": ["driver_license", "code95"] }` | **All** listed types must be present and approved | Separate license + Code 95 card |

Normative JSON:

```json
{
  "slot_code": "driver_license_with_code95",
  "satisfaction_alternatives": [
    {
      "alternative_code": "combined_eu_license",
      "any_of": ["driver_license_code95"]
    },
    {
      "alternative_code": "separate_documents",
      "all_of": ["driver_license", "code95"]
    }
  ]
}
```

**Hard rule:** alternatives are **OR**. Clauses inside an alternative use **any_of** (pick one type) or **all_of** (every type required). Do not nest OR inside a clause in P0.

### 3.3 Variant (concrete document type)

A **variant** is a normal canonical `document_type.code` (`visa`, `residence_card`, `driver_license`, …).

- Recruiter selects **which alternative** applies (`satisfaction_alternative_code`) when the slot has multiple paths.
- Instance carries file + `meta` / verified fields per document type schema.
- For `all_of` alternatives, **each** document shares the same `satisfaction_alternative_code` on `Document.meta`.

### 3.4 Chosen alternative / variant

**Chosen alternative** = which satisfaction path the recruiter declared (`combined_eu_license` vs `separate_documents`).

| Storage (P0) | Location |
|--------------|----------|
| Primary | `Document.meta.requirement_slot_code` + `Document.meta.satisfaction_alternative_code` on each instance in the path |
| Single-type alternative | `Document.meta.chosen_as_variant_for_slot = true` on the satisfying instance |
| Denormalized (handoff / HR) | `candidate.extra.recruitment_document_slots[slot_code].chosen_alternative_code` + `document_type_codes[]` |
| HR work eligibility | Seeds `WorkforceWorkEligibilityProfile.legal_stay_document_type` from slot `legal_stay_confirmation` at handoff |

System may **infer** chosen alternative when exactly one alternative is fully satisfied; recruiter confirmation still required before `ready_for_hr` when slot is blocking and multiple alternatives are partially present.

### 3.5 Slot satisfaction

Slot `S` is **satisfied** when:

1. Applicability conditions for `S` are true (or slot not applicable → treated as N/A), **and**
2. ∃ alternative `A` in `S.satisfaction_alternatives` where:
   - **any_of clause:** ∃ type `T` in `A.any_of` with an instance `D` where Document Runtime `satisfies_requirement === true`
   - **all_of clause:** ∀ type `T` in `A.all_of`, ∃ instance `D_T` with `satisfies_requirement === true`
   - If recruiter confirmation required: documents carry `meta.satisfaction_alternative_code === A.alternative_code`

If multiple alternatives are partially satisfied and none chosen → **`needs_alternative_selection`** (blocks handoff). Legacy alias: `needs_variant_selection` in API transitional period.

---

## 4. Slot registry (P0 seed)

Platform seed lives in **`requirement_slots.v1.json`** (new registry file under platform seeds — implementation path TBD; normative content below).

### 4.1 Seed slots (minimum for Recruitment → HR)

| slot_code | business_purpose | variant_type_codes (one_of) | Default level | Applicability sketch |
|-----------|------------------|----------------------------|---------------|----------------------|
| `identity_document` | identification | `any_of`: passport, national_id, id_card | blocking | always (recruitment dossier) |
| `legal_stay_confirmation` | legal_stay | `any_of`: visa, visa_d, residence_card, karta_pobytu | blocking | non-EU; waived for EU/EEA/CH |
| `work_authorization` | right_to_work | `any_of`: work_permit, oswiadczenie, zezwolenie_a | blocking | non-EU when permit required |
| `driver_license_with_code95` | driver_qualification | **`any_of` [driver_license_code95]** OR **`all_of` [driver_license, code95]** | blocking | driver C+E profiles |
| `tachograph_card` | driver_qualification | `any_of`: tachograph_card, tacho_card | blocking | driver profiles per pack |
| `medical_certificate` | medical | `medical_certificate`, `medical`, `badania_lekarskie` | blocking | process profile at `ready_for_handoff` (existing PE rule) |

Tenant may **add** optional slots or tighten level via audited override; may **not** redefine system slot semantics (same policy as document type tenant overrides).

### 4.2 Relationship to document packs

Document packs **reference slots**, not flat duplicate variant lists:

```yaml
# Normative pack item shape (P0 extension)
- slot_code: legal_stay_confirmation
  level: blocking
  reason_code: non_eu_legal_stay
```

Legacy pack rows that list `visa` and `residence_card` separately are **deprecated**; migration maps them to one slot (see task spec).

### 4.3 Relationship to HR verification slots

HR `VERIFICATION_SLOT_DEFS` (`hr_verification_plan.py`) **must consume the same `slot_code` registry** — not maintain a parallel frozenset map. Until migration, HR map is treated as **downstream projection** of platform slots.

---

## 5. Evaluation pipeline

```
1. Resolve applicable slots (Requirement Engine + applicability context)
2. Load candidate document instances (Document Hub)
3. For each slot:
   a. Filter instances by variant_type_codes (+ aliases via canonical bridge)
   b. Pick best instance per variant (Document Runtime)
   c. Determine chosen variant (meta flag or inference rules)
   d. Compute slot_status: satisfied | missing | needs_variant_selection | expired | pending_verification
4. Emit RequirementEvaluationResult.slots[] + flat legacy document_type_codes for transitional consumers
```

### 5.1 Slot status enum

| Status | Blocks handoff | Meaning |
|--------|----------------|---------|
| `not_applicable` | no | Slot does not apply to this candidate context |
| `missing` | yes (if blocking) | No instance for any variant |
| `needs_variant_selection` | yes | Multiple candidates or ambiguous; recruiter must pick |
| `pending_verification` | yes (if verification required) | File uploaded, not approved |
| `expired` | yes | Instance exists but expiry fails |
| `satisfied` | no | Chosen variant approved + valid |

### 5.2 Legacy equivalence map

`EQUIVALENT_SATISFACTION` and frontend `EQUIVALENT_TYPE_GROUPS` are **legacy shortcuts**. P0 implementation **replaces** them for gate logic with slot evaluation. UI may keep group display until slot API is wired.

**Rule:** No new equivalence maps outside slot registry.

---

## 6. Requirement Engine integration

### 6.1 New rule type (extension)

| Type | Code | Meaning |
|------|------|---------|
| Document slot required | `document_slot_required` | Slot must reach `satisfied` |

Process Engine transition evaluation and `recruitment_package_readiness` consume **`slots[]`**, not duplicated per-variant missing lists.

### 6.2 Evaluation result shape (normative sketch)

```json
{
  "slots": [
    {
      "slot_code": "legal_stay_confirmation",
      "status": "satisfied",
      "level": "blocking",
      "chosen_variant_type": "visa",
      "satisfying_document_id": "uuid",
      "variants_present": ["visa", "residence_card"],
      "blockers": []
    }
  ],
  "missing_slots": [],
  "legacy_missing_documents": ["visa"]
}
```

`legacy_missing_documents` is **transitional** only — populated for consumers not yet migrated; must not drive UI after Phase 2 (see task spec).

---

## 7. Handoff projection

Handoff snapshot (`candidate_handoff_snapshots.payload` v1 → v1.1 extension) adds:

```json
{
  "document_slots": [
    {
      "slot_code": "legal_stay_confirmation",
      "status": "satisfied",
      "chosen_variant_type": "visa",
      "document_id": "uuid",
      "document_type_code": "visa",
      "workflow_status": "approved",
      "expires_at": "2027-03-01",
      "extracted_fields": {
        "number": "…",
        "issue_date": "…",
        "expiry_date": "…",
        "issuing_country": "PL"
      }
    }
  ],
  "documents": []
}
```

- Existing `documents[]` block **remains** for backward compatibility during migration.
- HR seeds `legal_stay_document_type`, `legal_stay_valid_to` from `document_slots` entry for `legal_stay_confirmation`.
- Files are **not** copied — only ids + metadata (invariant from ADR-002 / handoff-contract).

---

## 8. Consumer matrix

| Consumer | Uses slots for |
|----------|----------------|
| Recruitment `CandidateDocuments` UI | Render one row per slot; variant picker + upload |
| `evaluate_recruitment_package` | Handoff gate blockers |
| `TransferPolicyResolver` / PE transition | Stage → `ready_for_hr` |
| `WorkforceEligibilityResolver` | Missing legal stay (any variant) |
| Handoff snapshot builder | `document_slots[]` |
| HR verification plan | Slot → checklist row (reuse registry) |
| Work eligibility journey | Pre-fill from handoff slot resolution |

---

## 9. Non-goals (P0)

| Non-goal | Where instead |
|----------|---------------|
| Slot admin UI / drag-and-drop designer | Future platform admin |
| Custom tenant slot creation (semantic) | Forbidden — request platform slot |
| OCR auto-fill of variant fields | Document type `supports_ocr_extraction` — later slice |
| Multiple simultaneous chosen variants per slot | Out of scope |
| Inter-tenant slot sharing | Out of scope |

---

## 10. Enforcement

Architecture is not implemented until:

1. Guard: no new `EQUIVALENT_*` maps in module code without slot registry reference
2. Tests: legal stay satisfied by `residence_card` only → handoff not blocked for missing `visa`
3. Tests: two variants uploaded, none chosen → `needs_variant_selection` blocks transition
4. Handoff snapshot contains `document_slots` for blocking slots

---

## 11. AI Agent Notes

- Before changing recruitment document checklist or HR legal-stay logic, read this file + [`recruitment-document-collection-handoff.md`](../workflows/recruitment-document-collection-handoff.md).
- Implement slot registry before UI rework.
- Do not add parallel HR-only slot maps — extend platform registry.
- Concrete document instances always use canonical `document_type.code`; slots are evaluation-only grouping.
