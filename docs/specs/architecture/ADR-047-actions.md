# ADR-047: Actions (contract + confirmed slice)

**Status:** Accepted  
**Date:** 2026-08-13  
**Layer of change:** Vocabulary (Actions) | Contract + slice inventory  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-038`](ADR-038-platform-standardization-model.md) · [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md) · [`ADR-036`](ADR-036-four-trust-roles-rbac.md) · [`ADR-026`](ADR-026-capability-ownership.md) · [`ADR-012`](ADR-012-activity-notification-operating-layer.md) · [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`ADR-040`](ADR-040-naming-identifiers.md) · [`ADR-042`](ADR-042-relationships.md) · L2 [`../platform/actions.md`](../platform/actions.md)

**Note on numbering:** ADR-043 = UI composition; ADR-044 = ListWorkspace / DataTable (rule); ADR-045 reserved for layouts; ADR-046 = analytics, visualization & reporting. This Actions vocabulary ADR is **047**.

**L0 checklist:** No new L0 P-rule; does not rewrite Passport/Manifest; fills ADR-038 area `actions` with an **Action contract + confirmed-slice inventory**, not the ADR-019 3A-3 runtime Action Registry implementation.

---

## Context

ADR-038 hard rule **Action ≠ Permission ≠ Capability**. ADR-019 §14.7 defines the future Action Registry (input contract, required capability, permission, idempotency, rollback, audit) and schedules public CRM actions in **3A-3**.

Today runtime still has **fragments**: tenant `automation_rules` JSON (`create_reminder`), Document Hub mutate/review ops, Process Engine transition/handoff rules, C2.2 **Intents** (egress keys — not Actions). Without a shared Action vocabulary, modules and automations keep inventing side-effect strings and collapsing authz layers.

---

## Decision

### 1. Action is vocabulary — not a runner, not a permission

An **Action** is a platform `qualified_code` (dotted `object.verb` / `domain.verb`, ADR-040) naming an **operation that may be invoked** (by human API, automation, or orchestrator). It is **not**:

| Not an Action | Why |
|---------------|-----|
| Permission | Who may invoke (ADR-036 / RBAC) |
| Capability / entitlement | Whether tenant/module/plan **exposes** the operation (Catalog / ADR-019 §14.8) |
| Domain Event | Fact that already happened (Events area; ADR-019 “event ≠ command”) |
| Communication Intent | C2.2 egress key (`intent_key`) — may later **map to** an Action, is not itself one |
| Process transition **rule** / gate code | Configuration of when a transition is allowed — the executable op is still an Action (e.g. `process.transition`) |
| RelationshipKind | Association between objects (ADR-042), not an operation |
| SQL procedure / service method name | Implementation may realize an Action; the code is the vocabulary SoT |

### 2. Mandatory contract fields

Every Action row must declare (aligned with ADR-019 §14.7 + inventory needs):

| Field | Meaning |
|-------|---------|
| `action_code` | Dotted `qualified_code` |
| `subject_kind` | Primary object / subject kind the action applies to |
| `effect_summary` | What successful invocation changes or requests |
| `owner` | Module/capability that owns the action semantics |
| `required_capability` | Capability code(s), or `—` if none |
| `permission` | Permission / authz surface (or pointer) |
| `idempotency` | Key strategy (descriptive) |
| `rollback` | Rollback / compensation notes (descriptive; may be `none`) |
| `writers` | Who may invoke (human roles, orchestrator, automation modes) |
| `status` | `confirmed` \| `fragment` |
| `sot_refs` | Evidence / target registry paths |
| `notes` | Aliases, forbidden mixes, 3A-3 deferrals |

### 3. Scope of this PR’s inventory

**Confirmed slice:** Documents / Activity-Notification / Process-handoff / platform notification send — operations already evidenced in Hub, PE, ADR-012, ADR-019 examples that are **not** CRM-pipeline-only.

**Fragment / out_of_slice:** full CRM 3A-3 set (`candidate.change_stage`, `candidate.open_transfer`, …), C2.2 intent keys as actions, PE rule codes as actions, legacy `create_reminder` JSON as a permanent code.

This ADR does **not** implement Action Registry packages or cross-module automation before ADR-019 3A-3.

### 4. Linkage to Permission and Capability

```text
Capability (exposed?) → Action (what) → Permission (who)
```

- Automation / Reaction Orchestrator may only invoke **registered Actions**.
- UI must not invent a parallel “can do X” string that bypasses Capability + Permission.
- Missing capability → CapabilityPreview / upsell path (ADR-019), not a silent no-op without explanation (product rule).

### 5. Naming

Prefer ADR-019-style dotted codes (`document.review`, `activity.create`, `notifications.send`). Do not invent a second flat snake_case Action vocabulary (`document_review`) for the same operations.

### 6. Runtime

Docs-only. No new `platform/actions/` package, migrations, or automation_rules JSON rewrite in this PR. ADR-019 3A-3 remains the implementation path.

---

## Out of scope (explicit)

- ADR-019 3A-3 runtime Action Registry
- Full CRM action set as `confirmed`
- Promoting C2.2 Intents to Actions
- Events Canon (next ADR-038 vocabulary item)
- Design SVL / DocumentType alignment

---

## Explicit next

1. **Events Canon** (ADR-038 area `events`) — facts vs commands.
2. ADR-019 **3A-3** implementation adopts `action_code` rows from L2 (+ CRM public actions).

---

## Architecture Review Checklist (L0)

- [x] P-01…P-05 respected — no new capability Passport
- [x] Action ≠ Permission ≠ Capability preserved
- [x] Does not implement cross-module actions before 3A-3
- [x] Aligns with ADR-019 §14.7 contract fields
- [x] L0 freeze untouched

---

## Consequences

- Positive: Actions area becomes `exists` as vocabulary/contract; Document Hub and PE ops have stable codes; Intent/Event/Permission stay separable.
- Negative: CRM public actions remain fragment until 3A-3; legacy automation JSON still runs.
- Follow-on: Events Canon; 3A-3 registry runtime.

---

## Alternatives considered

1. **Reuse ADR-043 number** — rejected; ADR-043 is UI composition.
2. **Confirm full ADR-019 §14.7 CRM table now** — rejected; those actions are 3A-3 vertical, not evidenced as shared platform slice here.
3. **Treat C2.2 intents as Actions** — rejected; Intent is communications egress, not platform operation semantics.

---

## Cross-references (updated in same change set)

- [`../platform/actions.md`](../platform/actions.md) — L2 inventory
- [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md) — area `actions` → `exists`
- [`ADR-038-platform-standardization-model.md`](ADR-038-platform-standardization-model.md) — next-pointer update
- [`architecture-guide.md`](architecture-guide.md) · [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)
