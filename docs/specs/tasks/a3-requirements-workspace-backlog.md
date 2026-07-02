# A3 — Requirements Workspace: backlog реализации

**Status:** implementation backlog (L3 task spec).  
**Parent canon:** [recruitment-operational-goals-and-order.md](../workflows/recruitment-operational-goals-and-order.md) §8 A3.  
**Architecture:** [requirement-evidence-model-p0.md](../platform/requirement-evidence-model-p0.md), [ADR-016](../architecture/ADR-016-requirement-evidence-document-separation.md), [requirement-rules-engine-p0.md](../platform/requirement-rules-engine-p0.md).

**Цель:** рекрутер открывает Candidate и видит **что закрыть** (checklist-first workspace), а не три параллельных чеклиста в узком rail поверх карточки.

**Proof profile (P0):** `recruitment.candidate.driver_ce` (Польша, водитель CE).

---

## 1. AS-IS (что уже есть)

### Backend — готово к потреблению

| Capability | Endpoint / service | Файл |
|------------|-------------------|------|
| Requirements checklist + pipeline blockers | `GET /api/v1/candidates/{id}/requirements/checklist` | `backend/app/api/v1/candidate_requirements.py` |
| Evidence workflow | `POST .../select-evidence`, `.../documents`, `.../approve`, `.../reject`, `.../replace-evidence` | `candidate_evidence_service.py` |
| Transfer readiness | `GET /api/v1/candidates/{id}/transfer-readiness` | `candidates/router.py` |
| Recruitment package | `GET /api/v1/candidates/{id}/recruitment-package` | `candidates/router.py` |
| Pipeline guard (409 на stage forward) | — | `candidate_doc_pipeline_guard.py` |
| Handoff fulfillments export | — | `build_requirement_fulfillments_for_candidate` |
| Platform evaluate | `POST /api/v1/platform/requirement-rules/evaluate` | `requirement_rules.py` |
| Work panel preview (list) | `GET /api/v1/candidates/{id}/work-panel` | `candidate_work_panel.py` |

### Frontend — долг

| Проблема | Деталь |
|----------|--------|
| Три параллельных UI | `CandidateRequirementsChecklist` + `RecruitmentDossierChecklist` + `CandidateDocsRailPanel` в одном rail |
| Checklist в узком rail | Evidence actions не помещаются; нет sequential flow |
| `TransferReadinessReport` не смонтирован | Данные грузятся, UI нет; scroll `#section-transfer-readiness` сломан |
| Dossier blocks — локальный FE catalog | `RECRUITMENT_DOSSIER_BLOCKS` дублирует requirements API |
| Нет маршрута workspace | Только `/candidates/:id` card |
| Ранние стадии без preview | Checklist скрыт до mid-funnel |

### Slot catalog (текущий seed)

`backend/app/requirement_rules/data/requirement_slots.v1.json`:

- `identity_document`
- `legal_stay_confirmation` (N/A для EU citizenship)
- `driver_license_with_code95`
- `tachograph_card`
- `work_authorization` (N/A для EU)

**Gap в catalog (добавить в A3-S0):** medical fitness, psychotests, PESEL, address/contacts data-only requirements, operational (call/write) — см. §5.

---

## 2. TO-BE — информационная архитектура

### 2.1 Принцип

```text
Candidate Card (контекст: профиль, стадия, timeline)
    │
    └── CTA «Требования» / primary tab
            │
            └── Requirements Workspace (full-width drawer или route)
                    ├── Summary bar (N/M closed, handoff readiness)
                    ├── Requirement list (filter: open | all | handoff)
                    ├── Detail pane (per selected requirement)
                    │     ├── Data fields (inline edit)
                    │     ├── Evidence variant picker
                    │     ├── Linked documents + upload
                    │     └── Approve / reject / replace
                    ├── Handoff readiness pane (transfer policy)
                    └── Activity pane (call / message requirements)
```

**Candidate card rail** после A3: **summary + CTA**, не полный checklist.

### 2.2 Маршрут

| Вариант | Path | Рекомендация |
|---------|------|--------------|
| Route | `/app/candidates/:id/requirements` | **P0** — deep link из списка, handoff queue |
| Drawer | `?workspace=requirements` на card | **P0** — быстрый вход без смены route |
| Rail-only | текущее | **deprecate** после P0 |

