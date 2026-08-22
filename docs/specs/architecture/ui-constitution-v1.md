# Product Surface Contract v1

**Former title:** UI Constitution v1  
**Status:** canonical (L1 — **domain** product surface).  
**Owner:** Product + Platform UX + Architecture.

**Platform canon (how UI is built):** [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md) — **HostFlow UI Platform Standard** — supreme entry point.  
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

Standard: ADR-010 Resource List Shell.

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
| `/app/leads` (LeadsPage) | **REDIRECT** (slice 4) | Application Workspace + Integrations admin |
| `/app/leads/:id` (LeadDetailPage) | **REDIRECT** (slice 4) | Application Workspace split-view |
| Recruitment Inbox → `/app/leads/:id` | **DONE** (2026-07-09) | `/app/recruitment/inbox/:applicationId` |
| Search Home as competing inbox | **DONE** (2026-07-09) | Process Workspace; pending apps → Отклики CTA |
| Three list implementations | **IN PROGRESS** | `ApplicationWorkspace` engine |
| Four detail cards | **IN PROGRESS** | `ApplicationDetailCard` + Action Panel plugins |
| Frontend `listLeads()` in sales/recruitment pages | **DONE** (2026-07-09) | Application facade API |
| Mutations via `/leads` in module pages | **DONE** (2026-07-09) | `/sales/inquiries`, `/recruitment/applications` facades |
| Dual reference (Search Home + Sales) | **RESOLVED** | Sales Application Workspace only |

Track progress in [`hostflow-core-domain-map-v1.md`](hostflow-core-domain-map-v1.md). Remaining mixed `/app/leads` product surface → Stage 3 slice 4 ([brief](../tasks/stage-3-slice-4-hard-module-separation.md)).

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

**Nearest goal:** Documents Platform E4 — Candidate Document Link through D2 `documents` + Hub `document_entity_links`. E3 First Consumer Bind (HR employee) is **COMPLETE**. Workspace Capability Platform is **COMPLETE**. G4 on Recruitment Application already **PASS** and is **not** the Documents proof. Entity Workspace and Application Workspace stay distinct (§3.2 / §3.3).

| Phase | Deliverable |
|-------|-------------|
| **1** | Universal Data Table + Selection Model + Detail Rail |
| **2** | Universal Entity Workspace + Context Rail (D1 chrome) |
| 2a | Platform surfaces on one entity (D2: overview / timeline / communication / forms / documents / context-rail) — brief-complete, **goal-incomplete** |
| **2b** | [Workspace Capability Platform Completion](../tasks/workspace-capability-platform-completion.md): G4 PASS on Recruitment Application. Program **COMPLETE** ([record](../gates/workspace-capability-platform-complete.md)). |
| **2b-eq ✅** | [Host runtime-equivalence](../tasks/workspace-capability-host-runtime-equivalence.md): Entity Workspace implements the same host contract at runtime; Notes/Consent hide transport. |
| **2c ✅** | [Documents Platform E3](../tasks/documents-platform-e3-first-consumer-bind.md): first D2 `documents` consumer bind (HR employee) + Document Link SoT. |
| **2d ← active** | [Documents Platform E4](../tasks/documents-platform-e4-candidate-document-link.md): Candidate Document Link. Host places; Documents owns semantics. Not mass D3–D9 bind. G4 stays Recruitment Application. |
| **3** | Application Workspace implements the **same** host contract — it does **not** become Entity Workspace |
| 4–5 | Process + Collection completion |

Workspace types (§3) describe **composition targets** (Level 4), not build priority.  
Full platform spec: [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md). Build phases: [`ADR-010-unified-resource-list-shell.md`](ADR-010-unified-resource-list-shell.md). Near-term Product Track: [`documents-platform-e4-candidate-document-link.md`](../tasks/documents-platform-e4-candidate-document-link.md). Complete: [`workspace-capability-platform-complete.md`](../gates/workspace-capability-platform-complete.md).

**Do not** invent module data types, fields, primitives, widgets, tables, rails, notes, or consent while assembling a new Entity or Application screen. Stage / vacancy / assignee stay **module contributions**. G4 proof = Recruitment Application assembled from the kit without page-local composition — **closed**; do not reopen it as the Documents proof. Shipping a Notes/Consent/RODO kit that modules still compose locally fails 2b. Do not fold Application into Entity. Documents E4 feat is **locked** until this brief merges. ListWorkspace is a separate collection slice.

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
| [`../tasks/workspace-capability-platform-completion.md`](../tasks/workspace-capability-platform-completion.md) | Capability Host Contract (Entity + Application hosts) |
| [`../tasks/documents-platform-e3-first-consumer-bind.md`](../tasks/documents-platform-e3-first-consumer-bind.md) | Documents E3 — first D2 documents consumer + Document Link SoT |
| [`../gates/workspace-capability-platform-complete.md`](../gates/workspace-capability-platform-complete.md) | WCP program COMPLETE |
| [`../gates/goal-completion-gate.md`](../gates/goal-completion-gate.md) | Phase close: original goal vs substituted brief |
| [`../gates/platform-scope-completeness-audit.md`](../gates/platform-scope-completeness-audit.md) | Closed-phase completeness vs residual capability |
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
| 2026-08-22 | 2c = Documents E3 brief (HR employee bind + Document Link SoT); E2 ✅; G4 stays Recruitment Application |
| 2026-08-21 | 2b COMPLETE (#274); G4 PASS; 2b-eq host runtime-equivalence done; E2 feat unlocked |
| 2026-08-21 | 2b G1–G5 PASS_WITH_CONSTRAINTS (#273); G4 PASS; 2b-eq host runtime-equivalence active; E2 locked until 2b COMPLETE |
| 2026-08-20 | §10 2b = Workspace Capability Platform (host places, owners own semantics; Entity ≠ Application); proof = Recruitment Application; D1–D9 brief-complete / goal-incomplete; Documents stay Phase E |
| 2026-07-09 | Platform Canon + Interaction Rules layer; §10 roadmap |
| 2026-07-09 | Renamed scope → Product Surface Contract; UI Platform split to hostflow-ui-platform-v1 |
| 2026-07-09 | §10 **primitives-first** build order; design-system-constitution-v1 |
| 2026-07-09 | §10 development order — four stages, freeze rules; link canonical-workspaces-roadmap |
| 2026-07-09 | v1 initial — product objects, ownership, four workspace types, Application reference = Sales, Lead ban in UI |
