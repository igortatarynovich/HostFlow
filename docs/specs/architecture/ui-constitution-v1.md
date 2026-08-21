# Product Surface Contract v1

**Former title:** UI Constitution v1  
**Status:** canonical (L1 — **domain** product surface).  
**Owner:** Product + Platform UX + Architecture.

**Platform canon (how UI is built):** [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md) (tokens / a11y) + [`ADR-043-ui-component-composition-canon.md`](ADR-043-ui-component-composition-canon.md) (React kit composition) + [`ADR-044-list-workspace-data-presentation-canon.md`](ADR-044-list-workspace-data-presentation-canon.md) (ListWorkspace) + [`ADR-046-analytics-visualization-canon.md`](ADR-046-analytics-visualization-canon.md) (analytics + reporting language).  
**Interaction Rules:** [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md)  
**Layer spec:** [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md)  
**Entity deep work:** [`ADR-010-unified-resource-list-shell.md`](ADR-010-unified-resource-list-shell.md)

This document covers **what** the user works on (objects, ownership, handoffs).  
**HostFlow Platform Canon** covers **how** every surface looks, behaves, and is composed.

**Parent:** [`applications-operating-model.md`](applications-operating-model.md)  
**Hierarchy:** [`hierarchy-of-truth.md`](../../governance/hierarchy-of-truth.md)

**Build roadmap:** [`ADR-010-unified-resource-list-shell.md`](ADR-010-unified-resource-list-shell.md)

> **There are no screens. There are compositions of primitives.** See HostFlow Platform Canon §4.

> **Workspace is not the canon. Workspace is a composition of canonical components.**

---

## §0. First principle

> **The user thinks in screens, not database tables.**
> If there is a separate nav item, list, and card — it is a separate product object.
> Backend storage ≠ product object.

> **Lead is internal transport infrastructure. UI never knows Lead exists.**
> Like Kafka, Redis, or OAuth tokens — Lead is not a CRM section.

---

## §1. Product objects (what exists in UI)

| Module | Product name (RU) | Product name (EN) | After conversion |
|--------|-------------------|-------------------|------------------|
| Recruitment | **Отклик** | Application | **Кандидат** → Employee |
| Sales | **Обращение** | Inquiry | **Клиент** (ClientAccount) → Заказ |
| Fleet (future) | **Заявка** | Request | **ТС** → Ремонт |
| HR (future) | **Запрос** | Request | **Сотрудник** → Решение |
| Marketing | — | — | Intake only; no user-facing object |

**Forbidden in user-facing UI:** «Лид», Lead, `/app/leads` in primary navigation, lead terminology in i18n for operational surfaces, `Lead` type imports in frontend module code.

**Intake** (routing, dedup, Meta errors, distribution) — backend/internal. Diagnostics live under **Integrations / Monitoring**, not operational CRM.

---

## §2. Ownership matrix

Each product object has **exactly one primary workspace** per lifecycle phase. After handoff, the object **leaves** the previous workspace.

| Object | Owner module | Primary workspace | Type | Lifecycle end |
|--------|-------------|-------------------|------|---------------|
| Отклик | Recruitment | `/app/recruitment/inbox` | Application | → Candidate or rejected |
| Обращение | Sales | `/app/sales` | Application | → Client or closed |
| Кандидат | Recruitment | `/app/candidates/:id` | Entity | → Employee handoff |
| Подбор | Recruitment | `/app/recruitment/searches/:id` | Process | positions filled |
| Клиент | Services (ClientAccount) | `/app/clients/:id` | Entity | active client relationship |
| Юрлицо (party) | Platform / Companies | section в Client workspace | Entity facet | billing / contract party |
| Заказ | Services | `/app/service-orders/:id` | Process | completed |

**Violation:** the same inbound signal visible on Отклики, Лиды, Search Home, and Candidate list simultaneously.

**Rule:** new unprocessed applications live **only** in Application Workspace until conversion. Process Workspace (Search Home) shows **candidates in search context**, progress, sources, stats — not a competing inbox.

---

## §3. Four allowed screen types

Creating a page outside these types is **forbidden** without L1 amendment.

### 3.1 Collection Workspace

List of homogeneous objects. Filters, bulk actions, export.

Examples: Кандидаты, Клиенты, Подборы (list), Заказы, Документы.

Standard: ADR-010 Resource List Shell. Runtime orchestration: [`ADR-044`](ADR-044-list-workspace-data-presentation-canon.md) `ListWorkspace` (kit-layer id `collection_orchestration`). `DataTable` / `TABLE_V1` is a representation, not the collection screen.

### 3.2 Application Workspace

Work with a **new inbound signal** before conversion.

**Reference implementation:** Sales (`/app/sales`) — not as final pixel-perfect UI, but as **structural model:**

1. Hero CTA — «что делать дальше» + start work session  
2. Status tab buckets with counts  
3. Application table / compact list (identical base columns)  
4. Split-view detail card (same 7 sections)  
5. Module Action Panel plugin  
6. Outcome → handoff to Entity Workspace  