### 2.3 Единый источник истины в UI

| Данные | Источник API | Запрещено |
|--------|--------------|-----------|
| Список требований | `requirements/workspace` → `checklist` | `RECRUITMENT_DOSSIER_BLOCKS` как primary |
| Статус closure | `evaluation.status` + evidence | Ручной confirm в `candidate.extra` |
| Handoff gates | `transfer_readiness` | Локальная логика на FE |
| Документы | Document Hub via evidence link | Отдельный doc-type checklist при active requirements mode |

---

## 3. API — новые и изменённые контракты

### 3.1 `GET /api/v1/candidates/{id}/requirements/workspace` (новый, A3-B1)

**Назначение:** один bundle для workspace UI (не 3–4 round-trip).

**Response `requirements_workspace_v1`:**

```json
{
  "schema_version": "requirements_workspace_v1",
  "candidate_id": "uuid",
  "entity_profile_code": "recruitment.candidate.driver_ce",
  "vacancy_id": "uuid|null",
  "can_edit": true,
  "summary": {
    "total_requirements": 12,
    "fulfilled_count": 5,
    "blocking_open_count": 4,
    "pending_review_count": 1,
    "all_fulfilled": false,
    "handoff_ready": false
  },
  "checklist": { },
  "field_requirements": {
    "required_fields": [
      { "qualified_code": "personal.phone", "level": "blocking", "satisfied": false, "current_value": null }
    ],
    "missing_count": 3
  },
  "transfer_readiness": {
    "transfer_allowed": false,
    "handoff_create_allowed": false,
    "blocking_reasons": [],
    "policy_version": "transfer_policy_v1"
  },
  "pipeline_blockers": {
    "source": "requirement_fulfillment_v1",
    "missing_requirements": [],
    "pending_review_requirements": []
  },
  "operational_requirements": [
    {
      "requirement_code": "first_contact_completed",
      "type": "activity",
      "status": "open",
      "activity_id": null
    }
  ],
  "evaluated_at": "ISO8601"
}
```

**Реализация:** compose в `candidate_evidence_service` или новый `requirements_workspace_service.py`:

1. `build_requirements_checklist`
2. `evaluate_candidate_readiness_requirements` (field + engine blockers)
3. `TransitionEvaluatorAdapter.evaluate_transition` с `target_system_stage=ready_for_handoff` (для честного handoff preview)
4. operational requirements (Phase 2 — Activity bridge)

### 3.2 `GET /transfer-readiness` — параметр `target_stage` (A3-B2)

Query: `?target_stage=ready_for_handoff`

Включает `requirement_gate` / `requirement_engine` overlay в ответе (сейчас пропускается без target).

### 3.3 `GET /recruitment-package` — вернуть `requirement_engine` (A3-B3)

Сейчас вычисляется в `evaluate_recruitment_package`, но router **отрезает** из response. Вернуть subset для workspace.

### 3.4 Operational requirements API (A3-B4, Phase 2)

`POST /candidates/{id}/requirements/{code}/complete-activity` — закрытие activity-type requirement с ссылкой на Activity id.

**Зависимость:** Slice 4 activity continuity.

---

## 4. Frontend — компоненты и файлы

### 4.1 Новые

| Компонент | Path | Роль |
|-----------|------|------|
| `CandidateRequirementsWorkspace` | `pages/candidate/CandidateRequirementsWorkspace.tsx` | Shell: layout, data fetch |
| `RequirementsWorkspaceSummaryBar` | `components/candidate/requirements/RequirementsWorkspaceSummaryBar.tsx` | Progress, handoff CTA state |
| `RequirementsWorkspaceList` | `components/candidate/requirements/RequirementsWorkspaceList.tsx` | Filterable list; refactor from `RequirementRow` |
| `RequirementDetailPane` | `components/candidate/requirements/RequirementDetailPane.tsx` | Variant, docs, approve |
| `RequirementDataFieldsPane` | `components/candidate/requirements/RequirementDataFieldsPane.tsx` | Data-only requirements |
| `RequirementActivityPane` | `components/candidate/requirements/RequirementActivityPane.tsx` | Call / message closure |
| `HandoffReadinessPane` | `components/candidate/requirements/HandoffReadinessPane.tsx` | Mount `TransferReadinessReport` |
| `useRequirementsWorkspace` | `hooks/useRequirementsWorkspace.ts` | Bundle fetch + invalidation |

