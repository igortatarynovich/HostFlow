# v1 Release DAG — Dependency-Position Review

**Status:** **REVIEW** (evidence for the next queue amendment; does **not** schedule Product)  
**Date:** 2026-08-26  
**Trusted base:** `integration/release-product-a-b` @ `32e68b5d` ([#327](https://github.com/igortatarynovich/HostFlow/pull/327) merged)  
**Parents:** [HostFlow v1 Release Goal](hostflow-v1-release-goal.md) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md) · [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [Handoff contract](../architecture/handoff-contract.md)  
**Product Track:** **none at review time** (this file did not queue a slice). Consumed by [RPM-1 schedule](../tasks/requirement-policy-management.md) in the sequential queue.

> Grain: the five [Release DAG](hostflow-v1-release-goal.md) blocker **capabilities**.  
> Question: which **one** node may become the first Product, and why the other four cannot or should not precede it.  
> Not: a total order of the five. Not: a Product brief. Unlock ≠ schedule.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After [#327](https://github.com/igortatarynovich/HostFlow/pull/327) the Release Goal is L2 and Product Track is none, but the next queue amendment has no evidence for cutting **one** DAG node. Without this review the amendment will invent a linear program (RPM → Mapping → Intake → Hiring → HR), pick a Phase E leftover, or start the node that “feels first.”

**Completion proof (named consumer):**  
The docs-only queue amendment that cites this review — [Requirement Policy Management](../tasks/requirement-policy-management.md). It may not treat this review as the schedule.

---

## Method

Each blocker is scored on three axes. Axes are not averaged into a rank of five.

| Axis | Meaning | Not |
|------|---------|-----|
| **Hard acceptance dependencies** | What must already be true before **this** capability’s release acceptance can pass. Includes the three [known acceptance edges](hostflow-v1-release-goal.md). Supporting capabilities (Company setup, Acquisition, Candidate workspace, Communications, Permissions) stay dependencies, not extra DAG nodes. | Nice-to-have sequencing; roadmap horizon letters |
| **Downstream unlocks** | Which other **v1 blocker** acceptance scenarios become runnable after this capability has an operator-managed authority. Transitive unlocks count. | “The product will feel more complete” |
| **Collapse of parallel authorities / workarounds** | How many live answerers currently reply to the **same operator question**, and whether the first Product would force them onto one authority (or an explicit contract between answerers). | Unifying unrelated editors that answer different questions |

**Startable** = no hard predecessor **among the five**. Two nodes are startable. One Active Product still applies: startable ≠ parallel tracks.

Evidence is repo canon + runtime inventory after E8-eval / R5 (same snapshot as the Goal four-check table). Not a live tenant walkthrough. Not acceptance.

---

## Recommendation (not a schedule)

**First Product should be Requirement Policy Management.**

The other four cannot or should not precede it:

| Node | May it go first? | Why |
|------|------------------|-----|
| **Requirement Policy Management** | **Yes — recommended** | Startable. Highest collapse (nine live answers to “must this candidate provide X?”). Unlocks Hiring E2E and, transitively, min HR handoff. E8-eval’s release delta left this OPEN on purpose. |
| **Mapping Authority** | Startable, **should not precede** | No hard edge from RPM (the Goal already says that is unproven). Partial operator surfaces already exist. Three mapping **models** (Sales convert, CL6 Flight map, intake/P9/Meta) answer different source→dest pairs; they are not nine contradictory answers to one question. Choosing Mapping first parks the highest-collapse gap and keeps Hiring/HR unprovable for a whole program. Write-set non-overlap does **not** mint a third track. |
| **External Intake / Forms Publish** | **Cannot** | Hard edge: Mapping Authority → Intake. Acceptance is `publish → … → mapping → canonical entity`. |
| **Hiring workflow E2E** | **Cannot** | Hard edge: RPM → Hiring. Walking `stage → docs → eligibility → transfer` against funnels/gates/transfer **without** policy authority is the false close the Goal forbids. |
| **Minimal Recruitment → HR handoff** | **Cannot** | Hard edge: Hiring E2E → min HR. Handoff acceptance needs a completed hire/transfer of one person. Not blocked on Forms (Goal: unproven). |

This is **not** a total order. After RPM is queued and closed, Mapping remains a separate startable node; Intake remains behind Mapping; Hiring remains behind RPM; min HR remains behind Hiring. Limited parallelism of Mapping vs a later RPM leftover is a **later** queue decision, not this review.

---

## Per-capability results

### 1. Requirement Policy Management

**v1 acceptance (Goal):** for this tenant / client / vacancy / profile / country: these requirements apply; base rule; override; reason; result. Documents is the **first domain** — not a second Documents Admin vs Rules Admin.

| Axis | Result |
|------|--------|
| **Hard acceptance dependencies** | **None among the five.** Supporting: Company setup and Permissions sufficient to operate a policy surface. R5 `merge(pack, tenant_delta)` and E8-eval D4 bind already exist as evaluation runtime — they are **inputs**, not blockers. Overlay stays a typed CL7 vacancy delta (different write-set), not a second RPM product. |
| **Downstream unlocks** | **Hiring E2E** directly (known edge). **Min HR handoff** transitively (Hiring → HR). Mapping and Intake do **not** consume RPM for their own acceptance (Goal: unproven). Finite criterion lines unlocked: “operator-managed requirements and documents” and, later, the hiring/transfer/employee walk. |
| **Collapse** | **High — nine live answerers** to “must this candidate provide type X?”: (1) R5 pack + `tenant_delta` (canonical for E8-eval only), (2) leftover `sample_ruleset.json` / seeded `document_ruleset_versions`, (3) Hub `DOCUMENT_PACK_DEFINITIONS`, (4) DB `ref_packs` consumed by transfer policy, (5) ADR-018 requirement graph / Engine packs, (6) `document_applicability_policy.py`, (7) Vacancy Overlay + screening pack (vacancy delta, not R5 merge), (8) hiring pipeline gates / `candidateStageDocPolicy.ts` (when missing docs block a stage), (9) `document_policies` table (TENANT/CLIENT/VACANCY flags). Operator surface: **none** that edits the R5 merge. Settings still splits Documents / Ruleset / Transfer Policy / Hiring gates. Four-check: authority partial, surface no, E2E no, acceptance OPEN. |

**Why this is the first Product:** E8-eval proved evaluation on D4 against pack merge. It did **not** give an operator one overlay with reason. ADR-018 already named the Yurchuk failure mode (parallel blockers). Hiring cannot accept until that question has one answerer. Mapping can wait: its editors already run.

**False first-slice:** Documents Admin separate from Rules Admin; minting a Hub packages table; treating Overlay rewrite as RPM; CL8; reopening E8-eval / R5.

---

### 2. Mapping Authority

**v1 acceptance (Goal):** one operator-visible **model** from source answers to canonical entity fields. Not “build another mapping editor.”

| Axis | Result |
|------|--------|
| **Hard acceptance dependencies** | **None among the five.** Supporting: Acquisition path (sources exist) and Company setup. CL2 membership + CL6 `entity_profile_flight_map.v1` already execute map on D4. Convert mapping (`convert_mapping_v1`) already runs Sales Inquiry → ClientAccount. P9 / Meta / Forms field mapping already exist as intake adapters. |
| **Downstream unlocks** | **External Intake** directly (known edge). Does **not** unlock Hiring or min HR. Finite criterion line unlocked: “map source data into canonical entities” and, later, “external candidate in” once Intake is queued. |
| **Collapse** | **Medium — three models, different questions.** (1) Sales convert mapping, (2) CL6 Flight map (raw → Profile member `qualified_code`, snapshot on Binding), (3) intake / P9 `mapping_rules` / Meta field mapping / Forms field mapping. These are parallel **models**, not three contradictory answers to the same source→dest pair. Operator surface: **partial** (C-5 / intake editors). E2E: **partial** (CL6 executes; convert is backend). Authority: **no** single model. Acceptance OPEN. |

**Why it should not precede RPM:** it is startable, and the Goal correctly refuses RPM-before-Mapping as an execution edge. It still should not take Product Track first: collapse is of editor-models, not of a contradictory runtime question that blocks two other DAG nodes. One Active Product means Mapping-first delays RPM, Hiring, and HR together.

**False first-slice:** a fourth mapping editor; Zapier UX in Flight; Meta admin as mapping SoT; treating P9 write as the v1 model.

---

### 3. External Intake / Forms Publish

**v1 acceptance (Goal):** `publish → public form → submit → mapping → canonical entity → visible in workspace`. Forms P4 / P5 stay later.

| Axis | Result |
|------|--------|
| **Hard acceptance dependencies** | **Mapping Authority** (known edge). Forms Foundation C1–C6 already serve→execute. Supporting: Acquisition path into intake. **Not** RPM. **Not** Hiring. **Not** min HR. |
| **Downstream unlocks** | **None among the five.** Unlocks the finite-criterion line “acquire an external candidate” once mapping is the authority the publish path consumes. TenantLeadForm remains a bridge until then. |
| **Collapse** | **Medium — missing operator surface on existing runtime.** Parallel paths: Forms Foundation public runtime (no P3 Publish UI), `TenantLeadForm` bridge, SalesInquiry questionnaire glue. P3 is locked by honest deferral, not by missing Foundation. Four-check: authority partial, surface no (P3 locked), E2E partial, acceptance OPEN. |

**Why it cannot go first:** Intake acceptance names mapping as a step. Publishing without one mapping authority recreates the “another editor / another bridge” product the Goal forbids.

**False first-slice:** opening P4 Themes / P5 Analytics with P3; a second Forms submit engine; treating TenantLeadForm as the v1 publish SoT.

---

### 4. Hiring workflow E2E

**v1 acceptance (Goal):** one candidate walks `stage → requirements/docs → eligibility → transfer` over **existing** funnels, gates, policy authority, and transfer. Not a new Hiring Product.

| Axis | Result |
|------|--------|
| **Hard acceptance dependencies** | **Requirement Policy Management** (known edge). Supporting: Candidate workspace (D4 exists), Communications (Epic C constraints; C2.4 frozen), Permissions. Funnels, hiring pipeline gates, Transfer Policy, and CL7 `ready`/`not_ready` + `blockers[]` already exist as **pieces**. They are not the policy authority. |
| **Downstream unlocks** | **Min HR handoff** directly (known edge). Does not unlock Mapping or Intake. |
| **Collapse** | **High as a symptom, not as a first Product.** Live answerers to “may this candidate advance / transfer?”: funnels / stage codes, `hiring_pipeline_gates`, Transfer Policy (`ref_packs` + document_configs), frontend `candidateStageDocPolicy.ts`, CL7 blockers, Hub outstanding asks. Those answerers **should consume RPM**. Walking one candidate through them today would prove a workaround path, not policy authority. Four-check: authority partial, surface partial, E2E not proven vs policy, acceptance OPEN. |

**Why it cannot go first:** the Goal’s Hiring acceptance is against policy authority. E2E-before-RPM is the same class of error as treating queue-complete as product-complete.

**False first-slice:** a new Hiring Product; LI-2+ as a substitute; unfreezing C2.4 to make the walk look complete.

---

### 5. Minimal Recruitment → HR handoff

**v1 acceptance (Goal):** hire / transfer creates or links Employee; identity / profile kept; documents reused via Document Link; handoff status visible; no manual copy. Full HR operations later.

| Axis | Result |
|------|--------|
| **Hard acceptance dependencies** | **Hiring E2E** (known edge) — a completed hire/transfer of one person. **Not** Forms / External Intake (Goal: unproven). Supporting: E3/E4 Document Link already exists; `CandidateHandoff` T2 (`accept_handoff` → `handoff_from_candidate`) is the canonical internal path; T1 stage-driven workforce create is deprecated. |
| **Downstream unlocks** | **None among the five.** Closes the finite-criterion line “minimum employee state.” |
| **Collapse** | **Medium — leftover paths, primary contract exists.** T1 vs T2 vs T3 (client portal); snapshot still mentions `candidate_evidence` fulfillments; HR verification plan still reads `document_configs`. Operator surface: **partial**. E2E: **partial** (handoff APIs and UI exist; continuity of person + Document Link without re-key is not the named v1 acceptance). Acceptance OPEN. |

**Why it cannot go first:** there is no person to hand off until Hiring E2E has accepted one walk against policy. Building Employee-create ahead of that walk reopens full HR operations as a substitute v1.

**False first-slice:** Kadry / payroll / extended lifecycle; file-copy handoff; a new Document Link table; treating T3 client portal as the v1 min.

---

## Scoreboard (not a ladder)

| Capability | Startable among the five? | Hard preds (among five) | Downstream unlocks (among five) | Collapse | First Product? |
|------------|---------------------------|-------------------------|----------------------------------|----------|----------------|
| Requirement Policy Management | **Yes** | none | Hiring E2E → min HR | **High** (9 answers to one question) | **Recommended** |
| Mapping Authority | **Yes** | none | External Intake | **Medium** (3 models, different pairs) | Should not precede RPM |
| External Intake / Forms Publish | No | Mapping | none | Medium (P3 missing; bridges) | Cannot |
| Hiring workflow E2E | No | RPM | min HR | High *after* RPM exists | Cannot |
| Minimal HR handoff | No | Hiring E2E | none | Medium (T2 exists) | Cannot |

Known acceptance edges unchanged from the Goal. Still **not** proven as execution predecessors: RPM before Mapping; RPM before Intake; min HR blocked on Forms; any total order of the five.

---

## What this document does not do

- Does not schedule Requirement Policy Management or any other Product slice  
- Does not amend the [sequential queue](../tasks/sales-to-comms-sequential-queue.md) ladder (Active Product stays **none**)  
- Does not mint a new L2 acceptance edge **RPM → Mapping**. Mapping **should not precede** RPM; that is not a hard predecessor  
- Does not lock a total order of the five blockers  
- Does not open a Product brief, named gate, or feat  
- Does not reopen E8-eval, Overlay, CL7, DR1-runtime, E8-bind, or R5  
- Does not mark Documents Foundation ✅  
- Does not unfreeze C2.4, Forms P4/P5, OCR, packages, automation plane, extensions, or Billing  

---

## Next (consumed)

The docs-only queue amendment after this review named **Requirement Policy Management** as the first Product and cut [RPM-1 / RPM-2 / RPM-3](../tasks/requirement-policy-management.md). The RPM program close amendment then named **Mapping Authority MA-1** as Active Product (brief; feat locked). Mapping Authority Contract Gate then **PASS**; Active Product is [MA-2](../tasks/mapping-authority.md) (brief; feat locked). External Intake / Hiring E2E / min HR remain queued. This review is still not the schedule.

Until that first amendment merged, Product Track stayed **none**. After it, Active Product was RPM-1 (brief; feat locked). After RPM program close, Active Product was MA-1. After MA-1 Contract Gate PASS, Active Product is MA-2.

---

## Refs

- [HostFlow v1 Release Goal](hostflow-v1-release-goal.md) — v1 in-scope vs later; Release DAG; known acceptance edges  
- [Sequential queue](../tasks/sales-to-comms-sequential-queue.md) — slice schedule; Active Product = [MA-2](../tasks/mapping-authority.md) after Mapping Authority Contract Gate PASS  
- [Mapping Authority Contract](../architecture/mapping-authority-contract.md) — MA-1 SoT (`mapping_authority.v1`)  
- [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md) — one evaluator; Admin UI for policy was out of Slice 1  
- [ADR-007](../architecture/ADR-007-forms-platform-capability.md) — Forms Foundation ✅; P3 Publish UI locked  
- [Handoff contract](../architecture/handoff-contract.md) · [Documents E8-eval](../tasks/documents-platform-e8-eval.md) · [CL6 Flight map](../tasks/entity-field-composition-cl6-flight-map.md)