Recruitment Inbox = **configuration** of `ApplicationWorkspace`, not a separate screen type.

### 3.3 Entity Workspace

Work with a converted object. Standard: ADR-017 Workspace Layer.

Examples: Candidate, Client, Employee, Vehicle, Company, Order (as entity).

### 3.4 Process Workspace

Work toward a **goal** spanning multiple objects.

Examples: Search (Подбор), Service Order flow, Campaign.

Search Home = Process Workspace. **Not** a second Application inbox.

### 3.5 Gate question

For any new screen:

> Is this Collection, Application, Entity, or Process?

If **none** — the screen is designed wrong. Use a plugin in an existing workspace type.

---

## §4. Application Workspace — canonical structure

### 4.1 One reference pattern

**There is exactly one reference pattern for Application Workspace: Sales.**

Search Home, Recruitment Inbox, Fleet Requests, HR Requests — **configurations of the same engine**, not independent UX products.

### 4.2 Application table — identical base

**Required columns (every module):**

| Column | Field |
|--------|-------|
| Контакт | name, phone, email |
| Источник | source, campaign |
| Дата | created_at |
| Статус | new / in_progress / waiting / completed / rejected |
| Ответственный | assignee |
| Следующее действие | next_action |
| Последняя активность | last_activity_at |
| Приоритет | priority |
| Теги | tags |

**Module extensions (plugin columns only):**

| Recruitment | Sales |
|-------------|-------|
| Подбор / Вакансия | Услуга |
| Fit score | Потенциальная сумма |

One component: `ApplicationTable` + `columnExtensions[]`.

### 4.3 Application card — identical structure

Seven fixed sections (order mandatory):

1. **Contact** — phone, email, WhatsApp, messenger quick actions  
2. **Next Action** — dominant block: what to do **now**  
3. **Timeline** — all events  
4. **Notes** — comments  
5. **Attachments** — files  
6. **Activity** — calls, email, WhatsApp  
7. **Outcome** — result link (Entity) or rejection reason  

Below sections: **Action Panel** (module plugin — only place modules differ).

### 4.4 Unified UI statuses

| UI status | Meaning |
|-----------|---------|
| **Новое** | Not yet touched |
| **В работе** | Actively processing |
| **Ожидает** | Waiting for response / documents |
| **Завершено** | Converted to Entity |
| **Отклонено** | Rejected / lost / spam |

Backend fields may differ per module; **one UI adapter** maps to these five buckets.

### 4.5 Work session

One-by-one queue over open applications. Shared engine; module config supplies filter (e.g. «new only») and return path.

---

## §5. Platform language

Every module follows the same chain:

```text
Источник  →  Отклик/Обращение  →  Работа  →  Результат
```

Only the **outcome entity** changes:

```text
Recruitment:  Source → Отклик → Кандидат → Employee
Sales:        Source → Обращение → Клиент (ClientAccount) → Заказ
Fleet:        Source → Заявка → ТС → Ремонт
HR:           Source → Запрос → Сотрудник → Решение
```

Modules are **configurations of one engine**, not separate UX products.

---

## §6. API surface — UI facades only

Frontend modules call **Application facades**, never Lead API:

| Module | List | Detail | Mutations |
|--------|------|--------|-----------|
| Sales | `GET /api/v1/sales/inquiries` | `GET …/inquiries/{id}` | stage, convert-client |
| Recruitment | `GET /api/v1/recruitment/applications` | `GET …/applications/{id}` | intake-decision, stage |

Backend may read/write `Lead` table internally. **UI must not import Lead types or call `/api/v1/leads` from module code.**

Admin/integration diagnostics: separate Monitoring surfaces (not primary CRM nav).

---

## §7. Forbidden (hard rules)

| Rule | Enforcement |
|------|-------------|
| No «Лиды» in primary sidebar | nav registry + `APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS` |
| No `/app/leads/:id` as recruitment/sales work target | routes redirect to Application Workspace |
| No `Lead` type in `hostflow-frontend/src/pages/*` module pages | lint / PR review |
| No second reference pattern for Application UX | PR gate: must use `ApplicationWorkspace` |
| No arbitrary page types | PR must declare §3 workspace type |
| No duplicate object on multiple primary screens post-handoff | ownership matrix review |

---

## §8. Current violations (migration register)

| Surface | Status | Replacement |
|---------|--------|-------------|
| `/app/leads` (LeadsPage) | **REMOVE** from product | Application Workspace + Integrations admin |
| `/app/leads/:id` (LeadDetailPage) | **REMOVE** from primary flow | Application Workspace split-view |
| Recruitment Inbox → `/app/leads/:id` | **DONE** (2026-07-09) | `/app/recruitment/inbox/:applicationId` |
| Search Home as competing inbox | **DONE** (2026-07-09) | Process Workspace; pending apps → Отклики CTA |
| Three list implementations | **IN PROGRESS** | `ApplicationWorkspace` engine |
| Four detail cards | **IN PROGRESS** | `ApplicationDetailCard` + Action Panel plugins |
| Frontend `listLeads()` in sales/recruitment pages | **DONE** (2026-07-09) | Application facade API |
| Mutations via `/leads` in module pages | **DONE** (2026-07-09) | `/sales/inquiries`, `/recruitment/applications` facades |
| Dual reference (Search Home + Sales) | **RESOLVED** | Sales Application Workspace only |