### 4.2 Рефактор (extract, не переписывать)

| From | To |
|------|-----|
| `CandidateRequirementsChecklist.tsx` → `RequirementRow` | Shared `RequirementRow` in `requirements/` |
| `requirementsChecklistPresentation.ts` | Unchanged, shared |
| `useCandidateRequirementsChecklist.ts` | Used by detail pane mutations |
| `TransferReadinessReport.tsx` | Embedded in `HandoffReadinessPane` |
| `CandidateDocuments.tsx` | `RequirementScopedDocuments` wrapper with `document_type_codes` filter |

### 4.3 Упростить на CandidateCard (A3-FE4)

| Было | Станет |
|------|--------|
| Full `CandidateRequirementsChecklist` in rail | `RequirementsWorkspaceSummaryCard` + button «Открыть требования» |
| `RecruitmentDossierChecklist` in rail | Hidden when workspace active; data from API only at handoff tab |
| `CandidateDocsRailPanel` full checklist | KPI + «Open workspace» only |
| `showTransferReadinessReport` without UI | Remove flag; readiness only in workspace |

### 4.4 i18n

Keys under `app.candidate_requirements.workspace.*` in `ru.json`, `en.json`, `pl.json`.

---

## 5. Типы требований — acceptance criteria

### 5.1 Тип A — **Данные** (data-only)

**Примеры:** телефон, email, адрес, PESEL, паспортные поля (без файла), опыт работы.

| # | Критерий |
|---|----------|
| A-D1 | Workspace показывает секцию «Данные» с полями из `field_requirements.required_fields` |
| A-D2 | Поля редактируются inline; save → PATCH candidate; workspace refetch |
| A-D3 | Satisfied = engine считает поле заполненным (не локальный state) |
| A-D4 | Blocker chip на stage panel показывает `qualified_code` / label |
| A-D5 | Handoff blocked пока blocking field empty |

**API:** `field_requirements` в workspace bundle; PATCH `/candidates/{id}` (existing).

**Тесты:**

- `test_requirements_workspace_data_fields.py` — missing phone blocks handoff preview
- FE: `RequirementDataFieldsPane.test.tsx`

---

### 5.2 Тип B — **Документ** (evidence → document only)

**Примеры:** tachograph card, psychotest result (file only).

| # | Критерий |
|---|----------|
| A-B1 | Строка requirement показывает статус: missing → variant → link → pending_review → satisfied |
| A-B2 | Recruiter выбирает `evidence_variant_code` из `accepted_evidence_variants` |
| A-B3 | Upload или link существующего Document Instance по `document_type_codes` variant |
| A-B4 | Approve evidence → `fulfilled=true`, requirement исчезает из `missing_requirements` |
| A-B5 | Reject → статус rejected, requirement снова open с причиной |
| A-B6 | Replace evidence → supersede chain, тот же `requirement_code` |

**API:** existing evidence endpoints.

**Тесты:** extend `test_candidate_requirements_integration.py` with workspace bundle assertions.

---

### 5.3 Тип C — **Документ + данные** (evidence + extraction)

**Примеры:** паспорт (файл + серия/номер), karta pobytu / visa (файл + даты), decyzja wojewody, права с категорией, Code 95, медкомиссия.

| # | Критерий |
|---|----------|
| A-C1 | Detail pane: document preview + extracted/required fields side-by-side |
| A-C2 | Missing extraction fields → status `pending_verification` или data blocker |
| A-C3 | Combined variant (`driver_license_code95`) vs separate (`driver_license` + `code95`) — UI показывает оба пути |
| A-C4 | `legal_stay_confirmation` N/A когда `citizenship_group=eu` — строка `not_applicable`, не blocker |
| A-C5 | Approve disabled пока blocking fields on linked document empty |

**API:** document extraction fields from Document Hub snapshot in checklist row.

**Тесты:**

