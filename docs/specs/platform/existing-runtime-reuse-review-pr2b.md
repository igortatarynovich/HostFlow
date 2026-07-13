# Existing Runtime Reuse Review — PR 2B

**Status:** Accepted direction  
**Date:** 2026-07-13  
**ADR:** [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md)  
**Prerequisite:** PR 2A + PR 2A.1 (registry, schemas, rule graph)  
**Decision:** **Variant B — Split responsibility**

---

## 1. Цель аудита

Определить, что в текущем runtime можно **расширить**, **заменить** или **удалить**, прежде чем писать Requirement Evaluation для вертикального среза Driver CE / Yurchuk.

**Запрет:** создавать второй параллельный evaluator без явного ownership и cutover-плана.

---

## 2. Найденные evaluators и их responsibilities

### 2.1 Document Hub — document-level (KEEP, extend as fact layer)

| Компонент | Путь | Responsibility | Policy? | Blockers? |
|-----------|------|----------------|---------|-----------|
| **DocumentRuntimeEvaluator** | `backend/app/document_runtime/evaluator.py` | Lifecycle одного instance: `workflow_status`, `expiry_status`, `satisfies_requirement`, `document_runtime_v1` | **Нет** | Только per-document signals (`document_missing`, `document_expired`, …) |
| **Delivery contract** | `backend/app/document_runtime/delivery_contract.py` | Enrich snapshots → `document_runtime_v1`; index/precedence для списков | **Нет** | Нет |
| **DocumentDataContract** (2A) | `backend/app/document_hub/document_data_contract.py` | Hub adapter: meta → canonical DocumentData; schema validation boundary | **Нет** | Нет |
| **Document expiry engine** | `backend/app/services/document_expiry_engine.py` | Даты истечения | **Нет** | Нет |

**Вывод:** `evaluate_document_runtime()` — корректный **fact evaluator** одного документа. Расширять до policy evaluation **нельзя** (нарушит границу Hub). Использовать как dependency RequirementEvaluationService.

**Reuse:** `resolve_workflow_status`, `resolve_expiry_status`, `compute_satisfies_requirement`, `runtime_precedence` — но **вход** должен быть `DocumentDataContract`, не raw snapshot с `meta`.

---

### 2.2 Requirement Rules Engine — legacy bridge (REPLACE for Driver CE slice)

| Компонент | Путь | Responsibility | Policy? | Blockers? |
|-----------|------|----------------|---------|-----------|
| **RequirementRulesEvaluator** | `backend/app/requirement_rules/evaluator.py` | Entity profile rule set → fields + doc types + **slots**; emits `requirement_evaluation_v1` | Частично (pack/profile) | **Да** — `blockers[]` |
| **SlotEvaluator** | `backend/app/requirement_rules/slot_evaluator.py` | Slot + **manual Candidate Evidence** + legacy type expansion via `DOCUMENT_TYPE_DEFINITIONS` | Bridge catalog | **Да** |
| **Slot registry** | `requirement_slots.v1.json` | Legacy slot codes | Superseded by `requirement_definitions.v1.json` | — |
| **Rule graph planner** (2A.1) | `requirement_rule_graph.py` | Applicability + dependencies + stage ownership | **Да** (`recruitment.driver_ce.pl/v1`) | Planning only |
| **Readiness bridge** | `readiness_bridge.py` | Candidate → payload + docs snapshot → `evaluate_requirement_rules` | Indirect | Maps to transfer fragments |
| **Transition bridge** | `transition_bridge.py` | `requirement_evaluation_v1` → PE gate payload | Indirect | Handoff gate |

**Вывод:** `evaluate_requirement_rules()` смешивает три модели:

1. field requirements (intake/readiness) — **оставить** для non-Driver-CE contexts  
2. `RULE_TYPE_DOCUMENT_REQUIRED` (doc type codes) — **deprecate** для Driver CE  
3. `RULE_TYPE_DOCUMENT_SLOT_REQUIRED` + manual evidence — **replace** для Driver CE  

**Reuse:** структура `requirement_evaluation_v1` envelope, `readiness_bridge` document loading, `transition_bridge` mapping pattern — но **источник blockers** меняется.

---

### 2.3 Candidate Evidence — manual workflow (SUPERSEDE for standard docs)

| Компонент | Путь | Responsibility |
|-----------|------|----------------|
| **CandidateEvidenceService** | `backend/app/services/candidate_evidence_service.py` | select → link → approve evidence; `build_requirements_checklist`; `map_requirements_checklist_to_pipeline_blockers` |
| **Models** | `candidate_evidence.py` | Manual fulfillment rows |

