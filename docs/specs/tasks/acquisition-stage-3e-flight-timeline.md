# Acquisition Stage 3E — Flight Timeline & automation events

**Status:** Active (Product Track kickoff)  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §14 slice **3E**  
**Parents:** Epic P / 3D ✅ · R3.5 Flights dispatch ✅ · Forms Sprint 1–6 ✅  
**Branch (proposed):** `feat/acquisition-stage-3e-flight-timeline`

> Closes the **V1 vertical** (3A→3E): operators can see and act on Flight history, not only attribution tables.  
> **Not** C2.4. **Not** full multi-Flight UX / Template catalog (V2).

---

## Why now

Communication foundation (C0–C2.2, C2.3 implemented) is mature enough for daily ops.  
The next product value jump is **Flight Runtime** — manage inbound advertising waves and lead flow end-to-end.

```text
Campaign → Flight → Endpoint → Submission → Result → Outcome → KPI
                 ↑
            Timeline (3E) makes this operable day-to-day
```

---

## Product Track vs Engineering Track

| Track | Work | Blocks Product? |
|-------|------|-----------------|
| **Product** (this slice) | Flight Timeline, events for Automations, operator-facing Flight Runtime | — |
| **Engineering** | Full-repo pytest debt, #127 CI-unblock polish, C2.3 merge rebase | **No** — unless clean deploy / Alembic / new module bootstrap breaks |

C2.4 Scheduling remains **frozen**. C2.3 stays implementation-complete; merge when Engineering Track can land without stopping Product.

---

## In scope (3E)

1. **Flight Timeline** — ordered events for a Flight (and roll-up readable on Campaign): routing, results, outcome transitions, spend/lead milestones already implied by 3D.  
2. **Automation events** — emit platform events suitable for Automation Engine consumption (full Automation Campaigns later).  
3. **Operator read surfaces** — thin API + minimal UI to inspect a Flight’s runtime (not Meta Ads Manager; not multi-wave compare).  
4. Capability isolation — Acquisition owns timeline; no Recruitment/Sales ORM ownership reverse.

## Out of scope

- Multi-Flight UX / wave compare (V2)  
- CampaignTemplate catalog  
- Forms Builder expansion  
- C2.4 Scheduling  
- Fixing the 657 base-known integration pytest failures (Engineering Track)  
- Weakening product contract tests for Acquisition

---

## Definition of Done (draft — refine in PR-1)

- [ ] Timeline events persisted and queryable per Flight (Campaign roll-up defined)  
- [ ] Events cover the V1 chain milestones (at least: flight active, submission routed, result attributed, outcome progress)  
- [ ] Automation-facing event emission documented + contract-tested  
- [ ] Thin operator UI or equivalent read API usable for daily Flight inspection  
- [ ] Acquisition contract suites green; no new SPA `/app` literals; no cross-module ownership breaks  
- [ ] ADR-024 3E marked DONE; V1 vertical closed

---

## Locked order (implementation)

```text
1. Domain timeline model + append-only write path
2. Emit from existing 3C/3D call sites (no second pipeline)
3. Read API (Flight → Campaign roll-up)
4. Thin UI last
```

---

## History

- 2026-07-21: Opened as Product Track after strategy split — do not block Flights on legacy full-repo pytest; C2.4 frozen; Engineering Track owns CI debt.
