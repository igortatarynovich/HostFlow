# PMI-B Inventory — Boundary isolation

**Status:** CLOSED with PMI-B PASS (2026-09-16)  
**Authority debt after cutover:** `module_isolation_pmi1_debt.json` (**1746** edges; was 1799 @ PMI-R / 2006 @ PMI-1)  
**Card:** [`docs/modules/boundary/module_isolation_card.md`](../../modules/boundary/module_isolation_card.md)  
**Does not:** rewrite Ready / dual-preflight / Kernel / PEM-1 / Employment Admit / EXC-PMI-R-FUNNEL

---

## Charter (narrow)

Boundary accepts Recruitment **public** output, records handoff/traceability, and publishes Ready-for-Employment **package** input for Employment. It is not a central orchestrator of Ready, Admit, Documents, or Workforce.

## Measured (at PMI-B open)

| Bucket | Count |
|--------|------:|
| Boundary-owned files | 9 |
| Debt inbound → boundary | 65 |
| of which Employment | 27 |
| of which Recruitment | 19 |
| Debt outbound boundary → | 38 |
| Named foreign → Boundary internals | 53 |

## Measured (at PMI-B close)

| Bucket | Count |
|--------|------:|
| Boundary-owned files | 15 (incl. `modules/boundary/public`) |
| Debt edges | **1746** (−53 vs PMI-R) |
| Named foreign → Boundary non-public | **0** |
| EXC-PMI-R-FUNNEL | preserved (Recruitment allowlist still 69) |

## Public surface

| Module | Role |
|--------|------|
| `public.ready` | `ready_for_employment.v1` validate/manifest |
| `public.handoff` | tenant/handoff query helpers |
| `public.models` | `CandidateHandoff`, `CandidateHandoffSnapshot` |
| `public.emit` | HR-lane emit helper |
| `public.dto` | `HandoffOut` |

## Explicit non-goals

- Owning Recruitment Ready composition  
- Owning Employment Admit / start_allowed  
- Clearing EXC-PMI-R-FUNNEL (belongs to PMI-E)  
- Publishing Employment/Documents facades (PMI-E / PMI-D)
