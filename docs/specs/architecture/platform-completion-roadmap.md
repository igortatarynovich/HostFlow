# Platform Completion Roadmap (product sequencing)

**Status:** **NORMATIVE** (L2 operating — product/platform sequencing)  
**Date:** 2026-07-20  
**Trusted base:** `integration/release-product-a-b` (fast-forward only)  
**Parents:** [L0 Platform Architecture](L0-platform-architecture.md) · [Hierarchy of Truth](../../governance/hierarchy-of-truth.md) · [Near-term queue](../tasks/sales-to-comms-sequential-queue.md)

> This is **not** an amendment to the frozen L0 constitution.  
> It locks **which platform epics run in which order** so product work does not compete  
> and later modules build on stable contracts.

---

## Why this order

HostFlow is consolidating real platform capabilities (Acquisition, Communication, Forms, Documents, Entity).  
Jumping back into Sales Stage 3 mid–Communication, or building Workspace/AI before Forms/Documents contracts settle, forces rewrites.

**Principle:** platform layer + clear contracts first → product scenarios on top → AI last as a consumer, never a parallel entity model.

**Boundary rule:** platforms do **not** depend on product modules. Integration is only through **public contracts and adapters** (Passport / Manifest / Exposes). Modules consume platforms; they do not own parallel senders, document stores, or form runtimes.

---

## Immediate rule (through Epic C)

**Epic C — complete** (`PASS_WITH_CONSTRAINTS`, 2026-08-03).  
**A2 Platform Governance Review** — **PASS_WITH_CONSTRAINTS** (2026-08-03).  
Locked handoff:

```text
Epic C Complete Gate → A2 PASS_WITH_CONSTRAINTS → Phase B Meta / Stage 3 → …
```

Order **after A2**:

1. **A2 — Platform Governance Review** — ✅ PASS_WITH_CONSTRAINTS ([gate](../gates/platform-governance-review-a2.md))  
2. **Phase B — Acquisition / Stage 3 + Meta** ← **next**  
3. Forms → Entity Workspace → Documents → Billing → AI  

Near-term slice execution remains one-at-a-time per [sequential queue](../tasks/sales-to-comms-sequential-queue.md).

---

## Phase A — Platform Completion (Communication)

### A1. Communication (Epic C)

