# PMI-W Inventory — Workforce isolation

**Status:** CLOSED with PMI-W PASS (2026-09-16)  
**Debt after cutover:** **1557** (was 1612 @ PMI-D / 2006 @ PMI-1)  
**Card:** [`docs/modules/workforce/module_isolation_card.md`](../../modules/workforce/module_isolation_card.md)  
**Does not:** Kernel Started→Workforce continuous witness; Ready/Admit/evidence reconstruction; PMI-UI

---

## Charter (ADR-042 proof gap — architectural, not Kernel)

Employment ends at public **Started Employee**. Workforce begins by accepting that continuity. PMI-W proves neighbours can no longer import Workforce internals and that Employment cannot write Workforce state except through `workforce.public.*`. It does **not** mint a Full Spine Kernel proof.

## Measured (open → close)

| Bucket | Open | Close |
|--------|-----:|------:|
| Named foreign→Workforce internals | 49 | **0** |
| Employment→Workforce internals | 41 | **0** (via public) |
| Debt edges | 1612 | **1557** (−55) |
| Workforce isolation allowlist | — | **0** |

## Public surface

| Module | Role |
|--------|------|
| `public.started` | Started Employee continuity helpers |
| `public.employees` | full proxy of employee service for neighbours |
| `public.models` | Workforce ORM types |
| `public.hr_review` | review ensure/approve |
| `public.ops` | operational context / eligibility / ZUS |

## Explicit non-goals

- P5→P6 Kernel continuous witness  
- Rewriting Ready / dual-preflight / PEM-1  
- PMI-UI design-system enforcement
