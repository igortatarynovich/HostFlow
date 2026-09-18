# UI Isolation Card (PMI-UI)

Status: ISOLATED  
Date: 2026-09-16  
Program: [`platform-modularization-isolation-cutover.md`](../../specs/tasks/platform-modularization-isolation-cutover.md)  
Inventory: [`pmi-ui-isolation-inventory.md`](../../specs/tasks/pmi-ui-isolation-inventory.md)

## Module

Name: `Design System / Spine UI`  
Owner: Platform UI (primitives) + spine modules (compositions)  
Runtime roots: `hostflow-frontend/src/platform/design-system/**`, `components/ui/**`, spine module folders  

**Owns:** canonical primitive kit; parallel-primitive forbid; spine composition boundary  

**Does not own:** module business decisions; Ready/Admit/Start policy; Kernel witness  

**Dependency rule:** Design System primitives → Module-owned UI composition → Public module contracts  

**Not PMI-UI:** rewriting all HostFlow screens; Kernel unpark (PMI-X)

## Isolation rows (mapped to four DoD levels)

| # | Row | Status | Evidence |
|---|-----|--------|----------|
| 1 | Owner defined | CLOSED | Platform primitives owner + spine composition owners in authority JSON |
| 2 | Public contract defined | CLOSED | `platform/design-system` barrel + `ui_primitive_authority.json` |
| 3 | Policy / decision authorities | CLOSED | Backend verdict/action contracts; UI must not reconstruct domain decisions |
| 4 | Internal state hidden | CLOSED | Spine compositions must not import sibling module internals for shared chrome |
| 5 | Cross-module dependencies enumerated | CLOSED | Documents→candidate NextActionBadge sealed via design-system |
| 6 | UI surface defined | CLOSED | Ten primitive categories; spine roots listed |
| 7 | Legacy leaks eliminated or isolated | CLOSED | UI debt allowlist **8** (shrink-only); Select controls + one readiness merge |
| 8 | Boundary enforcement works (CI) | CLOSED | `check_ui_isolation.py` + gate test + frontend-static-qa |

## Four DoD levels

| Level | PASS criterion |
|-------|----------------|
| Platform primitives | Authority chosen from inventory; no third kit |
| Module compositions | Spine screens assemble from primitives; DS has no module business logic |
| Decision ownership | Display backend contracts; forbid new reconstructors; legacy listed |
| Enforcement | CI blocks new parallel imports, cross-spine leaks, new reconstructors |

## Allowed dependencies

| From | To | Via |
|------|----|-----|
| Spine module composition | Primitives | `platform/design-system` or locked Layer-2 paths |
| Spine module composition | Backend | Public API / module contracts only |
| Design system | Module business logic | **forbidden** |

## Legacy leaks

| Edge | Disposition |
|------|-------------|
| `controls/Select*` imports (7) | Debt — non-spine / public intake; shrink-only |
| `buildEmployeeReadinessSummary` | Debt — status/CTA prefer backend in header |

## Decision

`ISOLATED`

UI debt baseline: **8**. Backend PMI debt remains **1557**. PMI-X may open. Ready/Kernel remain parked.