- `test_requirements_workspace_combined_license.py` — combined vs separate paths
- `test_legal_stay_not_applicable_eu.py`

---

### 5.4 Тип D — **Операционное действие** (activity)

**Примеры:** позвонить кандидату, написать в WhatsApp, запросить документ (comms).

| # | Критерий |
|---|----------|
| A-D1 | Requirement type `activity` в workspace с CTA «Записать звонок» / «Открыть чат» |
| A-D2 | Закрытие = Activity создана с `related_entity_type=candidate` и типом из catalog |
| A-D3 | Lead-side contact **не** создаёт duplicate task на Candidate (Slice 4 continuity) |
| A-D4 | SLA / overdue badge если activity requirement open > N hours (reuse reminders) |
| A-D5 | Не путать с pipeline stage «contacted» — requirement closure независим или linked per process profile |

**API:** A3-B4 (Phase 2); catalog seed `operational_requirements.v1.json`.

**Зависимость:** [slice-4-activity-continuity-guards.md](../workflows/slice-4-activity-continuity-guards.md).

**Тесты:** `test_operational_requirement_activity_closure.py`, continuity guard integration.

---

### 5.5 Тип E — **Handoff gate** (aggregate)

Не отдельное требование — **результат** closure A–D.

| # | Критерий |
|---|----------|
| A-E1 | Summary bar: «Готов к передаче» только когда `transfer_readiness.transfer_allowed=true` |
| A-E2 | Handoff button disabled с списком `blocking_reasons` (grouped by layer) |
| A-E3 | Stage PATCH to `ready_for_handoff` → 409 с теми же blockers (parity UI ↔ API) |
| A-E4 | `requirement_fulfillments[]` в handoff snapshot = только approved evidence |
| A-E5 | Workspace handoff tab = mounted `TransferReadinessReport` |

**Тесты:** extend `test_transfer_policy_regression.py`, `test_candidate_requirement_pipeline_guard.py`.

---

## 6. Срезы реализации (порядок PR)

### A3-S0 — Catalog expansion (backend, 1 PR) — **Done (2026-07-01)**

**Scope:** расширить `requirement_slots.v1.json` + field requirements в Entity Profile seed:

| Requirement code | Тип | Примечание |
|------------------|-----|------------|
| `contacts_and_address` | Data | phone, email, address fields |
| `pesel` | Data | conditional PL |
| `passport_identity` | Doc+data | merge with identity_document or sub-variant |
| `work_experience` | Data | structured experience |
| `medical_fitness` | Doc+data | медкомиссия |
| `psychological_tests` | Doc | psychotest file |
| `voivodeship_decision` | Doc+data | decyzja wojewody |
| `first_contact_completed` | Activity | Phase 2 stub OK |

**Done when:** checklist API returns new rows for `driver_ce` profile; tests seeded. ✅

---

### A3-B1 — Workspace bundle API (backend, 1 PR) — **Done (2026-07-01)**

**Files:**

- `backend/app/api/v1/candidate_requirements.py` — `GET .../requirements/workspace`
- `backend/app/services/requirements_workspace_service.py` — new
- `backend/tests/api/test_requirements_workspace.py` — new
- `backend/tests/services/test_requirements_workspace_service.py` — new

**Done when:** §3.1 response shape stable; includes checklist + field_requirements + transfer_readiness with `target_stage=ready_for_handoff`. ✅

**Note:** `summary.handoff_ready` mirrors legacy `transfer_allowed` (may still block on dossier confirmations until A3-FE4). `requirement_gate.satisfied` — честный сигнал closure requirements engine.

---

### A3-B2 — Transfer-readiness `target_stage` query (backend, small PR) — **Done (2026-07-01)**

**Done when:** `GET /transfer-readiness?target_stage=ready_for_handoff` returns `requirement_gate`. ✅

---

### A3-FE1 — Workspace shell + route (frontend, 1 PR) — **Done (2026-07-01)**

**Scope:**

- Route `/app/candidates/:id/requirements`
- `CandidateRequirementsWorkspace` + `useRequirementsWorkspace`
- List + summary bar (read-only first)
- CTA «Open workspace» на `CandidateRequirementsChecklist`
- Feature flag `VITE_FEATURE_REQUIREMENTS_WORKSPACE` (default `true`)

