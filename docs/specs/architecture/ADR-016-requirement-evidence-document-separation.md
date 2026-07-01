# ADR-016: Requirement, Evidence, Document Instance, Candidate Evidence

## Status

**Accepted** (architecture direction). Implementation phased — see [`requirement-evidence-model-p0.md`](../platform/requirement-evidence-model-p0.md).

**Supersedes (terminology & layering):** informal “document slot / one_of pack item” approach documented in [`requirement-document-slots-p0.md`](../platform/requirement-document-slots-p0.md) — that doc remains as **bridge** until code migration completes.

## Context

HostFlow mixed three different concerns into **document type codes**:

1. **What the business must prove** (legal stay, driving qualification, …)  
2. **Which document shapes are legally acceptable** (visa, karta pobytu, combined EU license, …)  
3. **A concrete uploaded file** with extracted fields  

Process Engine, Recruitment readiness, and HR handoff then grew **endless `one_of`, equivalence maps, and special cases** because the platform had no first-class layer for “this candidate satisfies Legal Stay **using Visa document #734**”.

Without separation, Recruitment and HR will keep accumulating exceptions.

## Decision

Introduce **four independent platform entities** with strict ownership:

```
Requirement  →  Accepted Evidence  →  Chosen Evidence  →  Document Instance
(business)      (catalog)            (candidate fact)     (Document Hub)
```

| # | Entity | Owns | Does **not** own |
|---|--------|------|------------------|
| 1 | **Requirement** | Business obligation; applicability; PE gate input | Files, document types as requirements |
| 2 | **Accepted Evidence** | Allowed ways to prove a requirement (variants + document-type mapping) | Concrete candidate choice |
| 3 | **Document Instance** | File, type schema, lifecycle, verification state | Business “why this document exists” |
| 4 | **Candidate Evidence** | Link: requirement + chosen evidence variant + document instance(s) | Document storage |

### 1. Requirement

- Canonical codes: `legal_stay_confirmation`, `identity_confirmation`, `driving_qualification`, `code95_qualification`, `tachograph_qualification`, `medical_fitness`, `criminal_record_check`, `adr_qualification`, …  
- Registered in **Requirement Catalog** (platform seed + tenant enablement).  
- **Process Engine** asks: *Is requirement X satisfied?* — never *Is visa present?*  
- Applicability (citizenship, role, vacancy, stage) lives on **Requirement**, not on document type.

### 2. Accepted Evidence

- Per-requirement catalog of **evidence variants** — the only place that lists visa vs karta pobytu vs EU passport for legal stay.  
- Variant shapes:
  - **Single type:** `any_of` one document type (e.g. `visa`)  
  - **Combined type:** `any_of` one combined document type (e.g. `driver_license_code95`)  
  - **Bundle:** `all_of` several types (e.g. `driver_license` + `code95`)  
- Legislative change = **update Accepted Evidence catalog**, not Process Engine rules or HR UI hacks.

### 3. Document Instance

- Unchanged Hub ownership ([ADR-009](ADR-009-document-hub-platform-layer.md)): one canonical row per upload, no copies at handoff.  
- Document **type** describes file schema (number, expiry, …) — not a business requirement.

### 4. Candidate Evidence

- **New operational fact:** “For candidate C, requirement R is fulfilled via evidence variant V using document instance(s) D.”  
- Stored explicitly (not only `Document.meta` flags).  
- Recruitment **writes** Candidate Evidence; HR **reads** it (and may add HR review without replacing Recruitment fact).  
- Handoff snapshot exports **Requirement fulfillment records**, not a flat document list.

## Consequences

### Positive

- PE, readiness, and handoff share one satisfaction signal: **requirement status**.  
- Replacing visa with karta pobytu = update Candidate Evidence row; requirement code unchanged.  
- Document type model stops being business-requirement taxonomy.  
- Model scales to employee lifecycle (renewal replaces evidence + document link, same requirement).

### Migration

| Current (bridge) | Target |
|------------------|--------|
| `slot_code` | `requirement_code` |
| `satisfaction_alternatives` | `accepted_evidence_variants` |
| `Document.meta.chosen_as_variant_for_slot` | `candidate_evidence` row |
| `slot_evaluator` | `requirement_satisfaction_service` (evaluates requirements using catalog + candidate evidence + document runtime) |

Phase 0–1 slot code remains valid **bridge** until `candidate_evidence` table and APIs land (Phase 2).

### Forbidden

- Process Engine blocking on raw `document_type_code` when a requirement exists in catalog.  
- HR inferring legal stay type from document list without Candidate Evidence / handoff fulfillment record.  
- New module-local equivalence maps (`EQUIVALENT_*`, parallel frozensets) outside Requirement + Accepted Evidence catalog.

## Cross-references

- Platform canon: [`requirement-evidence-model-p0.md`](../platform/requirement-evidence-model-p0.md)  
- Workflow: [`recruitment-document-collection-handoff.md`](../workflows/recruitment-document-collection-handoff.md)  
- Handoff: [`handoff-contract.md`](handoff-contract.md)  
- Requirement Engine: [`requirement-rules-engine-p0.md`](../platform/requirement-rules-engine-p0.md)  
- Document Hub: [ADR-009](ADR-009-document-hub-platform-layer.md)  
- Recruitment / HR boundary: [ADR-002](ADR-002-modular-recruitment-hr-boundary.md)

## AI Agent Notes

- Do not add product features that treat `visa` as a Process Engine requirement.  
- Implement Candidate Evidence persistence before expanding HR onboarding UX.  
- Rename user-facing copy to **Requirement / Accepted Evidence / Chosen Evidence** — avoid “slot” in product UI.
