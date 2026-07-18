# Documentation Ownership

**Status:** canonical (governance layer)

За каждым каноническим слоем закреплён **владелец-канон** — лицо или команда, без чьего согласия слой нельзя менять. Без явного владельца документация снова деградирует.

В HostFlow владелец указан как **роль / команда**, не персональное имя — чтобы не зависеть от конкретного человека.

---

## Owners by canon layer

| Слой | Документы | Owner | Что делает owner |
|---|---|---|---|
| **Engineering canon** | `AGENTS.md` | Engineering lead | Контракт PR, security gate, RLS правило, AGENTS.md обновляется при изменении PR-контракта |
| **Architecture canon** | `docs/specs/architecture/hostflow-core-domain-map-v1.md`, `platform-architecture-principles.md`, `module-catalog-and-routing-map.md`, `architecture-review-checklist.md`, `architecture-guide.md`, ADR-002…027 (incl. P-01…P-03) | Architecture canon owner | Аппрувит ADR, держит domain map / capability catalog консистентным, защищает P-01/P-02/P-03 |
| **Security canon** | `docs/security/security-ssot.md`, `security-review-checklist.md`, `runtime-roadmap.md`, `threat-models/*.md` | Security owner | Аппрувит изменения в RLS / handoff / classification / IR / threat models; держит PR security gate |
| **Module canon (per module)** | `docs/<module>/module-scope.md` + `docs/specs/modules/<module>.md` | Module owner (recruitment / sales / hr / fleet / services / finance / forms / document-hub) | Аппрувит изменения scope модуля; следит, что module spec не противоречит ADR |
| **Workflow canon** | `docs/specs/workflows/*.md` + `workflows/index.md` | Workflow index maintainer (engineering lead) | Любой новый workflow регистрируется в `index.md` и линкуется из ADR / module spec / кода |
| **Operational SSOT** | `docs/SSOT.md`, `HOSTFLOW_AUDIT_AND_PLAN.md`, `operations-loop.md`, `manager-assignment.md`, `vacancy-statuses.md`, `plans-matrix.md`, `personas.md`, `operational-metrics.md`, `lead-types.md`, `tenant-types.md`, `own-company-model.md` | Operational lead | Source of truth для backlog, KPI, плановой матрицы, ролей-операций |
| **DB canon** | `docs/specs/db/migrations_policy.md`, `doc_types_catalog.md`, schema_*.sql | DB / backend owner | Согласует миграции, держит migrations_policy актуальным |
| **Frontend canon** | `docs/specs/frontend/*.md`, ADR-010, ADR-011 | Frontend owner | UI standard, list shell, forms, tokens (`docs/pipedesign.md`) |
| **Platform canon** | `docs/specs/platform/observability.md`, `prometheus_integration.md`, `webhooks.md` | Platform owner | Observability, metrics, webhooks |
| **Integrations canon** | `docs/specs/integrations/*.md`, ADR-006, marketplace-integrations-data-model.md | Integrations owner | Marketplace, intake channels |
| **Journeys canon** | `docs/specs/journeys/*.md` | UX / product owner | UAT прогоны, persona journeys |
| **Glossary** | `docs/specs/glossary.md` | Cross-team (engineering + product) | Единый словарь терминов |
| **Governance** | `docs/governance/*.md` | Engineering lead + architecture canon owner | Эти три файла; lint script |

---

## Cross-cutting обязанности

| Обязанность | Owner |
|---|---|
| Запуск `make docs-lint` локально | Все контрибьюторы перед PR |
| Содержимое `docs/governance/*.md` | Engineering lead + architecture canon owner |
| Содержимое `archive/legacy/YYYY-MM-DD/README.md` | Тот, кто делает archive (PR author) |
| Cross-ref check (любой move в archive должен иметь canon replacement) | PR reviewer + lint |
| `workflows/index.md` ↔ `docs/specs/workflows/*` synchronization | Workflow index maintainer |
| `module-catalog-and-routing-map.md` ↔ `module-scope.md` ↔ `modules/*.md` synchronization | Architecture canon owner |
| Stale link cleanup | Lint enforces; manual fix by PR author |
| Promotion L3 → L2 (когда implementation note становится canon) | Module owner или architecture canon owner (через ADR) |
| Demotion L2 → archive (когда заменяется новым canon) | Owner соответствующего слоя |

---

## Что делать при отсутствии явного owner

Если для области нет назначенного owner — **запрещено** добавлять туда новые документы до назначения owner. Создание owner-less слоёв — основная причина drift.

В переходный период (пока команда не закрепила всех owner-ов) дефолт = **engineering lead**.

---

## Конфликт между owner-ами

При расхождении (например, security canon хочет одно, а module owner — другое):

1. Open issue / discussion с пометкой `governance-conflict`.
2. Решение принимает **более высокий L** ([`hierarchy-of-truth.md`](hierarchy-of-truth.md)).
3. Если оба на одном уровне — Architecture canon owner + Engineering lead arbitrate.
4. Решение фиксируется как ADR (если это архитектурный конфликт) или как короткая запись в `archive/legacy/<DATE>/governance-decisions.md`.

---

## История

- **2026-05-12** — введено вместе с governance package. До назначения именованных owner-ов default owner = engineering lead.