**Files:**

- `hostflow-frontend/src/pages/candidate/CandidateRequirementsWorkspace.tsx`
- `hostflow-frontend/src/hooks/useRequirementsWorkspace.ts`
- `hostflow-frontend/src/components/candidate/requirements/*`
- `hostflow-frontend/src/api/candidateRequirements.ts` + types

**Done when:** navigable from card CTA; shows checklist from bundle API. ✅

---

### A3-FE2 — Requirement detail + evidence actions (frontend, 1 PR) — **Done (2026-07-01)**

**Scope:**

- Extract `RequirementRow` → `RequirementDetailPane`
- Wire mutations from `useCandidateRequirementsChecklist`
- Requirement-scoped document drawer
- Master-detail workspace layout (`RequirementsWorkspaceNavList` + detail pane)

**Done when:** full evidence flow works in workspace (Type B, C partial). ✅

---

### A3-FE3 — Data fields pane (frontend + backend, 1 PR) — **Done (2026-07-01)**

**Scope:**

- `RequirementDataFieldsPane`
- Inline edit → PATCH candidate

**Done when:** Type A acceptance criteria pass. ✅

---

### A3-FE4 — Card rail simplification (frontend, 1 PR) — **Done (2026-07-01)**

**Scope:**

- Replace full rail checklists with summary card + CTA
- Mount handoff pane in workspace only
- Fix `#section-transfer-readiness` (or remove dead scroll)
- Deprecate `RecruitmentDossierChecklist` as primary (keep behind flag `VITE_FEATURE_DOSSIER_LEGACY` if needed)

**Done when:** Candidate card rail has ≤1 requirements block; workspace is primary entry. ✅

---

### A3-FE5 — Handoff readiness pane (frontend, 1 PR) — **Done (2026-07-01)**

**Scope:**

- `HandoffReadinessPane` with `TransferReadinessReport`
- Gate handoff modal on `transfer_allowed`

**Done when:** Type E criteria; handoff modal shows same blockers as workspace. ✅

---

### A3-B4 + FE6 — Operational requirements (Phase 2, after Slice 4) — **Done (2026-07-02)**

Activity-type requirements + continuity.

**Scope:**

- Catalog: `backend/app/requirement_rules/data/operational_requirements.v1.json` (`first_contact_completed`)
- Evaluation + lead continuity bridge in `operational_requirements_service.py`
- Workspace bundle includes `operational_requirements[]`; summary counts open ops rows
- API: `POST /candidates/{id}/requirements/{code}/complete-activity`
- FE: `RequirementActivityPane` + nav section in workspace
- Tests: `backend/tests/api/test_operational_requirement_activity_closure.py`

**Done when:** workspace shows activity requirement; complete-activity closes row; lead continuity auto-satisfies; FE records call. ✅

---

### A3-B5 — Operational requirements handoff gate parity — **Done (2026-07-02)**

**Scope:**

- Transfer policy blocks `transfer_allowed` / `handoff_create_allowed` when operational requirements are open
- `blocking_reasons[]` includes `operational_requirement_open` with `requirement_code`
- Test helper `close_driver_ce_requirements` satisfies `first_contact_completed` by default
- Tests: extended `test_requirements_workspace_gates.py`

**Done when:** open `first_contact_completed` blocks stage/handoff like document blockers; helpers green. ✅

---

### A3-C — Type C: Document + data (evidence + extraction) — **Done (2026-07-02)**

**Scope:**

- Checklist documents include `extracted_fields`, `required_extraction_fields`, `missing_extraction_fields`
- Multi-variant requirements expose full `alternatives_evaluated[]` (combined vs separate license paths)
- Missing extraction fields → `pending_verification` + `document_extraction_field_missing` blockers
- Approve API rejects evidence when required extraction fields are empty
- `legal_stay_confirmation` → `not_applicable` + `fulfilled=true` for EU citizenship
- FE: `RequirementDetailPane` — evidence paths, document data grid, approve disabled on extraction gaps

**Tests:**

- `backend/tests/api/test_requirements_workspace_combined_license.py`
- `backend/tests/api/test_legal_stay_not_applicable_eu.py`

