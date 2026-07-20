# HostFlow Repository Guidelines  
_Живой инженерный канон и стандарты разработки проекта HostFlow_

Этот документ определяет структуру, стандарты и правила разработки проекта HostFlow. Он служит источником истины для всех модулей (backend, frontend, инфраструктура, AI-агенты) и регулярно обновляется по мере развития системы.

## Project Structure & Module Organization
The FastAPI backend lives in `backend/app` with API routes under `backend/app/api/v1`, SQLAlchemy models in `backend/app/models`, and service helpers in `backend/app/services`. Database migrations are tracked via Alembic: the Alembic configuration file `alembic.ini` is located in the project root, and migration scripts are stored in `backend/alembic/versions`. Reusable scripts for seeding and utilities are in `backend/app/db/seeds`. Automated tests target live endpoints and reside in `backend/tests`. The React client is in `hostflow-frontend/src`, organised by feature modules (for example `src/modules/candidates` and `src/modules/vacancies`). Shared documentation and architecture notes belong in `docs/`, security governance in `docs/security/` (см. `docs/security/README.md`, [`security-events-governance.md`](docs/security/security-events-governance.md)), documentation governance in `docs/governance/`, and incremental tooling lives under `scripts/` and the top-level `Makefile`.

### Alembic Layout & Safety Checklist
- **Single source of truth:** запускайте Alembic только из `/opt/HostFlow` (repo root) — здесь лежит `alembic.ini` и сюда смотрит `script_location`.
- **Versions folder:** все ревизии должны находиться в `/opt/HostFlow/backend/alembic/versions`. Не копируйте миграции в `/opt/backend` или другие каталоги: они не подцепятся.
- **В контейнере:** backend-сервис монтирует `./backend` в `/app`, поэтому изменения в `backend/alembic/versions` автоматически видны внутри контейнера по тому же пути. Проверка: `docker compose exec backend ls backend/alembic/versions`.
- **Запуск миграций:** используйте `docker compose exec backend alembic upgrade heads` (или конкретный revision) — так гарантируется, что применяется актуальный код контейнера.
- **Повторный прогон:** если ревизия упала, удалите только её запись из `alembic_version` и повторите `alembic upgrade <rev>`. Перенос файлов между директориями запрещён.

## Build, Test, and Development Commands
### Makefile Commands

- `make up` — run API (uvicorn --reload).
- `make install` — create `.venv` (or use existing), ensure pip, install `backend/requirements.txt` (PEP 668).
- `make test` — pytest with project `.venv` (`ARGS=...`); DB host `db` → `127.0.0.1` fallback is handled in tests.
- `make test-search` — shortcut for global search API tests only.
- `make upg` — Alembic upgrade head.
- `make ensure-automation-schema` — ensure `automation_rules` table exists (dev fallback).
- `make mig msg=...` — Alembic autogenerate revision.
- `make down` — Alembic downgrade -1.
- `make seed-demo` — seed demo data (5 companies, 5 vacancies, 25 candidates).
- `make env-print` — print effective DB URLs.
- `make curl-list` — GET `/api/v1/candidates` (needs `TOKEN`).
- `make curl-create` — POST `/api/v1/candidates` (needs `TOKEN`).
- `make get-token` — print JWT for `admin@hostflow.dev` / `admin`.
- `make check-meta-oauth-env` — verify `META_LEADS_*` + `FRONTEND_URL` for Facebook Login (no DB).
- `make check-spa-paths` — fail on stray `/app/...` URL literals in `backend/app`.
- `make codegen-crm-app-paths` — regenerate TS/Python from `shared/crm_app_paths.json`.
- `make check-codegen-crm-paths` — fail if generated files drift from manifest.
- `make paths-qa` — codegen + SPA literals + frontend route static checks (needs npm in `hostflow-frontend`).
- `make docs-lint` — documentation governance lint.
- `make docs-lint-strict` — same as `docs-lint` but ignores baseline (zero tolerance).
- `make docs-lint-baseline` — rewrite `scripts/docs/governance_baseline.txt` with current violations (use sparingly).
- `make repo-health` — Repository Health Gate (clean tree, FF integration, alembic head, import integrity, worktrees).
- `make check-ts-imports` — GIT-IMPORT-INTEGRITY only.

Для клиента: установите зависимости в `hostflow-frontend` и используйте `npm run dev` для локальной разработки, `npm run build` для сборки, и `npm run preview` для проверки production-версии.

