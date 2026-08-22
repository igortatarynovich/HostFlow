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
| **Entity Workspace** | 🔄 Phase D D1–D9 | ⏳ | ⏳ | ⏳ |
| **Documents** | 🔄 Phase E E2 feat locked | ⏳ | ⏳ | ⏳ |
| **Billing** | ⏳ | ⏳ | ⏳ | ⏳ |

Notes:

- Communication Foundation = C0.0–C0.3 ([foundation doc](communication-platform-foundation.md)).  
- Communication Workspace = C1 Inbox Workspace ✅ (C1.1–C1.3; closed 2026-07-21 — [evidence](../gates/epic-c-complete-gate.md#c1-close-out-evidence-2026-07-21)).
- Communication Automation = C2.1–C2.3 ✅ (Intent-only; capability isolation); **C2.4 Scheduling frozen** (gate residual R1).
- Communication Complete = [Epic C Complete Gate](../gates/epic-c-complete-gate.md) **PASS_WITH_CONSTRAINTS** (2026-08-03) → **Epic C — complete**.  
- **A2 Platform Governance Review** = [PASS_WITH_CONSTRAINTS](../gates/platform-governance-review-a2.md) (2026-08-03). Catalog Notifications↔Communication → Architecture RFC (A2-F1).  
- Acquisition Automation residual = Stage 5 settings / R6 deferred — **not** the active slice. Phase B Meta / slice 3–4 ✅ ([#222](https://github.com/igortatarynovich/HostFlow/pull/222) · [#224](https://github.com/igortatarynovich/HostFlow/pull/224) · [#238](https://github.com/igortatarynovich/HostFlow/pull/238)).  
- Forms: Sprint 1–6 / Builder MVP + Phase C C1–C6 ✅ ([#250](https://github.com/igortatarynovich/HostFlow/pull/250)) — **Foundation ✅** (production serve→execute bound). P3–P5 stay locked.  
- **Entity Workspace:** Phase D D1–D9 brief-complete ([Services order cutover](../tasks/entity-workspace-d9-services-order-cutover.md) · [#268](https://github.com/igortatarynovich/HostFlow/pull/268)); **goal-incomplete** vs original Entity Shell ([audit](../gates/platform-scope-completeness-audit.md)). Shell + D2 surfaces + named consumer binds exist; Capability Host Contract typed + Application runtime host exist ([#273](https://github.com/igortatarynovich/HostFlow/pull/273)). G4 PASS on Recruitment Application. G1 **PASS_WITH_CONSTRAINTS** (no Entity host runtime). Product Track = [host runtime-equivalence](../tasks/workspace-capability-host-runtime-equivalence.md). D2 `documents` catalog unlock = [E2](../tasks/documents-platform-e2-public-contract.md) (consumers unbound; feat locked until WCP **COMPLETE**). Foundation 🔄 ([A2-F7](../gates/platform-governance-review-a2.md)). Do not mark Complete without [Goal Completion Gate](../gates/goal-completion-gate.md).  
- **Documents:** Phase E E2 brief ✅ ([public contract / D2 catalog enable](../tasks/documents-platform-e2-public-contract.md) [#271](https://github.com/igortatarynovich/HostFlow/pull/271)); **feat locked** until Workspace Capability program **COMPLETE** (G4 PASS does not unlock). E1 ✅ ([#270](https://github.com/igortatarynovich/HostFlow/pull/270)). Foundation stays 🔄 ([A2-F8](../gates/platform-governance-review-a2.md)). D2 `documents` catalog unlock is E2; D3–D9 unbound. Not OCR / not Hub UI rebuild.  
- **Workspace Capability Platform:** not a new Catalog platform row. Capability Host Contract between hosts and capability owners. Does not collapse Entity and Application. G1–G5 [PASS_WITH_CONSTRAINTS](../gates/workspace-capability-platform-g1-g5-closeout.md). Does not claim Entity Foundation ✅ until program COMPLETE.

AI remains sequenced later; it appears in the matrix when it becomes a platform SoT under active delivery.

---

## Rules

1. Update this matrix when a stage status changes (same PR that closes the stage, or the Complete Gate PR).  
2. Do **not** mark **Complete** without the platform’s Complete Gate **and** the [Goal Completion Gate](../gates/goal-completion-gate.md) (original problem vs substituted brief). Entity / Application workspace Complete additionally requires the [Recruitment Application proof](../tasks/workspace-capability-platform-completion.md#original-goal--completion-proof), not a UI-component kit and not Candidate-as-proof.  
3. Epic status ≠ maturity: e.g. Communication may be Foundation ✅ while Epic C is still open.  
4. Boundary rule unchanged: platforms do not depend on modules; modules use public contracts/adapters.

---

## Refs

- Sequencing: [platform-completion-roadmap.md](platform-completion-roadmap.md)  
- Near-term slices: [sales-to-comms-sequential-queue.md](../tasks/sales-to-comms-sequential-queue.md)  
- Goal Completion Gate: [goal-completion-gate.md](../gates/goal-completion-gate.md)  
- WCP G1–G5 close-out: [workspace-capability-platform-g1-g5-closeout.md](../gates/workspace-capability-platform-g1-g5-closeout.md)  
- Scope audit: [platform-scope-completeness-audit.md](../gates/platform-scope-completeness-audit.md)  
- Workspace Capability Platform Completion: [workspace-capability-platform-completion.md](../tasks/workspace-capability-platform-completion.md)  
- Host runtime-equivalence: [workspace-capability-host-runtime-equivalence.md](../tasks/workspace-capability-host-runtime-equivalence.md)  
- Communication Foundation: [communication-platform-foundation.md](communication-platform-foundation.md)  
