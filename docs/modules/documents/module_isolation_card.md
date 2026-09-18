# Documents Isolation Card

Status: ISOLATED  
Date: 2026-09-16  
Program: [`platform-modularization-isolation-cutover.md`](../../specs/tasks/platform-modularization-isolation-cutover.md)  
Inventory: [`pmi-d-documents-isolation-inventory.md`](../../specs/tasks/pmi-d-documents-isolation-inventory.md)

## Module

Name: `Documents`  
Owner: Documents (evidence / document lifecycle)  
Runtime roots: `backend/app/modules/documents/**`, `document_hub`, `document_runtime`, `document_types`, `services/document_*`, document APIs  
**Owns:** document identity, type/canonical reference, files, verification/status, validity, evidence views  
**Does not own:** Recruitment Ready, Employment Admit, Workforce lifecycle — neighbours interpret evidence with their own policy authorities

## Isolation rows

| # | Row | Status | Evidence |
|---|-----|--------|----------|
| 1 | Owner defined | CLOSED | `module_isolation_owners.json` documents prefixes |
| 2 | Public contract defined | CLOSED | `backend/app/modules/documents/public/` (`models`, `types`, `evidence`, `crud`, `open`, `storage`, `summary`) |
| 3 | Policy authorities defined | CLOSED | Table — Documents writes evidence facts only; Ready/Admit elsewhere |
| 4 | Internal state hidden | CLOSED | Named foreign→Documents non-public = **0** |
| 5 | Cross-module dependencies enumerated | CLOSED | Inbound via `documents.public.*`; EXC-PMI-B-DOC **closed** |
| 6 | UI surface defined | CLOSED | Documents module UI + APIs; must display evidence facts, not invent Ready/Admit |
| 7 | Legacy leaks eliminated or isolated | CLOSED | Debt **1705→1612**; EXC-PMI-B-DOC closed; DQC/Contract/BHP semantics **not** rewritten |
| 8 | Boundary enforcement works (CI) | CLOSED | `check_documents_isolation.py` + gate test |

## Public process contracts

| Contract id | Direction | Neighbours may |
|-------------|-----------|----------------|
| `documents.types.v1` | out | canonical/type normalize + runtime resolver facts |
| `documents.evidence.v1` | out | Hub/runtime delivery + data contracts + expiry aggregates |
| `documents.crud.v1` | out | list/check candidate documents |
| `documents.open.v1` | out | open/stream URLs for approval/Workforce |
| `documents.models.v1` | out | `Document` ORM type via public |
| `documents.storage.v1` | out | upload path helpers |
| `documents.summary.v1` | out | owner summary / pack / checklist facts |

## Policy authorities (write)

| Policy / fact / state | Write owner | Read contract |
|-----------------------|-------------|----------------|
| Document rows / files / verification / validity | Documents | `documents.public.*` |
| Catalog/canonical type codes | Documents | `public.types` |
| Recruitment Ready | Recruitment | not Documents |
| Employment Admit | Employment | consumes evidence facts only |
| Workforce lifecycle | Workforce | consumes open/evidence facts only |

## Allowed dependencies

| From | To | Via |
|------|----|-----|
| Recruitment / Boundary / Employment / Workforce / Platform / … | Documents | `documents.public.**` only |

## Legacy leaks

| Leak | Registry id | Status |
|------|-------------|--------|
| Boundary→Documents crud/open/resolver | EXC-PMI-B-DOC | **CLOSED** (PMI-D) |

Allowlist: `scripts/architecture/documents_isolation_allowlist.txt` (**0** edges).

## UI surface

Documents module compositions — evidence facts only; policy interpretation stays in owning modules.

## Decision

`ISOLATED`

Debt baseline after PMI-D: **1612** (PMI-E was 1705; PMI-1 was 2006). PMI-W may open. Ready/Kernel remain parked.
