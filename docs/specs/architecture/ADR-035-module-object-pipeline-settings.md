# ADR-035: Module → Objects → Pipelines → Settings

**Status:** Accepted (architecture). **Concept FROZEN** — further product work implements Phases B–D; do not extend the model without a superseding ADR.

**Supersedes (partial, strangler):** operational use of `ready_for_hr` / `processing_by_hr` / `ready_for_fleet` (and similar) as **Candidate operational stages** or as the object's current board position. Legacy codes remain readable during migration; new presets and builders must not add them as stages.

**Related:** [ADR-002](ADR-002-modular-recruitment-hr-boundary.md) (amended), [ADR-003](ADR-003-tenant-company-module-data-boundaries.md), [ADR-004](ADR-004-five-product-modules-and-billing-events.md), [ADR-005](ADR-005-three-level-settings-hierarchy.md) (amended), [ADR-023](ADR-023-recruitment-sales-module-separation.md), [ADR-028](ADR-028-configuration-ownership.md) (P-04), [ADR-029](ADR-029-settings-contract.md) (P-05), [module-owned-pipelines-p0.md](module-owned-pipelines-p0.md), [handoff-contract.md](handoff-contract.md), [operational-event-boundaries.md](operational-event-boundaries.md), [invariants-recruitment-hr-document-hub.md](invariants-recruitment-hr-document-hub.md).

**L0 checklist:** Ownership = product modules (Catalog); no new L0 P-rule; Settings Contract / ownership per P-04/P-05; SoT per object type; events = system transition fires + existing handoff/workforce facts; Requires = enabled modules for gated transitions; no new license key; public contract additive (pipeline edges + lifecycle).

---

## Context

HostFlow mixed four ideas that look alike in the UI: **business process**, **pipeline**, **module**, and **settings**. That produced a single “general funnel”, HR pseudo-stages on the Candidate board (`ready_for_hr`, `processing_by_hr`), and Sales language under `module_key=recruitment`. Companies named instances as if they were new product types (`Driver Test 2027`). The deepest defect: treating Lead → Candidate → Employee → Driver as **one growing object** instead of **linked objects in separate bounded contexts**.

---

## Decision

### 1. Ownership order (non-negotiable)

```text
Module → Object types → Pipelines (0..N) → Module Settings
```

**Forbidden:** `Settings → Pipelines → Modules` (including root admin `Settings → Funnels` as the product home for pipelines).

- A module **owns** its objects and may own **zero or more** pipelines per object type.
- Pipelines are configured under **that module’s** Company Module Settings, not under a global funnel dump.
- Platform System Settings (OAuth, Email/SMS, Meta, AI, Storage, logs, backup, superadmin) are **not** tenant operational pipelines ([ADR-005](ADR-005-three-level-settings-hierarchy.md) §0 as amended).

### 2. Vocabulary

| Term | Meaning | Must not confuse with |
|------|---------|------------------------|
| **Module** | Product / license key (`recruitment` \| `hr` \| `fleet` \| `services` \| `finance`) | Pipeline |
| **Object** | Domain entity of a module (`Candidate`, `WorkforceEmployee`, `SalesInquiry`, …) | “Same person renamed” |
| **Pipeline** | Graph for **one object type**: operational stages + exit **system transitions** | Cross-module business process |
| **Operational stage** | Where the object **is** and work happens | System transition |
| **System transition** | Platform-catalog exit / handoff into another BC | Pipeline stage / lifecycle |
| **Lifecycle status** | `active` \| `closed` \| `archived` | Board column |
| **Pipeline template / instance** | Platform template → company named instance | Inventing a new pipeline “type” |

Product language: **Recruitment Pipeline**, **HR Employee Pipeline**, **Sales Pipeline**. Do not use “воронка / funnel” as a universal product term. Table `funnels` remains a **storage shape** name only.

**Glossary (not new ADR-004 keys):** Documents = Document Hub (platform); ATS = Recruitment surface; Sales = commercial host (license capability often `services` per ADR-023).

