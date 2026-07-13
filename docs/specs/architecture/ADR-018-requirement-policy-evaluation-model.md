# ADR-018: Requirement Policy & Evaluation Model

**Status:** Accepted  
**Date:** 2026-07-13  
**Layer of change:** Domain | Life Cycle | Constitution  
**Start / Optimize / Scale:** Start (vertical slice), then Optimize  
**Authors:** Platform / Recruitment architecture  
**Related:** [ADR-009](ADR-009-document-hub-platform-layer.md), [ADR-016](ADR-016-requirement-evidence-document-separation.md), [`document-type-registry-v1.json`](../platform/document-type-registry-v1.json), [`requirement-rules-engine-p0.md`](../platform/requirement-rules-engine-p0.md)

> **Note:** В обсуждении фигурировал номер ADR-017; в каталоге ADR-017 уже закреплён за Workspace Layer. Этот ADR — канон runtime-контракта документной системы и требований.

---

## 1. Какой бизнес-процесс изменяется?

Подбор и оформление водителей CE (Recruitment): сбор документов, проверка готовности к этапам pipeline, переход между стадиями (`docs_received` → `permit_ordered` → … → employment). Рекрутер и оператор должны видеть **один** список требований с корректными blockers; система не должна блокировать этап документами, которые ещё не могут или не должны быть получены на этом этапе.

---

## 2. Какая Business Entity затрагивается?

| Entity | Класс | Owner Domain |
|--------|-------|--------------|
| RequirementDefinition | Business (platform registry) | Platform |
| RequirementPolicy | Business (platform registry) | Platform |
| RequirementEvaluation | Support (computed fact) | Platform |
| Document (instance) | Business | Document Hub |
| DocumentType / DocumentTypeVersion | Infrastructure (registry) | Document Hub |
| Candidate (process context) | Business | Recruitment |

---

## 3. Существующая Entity или новая? Почему?

**Evolution check:**

- [x] Можно использовать **существующую** Business Entity (Document, Requirement из ADR-016)
- [x] Можно расширить **существующий** Life Cycle (stage transitions)
- [x] Можно использовать **существующий** Workspace (Requirements section)

**Ответ:** существующие сущности **переопределяются по роли**; новая operational сущность — **RequirementEvaluation** (materialized result).

**Почему текущая модель не подходит:** HostFlow одновременно использует ruleset, profile `document_configs`, requirement slots JSON, frontend stage policy, owner summary и ручной `candidate_evidence`. Это даёт параллельные blockers и ложные блокировки (кейс Yurchuk).

---

## 4. Life Cycle

**Изменяется:** stage gate Recruitment candidate pipeline.

```
docs_received → permit_ordered → … → ready_for_hire → employment_start
```

**Запрещённые переходы:** определяются **только** RequirementEvaluationService для `target_stage` с учётом RequirementPolicy. Legacy fallback запрещён.

---

## 5. Owner Domain

| Entity | Owner Domain | Меняется ownership? |
|--------|--------------|---------------------|
| Document instance, files, extraction, review | Document Hub | нет |
| RequirementDefinition, RequirementPolicy | Platform registry | нет (уточняется контракт) |
| RequirementEvaluation | Platform (computed) | да — новая роль Evidence |
| Stage gate decision | Recruitment (consumer) | нет — только вызывает evaluator |

**Граница (обязательная):**

> **Document Hub сообщает факты о документе.**  
> **Requirement Evaluation интерпретирует эти факты в контексте политики.**

Policy-логика **не проникает** внутрь Hub.

---

## 6. Domain Contract

| Domain | Изменение контракта |
|--------|---------------------|
| Document Hub | Публикует typed Document facts (type, schema-validated data, review status, validity). Не публикует requirement satisfaction. |
| Platform Requirements | Единый `RequirementEvaluationDTO` для UI, stage gate, handoff snapshot. |
| Recruitment | Читает evaluation; пишет только manual overrides / waivers. |
| HR handoff | Читает evaluation projection + document links; не копирует файлы. |

