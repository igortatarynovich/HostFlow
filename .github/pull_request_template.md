## Summary

<!-- Что меняется и зачем (1–3 предложения). -->

## Risk & security perimeter

Отметьте **все**, что применимо (даже если ответ «нет» — так меньше дрейфа при review).

| Вопрос | Yes / No / N/A |
|--------|----------------|
| **Tenant isolation affected?** (данные другого тенанта могут затронуться) | |
| **RLS affected?** (новые/изменённые таблицы, политики, `set_config`, Alembic) | |
| **RBAC affected?** (роли, guards, permissions, client/candidate scope) | |
| **Hidden fields reviewed?** (сериализация API, CLASS 2–3 не утекают в «узкие» роли) | |
| **Upload flow touched?** | |
| **Export flow touched?** | |
| **Public links / intake / magic links touched?** | |
| **Webhooks or inbound integrations touched?** | |
| **Handoff / cross-tenant visibility touched?** | |
| **Portals (candidate / client) touched?** | |
| **Automations with external HTTP / callbacks touched?** | |
| **Audit logging added or verified?** (особенно CLASS 3, export, superadmin) | |
| **Threat model updated?** (см. чекбокс ниже — обязателен при триггере CI) | |
| **Security tests added or updated?** (`backend/tests/security/` или связанные API-тесты) | |
| **Cross-tenant tests executed?** (локально или в CI; tenant A / tenant B) | |
| **AI / LLM / embeddings / retrieval / semantic search touched?** | |
| **Global search (non-tenant-scoped) touched?** | |

## High-risk surfaces — mini-review (mandatory when touched)

Если PR затрагивает **AI**, **search**, **exports**, **portals**, **automations**, **integrations**, **analytics** — заполните таблицу **Mini-review** в [`docs/security/security-review-checklist.md`](docs/security/security-review-checklist.md) (раздел *Mini-review: high-risk surfaces*).

Если PR добавляет **AI assistant**, **global search**, **embeddings**, **retrieval layer** или **semantic search** — обязательны критерии раздела **Search / AI feature entry (merge criterion)** в том же файле.

## Threat model gate (mandatory when CI says so)

Если workflow **Threat model / security docs** на этом PR **красный**, нужно одно из:

- [ ] Обновлён соответствующий файл в `docs/security/threat-models/` **или**
- [ ] Обновлён `docs/security/security-ssot.md` / `security-review-checklist.md` с явным обоснованием **или**
- [ ] Добавлен комментарий в PR: почему изменение **не** меняет attack surface (и CI должен быть зелёным после корректировки путей/исключений — только по согласованию)

Список триггеров: `.github/workflows/security-gates.yml` (job `threat-model-docs`).

## Checklists

- [ ] Пройден [`docs/security/security-review-checklist.md`](docs/security/security-review-checklist.md), если PR в security perimeter
- [ ] Документы/ADR: при смене контрактов — `docs/specs/**` и при необходимости `docs/devel/pr-checklist-adr014-document-access.md`
- [ ] `make lint` / `make test` (или эквивалент CI) зелёные
- [ ] **Foundation:** no new deprecated foundation tokens introduced (`npm run foundation:check` in `hostflow-frontend`). If using `foundation-allow:`, include a short reason (min 8 chars) on the same line or the line above.
- [ ] **Primitives (Badge + Chip):** new status labels use `StatusBadge` (semantic API); new filter/toggle/action chips use `Chip` with allowed `behavior`. See `docs/specs/frontend/PRIMITIVES_V1.md`.
- [ ] **Primitives (Select):** new selects follow `SELECT_V1` scenario tree — `Combobox` / `MultiCombobox` / native `<select className="input">`; no new combobox copies or `SelectAsync`. See `docs/specs/frontend/SELECT_V1.md`.
- [ ] **Primitives (Button):** new buttons use `Button` or `.btn-*` canon; `variant="icon"` requires `aria-label` when no visible text. See `docs/specs/frontend/BUTTON_V1.md`.
- [ ] **Primitives (Input):** new text fields use native `<input className="input">` / `<textarea className="textarea">`; no custom field chrome, no pass-through `Input.tsx`. See `docs/specs/frontend/INPUT_V1.md`.
- [ ] **TABLE_V1 / ListWorkspace:** new operational entity lists use the Core Platform Kit (`ListWorkspace` + `DataTable`) once that public API exists; no new hand-written operational `<table>`. Visual child remains `docs/specs/frontend/TABLE_V1.md`.
- [ ] **Kit Gate** ([`docs/specs/architecture/platform-extraction-phase.md`](docs/specs/architecture/platform-extraction-phase.md)): a new product screen does not ship if its list / workspace chrome / analytics / action bar / filters are missing from the kit. No local stand-in. No module-only KPI card or fourth workspace shell.

## Labels (рекомендуется)

Для навигации по объёму PR: добавьте вручную или через labeler — `security`, и при необходимости `security-p0`, `security-rbac`, `security-rls`, `security-upload`, `security-public-link` (см. [`docs/security/github-labels.md`](docs/security/github-labels.md)).

## Специализированный шаблон (ADR-014)

Только document access / resolver: шаблон **Document access (ADR-014)** — `.github/PULL_REQUEST_TEMPLATE/document_access_adr014.md` (через UI «Choose a template» при создании PR).
