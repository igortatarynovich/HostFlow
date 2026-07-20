# Sales → Communication — sequential product queue (locked)

**Status:** **NORMATIVE QUEUE** (one active product slice at a time)  
**Date:** 2026-07-20 (rev. C0.0 Communication Canon gate)  
**Trusted base:** `integration/release-product-a-b` (fast-forward only)  
**Parents:** [Pipeline v1 seal](../architecture/sales-domain-pipeline-v1.md) · [Creation Origins v1](../architecture/client-account-creation-origins-v1.md) · [C0.0 Communication Canon](c0-0-communication-canon.md) · [Epic C0](epic-c0-communication-integrity.md) · [Repository Operational Canon](../../governance/repository-operational-canon.md)

> Sales domain contracts are sealed. Product convert engine unification is complete (Stage 3 slice 2 / PR #99).  
> **Communication Integrity (Epic C0) runs before Stage 3 slice 3** — starting with **C0.0 Canon & Contracts**, then outbound foundation.  
> Communication does **not** cancel Flights / Stage 3; it prevents building Sales flow on unreliable messaging.

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

**Open product GAPs (queued below):**

- Communication Canon / contracts not yet normative SoT (C0.0)  
- Outbound platform incomplete vs canon (C0.1 vertical in PR #100; align after C0.0)  
- Inbound resolver leaves too many unlinked threads  
- `lead.communication.failed` vs Message/Delivery model  
- Meta intake drops / under-shows raw answers  
- Remaining SalesInquiry product flow (Stage 3 slice 3+)  
- Inbox UX not a usable work module  
- Templates / automations / campaigns product (Epic C2)  

---

## 2. Locked near-term sequence (no parallel product branches)

| # | Work | Branch (proposed) | Result |
|---|------|-------------------|--------|
| **1** | **C0.0** Communication Canon & Contracts | *(with PR #100)* | ✅ SoT + Intent-first contracts |
| **2** | **C0.1** First Canon implementation (outbound) | `fix/communication-c0-outbound-linkage` (**PR #100 merged**) | ✅ Intent → Policy → Resolvers → Command → Sender + G13 |
| **3** | **C0.1b** Intent Policy & Snapshot Hardening | `fix/communication-c0-intent-policy-hardening` (**PR #101 merged**) | ✅ Typed policies, full snapshot, writer migration map |
| **4** | **C0.2** Incoming resolver | `fix/communication-c0-inbound-resolver` (**current**) | Deterministic thread/entity or unresolved queue |
| **5** | **C0.3** Delivery diagnostics | `fix/communication-c0-delivery-diagnostics` | Failures explainable without server logs |
| **6** | Meta Intake Completeness | `fix/meta-intake-completeness` | Full Meta payload retained and visible |
| **7** | Stage 3 slice 3 | *(TBD thin Sales product flow)* | Full SalesInquiry product flow |
| **8** | **C1** Inbox UX | *(TBD)* | Simple working messages module |
| **9** | **C2** Templates, Automations & Campaigns | *(TBD)* | Catalog + rules + bulk on platform command |
| **10** | Stage 3 slice 4 | *(TBD)* | Hard module separation |

**C0.1** ✅ `f8569fa9` (PR #100). **C0.1b** ✅ `7bc13d57` (PR #101).  
**Active:** [C0.2 inbound resolver](c0-2-inbound-resolver.md) — every inbound linked or explicitly unresolved.

**Deferred polish (as needed):** signature policy product UI, composer UX thin slice, historical unbound-thread repair queue, Service Orders / quotes / deals.

**Supersedes (this revision):** queue that started Epic C0 at C0.1 without a canon gate; C2 scoped as campaigns-only.

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

### Slice 3+ — **blocked until C0 (+ Meta Intake)**

Do **not** start Stage 3 slice 3 while C0.0–C0.3 (and Meta Intake Completeness) are incomplete, unless this queue is explicitly amended.

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

## 5. Meta Intake Completeness (after C0)

**Task:** [meta-intake-completeness.md](meta-intake-completeness.md)

Separate from Communication. Chain: Meta payload → Submission raw → normalized → SalesInquiry → UI. No answer may disappear before normalization (show as additional answers).

---

## 6. Epic C1 — Inbox UX (after integrity + Meta)

Not a second CRM and not Settings. Working folders only (Inbox, Unread, Needs reply, Assigned to me, Sent, Archive, Unresolved). Thread title priority: company → contact name → email/phone → readable fallback (**never** UUID stubs). Settings / signatures / templates live under **Настройки → Коммуникации**.

---

## 6b. Epic C2 — Templates, Automations & Campaigns

**Task:** [epic-c2-communication-campaigns.md](epic-c2-communication-campaigns.md)

After C0 (+ C1 as queued): product surfaces for template catalog, automation rules, and campaigns — all calling the same platform command. Not a second send engine.

---

## 7. Development rule

Exactly **one** product slice active.

Next branch only after:

1. Current PR merged  
2. Fast-forward `integration/release-product-a-b`  
3. `make repo-health` **PASSED**  
4. Stale worktrees pruned  
5. One dedicated worktree  

**Do not** open Stage 3 slice 3, C1 Inbox, or C2 product branches while C0 is the active epic (unless this queue is explicitly amended).  
**Do not** expand PR #100 beyond the locked vertical slice; align-to-canon is a separate follow-up after C0.0 docs.

---

## 8. History

- 2026-07-20: Queue locked — Capability UI → Manual create → Pipeline wiring → Communication (old 4–7) → CRM.  
- 2026-07-20 (rev): After Stage 3 slice 2, insert **Epic C0 Communication Integrity** (C0.1–C0.3) + **Meta Intake Completeness** before Stage 3 slice 3; then C1 Inbox; then Stage 3 slice 4.  
- 2026-07-20 (rev. C0.0): Insert **C0.0 Communication Canon & Contracts** before treating C0.1 as foundation; expand **C2** to templates + automations + campaigns; PR #100 = vertical slice only.  