**Вывод:** Для стандартных approved documents — **не участвует** в runtime (ADR-018). Остаётся для: waiver, operator attestation, external registry, non-file confirmation.

**Reuse:** `map_requirements_checklist_to_pipeline_blockers` — **shape** blocker lists для stage guard (missing / problematic / pending_review), но данные из нового evaluator.

**Remove from runtime path:** `evaluate_document_slot(..., candidate_evidence=...)` когда requirement satisfiable автоматически.

---

### 2.4 Stage gate — Recruitment consumer (REWRITE adapter)

| Компонент | Путь | Responsibility | Blockers? |
|-----------|------|----------------|-----------|
| **candidate_doc_pipeline_guard** | `backend/app/services/candidate_doc_pipeline_guard.py` | Forward stage block; **dual source** | **Да** |
| **hiring_pipeline_gates** | `backend/app/services/hiring_pipeline_gates.py` | Which stages check docs / vacancy / contact | Config only |

**Текущий порядок в `enforce_pipeline_doc_forward_block`:**

```
1. _requirement_fulfillment_blockers → candidate_evidence_service.build_requirements_checklist
2. else _legacy_document_type_blockers → owner_summary + sample_ruleset
```

**Вывод:** Stage guard **не должен** содержать собственных правил. Становится thin adapter:

```python
result = await requirement_evaluation_service.evaluate(..., target_stage=canon_old)
if result.has_blocking_requirements:
    raise HTTPException(409, detail=result.to_stage_gate_detail())
```

**Remove:** `_legacy_document_type_blockers`, fallback на `owner_summary` для Driver CE profile.

---

### 2.5 Transfer readiness — separate concern (KEEP, integrate read path)

| Компонент | Путь | Responsibility |
|-----------|------|----------------|
| **TransferPolicyResolver** | `backend/app/services/transfer_policy_resolver.py` | Handoff readiness: packs, recruitment package, tenant links, confirmations |
| **Requirements workspace** | `requirements_workspace_service.py` | UI aggregate: checklist + transfer_readiness + field_requirements |

**Вывод:** Transfer policy (`transfer_policy_v1`) — **отдельный** контракт для handoff, не stage doc pipeline. Но `requirement_gate` в workspace должен читать **тот же** RequirementEvaluation DTO, что и stage guard.

**Reuse:** `build_transfer_readiness_section`, workspace assembly — заменить источник requirement_gate.

---

### 2.6 Frontend / DTO status enums (MIGRATE)

| Surface | Current statuses | Target (ADR-018) |
|---------|------------------|------------------|
| `candidateRequirements.ts` | `missing`, `pending_evidence`, `pending_verification`, `satisfied`, `not_applicable`, `unknown` | + `fulfilled`, `not_required_yet`, `not_selected`, `process_pending`, `unresolved`, `expired`, `invalid`, `waived` |
| `requirement_evaluation_v1` | slot statuses | `requirement_evaluation_v2` or extend v1 with `policy_ref` |
| `CandidateEvidenceStatus` | manual workflow | Keep for edge cases only |

---

## 3. Карта: Extend / Replace / Remove

| Asset | Verdict | PR 2B action |
|-------|---------|--------------|
| `document_runtime/evaluator.py` | **Extend as fact layer** | Add adapter from `DocumentDataContract`; no policy |
| `document_hub/document_data_contract.py` | **Keep** | Sole Hub→Evaluation input |
| `requirement_rule_graph.py` | **Keep** | Called by orchestration service |
| `requirement_definitions.v1.json` + policy v1 | **Keep** | SSOT for matching conditions |
| `requirement_rules/evaluator.py` | **Partial replace** | Driver CE stage gate bypasses; fields rules remain |
| `slot_evaluator.py` | **Replace** for Driver CE | Shadow → remove from gate path |
| `candidate_evidence_service` checklist path | **Replace** for standard docs | Supersede manual rows; keep waiver API |
| `candidate_doc_pipeline_guard` legacy fallback | **Remove** after shadow | No owner_summary blockers |
| `owner_summary` + ruleset | **Remove from runtime** | Read-model / diagnostics only |
| `requirement_slots.v1.json` | **Deprecate** | Bridge until all profiles migrated |
| `transfer_policy_resolver` | **Keep** | Consume same evaluation DTO for requirement_gate section |
| Frontend `candidateStageDocPolicy.ts` | **Remove as blocker SSOT** | Display only |

---

## 4. Выбор варианта

### Variant A — Extend `document_runtime/evaluator.py`

