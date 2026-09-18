# Boundary Isolation Card

Status: ISOLATED  
Date: 2026-09-16  
Program: [`platform-modularization-isolation-cutover.md`](../../specs/tasks/platform-modularization-isolation-cutover.md)  
Inventory: [`pmi-b-boundary-isolation-inventory.md`](../../specs/tasks/pmi-b-boundary-isolation-inventory.md)

## Module

Name: `Boundary`  
Owner: Boundary (handoff / Ready-for-Employment package)  
Runtime roots: `backend/app/modules/boundary/**`, `backend/app/services/handoff*.py`, `ready_for_employment*`, `models/candidate_handoff*`, `api/v1/handoffs.py`  
**Narrow charter:** accept Recruitment public output → handoff/traceability → publish Ready-for-Employment input for Employment.  
**Does not own:** Recruitment Ready, Employment Admit / start_allowed, Documents rules, Workforce lifecycle.

## Isolation rows

| # | Row | Status | Evidence |
|---|-----|--------|----------|
| 1 | Owner defined | CLOSED | `module_isolation_owners.json` boundary prefixes + `modules/boundary`; map spine boundary=15 |
| 2 | Public contract defined | CLOSED | `backend/app/modules/boundary/public/` (`ready`, `handoff`, `models`, `emit`, `dto`); `module_isolation_public_contracts.json` |
| 3 | Policy authorities defined | CLOSED | Table below — Boundary writes handoff/trace + RFE package emit/accept shape only |
| 4 | Internal state hidden | CLOSED | Named foreign→Boundary non-public = **0** (`check_boundary_isolation.py`) |
| 5 | Cross-module dependencies enumerated | CLOSED | Inbound via `boundary.public.*`; outbound Employment/Documents orchestrators = EXC-PMI-B-EMP / EXC-PMI-B-DOC until PMI-E / PMI-D |
| 6 | UI surface defined | CLOSED | No Boundary frontend kit; surface = handoffs API + RFE package DTOs. UI must not invent Admit/Ready |
| 7 | Legacy leaks eliminated or isolated | CLOSED | Debt **1799→1746**; EXC-PMI-R-FUNNEL untouched; outbound exceptions below |
| 8 | Boundary enforcement works (CI) | CLOSED | `check_boundary_isolation.py` + `test_module_isolation_pmi_b_boundary_gate.py` |

## Public process contracts

| Contract id | Direction | Neighbours may |
|-------------|-----------|----------------|
| `ready_for_employment.v1` | in/out | validate/consume RFE package via `public.ready`; emit helpers via `public.emit` |
| `boundary.handoff.v1` | out | query/command handoff helpers via `public.handoff` |
| `boundary.models.v1` | out | `CandidateHandoff` / `CandidateHandoffSnapshot` via `public.models` |
| `boundary.dto.v1` | out | `HandoffOut` via `public.dto` |

## Policy authorities (write)

| Policy / fact / state | Write owner | Read contract |
|-----------------------|-------------|----------------|
| Handoff row + status transitions | Boundary | `boundary.handoff.v1` / API |
| Handoff snapshot / traceability | Boundary | snapshot ACL (internal) + read models for Employment via public models |
| Ready-for-Employment **package** shape | Boundary | `ready_for_employment.v1` |
| Recruitment Ready / Transfer permission | Recruitment | `recruitment.ready.v1` — Boundary does not write |
| Employment Admit / start_allowed | Employment | not Boundary |
| Document evidence rules | Documents | not Boundary |
| Workforce lifecycle | Workforce | not Boundary |

## Allowed dependencies

| From | To | Via |
|------|----|-----|
| Recruitment / Employment / Documents / Workforce / … | Boundary | `backend/app/modules/boundary/public/**` only |
| Boundary | Recruitment | `recruitment.public.*` only (already) |
| Boundary | Employment internals | EXC-PMI-B-EMP (orchestrator calls from handoffs API) → PMI-E |
| Boundary | Documents internals | EXC-PMI-B-DOC (snapshot/emit document reads) → PMI-D |

## Legacy leaks

| Leak | Registry id | Owner | Expiry |
|------|-------------|-------|--------|
| Boundary→Employment orchestrator imports | EXC-PMI-B-EMP | Boundary | **CLOSED @ PMI-E** |
| Boundary→Documents crud/resolvers | EXC-PMI-B-DOC | Boundary | **CLOSED @ PMI-D** |
| UNASSIGNED shell → Boundary internals | DEBT-PMI-B-SHELL | Platform | shrink-only non-spine; inbound allowlist **0** (PMI-X) |
| Employment→Funnel (Recruitment) | EXC-PMI-R-FUNNEL | Employment | **CLOSED @ PMI-E** |

Allowlist (inbound named foreign): `scripts/architecture/boundary_isolation_allowlist.txt` (**0** edges).

## UI surface

No module chrome. Operators use handoffs API / HR inbox consuming `HandoffOut` and RFE package — must not recompute Recruitment Ready or Employment Admit.

## Decision

`ISOLATED`

Debt baseline after PMI-B: **1746** edges (PMI-R was 1799; PMI-1 was 2006). PMI-E may open.