**Done when:** workspace shows extraction side-by-side, both license paths, EU legal stay N/A, approve gated. ✅

---

### A3-QA — E2E — **Done (2026-07-01)**

**File:** `e2e/candidate-requirements-workspace.api.spec.ts`

**Scenario:**

1. Create candidate `driver_ce`
2. Open workspace → see open requirements
3. Fill phone → data requirement satisfied
4. Select evidence → link doc → approve
5. `transfer-readiness?target_stage=ready_for_handoff` → `transfer_allowed=true`
6. Create handoff → snapshot contains `requirement_fulfillments`

✅

## 7. Матрица «срез → типы требований»

| Срез | A Data | B Doc | C Doc+data | D Activity | E Handoff |
|------|--------|-------|------------|------------|-----------|
| S0 Catalog | seed | seed | seed | stub | — |
| B1 Bundle | read | read | read | — | read |
| FE1 Shell | list | list | list | — | summary |
| FE2 Detail | — | **done** | **done** | — | — |
| FE3 Data pane | **done** | — | — | — | — |
| FE4 Card | CTA | CTA | CTA | — | — |
| FE5 Handoff | gate | gate | gate | — | **done** |
| B4+FE6 | — | — | — | **done** | — |

---

## 8. Feature flags

| Flag | Default | Purpose |
|------|---------|---------|
| `VITE_FEATURE_REQUIREMENTS_WORKSPACE` | `false` → flip `true` after FE1 | Rollout workspace route |
| `VITE_FEATURE_DOSSIER_LEGACY` | `true` → `false` after FE4 | Hide `RecruitmentDossierChecklist` |

---

## 9. Anti-patterns (review checklist)

- [ ] Новый checklist в rail без workspace
- [ ] Статус fulfilled только на FE
- [ ] `RECRUITMENT_DOSSIER_BLOCKS` как source of truth
- [ ] Handoff enabled при `all_fulfilled=false`
- [ ] Три API call там, где есть workspace bundle
- [ ] Doc-type upload без привязки к `requirement_code`

---

## 10. Шаблон задачи агенту

```markdown
## Task
A3-{slice-id}: {title}

## Canon
- docs/specs/tasks/a3-requirements-workspace-backlog.md
- docs/specs/workflows/recruitment-operational-goals-and-order.md

## Scope
{files}

## Acceptance
{copy from §5 or §6}

## Tests
{listed tests}

## Out of scope
{explicit}
```

---

## 11. Связь с A4 (gates)

После A3-FE5 включить **A4**: stage PATCH и handoff create **только** при `workspace.summary.handoff_ready`. UI и API parity обязательны.

### A4 — Stage/handoff gates parity (UI ↔ API) — **Done (2026-07-01)**

**Scope:**

- Candidate card + workspace используют `workspace.summary.handoff_ready` для stage gate
- Handoff modal gated on `transfer_readiness.handoff_create_allowed` из того же workspace bundle
- Backend tests: `test_requirements_workspace_gates.py` (409 stage / 400 handoff / happy path)

**Done when:** API и UI читают один сигнал; дублирующий `GET /transfer-readiness` на card при workspace mode убран. ✅

---

### B1 — Handoff gates (structured 409 parity) — **Done (2026-07-02)**

**Scope:**

- `POST /handoffs/candidates/{id}` → **409** + `handoff_docs_incomplete` detail (как stage PATCH)
- `POST /handoffs/bulk` → `errors[].detail` с тем же контрактом
- FE: handoff modal + bulk handoff распознают structured gate

**Done when:** create/bulk handoff не обходят transfer policy; UI показывает тот же blocker, что workspace. ✅

---

### B2-G1 — HR handoff runtime pipeline binding — **Done (2026-07-02)**

**Scope:**

- `handoff_from_candidate` → `meta.employee_pipeline` via HR resolver (not recruitment)
- Entry stage `received_from_recruitment` when mapped; fallback `handoff_pending` + `source_handoff_fallback`
- Repeat handoff §5.3 no-downgrade policy

**Done when:** accept internal HR handoff leaves workforce row with `employee_pipeline.origin=recruitment_handoff`. ✅

---

### B2-G3 — Module gates on handoff create/accept + from-candidate — **Done (2026-07-02)**