### 3. Pipeline is typed by object

Examples:

- Recruitment / **Candidate** → Driver Recruitment, Warehouse, Office (instances).
- HR / **WorkforceEmployee** → Onboarding, Relocation, Active Employment.
- Sales / **SalesInquiry** → New Clients, Existing Clients, Partners.

An Employee **cannot** be placed on a Recruitment pipeline: the pipeline’s object type forbids it.

### 4. Templates → company instances

- **Platform** publishes a limited **template catalog**.
- **Company** selects a template and creates a **named instance** (e.g. «Poltrakt Drivers») with allowed local edits (labels, order, which catalog transitions are wired, target pipeline for handoffs).
- Company must **not** invent unbounded new pipeline *types*. Naming / count limits are enforced in product (Phase B+).

### 5. Invariants A1 / A2 — stages vs system transitions

**A1.** A pipeline consists of **operational stages** and may exit/branch via **platform-defined system transitions**. A system transition appears in the pipeline **builder** as a node but:

- is **not** a `pipeline_stage` row used as board position;
- is **never** the object’s current position;
- fires as an **event** (closes lifecycle and/or creates a target-module object).

**A2.** Available transitions = f(`source_module`, `object_type`, company `enabled_modules`, **platform transition catalog**). Arbitrary “handoff anywhere” is forbidden. New paths require a **catalog + ADR** change, not a custom stage name.

#### Platform transition catalog (initial)

| Catalog key | Typical source | Effect |
|-------------|----------------|--------|
| `handoff_to_hr` | Recruitment / Candidate | Optionally create `WorkforceEmployee`; start chosen HR Employee Pipeline at initial stage; Candidate lifecycle → `closed` (read-only) |
| `handoff_to_fleet` | HR / Employee | Create Fleet assignment / entity linked to Employee — **not** a “Driver Employee” rename |
| `handoff_to_client` | Recruitment / Candidate | Client portal / client responsibility; Employee **not** required |
| `close_success` | Any pipelined object | Lifecycle → `closed` |
| `close_declined` | Any pipelined object | Lifecycle → `closed` (declined semantics) |

**Gating examples:**

- Recruitment: → HR (if `hr` enabled), → Client, → Close. **Not** → Fleet.
- HR: → Fleet (if `fleet` enabled), → Close.
- Sales: → Client, → Close. **Never** Candidate.

**Instance config** (does not redefine catalog semantics), e.g. `handoff_to_hr`:

- Target module/object — fixed (HR / WorkforceEmployee).
- Target HR pipeline instance + initial operational stage — selectable.
- Create Employee — system action when process keeps the person in HostFlow HR.
- Candidate lifecycle after — `closed` (system rule).

**Forbidden as operational stages / current position:** `ready_for_hr`, `processing_by_hr`, `ready_for_fleet`, and similar pseudo-stages. Legacy codes map via strangler to catalog transitions until removed from presets.

Handoff is a **system transition (event)**, not a kanban stage. Last operational stages on Recruitment are e.g. `accepted` / `ready_for_client` (product labels); then the transition fires.

### 6. Lifecycle ⊥ board position

| Axis | Values | Storage |
|------|--------|---------|
| Lifecycle | `active` \| `closed` \| `archived` | On the object |
| Position | Operational stage only | `pipeline_id` + `pipeline_stage_id` |
| Transition | Not a position | Edge config + event log on fire |

Do **not** use `lifecycle_status=handoff`. Handoff is an event that typically sets lifecycle to `closed`.

### 7. Employee creation is optional

`handoff_to_hr` / client paths: create `WorkforceEmployee` **only if** company has `hr` enabled **and** the process provides for managing the employee in HostFlow. Client-portal-only hire with **no** Employee row is a valid outcome.

### 8. Four objects, not one growing record

