# PMI-D Inventory — Documents isolation

**Status:** CLOSED with PMI-D PASS (2026-09-16)  
**Debt after cutover:** **1612** (was 1705 @ PMI-E / 2006 @ PMI-1)  
**Card:** [`docs/modules/documents/module_isolation_card.md`](../../modules/documents/module_isolation_card.md)  
**Does not:** rewrite DQC / Contract / BHP / Ready / Admit / Kernel

---

## Charter

Documents owns evidence and document lifecycle. It publishes **facts** through `documents.public.*`. It does **not** decide Recruitment Ready, Employment Admit, or Workforce lifecycle. Neighbours interpret evidence with their own policy authorities.

## Measured (open → close)

| Bucket | Open | Close |
|--------|-----:|------:|
| Named foreign→Documents internals | 93 | **0** |
| Boundary→Documents (EXC-PMI-B-DOC) | 5 | **0** |
| Debt edges | 1705 | **1612** (−93) |
| Documents isolation allowlist | — | **0** |

## Public surface

| Module | Role |
|--------|------|
| `public.models` | `Document` |
| `public.types` | canonical/type/resolver/catalog facts |
| `public.evidence` | delivery contracts, data contracts, runtime eval, expiry |
| `public.crud` | list/check candidate documents |
| `public.open` | open/stream for approval/Workforce |
| `public.storage` | upload path helpers |
| `public.summary` | owner summary / packs / checklist |

## Explicit non-goals

- Fixing DQC / Contract / BHP evidence semantics  
- Becoming a hidden policy engine for Ready/Admit  
- Kernel / Ready / PMI-W scope