**Scope:**

- `assert_hr_for_company_scope` / `assert_hr_for_candidate` (mirror recruitment helpers)
- `create_handoff` / `accept_handoff` / `handoff_from_candidate` → 403 when HR or recruitment off per §2.4
- `Company.enabled_modules` mapped on ORM model; derived `recruitment` in `company_module_access`
- Tests: `backend/tests/api/test_hr_handoff_module_gates_g3.py`

**Done when:** internal_hr blocked when HR off; recruitment handoff blocked when recruitment off; client_portal not blocked by HR-off alone. ✅

---

### B2-G2 — Delayed approve path pipeline binding — **Done (2026-07-02)**

**Scope:**

- `approve_employment_for_handoff` → `handoff_from_candidate` (same pipeline assignment as accept)
- Test assert `meta.employee_pipeline` after delayed approve: `test_hr_acceptance_stage_b_delayed_workforce.py`

**Done when:** delayed workforce path leaves employee with `employee_pipeline.origin=recruitment_handoff`. ✅

---

### B2-G4 — Idempotency + repeat handoff meta policy — **Done (2026-07-02)**

**Scope:**

- §5.3 no-downgrade via `merge_recruitment_handoff_pipeline_meta`
- API regression: `backend/tests/api/test_hr_handoff_idempotency_g4.py`
- Handoff test helper seeds dossier confirmations for transfer gate parity

**Done when:** repeat `from-candidate` returns same row; advanced pipeline stage preserved on repeat. ✅

---

### B3 — PR17 employee card enrichment — **Done (2026-07-02)**

**Scope:**

- Rich `candidate_snapshot` + `meta.recruitment_transfer` on handoff (17.1)
- Work eligibility + verified-field seed from candidate (17.1)
- Delayed path doc links + handoff→employee redirect (17.2)
- Case-first employee dossier + inbox routing (17.3)
- `CandidateOpenInHrLink` with delayed handoff fallback (17.4)
- Tests: `test_workforce_handoff_snapshot.py`, extended single-tenant + delayed + e2e

**Done when:** employee card shows recruitment context, linked docs, and wel profile after accept/approve. ✅

---

### B4 — Phase 1 manual stand sign-off — **Done (2026-07-02)**

**Scope:**

- Close `hr-handoff-runtime-p0.md` §7 gate checklist (G1–G4 + module gates)
- PR17 §7 acceptance criteria verified via automated regression
- Test helper fix: `setup_driver_ce_candidate` uses operating company (funnel alignment)
- E2E: strict PR17 workspace + full-flow assertions

**Regression suite (45 tests):** handoff gates, module gates G3, idempotency G4, single-tenant flow, delayed workforce, internal HR, pipeline H4, snapshot/wel, H6 HR-only.

**Done when:** Direction B Phase 1 gate closed; docs + tests green. ✅

---

### A1 — Slice 4 activity continuity (Guard 1) — **Done (2026-07-02)**

**Scope:**

- `lead_first_contact_continuity.py` — suppress UOS `Call candidate` when lead has prior touch
- Signals: intake resolution, lead stage, note, ActivityLog stage/operational touch, lead call activity
- Wired via `create_candidate_full(..., source_lead=lead)` on conversion paths
- Continuity marker: `lead_to_candidate.first_contact_suppressed` in ActivityLog
- Tests: `test_first_contact_continuity_guard.py` (14 cases incl. conversion integration + Guard 3 SLA dedup)

**Done when:** contacted/request_info/pooled lead → convert → no duplicate first-contact reminder; greenfield unchanged. ✅

---

### A2 — Lead workspace intake-first (Slice 6) — **Done (2026-07-02)**

**Scope:**

- Recruitment `LeadDetailPage`: sticky header + `RecruitmentAgencyIntakeDetailView` + `LeadIntakeDecisionRail` primary
- List inbox: `LeadIntakeWorkspacePanel` with decision rail; CRM chrome (playbook, stage, fit) under collapsed **More**
- Qualification summary collapsed; audit mode after convert
- Tests: `leadIntakeWorkspace.test.ts` utilities

**Done when:** intake decision is primary on recruitment lead detail + inbox; candidate-style ops demoted. ✅

---

