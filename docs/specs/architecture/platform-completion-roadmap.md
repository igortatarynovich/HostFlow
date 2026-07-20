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

---

## Immediate rule (after Epic C)

Do **not** return to Stage 3 Sales product wiring the moment Communication integrity slices close.  
Order after Epic C:

1. **A2 — Platform Governance Review (L0 gate)** — short architectural pass  
2. **Phase B — Acquisition / Stage 3 completion**  
3. Then Forms → Entity Workspace → Documents → Billing → AI  

Near-term slice execution remains one-at-a-time per [sequential queue](../tasks/sales-to-comms-sequential-queue.md).

---

## Phase A — Platform Completion (Communication)

### A1. Communication (Epic C)

Close the Communication Platform end-to-end:

| Slice | Focus | Status |
|-------|--------|--------|
| C0.0 Canon & Contracts | Intent-first SoT | ✅ |
| C0.1 / C0.1b Outbound + policy/snapshot | Canon writer path | ✅ |
| **C0.2** Inbound Resolver | Linked or explicit unresolved | **active** |
| **C0.3** Delivery Diagnostics | One record explains failure | queued |
| **C1** Inbox UX | Working messages module | queued |
| **C2** Templates, Automations & Campaigns | Product on platform command | queued |

**Result:** one Communication Platform, no parallel module senders / lost inbound.

**Refs:** [Epic C0](../tasks/epic-c0-communication-integrity.md) · [C2 epic](../tasks/epic-c2-communication-campaigns.md) · [Canon](../tasks/c0-0-communication-canon.md)

### A2. Platform Governance Review (L0 gate)

**Not** a product feature. Short architectural gate after Epic C volume:

- One SoT per platform (Acquisition, Communication, Documents, Forms, Entity, Automation)
- Remaining legacy contracts mapped or removed
- No duplicate domain models / parallel writers
- ADR + Canon + Catalog + AGENTS aligned
- Legacy migration map current

**Result:** platforms treated as stable enough for Acquisition completion and Forms infrastructure.

**Suggested branch:** `docs/platform-governance-review-post-epic-c`  
**DoD:** written review checklist + findings + ordered follow-ups (no drive-by refactors in the same PR unless trivial).

---

## Phase B — Acquisition Completion (Epic P / Stage 3)

Return to Acquisition after A1 + A2.

Close:

- Meta Intake Completeness (payload retention / visibility — Acquisition-adjacent)
- Stage 3 slice 3 — SalesInquiry product flow
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
| 1 | **A1** Epic C Communication | Unified comms platform |
| 2 | **A2** Platform Governance Review | Stable SoT / contracts gate |
| 3 | **B** Acquisition / Stage 3 | Full Campaign→Service Order chain |
| 4 | **C** Forms Platform | Shared form runtime contracts |
| 5 | **D** Universal Entity Workspace | One workspace composition |
| 6 | **E** Documents Platform | Full document lifecycle |
| 7 | **F** Billing Platform | SaaS commercial layer |
| 8 | **G** AI Platform | Assistants over existing canons |

---

## Anti-patterns (forbidden without amending this roadmap)

1. Starting Stage 3 slice 3+ **before** Epic C (A1) **and** Governance Review (A2).  
2. Forms Builder before Forms Platform infrastructure (Phase C).  
3. Entity Workspace redesign as a temporary shell before Phases A–C foundations.  
4. AI features that create their own message/document/entity stores.  
5. Parallel product branches that compete across phases (one active product slice).

---

## Relationship to other queues

| Doc | Role |
|-----|------|
| [sales-to-comms-sequential-queue.md](../tasks/sales-to-comms-sequential-queue.md) | **Near-term** slice order inside Phase A (and handoff into B) |
| This roadmap | **Horizon** order of platform phases A–G |
| [L0-platform-architecture.md](L0-platform-architecture.md) | Frozen constitution (shape of capabilities) — unchanged by this file |

Amendments to this roadmap require an explicit PR note and update to the near-term sequential queue when the active phase changes.

---

## History

- 2026-07-20: Locked Phase A→G after Communication platform work; Stage 3 deferred until Epic C + Governance Review.  
