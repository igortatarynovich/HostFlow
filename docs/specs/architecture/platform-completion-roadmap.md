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
**Phase B** ← ✅ Meta / Stage 3 slice 3–4 closed. **Phase C — Forms Platform** ← ✅ C1–C6 / Foundation ([#250](https://github.com/igortatarynovich/HostFlow/pull/250)). **Phase D — Entity Workspace** ← D1–D9 brief-complete ([#268](https://github.com/igortatarynovich/HostFlow/pull/268)); **goal-incomplete**. **Workspace Capability Platform Completion** ← **COMPLETE** ([#274](https://github.com/igortatarynovich/HostFlow/pull/274) · [record](../gates/workspace-capability-platform-complete.md)); G4 PASS. **Host runtime-equivalence** ← ✅ ([brief](../tasks/workspace-capability-host-runtime-equivalence.md)). **Phase E — Documents Platform** ← **active** ([E7](../tasks/documents-platform-e7-document-requests.md); feat). E6 ✅ ([#285](https://github.com/igortatarynovich/HostFlow/pull/285)). E5 ✅ ([#282](https://github.com/igortatarynovich/HostFlow/pull/282)).

```text
Epic C Complete Gate → A2 PASS_WITH_CONSTRAINTS → Phase B Meta / Stage 3 → Phase C Forms ✅ → Phase D Entity Workspace (brief-complete) → Workspace Capability Platform Completion → Phase E Documents → …
```

Order **after A2**:

1. **A2 — Platform Governance Review** — ✅ PASS_WITH_CONSTRAINTS ([gate](../gates/platform-governance-review-a2.md))  
2. **Phase B — Acquisition / Stage 3 + Meta** ← ✅  
3. **Phase C — Forms Platform** ← ✅ ([C1](../tasks/forms-platform-c1-contract-seal.md)…[C6](../tasks/forms-platform-c6-optimization.md) / Foundation) → **Phase D — Entity Workspace** D1–D9 brief-complete ([D9](../tasks/entity-workspace-d9-services-order-cutover.md) [#268](https://github.com/igortatarynovich/HostFlow/pull/268)) → **Workspace Capability Platform Completion** **COMPLETE** ([record](../gates/workspace-capability-platform-complete.md)) → **host runtime-equivalence** ✅ ([brief](../tasks/workspace-capability-host-runtime-equivalence.md)) → **Phase E — Documents Platform** (E6 ✅; [E7](../tasks/documents-platform-e7-document-requests.md) feat) → Billing → AI  

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

## Phase D — Universal Entity Workspace ← ✅ D1–D9

**Not** the same as PX **minimal EntityWorkspace chrome** (header / actions / rail). Phase D composes **platforms** onto one entity. PX only stops Stage 3 from inventing a fifth card shell.

Documents Foundation (Phase E) may leave document slots empty until a named Phase E slice **after E1** — Product Track still advanced here after Forms Foundation. Do **not** treat “Documents not Foundation ✅” as a STOP on D3 first-consumer cutover. E1 does **not** enable D2 `documents`.

Ladder (locked start):

| Slice | Focus | Status |
|-------|--------|--------|
| **D1** | Contract seal (ownership / PX ≠ Phase D) | ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252) |
| **D2** | Composition contract (platform slots) | ✅ [#253](https://github.com/igortatarynovich/HostFlow/pull/253)/[#254](https://github.com/igortatarynovich/HostFlow/pull/254) |
| **D3** | First consumer cutover (Sales Inquiry) | ✅ [#255](https://github.com/igortatarynovich/HostFlow/pull/255)/[#256](https://github.com/igortatarynovich/HostFlow/pull/256) |
| **D4** | Candidate cutover (Shell ≠ D2 slots) | ✅ [#257](https://github.com/igortatarynovich/HostFlow/pull/257)/[#258](https://github.com/igortatarynovich/HostFlow/pull/258) |
| **D5** | Client cutover | ✅ [#259](https://github.com/igortatarynovich/HostFlow/pull/259)/[#260](https://github.com/igortatarynovich/HostFlow/pull/260) |
| **D6** | Sales Order cutover | ✅ [#261](https://github.com/igortatarynovich/HostFlow/pull/261)/[#262](https://github.com/igortatarynovich/HostFlow/pull/262) |
| **D7** | Vacancy cutover | ✅ [#263](https://github.com/igortatarynovich/HostFlow/pull/263)/[#264](https://github.com/igortatarynovich/HostFlow/pull/264) |
| **D8** | HR employee cutover | ✅ [#265](https://github.com/igortatarynovich/HostFlow/pull/265)/[#266](https://github.com/igortatarynovich/HostFlow/pull/266) |
| **D9** | Services `/app/orders` cutover | ✅ [#267](https://github.com/igortatarynovich/HostFlow/pull/267)/[#268](https://github.com/igortatarynovich/HostFlow/pull/268) |

**Out of D9 (closed):** `HrHandoffDetailPage` stayed out · D2 `documents` stayed reserved · no Catalog Passport · Forms P3–P5 / Billing / AI out.

**Result:** named D-series consumers bound to D2 enabled slots (Sales Inquiry · Candidate · Client · Sales Order · Vacancy · HR employee · Services order). D2 `documents` stayed reserved through D9. **Brief-complete / goal-incomplete** vs original Entity Shell — [audit](../gates/platform-scope-completeness-audit.md). Catalog unlock is E2 (consumers unbound).

**Ref:** [entity-workspace-d9-services-order-cutover.md](../tasks/entity-workspace-d9-services-order-cutover.md) ✅ · [D8](../tasks/entity-workspace-d8-hr-employee-cutover.md) ✅ · [D7](../tasks/entity-workspace-d7-vacancy-cutover.md) ✅ · [D6](../tasks/entity-workspace-d6-sales-order-cutover.md) ✅ · [D5](../tasks/entity-workspace-d5-client-cutover.md) ✅ · [D4](../tasks/entity-workspace-d4-candidate-cutover.md) ✅ · [D3](../tasks/entity-workspace-d3-consumer-cutover.md) ✅ · [D2](../tasks/entity-workspace-d2-composition-contract.md) ✅ · [D1](../tasks/entity-workspace-d1-contract-seal.md) ✅ · [A2-F7](../gates/platform-governance-review-a2.md) · [ADR-010](ADR-010-unified-resource-list-shell.md).

---

## Workspace Capability Platform Completion ← **COMPLETE** (corrective; G4 PASS)

Queue insert **between** Phase D and Documents E2 feat. Not D10. Not Platform Extraction 2. Not a new A–G letter.

D1–D9 closed chrome + D2 **surfaces** + named consumer binds. That was a **substituted** goal. This program seals the **Capability Host Contract** (host places; owners own semantics). Entity Workspace and Application Workspace stay distinct; both implement the same contract **at runtime**. G4 proof = Recruitment Application ([#273](https://github.com/igortatarynovich/HostFlow/pull/273)). Final G1–G5: [PASS / COMPLETE](../gates/workspace-capability-platform-complete.md). Intermediate #273: [PASS_WITH_CONSTRAINTS](../gates/workspace-capability-platform-g1-g5-closeout.md).

**Ladder:**

| Slice | Focus | Status |
|-------|--------|--------|
| **Audit + Goal Completion Gate** | Classify closed phases | [audit](../gates/platform-scope-completeness-audit.md) · [gate](../gates/goal-completion-gate.md) |
| **Contract** | Capability Host Contract + four-class catalogs | [brief](../tasks/workspace-capability-platform-completion.md) ✅ [#272](https://github.com/igortatarynovich/HostFlow/pull/272) |
| **Feat + G4 bind** | Named gate + Recruitment Application host | ✅ [#273](https://github.com/igortatarynovich/HostFlow/pull/273) · G4 **PASS** |
| **G1–G5 close-out** | Goal Completion review of #273 | [close-out](../gates/workspace-capability-platform-g1-g5-closeout.md) **PASS_WITH_CONSTRAINTS** |
| **Host runtime-equivalence** | Second host + Notes/Consent owner boundaries | ✅ [#274](https://github.com/igortatarynovich/HostFlow/pull/274) ([brief](../tasks/workspace-capability-host-runtime-equivalence.md)) |
| **Final Goal Completion** | Program COMPLETE | [COMPLETE](../gates/workspace-capability-platform-complete.md) **PASS** |
| **Then E2** | Documents public contract / D2 `documents` enable | ✅ [#276](https://github.com/igortatarynovich/HostFlow/pull/276) |

**Out:** Shell-as-semantic-owner · Application-as-Entity · Candidate-as-proof · Recruitment rail patch as done · mass migration · starting E2 in the WCP PR · P3–P5 / R6 / C2.4 · mixing ListWorkspace into this close-out.

**Ref:** [workspace-capability-platform-completion.md](../tasks/workspace-capability-platform-completion.md) · [host runtime-equivalence](../tasks/workspace-capability-host-runtime-equivalence.md) · [COMPLETE](../gates/workspace-capability-platform-complete.md) · [D2](../tasks/entity-workspace-d2-composition-contract.md) · [UI constitution §3 / §10](ui-constitution-v1.md).

---

## Phase E — Documents Platform ← E7 ✅; Product Track = CL1

Evolve storage into a full document lifecycle platform (horizon):

- expiry / validity ✅ E6  
- document requests ✅ E7  
- document packages  
- OCR  
- approvals  
- automation  

Especially critical for transport-industry compliance flows.

Ladder (E7 ✅; Product Track = CL1):

| Slice | Focus | Status |
|-------|--------|--------|
| **E1** | Contract seal (ownership / Hub ≠ dossier / D2 still reserved) | ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269)/[#270](https://github.com/igortatarynovich/HostFlow/pull/270) |
| **E2** | Public contract / D2 `documents` catalog enable | ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276) · merge `826877b5` |
| **E3** | First consumer bind (HR employee) + Document Link SoT | ✅ [#277](https://github.com/igortatarynovich/HostFlow/pull/277)/[#278](https://github.com/igortatarynovich/HostFlow/pull/278) · merge `cc106a38` |
| **E4** | Candidate Document Link bind (D4) | ✅ [#279](https://github.com/igortatarynovich/HostFlow/pull/279)/[#280](https://github.com/igortatarynovich/HostFlow/pull/280) · merge `0af74913` |
| **E5** | Candidate storage-bridge retirement (`candidate_id` drop) | ✅ [#281](https://github.com/igortatarynovich/HostFlow/pull/281)/[#282](https://github.com/igortatarynovich/HostFlow/pull/282) · merge `702b922c` |
| **E6** | Document expiry / validity | ✅ [#284](https://github.com/igortatarynovich/HostFlow/pull/284)/[#285](https://github.com/igortatarynovich/HostFlow/pull/285) · merge `79e638c3` |
| **E7** | Document requests | ✅ [#286](https://github.com/igortatarynovich/HostFlow/pull/286)/[#287](https://github.com/igortatarynovich/HostFlow/pull/287) · merge `ceafbd48` |
| **E8+** | Remaining consumers / later lifecycle | locked (Product Track = [CL1](../tasks/entity-field-composition-cl1-inventory.md); do not start E8 here) |

**Out of E7:** D3 / D5–D7 / D9 `documents` bind · OCR / e-sign / packages / Hub UI rebuild · Hub request table · Catalog `document.requested` · Forms P3–P5 · Billing Platform · AI · L0 Catalog rewrite · G4 reopen · unbind D8 / D4.

**Result:** validity is Hub. Outstanding ask is Hub required type + entity (E7 ✅). Product Track = [Entity Field Composition CL1](../tasks/entity-field-composition-cl1-inventory.md). Foundation stays 🔄. E8 stays locked.

**Ref:** [entity-field-composition-cl1-inventory.md](../tasks/entity-field-composition-cl1-inventory.md) · [entity-field-composition-cl0-contract-seal.md](../tasks/entity-field-composition-cl0-contract-seal.md) ✅ · [documents-platform-e7-document-requests.md](../tasks/documents-platform-e7-document-requests.md) ✅ · [E6](../tasks/documents-platform-e6-document-expiry.md) ✅ · [E5](../tasks/documents-platform-e5-candidate-storage-bridge.md) ✅ · [E4](../tasks/documents-platform-e4-candidate-document-link.md) ✅ · [E3](../tasks/documents-platform-e3-first-consumer-bind.md) ✅ · [E2](../tasks/documents-platform-e2-public-contract.md) ✅ · [E1](../tasks/documents-platform-e1-contract-seal.md) ✅ · [ADR-009](ADR-009-document-hub-platform-layer.md) · [ADR-012](ADR-012-activity-notification-operating-layer.md) · [A2-F8](../gates/platform-governance-review-a2.md).

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
| 5 | **D** Universal Entity Workspace | D1–D9 brief-complete ([D9](../tasks/entity-workspace-d9-services-order-cutover.md) [#268](https://github.com/igortatarynovich/HostFlow/pull/268)); goal-incomplete |
| 5b | **Workspace Capability Platform Completion** | **COMPLETE** ([#274](https://github.com/igortatarynovich/HostFlow/pull/274) · [record](../gates/workspace-capability-platform-complete.md)); G4 PASS |
| 5c | **Host runtime-equivalence** | Second host + Notes/Consent owner boundaries ✅ [#274](https://github.com/igortatarynovich/HostFlow/pull/274) |
| 6 | **E** Documents Platform | ← **active** ([E7](../tasks/documents-platform-e7-document-requests.md); feat). E6 ✅ |
| 7 | **F** Billing Platform | SaaS commercial layer |
| 8 | **G** AI Platform | Assistants over existing canons |

---

## Anti-patterns (forbidden without amending this roadmap)

1. Starting Stage 3 slice 3+ **before** Governance Review (A2) closes — A2 is now **PASS_WITH_CONSTRAINTS**; Phase B may proceed.  
2. P3 Publish UI / P4 Themes / P5 Analytics while Forms product unlocks stay locked.  
3. Treating PX EntityWorkspace chrome as Phase D Universal Entity Workspace — or inventing a fifth card shell.  
4. AI features that create their own message/document/entity stores.  
5. Parallel product branches that compete across phases (one active product slice). **Documents Platform E7** **is** the active slice (feat) after E6 ✅; do not mix E7 into an E6/E5/E4/E3/E2/WCP PR, mass-bind D3–D9, reopen G4, D10-on-weak-D2, Recruitment rail patches, reopen D9, Forms C6, Stage 5 settings, or R6. Do not fold Application into Entity. Do not mix ListWorkspace into the WCP close-out. Closing a later phase as COMPLETE requires the [Goal Completion Gate](../gates/goal-completion-gate.md). New platform phase briefs require [Original Goal → Completion Proof](../gates/goal-completion-gate.md).  
6. Unfreezing C2.4 Scheduling without an explicit queue amendment.  
7. Rewriting L0 Catalog Notifications↔Communication without Architecture RFC.  
8. Minting Entity Catalog Passport, or binding D2 `documents` on D3 / D5–D7 / D9 in E5, without a later named E slice + Architecture checklist / RFC when Catalog shape changes.  
9. Treating E4 Candidate bind / a nullable `candidate_id` / Shell `documents` nav / G4 Recruitment Application as the E5 proof — or starting OCR / e-sign / Billing as this slice.

---

## Relationship to other queues

| Doc | Role |
|-----|------|
| [sales-to-comms-sequential-queue.md](../tasks/sales-to-comms-sequential-queue.md) | **Near-term** slice order (active = Entity Field Composition CL0 brief) |
| [workspace-capability-platform-completion.md](../tasks/workspace-capability-platform-completion.md) | Corrective program — Capability Host Contract; **COMPLETE** |
| [workspace-capability-host-runtime-equivalence.md](../tasks/workspace-capability-host-runtime-equivalence.md) | Equivalence slice — second host + owner boundaries ✅ |
| [workspace-capability-platform-complete.md](../gates/workspace-capability-platform-complete.md) | Final Goal Completion — program COMPLETE |
| [workspace-capability-platform-g1-g5-closeout.md](../gates/workspace-capability-platform-g1-g5-closeout.md) | Goal Completion review of #273 (historical) |
| [goal-completion-gate.md](../gates/goal-completion-gate.md) | Phase close: original goal vs substituted brief |
| [platform-scope-completeness-audit.md](../gates/platform-scope-completeness-audit.md) | Closed-phase completeness vs residual capability |
| [documents-platform-e4-candidate-document-link.md](../tasks/documents-platform-e4-candidate-document-link.md) | E4 COMPLETE — Candidate Document Link |
| [documents-platform-e5-candidate-storage-bridge.md](../tasks/documents-platform-e5-candidate-storage-bridge.md) | E5 COMPLETE — Candidate storage-bridge retirement |
| [documents-platform-e6-document-expiry.md](../tasks/documents-platform-e6-document-expiry.md) | E6 COMPLETE — Document expiry / validity |
| [documents-platform-e7-document-requests.md](../tasks/documents-platform-e7-document-requests.md) | E7 COMPLETE — Document requests |
| [entity-field-composition-cl0-contract-seal.md](../tasks/entity-field-composition-cl0-contract-seal.md) | CL0 COMPLETE — Entity Field Composition contract seal |
| [entity-field-composition-cl1-inventory.md](../tasks/entity-field-composition-cl1-inventory.md) | **Active Product Track** — Entity Field Composition CL1 (brief; feat locked) |
| [documents-platform-e3-first-consumer-bind.md](../tasks/documents-platform-e3-first-consumer-bind.md) | E3 first consumer bind ✅ |
| This roadmap | **Horizon** order of platform phases A–G |
| [platform-capability-maturity.md](platform-capability-maturity.md) | **Maturity** SoT (Foundation / Workspace / Automation / Complete per platform) |
| [L0-platform-architecture.md](L0-platform-architecture.md) | Frozen constitution (shape of capabilities) — unchanged by this file |

Amendments to this roadmap require an explicit PR note and update to the near-term sequential queue when the active phase changes.

---

## History

- 2026-08-23: CL1 brief — Candidate composition inventory. Active = [Entity Field Composition CL1](../tasks/entity-field-composition-cl1-inventory.md) (feat locked). CL0 ✅ [#289](https://github.com/igortatarynovich/HostFlow/pull/289).
- 2026-08-23: E7 feat — Hub outstanding-ask read on public contract. Active = [Documents Platform E7](../tasks/documents-platform-e7-document-requests.md) (feat). E6 ✅ [#285](https://github.com/igortatarynovich/HostFlow/pull/285).
- 2026-08-23: E7 brief — Document requests. Active = [Documents Platform E7](../tasks/documents-platform-e7-document-requests.md) (feat locked). E6 ✅ [#285](https://github.com/igortatarynovich/HostFlow/pull/285).
- 2026-08-23: E6 brief — Document expiry / validity. Active = [Documents Platform E6](../tasks/documents-platform-e6-document-expiry.md) (feat locked). E5 ✅ [#282](https://github.com/igortatarynovich/HostFlow/pull/282).
- 2026-08-22: E5 brief — Candidate storage-bridge retirement (`candidate_id` drop). Active = [Documents Platform E5](../tasks/documents-platform-e5-candidate-storage-bridge.md) (feat locked). E4 ✅ [#280](https://github.com/igortatarynovich/HostFlow/pull/280).
- 2026-08-22: E4 feat opened — D4 bind + Candidate Document Link resolve. Active = [Documents Platform E4](../tasks/documents-platform-e4-candidate-document-link.md) (feat).
- 2026-08-22: E4 brief — Candidate Document Link (D4). Active = [Documents Platform E4](../tasks/documents-platform-e4-candidate-document-link.md) (feat locked). E3 ✅ [#278](https://github.com/igortatarynovich/HostFlow/pull/278).
- 2026-08-22: E3 feat opened — D8 bind + Document Link SoT on `documents.hub_adapter_v1`. Active = [Documents Platform E3](../tasks/documents-platform-e3-first-consumer-bind.md) (feat).
- 2026-08-22: E3 brief — first consumer bind = HR employee + Document Link SoT. Active = [Documents Platform E3](../tasks/documents-platform-e3-first-consumer-bind.md) (feat locked). E2 ✅ [#276](https://github.com/igortatarynovich/HostFlow/pull/276).
- 2026-08-22: Documents E2 feat — `documents.public_contract.v1` / D2 catalog enable; named Public Contract Gate. After [#273](https://github.com/igortatarynovich/HostFlow/pull/273)/[#274](https://github.com/igortatarynovich/HostFlow/pull/274) merge `84a2ea94`.
- 2026-08-21: WCP program **COMPLETE** ([#274](https://github.com/igortatarynovich/HostFlow/pull/274) · [record](../gates/workspace-capability-platform-complete.md)). Active = [Documents E2](../tasks/documents-platform-e2-public-contract.md) (feat unlocked, not started).
- 2026-08-21: WCP G1–G5 **PASS_WITH_CONSTRAINTS** ([#273](https://github.com/igortatarynovich/HostFlow/pull/273) · [close-out](../gates/workspace-capability-platform-g1-g5-closeout.md)). G4 PASS. Program **not COMPLETE**. Active = [host runtime-equivalence](../tasks/workspace-capability-host-runtime-equivalence.md). E2 stays locked until COMPLETE.  
- 2026-08-20: D1–D9 reclassified brief-complete / goal-incomplete. Product Track → **Entity Platform Completion** ([brief](../tasks/workspace-capability-platform-completion.md)). [Goal Completion Gate](../gates/goal-completion-gate.md) + [audit](../gates/platform-scope-completeness-audit.md). Same-day Shared UI Capabilities draft superseded. E2 feat locked.  
- 2026-08-20: Brief retitled **Workspace Capability Platform Completion**. Host places / owners own semantics. Proof locked to Recruitment Application. Entity Platform Completion same-day draft superseded in place.
- 2026-08-18: E1 feat [#270](https://github.com/igortatarynovich/HostFlow/pull/270) (`f37deff1`); named gate 11 passed; full Tests with coverage 484 failed / 2740 passed (Engineering Track, same as D9). Product Track → **Documents Platform E2** ([brief](../tasks/documents-platform-e2-public-contract.md) [#271](https://github.com/igortatarynovich/HostFlow/pull/271); feat locked). Catalog unlock ≠ D3–D9 bind.
- 2026-08-18: E1 brief ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269) (`17bd3dd3`); Product Track → **Documents Platform E1** feat (named Contract Seal Gate). D2 `documents` stays reserved. E2+ locked.
- 2026-08-18: D9 ✅ [#267](https://github.com/igortatarynovich/HostFlow/pull/267)/[#268](https://github.com/igortatarynovich/HostFlow/pull/268) (`28978a1f`); Product Track → **Documents Platform E1** ([brief](../tasks/documents-platform-e1-contract-seal.md); feat locked). D2 `documents` stays reserved.
- 2026-08-17: D9 feat — named **Entity Workspace D9 Cutover Gate**; Services order bound to D2 slots; Product Track → D9 feat; next = Documents Phase E (locked).
- 2026-08-17: D8 ✅ [#265](https://github.com/igortatarynovich/HostFlow/pull/265)/[#266](https://github.com/igortatarynovich/HostFlow/pull/266) (`fae8202e`); Product Track → **D9 Services Order Cutover** ([brief](../tasks/entity-workspace-d9-services-order-cutover.md); feat locked).
- 2026-08-17: D8 feat — named **Entity Workspace D8 Cutover Gate**; HR employee bound to D2 slots; Product Track → D8 feat; next = D9 brief (locked).
- 2026-08-17: D7 ✅ [#263](https://github.com/igortatarynovich/HostFlow/pull/263)/[#264](https://github.com/igortatarynovich/HostFlow/pull/264) (`7484f98e`); Product Track → **D8 HR Employee Cutover** ([brief](../tasks/entity-workspace-d8-hr-employee-cutover.md); feat locked).
- 2026-08-15: D7 feat — named **Entity Workspace D7 Cutover Gate**; Vacancy bound to D2 slots; Product Track → D7 feat; next = D8 brief (locked).
- 2026-08-15: D6 ✅ [#261](https://github.com/igortatarynovich/HostFlow/pull/261)/[#262](https://github.com/igortatarynovich/HostFlow/pull/262) (`bc819768`); Product Track → **D7 Vacancy Cutover** ([brief](../tasks/entity-workspace-d7-vacancy-cutover.md); feat locked).
- 2026-08-15: D6 feat — named **Entity Workspace D6 Cutover Gate**; Sales Order bound to D2 slots; Product Track → D6 feat; next = D7 brief (locked).
- 2026-08-15: D5 ✅ [#259](https://github.com/igortatarynovich/HostFlow/pull/259)/[#260](https://github.com/igortatarynovich/HostFlow/pull/260) (`069f441d`); Product Track → **D6 Sales Order Cutover** ([brief](../tasks/entity-workspace-d6-sales-order-cutover.md); feat locked).
- 2026-08-15: D5 feat — named **Entity Workspace D5 Cutover Gate**; Client bound to D2 slots; Product Track → D5 feat; next = D6 brief (locked).
- 2026-08-15: D4 ✅ [#257](https://github.com/igortatarynovich/HostFlow/pull/257)/[#258](https://github.com/igortatarynovich/HostFlow/pull/258) (`b5f1f00a`); Product Track → **D5 Client Cutover** ([brief](../tasks/entity-workspace-d5-client-cutover.md); feat locked).
- 2026-08-15: D4 brief ✅ [#257](https://github.com/igortatarynovich/HostFlow/pull/257) (`cb543e68`); Product Track → **D4 Candidate Cutover** feat.
- 2026-08-15: D3 feat — named **Entity Workspace D3 Cutover Gate**; Sales Inquiry first consumer; Product Track → D3 ✅; next = D4 brief (locked).
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
