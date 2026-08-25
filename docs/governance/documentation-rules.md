# Documentation Rules

**Status:** canonical (governance layer)
**Owners:** engineering lead + architecture canon owner (см. [`ownership.md`](ownership.md))
**Enforcement:** `make docs-lint` локально + CI job `docs-governance-gate` (см. `.github/workflows/security-gates.yml`)

> **Перед чтением:** иерархия слоёв — [`hierarchy-of-truth.md`](hierarchy-of-truth.md). Владельцы — [`ownership.md`](ownership.md). Этот файл = правила.

---

## §1 Где можно создавать новые `.md` файлы

| Тип документа | Канонический путь | Дополнительное требование |
|---|---|---|
| **Architecture decision (ADR)** | `docs/specs/architecture/ADR-NNN-<slug>.md` (или `docs/<module>/ADR-001-...md` для модуля HR — historical exception) | Sequential `NNN`. Reference из `module-catalog-and-routing-map.md` или `hostflow-core-domain-map-v1.md` |
| **Architecture supplementary** | `docs/specs/architecture/<slug>.md` | Reference из L1 (domain map / ADR / platform principles) |
| **Module scope** | `docs/<module>/module-scope.md` (один файл на модуль) | Reference из `module-catalog-and-routing-map.md` |
| **Module spec** | `docs/specs/modules/<module>.md` | Reference из module-scope или ADR |
| **Workflow** | `docs/specs/workflows/<slug>.md` | **Обязательная запись** в `docs/specs/workflows/index.md` |
| **Security canon** | `docs/security/<slug>.md` | Аппрув security owner |
| **Threat model** | `docs/security/threat-models/<surface>.md` | Reference из `security-ssot.md` или `security-review-checklist.md` |
| **DB canon** | `docs/specs/db/<slug>.md` | Reference из `migrations_policy.md` |
| **Frontend canon** | `docs/specs/frontend/<slug>.md` | Reference из ADR-010 / ADR-011 или from frontend code |
| **Platform canon** | `docs/specs/platform/<slug>.md` | Reference из ADR или platform principles |
| **Integrations canon** | `docs/specs/integrations/<slug>.md` | Reference из ADR-006 или marketplace data model |
| **Operational SSOT** | `docs/specs/<slug>.md` (root specs) | Reference из `SSOT.md` или `HOSTFLOW_AUDIT_AND_PLAN.md` |
| **Journey** | `docs/specs/journeys/<slug>.md` | Reference из roadmap или UAT plan |
| **Runbook** | `docs/runbooks/<slug>.md` (целевая структура) или `docs/<UPPERCASE_SLUG>.md` (legacy) | Reference из соответствующего L2 / ADR |
| **Implementation note / task** | `docs/specs/tasks/<slug>.md` | Reference из ADR / module-scope / commit |
| **Research draft** | `docs/specs/workflows/<slug>-research.md` или `docs/analysis/<slug>.md` | Помечен `**Status:** research draft` в шапке |
| **i18n drafts** | `docs/specs/i18n/<step>-<scope>.md` | n/a |
| **Personal draft (work-in-progress)** | `docs/_drafts/<author>/<slug>.md` (вне canonical surface) | Не должен попасть в L1/L2 cross-ref |
| **LLM-min spec / context** | `docs/specs/min/<slug>.min.md` или `docs/_llm/...` | Reference из ADR (для `.min.md`) или из AI tooling |
| **PR checklist / dev guide** | `docs/devel/<slug>.md` | n/a |

---

## §2 Что **запрещено** делать

### 2.1 Forbidden filename patterns

Запрещены имена, означающие drift или неуверенность в каноне:

- `*-draft.md`, `*-draft-v2.md`, `*-final.md`, `*-final-v2.md`, `*-old.md`, `*-new.md`, `*-copy.md`, `*-backup.md`, `*-tmp.md`, `*-temp.md`, `*-wip.md`
- `*-v[0-9]+-final.md`, `*-final-[0-9]+.md`
- `Untitled*.md`, `*-Untitled*.md`

Исключения:
- `*.min.md` (LLM-минимизированный спец-формат, разрешён)
- `*-research.md` (research drafts, разрешены при наличии «Status: research draft»)
- `phase-*.md` / `ADR-*.md` (используют numeric suffix, не drift)

### 2.2 Forbidden paths for canonical content

Канонические документы (L1/L2) **не могут** жить в:

- Корне репозитория, кроме `AGENTS.md`, `README.md`, `CONTRIBUTING.md` (если появятся)
- `docs/_drafts/**` (это L3-only)
- `archive/**` (это history-only)

### 2.3 Forbidden duplication

