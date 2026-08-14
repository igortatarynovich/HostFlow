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
| **Communication** | ✅ | ✅ (C1) | ✅ (C2.1–C2.3; C2.4 frozen) | ✅ `PASS_WITH_CONSTRAINTS` |
| **Acquisition** | ✅ | ✅ | 🔄 residual | ⏳ |
| **Forms** | ✅ Phase C C1–C6 | ⏳ | ⏳ | ⏳ |
| **Entity Workspace** | 🔄 Phase D D1 | ⏳ | ⏳ | ⏳ |
| **Documents** | 🔄 | ⏳ | ⏳ | ⏳ |
| **Billing** | ⏳ | ⏳ | ⏳ | ⏳ |

Notes:

- Communication Foundation = C0.0–C0.3 ([foundation doc](communication-platform-foundation.md)).  
- Communication Workspace = C1 Inbox Workspace ✅ (C1.1–C1.3; closed 2026-07-21 — [evidence](../gates/epic-c-complete-gate.md#c1-close-out-evidence-2026-07-21)).
- Communication Automation = C2.1–C2.3 ✅ (Intent-only; capability isolation); **C2.4 Scheduling frozen** (gate residual R1).
- Communication Complete = [Epic C Complete Gate](../gates/epic-c-complete-gate.md) **PASS_WITH_CONSTRAINTS** (2026-08-03) → **Epic C — complete**.  
- **A2 Platform Governance Review** = [PASS_WITH_CONSTRAINTS](../gates/platform-governance-review-a2.md) (2026-08-03). Catalog Notifications↔Communication → Architecture RFC (A2-F1).  
- Acquisition Automation residual = Stage 5 settings / R6 deferred — **not** the active slice. Phase B Meta / slice 3–4 ✅ ([#222](https://github.com/igortatarynovich/HostFlow/pull/222) · [#224](https://github.com/igortatarynovich/HostFlow/pull/224) · [#238](https://github.com/igortatarynovich/HostFlow/pull/238)).  
- Forms: Sprint 1–6 / Builder MVP + Phase C C1–C6 ✅ ([#250](https://github.com/igortatarynovich/HostFlow/pull/250)) — **Foundation ✅** (production serve→execute bound). P3–P5 stay locked.  
- **Entity Workspace:** Phase D D1 ✅ ([contract seal](../tasks/entity-workspace-d1-contract-seal.md)). Shell adapter on tip; public chrome SoT path = `components/ui/EntityWorkspace`; Universal composition SoT not sealed yet ([A2-F7](../gates/platform-governance-review-a2.md)). Foundation 🔄 until D ladder closes composition contracts.  
- Documents Foundation in progress = platform lifecycle contracts still consolidating (roadmap Phase E).

AI remains sequenced later; it appears in the matrix when it becomes a platform SoT under active delivery.

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