**Communication Platform Foundation — complete** (after C0.3 / PR #104).  
See [communication-platform-foundation.md](communication-platform-foundation.md).  
**Epic C — complete** via [Epic C Complete Gate](../gates/epic-c-complete-gate.md) **PASS_WITH_CONSTRAINTS** (2026-08-03; C2.4 frozen residual).

| Slice | Focus | Status |
|-------|--------|--------|
| C0.0 Canon & Contracts | Intent-first SoT | ✅ |
| C0.1 / C0.1b Outbound + policy/snapshot | Canon writer path | ✅ |
| C0.2 Inbound Resolver | Linked or explicit unresolved | ✅ (PR #102) |
| C0.3 Delivery Diagnostics | Attempts + canonical diagnostics | ✅ (PR #104) |
| **C1** Communication Inbox Workspace | Thread workplace for managers | ✅ closed 2026-07-21 |
| **C2** Capability epic (Intent-only) | Templates → Automation → Campaigns (C2.4 Schedule frozen) | ✅ C2.1–C2.3 (PR #219) |
| **Epic C Complete Gate** | Single Communication capability check | ✅ **PASS_WITH_CONSTRAINTS** |

**Foundation result:** Intent, Policy, Registry, Sender, Snapshot, Inbound Resolver, G13, unresolved inbound, delivery attempts/diagnostics/retry/callbacks/timeline.  
**Epic C — complete** = Foundation + C1 + C2.1–C2.3 + gate (**not** after C2 alone; C2.4 not required while frozen).

**Refs:** [Foundation](communication-platform-foundation.md) · [C1](../tasks/c1-communication-inbox-workspace.md) · [Epic C Complete Gate](../gates/epic-c-complete-gate.md) · [Epic C0](../tasks/epic-c0-communication-integrity.md) · [C2 epic](../tasks/epic-c2-communication-campaigns.md) · [Canon](../tasks/c0-0-communication-canon.md)

### A1b. Epic C Complete Gate (mandatory)

**Not** a product feature. Final Communication capability gate — see [epic-c-complete-gate.md](../gates/epic-c-complete-gate.md).

Runs **after C2** (C2.4 may remain frozen), **before** A2 Governance.  
Decision 2026-08-03: **PASS_WITH_CONSTRAINTS** → **Epic C — complete**. A2 closed same day.

### A2. Platform Governance Review (L0 gate) ← **PASS_WITH_CONSTRAINTS**

**Not** a product feature. Cross-platform audit **after Epic C — complete**.  
**Decision:** [platform-governance-review-a2.md](../gates/platform-governance-review-a2.md) **PASS_WITH_CONSTRAINTS** (2026-08-03).

Purpose: verify the boundary principle was not violated during platform growth  
(platforms independent; modules integrate only via public contracts/adapters) —  
not a re-validation of Communication wiring (that is the Epic C Complete Gate).

- One SoT per platform (Acquisition, Communication, Documents, Forms, Entity, Automation)
- Remaining legacy contracts mapped or removed
- No duplicate domain models / parallel writers
- ADR + Canon + Catalog + AGENTS aligned
- Legacy migration map current

**Result:** platforms treated as stable enough for Acquisition completion and Forms infrastructure.  
**Next Product Track:** Phase B — Meta Intake Completeness → Stage 3 slice 3–4.  
**Constraint:** Catalog Notifications↔Communication → Architecture RFC (A2-F1); Catalog not rewritten in A2.

**Branch:** `docs/platform-governance-review-post-epic-c`  
**DoD:** ✅ written review checklist + findings + ordered follow-ups.

---

## Phase B — Acquisition Completion (Epic P / Stage 3)

Return to Acquisition only after **Epic C — complete** + **A2 Governance** (both PASS_WITH_CONSTRAINTS, 2026-08-03). **Phase B is now open.**

Close:

- Meta Intake Completeness (payload retention / visibility — Acquisition-adjacent) — [#222](https://github.com/igortatarynovich/HostFlow/pull/222)
- Stage 3 slice 3 — SalesInquiry product flow — [brief](../tasks/stage-3-sales-inquiry-product-flow.md) sealed; code after Meta
- Stage 3 slice 4 — hard module separation

**End-to-end chain (must be complete):**

```text
Campaign → Flight → Submission → Result → Outcome → Sales → Client → Service Order
```

**Result:** finished client-acquisition process on sealed Sales contracts + reliable Communication.

---

## Phase C — Forms Platform (infrastructure, not Builder)

Build Forms as a platform capability:

- Passport  
- Manifest  
- Public Contract  
- Adapter  
- Runtime  
- Versioning  

**Out until platform done:** Forms Builder / authoring UX product.

**Result:** every questionnaire, form, and survey shares one runtime contract.

**Ref:** [forms-product-layer-epic.md](../tasks/forms-product-layer-epic.md) (scope must stay infrastructure-first until this phase).

---

## Phase D — Universal Entity Workspace

Only after Communication, Forms, Documents foundation, Sales, and Recruitment surfaces are stable enough to compose.

**Result:** one Entity Workspace without temporary side panels / one-off shells.

---

## Phase E — Documents Platform

Evolve storage into a full document lifecycle platform:

- expiry / validity  
- document requests  
- document packages  
- OCR  
- approvals  
- automation  

Especially critical for transport-industry compliance flows.

---

## Phase F — Billing / Subscription Platform

SaaS commercial layer when first customers need it:

- subscriptions · plans · limits  
- invoices · payments  
- tenant billing · usage metering  

---

## Phase G — AI Platform (last)

Not standalone AI features. A **service layer over existing platforms**:

- draft replies / suggested templates (Communication)  
- extract from documents / OCR assist (Documents)  
- fill CRM from mail / summarize threads / next-step suggestions  

**Hard rule:** AI must **not** invent parallel entities. It consumes Communication, Forms, Documents, and Entity Workspace canons only.

---

## Locked sequence (summary)

| Order | Phase | One-line outcome |
|------:|-------|------------------|
| 1 | **A1** Epic C Communication | ✅ Unified comms platform (`PASS_WITH_CONSTRAINTS`) |
| 2 | **A2** Platform Governance Review | ✅ Stable SoT / contracts gate (`PASS_WITH_CONSTRAINTS`) |
| 3 | **B** Acquisition / Stage 3 + Meta | ← **next** Full Campaign→Service Order chain |
| 4 | **C** Forms Platform | Shared form runtime contracts |
| 5 | **D** Universal Entity Workspace | One workspace composition |
| 6 | **E** Documents Platform | Full document lifecycle |
| 7 | **F** Billing Platform | SaaS commercial layer |
| 8 | **G** AI Platform | Assistants over existing canons |

---

## Anti-patterns (forbidden without amending this roadmap)

1. Starting Stage 3 slice 3+ **before** Governance Review (A2) closes — A2 is now **PASS_WITH_CONSTRAINTS**; Phase B may proceed.  
2. Forms Builder before Forms Platform infrastructure (Phase C).  
3. Entity Workspace redesign as a temporary shell before Phases A–C foundations.  
4. AI features that create their own message/document/entity stores.  
5. Parallel product branches that compete across phases (one active product slice).  
6. Unfreezing C2.4 Scheduling without an explicit queue amendment.  
7. Rewriting L0 Catalog Notifications↔Communication without Architecture RFC.

---

## Relationship to other queues

| Doc | Role |
|-----|------|
| [sales-to-comms-sequential-queue.md](../tasks/sales-to-comms-sequential-queue.md) | **Near-term** slice order inside Phase A (and handoff into B) |
| This roadmap | **Horizon** order of platform phases A–G |
| [platform-capability-maturity.md](platform-capability-maturity.md) | **Maturity** SoT (Foundation / Workspace / Automation / Complete per platform) |
| [L0-platform-architecture.md](L0-platform-architecture.md) | Frozen constitution (shape of capabilities) — unchanged by this file |

Amendments to this roadmap require an explicit PR note and update to the near-term sequential queue when the active phase changes.

---

## History

- 2026-08-03: A2 Platform Governance Review **PASS_WITH_CONSTRAINTS**; Product Track → **Phase B Meta / Stage 3**; Catalog Notifications↔Communication deferred to Architecture RFC.  
- 2026-08-03: Epic C Complete Gate **PASS_WITH_CONSTRAINTS**; Product Track → **A2 Platform Governance Review**; C2.4 remains frozen.  
- 2026-07-20: Locked Phase A→G after Communication platform work; Stage 3 deferred until Epic C + Governance Review.  