- Два файла на одну архитектурную тему = `MERGE_INTO_CANON` → один остаётся, второй идёт в `archive/`.
- Документ на ту же тему, что L1 ADR, обязан **ссылаться** на ADR, не пересказывать его.
- Workflow без записи в `workflows/index.md` — невалидный workflow.

### 2.4 Forbidden down-references

L1-документ **не может** ссылаться на L3 как «источник истины». Можно упоминать L3 как «implementation context» — но не «канон».

### 2.5 Forbidden direct architecture changes

- Менять архитектуру **без ADR** — запрещено. ADR-процесс (см. §3) — единственный путь.
- Менять security canon без ADR / документированного PR-ревью security owner — запрещено.

---

## §3 Как добавлять новые architecture decisions (ADR)

1. **Создать файл:** `docs/specs/architecture/ADR-NNN-<short-slug>.md` (либо `docs/<module>/ADR-NNN-...md` если ADR полностью внутри модуля).
2. **Сначала L0:** пройти [`architecture-review-checklist.md`](../specs/architecture/architecture-review-checklist.md); спор ownership/settings/adapter → [`L0-platform-architecture.md`](../specs/architecture/L0-platform-architecture.md) / Catalog. Найденный ответ L0 **не** пересматривается в ADR.
3. **Не дублировать L0:** ADR **ссылается** на P-01…P-05 / INV-… / Passport, а не переписывает конституцию. Расширение L0 «под задачу» запрещено (только Architecture RFC).
4. **Структура (минимум):**
   - `Status` (Proposed / Accepted / Superseded by ADR-MMM)
   - `Context`
   - `Decision` (с явными ссылками: «per P-01», «owner per Catalog…»)
   - `Consequences`
   - `Alternatives considered`
   - `Cross-references` (какие L1/L2 документы обновляются)
5. **Linkage:** добавить в `module-catalog-and-routing-map.md` и/или `hostflow-core-domain-map-v1.md` явную ссылку; при новой capability — Passport (+ Manifest) в Catalog.
6. **Если ADR заменяет другой ADR** — в новом ADR указать `Supersedes: ADR-MMM`, в старом `Status: Superseded by ADR-NNN` (старый **не** удаляется).
7. **PR security gate:** если ADR трогает security perimeter — заполнить `docs/security/security-review-checklist.md`.
8. **Новый модуль / capability** без Passport, Exposes, Data Ownership, Dependencies, License Class (и Manifest при наличии config) — **не accept**.

---

## §3.1 Platform phase briefs (Original Goal → Completion Proof)

Каждый **platform phase brief** в `docs/specs/tasks/` обязан:

1. Содержать маркер `**Phase class:** platform` в шапке.  
2. Содержать отдельный заголовок `## Original Goal → Completion Proof` (не внутри списка deliverables).  
3. Заполнить два поля:

   - `**Problem this phase must permanently remove:**` — какую проблему этап должен **навсегда** устранить для следующего consumer.  
   - `**Completion proof (named consumer):**` — каким **реальным** экраном/путём это доказано (или будет доказано); что этот consumer **не** имеет права форкать.

Это brief-time контроль. Close-out — [Goal Completion Gate](../specs/gates/goal-completion-gate.md) G1–G5 **против этого раздела**, не против последнего декомпозированного AC.

**Reject:** brief, который описывает только deliverables (слоты, виджеты, named CI) и не называет устраняемую проблему и proof-consumer.

**Не ретроактивно** для исторических D1–D9 / C1–C6 briefs. Обязательно для новых platform phase briefs, начиная с [Workspace Capability Platform Completion](../specs/tasks/workspace-capability-platform-completion.md).

Lint: `phase-brief-missing-goal-proof` (см. §7).

---

## §4 Как добавлять новый workflow

1. Создать файл `docs/specs/workflows/<slug>.md`.
2. Добавить строку в `docs/specs/workflows/index.md` (table format с колонками: путь, описание, ключевые сущности, что автоматизируется).
3. Linkage из L1: ADR / domain map / module-scope.
4. Если workflow заменяет существующий — старый идёт в `archive/legacy/YYYY-MM-DD/` с canon replacement (см. §6).

---

## §5 Как менять module behavior

1. Канон поведения модуля живёт в `docs/<module>/module-scope.md`.
2. Любое изменение scope модуля = update `module-scope.md` **и** соответствующего `docs/specs/modules/<module>.md` в одном PR.
3. Если изменение касается границы между модулями (например recruitment ↔ HR) — это **architecture decision** (см. §3, ADR-002 как пример).

---

## §6 Archive contract

Контракт archiving документа (отработан в commits `f1b986e` / `cb3e79a`):

