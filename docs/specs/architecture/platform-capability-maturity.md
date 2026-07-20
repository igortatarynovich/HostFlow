# Platform Capability Maturity

**Status:** **NORMATIVE** (L2 operating — platform maturity SoT)  
**Date:** 2026-07-20  
**Trusted base:** `integration/release-product-a-b`  
**Parents:** [L0 Platform Architecture](L0-platform-architecture.md) · [Platform Completion Roadmap](platform-completion-roadmap.md) · [Hierarchy of Truth](../../governance/hierarchy-of-truth.md)

> Tracks **how mature each platform is**, not only which epic is active.  
> This matrix is long-lived: “Foundation complete” and “Epic complete” stay interpretable years later.

---

## Maturity stages (locked)

| Stage | Meaning |
|-------|---------|
| **Foundation** | Canonical SoT, public contracts, unified pipelines, no parallel writers |
| **Workspace** | Primary operator workplace over the platform (queues, cards, actions) |
| **Automation** | Product automation on platform command (templates / rules / campaigns / bulk) |
| **Complete** | Platform epic closed via its Complete Gate (capability + docs match implementation) |

Legend: ✅ done · 🔄 in progress · ⏳ not started

---

## Maturity matrix (current)

| Platform | Foundation | Workspace | Automation | Complete |
|----------|------------|-----------|------------|----------|
| **Communication** | ✅ | 🔄 (C1) | ⏳ (C2) | ⏳ |
| **Acquisition** | ✅ | ✅ | 🔄 | ⏳ |
| **Forms** | ⏳ | ⏳ | ⏳ | ⏳ |
| **Documents** | 🔄 | ⏳ | ⏳ | ⏳ |
| **Billing** | ⏳ | ⏳ | ⏳ | ⏳ |

Notes:

- Communication Foundation = C0.0–C0.3 ([foundation doc](communication-platform-foundation.md)).  
- Communication Workspace = C1 Inbox Workspace (C1.1 ThreadContext ✅ · **C1.2 Workspace Actions** active).  
- Communication Automation = C2 Templates / Automations / Campaigns.  
- Communication Complete = [Epic C Complete Gate](../gates/epic-c-complete-gate.md) PASS → **Epic C — complete**.  
- Acquisition Automation in progress = Stage 3 / Meta / campaign automation remaining work (see roadmap Phase B).  
- Documents Foundation in progress = platform lifecycle contracts still consolidating (roadmap Phase E).

Entity Workspace and AI are sequenced later on the roadmap; they appear in the matrix when they become platform SoTs under active delivery.

---

## Rules

1. Update this matrix when a stage status changes (same PR that closes the stage, or the Complete Gate PR).  
2. Do **not** mark **Complete** without the platform’s Complete Gate.  
3. Epic status ≠ maturity: e.g. Communication may be Foundation ✅ while Epic C is still open.  
4. Boundary rule unchanged: platforms do not depend on modules; modules use public contracts/adapters.

---

## Refs

- Sequencing: [platform-completion-roadmap.md](platform-completion-roadmap.md)  
- Near-term slices: [sales-to-comms-sequential-queue.md](../tasks/sales-to-comms-sequential-queue.md)  
- Communication Foundation: [communication-platform-foundation.md](communication-platform-foundation.md)  
