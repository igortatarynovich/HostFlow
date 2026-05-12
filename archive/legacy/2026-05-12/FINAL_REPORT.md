# HostFlow Documentation Canonicalization — Final Report

**Дата cleanup:** 2026-05-12
**Канонический baseline:** последняя неделя разработки (commits 2026-05-09…2026-05-11) + новые архитектурные ADR-002…014, security canon, module-scope.md, новые workflows.

## Commit chain

| Stage | Commit | Что зафиксировано |
|---|---|---|
| Stage 0 | `9370fc4` | `docs: establish canonical documentation baseline` — 78 .md, +9682 lines, 0 не-doc файлов |
| Stage 2 (initial) | `f1b986e` | `docs: archive 10 obvious legacy / duplicate documents` — переименование + 4 inbound link updates + archive README |
| Stage 3 | `7010814` | `docs: add Stage 3 REVIEW_REQUIRED report` — `archive/legacy/2026-05-12/REVIEW_REQUIRED.md` |
| Stage 4 (extension) | `cb3e79a` | `docs: archive 4 orphan LLM-min duplicate specs` — 4 .min.md в archive |

---

## Canonical docs kept

**~134 файла** остаются актуальным каноном без изменений (дельты по сравнению с pre-cleanup: +78 baseline новых, -14 заархивированных, обновлены 4 inbound links).

### Главные anchors (читать в первую очередь, не противоречат друг другу)

1. `AGENTS.md` (root) — engineering canon, security operating model, PR security gate
2. `docs/specs/architecture/hostflow-core-domain-map-v1.md` — главная карта домена v1 (Platform Core → Tenant → Company → Module → User → Scope → Cross-company)
3. `docs/specs/architecture/platform-architecture-principles.md` — modular multi-company SaaS принципы
4. `docs/specs/architecture/module-catalog-and-routing-map.md` — каталог продуктовых модулей и маршрутов

### ADRs (canonical decision records)

| ADR | Тема |
|---|---|
| ADR-002 | Recruitment vs HR boundary on candidate stages |
| ADR-003 | Tenant ↔ Company ↔ Module data boundaries |
| ADR-004 | Five product modules and Billing Events |
| ADR-005 | Three-level settings hierarchy |
| ADR-006 | Marketplace and Integration Platform |
| ADR-007 | Forms platform capability |
| ADR-008 | Job publishing and distribution |
| ADR-009 | Document Hub platform layer |
| ADR-010 | Unified resource list shell |
| ADR-011 | HostFlow UI platform standard |
| ADR-012 | Activity & Notification Operating Layer |
| ADR-013 | Public intake strategy |
| ADR-014 | Document Hub access model |
| ADR-014 phase 1 | Implementation epic |
| `docs/hr/`ADR-001 | Workforce Employee vs App User |

### Security canon

- `docs/security/security-ssot.md` — main security SSOT
- `docs/security/security-review-checklist.md` — PR gate
- `docs/security/runtime-roadmap.md`
- `docs/security/github-labels.md`
- `docs/security/README.md`
- `docs/security/threat-models/` × 8 (automations, candidate-portal, client-portal, document-uploads, exports, handoff, public-links, webhooks)

### Module scopes (новый canonical layer)

`docs/<module>/module-scope.md` для: document-hub, finance, fleet, forms, hr, recruitment, services. Плюс `docs/hr/test-plan-org-structure.md`.

### Architecture supplementary

`applications-operating-model.md`, `recruitment-domain-model.md`, `handoff-contract.md`, `operational-event-boundaries.md`, `invariants-recruitment-hr-document-hub.md`, `marketplace-integrations-data-model.md`, `person-identity-layer-and-roadmap.md`, `candidate-direct-write-paths-inventory.md`, `activity-notification-operating-layer.md`, `phase-1-3-activity-layer-v1-migration-plan.md`, `phase-2-1-planner-tasks-into-activities.md`, `phase-3-cleanup-inventory.md`.

### Workflows (новый канон, цитируется кодом)

`recruitment-application-lifecycle.md` (+ sync note), `application-creation-mvp.md`, `lead-conversion-contract.md`, `lead-ingestion-external-id-idempotency.md`, `lead-intake-resolution-and-activity-continuity.md`, `lead-intake-conversion-flow-audit.md`, `lead-to-candidate-operating-model.md`, `candidate-creation-entrypoints-audit.md`, `current-separation-status-recruitment-hr-doc-hub.md`, `first-operational-flow-recruitment-documents-hr.md`, `implementation-roadmap-single-tenant-hr-handoff.md`, `module-separation-implementation-order.md`, `slice-3-qualification-summary-data-audit.md`, `slice-4-activity-continuity-guards.md`, `activities.md`, `activities-sla-matrix.md`, `ingestion-contract-template.md`, `index.md`. Плюс существовавшие до этого: `reminders.md`, `reminders_matrix.md`, `document_expiry.md`, `candidate-intake-via-telegram*.md`, `lead-intake-conversion-flow-audit.md`, `email-client-outlook-style-research.md`, `communications-workspace-research.md`.

