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
**Phase B** ← ✅ Meta / Stage 3 slice 3–4 closed. **Phase C — Forms Platform** ← ✅ C1–C6 / Foundation ([#250](https://github.com/igortatarynovich/HostFlow/pull/250)). **Phase D — Entity Workspace** ← **active** ([D3](../tasks/entity-workspace-d3-consumer-cutover.md) brief; D2 ✅ [#254](https://github.com/igortatarynovich/HostFlow/pull/254); D1 ✅).

```text
Epic C Complete Gate → A2 PASS_WITH_CONSTRAINTS → Phase B Meta / Stage 3 → Phase C Forms ✅ → Phase D Entity Workspace → …
```

Order **after A2**:

1. **A2 — Platform Governance Review** — ✅ PASS_WITH_CONSTRAINTS ([gate](../gates/platform-governance-review-a2.md))  
2. **Phase B — Acquisition / Stage 3 + Meta** ← ✅  
3. **Phase C — Forms Platform** ← ✅ ([C1](../tasks/forms-platform-c1-contract-seal.md)…[C6](../tasks/forms-platform-c6-optimization.md) / Foundation) → **Phase D — Entity Workspace** ← **active** ([D3](../tasks/entity-workspace-d3-consumer-cutover.md) brief; D2 ✅; D1 ✅) → Documents → Billing → AI  

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

Return to Acquisition only after **Epic C — complete** + **A2 Governance** (both PASS_WITH_CONSTRAINTS, 2026-08-03). Phase B listed slices are **closed**.

Close:

- Meta Intake Completeness (payload retention / visibility — Acquisition-adjacent) — ✅ [#222](https://github.com/igortatarynovich/HostFlow/pull/222)
- Stage 3 slice 3 — SalesInquiry product flow — ✅ [#224](https://github.com/igortatarynovich/HostFlow/pull/224)
- Stage 3 slice 4 — hard module separation — ✅ [#238](https://github.com/igortatarynovich/HostFlow/pull/238)

**Not in Phase B close-out / not in Phase C C1:** Stage 5 settings/enable-disable · R6 table-cutover.

**End-to-end chain (must be complete):**

```text
Campaign → Flight → Submission → Result → Outcome → Sales → Client → Service Order
```

**Result:** finished client-acquisition process on sealed Sales contracts + reliable Communication.

---

## Phase C — Forms Platform (Core Platform Kit class) ← ✅ Foundation

Forms is **not** a product module. It sits with EntityWorkspace, ListWorkspace, Analytics Kit, RBAC, and Automations: one platform consumed by Recruitment / HR / Fleet / Finance / Services. Compatibility bar is **stricter** than for product modules.

Ladder (locked):

| Slice | Focus | Status |
|-------|--------|--------|
| **C1** | Contract seal (ids / drift docs) | ✅ [#239](https://github.com/igortatarynovich/HostFlow/pull/239)/[#240](https://github.com/igortatarynovich/HostFlow/pull/240) |
| **C2** | Runtime contract + gates | ✅ [#241](https://github.com/igortatarynovich/HostFlow/pull/241)/[#242](https://github.com/igortatarynovich/HostFlow/pull/242) |
| **C3** | Builder Runtime (editor of FormDefinition) | ✅ [#243](https://github.com/igortatarynovich/HostFlow/pull/243)/[#244](https://github.com/igortatarynovich/HostFlow/pull/244) |
| **C4** | Form Runtime | ✅ [#245](https://github.com/igortatarynovich/HostFlow/pull/245)/[#246](https://github.com/igortatarynovich/HostFlow/pull/246) |
| **C5** | Form Execution | ✅ [#247](https://github.com/igortatarynovich/HostFlow/pull/247)/[#248](https://github.com/igortatarynovich/HostFlow/pull/248) |
| **C6** | Optimization | ✅ [#249](https://github.com/igortatarynovich/HostFlow/pull/249)/[#250](https://github.com/igortatarynovich/HostFlow/pull/250) |

C3 edits mutable definitions. Draft save is not publish. C4 is **Runtime, not an Engine**. C5 binds Validation → Submission → Persistence to Runtime Model. C6 wires production Shared Intake through serve→execute and closes Forms Foundation. Do not open P3 / P4 / P5 until unlocked by queue.

**Not** Communication Epic C2 / C2.4 / Communication C3. Historical Forms “C4 HTTP resolve” ≠ Phase C C4 Form Runtime. Acquisition UI C-5 ≠ Phase C C5 Form Execution.

**Out of Phase C (still locked):** P3 Publish UI / P4 Themes / P5 Analytics · FormTemplate SoT · ADR-022 · Stage 5 settings/enable-disable · R6.

**Result:** every questionnaire, form, and survey shares one runtime contract. **Foundation ✅.**

**Ref:** [forms-product-layer-epic.md](../tasks/forms-product-layer-epic.md) · [C6](../tasks/forms-platform-c6-optimization.md) ✅.

---

## Phase D — Universal Entity Workspace ← **active** (D3 brief; D2 ✅)

**Not** the same as PX **minimal EntityWorkspace chrome** (header / actions / rail). Phase D composes **platforms** onto one entity. PX only stops Stage 3 from inventing a fifth card shell.

Documents Foundation (Phase E) may leave document slots empty until Phase E — Product Track still advances here after Forms Foundation. Do **not** treat “Documents not Foundation ✅” as a STOP on D3 first-consumer cutover.

Ladder (locked start):

| Slice | Focus | Status |
|-------|--------|--------|
| **D1** | Contract seal (ownership / PX ≠ Phase D) | ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252) |
| **D2** | Composition contract (platform slots) | ✅ [#253](https://github.com/igortatarynovich/HostFlow/pull/253)/[#254](https://github.com/igortatarynovich/HostFlow/pull/254) |
| **D3** | First consumer cutover (Sales Inquiry) | [brief](../tasks/entity-workspace-d3-consumer-cutover.md) (feat locked) |
| **D4+** | Remaining consumers | locked until D4 brief |

**Out of D3:** Candidate / HR / Vacancy cutover · Shell `EntityWorkspaceSectionId` collapse into D2 slots · Catalog Passport mint · Documents Phase E enable · Forms P3–P5 · Billing · AI · module workspace promotion into the kit.

**Result:** one Entity Workspace without temporary side panels / one-off shells (after D ladder — not after D3 docs alone).

**Ref:** [entity-workspace-d3-consumer-cutover.md](../tasks/entity-workspace-d3-consumer-cutover.md) · [D2](../tasks/entity-workspace-d2-composition-contract.md) ✅ · [D1](../tasks/entity-workspace-d1-contract-seal.md) ✅ · [A2-F7](../gates/platform-governance-review-a2.md) · [ADR-010](ADR-010-unified-resource-list-shell.md).

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
| 3 | **B** Acquisition / Stage 3 + Meta | ✅ Meta / slice 3–4 (#222 / #224 / #238) |
| 4 | **C** Forms Platform | ✅ Shared form runtime / Foundation ([C6](../tasks/forms-platform-c6-optimization.md) [#250](https://github.com/igortatarynovich/HostFlow/pull/250)) |
| 5 | **D** Universal Entity Workspace | ← **active** (D3 [brief](../tasks/entity-workspace-d3-consumer-cutover.md); D2 ✅ [#254](https://github.com/igortatarynovich/HostFlow/pull/254)) |
| 6 | **E** Documents Platform | Full document lifecycle |
| 7 | **F** Billing Platform | SaaS commercial layer |
| 8 | **G** AI Platform | Assistants over existing canons |

---

## Anti-patterns (forbidden without amending this roadmap)

1. Starting Stage 3 slice 3+ **before** Governance Review (A2) closes — A2 is now **PASS_WITH_CONSTRAINTS**; Phase B may proceed.  
2. P3 Publish UI / P4 Themes / P5 Analytics while Forms product unlocks stay locked.  
3. Treating PX EntityWorkspace chrome as Phase D Universal Entity Workspace — or inventing a fifth card shell.  
4. AI features that create their own message/document/entity stores.  
5. Parallel product branches that compete across phases (one active product slice). Phase D (Entity Workspace D3 brief; feat locked) **is** the active phase; do not reopen Forms C6, Stage 5 settings, or R6.  
6. Unfreezing C2.4 Scheduling without an explicit queue amendment.  
7. Rewriting L0 Catalog Notifications↔Communication without Architecture RFC.  
8. Minting Entity Catalog Passport or enabling Documents slot before Phase E without Architecture checklist / RFC when Catalog shape changes.  
9. Starting D3 feat cutover before the D3 brief merges.

---

## Relationship to other queues

| Doc | Role |
|-----|------|
| [sales-to-comms-sequential-queue.md](../tasks/sales-to-comms-sequential-queue.md) | **Near-term** slice order (active = Entity Workspace D3 brief; feat locked) |
| This roadmap | **Horizon** order of platform phases A–G |
| [platform-capability-maturity.md](platform-capability-maturity.md) | **Maturity** SoT (Foundation / Workspace / Automation / Complete per platform) |
| [L0-platform-architecture.md](L0-platform-architecture.md) | Frozen constitution (shape of capabilities) — unchanged by this file |

Amendments to this roadmap require an explicit PR note and update to the near-term sequential queue when the active phase changes.

---

## History

- 2026-08-15: D2 ✅ [#253](https://github.com/igortatarynovich/HostFlow/pull/253)/[#254](https://github.com/igortatarynovich/HostFlow/pull/254) (`a61543cf`); Product Track → **D3 Consumer Cutover** ([brief](../tasks/entity-workspace-d3-consumer-cutover.md); feat locked).
- 2026-08-14: C4 ✅ [#245](https://github.com/igortatarynovich/HostFlow/pull/245)/[#246](https://github.com/igortatarynovich/HostFlow/pull/246) (`4427b110`); Product Track → **C5 Form Execution** ([brief](../tasks/forms-platform-c5-form-execution.md); feat locked).
- 2026-08-14: C5 ✅ [#247](https://github.com/igortatarynovich/HostFlow/pull/247)/[#248](https://github.com/igortatarynovich/HostFlow/pull/248) (`f6bbe03f`); Product Track → **C6 Optimization** ([brief](../tasks/forms-platform-c6-optimization.md); feat locked).
- 2026-08-14: C5 brief ✅ [#247](https://github.com/igortatarynovich/HostFlow/pull/247); Product Track → **C5 Form Execution** feat.
- 2026-08-14: C4 brief [#245](https://github.com/igortatarynovich/HostFlow/pull/245); Product Track → **C4 Form Runtime feat** ([brief](../tasks/forms-platform-c4-form-runtime.md); Runtime Model).
- 2026-08-14: C3 ✅ [#243](https://github.com/igortatarynovich/HostFlow/pull/243)/[#244](https://github.com/igortatarynovich/HostFlow/pull/244); Product Track → **C4 Form Runtime** ([brief](../tasks/forms-platform-c4-form-runtime.md); feat locked).
- 2026-08-14: C1 ✅ [#239](https://github.com/igortatarynovich/HostFlow/pull/239)/[#240](https://github.com/igortatarynovich/HostFlow/pull/240); C2 ✅ [#241](https://github.com/igortatarynovich/HostFlow/pull/241)/[#242](https://github.com/igortatarynovich/HostFlow/pull/242); Product Track → **C3 Builder Runtime** ([brief](../tasks/forms-platform-c3-builder-runtime.md)).  
- 2026-08-13: Stage 3 slice 4 ✅ [#238](https://github.com/igortatarynovich/HostFlow/pull/238); Product Track → **Phase C Forms Platform C1** ([brief](../tasks/forms-platform-c1-contract-seal.md)). Stage 5 settings and R6 stay out of this slice.  
- 2026-08-13: Phase C ladder locked C1→C6; **C2 Runtime Contract** sealed as next ([brief](../tasks/forms-platform-c2-runtime-contract.md)). Builder / C3 after C2 feat only.  
- 2026-08-13: C2 identity model — publication version freeze; lifecycle not identity.  
- 2026-08-03: Epic C Complete Gate **PASS_WITH_CONSTRAINTS**; Product Track → **A2 Platform Governance Review**; C2.4 remains frozen.  
- 2026-07-20: Locked Phase A→G after Communication platform work; Stage 3 deferred until Epic C + Governance Review.  