## Coding Style & Naming Conventions
Python code uses 4-space indentation, type hints, and snake_case for modules, packages, and variables. Enforce formatting and linting with `ruff --fix` (Python), type checking via `mypy`, and import ordering via `isort --profile=black`; all эти инструменты запускаются автоматически через pre-commit hooks. Для фронтенда используется `eslint` (см. `hostflow-frontend/eslint.config.js`). React и TypeScript исходники используют функциональные компоненты, PascalCase для компонентов и camelCase для хуков и вспомогательных функций. Tailwind utility classes должны оставаться в `*.tsx` файлах для колокации стилей.

## Testing Guidelines
Pytest is configured in `backend/pytest.ini` with asyncio support. Name new test modules `test_<feature>.py`, mirror the API surface, and assert both status codes and payload shapes. Add integration tests whenever you expose a new route, and keep seed data scripts up to date so fixtures succeed locally and in CI.

`backend/tests/api/test_public_intake.py` и связанные интеграционные тесты нужно гонять только в окружении с доступной Postgres — в песочницах без реальной базы они падают еще на попытке коннекта.

## Commit & Pull Request Guidelines
Commit messages follow a short `scope: summary` convention (for example `API: mount stages under /api/v1` or `labs(docs-module): ruleset v1.1`). Group related changes into coherent commits, and reference tickets in the body when relevant. Pull requests should outline the change, list validation steps (such as `pytest` or `npm run build`), attach screenshots for UI updates, and link any blocking migrations or feature flags. Tag reviewers from the affected domain (backend, frontend, or tooling) to keep feedback focused.

### Pull Request Checklist
- [ ] Обновлены соответствующие файлы в `docs/specs/**` при изменении логики или моделей
- [ ] Добавлены/обновлены тесты
 - [ ] Проведён `make lint` и `make test`
 - [ ] Проверены миграции Alembic и сиды
 - [ ] Обновлены связанные спеки и README при необходимости
- [ ] Если PR в security perimeter (см. `docs/security/security-review-checklist.md`) — отмечены все пункты чеклиста в описании PR
- [ ] Если PR затрагивает модули / shared capabilities / integrations / settings / contracts — пройден [`docs/specs/architecture/architecture-review-checklist.md`](docs/specs/architecture/architecture-review-checklist.md) (**10 вопросов L0**; обязателен также перед новым ADR)
- [ ] Если PR меняет L0 (P-rules, Passport/Manifest **shape**, freeze docs) — есть **Architecture RFC** (`architecture-rfc` / `l0-change`) или `l0-errata` + аппрув Architecture canon owner — [`L0-platform-architecture.md`](docs/specs/architecture/L0-platform-architecture.md)
- [ ] Если PR трогает `*.md` — пройден `make docs-lint` и контрибьютор-чеклист (`docs/governance/documentation-rules.md` §9)
- [ ] Перед стартом Product PR — `make repo-health` зелёный (`docs/governance/repository-operational-canon.md`)
- [ ] PR не смешанный (один concern); base = `integration/release-product-a-b` для integration line

---

## Multi-tenancy & RLS

- Каждая запись в базе данных содержит поле `tenant_id`.
- Включён Row-Level Security (RLS) на уровне базы данных.
- Приложение устанавливает текущий tenant через `current_setting('app.tenant_id')` в сессии PostgreSQL.
- Все запросы и операции должны учитывать tenant isolation.

## Security operating model

- Канон: `docs/security/security-ssot.md` (классификация данных, handoff, superadmin, тесты, KPI, IR).
- **Security events (canonical):** новые producer-события — только `emit_security_event_v1` и согласованная таксономия; правила drift/process — `docs/security/security-events-governance.md`. Legacy `emit_security_event` — только migration path, не для новых типов событий.
- **PR template (весь репозиторий):** `.github/pull_request_template.md` — заполняется для каждого PR.
- **PR gate (чеклист):** для изменений в API, RLS, документах, экспорте, webhooks, публичных ссылках, порталах и handoff — пройти и приложить к описанию PR пункты из `docs/security/security-review-checklist.md`.
- **CI enforcement:** `.github/workflows/security-gates.yml` (pip-audit, bandit, npm audit + sensitive gate, dependency-review, Trivy, threat-model/docs gate, SQL f-string scan, **raw `emit_security_event(` gate**).
- **Авто-метки:** `.github/workflows/pull-request-labeler.yml` + `.github/labeler.yml` (метки создать один раз: `docs/security/github-labels.md`).
- Threat models по поверхностям: `docs/security/threat-models/`.