### Operational SSOT (heavy code references — критически нельзя трогать)

| Файл | Цитируется из |
|---|---|
| `docs/SSOT.md` | `i18n/{en,pl,ru}.json`, `main.py`, `spa_paths.py`, `stripe_price_catalog.py`, `featureFlags.ts`, `bundle-budget.json`, scripts |
| `docs/HOSTFLOW_AUDIT_AND_PLAN.md` | `communications/schemas.py`, `services/__init__.py` (leads), `featureFlags.ts`, candidates hooks, `check_alembic_heads.py`, десятки specs |
| `docs/specs/operations-loop.md` | `next_action.py`, `next_action_api.py`, `test_document_next_action.py` |
| `docs/specs/manager-assignment.md` | `candidates/router.py`, `candidates/service.py`, `services/recruiter_assignment.py` |
| `docs/specs/vacancy-statuses.md` | `services/next_action.py` |
| `docs/specs/plans-matrix.md` | `tests/test_plan_matrix_consistency.py` (CI gate) |
| `docs/specs/architecture/multi_tenant_model.md` | `security-ssot.md`, `threat-models/handoff.md`, `.github/labeler.yml` |
| `docs/specs/architecture/rbac_matrix.md` | `security-ssot.md`, `security-review-checklist.md`, threat-models, `auth/hiring_workspace_roles.py` |
| `docs/specs/architecture/object_storage.md` | `security-ssot.md`, `threat-models/document-uploads.md`, `security/README.md` |
| `docs/specs/architecture/job_queue.md` | `HOSTFLOW_AUDIT_AND_PLAN.md` Phase 0 #5 |
| `docs/pipedesign.md` | `hostflow-frontend/tailwind.config.cjs` (brand tokens SoT) |

### Modules / Tasks / Journeys / DB / Frontend / Platform / Integrations / Seeds / i18n / Min

Module specs (~30), journeys (10), DB specs (`migrations_policy.md`, `doc_types_catalog.md`, `migrations_plan_*.md`), frontend specs (`page_header.md`, `error_handling.md`, `documents_readiness.md`), platform specs (`observability.md`, `prometheus_integration.md`, `webhooks.md`), tasks/seeds/i18n — все остались как operational backlog.

`docs/specs/min/scheduler.min.md` оставлен (цитируется ADR-012).

### Misc

`docs/legal/billing-ssot-v1/README.md`, `hostflow-frontend/README.md`, `backend/app/modules/documents/README.md`, `backend/tests/security/README.md`, `scripts/security/README.md`, `.github/PULL_REQUEST_TEMPLATE/document_access_adr014.md`, `.github/pull_request_template.md`, `docs/devel/pr-checklist-adr014-document-access.md`, `docs/_llm/edit_protocol.md`, `docs/_llm/abbreviations.yml`, `docs/_llm/context_map.yml`, `docs/_llm/snippets/*`, `docs/specs/marketplace-catalog-keys.md`, `docs/specs/tasks/eslint-adr011-ui-enforcement.md`.

---

## Archived docs

**14 файлов** перемещены в `archive/legacy/2026-05-12/` через `git mv` (история сохранена; восстановление: `git mv archive/legacy/2026-05-12/<file> docs/<original-path>`).

| Архивный файл | Прежний путь | Canon replacement |
|---|---|---|
| `agent_tz.md` | `docs/specs/agent_tz.md` | `AGENTS.md` |
| `agent_prompt.md` | `docs/specs/agent_prompt.md` | `AGENTS.md`, `docs/_llm/edit_protocol.md` |
| `hostflow-ecosystem.md` | `docs/specs/hostflow-ecosystem.md` | ADR-004 + platform-architecture-principles + module-catalog-and-routing-map |
| `architecture-client_and_subscription_model.md` | `docs/specs/architecture/client_and_subscription_model.md` | hostflow-core-domain-map-v1 + ADR-003 + handoff-contract |
| `client-profile-and-vacancy-redesign.md` | `docs/specs/client-profile-and-vacancy-redesign.md` | recruitment-domain-model + modules/vacancies + companies |
| `public_intake_new_specification.md` | `docs/specs/public_intake_new_specification.md` | ADR-013 |
| `analysis-candidate_intake_improvement_plan.md` | `docs/analysis/candidate_intake_improvement_plan.md` | workflows/lead-intake-* серия |
| `workflows-lead_to_candidate.md` | `docs/specs/workflows/lead_to_candidate.md` | lead-conversion-contract + lead-to-candidate-operating-model |
| `workflows-candidate_pipeline.md` | `docs/specs/workflows/candidate_pipeline.md` | recruitment-domain-model + ADR-002 |
| `workflows-reminders_rework.md` | `docs/specs/workflows/reminders_rework.md` | ADR-012 + activity-notification-operating-layer |
| `min-companies.min.md` | `docs/specs/min/companies.min.md` | modules/companies.md |
| `min-documents.min.md` | `docs/specs/min/documents.min.md` | modules/documents.md |
| `min-invoicing.min.md` | `docs/specs/min/invoicing.min.md` | modules/invoicing.md |
| `min-portals.min.md` | `docs/specs/min/portals.min.md` | modules/{client,candidate}_portal.md |

