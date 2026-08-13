# ADR-038: Platform Standardization Model

**Status:** Accepted  
**Date:** 2026-08-13  
**Layer of change:** Constitution (meta) | Platform standardization map  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-037`](ADR-037-platform-object-kind-catalog.md) · [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md) · [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md) · [`ADR-026`](ADR-026-capability-ownership.md) · [`ADR-036`](ADR-036-four-trust-roles-rbac.md) · [`platform-capability-catalog.md`](platform-capability-catalog.md) · L2 index [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md)

**L0 checklist:** No new L0 P-rule; does not rewrite Passport/Manifest shape; references Catalog / P-01…P-05; ADR-037 remains the ObjectKind / RuleKind / LibraryKind vocabulary and is **not** expanded by this ADR.

---

## Context

HostFlow already has strong pieces of platform standardization (Object Kind Catalog, Capability Catalog, Field Registry, RBAC trust roles, UI Platform Standard, Forms contracts). Without a single **map of standardization areas**, each next canon (states, colors, relationships, events) risks becoming an independent initiative — thirteen documents without a shared coordinate system.

ADR-037 answered *what object classes exist* for Documents / Requirements / Automation / Templates. This ADR answers *which standardization areas the platform has at all*, who owns each, and the rule that forces modules to reuse platform standards before inventing local ones.

---

## Decision

### 1. One meta-canon — Platform Standardization Model

The Platform Standardization Model is **one** meta-canon. It is **not** a list of thirteen independent canons and **not** a data SoT.

It defines:

1. Which **groups** of platform standards exist.
2. Which **areas** live in each group (closed list of fourteen).
3. That each area has an owner and a maturity status (`exists` | `next` | `gap`) in the L2 index.
4. The **Platform-first / Reuse-first** rule (mandatory).
5. That **Architecture Enforcement** is a mechanism, not a fifteenth subject area.

Inventory content for each area (datatype catalog rows, state dimensions, semantic colors, …) lives in follow-on ADRs / L2 specs — not here.

### 2. Five groups

| Group | Purpose |
|-------|---------|
| **Vocabulary** | Shared language: kinds, roles, fields, types, relationships, states, actions, events, naming |
| **Policy & Reuse** | Rules, libraries, capabilities — how truth and reuse are governed |
| **Runtime Contracts** | API / envelope / error / reference / audit / pagination contracts |
| **Experience** | Design system and interaction standards |
| **Governance** | Enforcement mechanisms that make the other areas binding |

### 3. Fourteen standardization areas (closed)

| # | Area | Group |
|---|------|-------|
| 1 | Object Kind | Vocabulary |
| 2 | Roles & Permissions | Vocabulary |
| 3 | Fields | Vocabulary |
| 4 | Data Types | Vocabulary |
| 5 | Relationships | Vocabulary |
| 6 | States & Transitions | Vocabulary |
| 7 | Rules | Policy & Reuse |
| 8 | Libraries | Policy & Reuse |
| 9 | Actions | Vocabulary |
| 10 | Events | Vocabulary |
| 11 | Capabilities | Policy & Reuse |
| 12 | Runtime / API Contracts | Runtime Contracts |
| 13 | Design & Interaction | Experience |
| 14 | Naming & Identifiers | Vocabulary |

Status of each area (`exists` / `next` / `gap`), owners, and current refs: L2 [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md).

**ADR-037 placement:** Object Kind, Rules (RuleKind), and Libraries (LibraryKind) are **exists** under Vocabulary + Policy & Reuse. This ADR does **not** add ObjectKinds or rewrite ADR-037.

### 4. Platform-first / Reuse-first (mandatory)

> Any new platform element — entity, field, datatype, relationship, state, action, event, rule, library, capability, API contract, or UI pattern — is first checked against the corresponding Platform Catalog / standard.  
> Only if no suitable element exists may the canon be extended.  
> Only after that extension may a module use the new element.

Local duplicates of an existing platform element are an architecture violation (caught by review checklist and, over time, by enforcement hooks).

### 5. Hard separations (must not collapse)

| Layers | Rule |
|--------|------|
| **Field ≠ DataType** | Semantic datatypes (`phone`, `money`, `country`, `date`) are shared; fields (`candidate.phone`, `vacancy.salary`) **use** a datatype. Formatters, validators, serializers, filters, and UI renderers bind primarily to DataType. |
| **Action ≠ Permission ≠ Capability** | Action = operation semantics (`document.review`, `workflow.transition`). Permission = who may execute it. Capability = whether the tenant/module/plan exposes it. Link them; do not merge. |
| **EvaluationFact ≠ RuntimeInstance lifecycle** | Per ADR-037: computed outcomes are not process lifecycles. |

### 6. Relationship Canon requirement (named, not inventoried)

A future Relationship Canon must define a **contract**, not only a list of edges:

- `source_kind` / `target_kind`
- cardinality
- ownership
- requiredness
- lifecycle dependency
- deletion policy
- visibility
- allowed writers

Inventory is out of scope for this ADR.

### 7. Design & Interaction norms (area 13)

Under ADR-011, three prohibitions are platform law for modules:

1. No local **semantic colors**.
2. No local clones of existing **primitives / patterns**.
3. No module-specific **interaction patterns** without registering a new platform pattern.

**Semantic Visual Language** (State/Meaning → semantic token → visual treatment → icon/sign → tooltip/a11y) is the intended Design System extension. Token tables and color migration are **out of scope** for this PR; noted as a sub-gap under area 13.

### 8. Architecture Enforcement is a mechanism

Enforcement (architecture-review-checklist, `docs-lint`, REF-4 / boundary gates, ADR-011 UI drift checks) is **Governance**: it forces the fourteen areas to work. It is **not** a fifteenth subject canon and does not own domain vocabulary.

### 9. Explicit next PR

**States & Transitions** inventory: **done** — [`ADR-039`](ADR-039-state-lifecycle-inventory.md) · [`../platform/state-lifecycle-inventory.md`](../platform/state-lifecycle-inventory.md). Shared platform status enum remains **deferred**.

**Naming & Identifiers:** **done** — [`ADR-040`](ADR-040-naming-identifiers.md) · [`../platform/naming-identifiers.md`](../platform/naming-identifiers.md). DocumentType runtime alignment (`integrity=split` → `aligned`) remains a **separate** PR.

**Data Types:** **done** — [`ADR-041`](ADR-041-data-types.md) · [`../platform/data-types.md`](../platform/data-types.md). Runtime Field/Forms `data_type` adoption remains a **separate** PR.

**Next in ADR-038 sequence:** Relationships contract (area 5, `gap`) — unless product prioritizes Design Semantic Visual Language, DocumentType alignment, or Field/Forms DataType adoption.

---

## Architecture Review Checklist (L0)

- [x] P-01…P-05 respected — no new capability Passport; indexes existing Catalog / ADR-037 / ADR-011 / ADR-036
- [x] Does not rewrite L0 or expand ADR-037 ObjectKinds
- [x] Platform-first rule aligns with INV-16 (ownership / contracts before convenience)
- [x] ADR references Catalog — does not duplicate constitution
- [x] Enforcement described as mechanism, not a new domain SoT

---

## Consequences

- Positive: single coordinate system for all follow-on canons; clear exists/next/gap map; Platform-first turns documentation into architecture; Action / Permission / Capability and Field / DataType stay separable.
- Negative: gap areas must be filled by dedicated PRs; until then modules must not invent local replacements.
- Follow-on sequence (separate PRs): ~~State/Lifecycle inventory~~ (ADR-039) → ~~Naming & Identifiers~~ (ADR-040) → ~~Data Types~~ (ADR-041) → Relationships contract → Actions / Events (ADR-019 3A-*) → Design Semantic Visual Language on ADR-011. DocumentType alignment and Field/Forms `data_type` adoption may run in parallel.

---

## Alternatives considered

1. **Thirteen independent canons without a parent model** — rejected; recreates fragmentation.
2. **Expand ADR-037 to hold all fourteen areas** — rejected; mixes object ontology with platform map.
3. **Ship State inventory in the same PR** — rejected; one PR — one architectural idea.
4. **Merge Action into Permission or Capability** — rejected; three layers must stay linked but distinct.

---

## Cross-references (updated in same change set)

- [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md) — L2 area index + status map
- [`ADR-037-platform-object-kind-catalog.md`](ADR-037-platform-object-kind-catalog.md) — Object Kind / Rules / Libraries under this model
- [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md) — parent pointer
- [`platform-capability-catalog.md`](platform-capability-catalog.md) · [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) · [`architecture-guide.md`](architecture-guide.md)
