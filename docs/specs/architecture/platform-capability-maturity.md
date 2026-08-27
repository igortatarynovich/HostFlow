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
| **Documents** | 🔄 Phase E E7 | ⏳ | ⏳ | ⏳ |
| **Billing** | ⏳ | ⏳ | ⏳ | ⏳ |

Notes:

- Communication Foundation = C0.0–C0.3 ([foundation doc](communication-platform-foundation.md)).  
- Communication Workspace = C1 Inbox Workspace ✅ (C1.1–C1.3; closed 2026-07-21 — [evidence](../gates/epic-c-complete-gate.md#c1-close-out-evidence-2026-07-21)).
- Communication Automation = C2.1–C2.3 ✅ (Intent-only; capability isolation); **C2.4 Scheduling frozen** (**Epic C residual R1**, not Reference R1).
- Communication Complete = [Epic C Complete Gate](../gates/epic-c-complete-gate.md) **PASS_WITH_CONSTRAINTS** (2026-08-03) → **Epic C — complete**.  
- **A2 Platform Governance Review** = [PASS_WITH_CONSTRAINTS](../gates/platform-governance-review-a2.md) (2026-08-03). Catalog Notifications↔Communication → Architecture RFC (A2-F1).  
- Acquisition Automation residual = Stage 5 settings / R6 deferred — **not** the active slice. Phase B Meta / slice 3–4 ✅ ([#222](https://github.com/igortatarynovich/HostFlow/pull/222) · [#224](https://github.com/igortatarynovich/HostFlow/pull/224) · [#238](https://github.com/igortatarynovich/HostFlow/pull/238)).  
- Forms: Sprint 1–6 / Builder MVP + Phase C C1–C6 ✅ ([#250](https://github.com/igortatarynovich/HostFlow/pull/250)) — **Foundation ✅** (production serve→execute bound). P3–P5 stay locked.  
- **Entity Workspace:** Phase D D1–D9 brief-complete ([Services order cutover](../tasks/entity-workspace-d9-services-order-cutover.md) · [#268](https://github.com/igortatarynovich/HostFlow/pull/268)); **goal-incomplete** vs original Entity Shell chrome-only ([audit](../gates/platform-scope-completeness-audit.md)). Capability Host Contract is program **COMPLETE** ([record](../gates/workspace-capability-platform-complete.md) · [#274](https://github.com/igortatarynovich/HostFlow/pull/274)): both hosts at runtime; G4 PASS on Recruitment Application; Candidate is the Entity bind, not G4. Product Track = **[RPM-1](../tasks/requirement-policy-management.md)** (brief; feat locked) after E8-eval Gate **PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6` ([brief](../tasks/documents-platform-e8-eval.md)). E8-bind Gate **PASS** [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` ([brief](../tasks/documents-platform-e8-bind.md)). E7 ✅. D2 `documents` catalog unlock = E2 ✅; first consumer bind = E3 (HR employee) ✅; Candidate Document Link = E4 ✅; storage-bridge retirement = E5 ✅; expiry / validity = E6 ✅; document requests = E7 ✅. Foundation 🔄 ([A2-F7](../gates/platform-governance-review-a2.md)). Do not mark Entity Complete without Documents Foundation and remaining migrate-on-touch.  
- **Documents:** Phase E E7 ✅ ([Document Requests](../tasks/documents-platform-e7-document-requests.md); [#287](https://github.com/igortatarynovich/HostFlow/pull/287)). DR1-runtime ✅ ([#313](https://github.com/igortatarynovich/HostFlow/pull/313)). Product Track = **[RPM-1](../tasks/requirement-policy-management.md)** (brief; feat locked) after E8-eval Gate **PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6` ([brief](../tasks/documents-platform-e8-eval.md)). E8-bind Gate **PASS** [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` ([brief](../tasks/documents-platform-e8-bind.md)). Engineering Track = **DONE** ([Reference Identity SoT](../tasks/platform-reference-identity-sot.md); Exit PASS [#298](https://github.com/igortatarynovich/HostFlow/pull/298)). OCR stays locked. E6 ✅ ([#285](https://github.com/igortatarynovich/HostFlow/pull/285)). E5 ✅ ([#282](https://github.com/igortatarynovich/HostFlow/pull/282)). E4 ✅ ([#280](https://github.com/igortatarynovich/HostFlow/pull/280)). E3 ✅ ([#278](https://github.com/igortatarynovich/HostFlow/pull/278)). E2 ✅ ([#276](https://github.com/igortatarynovich/HostFlow/pull/276)). E1 ✅ ([#270](https://github.com/igortatarynovich/HostFlow/pull/270)). Foundation stays 🔄 ([A2-F8](../gates/platform-governance-review-a2.md)). D2 `documents` catalog unlock is E2; first consumer bind is E3 (HR employee). Candidate consume path is E4. `candidate_id` drop is E5. Expiry / validity is E6. Document requests is E7. Canonical type bind is E8-bind ✅ [#321](https://github.com/igortatarynovich/HostFlow/pull/321). D3 / D5–D7 / D9 unbound. Not OCR / not packages / not Hub UI rebuild / not G4 / not Foundation ✅ / not OCR auto-start.  
- **Workspace Capability Platform:** not a new Catalog platform row. Capability Host Contract between hosts and capability owners. Does not collapse Entity and Application. G1–G5 [COMPLETE](../gates/workspace-capability-platform-complete.md). Does not claim Entity Foundation ✅.

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
- WCP COMPLETE: [workspace-capability-platform-complete.md](../gates/workspace-capability-platform-complete.md)  
- Scope audit: [platform-scope-completeness-audit.md](../gates/platform-scope-completeness-audit.md)  
- Workspace Capability Platform Completion: [workspace-capability-platform-completion.md](../tasks/workspace-capability-platform-completion.md)  
- Documents Platform E7: [documents-platform-e7-document-requests.md](../tasks/documents-platform-e7-document-requests.md)
- Entity Field Composition CL0: [entity-field-composition-cl0-contract-seal.md](../tasks/entity-field-composition-cl0-contract-seal.md)
- Reference R1 (Engineering): [platform-reference-identity-sot.md](../tasks/platform-reference-identity-sot.md)
- Lifecycle Identity (LI-1 after CL1): [lifecycle-identity-l0-contract-seal.md](../tasks/lifecycle-identity-l0-contract-seal.md) · [ADR-037](ADR-037-lifecycle-identity-canon.md)
- Documents Platform E6: [documents-platform-e6-document-expiry.md](../tasks/documents-platform-e6-document-expiry.md)
- Documents Platform E5: [documents-platform-e5-candidate-storage-bridge.md](../tasks/documents-platform-e5-candidate-storage-bridge.md)
- Documents Platform E4: [documents-platform-e4-candidate-document-link.md](../tasks/documents-platform-e4-candidate-document-link.md)  
- Documents Platform E3: [documents-platform-e3-first-consumer-bind.md](../tasks/documents-platform-e3-first-consumer-bind.md)  
- Host runtime-equivalence: [workspace-capability-host-runtime-equivalence.md](../tasks/workspace-capability-host-runtime-equivalence.md)  
- Communication Foundation: [communication-platform-foundation.md](communication-platform-foundation.md)  