**Отклонён.** Evaluator уже декларирует: *«Requirement Engine decides which types are required; this function decides whether instance satisfies.»* Добавление policy/rule graph нарушит границу Hub и смешает document facts с recruitment policy.

### Variant B — Split responsibility ✅ **ВЫБРАН**

```
Document Hub
  → DocumentDataContract + DocumentRuntimeEvaluator (facts)

Platform Policy/Evaluation layer  ← NEW OWNER
  → RequirementEvaluationService
      1. plan_requirement_rule_graph()
      2. match DocumentDataContract + PersonContext
      3. apply dependency rules
      4. compute stage blocking vs target_stage
      5. emit RequirementEvaluationResult DTO

Recruitment (consumer)
  → candidate_doc_pipeline_guard (thin adapter)
  → requirements_workspace_service (read model)
  → transfer_policy_resolver (handoff section)
```

**Не два SSOT:** DocumentRuntime не решает blockers; RequirementEvaluation не читает `meta` напрямую.

### Variant C — Full replace document_runtime

**Отклонён.** Fact layer работает; замена создаст лишний diff без пользы.

---

## 5. Ownership (зафиксировано до кода)

| Layer | Owner module path | Owns |
|-------|-------------------|------|
| Document facts | `backend/app/document_hub/` + `document_runtime/` | instances, schema, lifecycle |
| Policy registry | `backend/app/requirement_rules/data/` + loaders | definitions, policy, rule graph |
| **Requirement evaluation** | **`backend/app/requirement_rules/evaluation/`** (new package) | matching, DTO, tie-break, process states |
| Recruitment consumption | `backend/app/services/candidate_doc_pipeline_guard.py` | entity + target_stage only |
| UI projection | `requirements_workspace_service.py` | read-only assembly |

Recruitment **не** импортирует policy JSON напрямую — только сервис evaluation.

---

## 6. PR 2B implementation order

### Part 1 — Evaluation result contract

**New:** `backend/app/requirement_rules/evaluation/result_contract.py`

Per-requirement row:

- `policy_ref`, `policy_version`
- `requirement_code`
- `applicability` (`applicable` | `not_applicable`)
- `status` (lifecycle — см. список ниже)
- `stage_relevance` (`required_now` | `not_required_yet` | `not_applicable`)
- `is_blocking` (relative to `target_stage`)
- `matched_alternative_code`
- `matched_document_ids[]`
- `matched_person_facts[]`
- `excluded_alternatives[]` (with disposition `not_selected`)
- `missing_fields[]`
- `reasons[]`
- `stage_ownership` (from policy binding)
- `next_action` (optional hint)

**Statuses:**

`fulfilled` | `missing` | `pending_review` | `invalid` | `expired` | `not_applicable` | `not_required_yet` | `not_selected` | `process_pending` | `waived` | `unresolved`

`unresolved` — когда недостаточно данных (например `work_access` не заполнен на residence card).

Envelope: `RequirementEvaluationResult` — same DTO for UI, stage gate, handoff requirement_gate.

### Part 2 — Matching orchestration

**New:** `backend/app/requirement_rules/evaluation/service.py`

Pipeline:

1. Load pinned `policy_ref` from candidate (or resolve + pin)
2. `plan_requirement_rule_graph(person, matched_alternatives=[])`
3. Load documents → `DocumentDataContract[]` via Hub adapter
4. For each applicable requirement: evaluate alternatives (conditions from definitions v1)
5. Apply dependency rules (excludes/satisfies/activates) post-match
6. Compute `is_blocking` from `stage_ownership.blocks_stage` vs `target_stage`

**Reuse:**

- `plan_requirement_rule_graph` (2A.1)
- `validate_document_data` / schema_registry
- `document_runtime.evaluator` for workflow+expiry **after** canonical type confirmed
- Condition kinds from definitions JSON (same registry as 2A.1 tests)

### Part 3 — Deterministic tie-break

**New:** `backend/app/requirement_rules/evaluation/tie_break.py`

Order (per user spec):

1. Fully satisfies alternative conditions  
2. `approved` review  
3. Schema-valid DocumentData  
4. Active / not expired  
5. Later `valid_to`  
6. Newer document version (`document_type_version_id` / updated_at)  
7. Later review timestamp  
8. Stable tie: `document_id` lexicographic  

**Explicitly NOT:** `created_at` alone.

### Part 4 — Process requirements

**New:** `backend/app/requirement_rules/evaluation/process_state.py`