**Ссылки:** обновить [`handoff-contract.md`](handoff-contract.md), [`requirement-evidence-model-p0.md`](../platform/requirement-evidence-model-p0.md) после Slice 1.

---

## 7. Canonical State

- **Единственный SSOT blockers:** `RequirementEvaluation[]` + pinned `requirement_policy_version`.
- **Единственный SSOT document types:** `DocumentType Registry` (`document-type-registry-v1.json` → `ref_document_types`).
- **Риск параллельных истин устраняется:** owner summary, ruleset, frontend policy — **не runtime**.

| Было (запрещено как SSOT) | Становится |
|---------------------------|------------|
| `sample_ruleset.json` | deprecated |
| `CandidateProfile.document_configs.requiredTypes` | deprecated |
| `requirement_slots.v1.json` (runtime) | bridge → deprecated |
| `candidateStageDocPolicy.ts` (blockers) | UI display only / removed |
| Manual `candidate_evidence` for standard docs | auto evaluation |
| `Document.meta` free-form | DocumentData + Extraction + Audit |

---

## 8. Transitions

| Transition | Trigger | Side effects | Новый? |
|------------|---------|--------------|--------|
| Document uploaded | User / intake | Hub stores instance; type may be `unclassified` | evolve |
| Document classified | Operator | `document_type_id` set; schema validation | evolve |
| Document approved | Reviewer | Re-triggers RequirementEvaluation | evolve |
| Requirement auto-satisfied | Evaluator | Materialize/update RequirementEvaluation | **да** |
| Stage advance | Recruiter | Gate calls EvaluationService only | **да** |
| Manual attestation | Operator | Manual Evidence / Override only for non-standard cases | evolve |

---

## 9. History

- [x] Evaluation results versioned via `requirement_policy_version` + `evaluated_at`
- [x] Document field changes — audit trail (DocumentReview / lifecycle)
- [x] Migration: normalize doc types → recompute evaluations; **no manual evidence backfill**

---

## 10. Workspace

| Элемент | Тип | Domain Workspace | Новый? |
|---------|-----|------------------|--------|
| Requirements block | View | Entity Workspace (candidate) | evolve |
| Documents library | View | Document Hub | existing |
| Classification inbox | Command | Document Hub | evolve (`unclassified`) |

**Workspace хранит state?** нет — только отображает Evaluation DTO.

---

## 11. Start / Optimize / Scale

**Класс:** Start — первый вертикальный срез; затем Optimize.

**Обоснование:** Не строим 8 изолированных инфраструктурных этапов. Доказываем архитектуру на **Driver CE / один кандидат / один stage transition**.

---

## 12. Почему существующая модель не подходит?

ADR-016 Phase 2 реализован как **ручной** Candidate Evidence workflow: upload → approve → select evidence → link → approve evidence. Для стандартных документов это двойная работа и источник расхождений UI/backend. Параллельно legacy owner summary показывает «всё OK», а requirement engine — «missing». Driver CE pack требует все requirements сразу, хотя voivodeship_decision и medical_fitness не применимы на ранних этапах.

---

## 13. Альтернативы

| Альтернатива | Плюсы | Минусы | Отклонена |
|--------------|-------|--------|-----------|
| A. Auto-bridge / SQL backfill evidence | Быстрый hotfix | Ложные подтверждения; не лечит модель | **да** |
| B. Ручной Evidence для всех документов (ADR-016 P2 as-is) | Явный audit trail | Двойная работа; UX friction | **да** |
| C. Requirement Policy + auto Evaluation (этот ADR) | Один blocker source; stage-aware | Требует миграции | **выбрано** |
| D. Frontend-only stage rules | Быстро | UI ≠ backend | **да** |

---

## 14. Решение

### 14.1 Канонические сущности