| Module | Creates | Does not become |
|--------|---------|-----------------|
| Sales | Client (via Inquiry / Opportunity) | Candidate |
| Recruitment | Candidate | Employee |
| HR | Employee | Driver |
| Fleet | Driver Assignment (etc.) | — |

Links and events are allowed. Renaming one row through Sales → Recruitment → HR → Fleet is forbidden.

Sales **never** operates on `Candidate`. Spine: `SalesInquiry → Opportunity → Client`; Recruitment consumes **Client** demand separately ([ADR-023](ADR-023-recruitment-sales-module-separation.md)).

### 9. Settings levels (ADR-005 amendment)

1. **System** — platform integrations and superadmin (not company pipelines).
2. **Tenant** — module licenses + limits (+ copy-on-create presets only).
3. **Company** — `enabled_modules`, legal/access context.
4. **Module Settings (per company)** — pipelines (instances), profiles, automations, SLA under the owning module.

UI: `Recruitment → Pipelines`, `HR → Employee Pipelines`, `Sales → Sales Pipelines` — never a global funnel home as SoT.

### 10. Target data model (implementation Phases C+)

- Object: `lifecycle_status`, `pipeline_id`, `pipeline_stage_id` (FK to operational stage of the same pipeline).
- Pipeline definition: stage rows + **transition edges** `{ catalog_key, from_stage_id?, config_json }` — edges are **not** stage rows.
- Storage may keep `funnels` / `funnel_stages` naming; add edge table/entity. Do not encode transitions as fake `funnel_stages.code`.
- Compatibility: map legacy `ready_for_*` writes to catalog transition fire where possible; then delete from operational presets.

### 11. Implementation sequence

| Phase | Scope |
|-------|--------|
| **A** | This ADR + doc amends (this PR) |
| **B** | Builder palettes; module IA; template→instance; gate transitions; reject stage ∉ pipeline |
| **C** | Lifecycle + `pipeline_stage_id`; edge storage; fire handlers; tests |
| **D** | Sales cleanup — Inquiry→Opportunity→Client only; remove recruitment “sales” lead product path |

---

## Consequences

- Product and agents stop designing “one HostFlow funnel”.
- Poltrakt (Recruitment on, HR off): instance ends with `handoff_to_client`; builder hides `handoff_to_hr`.
- Focus (Recruitment + HR): `handoff_to_hr` closes Candidate and may start Employee on HR pipeline.
- Process Engine / analytics must treat catalog transitions as events, not as `Candidate.stage` values (cutover in Phase C).
- ADR-002 stage codes `ready_for_hr` / `hired` remain **legacy strangler** labels until Phase C cutover; new design must not add more cross-module stage codes.

## Alternatives considered

- **Keep handoff as Candidate stages** — rejected; recreates `ready_for_*` pollution.
- **Company-defined transition types** — rejected; catalog chaos.
- **Sixth product module for Documents/ATS** — rejected without Architecture RFC; map via glossary.
- **Replace `funnels` table immediately** — rejected; strangler on shape + ownership first.

## Cross-references (updated with this ADR)

- [ADR-002](ADR-002-modular-recruitment-hr-boundary.md) — handoff as transition; legacy stages marked strangler.
- [ADR-005](ADR-005-three-level-settings-hierarchy.md) — System level + module-first pipeline home.
- [handoff-contract.md](handoff-contract.md), [operational-event-boundaries.md](operational-event-boundaries.md).
- [invariants-recruitment-hr-document-hub.md](invariants-recruitment-hr-document-hub.md).
- [docs/recruitment/module-scope.md](../../recruitment/module-scope.md), [docs/hr/module-scope.md](../../hr/module-scope.md).
- [docs/specs/tasks/adr035-phase-d-sales-pipeline-cleanup.md](../tasks/adr035-phase-d-sales-pipeline-cleanup.md) — Sales Inquiry→Client only.

## History

- 2026-08-07: Accepted — frozen Module → Objects → Pipelines → Settings canon; A1/A2 system transitions; four-object rule; Phases B–D implementation track.
