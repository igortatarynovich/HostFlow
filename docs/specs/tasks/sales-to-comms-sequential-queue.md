# Sales → Communication — sequential product queue (locked)

**Status:** **NORMATIVE QUEUE** (one active **Product Track** slice; Engineering Track is background)  
**Date:** 2026-07-21 (rev. Product vs Engineering tracks)  
**Trusted base:** `integration/release-product-a-b` (fast-forward only)  
**Parents:** [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) · [C0.0 Communication Canon](c0-0-communication-canon.md) · [Repository Operational Canon](../../governance/repository-operational-canon.md)

> **2026-08-14 strategy:** Epic C + A2 **PASS_WITH_CONSTRAINTS**. Meta [#222](https://github.com/igortatarynovich/HostFlow/pull/222) · slice 3 [#224](https://github.com/igortatarynovich/HostFlow/pull/224) · slice 4 [#238](https://github.com/igortatarynovich/HostFlow/pull/238) merged. Forms C1–C5 ✅ ([#248](https://github.com/igortatarynovich/HostFlow/pull/248)). **Product Track:** [Forms Platform C6 — Optimization](forms-platform-c6-optimization.md) (feat). **Engineering Track** = legacy pytest / Catalog Notifications↔Communication RFC.  
> Communication **C2.4 frozen** (gate residual R1) — not Forms C2 / C3 / C4 / C5.  
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
| **Product** | **Forms Platform C6** Optimization — [brief](forms-platform-c6-optimization.md); C1–C5 ✅ [#248](https://github.com/igortatarynovich/HostFlow/pull/248); feat open | Almost all capacity |
| **Engineering** | [#127](https://github.com/igortatarynovich/HostFlow/pull/127) / [pytest baseline](stabilize-integration-pytest-baseline.md) (deferred); Catalog Notifications↔Communication RFC | Background; full-suite red is base debt — does not block Acquisition merges when Stage suites/gates are green |

**Open product GAPs:**

- **Acquisition Stage 3E / Activity Timeline** ← **DONE** (#130–#133) — [timeline](acquisition-stage-3e-activity-timeline.md); deferred gaps — [deferred](acquisition-stage-3e-deferred.md)  
- **Acquisition Stage 4 / Flight Runtime** ← **Runtime DONE** (#136 / #148–#151) — [stage-4](acquisition-stage-4-flight-runtime.md)  
- **Acquisition UI Cutover** ← **PASS** — [cutover](acquisition-ui-cutover.md) · [C-7](acquisition-ui-cutover-c7-searches-decommission.md) (C-1…C-7 closed 2026-07-27; Stage 5 PR-2 may resume)
- **FlightAdBinding Ad-ID bind UI** ← **DONE** (#187) — Campaign Detail Ad→Flight panel  
- **Source Diagnostics** ← **PR1–PR9 ✅** (#196–#212) — [brief](acquisition-source-diagnostics.md); Wave-1 notifications closed (SPA-only)  
- **Acquisition Stage 5 / Optimization** ← PR-1 DONE · **PR-2 DONE** (#203) — [stage-5](acquisition-stage-5-optimization.md)  
- **Acquisition Stage 6 Analytics** ← **DONE** (PR-1…PR-6b) — [brief](acquisition-stage-6-analytics.md) · [ownership](../../modules/acquisition/outcome-commercial-value-ownership.md)  
- C2.3 Campaign Orchestrator ← **DONE** (landed on tip; #121–#126 superseded; **#219**)  
- C2.4 Scheduling ← **frozen** (gate residual R1; do not start)  
- **Epic C Complete Gate** ← **PASS_WITH_CONSTRAINTS** (2026-08-03) — [gate](../gates/epic-c-complete-gate.md)  
- **A2 Platform Governance Review** ← **PASS_WITH_CONSTRAINTS** (2026-08-03) — [gate](../gates/platform-governance-review-a2.md)  
- **Meta intake completeness** ← **MERGED** [#222](https://github.com/igortatarynovich/HostFlow/pull/222) — [meta-intake-completeness.md](meta-intake-completeness.md)  
- **Stage 3 slice 3 — SalesInquiry product flow** ← **MERGED** [#224](https://github.com/igortatarynovich/HostFlow/pull/224) — [brief](stage-3-sales-inquiry-product-flow.md)  
- **Stage 3 slice 4 — hard module separation** ← ✅ [#238](https://github.com/igortatarynovich/HostFlow/pull/238) — [brief](stage-3-slice-4-hard-module-separation.md)  
- **Forms Platform C1 — contract seal** ← ✅ [#239](https://github.com/igortatarynovich/HostFlow/pull/239)/[#240](https://github.com/igortatarynovich/HostFlow/pull/240) — [brief](forms-platform-c1-contract-seal.md)  
- **Forms Platform C2 — Runtime Contract** ← ✅ [#241](https://github.com/igortatarynovich/HostFlow/pull/241)/[#242](https://github.com/igortatarynovich/HostFlow/pull/242) — [brief](forms-platform-c2-runtime-contract.md)  
- **Forms Platform C3 — Builder Runtime** ← ✅ [#243](https://github.com/igortatarynovich/HostFlow/pull/243)/[#244](https://github.com/igortatarynovich/HostFlow/pull/244) — [brief](forms-platform-c3-builder-runtime.md)
- **Forms Platform C4 — Form Runtime** ← ✅ [#245](https://github.com/igortatarynovich/HostFlow/pull/245)/[#246](https://github.com/igortatarynovich/HostFlow/pull/246) — [brief](forms-platform-c4-form-runtime.md); Runtime Model; not P3 Publish UI / P4 Themes / Sprint HTTP C4  
- **Forms Platform C5 — Form Execution** ← ✅ [#247](https://github.com/igortatarynovich/HostFlow/pull/247)/[#248](https://github.com/igortatarynovich/HostFlow/pull/248) — [brief](forms-platform-c5-form-execution.md)
- **Forms Platform C6 — Optimization** ← **active** (feat) — [brief](forms-platform-c6-optimization.md); not P3 Publish UI / P4 Themes / P5 Analytics / Acquisition Stage 5  
- Stage 5 settings/enable-disable · R6 table-cutover ← **out of this slice**

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
| **7c** | **C2.3** Campaign Orchestrator | `feat/communication-c2-3-land-on-tip` | ✅ Landed on tip (supersedes #121–#126) |
| **7c-eng** | CI / pytest debt | [#127](https://github.com/igortatarynovich/HostFlow/pull/127) · [stabilize](stabilize-integration-pytest-baseline.md) **deferred** | Engineering Track — base-known; not Product-blocking |
| **P-3E** | **Acquisition Stage 3E** Activity Timeline | PR #130–#133 ✅ | **DONE** — observability vertical closed; deferred — [3e-deferred](acquisition-stage-3e-deferred.md) |
| **P-4** | **Acquisition Stage 4** Flight Runtime | — | ✅ **Runtime DONE** (#136 / #148–#151) — [stage-4](acquisition-stage-4-flight-runtime.md) |
| **P-4b** | **Acquisition UI Cutover** | C-1…C-6 ✅ · **C-7 PASS** (#184 · #185 · inventory) | **PASS** — [C-7](acquisition-ui-cutover-c7-searches-decommission.md); Ad-ID bind ✅ #187 → **Diagnostics** — [cutover](acquisition-ui-cutover.md) |
| **P-5** | **Acquisition Stage 5** Optimization | PR-2 done | **PR-1 DONE** (#153) · **PR-2 DONE** (#203) — [stage-5](acquisition-stage-5-optimization.md) |
| **7d** | **C2.4** Scheduling | *(frozen)* | Do not start (gate residual R1) |
| **8** | **Epic C Complete Gate** | `docs/epic-c-complete-gate` | ✅ **PASS_WITH_CONSTRAINTS** (2026-08-03) |
| **8b** | **Compliance outbound (ADR-031)** | [compliance-outbound-pipeline-early-result](compliance-outbound-pipeline-early-result.md) | Early opaque result + RODO/ops binders; **Engineering track**; no SMTP bypass |
| **9** | **A2** Platform Governance Review | `docs/platform-governance-review-post-epic-c` | ✅ **PASS_WITH_CONSTRAINTS** — [gate](../gates/platform-governance-review-a2.md) |
| **10** | **Meta Intake Completeness** | `feat/meta-intake-completeness` | [#222](https://github.com/igortatarynovich/HostFlow/pull/222) ✅ merged — answers + B2B naming |
| **11** | **Stage 3 slice 3** SalesInquiry product flow | `feat/stage-3-slice-3-sales-inquiry-product-flow` | ✅ [#224](https://github.com/igortatarynovich/HostFlow/pull/224) — [brief](stage-3-sales-inquiry-product-flow.md) |
| **12** | **Stage 3 slice 4** hard module separation | `feat/stage-3-slice-4-hard-module-separation` | ✅ [#238](https://github.com/igortatarynovich/HostFlow/pull/238) |
| **13** | **Forms Platform C1** contract seal | `docs/forms-platform-c1-contract-seal` then `feat/…` | ✅ [#239](https://github.com/igortatarynovich/HostFlow/pull/239)/[#240](https://github.com/igortatarynovich/HostFlow/pull/240) |
| **14** | **Forms Platform C2** Runtime Contract & Gates | `docs/forms-platform-c2-runtime-contract` then `feat/…` | ✅ [#241](https://github.com/igortatarynovich/HostFlow/pull/241)/[#242](https://github.com/igortatarynovich/HostFlow/pull/242) |
| **15** | **Forms Platform C3** Builder Runtime | `docs/forms-platform-c3-builder-runtime` then `feat/…` | ✅ [#243](https://github.com/igortatarynovich/HostFlow/pull/243)/[#244](https://github.com/igortatarynovich/HostFlow/pull/244) |
| **16** | **Forms Platform C4** Form Runtime | `docs/forms-platform-c4-form-runtime` then `feat/…` | ✅ [#245](https://github.com/igortatarynovich/HostFlow/pull/245)/[#246](https://github.com/igortatarynovich/HostFlow/pull/246) |
| **17** | **Forms Platform C5** Form Execution | `docs/…` ✅ [#247](https://github.com/igortatarynovich/HostFlow/pull/247) · `feat/…` ✅ [#248](https://github.com/igortatarynovich/HostFlow/pull/248) | ✅ PASS-ready `c24bdc18` · merge `f6bbe03f` |
| **18** | **Forms Platform C6** Optimization | `docs/forms-platform-c6-optimization` ✅ [#249](https://github.com/igortatarynovich/HostFlow/pull/249) · `feat/forms-platform-c6-optimization` | **active** (feat) — [brief](forms-platform-c6-optimization.md); not P3 / P4 / P5 / Stage 5 / R6 |

**C0–C2.3** ✅. **C2.4 frozen.** **Epic C — complete.** **A2 — PASS_WITH_CONSTRAINTS.**  
**Active (Product):** Forms Platform C6 — [Optimization](forms-platform-c6-optimization.md) (feat). C1–C5 merged.  
**Engineering:** legacy full-repo pytest does **not** stop Product Track unless Product PR breaks deploy/Alembic/new-module bootstrap.

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

### Slice 3 — SalesInquiry product flow ✅

**Merged** [#224](https://github.com/igortatarynovich/HostFlow/pull/224) — [brief](stage-3-sales-inquiry-product-flow.md).  
Lead demotion on Sales path; SalesInquiry product identity; not full R6 / slice 4.

### Slice 4 — hard module separation ← **DONE** (#238)

[stage-3-slice-4-hard-module-separation.md](stage-3-slice-4-hard-module-separation.md). `/app/leads` is not a mixed inbox; `/app/leads/:id` redirects to SalesInquiry or Recruitment Application. Stage 5 settings and R6 stayed out.

### Forms Platform C1 — contract seal ← **DONE** (#239 / #240)

[forms-platform-c1-contract-seal.md](forms-platform-c1-contract-seal.md). Passport / Manifest / Public Contract / Adapter ids sealed.

### Forms Platform C2 — Runtime Contract ← **DONE** (#241 / #242)

[forms-platform-c2-runtime-contract.md](forms-platform-c2-runtime-contract.md). Contract Identity on publication versions; four named gates. Not Communication C2.4.

### Forms Platform C3 — Builder Runtime ← **DONE** (#243 / #244)

[forms-platform-c3-builder-runtime.md](forms-platform-c3-builder-runtime.md). Editor of FormDefinition; draft save ≠ publish. Named C3 gate SUCCESS at `2e5f9720`; merge `638955d5`.

### Forms Platform C4 — Form Runtime ← **DONE** (#245 / #246)

[forms-platform-c4-form-runtime.md](forms-platform-c4-form-runtime.md). Runtime, not an Engine. Adapter resolve → Runtime Model. Read-only. Dual Builder boundary. Named C4 gate SUCCESS at `626e5a9d`; merge `4427b110`.

### Forms Platform C5 — Form Execution ← **DONE** (#247 / #248)

[forms-platform-c5-form-execution.md](forms-platform-c5-form-execution.md). Runtime Model → Validation → Submission → Persistence. Named C5 gate SUCCESS at `c24bdc18`; merge `f6bbe03f`.

### Forms Platform C6 — Optimization ← **active** (feat)

[forms-platform-c6-optimization.md](forms-platform-c6-optimization.md). Production Shared Intake binds resolve → serve → execute; Forms Foundation close. Not P3 Publish UI / P4 Themes / P5 Analytics / Acquisition Stage 5.

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

## 5b. Epic C2 — Communication Capability Epic ← **closed (C2.4 frozen)**

**Epic:** [epic-c2-communication-campaigns.md](epic-c2-communication-campaigns.md)  
**Product active:** **A2 Platform Governance Review**. C2.1–C2.3 ✅; C2.4 = frozen (gate residual R1).

C2 is **not** Communication v2. Sole responsibility: emit `CommunicationIntent` into the existing platform pipeline.  
Order: Template Platform → Automation → Campaigns → Scheduling → Complete Gate.  
Merge gates: Intent-only egress · no second pipeline · capability isolation · frozen Thread model.

---

## 5c. A2 — Platform Governance Review ← **PASS_WITH_CONSTRAINTS**

Short L0 gate — [platform-governance-review-a2.md](../gates/platform-governance-review-a2.md) (2026-08-03).  
Catalog Notifications↔Communication deferred to Architecture RFC (A2-F1). **Next Product Track:** Meta Intake Completeness.

---

## 6. Meta Intake Completeness (Phase B) ← **MERGED #222**

**Task:** [meta-intake-completeness.md](meta-intake-completeness.md)

Separate from Communication. Chain: Meta payload → Submission raw → normalized → SalesInquiry → UI. No answer may disappear before normalization (show as additional answers). Runs **after** A2 (now closed).

---

## 7. Development rule

Exactly **one Product Track** slice active. Engineering Track may proceed in parallel without claiming Product Active.

Next branch only after:

1. Current PR merged  
2. Fast-forward `integration/release-product-a-b`  
3. `make repo-health` **PASSED**  
4. Stale worktrees pruned  
5. One dedicated worktree  

**Do not** start C2.4 (frozen; gate residual R1).  
**Do not** spend Product capacity on the 657 base-known pytest failures.  
**Do not** mix Stage 5 settings/enable-disable or R6 table-cutover into Forms.  
**Do not** start C5 **feat**, P3 Publish UI, P4 Themes, or P5 Analytics in this brief PR.  
**Do** amend this queue when switching Product Active (this revision: live = Forms C5 brief).

---

## 8. History

- 2026-08-14: C6 brief ✅ [#249](https://github.com/igortatarynovich/HostFlow/pull/249) (`28714fd7`); Product Track → **Forms Platform C6** feat — production resolve→serve→execute / Foundation close.
- 2026-08-14: C5 ✅ [#247](https://github.com/igortatarynovich/HostFlow/pull/247)/[#248](https://github.com/igortatarynovich/HostFlow/pull/248) (`f6bbe03f`); Product Track → **Forms Platform C6** — [brief](forms-platform-c6-optimization.md) (feat locked).
- 2026-08-14: C5 brief ✅ [#247](https://github.com/igortatarynovich/HostFlow/pull/247) (`0b39baa1`); Product Track → **Forms Platform C5** feat — [brief](forms-platform-c5-form-execution.md).
- 2026-08-14: C4 ✅ [#245](https://github.com/igortatarynovich/HostFlow/pull/245)/[#246](https://github.com/igortatarynovich/HostFlow/pull/246) (`4427b110`); Product Track → **Forms Platform C5** — [brief](forms-platform-c5-form-execution.md) (feat locked).
- 2026-08-14: C4 brief [#245](https://github.com/igortatarynovich/HostFlow/pull/245); Product Track → **Forms Platform C4 feat** — Runtime Model (read-only; not an Engine).
- 2026-08-14: C3 ✅ [#243](https://github.com/igortatarynovich/HostFlow/pull/243)/[#244](https://github.com/igortatarynovich/HostFlow/pull/244) (`638955d5`); Product Track → **Forms Platform C4** — [brief](forms-platform-c4-form-runtime.md) (feat locked).
- 2026-08-14: C1 ✅ [#239](https://github.com/igortatarynovich/HostFlow/pull/239)/[#240](https://github.com/igortatarynovich/HostFlow/pull/240); C2 ✅ [#241](https://github.com/igortatarynovich/HostFlow/pull/241)/[#242](https://github.com/igortatarynovich/HostFlow/pull/242); Product Track → **Forms Platform C3** — [brief](forms-platform-c3-builder-runtime.md).  
- 2026-08-13: Product Track → **Stage 3 slice 3** [#224](https://github.com/igortatarynovich/HostFlow/pull/224); Meta #222 merged.  
- 2026-08-03: **A2 PASS_WITH_CONSTRAINTS**; Product Track → **Meta Intake Completeness** (Phase B).  
- 2026-08-03: **Epic C Complete Gate PASS_WITH_CONSTRAINTS**; Product Track → **A2 Platform Governance Review**; C2.4 remains frozen.  
- 2026-08-13: Stage 3 slice 3 **✅ #224**; Product Track → **Stage 3 slice 4** hard module separation — [brief](stage-3-slice-4-hard-module-separation.md).  
- 2026-08-13: Stage 3 slice 4 ✅ [#238](https://github.com/igortatarynovich/HostFlow/pull/238); Product Track → **Forms Platform C1** — [brief](forms-platform-c1-contract-seal.md). Stage 5 settings and R6 stay out of this slice.  
- 2026-08-13: Sealed **Forms Platform C2** as next after C1 — [brief](forms-platform-c2-runtime-contract.md). Builder locked until C2 feat. Communication C2.4 remains frozen.  
- 2026-08-13: C2 brief correction — Contract Identity on publication versions only; `lifecycle_status` is Publication State; canonical schema hash; declared compatibility.  
- 2026-08-03: Stage 6 **PR-4 ✅ #216**; Product Track → **Stage 6 PR-5 month buckets**.  
- 2026-08-03: Stage 6 **PR-3 ✅ #215**; Product Track → **Stage 6 PR-4 portfolio**.  
- 2026-08-03: Stage 6 **PR-2 ✅ #214**; Product Track → **Stage 6 PR-3 week buckets**.  
- 2026-08-03: Stage 6 **PR-1 ✅ #213**; Product Track → **Stage 6 PR-2 windowed cohorts**.  
- 2026-08-03: Source Diagnostics **PR9 ✅ #212**; Product Track → **Stage 6 PR-1 Flight wave compare**.  
- 2026-08-02: Source Diagnostics **PR9** drift-summary Wave-1 (merged #212); SPA-only notifications closed.  
- 2026-08-02: Source Diagnostics **PR8 ✅ #210**; Product Track → **PR9 drift notification Wave-1**.  
- 2026-08-01: Source Diagnostics **PR7 ✅ #206**; Product Track → **PR8 replay submission**.  
- 2026-08-01: Source Diagnostics **PR6 ✅ #205**; Product Track → **PR7 Mapping Health drift alerts**.  
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