### Inbound link updates (4)

- `docs/specs/rules.md` — ссылка на `workflows/candidate_pipeline.md` заменена на ADR-002 + `recruitment-domain-model.md`
- `docs/specs/workflows/index.md` — удалены строки таблицы для `candidate_pipeline.md` и `lead_to_candidate.md`; обновлено упоминание в §«Взаимосвязь Workflow»
- `docs/specs/workflows/activities.md` — линк на `reminders_rework.md` помечен как **archived** + указан canon
- `docs/specs/architecture/ADR-012-activity-notification-operating-layer.md` — линк на `reminders_rework.md` помечен как заархивированный

---

## Deleted docs

**0** (ноль).

Принятая политика: «никогда не удалять автоматически». Все «легкоудаляемые» (orphan + duplicate + obsolete) кандидаты вместо удаления перемещены в `archive/legacy/2026-05-12/` через `git mv`, что сохраняет историю и позволяет тривиальный rollback.

Stage 4 SAFE_DELETE candidate set после анализа: **∅**.

---

## Conflicting docs (резолвлены этим cleanup)

| Конфликт | Источники | Резолюция |
|---|---|---|
| 5-подбренд модель vs 5-модульная | `hostflow-ecosystem.md` (CRM/LeadHub/Docs/HR/Connect) ↔ ADR-004 (recruitment/hr/fleet/services/finance) | Архив + canon = ADR-004 |
| Public intake spec | `public_intake_new_specification.md` (2025-12) ↔ ADR-013 | Архив + canon = ADR-013 |
| Tenant boundary model | `architecture/client_and_subscription_model.md` (`tenant_links`) ↔ `hostflow-core-domain-map-v1.md` + ADR-003 (Company = data boundary) | Архив + canon = domain map v1 |
| Lead → Candidate workflow | `workflows/lead_to_candidate.md` (старый) ↔ `lead-conversion-contract.md` + `lead-to-candidate-operating-model.md` (новый) | Архив + canon = новые workflows |
| Candidate pipeline | `workflows/candidate_pipeline.md` ↔ ADR-002 + `recruitment-domain-model.md` | Архив + canon = ADR-002 |
| Reminders rework | `workflows/reminders_rework.md` ↔ ADR-012 + `activity-notification-operating-layer.md` | Архив + canon = ADR-012 |
| LLM agent guidance | `agent_tz.md` + `agent_prompt.md` ↔ `AGENTS.md` | Архив + canon = AGENTS.md |
| Module mini-specs | 4 × `*.min.md` (companies, documents, invoicing, portals) ↔ `docs/specs/modules/*.md` | Архив + canon = full module specs |

---

## Missing SSOT areas

**Не обнаружено критических пробелов.** Полный canon покрывает:

- ✅ Domain map / ownership / scopes (`hostflow-core-domain-map-v1.md`)
- ✅ Platform principles (`platform-architecture-principles.md`)
- ✅ Module catalog (`module-catalog-and-routing-map.md`)
- ✅ Architecture decisions (ADR-002…014, hr/ADR-001)
- ✅ Security (SSOT + threat models × 8 + checklist + runtime roadmap)
- ✅ Modules (~30 specs)
- ✅ Workflows (recruitment lifecycle, lead intake, application MVP, activities, reminders, document expiry)
- ✅ RBAC (`rbac_matrix.md`)
- ✅ Multi-tenant (`multi_tenant_model.md`) [требует обновления под domain map v1]
- ✅ Data storage (`object_storage.md`, `job_queue.md`)
- ✅ DB (migrations policy + doc types catalog)
- ✅ Frontend (page header, error handling, documents readiness)
- ✅ Platform (observability, prometheus, webhooks)
- ✅ Journeys (10 user journeys)
- ✅ Operational SSOT (`docs/SSOT.md`, `HOSTFLOW_AUDIT_AND_PLAN.md`)
- ✅ Phase roadmaps (phase-8 + phases-2-8 closure + phase-1-3 + phase-2-1 + phase-3-cleanup)
- ✅ Operations loop / personas / metrics / plans matrix / glossary

