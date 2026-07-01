# Requirement & Evidence Model — platform capability canon (P0)

**Status:** Accepted (architecture canon). **Implementation:** Phase 0–1 bridge (evaluator + catalog); **Candidate Evidence persistence — not started**.  
**Hierarchy:** L2 operating canon — platform layer.  
**Owner:** Architecture canon + platform core team.

**Decision record:** [ADR-016](../architecture/ADR-016-requirement-evidence-document-separation.md)

**Supersedes terminology in:** [`requirement-document-slots-p0.md`](requirement-document-slots-p0.md) (bridge doc — do not extend “slot” naming in new code)

**Related canon:**

| Document | Relationship |
|----------|--------------|
| [`requirement-rules-engine-p0.md`](requirement-rules-engine-p0.md) | Resolves *which requirements apply*; satisfaction uses Candidate Evidence + Document Runtime |
| [`document-runtime-engine-p0.md`](document-runtime-engine-p0.md) | Document **instance** lifecycle only |
| [`document-type-model-standard.md`](../architecture/document-type-model-standard.md) | Document **type** = file schema + verification profile — not business requirement |
| [`ADR-009`](../architecture/ADR-009-document-hub-platform-layer.md) | Document Instance storage |
| [`handoff-contract.md`](../architecture/handoff-contract.md) | Exports requirement fulfillment, not document copies |

---

## 1. Purpose

Answer four distinct questions without conflating them:

| Question | Entity |
|----------|--------|
| What must be proven for this candidate / stage? | **Requirement** |
| What document shapes may prove it? | **Accepted Evidence** |
| What did this candidate actually use? | **Candidate Evidence** |
| Where is the file and extracted data? | **Document Instance** |

**Process Engine canon:** gates on **requirement satisfaction**, not document type presence.

---

## 2. Four entities (normative)

### 2.1 Requirement

**Not a document.** A business obligation.

| Field | Description |
|-------|-------------|
| `requirement_code` | Stable id, e.g. `legal_stay_confirmation` |
| `public_name` | i18n label for recruiters / HR |
| `category` | `identity`, `immigration`, `driver_qualification`, `medical`, … |
| `level` | `blocking` \| `recommended` \| `optional` |
| `applicability` | When requirement applies (citizenship, role, vacancy, stage) |
| `verification_policy` | Recruitment approve required before satisfied |

**Seed requirements (platform baseline):**

| requirement_code | Product name |
|------------------|--------------|
| `identity_confirmation` | Identity confirmation |
| `legal_stay_confirmation` | Legal stay confirmation |
| `driving_qualification` | Driving qualification |
| `code95_qualification` | Code 95 qualification |
| `tachograph_qualification` | Tachograph card |
| `medical_fitness` | Medical fitness |
| `criminal_record_check` | Criminal record |
| `adr_qualification` | ADR qualification |

Modules **consume** requirements from catalog; they do not invent parallel requirement lists.

### 2.2 Accepted Evidence

**Catalog entry:** allowed ways to satisfy a requirement. Lives **on the requirement**, not inside Process Engine or pack JSON long-term.

Each **evidence variant** (`evidence_variant_code`):

| Field | Description |
|-------|-------------|
| `evidence_variant_code` | e.g. `visa`, `residence_card`, `combined_eu_license`, `separate_license_and_code95` |
| `public_name` | Recruiter-facing label (“Visa”, “Karta pobytu”, …) |
| `document_mapping` | How instance(s) map to types — see below |
| `sort_order` | UI order in picker |

**Document mapping shapes (same expressiveness as former `satisfaction_alternatives`):**

```yaml
# Single acceptable document type
document_mapping:
  mode: any_of
  document_type_codes: [visa]

# Combined EU license (one file)
document_mapping:
  mode: any_of
  document_type_codes: [driver_license_code95]

# Two separate documents
document_mapping:
  mode: all_of
  document_type_codes: [driver_license, code95]
```

**Example — Legal stay confirmation:**

| evidence_variant_code | document_type_codes (any_of) |
|-----------------------|------------------------------|
| `visa` | visa, visa_d |
| `residence_card` | residence_card, karta_pobytu |
| `permanent_residence` | permanent_residence |
| `eu_passport` | passport (when used as legal stay proof — applicability rule) |

Legislation change → edit **Accepted Evidence** rows only.

### 2.3 Document Instance

Existing **Document Hub** entity ([ADR-009](../architecture/ADR-009-document-hub-platform-layer.md)).

