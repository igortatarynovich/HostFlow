# Documentation Ownership

**Status:** canonical (governance layer)

За каждым каноническим слоем закреплён **владелец-канон** — лицо или команда, без чьего согласия слой нельзя менять. Без явного владельца документация снова деградирует.

В HostFlow владелец указан как **роль / команда**, не персональное имя — чтобы не зависеть от конкретного человека.

---

## Owners by canon layer

| Слой | Документы | Owner | Что делает owner |
|---|---|---|---|
| **Engineering canon** | `AGENTS.md`, [`repository-operational-canon.md`](repository-operational-canon.md) | Engineering lead | Контракт PR, security gate, RLS правило; worktree / trusted integration / health+import gates; AGENTS.md обновляется при изменении PR-контракта |
| **Architecture canon** | `docs/specs/architecture/L0-platform-architecture.md`, `architecture-invariants.md`, `platform-architecture-principles.md`, `platform-capability-catalog.md`, `capability-settings-manifest.md`, `module-catalog-and-routing-map.md`, `architecture-review-checklist.md`, `architecture-guide.md`, ADR-002…030 (L0 = ADR-025…030 / P-01…P-05) | Architecture canon owner | Держит L0 **FROZEN**; аппрувит Architecture RFC / l0-errata; защищает P-01…P-05 + INV-01…15 |
| **Security canon** | `docs/security/security-ssot.md`, `security-review-checklist.md`, `runtime-roadmap.md`, `threat-models/*.md` | Security owner | Аппрувит изменения в RLS / handoff / classification / IR / threat models; держит PR security gate |
| **Module canon (per module)** | `docs/<module>/module-scope.md` + `docs/specs/modules/<module>.md` | Module owner (recruitment / sales / hr / fleet / services / finance / forms / document-hub) | Аппрувит изменения scope модуля; следит, что module spec не противоречит ADR |
| **Module ownership boundaries** | `docs/modules/<module>/module_ownership_card.md` (+ contract map / dependency audit / test boundary) · [coverage record](../specs/gates/module-ownership-coverage.md) | Architecture canon owner (классификация домена) + Module owner (содержание карточки) | Rule 3: новый домен не создаётся без карточки. Coverage record фиксирует, у каких доменов карточки **нет**; MOC-1…MOC-3 обязательны до Release Readiness Gate (RR1). Enforcement отсутствует — см. §5 записи |
| **Workflow canon** | `docs/specs/workflows/*.md` + `workflows/index.md` | Workflow index maintainer (engineering lead) | Любой новый workflow регистрируется в `index.md` и линкуется из ADR / module spec / кода |
| **Operational SSOT** (**не** релизная власть) | `docs/SSOT.md`, `HOSTFLOW_AUDIT_AND_PLAN.md`, `operations-loop.md`, `manager-assignment.md`, `vacancy-statuses.md`, `plans-matrix.md`, `personas.md`, `operational-metrics.md`, `lead-types.md`, `tenant-types.md`, `own-company-model.md` | Operational lead | Source of truth для операционного backlog, KPI, плановой матрицы, ролей-операций. **Не** определяет scope v1, порядок слайсов и готовность к запуску — см. release authority в [`hierarchy-of-truth.md`](hierarchy-of-truth.md) |
| **DB canon** | `docs/specs/db/migrations_policy.md`, `doc_types_catalog.md`, schema_*.sql | DB / backend owner | Согласует миграции, держит migrations_policy актуальным |
| **Frontend canon** | `docs/specs/frontend/*.md`, ADR-010, ADR-011 | Frontend owner | UI standard, list shell, forms, tokens (`docs/pipedesign.md`) |
| **Platform canon** | `docs/specs/platform/observability.md`, `prometheus_integration.md`, `webhooks.md` | Platform owner | Observability, metrics, webhooks |
| **Integrations canon** | `docs/specs/integrations/*.md`, ADR-006, marketplace-integrations-data-model.md | Integrations owner | Marketplace, intake channels |
| **Journeys canon** | `docs/specs/journeys/*.md` | UX / product owner | UAT прогоны, persona journeys, release acceptance suite |
| **Gates canon** | `docs/specs/gates/*.md` (gate records, [Release Goal](../specs/gates/hostflow-v1-release-goal.md), [Release Readiness Gate](../specs/gates/release-readiness-gate.md), [Goal Completion Gate](../specs/gates/goal-completion-gate.md), [unowned work register](../specs/gates/v1-unowned-work-register.md), [module ownership coverage](../specs/gates/module-ownership-coverage.md)) | Engineering lead + Operational lead; Architecture canon owner аппрувит architecture-gates; Security owner co-signs security-perimeter gates | Держит формальные outcomes (PASS / PASS_WITH_CONSTRAINTS / STOP); запрещает promotion без evidence; ни один gate не объявляет release-ready кроме Release Readiness Gate |
| **Runbooks (operational procedures)** | `docs/runbooks/*.md` + [`docs/runbooks/README.md`](../runbooks/README.md) (индекс обязательного набора) | Operational lead (набор процедур) + Engineering lead (deploy / recovery) | Держит required set актуальным; runbook без записи об исполнении не считается выполненным; изменение обязательного набора = изменение scope блокера 6 ([Operate & Launch](../specs/tasks/operate-and-launch.md)) |
| **Tenant data lifecycle** | [`ADR-039`](../specs/architecture/ADR-039-tenant-data-lifecycle.md) + участники (provision / import / export / erase / retain) | Platform owner; Security owner co-signs erasure / export | Аппрувит контракт participant-ов; запрещает module-owned tenant export и subject erasure; следит, что soft delete не выдаётся за erasure |
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
| `platform-capability-catalog.md` ↔ `module-catalog-and-routing-map.md` §0.1 ↔ `module-scope.md` synchronization | Architecture canon owner |
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
- **2026-08-28** — добавлены слои Gates canon, Runbooks, Tenant data lifecycle и Module ownership boundaries; Operational SSOT явно лишён релизной власти (release authority — [`hierarchy-of-truth.md`](hierarchy-of-truth.md) L2).
