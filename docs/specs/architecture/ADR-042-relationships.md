# ADR-042: Relationships (contract + confirmed slice)

**Status:** Accepted  
**Date:** 2026-08-13  
**Layer of change:** Vocabulary (Relationships) | Contract + slice inventory  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-038`](ADR-038-platform-standardization-model.md) · [`ADR-037`](ADR-037-platform-object-kind-catalog.md) · [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`ADR-012`](ADR-012-activity-notification-operating-layer.md) · [`ADR-040`](ADR-040-naming-identifiers.md) · [`ADR-041`](ADR-041-data-types.md) · L2 [`../platform/relationships.md`](../platform/relationships.md) · [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md)

**L0 checklist:** No new L0 P-rule; does not rewrite Passport/Manifest; fills ADR-038 area `relationships` with a **RelationshipKind contract + confirmed-slice inventory**, not a full CRM graph and not a runtime table redesign.

---

## Context

ADR-038 required a Relationship Canon as a **contract**, not only a list of edges: `source_kind` / `target_kind`, cardinality, ownership, requiredness, lifecycle dependency, deletion policy, visibility, allowed writers. Runtime today has fragments (`document_entity_links`, Activity soft refs, thread links) without a shared vocabulary of **kinds**.

Without this canon, modules invent ad-hoc FK tables or overload Activity pointers as if they were typed relationships.

---

## Decision

### 1. RelationshipKind is vocabulary — not a table description

A **RelationshipKind** is a platform `stable_code` (ADR-040) naming a *typed association between object kinds*. It is **not**:

- the name of a SQL table or FK column;
- a dump of every join that exists in the schema;
- a substitute for ObjectKind / Field / DataType.

Concrete tables may **implement** one or more kinds. Inventory rows may cite `sot_refs` for evidence; the kind remains the SoT for meaning.

### 2. Hard separations (must not collapse)

| Not a RelationshipKind | Why |
|------------------------|-----|
| Field / DataType | Value semantics and field identity (ADR-041); `reference_code` is not an edge |
| Permission / Capability | Who may act / what is entitled (ADR-036 / Catalog) |
| Activity / Notification soft pointer alone | Polymorphic work-item binding (ADR-012); may **cite** a kind when catalogued, but `related_entity_type` is not itself the Relationship Canon |
| Process / handoff **lifecycle state** | Workflow progress (ADR-039 dimensions / Process Engine); a handoff *edge* may be a kind, its status is not |
| DocumentType / evaluation codes | Naming / evaluation vocabulary (ADR-040 / ADR-018) |

### 3. Mandatory contract fields

Every RelationshipKind row must declare:

| Field | Meaning |
|-------|---------|
| `relationship_kind` | Flat `stable_code` |
| `source_kind` | Object / entity kind of the source end |
| `target_kind` | Object / entity kind of the target end (may be an opaque ref kind — see §5) |
| `cardinality` | e.g. `1:1`, `1:N`, `N:M` (descriptive) |
| `ownership` | Who owns the relationship record / SoT |
| `requiredness` | Whether the edge is mandatory for source/target validity |
| `lifecycle_dependency` | What happens relative to source/target lifecycle (independent / follows source / …) |
| `deletion_policy` | Cascade / restrict / orphan / soft — descriptive of intended policy |
| `visibility` | Who may see the edge |
| `writers` | Who may create/update/delete the edge |

### 4. Scope of this PR’s inventory

**In slice (confirmed):** Documents / Object Kind links already named in platform docs or live MVP writers, plus a small set of proven handoff / assignment / Activity-binding / Communications C1 kinds with clear evidence.

**Fragment / out_of_slice:** edges that exist as tables or soft refs but are not confirmed as platform RelationshipKinds yet — listed only as notes, **not** invented into full contract rows.

Do not “complete the CRM graph” in this PR.

### 5. Opaque / external results

`thread_opaque_result` (and any future opaque kinds) means: a link from a Communications Thread to an **OpaqueResultRef** (module_owner + result_type + result_id, optional ledger provenance) — **not** a new first-class domain entity and **not** an ORM FK to Application / SalesInquiry. The target is an opaque external/result handle, not a promoted ObjectKind.

### 6. Platform-first

New cross-module association that needs shared semantics must **register a RelationshipKind** (or stay explicitly module-local with an architecture exception). Registering a kind does not require shipping a new table in the same PR.

### 7. Runtime

This ADR does **not** migrate schemas, rename `relation_type` values, or add enforcement gates beyond docs-lint inbound links.

---

## Out of scope (explicit)

- Full CRM / Candidate / Vacancy / Campaign relationship graph
- Calendar provider sync links as platform kinds
- Field Registry `reference_code` remodel
- Actions / Events / Design SVL
- DocumentType seed alignment
- Runtime migrations

---

## Explicit next

1. Actions: **done** ([`ADR-047`](ADR-047-actions.md)). ADR-038 vocabulary sequence continues with **Events**.
2. Optional: expand L2 with more confirmed kinds; Document Hub writers adopt registered `relationship_kind` codes.

---

## Architecture Review Checklist (L0)

- [x] P-01…P-05 respected — no new capability Passport
- [x] Does not invent a full CRM edge SoT
- [x] Preserves Field/DataType, Permission, Activity, Process separations
- [x] Aligns with ADR-038 §6 contract requirement
- [x] L0 freeze untouched

---

## Consequences

- Positive: Relationships area becomes `exists` as a contract; Document Link and Comms opaque results have vocabulary homes; modules know when to register a kind.
- Negative: many runtime joins remain `fragment` until confirmed; Activity soft refs stay dual-nature until adoption guidance expands.
- Follow-on: ~~Actions~~ (ADR-047); Events; UI Data Presentation (ADR-044) / Layouts (ADR-045) / Visualization (ADR-046).

---

## Alternatives considered

1. **Inventory every FK in the database** — rejected; recreates an unmaintainable graph and violates one-slice PRs.
2. **Treat Activity `related_entity_type` as the Relationship Canon** — rejected; soft work-item binding ≠ typed association contract.
3. **Ship table migrations with the ADR** — rejected; docs-only pattern (ADR-037…041).

---

## Cross-references (updated in same change set)

- [`../platform/relationships.md`](../platform/relationships.md) — L2 contract inventory
- [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md) — area `relationships` → `exists`
- [`ADR-038-platform-standardization-model.md`](ADR-038-platform-standardization-model.md) — next-pointer update
- [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md) · [`architecture-guide.md`](architecture-guide.md) · [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)
