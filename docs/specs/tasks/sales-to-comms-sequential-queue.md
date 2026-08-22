# Sales → Communication — sequential product queue (locked)

**Status:** **NORMATIVE QUEUE** (one active **Product Track** slice; Engineering Track is background)  
**Date:** 2026-07-21 (rev. Product vs Engineering tracks)  
**Trusted base:** `integration/release-product-a-b` (fast-forward only)  
**Parents:** [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Goal Completion Gate](../gates/goal-completion-gate.md) · [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) · [C0.0 Communication Canon](c0-0-communication-canon.md) · [Repository Operational Canon](../../governance/repository-operational-canon.md)

> **2026-08-22:** Epic C + A2 **PASS_WITH_CONSTRAINTS**. Forms C1–C6 ✅ / Foundation ✅ ([#250](https://github.com/igortatarynovich/HostFlow/pull/250)). Entity Workspace D1–D9 brief-complete ([#268](https://github.com/igortatarynovich/HostFlow/pull/268)) and **goal-incomplete** vs original D ([audit](../gates/platform-scope-completeness-audit.md)). E1 ✅ ([#270](https://github.com/igortatarynovich/HostFlow/pull/270)). E2 ✅ ([#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276)). **Workspace Capability Platform Completion** [COMPLETE](../gates/workspace-capability-platform-complete.md) (**PASS**) on [#274](https://github.com/igortatarynovich/HostFlow/pull/274); G4 PASS (Recruitment Application) — **not** the Documents proof. Intermediate #273: [PASS_WITH_CONSTRAINTS](../gates/workspace-capability-platform-g1-g5-closeout.md). **Product Track:** [Documents Platform E4](documents-platform-e4-candidate-document-link.md) — brief; feat locked; Candidate Document Link (D4). E3 ✅ ([#278](https://github.com/igortatarynovich/HostFlow/pull/278); named First Consumer Bind Gate). Catalog unlock ≠ mass bind. Not mass D3–D9 bind. Not D10. Not a Recruitment rail patch. Not ListWorkspace. Entity Workspace ≠ Application Workspace. Documents Foundation stays 🔄. **Engineering Track** = legacy pytest / Catalog Notifications↔Communication RFC / Kit Baseline chrome sync.  
> Communication **C2.4 frozen** (gate residual R1).  
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
| **Product** | **Documents Platform E4** Candidate Document Link — [brief](documents-platform-e4-candidate-document-link.md); feat locked; D4 bind; D8 stays; D3 / D5–D7 / D9 stay unbound | Almost all capacity |
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
- **Forms Platform C6 — Optimization** ← ✅ [#249](https://github.com/igortatarynovich/HostFlow/pull/249)/[#250](https://github.com/igortatarynovich/HostFlow/pull/250) — [brief](forms-platform-c6-optimization.md); Forms Foundation ✅  
- **Entity Workspace D1 — Contract Seal** ← ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252) — [brief](entity-workspace-d1-contract-seal.md)  
- **Entity Workspace D2 — Composition Contract** ← ✅ [#253](https://github.com/igortatarynovich/HostFlow/pull/253)/[#254](https://github.com/igortatarynovich/HostFlow/pull/254) — [brief](entity-workspace-d2-composition-contract.md); named Composition Gate; slot catalog frozen; Documents reserved empty; no Passport  
- **Entity Workspace D3 — Consumer Cutover** ← ✅ [#255](https://github.com/igortatarynovich/HostFlow/pull/255)/[#256](https://github.com/igortatarynovich/HostFlow/pull/256) — [brief](entity-workspace-d3-consumer-cutover.md); named Cutover Gate; first consumer = Sales Inquiry  
- **Entity Workspace D4 — Candidate Cutover** ← ✅ [#257](https://github.com/igortatarynovich/HostFlow/pull/257)/[#258](https://github.com/igortatarynovich/HostFlow/pull/258) — [brief](entity-workspace-d4-candidate-cutover.md); Shell `documents` nav ≠ D2 `documents` enable  
- **Entity Workspace D5 — Client Cutover** ← ✅ [#259](https://github.com/igortatarynovich/HostFlow/pull/259)/[#260](https://github.com/igortatarynovich/HostFlow/pull/260) — [brief](entity-workspace-d5-client-cutover.md); named Cutover Gate; Client bound  
- **Entity Workspace D6 — Sales Order Cutover** ← ✅ [#261](https://github.com/igortatarynovich/HostFlow/pull/261)/[#262](https://github.com/igortatarynovich/HostFlow/pull/262) — [brief](entity-workspace-d6-sales-order-cutover.md); named Cutover Gate; Sales Order bound  
- **Entity Workspace D7 — Vacancy Cutover** ← ✅ [#263](https://github.com/igortatarynovich/HostFlow/pull/263)/[#264](https://github.com/igortatarynovich/HostFlow/pull/264) — [brief](entity-workspace-d7-vacancy-cutover.md); named Cutover Gate; Vacancy bound  
- **Entity Workspace D8 — HR Employee Cutover** ← ✅ [#265](https://github.com/igortatarynovich/HostFlow/pull/265)/[#266](https://github.com/igortatarynovich/HostFlow/pull/266) — [brief](entity-workspace-d8-hr-employee-cutover.md); named Cutover Gate; HR employee bound  
- **Entity Workspace D9 — Services Order Cutover** ← ✅ [#267](https://github.com/igortatarynovich/HostFlow/pull/267)/[#268](https://github.com/igortatarynovich/HostFlow/pull/268) — [brief](entity-workspace-d9-services-order-cutover.md); named Cutover Gate; Services order bound  
- **Documents Platform E1 — Contract Seal** ← ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269)/[#270](https://github.com/igortatarynovich/HostFlow/pull/270) — [brief](documents-platform-e1-contract-seal.md); named Contract Seal Gate; D2 `documents` stayed reserved  
- **Workspace Capability Platform Completion** ← **COMPLETE** ([PASS](../gates/workspace-capability-platform-complete.md) [#274](https://github.com/igortatarynovich/HostFlow/pull/274)) — intermediate [PASS_WITH_CONSTRAINTS](../gates/workspace-capability-platform-g1-g5-closeout.md) [#273](https://github.com/igortatarynovich/HostFlow/pull/273); G4 PASS; [brief](workspace-capability-platform-completion.md)  
- **Workspace Capability host runtime-equivalence** ← ✅ [#274](https://github.com/igortatarynovich/HostFlow/pull/274) — [brief](workspace-capability-host-runtime-equivalence.md); second host + Notes/Consent owner boundaries  
- **Documents Platform E2 — Public contract / D2 catalog enable** ← ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276) — [brief](documents-platform-e2-public-contract.md); catalog unlock ≠ consumer bind; named Public Contract Gate  
- **Documents Platform E3 — First Consumer Bind + Document Link SoT** ← ✅ [#277](https://github.com/igortatarynovich/HostFlow/pull/277)/[#278](https://github.com/igortatarynovich/HostFlow/pull/278) — [brief](documents-platform-e3-first-consumer-bind.md); first consumer = HR employee; named First Consumer Bind Gate  
- **Documents Platform E4 — Candidate Document Link** ← **active** (brief; feat locked) — [brief](documents-platform-e4-candidate-document-link.md); D4 consume path = Document Link; D8 stays; D3 / D5–D7 / D9 stay unbound; not column drop / not OCR / not Foundation ✅  
- **Documents Platform E5+** Remaining consumers / `candidate_id` drop / lifecycle ← **locked until E4 feat**  
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
| **18** | **Forms Platform C6** Optimization | `docs/…` ✅ [#249](https://github.com/igortatarynovich/HostFlow/pull/249) · `feat/…` ✅ [#250](https://github.com/igortatarynovich/HostFlow/pull/250) | ✅ Foundation close `e81e2a08` · merge `9933a835` |
| **19** | **Entity Workspace D1** Contract Seal | `docs/…` ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251) · `feat/…` ✅ [#252](https://github.com/igortatarynovich/HostFlow/pull/252) | ✅ Gate · merge `f0572257` |
| **20** | **Entity Workspace D2** Composition Contract | `docs/…` ✅ [#253](https://github.com/igortatarynovich/HostFlow/pull/253) · `feat/…` ✅ [#254](https://github.com/igortatarynovich/HostFlow/pull/254) | ✅ named Composition Gate · merge `a61543cf` |
| **21** | **Entity Workspace D3** Consumer cutover | `docs/…` ✅ [#255](https://github.com/igortatarynovich/HostFlow/pull/255) · `feat/…` ✅ [#256](https://github.com/igortatarynovich/HostFlow/pull/256) | ✅ named Cutover Gate · merge `c30b07f8` |
| **22** | **Entity Workspace D4** Candidate cutover | `docs/…` ✅ [#257](https://github.com/igortatarynovich/HostFlow/pull/257) · `feat/…` ✅ [#258](https://github.com/igortatarynovich/HostFlow/pull/258) | ✅ named Cutover Gate · merge `b5f1f00a` |
| **23** | **Entity Workspace D5** Client cutover | `docs/…` ✅ [#259](https://github.com/igortatarynovich/HostFlow/pull/259) · `feat/…` ✅ [#260](https://github.com/igortatarynovich/HostFlow/pull/260) | ✅ named Cutover Gate · merge `069f441d` |
| **24** | **Entity Workspace D6** Sales Order cutover | `docs/…` ✅ [#261](https://github.com/igortatarynovich/HostFlow/pull/261) · `feat/…` ✅ [#262](https://github.com/igortatarynovich/HostFlow/pull/262) | ✅ named Cutover Gate · merge `bc819768` |
| **25** | **Entity Workspace D7** Vacancy cutover | `docs/…` ✅ [#263](https://github.com/igortatarynovich/HostFlow/pull/263) · `feat/…` ✅ [#264](https://github.com/igortatarynovich/HostFlow/pull/264) | ✅ named Cutover Gate · merge `7484f98e` |
| **26** | **Entity Workspace D8** HR employee cutover | `docs/…` ✅ [#265](https://github.com/igortatarynovich/HostFlow/pull/265) · `feat/…` ✅ [#266](https://github.com/igortatarynovich/HostFlow/pull/266) | ✅ named Cutover Gate · merge `fae8202e` |
| **27** | **Entity Workspace D9** Services `/app/orders` | `docs/…` ✅ [#267](https://github.com/igortatarynovich/HostFlow/pull/267) · `feat/…` ✅ [#268](https://github.com/igortatarynovich/HostFlow/pull/268) | ✅ named Cutover Gate · merge `28978a1f` |
| **28** | **Documents Platform E1** Contract Seal | `docs/…` ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269) · `feat/…` ✅ [#270](https://github.com/igortatarynovich/HostFlow/pull/270) | ✅ named Contract Seal Gate · merge `f37deff1` |
| **29** | **Workspace Capability Platform Completion** | `feat/workspace-capability-platform-completion` | **COMPLETE** [#274](https://github.com/igortatarynovich/HostFlow/pull/274) — G4 PASS; [COMPLETE](../gates/workspace-capability-platform-complete.md) · intermediate [PASS_WITH_CONSTRAINTS](../gates/workspace-capability-platform-g1-g5-closeout.md) [#273](https://github.com/igortatarynovich/HostFlow/pull/273) · [brief](workspace-capability-platform-completion.md) · [inventory](workspace-capability-legacy-inventory.md) |
| **29b** | **Workspace Capability host runtime-equivalence** | `feat/workspace-capability-host-runtime-equivalence` | ✅ [#274](https://github.com/igortatarynovich/HostFlow/pull/274) — [brief](workspace-capability-host-runtime-equivalence.md) |
| **30** | **Documents Platform E2** Public contract / D2 catalog enable | `docs/…` ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271) · `feat/…` ✅ [#276](https://github.com/igortatarynovich/HostFlow/pull/276) | ✅ named Public Contract Gate · merge `826877b5` |
| **31** | **Documents Platform E3** First consumer bind + Document Link SoT | `docs/…` ✅ [#277](https://github.com/igortatarynovich/HostFlow/pull/277) · `feat/…` ✅ [#278](https://github.com/igortatarynovich/HostFlow/pull/278) | ✅ named First Consumer Bind Gate · merge `cc106a38` |
| **32** | **Documents Platform E4** Candidate Document Link | `docs/…` | **active** (brief; feat locked) — [brief](documents-platform-e4-candidate-document-link.md); D4 bind; not mass D3–D9 |
| **33** | **Documents Platform E5+** Remaining consumers / `candidate_id` drop / lifecycle | locked | until E4 feat |

**C0–C2.3** ✅. **C2.4 frozen.** **Epic C — complete.** **A2 — PASS_WITH_CONSTRAINTS.** Forms Foundation ✅. D1–D9 brief-complete / goal-incomplete.  
**Active (Product):** Documents Platform E4 — [Candidate Document Link](documents-platform-e4-candidate-document-link.md) (brief; feat locked). D4 consume path = Document Link. E3 ✅ [#278](https://github.com/igortatarynovich/HostFlow/pull/278) (named First Consumer Bind Gate). E2 ✅. WCP [COMPLETE](../gates/workspace-capability-platform-complete.md). E1 ✅. D8 stays bound. D3 / D5–D7 / D9 stay unbound. G4 stays Recruitment Application. Foundation stays 🔄. E5+ locked until this feat.  
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

### Forms Platform C6 — Optimization ← **DONE** (#249 / #250)

[forms-platform-c6-optimization.md](forms-platform-c6-optimization.md). Production Shared Intake binds resolve → serve → execute; Forms Foundation ✅. Named C6 gate; merge `9933a835` / `e81e2a08`.

### Entity Workspace D1 — Contract Seal ← **DONE** (#251 / #252)

[entity-workspace-d1-contract-seal.md](entity-workspace-d1-contract-seal.md). Ownership + boundary. Named D1 Contract Seal Gate. Merge `f0572257` / `3375adf1`.

### Entity Workspace D2 — Composition Contract ← **DONE** (#253 / #254)

[entity-workspace-d2-composition-contract.md](entity-workspace-d2-composition-contract.md). Slot catalog frozen (overview / timeline / communication / forms / documents-reserved / context-rail). Named D2 Composition Gate. No cutover UI. No Catalog Passport. Documents reserved until a named Phase E slice after E1. Merge `a61543cf` / `42bd51b7`.

### Entity Workspace D3 — Consumer cutover ← **DONE** (#255 / #256)

[entity-workspace-d3-consumer-cutover.md](entity-workspace-d3-consumer-cutover.md). First consumer = Sales Inquiry bound to D2 slots. Named D3 Cutover Gate. Merge `c30b07f8` / `bdaeb47b`.

### Entity Workspace D4 — Candidate cutover ← **DONE** (#257 / #258)

[entity-workspace-d4-candidate-cutover.md](entity-workspace-d4-candidate-cutover.md). Candidate binds to D2 enabled slots. Shell `documents` nav ≠ D2 `documents` enable. Named D4 Cutover Gate. Merge `b5f1f00a` / `0ab40717`.

### Entity Workspace D5 — Client cutover ← **DONE** (#259 / #260)

[entity-workspace-d5-client-cutover.md](entity-workspace-d5-client-cutover.md). Client binds to D2 enabled slots. Named D5 Cutover Gate. Merge `069f441d` / `64289c22`.

### Entity Workspace D6 — Sales Order cutover ← **DONE** (#261 / #262)

[entity-workspace-d6-sales-order-cutover.md](entity-workspace-d6-sales-order-cutover.md). Sales Order (`SalesOrder` / `/app/sales/orders/:id`) binds to D2 enabled slots. Named D6 Cutover Gate. Merge `bc819768` / `346f6fcc`.

### Entity Workspace D7 — Vacancy cutover ← **DONE** (#263 / #264)

[entity-workspace-d7-vacancy-cutover.md](entity-workspace-d7-vacancy-cutover.md). Vacancy (`Vacancy` / `/app/vacancies/:id`) binds to D2 enabled slots. Named D7 Cutover Gate. Merge `7484f98e` / `9582c00d`.

### Entity Workspace D8 — HR employee cutover ← **DONE** (#265 / #266)

[entity-workspace-d8-hr-employee-cutover.md](entity-workspace-d8-hr-employee-cutover.md). HR employee (`HrEmployeeDetailPage` / `/app/hr/employees/:employeeId`) binds to D2 enabled slots. Named D8 Cutover Gate. Merge `fae8202e` / `24d758f0`.

### Entity Workspace D9 — Services order cutover ← **DONE** (#267 / #268)

[entity-workspace-d9-services-order-cutover.md](entity-workspace-d9-services-order-cutover.md). Services order (`ServicesPage` / `/app/orders` · `service_order`) binds to D2 enabled slots. Named D9 Cutover Gate. Merge `28978a1f`. `HrHandoffDetailPage` out.

### Documents Platform E1 — Contract Seal ← **DONE** (#269 / #270)

[documents-platform-e1-contract-seal.md](documents-platform-e1-contract-seal.md). Ownership + Hub ≠ dossier ≠ D2 enable. Named E1 Contract Seal Gate (CI: 11 passed). D2 `documents` stayed reserved. Merge `f37deff1`. Full-repo Tests with coverage 484 failed / 2740 passed — Engineering Track, same as D9.

### Workspace Capability Platform Completion ← **COMPLETE** (#274)

[workspace-capability-platform-completion.md](workspace-capability-platform-completion.md). Capability Host Contract: host places, owners own semantics. Entity Workspace ≠ Application Workspace. G4 PASS = Recruitment Application (`ApplicationWorkspaceCapabilityHost`). Final [G1–G5](../gates/workspace-capability-platform-complete.md): program **COMPLETE**. Intermediate [#273](https://github.com/igortatarynovich/HostFlow/pull/273): [PASS_WITH_CONSTRAINTS](../gates/workspace-capability-platform-g1-g5-closeout.md). [Inventory](workspace-capability-legacy-inventory.md). ListWorkspace is a separate previous slice.

### Workspace Capability host runtime-equivalence ← **DONE** (#274)

[workspace-capability-host-runtime-equivalence.md](workspace-capability-host-runtime-equivalence.md). `EntityWorkspaceCapabilityHost` + Notes/Consent owner facades (no Lead / candidate-notes API in capability UI). Not a new proof-screen. Not a new widget. Documents E2 feat unlocked by program COMPLETE.

### Documents Platform E2 — Public contract / D2 catalog enable ← **DONE** (#271 / #276)

[documents-platform-e2-public-contract.md](documents-platform-e2-public-contract.md) [#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276). `documents.public_contract.v1` + D2 catalog unlock. D3–D9 stayed unbound. Merge `826877b5`. Foundation stayed 🔄.

### Documents Platform E3 — First Consumer Bind + Document Link SoT ← **DONE** (#277 / #278)

[documents-platform-e3-first-consumer-bind.md](documents-platform-e3-first-consumer-bind.md) [#277](https://github.com/igortatarynovich/HostFlow/pull/277)/[#278](https://github.com/igortatarynovich/HostFlow/pull/278). One named consumer (HR employee / D8) receives documents via D2 `documents` surface + `documents.hub_adapter_v1` + `document_entity_links`. Merge `cc106a38`. Foundation stayed 🔄.

### Documents Platform E4 — Candidate Document Link ← **active** (brief; feat locked)

[documents-platform-e4-candidate-document-link.md](documents-platform-e4-candidate-document-link.md). Candidate (D4) consume path = Hub `document_entity_links` (`candidate` / `primary`). Not `candidate_id` list. Not Shell nav. Not mass D3–D9 bind. D8 stays bound. Column stays. Foundation stays 🔄.

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
**Do not** mix Stage 5 settings/enable-disable or R6 table-cutover into Documents.  
**Do not** treat Shell/chrome or D1–D9 named gates as original Entity Platform done; **do not** mix E4 into an E3/E2/WCP PR; **do not** multiply new entity/application screens, rails, or D10 cutovers; **do not** fold Application Workspace into Entity Workspace; **do not** treat E3 HR bind as mass D3–D9 `documents` bind; **do not** treat Shell `documents` nav, Vacancy docs section, HR dossier, CandidateCard, or Services billing tab as the D2 `documents` slot; **do not** treat Recruitment Application G4 as the Documents proof; **do not** start OCR / e-sign / packages / Forms P3–P5 / Billing / AI; **do not** drop `documents.candidate_id` in E4; **do not** patch Recruitment RODO/comments as the platform fix; **do not** mix ListWorkspace into this close-out.  
**Do** apply [Goal Completion Gate](../gates/goal-completion-gate.md) before marking a future platform phase COMPLETE.  
**Do** require `**Phase class:** platform` + [Original Goal → Completion Proof](../gates/goal-completion-gate.md) on every new platform phase brief (problem to permanently remove + named consumer — not a deliverables list).  
**Do** amend this queue when switching Product Active (this revision: live = Documents Platform E4 brief; feat locked).

---

## 8. History

- 2026-08-22: E4 brief opened — Candidate Document Link (D4). Product Track → [Documents Platform E4](documents-platform-e4-candidate-document-link.md) (feat locked). E3 ✅ [#278](https://github.com/igortatarynovich/HostFlow/pull/278) (`cc106a38`). D3 / D5–D7 / D9 stay unbound. Foundation stays 🔄.
- 2026-08-22: E3 feat opened — D8 bind + entity-link resolve on `documents.hub_adapter_v1`; named First Consumer Bind Gate. Product Track stays [Documents Platform E3](documents-platform-e3-first-consumer-bind.md). E4+ locked. Foundation stays 🔄.
- 2026-08-22: E3 brief opened — first consumer bind = HR employee + Document Link SoT. Product Track → [Documents Platform E3](documents-platform-e3-first-consumer-bind.md) (feat locked). E2 ✅ [#276](https://github.com/igortatarynovich/HostFlow/pull/276) (`826877b5`). G4 stays Recruitment Application. Foundation stays 🔄.
- 2026-08-22: E2 feat — `documents.public_contract.v1` / `documents.hub_adapter_v1`; D2 `documents` catalog enabled; D3–D9 unbound; named Public Contract Gate. Foundation stays 🔄. After [#273](https://github.com/igortatarynovich/HostFlow/pull/273)/[#274](https://github.com/igortatarynovich/HostFlow/pull/274) merge `84a2ea94`.
- 2026-08-21: WCP program **COMPLETE** ([#274](https://github.com/igortatarynovich/HostFlow/pull/274) · [record](../gates/workspace-capability-platform-complete.md)). G1 PASS. Product Track → [Documents Platform E2](documents-platform-e2-public-contract.md) (feat unlocked, not started). G4 remains Recruitment Application.
- 2026-08-21: WCP G1–G5 close-out **PASS_WITH_CONSTRAINTS** ([#273](https://github.com/igortatarynovich/HostFlow/pull/273) · [record](../gates/workspace-capability-platform-g1-g5-closeout.md)). G4 PASS. Program **not COMPLETE**. Product Track → [host runtime-equivalence](workspace-capability-host-runtime-equivalence.md). E2 stays locked until COMPLETE. ListWorkspace not this close-out.  
- 2026-08-20: **Goal substitution** on D caught. Queue: [Goal Completion Gate](../gates/goal-completion-gate.md) + [scope audit](../gates/platform-scope-completeness-audit.md) + **Entity Platform Completion** ([brief](workspace-capability-platform-completion.md); feat locked). Same-day Shared UI Capabilities (Notes+Consent, no registry) draft superseded. Documents E2 brief stays ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271); **E2 feat locked**. Not D10.  
- 2026-08-20: Brief retitled **Workspace Capability Platform Completion**. Capability Host Contract; Entity ≠ Application; proof locked to Recruitment Application. Same-day Entity Platform Completion draft (Shell owns commons; Candidate-or-Recruitment proof) superseded in place.
- 2026-08-18: E1 feat [#270](https://github.com/igortatarynovich/HostFlow/pull/270) (`f37deff1`); named gate 11 passed; full Tests with coverage 484 failed / 2740 passed (Engineering Track, same as D9). Product Track → **Documents Platform E2** ([brief](documents-platform-e2-public-contract.md) [#271](https://github.com/igortatarynovich/HostFlow/pull/271); feat locked). Catalog unlock ≠ D3–D9 bind.
- 2026-08-18: E1 brief ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269) (`17bd3dd3`); Product Track → **Documents Platform E1** feat (named Contract Seal Gate). D2 `documents` stays reserved. E2+ locked.
- 2026-08-18: D9 ✅ [#267](https://github.com/igortatarynovich/HostFlow/pull/267)/[#268](https://github.com/igortatarynovich/HostFlow/pull/268) (`28978a1f`); Product Track → **Documents Platform E1** ([brief](documents-platform-e1-contract-seal.md); feat locked). D2 `documents` stays reserved.
- 2026-08-17: D9 feat — named **Entity Workspace D9 Cutover Gate**; Services order bound to D2 slots; Product Track → D9 feat; next = Documents Phase E (locked).
- 2026-08-17: D9 brief opened — Services order cutover; Product Track → **Entity Workspace D9** (feat locked). D8 ✅ [#265](https://github.com/igortatarynovich/HostFlow/pull/265)/[#266](https://github.com/igortatarynovich/HostFlow/pull/266) (`fae8202e`).
- 2026-08-17: D8 feat — named **Entity Workspace D8 Cutover Gate**; HR employee bound to D2 slots; Product Track → D8 feat; next = D9 brief (locked).
- 2026-08-17: D8 brief opened — HR employee cutover; Product Track → **Entity Workspace D8** (feat locked). D7 ✅ [#263](https://github.com/igortatarynovich/HostFlow/pull/263)/[#264](https://github.com/igortatarynovich/HostFlow/pull/264) (`7484f98e`).
- 2026-08-15: D7 feat — named **Entity Workspace D7 Cutover Gate**; Vacancy bound to D2 slots; Product Track → D7 feat; next = D8 brief (locked).
- 2026-08-15: D7 brief opened — Vacancy cutover; Product Track → **Entity Workspace D7** (feat locked). D6 ✅ [#261](https://github.com/igortatarynovich/HostFlow/pull/261)/[#262](https://github.com/igortatarynovich/HostFlow/pull/262) (`bc819768`).
- 2026-08-15: D6 feat — named **Entity Workspace D6 Cutover Gate**; Sales Order bound to D2 slots; Product Track → D6 feat; next = D7 brief (locked).
- 2026-08-15: D6 brief opened — Sales Order cutover; Product Track → **Entity Workspace D6** (feat locked). D5 ✅ [#259](https://github.com/igortatarynovich/HostFlow/pull/259)/[#260](https://github.com/igortatarynovich/HostFlow/pull/260) (`069f441d`).
- 2026-08-15: D5 feat — named **Entity Workspace D5 Cutover Gate**; Client bound to D2 slots; Product Track → D5 feat; next = D6 brief (locked).
- 2026-08-15: D5 brief ✅ [#259](https://github.com/igortatarynovich/HostFlow/pull/259) (`6a11785b`); Product Track → **Entity Workspace D5** feat.
- 2026-08-15: D4 ✅ [#257](https://github.com/igortatarynovich/HostFlow/pull/257)/[#258](https://github.com/igortatarynovich/HostFlow/pull/258) (`b5f1f00a`); Product Track → **Entity Workspace D5** — [brief](entity-workspace-d5-client-cutover.md) (feat locked).
- 2026-08-15: D4 brief ✅ [#257](https://github.com/igortatarynovich/HostFlow/pull/257) (`cb543e68`); Product Track → **Entity Workspace D4** feat.
- 2026-08-15: D3 ✅ [#255](https://github.com/igortatarynovich/HostFlow/pull/255)/[#256](https://github.com/igortatarynovich/HostFlow/pull/256) (`c30b07f8`); Product Track → **Entity Workspace D4** — [brief](entity-workspace-d4-candidate-cutover.md) (feat locked).
- 2026-08-15: D2 ✅ [#253](https://github.com/igortatarynovich/HostFlow/pull/253)/[#254](https://github.com/igortatarynovich/HostFlow/pull/254) (`a61543cf`); Product Track → **Entity Workspace D3** — [brief](entity-workspace-d3-consumer-cutover.md) (feat locked).
- 2026-08-15: D2 feat — named **Entity Workspace D2 Composition Gate**; slot allowlist frozen; Product Track → D2 ✅; next = D3 cutover brief (locked).
- 2026-08-14: D1 ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252) (`f0572257`); Product Track → **Entity Workspace D2** — [brief](entity-workspace-d2-composition-contract.md) (feat locked).
- 2026-08-14: D1 feat — named **Entity Workspace D1 Contract Seal Gate**; D1 ✅; Product Track → open D2 composition brief (locked).
- 2026-08-14: D1 brief ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251) (`658c63b0`); Product Track → **Entity Workspace D1** feat.
- 2026-08-14: C6 ✅ [#249](https://github.com/igortatarynovich/HostFlow/pull/249)/[#250](https://github.com/igortatarynovich/HostFlow/pull/250) (`e81e2a08` / merge `9933a835`); Forms Foundation ✅; Product Track → **Entity Workspace D1** — [brief](entity-workspace-d1-contract-seal.md) (feat locked).
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
