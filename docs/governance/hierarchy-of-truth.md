# Hierarchy of Truth

**Status:** canonical (governance layer)
**Owner:** governance + architecture canon owners (см. [`ownership.md`](ownership.md))

## Принцип

В HostFlow **не все документы равны**. При расхождении между двумя документами **выигрывает более высокий уровень**. Этот файл фиксирует уровни.

Любой автор / AI-агент **обязан**, прежде чем ссылаться на документ как на «источник истины», свериться с уровнем. Ссылка на L3 в качестве замены L1 — это нарушение, ловится `make docs-lint`.

---

## Level 0 — Platform Architecture Constitution (**FROZEN**)

Документы, которые **задают форму платформы capabilities** (P-rules, Passport/Manifest shape, lifecycle/licensing/deps models, review checklist).

| Документ | Чем владеет |
|---|---|
| `docs/specs/architecture/L0-platform-architecture.md` | Конституция L0; freeze / RFC rule; completeness |
| `docs/specs/architecture/ADR-025`…`ADR-030` | P-01…P-05 + L0 closure norms |
| `docs/specs/architecture/platform-capability-catalog.md` | Capability Passport template + index (заполнение строк = применение L0) |
| `docs/specs/architecture/capability-settings-manifest.md` | Settings Contract schema (P-05) |
| `docs/specs/architecture/architecture-review-checklist.md` | Обязательный gate перед ADR/PR |
| `docs/specs/architecture/architecture-invariants.md` | Аксиомы INV-01…15 (не ADR) |
| `docs/specs/architecture/architecture-guide.md` | Навигация по канону |
| `docs/specs/architecture/platform-architecture-principles.md` §0 | Сводка P-01…P-05 |

**Изменения L0:** только через **Architecture RFC** (`architecture-rfc` / `l0-change`) с аппрувом Architecture canon owner — см. L0 Freeze rule. Явные ошибки — `l0-errata`.

**Жёсткое правило:** обычные feature ADR (L1) **не** переписывают P-rules и шаблоны границ L0.

---

## Level 1 — Canon (constitutional / domain)

Документы, которые **определяют форму системы** на уровне домена и engineering. Менять через ADR-процесс (см. [`documentation-rules.md`](documentation-rules.md) § «Adding architecture decisions»), **не** ломая L0.

| Документ | Чем владеет |
|---|---|
| `AGENTS.md` (root) | Engineering canon, security operating model, PR gates |
| `docs/specs/architecture/hostflow-core-domain-map-v1.md` | Bounded contexts, ownership matrix, scopes (GLOBAL/TENANT/COMPANY/MODULE) |
| `docs/specs/architecture/platform-architecture-principles.md` (кроме §0 L0) | Modular multi-company SaaS принципы |
| `docs/specs/architecture/module-catalog-and-routing-map.md` | Каталог продуктовых модулей, ключи, маршруты |
| `docs/specs/architecture/ADR-002`…`ADR-024` + domain ADRs; `docs/hr/ADR-001` | Канонические architecture decisions (**не** P-01…P-05 / ADR-025…030 — те в L0) |
| `docs/security/security-ssot.md` | Security canon (классификация, RLS, handoff, IR) |
| `docs/security/security-review-checklist.md` | PR security gate (контракт) |
| `docs/security/threat-models/*.md` | Threat models по поверхностям |

**Жёсткое правило:** L1 документ **не может ссылаться на L3 как на источник истины**. Только наоборот.

**Изменения L1:** только через PR с ревью архитектурного канона + обновлением всех L2/L3, которые на этот L1 опираются.

---

## Level 2 — Operating canon

Документы, которые **специфицируют как L1 проявляется в конкретных подсистемах**. Источник истины для разработчика конкретного модуля / workflow.