| Сущность | Назначение |
|----------|------------|
| **DocumentType** | Стабильный код типа документа (registry SSOT) |
| **DocumentTypeVersion** | Schema полей, expiry, sensitivity, extraction mapping |
| **Document** | Instance: type, status, validity, owner link |
| **DocumentFile** | Файл(ы) instance |
| **DocumentData** | Schema-validated JSONB (не free `meta`) |
| **DocumentExtraction** | OCR / model output + confidence |
| **DocumentReview** | Решение проверяющего |
| **RequirementDefinition** | Логическое требование (не документ) |
| **RequirementAlternative** | Способ удовлетворения **с условиями** |
| **RequirementPolicy** | Applicability + `blocks_stage` per requirement |
| **RequirementPolicyAssignment** | tenant / company / vacancy / candidate context |
| **RequirementEvaluation** | Materialized результат проверки |
| **RequirementOverride** | Waiver / individual change |

### 14.2 Runtime contract

1. **RequirementDefinition** — единственный источник *что* нужно подтвердить.  
2. **RequirementPolicy** — единственный источник *когда / для кого / что блокирует*.  
3. **RequirementEvaluationService** — единственный источник *результата* для UI, backend gate, handoff.  
4. **Approved document** с valid schema + review → **автоматически** закрывает matching alternatives.  
5. **Manual Evidence** — только нестандартные случаи (attestation, registry, waiver, no-file).  
6. **Document Hub** — хранит документы; **не** интерпретирует requirements.  
7. **Versioning:** document types, requirements, policies — versioned; candidate **pins** policy version.  
8. **`additional_document`** → состояние **`unclassified`** (classification inbox); не участвует в rules.  
9. **Legacy aliases** — только input normalization и migration; **запрещены** в runtime evaluation.  
10. **Owner Summary** — projection из RequirementEvaluation, не SSOT.

### 14.3 Supersede ADR-016 Phase 2 (manual workflow)

ADR-016 **сохраняет** разделение Requirement / Document Instance.  
**Superseded:** обязательный ручной Candidate Evidence для стандартных загруженных документов.  
Evidence Record становится **результатом** Evaluation, не отдельным пользовательским workflow.

### 14.4 Запреты (effective with Slice 1 PR chain)

- Новые записи в `sample_ruleset.json`
- Новые `requiredTypes` в `CandidateProfile.document_configs`
- Новые document codes вне [`document-type-registry-v1.json`](../platform/document-type-registry-v1.json)
- Ручной `candidate_evidence` для стандартных документов
- Новые frontend blocker rules вне Evaluation DTO
- Stage gate обращения к owner summary как к blocker source
- Распознавание типа по `custom_name`
- Auto-backfill evidence как постоянное решение

---

## Implementation Contract — Vertical Slice 1 (Driver CE)

**Goal:** один кандидат (Yurchuk), один transition `docs_received` → `permit_ordered`, один policy, один evaluator path.

### Scope IN

| Deliverable | PR |
|-------------|-----|
| ADR-018 (this document) | docs | **done** |
| Canonical Document Type Registry + legacy aliases + audit + CI guard | **PR 1** | **done** |
| DocumentTypeVersion schemas (Driver CE contour) | **PR 2A** | **done** |
| RequirementDefinition + RequirementPolicy (Poltrakt / Driver CE / PL) | **PR 2A** | **done** |
| DocumentData contract + policy pin | **PR 2A** | **done** |
| Requirement Rule Graph (applicability, dependencies, ownership) | **PR 2A.1** | **done** |
| **PR 2B-0:** Existing Runtime Reuse Review | docs | **done** |
| **PR 2B-1:** Evaluation result contract + tie-break + fingerprint | `requirement_rules/evaluation/` | **done** |
| **PR 2B-2:** RequirementEvaluationService + shadow comparison | `requirement_rules/evaluation/` | **done** |
| **PR 2B-3:** Stage gate cutover + cleanup + Yurchuk migration | guard/workspace/transfer | **done** |
| **ADR-019:** Automation, Capability & Entitlement Control Plane | platform/reaction-orchestrator | **done** (architecture) |
| **3A-0:** Code-level runtime reuse audit (automation plane) | docs §8–§11 | **done** |
| **3A-1:** Event Contract Registry + transactional outbox + dispatcher | platform/events | **next** |
| Stage gate wired to evaluator only | PR 3 |
| Requirements read-model in Entity Workspace | PR 4 |
| Data migration: Yurchuk + normalize types | PR 3–4 |

