# Sales → Communication — sequential product queue (locked)

**Status:** **NORMATIVE QUEUE** (one active product slice at a time)  
**Date:** 2026-07-20 (rev. Platform Completion Roadmap)  
**Trusted base:** `integration/release-product-a-b` (fast-forward only)  
**Parents:** [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Pipeline v1 seal](../architecture/sales-domain-pipeline-v1.md) · [Creation Origins v1](../architecture/client-account-creation-origins-v1.md) · [C0.0 Communication Canon](c0-0-communication-canon.md) · [Epic C0](epic-c0-communication-integrity.md) · [Repository Operational Canon](../../governance/repository-operational-canon.md)

> Sales domain contracts are sealed. Product convert engine unification is complete (Stage 3 slice 2 / PR #99).  
> **Horizon SoT:** [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) — finish **Epic C**, then **Governance Review**, then Acquisition/Stage 3.  
> This file is the **near-term slice queue** inside Phase A (Communication).  
> **Communication Platform Foundation is complete** (C0.0–C0.3). Do **not** jump to Stage 3.  
> Locked close-out: **C1 → C2 → Epic C Complete Gate → Governance → Stage 3 / Meta → …**

---

## 1. Frozen completed state

| Stage | Status |
|-------|--------|
| Sales Domain Pipeline v1 seal | ✅ PR #93 |
| ClientAccount Creation Origins v1 | ✅ PR #94 |
| Convert Mapping + Review + Traceability | ✅ |
| Stage 1 Capability UI | ✅ PR #96 |
| Stage 2 Manual ClientAccount create | ✅ PR #97 |
| Stage 3 slice 1 — product convert → mapping | ✅ PR #98 |
| Stage 3 slice 2 — convert entrypoints | ✅ PR #99 |
| Repository Health | ✅ required PASS before each new branch |

**Open product GAPs (queued below / in roadmap):**

- Communication Inbox Workspace (C1 — **active**, slice **C1.2**)  
- Templates/Automations/Campaigns (C2)  
- Epic C Complete Gate (after C2; before Governance)  
- Platform Governance Review (after **Epic C — complete**)  
- Meta intake completeness · Stage 3 slice 3–4 (Acquisition — **after** Epic C + governance)  

---

## 2. Locked near-term sequence (Phase A — Epic C)

| # | Work | Branch (proposed) | Result |
|---|------|-------------------|--------|
| **1** | **C0.0** Communication Canon & Contracts | *(with PR #100)* | ✅ SoT + Intent-first contracts |
| **2** | **C0.1** First Canon implementation (outbound) | `fix/communication-c0-outbound-linkage` (**PR #100 merged**) | ✅ Intent → Policy → Resolvers → Command → Sender + G13 |
| **3** | **C0.1b** Intent Policy & Snapshot Hardening | `fix/communication-c0-intent-policy-hardening` (**PR #101 merged**) | ✅ Typed policies, full snapshot, writer migration map |
| **4** | **C0.2** Incoming resolver | `fix/communication-c0-inbound-resolver` (**PR #102 merged**) | ✅ Deterministic thread/entity or unresolved queue |
| **5** | **C0.3** Delivery diagnostics | `fix/communication-c0-delivery-diagnostics` (**PR #104 merged**) | ✅ Failures explainable without server logs |
| **6** | **C1** Communication Inbox Workspace | `feat/communication-c1-inbox-workspace` (**PR #107 merged**) | ✅ Queues + ThreadContext + capability Composer (C1.1) |
| **6b** | **C1.2** Workspace Actions | `feat/communication-c1-2-workspace-actions` (**current**) | Commands → ThreadContext; invariants; no queue writes |
| **6c** | **C1.3** Workspace Experience | *(after C1.2)* | Thread card UX on frozen Thread/Command model |
| **7** | **C2** Templates, Automations & Campaigns | *(TBD)* | Catalog + rules + bulk on **same** Commands |
| **8** | **Epic C Complete Gate** | `docs/epic-c-complete-gate` | Single Communication capability; status → Epic C complete |
| **9** | **A2** Platform Governance Review | `docs/platform-governance-review-post-epic-c` | Boundary principle across platforms |
| **10** | Meta Intake Completeness | `fix/meta-intake-completeness` | Full Meta payload retained and visible |
| **11** | Stage 3 slice 3 | *(TBD)* | Full SalesInquiry product flow |
| **12** | Stage 3 slice 4 | *(TBD)* | Hard module separation |

**C0.1–C0.3** ✅ → [Communication Platform Foundation — complete](../architecture/communication-platform-foundation.md) (`95f2a525`, PR #104).  
**C1 / C1.1** ✅ → PR #107 (`dbeb36ed`) — [ThreadContext](c1-1-thread-context-composer.md).  
**Active:** **C1.2 Workspace Actions** — [c1-2-workspace-actions.md](c1-2-workspace-actions.md).  
**Close-out:** C1.2 → [C1.3 Workspace Experience](c1-3-workspace-experience.md) → C2 → [Epic C Complete Gate](../gates/epic-c-complete-gate.md) → Governance → Stage 3.  
**Epic C — complete** only after gate PASS (not after C2 alone).

**After row 9:** continue [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) Phase B→G  
(Acquisition/Stage 3 + Meta → Forms → Entity Workspace → Documents → Billing → AI).

**Deferred polish (as needed):** signature policy product UI, composer UX thin slice, historical unbound-thread repair queue, Service Orders / quotes / deals.

**Supersedes (this revision):** Stage 3 slice 3 immediately after C0.3/Meta; C1/C2 after Stage 3.

---

## 3. Stage 1 — Capability UI ✅

**Branch:** `feat/sales-capability-ui` (merged PR #96)

---

## 3b. Stage 2 — Manual ClientAccount creation ✅

**Branch:** `feat/manual-client-account-creation` (merged PR #97)  
**Task:** [stage-2-manual-client-account-creation.md](stage-2-manual-client-account-creation.md)

---

## 3c. Stage 3 — Sales Pipeline product wiring

**Slice 1 ✅** — [stage-3-sales-pipeline-product-wiring.md](stage-3-sales-pipeline-product-wiring.md) (PR #98)  
**Slice 2 ✅** — [stage-3-sales-pipeline-convert-entrypoints.md](stage-3-sales-pipeline-convert-entrypoints.md) (PR #99)

### Slice 3+ — **blocked until Epic C + Governance Review**

Do **not** start Stage 3 slice 3 until **A1 Epic C** (through C2) and **A2 Platform Governance Review** are done, unless the [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) is explicitly amended.  
Meta Intake Completeness runs at the start of Phase B (with Stage 3), not as a shortcut past Epic C.

---

## 4. Epic C0 — Communication Integrity

**Canon:** [c0-0-communication-canon.md](c0-0-communication-canon.md)  
**Epic:** [epic-c0-communication-integrity.md](epic-c0-communication-integrity.md)

| Slice | Focus | Acceptance (one line) |
|-------|--------|------------------------|
| **C0.0** | Canon & contracts (docs only) | SoT fixed; anti-patterns named; queue/epics aligned |
| **C0.1** | Universal outbound foundation | Inquiry-sent mail on inquiry history; command path toward canon |
| **C0.2** | Inbound resolver / threading | Reply joins same thread on same entity |
| **C0.3** | Delivery diagnostics / history | One record explains send failure |

**C0.1 contract (unchanged intent):** outbound from a known HostFlow entity **must** have durable `thread ↔ origin entity`. Unknown delivery result OK; unbound thread with known origin **forbidden**.

**Invariant (C0.1+):**

```text
Entity → Communication Context → Thread Entity Link (G13) → Message Outbox → Provider
```

Full prepare-send chain (canon): authorization → capabilities → recipient → consent → template → links → signature → thread → G13 → snapshot → outbox → audit.

---

## 5. Epic C1 — Inbox UX (after C0.3)

Not a second CRM and not Settings. Working folders only (Inbox, Unread, Needs reply, Assigned to me, Sent, Archive, Unresolved). Thread title priority: company → contact name → email/phone → readable fallback (**never** UUID stubs). Settings / signatures / templates live under **Настройки → Коммуникации**.

- [C1 kickoff](c1-communication-inbox-workspace.md) · [C1.1 ThreadContext](c1-1-thread-context-composer.md) ✅  
- **[C1.2 Workspace Actions](c1-2-workspace-actions.md)** ← active  
- [C1.3 Workspace Experience](c1-3-workspace-experience.md) (after C1.2)

---

## 5b. Epic C2 — Templates, Automations & Campaigns

**Task:** [epic-c2-communication-campaigns.md](epic-c2-communication-campaigns.md)

After C0 + C1: product surfaces for template catalog, automation rules, and campaigns — all calling the same platform command. Not a second send engine. Closes Phase A1.

---

## 5c. A2 — Platform Governance Review (after Epic C)

Short L0 gate — see [Platform Completion Roadmap § A2](../architecture/platform-completion-roadmap.md). Not a feature sprint.

---

## 6. Meta Intake Completeness (Phase B — with Acquisition)

**Task:** [meta-intake-completeness.md](meta-intake-completeness.md)

Separate from Communication. Chain: Meta payload → Submission raw → normalized → SalesInquiry → UI. No answer may disappear before normalization (show as additional answers). Runs **after** A2, before/with Stage 3 slice 3.

---

## 7. Development rule

Exactly **one** product slice active.

Next branch only after:

1. Current PR merged  
2. Fast-forward `integration/release-product-a-b`  
3. `make repo-health` **PASSED**  
4. Stale worktrees pruned  
5. One dedicated worktree  

**Do not** open Stage 3 / Meta / Forms / Workspace while Phase A Communication slices are active (unless roadmap + this queue are explicitly amended).  
**Do not** expand the active Communication PR beyond its locked slice.

---

## 8. History

- 2026-07-20: Queue locked — Capability UI → Manual create → Pipeline wiring → Communication (old 4–7) → CRM.  
- 2026-07-20 (rev): After Stage 3 slice 2, insert **Epic C0 Communication Integrity** (C0.1–C0.3) + **Meta Intake Completeness** before Stage 3 slice 3; then C1 Inbox; then Stage 3 slice 4.  
- 2026-07-20 (rev. C0.0): Insert **C0.0 Communication Canon & Contracts** before treating C0.1 as foundation; expand **C2** to templates + automations + campaigns; PR #100 = vertical slice only.  
- 2026-07-20 (rev. Platform Completion Roadmap): Finish **full Epic C** (C0.2–C0.3, C1, C2) → **Governance Review** → Acquisition/Stage 3; horizon phases Forms → Workspace → Documents → Billing → AI.  
- 2026-07-20: PR #107 merged (`dbeb36ed`) — C1 queues + C1.1 ThreadContext; open **C1.2 Workspace Actions**.  