| Слой L2 | Где живёт | Канон-владелец |
|---|---|---|
| **Module scopes** | `docs/<module>/module-scope.md` (document-hub, finance, fleet, forms, hr, recruitment, services) | Модульный owner |
| **Module specs** | `docs/specs/modules/<name>.md` | Модульный owner |
| **Workflows** | `docs/specs/workflows/*.md` (зарегистрированы в `workflows/index.md`) | Workflow owner + index maintainer |
| **Architecture supplementary** | `docs/specs/architecture/*.md` (recruitment-domain-model, handoff-contract, multi_tenant_model, rbac_matrix, object_storage, job_queue, applications-operating-model, и т.д.) | Architecture canon owner |
| **Operational SSOT** | `docs/SSOT.md`, `docs/HOSTFLOW_AUDIT_AND_PLAN.md`, `docs/specs/operations-loop.md`, `docs/specs/manager-assignment.md`, `docs/specs/vacancy-statuses.md`, `docs/specs/plans-matrix.md`, `docs/specs/personas.md`, `docs/specs/operational-metrics.md`, `docs/specs/lead-types.md`, `docs/specs/tenant-types.md`, `docs/specs/own-company-model.md` | Operational owner |
| **Phase / roadmap** | [`platform-completion-roadmap.md`](../specs/architecture/platform-completion-roadmap.md) (**horizon SoT** Phases A–G), [`hostflow-v1-release-goal.md`](../specs/gates/hostflow-v1-release-goal.md) (**v1 in-scope vs later**), [`platform-capability-maturity.md`](../specs/architecture/platform-capability-maturity.md) (maturity SoT), `docs/specs/tasks/sales-to-comms-sequential-queue.md` (near-term slices), `docs/specs/phase-8-roadmap.md`, `phases-2-8-engineering-closure.md`, `phase-1-3-…`, `phase-2-1-…`, `phase-3-cleanup-inventory.md`, `runbooks/phase-2-1-drop-runbook.md` | Engineering lead + Architecture canon owner |
| **Journeys** | `docs/specs/journeys/*.md` | UX / product owner |
| **DB / Frontend / Platform / Integrations** | `docs/specs/db/`, `docs/specs/frontend/`, `docs/specs/platform/`, `docs/specs/integrations/` | Соответствующая команда |
| **Glossary** | `docs/specs/glossary.md` | Cross-team |

**Правило:** L2 **должен** быть консистентен с L1. Расхождение — баг (ловится `make docs-lint`, секция «conflict with canon»).

**Изменения L2:** PR в нормальном порядке + linkage:
- Workflow: запись в `workflows/index.md` + reference в коде или из L1
- Module spec: reference из L1 (module-catalog или ADR) или из `module-scope.md`
- Architecture supplementary: reference из L1 (domain map / ADR / platform principles)

---

## Level 3 — Implementation context

Документы, которые **поддерживают конкретную реализацию**, могут устаревать быстрее, **не являются источником истины для архитектуры**.

| Слой L3 | Где живёт |
|---|---|
| **Implementation notes / tasks** | `docs/specs/tasks/*.md` |
| **Research drafts** | `docs/specs/workflows/*-research.md`, `docs/analysis/` |
| **Plans / migration plans** | `docs/specs/db/migrations_plan_*.md`, drafts in `docs/specs/architecture/phase-*-plan.md` (когда не L2-канон) |
| **Runbooks (operational)** | `docs/META_GRAPH_190_FIX.md`, `docs/VAPID_KEYS.md`, `docs/FRONTEND_DEPLOY.md`, `deploy/TROUBLESHOOTING.md` (после реструктуризации — `docs/runbooks/`) |
| **Seeds** | `docs/specs/seeds/*.md` |
| **i18n drafts** | `docs/specs/i18n/<step>-<scope>.md` |
| **PR checklists** | `docs/devel/*.md` |
| **Min specs / LLM context** | `docs/specs/min/*.min.md`, `docs/_llm/*` |
| **Living drafts** | `docs/_drafts/<author>/*.md` (вне canonical surface) |

**Правила:**
- L3 **может** ссылаться на L1/L2.
- L3 **не должен** быть единственной «обоснованной» причиной архитектурного решения. Если L3 определяет архитектуру — это сигнал создать L1 (ADR) или L2 (workflow / module-scope).
- L3 **может** устаревать; устаревший L3 → archive (см. [`documentation-rules.md`](documentation-rules.md) § «Archive»).

---

## Conflict resolution

При обнаружении противоречия:

| Случай | Что делать |
|---|---|
| L0 vs L1/L2/L3 | **L0 выигрывает**. Изменение L0 только через Architecture RFC / `l0-errata`. |
| L1 vs L2 | L1 выигрывает. L2 обновляется или архивируется. |
| L2 vs L2 (одного слоя) | Один из них объявляется canon, второй — `archive` или `MERGE_INTO_CANON` (см. governance commit pattern). |
| L1 vs L3 | L1 выигрывает. L3 обновляется или архивируется. |
| L2 vs L3 | L2 выигрывает. |
| Code vs Documentation | **Code wins** только если изменение в коде сделано в рамках утверждённого ADR / workflow / module-scope; иначе — bug (документация — контракт). |

---

## Lint-rules, опирающиеся на эту иерархию

`scripts/docs/check_doc_governance.py` использует эту иерархию:

- **forbidden-down-ref:** L1 не должен иметь ссылку «as source of truth» на L3 (паттерны: `см.` / `источник истины` / `канон`).
- **canon-replacement-required:** при move в `archive/` обязателен canon replacement из L1/L2.
- **workflow-without-linkage:** новый файл в `docs/specs/workflows/` без записи в `workflows/index.md` блокирует.

Полный список — в [`documentation-rules.md`](documentation-rules.md) § «Lint contract».
