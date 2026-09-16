# <Module> Isolation Card

Status: open  
Date: YYYY-MM-DD  
Program: [`platform-modularization-isolation-cutover.md`](../../specs/tasks/platform-modularization-isolation-cutover.md)

A row is **CLOSED** only with a path to machine evidence (test, scanner, or published contract module). Prose alone is **OPEN**.

## Module

Name: `<Module>`  
Owner: `<Team/Owner>`  
Runtime roots: `<backend/app/... prefixes>` · `<hostflow-frontend/src/... prefixes>`

## Isolation rows

| # | Row | Status | Evidence |
|---|-----|--------|----------|
| 1 | Owner defined | OPEN | |
| 2 | Public contract defined | OPEN | |
| 3 | Policy authorities defined (one write each) | OPEN | |
| 4 | Internal state hidden | OPEN | |
| 5 | Cross-module dependencies enumerated | OPEN | |
| 6 | UI surface defined | OPEN | |
| 7 | Legacy leaks eliminated or isolated (owner + expiry) | OPEN | |
| 8 | Boundary enforcement works (CI) | OPEN | |

## Public process contracts

| Contract id | Direction | Neighbours may |
|-------------|---------|----------------|
| `<id.vN>` | in / out | read verdict / emit / command |

## Policy authorities (write)

| Policy / fact / state | Write owner | Read contract |
|-----------------------|-------------|----------------|
| | | |

## Allowed dependencies

| From | To | Via |
|------|----|-----|
| | | |

## Legacy leaks

| Leak | Registry id | Owner | Expiry / cutover slice |
|------|-------------|-------|------------------------|
| | | | |

## UI surface

Primitives used (platform only — no parallel kit where a platform primitive exists):  
Module compositions:  

## Decision

`ISOLATED` | `OPEN` | `STOP`