### Scope OUT (until slice proven)

- Full HR / Fleet policies
- All document type schemas globally
- Admin UI for policy editing
- Automatic policy migration for all in-flight candidates

---

## PR 2A.1 — Dependency and Applicability Model

### Separation: Requirement / Document / Process

| Layer | Examples | Role |
|-------|----------|------|
| **Requirement** | `legal_stay_confirmation`, `labor_market_access`, `driver_attestation` | Business obligation |
| **Document** | passport, visa, residence_card, driver_attestation | Evidence or process output |
| **Process** | work permit application, residence case, GITD attestation | Creates documents/status |

Universal `voivodeship_decision` is **removed** as a requirement. Administrative decisions are typed evidence (`work_permit_decision`, `temporary_residence_decision`, `temporary_residence_and_work_decision`) or `unclassified` until classified.

### Citizenship segments (Poland employment)

| Segment | Labor market access | Work permit process | Driver attestation |
|---------|---------------------|---------------------|-------------------|
| Poland (`pl`) | not_applicable | not_applicable | not_applicable |
| EU / EEA / Swiss | free movement (no work permit) | not_applicable | not_applicable |
| Third country | assessed by stay basis + documents | may activate | applicable for international Community-licence haulage |

**Forbidden:** `citizenship != PL → work permit required`. Non-Polish EU citizens work on the same basis as Polish citizens.

### Requirement Rule Graph (single policy SSOT)

Policy `recruitment.driver_ce.pl/v1` contains four blocks:

1. **applicability_rules** — whether requirement applies to person/segment  
2. **requirement_bindings** + definitions — satisfaction alternatives with conditions  
3. **dependency_rules** — requires / satisfies / excludes / activates / supersedes  
4. **stage_ownership** per binding — source, owner, verification, acquisition, stages  

Implementation: `requirement_rule_graph.plan_requirement_rule_graph()` (planning only).  
PR 2B evaluator consumes the same policy + DocumentData facts.

### Dependency examples (canonical)

- Valid **visa** matched → residence card alternative **excluded** (not missing) for `legal_stay_confirmation`  
- **Residence card** with labor access → separate **work permit process** not_applicable  
- **Driver licence + Code 95** → satisfies `driver_entitlement` and `professional_qualification`; separate qualification card **not_selected**  
- **EU/EEA/CH citizenship** → satisfies `labor_market_access` via free movement  
- Unclassified administrative upload → satisfies **nothing** (classification inbox)

### Driver CE requirement codes (2A.1)

`identity_document`, `legal_stay_confirmation`, `labor_market_access`, `work_authorization_process`, `residence_authorization_process`, `driver_entitlement`, `professional_qualification`, `tachograph_eligibility`, `medical_fitness`, `psychological_fitness`, `driver_attestation`.

---

### Driver CE canonical document types (registry v1.1)

`passport`, `national_identity_card`, `residence_card`, `visa`, `driver_license`, `driver_qualification_card`, `tachograph_card`, `medical_certificate`, `psychological_certificate`, `work_permit`, `voivodeship_decision`, `driver_certificate`, `unclassified` (state only).

### Driver CE requirement codes (target)

`identity_document`, `legal_stay_confirmation`, `driver_entitlement`, `professional_qualification`, `tachograph_eligibility`, `medical_fitness`, `psychological_fitness`, `work_authorization`, `voivodeship_decision` (process-generated).

### Policy sketch — stage blocking (Slice 1)

| Requirement | blocks_stage (initial) |
|-------------|------------------------|
| identity_document | `docs_received` |
| driver_entitlement | `docs_received` |
| professional_qualification | `docs_received` |
| tachograph_eligibility | `docs_received` |
| psychological_fitness | `docs_received` |
| legal_stay_confirmation | `permit_ordered` (non-EU) |
| medical_fitness | `ready_for_hire` |
| voivodeship_decision | `employment_start` |
| work_authorization | `employment_start` |

### Evaluation DTO (shared contract)

