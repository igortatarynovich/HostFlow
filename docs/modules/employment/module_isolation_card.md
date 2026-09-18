# Employment Isolation Card

Status: ISOLATED  
Date: 2026-09-16  
Program: [`platform-modularization-isolation-cutover.md`](../../specs/tasks/platform-modularization-isolation-cutover.md)  
Inventory: [`pmi-e-employment-isolation-inventory.md`](../../specs/tasks/pmi-e-employment-isolation-inventory.md)

## Module

Name: `Employment` (HR)  
Owner: Employment  
Runtime roots: `backend/app/modules/employment/**`, `backend/app/services/{hr_,employment_}*`, employment reference contracts, HR APIs  
**Owns:** Formalize / Employee ensure / Admit / Start  
**Does not own:** Recruitment Ready, Boundary handoff topology, Documents Hub storage, Workforce post-start lifecycle

## Isolation rows

| # | Row | Status | Evidence |
|---|-----|--------|----------|
| 1 | Owner defined | CLOSED | `module_isolation_owners.json` + `modules/employment`; map employment files |
| 2 | Public contract defined | CLOSED | `backend/app/modules/employment/public/` (`commands`, `started` via commands, `identity`, `funnel`, `transfer`, `review`, `manifest`, `accept_policy`) |
| 3 | Policy authorities defined | CLOSED | Table — Admit/start_allowed rulesets **internal**; `employment_started.v1` entry = `confirm_employment_started_for_handoff` only |
| 4 | Internal state hidden | CLOSED | Named foreign→Employment non-public = **0** |
| 5 | Cross-module dependencies enumerated | CLOSED | Inbound via `employment.public.*`; Recruitment via `recruitment.public.*`; EXC-PMI-B-DOC remains Boundary→Documents until PMI-D |
| 6 | UI surface defined | CLOSED | HR inbox/dashboard/employments API — display Employment verdicts; must not recompute Ready/Admit rulesets in UI |
| 7 | Legacy leaks eliminated or isolated | CLOSED | Debt **1746→1705**; EXC-PMI-B-EMP **closed**; EXC-PMI-R-FUNNEL (6) **closed** (not renamed); EXC-PMI-B-DOC deferred to PMI-D |
| 8 | Boundary enforcement works (CI) | CLOSED | `check_employment_isolation.py` + gate test |

## Public process contracts

| Contract id | Direction | Neighbours may |
|-------------|-----------|----------------|
| `employment.accept.v1` / formalize / missing / start_allowed **host** | in (from Boundary) | call `public.commands` only — not orchestrator modules |
| `employment_started.v1` | out | `confirm_employment_started_for_handoff` only — not ESO-5 internals |
| `employment.identity.v1` | out | trusted identity reads for Workforce |
| `employment.funnel.v1` | out | HR employee pipeline assign helpers |
| `employment.review.v1` | out | Workforce review/directory helpers (thin later at PMI-W) |

## Policy authorities (write)

| Policy / fact / state | Write owner | Read contract |
|-----------------------|-------------|----------------|
| Formalize / Employee ensure | Employment | `public.commands` |
| Admit / `employment_start_allowed.v1` rulesets | Employment (**internal**) | host evaluate/apply via `public.commands` only |
| Start / `employment_started.v1` fact | Employment | `confirm_employment_started_for_handoff` |
| Ready / Transfer | Recruitment | not Employment |
| RFE package shape | Boundary | `boundary.public.ready` |
| Document Hub storage / aliases | Documents | evidence contracts only (PMI-D) |
| Post-start Workforce | Workforce | Started Employee contract |

## Allowed dependencies

| From | To | Via |
|------|----|-----|
| Boundary / Recruitment / Workforce / Platform | Employment | `employment.public.**` only |
| Employment | Recruitment | `recruitment.public.**` (models/evidence/pipeline) |
| Boundary | Documents | **CLOSED** (was EXC-PMI-B-DOC @ PMI-D) |

## Legacy leaks

| Leak | Registry id | Status |
|------|-------------|--------|
| Boundary→Employment orchestrators | EXC-PMI-B-EMP | **CLOSED** (PMI-E) |
| Employment→Recruitment Funnel×6 | EXC-PMI-R-FUNNEL | **CLOSED** (hr_funnel_types + recruitment.public.models) |
| Boundary→Documents | EXC-PMI-B-DOC | **CLOSED** (PMI-D) |

Allowlist: `scripts/architecture/employment_isolation_allowlist.txt` (**0** edges).

## UI surface

HR inbox / dashboard / candidate employments — consume Employment public commands and read models; do not re-implement Admit composition.

## Decision

`ISOLATED`

Debt baseline after PMI-E: **1705** (PMI-B was 1746). PMI-D may open. Ready/Kernel remain parked.