- `document_type_code`, files, `meta` / verified fields, lifecycle status  
- **Does not** encode which business requirement it satisfies (that's Candidate Evidence)  
- No copy at handoff — same `document_id` linked from employee context

### 2.4 Candidate Evidence

**Missing today — mandatory before HR flow expansion.**

Operational fact:

```
Requirement  legal_stay_confirmation
Chosen Evidence variant  visa
Document Instance(s)  #734
Status  satisfied (after recruitment approve)
```

| Field | Description |
|-------|-------------|
| `id` | UUID |
| `tenant_id` | RLS |
| `candidate_id` | Owner during recruitment |
| `employee_id` | Optional; set / linked at handoff |
| `requirement_code` | FK to requirement catalog |
| `evidence_variant_code` | Chosen Accepted Evidence variant |
| `status` | `draft` \| `chosen` \| `satisfied` \| `superseded` |
| `recruitment_verified_at` / `by` | Recruitment approval boundary |
| `superseded_by_id` | Replacement chain (visa → karta pobytu) |

**Document links (junction):**

| Field | Description |
|-------|-------------|
| `candidate_evidence_id` | Parent |
| `document_id` | Hub document |
| `document_type_code` | Denormalized for queries |
| `role` | `primary` \| `component` (for `all_of` bundles) |

One Candidate Evidence row with **two** junction rows for `separate_license_and_code95`.

**Invariant:** At most one **active** (`chosen` \| `satisfied`) Candidate Evidence per `(candidate_id, requirement_code)` unless product explicitly allows history via `superseded`.

---

## 3. Satisfaction pipeline

```
1. Resolve applicable Requirements (Entity Profile + packs + applicability)
2. Load active Candidate Evidence rows for candidate
3. Load linked Document Instances → Document Runtime
4. For each requirement without satisfied evidence:
     - If Candidate Evidence exists → evaluate linked documents against chosen variant mapping
     - Else → requirement status = missing | needs_evidence_selection
5. Emit RequirementEvaluationResult (requirements[], not flat doc codes)
```

| Requirement status | PE blocks? |
|--------------------|------------|
| `not_applicable` | no |
| `missing` | yes if blocking |
| `needs_evidence_selection` | yes — recruiter must pick Accepted Evidence variant |
| `pending_verification` | yes — document uploaded, not approved |
| `satisfied` | no |

**Multi-requirement from one document (advanced):** A single Document Instance may satisfy **multiple** requirements via **separate** Candidate Evidence rows (e.g. combined license → rows for `driving_qualification` and `code95_qualification` with same `document_id`). P1 optional; P0 may use one bundled requirement `driving_qualification_with_code95` instead.

---

## 4. Recruitment UX (product)

Checklist shows **Requirements**, not document types:

```
☐ Identity confirmation
☐ Legal stay confirmation
☐ Driving qualification
☐ Tachograph qualification
```

Recruiter opens **Legal stay confirmation**:

1. **Чем подтверждается?** — picker from **Accepted Evidence** (Visa / Karta pobytu / …)  
2. Form for selected variant’s document type(s)  
3. Upload + field entry  
4. Approve → Candidate Evidence → `satisfied`  
5. Requirement row turns green automatically  

No separate blocking rows for visa **and** karta pobytu.

---

## 5. Handoff to HR

Snapshot block **`requirement_fulfillments[]`** (replaces ambiguous `documents[]` / `document_slots[]`):

```json
{
  "requirement_code": "legal_stay_confirmation",
  "status": "satisfied",
  "chosen_evidence_variant_code": "visa",
  "documents": [
    {
      "document_id": "734",
      "document_type_code": "visa",
      "extracted_fields": {
        "number": "AB123456",
        "expiry_date": "2028-04-12",
        "issuing_country": "PL"
      }
    }
  ],
  "recruitment_verification": {
    "approved_at": "2026-06-30T12:00:00Z",
    "approved_by_user_id": "…"
  }
}
```

HR sees:

- **what** was required  
- **how** it was proven  
- **where** the document lives  
- **what** recruitment verified  

HR review is a **separate** check on the same Document Instance — does not rewrite Recruitment Candidate Evidence.

---

## 6. Replacing evidence (visa → karta pobytu)

1. Mark old Candidate Evidence `superseded`  
2. Create new row: same `requirement_code`, new `evidence_variant_code`, new `document_id`  
3. Requirement code **unchanged**  
4. Handoff / employee context updated via new fulfillment record  

---

## 7. Layering (anti-patterns forbidden)

| Anti-pattern | Why wrong | Correct layer |
|--------------|-----------|---------------|
| PE rule “require visa” | Conflates evidence with requirement | `requirement_code: legal_stay_confirmation` |
| Document type `business_purposes` drives gates alone | Type ≠ candidate choice | Requirement + Candidate Evidence |
| `EQUIVALENT_SATISFACTION` in modules | Duplicates Accepted Evidence | Requirement catalog |
| Handoff flat `documents[]` only | HR guesses intent | `requirement_fulfillments[]` |
| Copy document on handoff | Breaks Hub invariant | Link same `document_id` |

Document type `business_purposes[]` may **inform** Accepted Evidence seeding but **must not** replace Requirement catalog.

---

## 8. Implementation phases

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **0** | Requirement + Accepted Evidence catalog seed | Bridge: `requirement_slots.v1.json` |
| **1** | Requirement satisfaction evaluator (in-memory, no Candidate Evidence table) | In progress |
| **2** | **`candidate_evidence` + junction tables**, Recruitment write API | Not started |
| **3** | Recruitment UI: requirement checklist + evidence picker | Not started |
| **4** | Handoff `requirement_fulfillments[]` | Not started |
| **5** | HR read model + Work Eligibility seed from fulfillments | Not started |
| **6** | Rename bridge code; remove slot terminology | Not started |

**Hard gate:** Do not expand HR onboarding until Phase 2 + 4 exit criteria met.

---

## 9. Bridge mapping (current code → target)

| Bridge (today) | Target |
|----------------|--------|
| `slot_code` | `requirement_code` |
| `satisfaction_alternatives[]` | `accepted_evidence_variants[]` |
| `alternative_code` | `evidence_variant_code` |
| `any_of` / `all_of` | `document_mapping.mode` |
| `slot_evaluator.py` | `requirement_satisfaction.py` |
| `Document.meta.requirement_slot_code` | `candidate_evidence.requirement_code` |
| `evaluate_document_slots()` | `evaluate_requirements()` + DB-backed evidence |

---

## 10. AI Agent Notes

- Read ADR-016 before any Recruitment document or HR verification change.  
- Product language: **Requirement**, **Accepted Evidence**, **Chosen Evidence** — not “slot”.  
- Process Engine consumes **requirement satisfaction** only.  
- Document Hub stays owner of Document Instance; Candidate Evidence is a **platform fact table**, not a Recruitment-only JSON blob.
