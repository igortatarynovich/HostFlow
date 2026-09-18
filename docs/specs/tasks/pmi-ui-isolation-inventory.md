# PMI-UI Inventory — Design system + spine UI isolation

**Status:** CLOSED with PMI-UI PASS (2026-09-16)  
**UI debt (allowlist):** **8** (shrink-only; not backend PMI-1 debt)  
**Card:** [`docs/modules/ui/module_isolation_card.md`](../../modules/ui/module_isolation_card.md)  
**Does not:** rewrite all HostFlow frontend; Kernel; Ready composition; dual preflight; PEM-1

---

## Charter (four DoD levels)

1. **Platform primitives** — one authority set (inventory → choose, never invent a third).  
2. **Module compositions** — spine modules own screens; assemble from platform primitives.  
3. **Decision ownership** — UI displays backend verdict/action contracts; no multi-payload domain reconstruction.  
4. **Enforcement** — CI forbids new parallel primitives, legacy control imports growth, cross-spine composition leaks, new decision reconstructors.

Target dependency:

`Design System primitives → Module-owned UI composition → Public module contracts`

## Authority (chosen, not invented)

| Category | Authority |
|----------|-----------|
| Status / verdict | `components/ui/StatusBadge` + `platform/design-system/NextActionBadge` |
| Actions | `components/ui/Button` + `.btn-*` CSS |
| Forms | Combobox / MultiCombobox / Checkbox / `.input` CSS |
| Layout / shell | `PageShell`, nav Sidebar/Topbar/PageHeader |
| Tables / rails | EntityListShell / DataTable* / `platform/detail-rail` (data-table DetailRail = re-export) |
| Overlays / feedback | `Modal`, `EmptyStatePanel`, `Toast` |
| Public barrel | `platform/design-system` |

Forbidden parallel (imports = debt): `components/controls/{Select,SelectAsync,MultiSelect}`.

## Spine surfaces in scope

Recruitment / Boundary / Employment / Documents / Workforce UI roots listed in `ui_primitive_authority.json`. Remaining frontend = shrink-only debt.

## Measured close

| Bucket | Result |
|--------|--------|
| Documents → candidate `NextActionBadge` | **0** (moved to design-system) |
| Cross-spine documents→recruitment | **0** |
| Parallel Select control imports | **7** (non-spine / legacy, allowlisted) |
| Decision reconstruction legacy | **1** (`buildEmployeeReadinessSummary`) |
| New decision reconstructors | **0** |
| UI isolation allowlist | **8** |

## Decision ownership seal

- Good pattern: `HrHandoffContextSummary` displays backend `why_ready`.  
- Legacy: `buildEmployeeReadinessSummary` remain listed.  
- Seal: `EmployeeReadinessHeader` prefers `hrReview.decision_readiness` (+ recommended next action) for status/CTA.

## Explicit non-goals

- Full frontend rewrite  
- PMI-X program exit / Kernel unpark  
- Ready / dual-preflight / PEM-1