1. Не используется `git rm` — всегда `git mv <file> archive/legacy/YYYY-MM-DD/<flat-name>` (history сохраняется).
2. **Канонический replacement обязателен** — в `archive/legacy/YYYY-MM-DD/README.md` рядом с записью архивированного файла должна быть ссылка на canon, который его заменяет (L1 или L2).
3. **Inbound link sweep** — все упоминания архивируемого файла в активных документах обновляются:
   - Либо переписываются на canon replacement
   - Либо помечены `**archived**: <link to archive>; canon: <link to canon>`
4. Папка `YYYY-MM-DD` создаётся одна на день; если нужны несколько — добавлять `archive/legacy/YYYY-MM-DD-<slug>/`.
5. Архивирование security-документов / production-conf-документов / migrations / референсных от кода — **запрещено** автоматическим путём. Только PR с явным апрувом security owner / DB owner.

---

## §7 Lint contract — что проверяет `make docs-lint`

`scripts/docs/check_doc_governance.py` запускает следующие проверки. Любая failed-проверка = exit code != 0 = блок merge.

| Проверка | Описание |
|---|---|
| `forbidden-filename` | §2.1 — `*-draft.md`, `*-final-v2.md`, `Untitled*.md`, и т.д. |
| `forbidden-path-canon` | §2.2 — каноническое содержимое в `docs/_drafts/**` или в корне репо |
| `workflow-without-linkage` | §4 — файл в `docs/specs/workflows/*.md`, не упомянутый в `index.md` |
| `archive-without-canon-replacement` | §6.2 — файл в `archive/legacy/<DATE>/` без записи в `archive/legacy/<DATE>/README.md` |
| `broken-md-link` | Любой ссылочный путь `[..](..)` или `[..](<..>)` в `docs/**` или `AGENTS.md`, который не существует на диске и не является http(s) |
| `orphan-canon-doc` | L1/L2 документ без единого inbound reference из L1/L2 / кода / `AGENTS.md` (warning, не fail-by-default; включается флагом) |
| `superseded-without-status` | ADR помечен `Supersedes: ADR-MMM`, но в `ADR-MMM` нет `Status: Superseded by` |
| `phase-brief-missing-goal-proof` | Task с `**Phase class:** platform` без `## Original Goal → Completion Proof` и двух обязательных полей (проблема навсегда + named consumer) |

Severity:
- `forbidden-filename`, `forbidden-path-canon`, `workflow-without-linkage`, `archive-without-canon-replacement`, `broken-md-link`, `superseded-without-status`, `phase-brief-missing-goal-proof` — **error** (fail).
- `orphan-canon-doc` — **warning** (по умолчанию; `--strict` поднимает до fail).

---

## §8 Что **не** проверяет lint (контракт владельца)

Lint не оценивает:

- Содержательную правильность ADR / spec.
- Стилистику.
- Соответствие документа реальному коду (это работа PR review).
- Содержательную достаточность Original Goal → Completion Proof (lint проверяет только наличие раздела и двух полей).
- Конфликты между двумя L2-документами с одинаковой важностью (это работа owner — см. [`ownership.md`](ownership.md) § «Конфликт между owner-ами»).

---

## §9 Контрибьютор checklist

Перед PR, который трогает `*.md`:

- [ ] Прочитал [`hierarchy-of-truth.md`](hierarchy-of-truth.md) — знаю, на каком уровне мой документ
- [ ] Файл лежит в правильной канонической папке (см. §1)
- [ ] Имя файла не нарушает §2.1
- [ ] У документа есть **минимум один inbound reference** (если L1/L2)
- [ ] Если это новый workflow — добавлена строка в `workflows/index.md`
- [ ] Если это новый ADR — добавлен в `module-catalog-and-routing-map.md` или `hostflow-core-domain-map-v1.md`
- [ ] Если архивируется старый документ — в `archive/legacy/YYYY-MM-DD/README.md` есть запись с canon replacement
- [ ] Если это новый **platform phase brief** — есть `**Phase class:** platform` и раздел `Original Goal → Completion Proof` (см. §3.1 / [goal-completion-gate.md](../specs/gates/goal-completion-gate.md))
- [ ] `make docs-lint` зелёный
- [ ] Если затронут security perimeter — пройден чеклист `docs/security/security-review-checklist.md`

---

## §10 История правил

| Дата | Изменение |
|---|---|
| 2026-08-20 | §3.1 — platform phase brief обязан иметь Original Goal → Completion Proof; lint `phase-brief-missing-goal-proof` |
| 2026-05-12 | Введены вместе с governance package по итогам canonicalization pass (commits `9370fc4`…`b143e51`, archive `f1b986e` / `cb3e79a`) |
