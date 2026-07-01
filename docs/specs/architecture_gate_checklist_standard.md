# Architecture Gate Checklist Standard

Status: mandatory process standard  
Applies to: HostFlow platform architecture decisions and architecture-impacting tasks.

## 1. Purpose

This standard defines a mandatory architectural gate process that must pass before system complexity is increased.

This is not per-PR bureaucracy. It is required before any architecture decision/task that introduces or changes platform contracts, runtime layers, or source-of-truth boundaries.

## 2. When Gate Is Mandatory

Gate is required before:
1. new module layer;
2. new runtime contract;
3. new resolver;
4. new consumer of existing contract;
5. new integration flow between modules;
6. any change to source of truth, reference ownership, or contract shape.

## 3. Gate Outcome Types

1. `PASS`: implementation may start.
2. `PASS_WITH_CONSTRAINTS`: implementation may start only with listed constraints.
3. `STOP`: implementation is prohibited until blocking conditions are resolved.

## 4. Foundation Gate (mandatory)

All answers must be explicit (`yes/no + evidence`):
1. canonical source of truth exists for this domain;
2. reference layer is complete enough for this change;
3. versioning strategy is defined;
4. ownership is defined (platform vs module);
5. migration path is defined;
6. compatibility strategy is defined (and time-bounded).

Evidence examples:
- spec/ADR link;
- existing resolver/facade contract;
- migration doc;
- ownership map.

## 5. Contract Gate (mandatory)

1. contract is frozen (or a freeze date/version is set);
2. DTO/response model is stable for current phase;
3. facade exists as single read path;
4. direct table access is forbidden for consumers;
5. override policy is defined (what tenant can and cannot override).

## 6. Consumer Gate (mandatory)

1. current consumer count is known;
2. no duplicated business logic across consumers;
3. no local module-side `if/else` rule engines;
4. no facade bypass in runtime paths;
5. hidden runtime assumptions are listed and validated.

## 7. Rewrite Risk Gate (mandatory)

1. rewrite impact is estimated if foundation changes;
2. affected runtime layers are enumerated;
3. irreversible coupling risks are identified;
4. rollback cost and feasibility are assessed.

Minimum output:
- impacted modules list;
- contract break risk (`low/medium/high`);
- rollback strategy (`safe/limited/high-cost`).

## 8. Delivery Gate (mandatory)

1. tests exist (unit + integration scope as applicable);
2. migration strategy exists;
3. observability/logging exists for new runtime decisions;
4. deprecation plan exists for replaced paths;
5. removal owner is assigned for every compatibility path.

Compatibility path rule:
- must include owner + target removal milestone/version/date.

## 9. STOP CONDITIONS (hard blockers)

Implementation of next layer is prohibited if any is true:
1. foundation incomplete for intended scope;
2. contract unstable with no freeze plan;
3. multiple sources of truth in same domain;
4. unresolved ownership boundary;
5. missing facade for cross-module consumption;
6. duplicated consumer logic already exists;
7. compatibility path introduced without removal plan/owner.

Optional additional stops (recommended):
1. no migration strategy for stateful change;
2. no observability for new decision path;
3. consumer count > 2 with contract still unstable.

## 10. Process Flow

1. Open architecture task/decision record.
2. Run all gates (Sections 4-8).
3. If any STOP condition exists -> mark `STOP`, do not implement next layer.
4. Resolve blockers at foundation/contract level.
5. Re-run gate and record decision (`PASS` or `PASS_WITH_CONSTRAINTS`).
6. Only then implementation begins.

## 11. Required Gate Record (artifact)

Each architectural decision/task must include a gate record with:
1. scope;
2. owner;
3. gate answers with evidence links;
4. STOP conditions status;
5. decision (`PASS` / `PASS_WITH_CONSTRAINTS` / `STOP`);
6. constraints (if any);
7. compatibility removals (owner + milestone).

## 12. Enforcement Policy

1. Architecture-impacting implementation without gate record is non-compliant.
2. New runtime layer cannot be approved if gate decision is `STOP`.
3. Temporary compatibility paths without removal owner/milestone are forbidden.
4. Module-level rule logic that bypasses facade is forbidden.

## 13. Relation to Existing Standards

This standard is a process gate and must be used together with:
- `Reference Delivery Contract Standard (REF-2)`.

Operational sequencing:
1. REF-2 contract baseline;
2. this Architecture Gate process;
3. REF-3/REF-4/REF-5 implementation under gate control;
4. only then higher runtime engines (e.g., M5 as source of truth).
