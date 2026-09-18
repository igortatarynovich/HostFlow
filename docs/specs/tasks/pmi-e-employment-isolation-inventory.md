# PMI-E Inventory — Employment isolation

**Status:** CLOSED with PMI-E PASS (2026-09-16)  
**Debt after cutover:** **1705** (was 1746 @ PMI-B / 1799 @ PMI-R / 2006 @ PMI-1)  
**Card:** [`docs/modules/employment/module_isolation_card.md`](../../modules/employment/module_isolation_card.md)  
**Does not:** rewrite Admit / Ready / dual-preflight / Kernel / PEM-1; does not clear EXC-PMI-B-DOC

---

## Charter

Employment owns Formalize, Employee ensure, Admit, Start. Neighbours see only `employment.public.*`. Admit rulesets and ESO-5 internals stay private. Boundary passes RFE/handoff contracts via `public.commands` — not orchestrator modules.

## Measured (open → close)

| Bucket | Open | Close |
|--------|-----:|------:|
| Named foreign→Employment internals | 35 | **0** |
| Boundary→Employment (EXC-PMI-B-EMP) | 9 | **0** (public.commands/transfer) |
| EXC-PMI-R-FUNNEL (employment→funnel×6) | 6 | **0** |
| Debt edges | 1746 | **1705** |
| Employment isolation allowlist | — | **0** |

## Public surface

| Module | Role |
|--------|------|
| `public.commands` | accept / formalize / missing / start_allowed host / started confirm / HR accept |
| `public.transfer` | snapshot flatten/enrich for Boundary |
| `public.identity` | trusted identity for Workforce |
| `public.funnel` | HR employee pipeline assign |
| `public.review` | Workforce review/directory (lazy) |
| `public.manifest` / `accept_policy` | PE registration / package field codes |

## Explicit non-goals

- Improving Admit composition (already separated)  
- Publishing `employment_start_allowed` ruleset internals  
- Publishing ESO-5 internals beyond started confirm  
- Clearing Boundary→Documents (PMI-D)  
- Kernel / Ready