```json
{
  "entity_type": "candidate",
  "entity_id": "uuid",
  "target_stage": "permit_ordered",
  "policy_version": "recruitment.driver_ce.pl/v1",
  "evaluated_at": "2026-07-13T12:00:00Z",
  "requirements": [
    {
      "code": "identity_document",
      "status": "fulfilled",
      "applicability": "required",
      "blocks_stage": "docs_received",
      "fulfilled_by": { "kind": "document", "document_id": "uuid", "document_type": "passport" },
      "reason": "approved, valid until 2031-05-01"
    }
  ],
  "blockers": [],
  "can_transition": true
}
```

**Statuses:** `fulfilled` | `pending` | `missing` | `invalid` | `expired` | `waived` | `not_applicable`.

### Expected Yurchuk outcome (post-slice)

| Requirement | Status |
|-------------|--------|
| identity_document | fulfilled (passport) |
| driver_entitlement | fulfilled (driver_license) |
| professional_qualification | fulfilled (driver_qualification_card / code95) |
| tachograph_eligibility | fulfilled (tachograph_card) |
| psychological_fitness | fulfilled (psychological_certificate) |
| legal_stay_confirmation | missing (no visa/residence; non-EU) |
| medical_fitness | not_applicable at `docs_received` |
| voivodeship_decision | not_applicable at `docs_received` |

**Transition `docs_received` → `permit_ordered`:** allowed if policy blocks only requirements fulfilled or not yet due for target stage.

---

## Последствия

### Для кода / данных

- PR 1: registry JSON, loader, audit, CI guard, seed sync from registry
- PR 2–3: evaluator service, deprecate slot_evaluator runtime path for Driver CE
- PR 3: remove legacy stage guard fallbacks for slice stages
- Migration: `documents.document_type_id` bound to canonical ref types; rollback manual Yurchuk evidence

### Для Domain Contracts

- Handoff exports `requirement_evaluations[]`, not flat doc checklist
- Document Hub delivery contract unchanged; adds schema-validated DocumentData

### Для Entity Specs

- Update requirement-evidence-model-p0.md after Slice 1 lands

### Human Language (UI)

| Модель | UI |
|--------|-----|
| RequirementDefinition | «Требование» |
| RequirementEvaluation | «Статус требования» |
| Document (library) | «Документы» (файлы, не checklist) |
| unclassified | «Требует классификации» |

---

## Compliance checklist

- [x] Первый принцип: моделируем работу, не экран
- [x] Identity отделена от State
- [x] Business time: `evaluated_at`, validity on documents
- [x] Layer of change: Domain + Platform registry
- [ ] Entity Spec / Domain Contract обновлены (после Slice 1)

---

## Ссылки

- Constitution: [`hostflow-constitution.md`](../hostflow-constitution.md)
- Document Hub: [ADR-009](ADR-009-document-hub-platform-layer.md)
- Requirement separation: [ADR-016](ADR-016-requirement-evidence-document-separation.md)
- Registry SSOT: [`document-type-registry-v1.json`](../platform/document-type-registry-v1.json)
- Driver CE schemas: [`document-type-schemas-driver-ce-v1.json`](../platform/document-type-schemas-driver-ce-v1.json)
- Requirement definitions: `backend/app/requirement_rules/data/requirement_definitions.v1.json`
- Requirement policy: `backend/app/requirement_rules/data/requirement_policy.recruitment.driver_ce.pl.v1.json`
- DocumentData contract: `backend/app/document_hub/document_data_contract.py`
- Evaluator input contract: `backend/app/requirement_rules/evaluation_input_contract.py`
- **PR 2B reuse audit:** [`existing-runtime-reuse-review-pr2b.md`](existing-runtime-reuse-review-pr2b.md) — Variant B: DocumentRuntime (facts) + RequirementEvaluationService (policy)
- **Next platform layer:** [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md) — Automation & Capability Engine (after 2B-3)
- Legacy aliases: [`document-type-legacy-aliases-v1.json`](../platform/document-type-legacy-aliases-v1.json)
- CI guard: `backend/scripts/check_document_type_registry.py`
- Audit: `backend/scripts/audit_document_type_codes.py`
