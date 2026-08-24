# Entity Field Composition CL5 — Recruiter Q&A

**Status:** **IN PROGRESS** (feat)  
**Phase class:** platform  
**Branch:** `feat/entity-field-composition-cl5-qa`  
**Parents:** [CL0 contract seal](entity-field-composition-cl0-contract-seal.md) · [CL2 membership](entity-field-composition-cl2-membership.md) · [CL4 builder](entity-field-composition-cl4-builder.md) · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) · [Sequential queue](sales-to-comms-sequential-queue.md)

> CL5 ships **Recruiter Q&A** as a named consumer artifact (`entity_profile_qa.v1`). Q&A is **not** an Entity Profile implementation — Profile may only ref. Source = Lead / Application, never a copy in `candidate.extra`. Three dispositions exist: Map / Q&A only / Ignore. This slice seals **Q&A only**. Map (raw → `qualified_code`) is CL6 Flight mapping — recognized, not executed. Proof consumer = D4 Q&A zone (`CandidateEntityWorkspacePanel` overview). **Not** Flight (CL6). **Not** a CL3 layout widget. **Not** DR1-runtime. **Not** E8.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After CL4, source answers that are not Profile fields have no named artifact. Without CL5 the next slice will copy Q&A into `candidate.extra`, mint `phone` from «Telefon?», hide answers after convert, treat Q&A as a layout widget, or execute Flight mapping (Zapier UX) inside Profile membership.

**Completion proof (named consumer):**  
`entity_profile_qa.v1` for `recruitment.candidate.driver_ce` — `list_qa_dispositions` / `resolve_qa`. Resolve emits **only** `qa_only` items from Lead / Application (`source=lead_application`). D4 **places** the Q&A zone (`CandidateQaPanel` next to Information / Composition builder). Information zone stays `candidate.card` only. D4 **places**; it does not own field semantics.

**False close:** Copy into `candidate.extra`; mint fields from question text; hide Q&A after convert; Q&A as a CL3 layout widget / card fields; executing Map / Flight snapshot / Zapier UX (CL6); CandidateCard cutover; G4; Client card; Meta admin; Forms P3; dropping `transition_level` columns; Engine evaluation; E8-bind; DR1-runtime.

---

## Scope (Q&A only)

| In scope | Out of scope |
|----------|--------------|
| Dispositions catalogued: `map` / `qa_only` / `ignore` | Executing Map (CL6 Flight) |
| `resolve_qa` emits only `qa_only` | Writing Q&A onto Profile membership |
| Mapped member fields absent; ignore dropped | Copy into `candidate.extra` |
| Survives convert (`survives_convert=true`) | Hiding Q&A after convert |
| Source = Lead / Application | Minting `phone` from «Telefon?» |
| D4 Q&A zone bind (thin) | Q&A as layout widget; CandidateCard cutover |
| Gate test + boundary guard + named CI | DB column drop; E8; DR1-runtime |

---

## Contract shape

```text
list_qa_dispositions() → (map, qa_only, ignore)

resolve_qa(profile_code, source_answers) → only qa_only items:
  contract_id: entity_profile_qa.v1
  profile_code
  source: lead_application
  survives_convert: true
  items[]: source_key, question_label, answer, disposition=qa_only
```

Reject: unknown disposition; treating question text / leaf names as `qualified_code`; writing into `extra`; putting Q&A on Profile membership; executing Map (that is CL6); hiding after convert.

---

## Artifacts

| Artifact | Path |
|----------|------|
| Brief | this file |
| Runtime | `backend/app/entity_profile/qa_runtime.py` |
| D4 bind | `hostflow-frontend/src/platform/entity-workspace/CandidateQaPanel.tsx` |
| Boundary guard | `scripts/architecture/check_entity_profile_qa_boundary.py` |
| Gate test | `backend/tests/entity_field_composition/test_cl5_qa_gate.py` |

---

## CL5 Gate (named)

PASS when:

1. Brief + Q&A runtime committed.  
2. Two-plus dispositions catalogued; `resolve_qa` emits only `qa_only`.  
3. Mapped member fields not in Q&A; ignore dropped.  
4. Question text / `phone` is not a qualified field; no write to `extra`.  
5. Survives convert (not hidden).  
6. D4 places Q&A zone; Information zone still `candidate.card` only.  
7. Boundary guard reports exactly one `resolve_qa` producer.  
8. Named CI job runs `test_cl5_qa_gate.py`.

Unlocks: **CL6** (Flight mapping). Does **not** unlock DR1-runtime or E8.

---

## Queue position

**Depends on:** CL4 Gate ✅ (#305 / `c49716e3`)  
**Unlocks:** CL6  
**Does not:** park on Reference R5; start E8; start DR1-runtime; execute Flight mapping

---

## History

- 2026-08-24: CL5 Recruiter Q&A opened — `entity_profile_qa.v1`; qa_only from Lead / Application; D4 places Q&A zone, not extra / not a layout widget.