## Repository operational canon (mandatory)

Перед **любой** новой продуктовой работой прочитайте [`docs/governance/repository-operational-canon.md`](docs/governance/repository-operational-canon.md) и прогоните:

```bash
make repo-health
```

Кратко: единственный trusted base — `integration/release-product-a-b` (FF only); работа через worktree; один concern — один PR; `/tmp` и `recovery/*` не SoT; GIT-IMPORT-INTEGRITY + Repository Health обязательны. Нарушение = process fail.

## Documentation governance

Перед созданием или изменением любого `.md` файла прочитайте `docs/governance/` (читать все):

- **`docs/governance/hierarchy-of-truth.md`** — три уровня источников истины (L1 canon / L2 operating canon / L3 implementation context). При конфликте выигрывает более высокий уровень. L1 не может ссылаться на L3 как на «канон».
- **`docs/governance/documentation-rules.md`** — куда класть новый ADR / workflow / module spec / runbook, что запрещено (`*-draft.md`, `*-final-v2.md`, и т.д.), как архивировать с canon replacement, контрибьютор-checklist (§9).
- **`docs/governance/ownership.md`** — владельцы канона по слою (security / architecture / module / workflows / operational SSOT). Без явного owner-а новый канонический слой не создаётся.
- **`docs/governance/repository-operational-canon.md`** — операционный канон репозитория (worktree, gates, PR split, recovery).

**Жёсткие правила (выдержка из rules):**
- Новое architecture decision — только через ADR (`docs/specs/architecture/ADR-NNN-<slug>.md` + linkage). ADR **ссылается** на L0 (P-01…P-05 / INV / Catalog), **не** переписывает конституцию. Сначала checklist + Catalog.
- Platform architecture **L0 FROZEN · Phase 0 complete** — [`L0-platform-architecture.md`](docs/specs/architecture/L0-platform-architecture.md). Дальше **Phase 1** (platform capabilities). L0 changes only via Architecture RFC. Design path: Catalog → Passport → Manifest → code.
- Новый workflow — обязательная запись в `docs/specs/workflows/index.md`.
- Изменение поведения модуля — обновление `docs/<module>/module-scope.md` + `docs/specs/modules/<module>.md` в одном PR.
- Запрещено создавать спеки в корне репо (кроме `AGENTS.md`, `README.md` и т.п.) или в `docs/_drafts/**`.
- Любой архивированный документ должен иметь явный canon replacement в `archive/legacy/YYYY-MM-DD/README.md`.
- ADR с `Supersedes: ADR-NNN` обязан иметь backref `Status: Superseded by ADR-MMM` в `ADR-NNN`.

**Enforcement:**
- Локально: `make docs-lint` (или `make docs-lint-strict` без baseline). Запускать перед PR.
- CI: `.github/workflows/docs-gates.yml → docs-governance-gate` блокирует merge при нарушениях вне `scripts/docs/governance_baseline.txt`.
- Lint-script: `scripts/docs/check_doc_governance.py`.

**PR-checklist (для PR, который трогает `*.md`):** прочитан hierarchy-of-truth, файл в правильной канонической папке, имя не нарушает §2.1, есть минимум один inbound reference, новый workflow добавлен в `workflows/index.md`, новый ADR — в module-catalog/domain-map, `make docs-lint` зелёный.

## Notes for AI Agents (Codex/ChatGPT)

1. Перед выполнением изменений всегда формируйте план и список файлов для редактирования и ожидайте подтверждения.
2. Не выполняйте shell-команды, коммиты или push без явного разрешения.
3. При изменении схемы базы данных необходимо:
   - Создать миграцию через Alembic (см. Makefile).
   - Обновить сиды в `backend/app/db/seeds`, чтобы тестовые/локальные данные были актуальны.

## Living Spec Integration
HostFlow использует живую спецификацию в `docs/specs/` + canonical baseline (см. `docs/governance/hierarchy-of-truth.md`). Перед изменением логики, структуры моделей или API необходимо:
1. Определить уровень изменения по `hierarchy-of-truth.md` (L1: ADR / domain map / security canon; L2: module-scope / workflows / specs/architecture; L3: notes / research / runbooks).
2. Обновить документ соответствующего слоя:
   - L1: open ADR (см. `docs/governance/documentation-rules.md` §3) — без ADR изменения архитектуры запрещены.
   - L2: обновить `docs/<module>/module-scope.md` + `docs/specs/modules/<module>.md` в том же PR; новый workflow — добавить в `docs/specs/workflows/index.md`.
   - L3: обновить implementation-note и убедиться, что ссылка на L3 не используется как «источник истины».
