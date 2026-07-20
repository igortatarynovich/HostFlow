# Epic C Complete Gate

**Status:** Queued (after C2; before Platform Governance Review)  
**Type:** Mandatory merge / capability gate (not a product feature)  
**Parents:** [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Communication Platform Foundation](../architecture/communication-platform-foundation.md) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md)

> Final check that Communication is a **single platform capability**.  
> Passing this gate is the only allowed transition from  
> **Communication Platform Foundation — complete** → **Epic C — complete**.

---

## Sequence (locked)

```text
C1 Inbox Workspace
  → C2 Templates, Automations & Campaigns
  → Epic C Complete Gate   ← this document
  → A2 Platform Governance Review
  → Acquisition (Stage 3 + Meta)
  → Forms → Entity Workspace → Documents → Billing → AI
```

Do **not** skip this gate and mark Epic C complete after C2 alone.

---

## Checklist

| # | Check |
|---|--------|
| 1 | One SoT for Communication |
| 2 | No legacy senders and no legacy inbound paths |
| 3 | All modules use only the public Communication Contract via adapters |
| 4 | No platform → module dependencies |
| 5 | All messages (outbound / inbound) pass through the unified pipeline |
| 6 | Callbacks, retries, diagnostics, and Inbox share one data model |
| 7 | Templates, Automations, and Campaigns use Intent Registry — not private rule engines |
| 8 | Documentation (ADR, Canon, Catalog) matches implementation |

---

## Status transition (only after PASS)

| Before gate | After gate PASS |
|-------------|-----------------|
| Communication Platform Foundation — complete | **Epic C — complete** |

Foundation remains historically true (C0.0–C0.3 closed earlier).  
Epic C complete means Foundation + C1 + C2 + this gate.

---

## Relation to A2 Governance

**Epic C Complete Gate** = Communication capability closed as one platform.  
**A2 Platform Governance Review** = cross-platform check that the boundary rule  
(platforms independent; modules only via public contracts/adapters) was not violated  
during platform growth — not a re-test of “are integrations wired”.

Governance does not replace this gate.

---

## Suggested branch

`docs/epic-c-complete-gate` (checklist + evidence links; no drive-by refactors unless trivial)

## DoD

- [ ] Checklist filled with evidence (paths / PRs / contract tests)  
- [ ] Residual gaps listed with owners or accepted waivers  
- [ ] Status docs updated: Foundation stays complete; **Epic C — complete** set only here  
- [ ] Sequential queue + roadmap point at A2 next  