States: `not_started` | `data_required` | `ready_to_submit` | `submitted` | `authority_pending` | `decision_issued` | `document_issued` | `rejected` | `cancelled`

Mapping:

- `work_authorization_process`, `residence_authorization_process`, `driver_attestation`
- `submitted` ≠ `fulfilled` for dispatch-blocking policies
- Process state from candidate process fields / linked process documents (minimal for slice)

---

## 7. Stage gate cutover

### Phase 2B-a — Shadow mode (limited, logged)

```python
new_result = await evaluate_requirements(...)
legacy_blockers = await _requirement_fulfillment_blockers(...)  # or legacy

if divergence(new_result, legacy_blockers):
    log_shadow_divergence(candidate_id, old_stage, new_result, legacy_blockers)

# OLD path still blocks (no dual truth in response)
enforce_legacy(...)
```

Shadow **не** fallback. Feature flag + expiry date in code comment.

### Phase 2B-b — Cutover (same PR or +1 small PR)

- `enforce_pipeline_doc_forward_block` → only `RequirementEvaluationService`
- Delete `_legacy_document_type_blockers` call for Driver CE profiles
- Delete manual evidence path for standard document requirements

---

## 8. Yurchuk migration (same PR or immediate follow-up)

1. Pin `requirement_policy_ref = recruitment.driver_ce.pl/v1`
2. Normalize documents → `DocumentDataContract` + canonical types
3. Classify `additional_document` / unclassified where possible
4. **Supersede** manual `candidate_evidence` rows (not delete): reason `ADR-018 evaluator migration`, link to new evaluation id
5. Recalculate evaluation for `target_stage = permit_ordered`
6. Verify UI DTO matches backend gate
7. Document **which single requirement** blocks (expected: `legal_stay_confirmation` if Poltrakt requires it before `permit_ordered` — **not** tuned to force pass)

---

## 9. Additional tests (beyond 2A.1 decision table)

| # | Scenario | Expected |
|---|----------|----------|
| 10 | Unknown citizenship | `unresolved`, not `third_country` |
| 11 | Expired visa | `legal_stay_confirmation` → `expired` |
| 12 | Approved residence card, empty `work_access` | legal stay fulfilled; labor market `unresolved` |
| 13 | Two passports, one expired | valid one wins (tie-break) |
| 14 | Two valid docs | deterministic choice by tie-break |
| 15 | CE licence, Code 95 expired | entitlement fulfilled; qualification `expired` |
| 16 | Attestation submitted not issued | `process_pending`; blocks dispatch |
| 17 | Legacy alias doc type in evaluation input | rejected / normalized at Hub only |
| 18 | Unclassified doc | satisfies nothing |
| 19 | Change `target_stage` | `is_blocking` changes; base status unchanged |

---

## 10. Contracts preserved vs new

| Contract | Verdict |
|----------|---------|
| `document_runtime_v1` | **Preserved** — attached to DocumentData in evaluation input |
| `requirement_evaluation_v1` | **Extended** — add `policy_ref`, per-requirement v2 rows; keep envelope for bridges during migration |
| `Document Hub delivery contracts` | **Preserved** — no policy in Hub |
| `candidate_evidence_v1` | **Preserved** — edge cases only |
| `transfer_policy_v1` | **Preserved** — handoff; reads evaluation DTO |

---

## 11. PR 2B commit plan

| Commit | Content |
|--------|---------|
| **2B-0** (this doc) | Existing Runtime Reuse Review + Variant B decision |
| **2B-1** ✅ | `result_contract.py` + tie_break + process_state + fingerprint + unit tests |
| **2B-2** ✅ | `RequirementEvaluationService` + matching + shadow logging in stage guard |
| **2B-3** ✅ | Cutover + Yurchuk migration + workspace DTO + remove legacy fallback |

---

## 12. Definition of done (PR 2B)

- [ ] One canonical RequirementEvaluationService (platform layer)
- [ ] DocumentRuntime = facts only
- [ ] UI + backend + stage gate = one DTO
- [ ] Stage guard has no own rules; no owner_summary / slots / frontend policy fallback
- [ ] Manual evidence not in standard document flow
- [ ] Yurchuk: explainable result; block/allow matches single policy reason
- [ ] 19 decision-table / matching tests green

---

## References

- ADR-018: `docs/specs/architecture/ADR-018-requirement-policy-evaluation-model.md`
- Rule graph: `backend/app/requirement_rules/requirement_rule_graph.py`
- Policy: `requirement_policy.recruitment.driver_ce.pl.v1.json`
- DocumentData: `backend/app/document_hub/document_data_contract.py`
