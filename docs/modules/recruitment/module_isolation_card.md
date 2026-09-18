# Recruitment Isolation Card

Status: ISOLATED  
Date: 2026-09-16  
Program: [`platform-modularization-isolation-cutover.md`](../../specs/tasks/platform-modularization-isolation-cutover.md)  
Inventory: [`pmi-r-recruitment-isolation-inventory.md`](../../specs/tasks/pmi-r-recruitment-isolation-inventory.md)

A row is **CLOSED** only with a path to machine evidence (test, scanner, or published contract module). Prose alone is **OPEN**.

## Module

Name: `Recruitment`  
Owner: Recruitment module (runtime)  
Runtime roots: `backend/app/modules/recruitment/**`, `backend/app/modules/applications/**`, `backend/app/modules/vacancies/**`, candidate/vacancy/funnel API+models prefixes in `module_isolation_owners.json` · `hostflow-frontend/src/modules/{recruitment,candidates,candidate-card,pipeline}`

## Isolation rows

| # | Row | Status | Evidence |
|---|-----|--------|----------|
| 1 | Owner defined | CLOSED | `module_isolation_owners.json` recruitment prefixes; map spine_file_counts.recruitment=140; residual recruitment-ish left UNASSIGNED only when ownership is ambiguous (intake/employment bridge) — see inventory |
| 2 | Public contract defined | CLOSED | `backend/app/modules/recruitment/public/` (`access`, `application`, `assignment`, `candidate`, `candidate_repo`, `evidence`, `funnel`, `models`, `pipeline`, `ready`, `write_guard`); registered in `module_isolation_public_contracts.json` |
| 3 | Policy authorities defined (one write each) | CLOSED | Table below — Ready classified as Recruitment policy authority; **not rewritten** (parked) |
| 4 | Internal state hidden | CLOSED | Spine Boundary/Employment/Documents/Workforce → Recruitment via `recruitment.public.*` only (spine foreign internals = **0**). Non-spine residual = shrink-only debt (≤63), not a spine reopen |
| 5 | Cross-module dependencies enumerated | CLOSED | Outbound: platform public (`auth`/`db`/`core`); Documents/Boundary via their surfaces; non-spine residual allowlisted |
| 6 | UI surface defined | CLOSED | Owned compositions: `hostflow-frontend/src/modules/{recruitment,candidates,candidate-card,pipeline}`; display Recruitment verdicts via platform design-system (PMI-UI) |
| 7 | Legacy leaks eliminated or isolated | CLOSED | Debt path recorded; EXC-PMI-R-FUNNEL **CLOSED @ PMI-E**; remaining non-spine edges = registered shrink-only debt (not active spine exceptions) |
| 8 | Boundary enforcement works (CI) | CLOSED | `check_recruitment_isolation.py` + PMI-X joint exit |

## Public process contracts

| Contract id | Direction | Neighbours may |
|-------------|-----------|----------------|
| `recruitment.ready.v1` | out | read Ready/Transfer **verdict** via `public.ready` (not R5/slots/confirmations) |
| `recruitment.application.v1` | out | handoff application get/status normalize via `public.application` |
| `recruitment.access.v1` | out | ACL / ensure_candidate_access via `public.access` |
| `recruitment.write_guard.v1` | out | handoff lock / agency write guard via `public.write_guard` |
| `recruitment.models.v1` | out | read ORM types Candidate/Vacancy/RecruitmentApplication via `public.models` |
| `recruitment.evidence.v1` | out | evidence/checklist/lifecycle helpers via `public.evidence` |

## Policy authorities (write)

| Policy / fact / state | Write owner | Read contract |
|-----------------------|-------------|----------------|
| Ready / Transfer permission (leave Recruitment) | Recruitment | `recruitment.ready.v1` |
| R5 / slots / confirmations / package layers | Recruitment (internal) | none — not published |
| Pipeline override / hiring gates | Recruitment | settings API / `public.pipeline` where needed |
| Candidate assignment / funnel binding | Recruitment | `public.assignment` / `public.funnel` |
| Recruitment application status | Recruitment | `public.application` |
| Handoff lock write-guard flags | Recruitment | `public.write_guard` |

## Allowed dependencies

| From | To | Via |
|------|----|-----|
| Boundary / Employment / Documents / Workforce | Recruitment | `backend/app/modules/recruitment/public/**` only |
| Recruitment | Platform session/persistence | `backend/app/auth`, `db/deps\|session\|base`, `core` (platform public contracts) |
| Integrations (leads) | Recruitment | prefer public; residual non-spine = shrink-only debt |

## Legacy leaks

| Leak | Registry id | Owner | Disposition |
|------|-------------|-------|-------------|
| Employment HR funnel ↔ Funnel×6 | EXC-PMI-R-FUNNEL | Employment | **CLOSED @ PMI-E** |
| Non-spine → Recruitment non-public (allowlist ≤63) | DEBT-PMI-R-NONSPINE | acquisition/comms/integrations/platform/sales | shrink-only; **not** an active spine exception (PMI-X) |

Allowlist file: `scripts/architecture/recruitment_isolation_boundary_allowlist.txt` (shrink-only; spine owners = **0**).

## UI surface

Primitives: platform design-system (`PMI-UI`). Module compositions display Recruitment verdicts; must not recompute Ready.

## Decision

`ISOLATED`

Spine foreign→Recruitment internals = **0**. Non-spine residual debt ≤63 (shrink-only). Backend program debt after PMI-W: **1557**.