3. После обновления — сгенерировать/обновить код и тесты, прогнать `make docs-lint` и `make test`.
4. При архивации устаревшего документа — `git mv` в `archive/legacy/YYYY-MM-DD/` + явный canon replacement в `archive/legacy/YYYY-MM-DD/README.md` (см. `documentation-rules.md` §6).

---

# HostFlow Architecture Enforcement Rules (Mandatory)

## Core Principle

System Layer stores shared language, contracts, canonical catalogs, schemas and cross-module boundaries.

Module Layer stores business behavior, workflows, decisions, scoring, approvals, checklists and runtime logic.

A module must never push its own business behavior into the system layer unless explicitly approved through architecture review.

## Rule 1. No New Local Reference Dictionaries

Creating new local dictionaries is prohibited unless explicitly approved.

This includes, but is not limited to:

- document type lists
- document category lists
- country lists
- citizenship lists
- permit lists
- visa lists
- status dictionaries
- field definition registries
- normalization tables

All shared reference data must come from the Platform Reference Layer.

Any new local reference dictionary is considered an architecture violation until proven otherwise.

## Rule 2. No Cross-Module Internal Access

Modules must not access internal implementation details of other modules.

Allowed:

- facade contracts
- delivery contracts
- API contracts
- event contracts
- typed DTO contracts

Prohibited:

- direct service imports from another module
- direct CRUD access from another module
- direct repository access from another module
- direct internal helper usage from another module

A module may communicate only through approved contracts.

## Rule 3. Ownership Card Required Before New Domain Creation

No new domain may be created without an ownership definition.

Required ownership card:

- Domain name
- Owner
- Source of truth
- Consumers
- Delivery contract
- Versioning strategy
- Override policy
- Enforcement requirements

Examples:

- Billing
- Fleet
- Payroll
- Housing
- Training
- Compliance

Creation of a domain without an ownership card is prohibited.

## Rule 4. Two-Module Promotion Rule

Business rules must remain inside their owning module.

A rule may be promoted to the System Layer only if:

- it is required by at least two independent modules

OR

- it is a mandatory platform contract

If neither condition is true, the rule remains module-owned.

Default decision:

KEEP INSIDE MODULE.

## Rule 5. Runtime Is Always Downstream

For every new capability the implementation order must be:

1. Ownership
2. Reference
3. Contract
4. Enforcement
5. Runtime

Never:

1. Runtime
2. Fix architecture later

Architecture must exist before runtime adoption.

## Rule 6. System Layer Cannot Contain Module Behavior

System Layer may contain:

- canonical catalogs
- shared schemas
- field definitions
- normalization rules
- compatibility contracts
- version metadata
- reference facades
- delivery contracts
- cross-module boundaries

System Layer may not contain:

- recruitment workflows
- HR workflows
- billing workflows
- candidate scoring
- approval decisions
- business eligibility decisions
- module checklists
- operational automation logic

These belong to modules.

## Rule 7. Every Boundary Requires Enforcement

Architecture is not considered implemented until enforcement exists.

Required enforcement may include:

- guard scans
- boundary tests
- import restrictions
- contract validation
- compatibility checks

A rule without enforcement is considered documentation only.

## Rule 8. Every STOP Condition Blocks Progress

Any unresolved STOP condition immediately blocks promotion to the next gate.

Work may continue only after:

- remediation
- documented exception
- formal PASS_WITH_CONSTRAINTS decision

Unresolved STOP conditions may never be silently bypassed.

## Rule 9. Formal Evidence Required For Promotion

A gate may only be promoted through a formal decision record.

Allowed outcomes:

- PASS
- PASS_WITH_CONSTRAINTS
- PASS_WITH_BASELINE_NOTE
- STOP

Every decision must include evidence.

No verbal or implicit promotion is allowed.

## Rule 10. Platform First, Modules Second

HostFlow architecture is built in the following order:

Platform Layer
→ Contracts
→ Enforcement
→ Runtime Modules

The platform exists to allow independent evolution of modules.

A module must never become the source of truth for platform concepts.