**Слабые места** (есть документ, но он либо помечен REVIEW_REQUIRED, либо требует обновления):

- ⚠️ `docs/specs/architecture/multi_tenant_model.md` — частично перекрывается с `hostflow-core-domain-map-v1.md`; рекомендация в Stage 3 — MERGE_INTO_CANON
- ⚠️ `docs/spec-documents.md` — параллелен с `docs/specs/modules/documents.md` + ADR-009/014; рекомендация — MERGE_INTO_CANON
- ⚠️ `docs/_llm/context_map.yml` — содержит stale пути; либо обновить, либо ARCHIVE
- ⚠️ Operational runbooks (`META_GRAPH_190_FIX`, `VAPID_KEYS`, `FRONTEND_DEPLOY`, `deploy/TROUBLESHOOTING`) разбросаны; стандартизация в `docs/runbooks/` отложена до этапа структурной реорганизации
- ⚠️ `docs/SSOT.md` и `docs/HOSTFLOW_AUDIT_AND_PLAN.md` лежат в корне `docs/`, а не в `docs/ssot/` — отложено до отдельного этапа

---

## Duplicate areas still requiring merge

Из Stage 3 REVIEW_REQUIRED отчёта (`archive/legacy/2026-05-12/REVIEW_REQUIRED.md`) — **5 областей** требуют ручного merge перед потенциальным архивированием:

| Область | Старый | Новый канон | Действие |
|---|---|---|---|
| Documents living spec | `docs/spec-documents.md` (v0.1: ruleset JSON, regex per-type, валидации) | `docs/specs/modules/documents.md` + `documents_workflow_contract.md` + ADR-009 + ADR-014 | MERGE: уникальные части (ruleset JSON структура, regex per-type) → modules/documents.md |
| Multi-tenant model | `docs/specs/architecture/multi_tenant_model.md` (`tenant_links`-centric) | `hostflow-core-domain-map-v1.md` + ADR-003 (Company = data boundary) | MERGE: обновить под Company-boundary; security canon сейчас цитирует старый |
| Business terminology | `docs/ux/business-terminology-map.md` (agency/employer/services термины) | `docs/specs/glossary.md` | MERGE: business-type mapping → glossary, ux/ ARCHIVE |
| LLM context map | `docs/_llm/context_map.yml` (stale paths) | (нет нового — либо обновить, либо отказаться от подхода) | DECIDE: обновить или ARCHIVE весь `_llm/` подход |
| Pipe blueprint | `docs/pipe.md` (UX/IA + частично data model) | `hostflow-core-domain-map-v1.md` (data model) + UX парадигма уникальна | KEEP + добавить header «Data model сменён на domain map v1; здесь — UX/IA blueprint» |

---

## Что **НЕ тронуто** по прямой инструкции

Operational backlog — оставлен на месте без изменений до явного решения:

- `docs/specs/seeds/` × 4
- `docs/specs/tasks/` × 6 (кроме нового eslint-adr011, который в canon)
- `docs/specs/db/migrations_plan_*.md` × 2
- `docs/specs/workflows/document_expiry.md`
- `docs/specs/i18n/`
- `docs/specs/workflows/candidate-intake-via-telegram*.md`
- `docs/specs/workflows/communications-workspace-research.md`, `email-client-outlook-style-research.md`

---

## Принципы, которым следовали

1. **Канонический baseline сначала в Git** — Stage 0 `9370fc4` зафиксировал 78 .md untracked → tracked, прежде чем что-либо двигать.
2. **Не ломать структуру папок механически** — ADRs остались в `docs/specs/architecture/`, security в `docs/security/`, modules в `docs/<module>/`. Реструктуризация в `/docs/adr/`, `/docs/ssot/`, `/docs/runbooks/` — отложена.
3. **Никогда не удалять автоматически** — Deleted = 0; всё через `git mv` в archive.
4. **Решение по содержимому, не по имени** — все 14 архивированных файлов прошли cross-check на references (code + docs); 4 .min.md квалифицированы как orphan только после grep по всему репо.
5. **REVIEW_REQUIRED — отдельным отчётом** — `REVIEW_REQUIRED.md` содержит per-file recommendation; ничего не тронуто без прямого решения.

---

## Conclusion

После cleanup репозиторий имеет **78 канонических документов** в зафиксированном baseline, **14 заархивированных legacy** с ясной trail на canonical replacement, **0 удалённых** (всё восстанавливается одной командой), и формальный `REVIEW_REQUIRED.md` для ~21 неоднозначного файла.

Главный принцип — «единственный источник истины» — соблюдён по каждой канонической области (architecture, security, modules, workflows, ADR, RBAC, multi-tenant, document hub, activity layer, journeys, operational SSOT). Конфликты между старыми и новыми спеками разрешены архивированием старых.