Track progress in [`hostflow-core-domain-map-v1.md`](hostflow-core-domain-map-v1.md).

---

## §9. Visual reference (mockup v1)

Application Workspace layout (Sales = canonical):

```text
┌──────────┬─────────────────────┬──────────────────────────────┐
│ Sidebar  │  List + tabs        │  Detail card                 │
│ (shell)  │  Hero CTA           │  Contact                     │
│          │  Status filters     │  Next Action (dominant)      │
│          │  Application rows   │  Timeline / Notes / …        │
│          │                     │  Action Panel (module)       │
│          │                     │  Outcome footer              │
└──────────┴─────────────────────┴──────────────────────────────┘
```

Brand: dark forest green primary CTA; status badges mint / amber / blue; rounded cards; split-view when item selected.

Recruitment Inbox uses **identical layout**; Action Panel and extension columns differ.

---

## §10. Development order (primitives first, workspaces composed)

**Nearest goal:** Phase 1 DoD (DataTable + Selection + Detail Rail) → **Phase 2 Universal Entity Workspace** → Phase 3 Application Workspace.

| Phase | Deliverable |
|-------|-------------|
| **1 ← now** | Universal Data Table + Selection Model + Detail Rail |
| **2 ← next** | Universal Entity Workspace + Context Rail |
| 2b | Embedded primitives: Documents, Timeline, Notes, Contacts, Relations |
| **3** | Universal Application Workspace (composes Phase 2) |
| 4–5 | Process + Collection completion |

Workspace types (§3) describe **composition targets** (Level 4), not build priority.  
Full platform spec: [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md). Build phases: [`ADR-010-unified-resource-list-shell.md`](ADR-010-unified-resource-list-shell.md).

**Frozen until Phase 2:** candidate entity page layout refactor; Application Workspace rewrite; Search Home.

---

## §11. Decision filter for new work

Before any UI task:

1. Which **primitive or phase** (§10) does this extend?  
2. Is that phase **active**? If not — bugfix only on frozen surfaces.  
3. Which workspace **type** (§3) will eventually compose this primitive?  
4. Does it **fork** a table/card/timeline in a module? → reject; extend platform.  
5. Does frontend avoid Lead (§6–§7)?  

If any answer fails — stop and fix design before coding.

---

## §12. Related documents

| Document | Role |
|----------|------|
| [`applications-operating-model.md`](applications-operating-model.md) | L1 — operational work model |
| [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md) | List → Workspace → Capabilities |
| [`ADR-010`](ADR-010-unified-resource-list-shell.md) | Collection Workspace |
| [`ADR-010-unified-resource-list-shell.md`](ADR-010-unified-resource-list-shell.md) | Entity Workspace |
| Product contract | See this document (UI Constitution) |
| [`hostflow-core-domain-map-v1.md`](hostflow-core-domain-map-v1.md) | Migration progress |
| [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md) | **UI Platform Standard** — supreme; five layers |
| [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md) | Interaction Rules — click, keyboard, selection, … |
| [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md) | Primitives, Compositions, Workspaces |
| [`ADR-010-unified-resource-list-shell.md`](ADR-010-unified-resource-list-shell.md) | Universal Entity Workspace |
| [`ADR-010-unified-resource-list-shell.md`](ADR-010-unified-resource-list-shell.md) | Build order Phase 1–5 |
| [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md) | Superseded — redirect to Platform Canon |
| [`ADR-010-unified-resource-list-shell.md`](ADR-010-unified-resource-list-shell.md) | Superseded — workspace types reference only |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-08-21 | Collection orchestration: `ListWorkspace` owns query/filter/sort/pagination/selection/saved views/URL; DataTable is one representation (`collection_orchestration`) |
| 2026-08-13 | Analytics canon: [`ADR-046`](ADR-046-analytics-visualization-canon.md) — four layers (semantics, grammar, composition, presentation/sharing); Recruitment efficiency reference |
| 2026-08-13 | Composition canon: [`ADR-043`](ADR-043-ui-component-composition-canon.md) — pages assemble the React kit |
| 2026-07-09 | Platform Canon + Interaction Rules layer; §10 roadmap |
| 2026-07-09 | Renamed scope → Product Surface Contract; UI Platform split to hostflow-ui-platform-v1 |
| 2026-07-09 | §10 **primitives-first** build order; design-system-constitution-v1 |
| 2026-07-09 | §10 development order — four stages, freeze rules; link canonical-workspaces-roadmap |
| 2026-07-09 | v1 initial — product objects, ownership, four workspace types, Application reference = Sales, Lead ban in UI |
