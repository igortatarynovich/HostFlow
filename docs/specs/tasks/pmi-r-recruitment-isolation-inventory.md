# PMI-R Inventory — Recruitment isolation

**Status:** CLOSED with PMI-R PASS (2026-09-16)  
**Authority debt after cutover:** `module_isolation_pmi1_debt.json` (**1799** edges; was 2006 @ PMI-1)  
**Card:** [`docs/modules/recruitment/module_isolation_card.md`](../../modules/recruitment/module_isolation_card.md)  
**Does not:** rewrite Ready / dual-preflight / Kernel / PEM-1

---

## Measured (at PMI-R open)

| Bucket | Count |
|--------|------:|
| Files owned `recruitment` | 73 |
| UNASSIGNED recruitment-ish (heuristic) | 63 |
| Debt inbound → recruitment (all) | 92 |
| Debt inbound from named modules | ~36 (excl. UNASSIGNED) |
| Debt outbound recruitment → | 365 |
| of which → UNASSIGNED | 285 (mostly false: models/services still UNASSIGNED) |
| of which → named modules | 80 |

## Measured (at PMI-R close)

| Bucket | Count |
|--------|------:|
| Files owned `recruitment` | 140 |
| Platform-owned (auth/db/core + prior) | 202 |
| Debt edges | **1799** (−207 vs PMI-1) |
| Foreign→Recruitment non-public (allowlist) | 69 |
| Spine→Recruitment internals remaining | 6 (Employment funnel EXC) |

## Finding

Most “Recruitment → UNASSIGNED” edges were **map incompleteness**, not true foreign coupling. Completing owner prefixes (Row 1) revealed hidden UNASSIGNED↔UNASSIGNED edges; PMI-1 freeze admits those only as **ownership reveals**, then requires net debt shrink.

## Spine inbound sealed (Row 4)

| From | Was | Now |
|------|-----|-----|
| boundary handoff / ready emit | application/lifecycle/write_guard/package internals | `recruitment.public.*` |
| documents / workforce / handoffs API | `candidates.acl`, write_guard, Candidate ORM | `public.access` / `write_guard` / `models` / `evidence` |
| employment `hr_documents_queue` | pipeline overrides | `public.pipeline` |
| platform PE | TransferPolicyResolver | `public.ready` / `funnel` |

## Ready / Transfer (Row 3 — classify only)

| Concern | Classification |
|---------|----------------|
| Ready / Transfer permission | **Recruitment policy authority** (process contract: Ready verdict) |
| R5 / slots / confirmations / package layers | **Recruitment internal policy machinery** — not topology; **not rewritten** in PMI-R |
| `transfer_policy_resolver` | Internal evaluator; neighbours consume **public Ready verdict only** |

## Out of PMI-R rewrite

Integrations/leads deep coupling, sales convert paths, full UI redesign — classified as legacy leaks with owner+expiry. PMI-B opens next.
