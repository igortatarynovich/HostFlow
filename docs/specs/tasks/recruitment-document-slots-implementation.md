# Task: Requirement & Evidence — implementation plan

**Status:** Implementation backlog (L3). **Canon:** [ADR-016](../architecture/ADR-016-requirement-evidence-document-separation.md), [`requirement-evidence-model-p0.md`](../platform/requirement-evidence-model-p0.md).

**Priority:** Complete **Candidate Evidence** before HR onboarding expansion.

---

## Definition of Done (global)

- [ ] Requirement + Accepted Evidence catalog (platform seed, not module-local lists)  
- [ ] **`candidate_evidence` + `candidate_evidence_documents`** tables with RLS  
- [ ] Recruitment API: choose evidence variant → link documents → approve → satisfy requirement  
- [ ] Process Engine / readiness evaluate **requirement status** via Candidate Evidence + Document Runtime  
- [ ] Handoff snapshot **`requirement_fulfillments[]`**  
- [ ] HR reads fulfillments (no inference from flat document list)  
- [ ] Bridge `slot_*` code renamed or wrapped; no new `EQUIVALENT_*` maps  
- [ ] UAT scenarios in workflow spec §9  

---

## Phase 0 — Catalog (bridge → target naming)

| Step | Work |
|------|------|
| 0.1 | Rename seed `requirement_slots.v1.json` → `requirements.v1.json` with `requirement_code`, `accepted_evidence_variants` |
| 0.2 | Expand seed: identity, legal stay, driving+code95 paths, tacho, medical, criminal, ADR |
| 0.3 | Loader validates variant `document_mapping` (`any_of` \| `all_of`) |
| 0.4 | Deprecate `requirement-document-slots-p0.md` references in new code comments |

**Exit:** registry loads; mapping table in platform spec §9 matches JSON.

**Status:** partial — bridge JSON + `slot_registry.py` exist.

---

## Phase 1 — Satisfaction evaluator (in-memory bridge)

| Step | Work |
|------|------|
| 1.1 | `requirement_satisfaction.py` (wrap / rename `slot_evaluator.py`) |
| 1.2 | Evaluate requirement from catalog + documents **without** Candidate Evidence (bridge) |
| 1.3 | Integrate Requirement Engine: `requirement_required` rules, not flat `document_required` for catalog-covered types |
| 1.4 | Tests: legal stay via residence_card; driving combined vs separate; only license → not satisfied |

**Exit:** tests pass via smoke / unit (see bridge tests).

**Status:** partial — `slot_evaluator.py` + PE integration exist.

---

## Phase 2 — Candidate Evidence (CRITICAL)

| Step | Work |
|------|------|
| 2.1 | Alembic: `candidate_evidence`, `candidate_evidence_documents` |
| 2.2 | Models + RLS policies (`tenant_id`, `candidate_id`) |
| 2.3 | Service: `choose_evidence(candidate, requirement, variant)` → draft row |
| 2.4 | Service: `link_document(evidence_id, document_id, role)` |
| 2.5 | Service: `approve_recruitment_evidence` → `satisfied` + runtime check |
| 2.6 | Service: `supersede_evidence` for replacement flows |
| 2.7 | API under `/candidates/{id}/requirements/...` |

**Exit:** DB-backed evidence; evaluator prefers Candidate Evidence over heuristic document scan.

---

## Phase 3 — Recruitment UI

| Step | Work |
|------|------|
| 3.1 | Checklist by **Requirement** name |
| 3.2 | Evidence variant picker (Accepted Evidence) |
| 3.3 | Dynamic form from Document Type schema |
| 3.4 | Readiness rail uses `requirements[].status` |

---

## Phase 4 — Handoff

| Step | Work |
|------|------|
| 4.1 | Snapshot `requirement_fulfillments[]` from Candidate Evidence |
| 4.2 | `document_entity_links` from evidence document_ids |
| 4.3 | Seed HR Work Eligibility from `legal_stay_confirmation` fulfillment |
| 4.4 | Deprecate snapshot `documents[]` minimal block (keep transitional) |

---

## Phase 5 — HR consumption

| Step | Work |
|------|------|
| 5.1 | HR inbox / review reads `requirement_fulfillments` |
| 5.2 | Verification plan maps **requirement_code**, not duplicate frozensets |
| 5.3 | HR review on same `document_id` — separate `DocumentCheck` |

---

## Phase 6 — Cleanup

| Step | Work |
|------|------|
| 6.1 | Remove `EQUIVALENT_SATISFACTION`, frontend `EQUIVALENT_TYPE_GROUPS` for gates |
| 6.2 | Remove `Document.meta` slot flags (migrate to Candidate Evidence) |
| 6.3 | Architecture guard: no PE rules on raw document types when requirement exists |

---

## Strict order

```
Phase 0 → 1 → 2 → 3 → 4 → 5 → 6
```

**Stop line:** Do not ship HR onboarding UX past Phase 4 without Phase 2 in production schema.

---

## AI Agent Notes

- Four entities are non-negotiable — see ADR-016.  
- “Slot” is bridge terminology only.  
- Document Type ≠ Requirement — never add business gates to type codes alone.
