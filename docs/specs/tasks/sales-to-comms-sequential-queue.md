# Sales → Communication — sequential product queue (locked)

**Status:** **NORMATIVE QUEUE** (one active **Product Track** slice; Engineering Track is background)  
**Date:** 2026-07-21 (rev. Product vs Engineering tracks)  
**Trusted base:** `integration/release-product-a-b` (fast-forward only)  
**Parents:** [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) · [C0.0 Communication Canon](c0-0-communication-canon.md) · [Repository Operational Canon](../../governance/repository-operational-canon.md)

> **2026-07-21 strategy:** Communication foundation is mature enough. **Product Track** = Acquisition Stage **3E — Activity Timeline** (`AcquisitionActivityEvent`). **Engineering Track** = legacy full-repo pytest / CI debt — must not stop Product unless clean deploy or a Product PR introduces breakage.  
> C2.4 **frozen**. C2.3 implementation complete — merge opportunistic on Engineering Track.  
> Base-known CI: same class as [acquisition-epic-p-base-known-ci-failures.md](acquisition-epic-p-base-known-ci-failures.md).

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

**Tracks:**

| Track | Active work | Rule |
|-------|-------------|------|
| **Product** | **Source Diagnostics PR2** (filters; PR1 ✅ #196) | Almost all capacity |
| **Engineering** | [#127](https://github.com/igortatarynovich/HostFlow/pull/127) / [pytest baseline](stabilize-integration-pytest-baseline.md) (deferred) | Background; full-suite red is base debt — does not block Acquisition merges when Stage suites/gates are green |

**Open product GAPs:**

- **Acquisition Stage 3E / Activity Timeline** ← **DONE** (#130–#133) — [timeline](acquisition-stage-3e-activity-timeline.md); deferred gaps — [deferred](acquisition-stage-3e-deferred.md)  
- **Acquisition Stage 4 / Flight Runtime** ← **Runtime DONE** (#136 / #148–#151) — [stage-4](acquisition-stage-4-flight-runtime.md)  
- **Acquisition UI Cutover** ← **PASS** — [cutover](acquisition-ui-cutover.md) · [C-7](acquisition-ui-cutover-c7-searches-decommission.md) (C-1…C-7 closed 2026-07-27; Stage 5 PR-2 may resume)
- **FlightAdBinding Ad-ID bind UI** ← **DONE** (#187) — Campaign Detail Ad→Flight panel  
- **Source Diagnostics** ← **ACTIVE Product Track** — [brief](acquisition-source-diagnostics.md) · [cutover](acquisition-ui-cutover.md#after-cutover--source-diagnostics-separate-product-epic)
- **Acquisition Stage 5 / Optimization** ← PR-1 DONE · **PR-2 may resume** after C-7 PASS — [stage-5](acquisition-stage-5-optimization.md)  
- **Acquisition Stage 6 Analytics** ← future horizon (ADR-024 §14.1); do not open while 5 incomplete  
- C2.3 stack merge + C2.4 + Epic C Complete Gate — Engineering / later Communication close-out (**C2.4 frozen**)  
- Meta intake completeness · Sales Stage 3 slice 3–4 — after Flight V1 vertical (3A–3E) as needed; see also 3E deferred D1–D2

---

## 2. Communication close-out (Phase A — not Product-blocking)

| # | Work | Branch (proposed) | Result |
|---|------|-------------------|--------|
| **1** | **C0.0** Communication Canon & Contracts | *(with PR #100)* | ✅ SoT + Intent-first contracts |
| **2** | **C0.1** First Canon implementation (outbound) | `fix/communication-c0-outbound-linkage` (**PR #100 merged**) | ✅ Intent → Policy → Resolvers → Command → Sender + G13 |
| **3** | **C0.1b** Intent Policy & Snapshot Hardening | `fix/communication-c0-intent-policy-hardening` (**PR #101 merged**) | ✅ Typed policies, full snapshot, writer migration map |
| **4** | **C0.2** Incoming resolver | `fix/communication-c0-inbound-resolver` (**PR #102 merged**) | ✅ Deterministic thread/entity or unresolved queue |
| **5** | **C0.3** Delivery diagnostics | `fix/communication-c0-delivery-diagnostics` (**PR #104 merged**) | ✅ Failures explainable without server logs |
| **6** | **C1** Communication Inbox Workspace | `feat/communication-c1-inbox-workspace` (**PR #107 merged**) | ✅ Queues + ThreadContext + capability Composer (C1.1) |
| **6b** | **C1.2** Workspace Actions | `feat/communication-c1-2-workspace-actions` (**PR #108**) | ✅ Commands → ThreadContext; concurrency; no mixed path |
| **6c** | **C1.3** Workspace Experience | `feat/communication-c1-3-workspace-experience` | ✅ Thread card UX; C1 closed 2026-07-21 (live Commands smoke) |
| **7** | **C2** Capability epic (Intent-only) | [epic-c2](epic-c2-communication-campaigns.md) | Creates `CommunicationIntent` only; never mutates Thread |
| **7a** | **C2.1** Template Platform | PR #110–#114 ✅ | Domain → Renderer → Registry → API → UI; `template_version_id` SoT |
| **7b** | **C2.2** Automation Engine | PR #116–#120 ✅ | Event → Rules → Policy → Intent (no provider/Thread) |
| **7c** | **C2.3** Campaign Orchestrator | PR #121–#126 — implementation complete; Engineering merge later | Audience + plan → Intent |
| **7c-eng** | CI / pytest debt | [#127](https://github.com/igortatarynovich/HostFlow/pull/127) · [stabilize](stabilize-integration-pytest-baseline.md) **deferred** | Engineering Track — base-known; not Product-blocking |
| **7d** | **C2.4** Scheduling | *(frozen)* | Do not start |
| **P-3E** | **Acquisition Stage 3E** Activity Timeline | PR #130–#133 ✅ | **DONE** — observability vertical closed; deferred — [3e-deferred](acquisition-stage-3e-deferred.md) |
| **P-4** | **Acquisition Stage 4** Flight Runtime | — | ✅ **Runtime DONE** (#136 / #148–#151) — [stage-4](acquisition-stage-4-flight-runtime.md) |
| **P-4b** | **Acquisition UI Cutover** | C-1…C-6 ✅ · **C-7 PASS** (#184 · #185 · inventory) | **PASS** — [C-7](acquisition-ui-cutover-c7-searches-decommission.md); Ad-ID bind ✅ #187 → **Diagnostics** — [cutover](acquisition-ui-cutover.md) |
| **P-5** | **Acquisition Stage 5** Optimization | paused | **PR-1 DONE** (#153) · **PR-2 PAUSED** until P-4b — [stage-5](acquisition-stage-5-optimization.md) |
| **8** | **Epic C Complete Gate** | after C2.3 merge + C2.4 (later) | Communication capability closed |
| **8b** | **Compliance outbound (ADR-031)** | [compliance-outbound-pipeline-early-result](compliance-outbound-pipeline-early-result.md) | Early opaque result + RODO/ops binders; **Engineering track**; no SMTP bypass |
| **9** | **A2** Platform Governance Review | after Epic C complete | Boundary principle |
| **10+** | Meta / Sales slices | after Flight V1 (3A–3E) as needed | Per roadmap |

**C0–C2.2** ✅. **C2.3** implemented (merge opportunistic). **C2.4 frozen.**  
**Active (Product):** **Source Diagnostics PR2** filters (PR1 ✅ [#196](https://github.com/igortatarynovich/HostFlow/pull/196); after Ad-ID [#187](https://github.com/igortatarynovich/HostFlow/pull/187)). Stage 5 PR-2 may resume.  
**Engineering:** legacy full-repo pytest does **not** stop Acquisition Product Track unless Product PR breaks deploy/Alembic/new-module bootstrap. Stage 4 merge (2026-07-23) accepted with known baseline debt — Stage 4 tests/gates green; full suite red outside scope.

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

- [C1](c1-communication-inbox-workspace.md) ✅ · [C1.1](c1-1-thread-context-composer.md) ✅ · [C1.2](c1-2-workspace-actions.md) ✅ · [C1.3](c1-3-workspace-experience.md) ✅  
- Live close-out: [C1 evidence in gate](../gates/epic-c-complete-gate.md#c1-close-out-evidence-2026-07-21)

---

## 5b. Epic C2 — Communication Capability Epic ← **parked (Engineering)**

**Epic:** [epic-c2-communication-campaigns.md](epic-c2-communication-campaigns.md)  
**Product active elsewhere:** [Stage 3E Activity Timeline](acquisition-stage-3e-activity-timeline.md). C2.3 merge + C2.4 = Engineering / later close-out.

C2 is **not** Communication v2. Sole responsibility: emit `CommunicationIntent` into the existing platform pipeline.  
Order: Template Platform → Automation → Campaigns → Scheduling → Complete Gate.  
Merge gates: Intent-only egress · no second pipeline · capability isolation · frozen Thread model.

---

## 5c. A2 — Platform Governance Review (after Epic C)

Short L0 gate — see [Platform Completion Roadmap § A2](../architecture/platform-completion-roadmap.md). Not a feature sprint.

---

## 6. Meta Intake Completeness (Phase B — with Acquisition)

**Task:** [meta-intake-completeness.md](meta-intake-completeness.md)

Separate from Communication. Chain: Meta payload → Submission raw → normalized → SalesInquiry → UI. No answer may disappear before normalization (show as additional answers). Runs **after** A2, before/with Stage 3 slice 3.

---

## 7. Development rule

Exactly **one Product Track** slice active. Engineering Track may proceed in parallel without claiming Product Active.

Next branch only after:

1. Current PR merged  
2. Fast-forward `integration/release-product-a-b`  
3. `make repo-health` **PASSED**  
4. Stale worktrees pruned  
5. One dedicated worktree  

**Do not** start C2.4 while Product Track is on Flights/Acquisition.  
**Do not** spend Product capacity on the 657 base-known pytest failures.  
**Do** amend this queue when switching Product Active (this revision: → Stage 4).

---

## 8. History

- 2026-07-20: Queue locked — Capability UI → Manual create → Pipeline wiring → Communication (old 4–7) → CRM.  
- 2026-07-21 (rev. tracks): **Product Track** = Acquisition Stage 3E; **Engineering Track** = legacy pytest/CI (#127/#128 deferred); C2.4 frozen; do not block Acquisition on 657 base-known fails.  
- 2026-07-21 (rev. 3E Activity Timeline): Product Track renamed/corrected — **Activity Timeline** (`AcquisitionActivityEvent`); Timeline ≠ event bus; PR 1–4; see [acquisition-stage-3e-activity-timeline.md](acquisition-stage-3e-activity-timeline.md).  
- 2026-07-21 (rev. Stage 3E vs 4): **3E = observability** (ends PR-4); **Stage 4 Flight Runtime = operations** queued next — [acquisition-stage-4-flight-runtime.md](acquisition-stage-4-flight-runtime.md); do not mix Launch/CRUD into 3E UI.  
- 2026-07-21 (rev. maturity ladder): Acquisition ladder locked — Observability (3E) → Operations (4) → Optimization (5) → Analytics (6); ADR-024 §14.1.  
- 2026-07-21 (rev. 3E DONE): Stage 3E closed (#130–#133); deferred backlog — [acquisition-stage-3e-deferred.md](acquisition-stage-3e-deferred.md); **Product Track → Stage 4**.  
- 2026-07-20 (rev): After Stage 3 slice 2, insert **Epic C0 Communication Integrity** (C0.1–C0.3) + **Meta Intake Completeness** before Stage 3 slice 3; then C1 Inbox; then Stage 3 slice 4.  
- 2026-07-20 (rev. C0.0): Insert **C0.0 Communication Canon & Contracts** before treating C0.1 as foundation; expand **C2** to templates + automations + campaigns; PR #100 = vertical slice only.  
- 2026-07-20 (rev. Platform Completion Roadmap): Finish **full Epic C** (C0.2–C0.3, C1, C2) → **Governance Review** → Acquisition/Stage 3; horizon phases Forms → Workspace → Documents → Billing → AI.  
- 2026-07-20: PR #107 merged (`dbeb36ed`) — C1 queues + C1.1 ThreadContext; open **C1.2 Workspace Actions**.  
