# Sales → Communication — sequential product queue (locked)

**Status:** **NORMATIVE QUEUE** (one active product slice at a time)  
**Date:** 2026-07-20 (rev. C0 integrity insertion)  
**Trusted base:** `integration/release-product-a-b` (fast-forward only)  
**Parents:** [Pipeline v1 seal](../architecture/sales-domain-pipeline-v1.md) · [Creation Origins v1](../architecture/client-account-creation-origins-v1.md) · [Epic C0](epic-c0-communication-integrity.md) · [Repository Operational Canon](../../governance/repository-operational-canon.md)

> Sales domain contracts are sealed. Product convert engine unification is in flight (Stage 3 slice 2).  
> **Communication Integrity (Epic C0) is inserted before Stage 3 slice 3** — platform GAP: correspondence loses entity linkage.  
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
| Repository Health | ✅ required PASS before each new branch |

**Open product GAPs (queued below):**

- Dual convert entrypoints → single engine (Stage 3 slice 2 / PR #99)  
- Outbound threads without G13 entity links  
- Inbound resolver leaves too many unlinked threads  
- `lead.communication.failed` vs Message/Delivery model  
- Meta intake drops / under-shows raw answers  
- Remaining SalesInquiry product flow (Stage 3 slice 3+)  
- Inbox UX not a usable work module  

---

## 2. Locked near-term sequence (no parallel product branches)

| # | Work | Branch (proposed) | Result |
|---|------|-------------------|--------|
| **1** | Stage 3 slice 2 — convert entrypoints | `fix/sales-pipeline-v1-convert-entrypoints` (PR #99) | One product convert engine |
| **2** | **C0.1** Outbound linkage | `fix/communication-c0-outbound-linkage` | Outbound always entity-linked |
| **3** | **C0.2** Incoming resolver | `fix/communication-c0-inbound-resolver` | Replies land on correct thread/entity |
| **4** | **C0.3** Delivery diagnostics | `fix/communication-c0-delivery-diagnostics` | Failures explainable without server logs |
| **5** | Meta Intake Completeness | `fix/meta-intake-completeness` | Full Meta payload retained and visible |
| **6** | Stage 3 slice 3 | *(TBD thin Sales product flow)* | Full SalesInquiry product flow |
| **7** | **C1** Inbox UX | *(TBD)* | Simple working messages module |
| **8** | Stage 3 slice 4 | *(TBD)* | Hard module separation |

**Deferred (after C0 / as needed):** signature policy product polish, composer UX thin slice, historical unbound-thread repair queue, Service Orders / quotes / deals.

**Supersedes (this revision):** earlier rule “no Communication until all of Stage 3 closed”. Integrity slices C0.1–C0.3 run **after** Stage 3 slice 2 and **before** Stage 3 slice 3. Still **one** active product slice at a time.

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
Product convert → `convert_sales_inquiry_mapping`; Review SoT; mandatory audit; idempotent replay.

### Slice 2 — Convert entrypoints (**current / merge gate**)

**Branch:** `fix/sales-pipeline-v1-convert-entrypoints` · **PR #99** (draft)  
**Task:** [stage-3-sales-pipeline-convert-entrypoints.md](stage-3-sales-pipeline-convert-entrypoints.md)

- Lead `convert-client` = compatibility facade over mapping  
- FE → `convertSalesInquiryToClient`  
- **Do not mix** Communication code into this PR  
- After merge: FF integration, `make repo-health`, remove `/tmp/hf-convert-entrypoints`

### Slice 3+ — **blocked until C0 (+ Meta Intake)**

Do **not** start Stage 3 slice 3 immediately after #99. Resume Sales product flow only after C0.1–C0.3 and Meta Intake Completeness (or an explicit queue amendment).

---

## 4. Epic C0 — Communication Integrity (**next after #99**)

**Task:** [epic-c0-communication-integrity.md](epic-c0-communication-integrity.md)

| Slice | Focus | Acceptance (one line) |
|-------|--------|------------------------|
| **C0.1** | Guaranteed outbound linkage + G13 on send | Inquiry-sent mail appears in inquiry history immediately |
| **C0.2** | Inbound resolver / threading | Reply joins same thread on same entity |
| **C0.3** | Delivery diagnostics / history | One record explains send failure |

**Invariant (C0.1):**

```text
Entity → Communication Context → Thread Entity Link (G13) → Message Outbox → Provider
```

Outbound without entity link is forbidden. Convert adds ClientAccount link without deleting SalesInquiry link.

---

## 5. Meta Intake Completeness (after C0)

**Task:** [meta-intake-completeness.md](meta-intake-completeness.md)

Separate from Communication. Chain: Meta payload → Submission raw → normalized → SalesInquiry → UI. No answer may disappear before normalization (show as additional answers).

---

## 6. Epic C1 — Inbox UX (after integrity + Meta)

Not a second CRM and not Settings. Working folders only (Inbox, Unread, Needs reply, Assigned to me, Sent, Archive, Unresolved). Thread title priority: company → contact name → email/phone → readable fallback (**never** UUID stubs). Settings / signatures / templates live under **Настройки → Коммуникации**.

---

## 7. Development rule

Exactly **one** product slice active.

Next branch only after:

1. Current PR merged  
2. Fast-forward `integration/release-product-a-b`  
3. `make repo-health` **PASSED**  
4. Stale worktrees pruned  
5. One dedicated worktree  

**Do not** open Stage 3 slice 3, C1 Inbox, or signature/composer product branches while C0 is the active epic (unless this queue is explicitly amended).

---

## 8. History

- 2026-07-20: Queue locked — Capability UI → Manual create → Pipeline wiring → Communication (old 4–7) → CRM.  
- 2026-07-20 (rev): After Stage 3 slice 2, insert **Epic C0 Communication Integrity** (C0.1–C0.3) + **Meta Intake Completeness** before Stage 3 slice 3; then C1 Inbox; then Stage 3 slice 4. Integrity is a platform GAP, not cosmetics.