### A5 — ADR-013 + public intake alignment — **Done (2026-07-02)**

**Scope:**

- ADR-013 **Accepted** — Decision (2) Lead stub / P5C Lead-first draft session
- Filled [ingestion-contract-public-intake.md](../workflows/ingestion-contract-public-intake.md)
- Audit §2.1 updated; CRM readonly rail covers `public_intake` + legacy `public-intake` client path
- FE: `leadPublicIntakeSourceKind`, notice variants (draft / submitted / client)

**Done when:** public candidate intake documented and CRM-aligned with Lead-first governance; no undocumented Candidate-first path for new traffic. ✅

---

### A6 — Application lifecycle I1 / C2b / C3 — **Done (2026-07-02)**

**Scope:**

- **C2b:** `external_id` column + `ensure_recruitment_application_for_external_intent`
- **I1:** `switch_recruitment_application_vacancy` + POST switch-vacancy API
- **C3:** PATCH application status API; `hired` does not create WorkforceEmployee
- Tests: `backend/tests/api/test_recruitment_application_a6.py`

**Done when:** second apply idempotent by external_id; vacancy switch creates new row; hired status has no implicit HR materialization. ✅

---

### C1 — Form Constructor → Lead-first (ADR-013) — **Done (2026-07-02)**

**Scope:**

- `POST /public/intake` with bound `TenantLeadForm` always uses `create_or_reuse_public_intake_lead_draft` (never legacy candidate reuse)
- Admin `submit_destination` documents Lead-first pipeline + ADR canon ref
- Deprecation notice on `create_public_intake_draft_via_service` (legacy in-flight only)
- Tests: `test_public_intake_c1.py`, updated `test_public_intake_matches_phone_digits_without_country_code`

**Done when:** Form Constructor smoke + public create return `lead_id`; no Candidate INSERT on create for bound forms. ✅

---

### C2 — Bridge removal: deprecate `CandidateProfile.config` — **Done (2026-07-02)**

**Scope:**

- `config_deprecation.py` — block `field_configs` / `document_configs` writes for Entity Profile–mapped codes; warn on unmapped legacy writes
- `POST/PATCH /candidate-profiles` returns `deprecation_warnings`; mapped profiles get HTTP 422 on semantic config edits
- `candidate_layout_bridge` marks overlay with `layout_bridge_source=candidate_profile_deprecated_overlay`
- Admin Candidate Profiles page deprecation banner
- Tests: `backend/tests/entity_profile/test_entity_profile_c2_bridge_deprecation.py`

**Done when:** mapped profiles resolve via registry facade; API rejects new semantic config on mapped codes; unmapped profiles still work with warnings. ✅

---

### C3 — Mapping / smoke для новых профилей (страна, роль) — **Done (2026-07-02)**

**Scope:**

- Entity Profile seeds: `recruitment.candidate.warehouse_worker` (role) + `recruitment.candidate.driver_ce_ua` (country/market variant)
- Document pack: `recruitment.warehouse_worker_documents` (identity + legal stay)
- Intake mapping validation rejects fields outside profile; P8 create + smoke-test → Lead draft for both profiles
- Tests: `backend/tests/entity_profile/test_entity_profile_c3.py`

**Done when:** admin entity-profile picker lists new profiles; form create + smoke pass; mapping rejects out-of-profile fields. ✅

---

### C4 — ADR-007 Forms platform publication bridge — **Done (2026-07-02)**

**Scope:**

- `backend/app/forms_platform/` — contract constants, submission handler registry, `TenantLeadForm` → ADR-007 publication bridge
- API: `GET /api/v1/platform/forms/handlers`, `GET /api/v1/platform/forms/publications/resolve`
- Admin intake form detail includes `forms_platform` block (publication contract + available handlers)
- Bridge storage backend `tenant_lead_form` (no FormTemplate DB migration in this slice)
- Tests: `backend/tests/forms_platform/test_forms_platform_c4.py`

**Done when:** handlers API lists `recruitment.lead_draft`; publication resolve by `form_id` / `public_slug` returns ADR-007 contract; intake form detail exposes `forms_platform`. ✅

---

*Обновлять этот backlog при закрытии срезов (менять Status среза на Done + дата).*
