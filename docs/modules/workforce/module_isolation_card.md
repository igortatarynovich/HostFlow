# Workforce Isolation Card

Status: ISOLATED  
Date: 2026-09-16  
Program: [`platform-modularization-isolation-cutover.md`](../../specs/tasks/platform-modularization-isolation-cutover.md)  
Inventory: [`pmi-w-workforce-isolation-inventory.md`](../../specs/tasks/pmi-w-workforce-isolation-inventory.md)

## Module

Name: `Workforce`  
Owner: Workforce (post-start employment continuity)  
Runtime roots: `backend/app/modules/workforce/**`, `services/workforce_*`, `models/workforce_*`, workforce APIs  

**Owns:** post-start employee continuity, HR review/ops state on Workforce tables, eligibility journey after start, ZUS/workspace tasks  

**Does not own / must not reconstruct:** Recruitment Ready, RFE package semantics, Employment Admit/Start policy, Documents evidence policy  

**Input contract:** Started Employee (`employment_started.v1` / `employment.public.commands.confirm_employment_started_for_handoff`) with stable identity — accepted via `workforce.public.started` / `employees` continuity helpers  

**Not PMI-W:** continuous Kernel witness Started→Workforce (after PMI-X)

## Isolation rows

| # | Row | Status | Evidence |
|---|-----|--------|----------|
| 1 | Owner defined | CLOSED | `module_isolation_owners.json` + `modules/workforce` |
| 2 | Public contract defined | CLOSED | `workforce.public.{started,employees,models,hr_review,ops}` |
| 3 | Policy authorities defined | CLOSED | Table — post-start policies Workforce-owned; Started Employee is Employment output |
| 4 | Internal state hidden | CLOSED | Named foreign→Workforce non-public = **0** |
| 5 | Cross-module dependencies enumerated | CLOSED | Employment writes only via `workforce.public.*`; consumes Started Employee from Employment public |
| 6 | UI surface defined | CLOSED | Workforce API/routers — display post-start state; must not recompute Ready/Admit |
| 7 | Legacy leaks eliminated or isolated | CLOSED | Debt **1612→1557**; Employment→Workforce internals sealed |
| 8 | Boundary enforcement works (CI) | CLOSED | `check_workforce_isolation.py` + gate test |

## Public process contracts

| Contract id | Direction | Neighbours may |
|-------------|-----------|----------------|
| `workforce.started.v1` | in | accept Started Employee continuity (`public.started` / `employees`) |
| `workforce.models.v1` | out | ORM types for Employment continuity rows |
| `workforce.hr_review.v1` | out | review ensure/approve queries |
| `workforce.ops.v1` | out | operational context, eligibility journey, ZUS hooks |

## Policy authorities (write)

| Policy / fact / state | Write owner | Read contract |
|-----------------------|-------------|----------------|
| WorkforceEmployee / post-start profiles | Workforce | `workforce.public.*` |
| HR review / verification rows on Workforce tables | Workforce | `public.hr_review` / `models` |
| Started Employee fact | Employment | `employment.public.commands` |
| Ready / RFE / Admit | Recruitment / Boundary / Employment | not Workforce |

## Allowed dependencies

| From | To | Via |
|------|----|-----|
| Employment / Boundary / Documents / Recruitment | Workforce | `workforce.public.**` only |
| Workforce | Employment Started | `employment.public.commands` (started confirm) |
| Workforce | Documents evidence | `documents.public.*` |

## Legacy leaks

None remaining for named foreign→Workforce internals (allowlist **0**).

## UI surface

Workforce routers/modules — post-start compositions only; no parallel Ready/Admit UI language (PMI-UI PASS).

## Decision

`ISOLATED`

Debt baseline after PMI-W: **1557** (PMI-D was 1612; PMI-1 was 2006). PMI-UI may open. Ready/Kernel remain parked.
