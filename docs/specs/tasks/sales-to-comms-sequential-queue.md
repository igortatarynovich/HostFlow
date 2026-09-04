# Sales → Communication — sequential product queue (locked)

**Status:** **NORMATIVE QUEUE** (Product is either exactly one active **Product Track** slice **or DONE with no successor until amendment**; Engineering is either exactly one Active slice except the named `{R2, R3}` fan-out, **or DONE with no successor until amendment**; Engineering ≠ pytest background)  
**Date:** 2026-07-21 (rev. Product vs Engineering tracks)  
**Trusted base:** `integration/release-product-a-b` (fast-forward only)  
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) · [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Goal Completion Gate](../gates/goal-completion-gate.md) · [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) · [C0.0 Communication Canon](c0-0-communication-canon.md) · [Repository Operational Canon](../../governance/repository-operational-canon.md)

> **2026-08-31:** **Launch-ops opened** — Active Launch-ops = [OL-1](operate-and-launch.md) (docs). Two tracks now: Product **RPM-1** ∥ Launch-ops **OL-1**. Engineering stays **DONE**. Production target for v1: one dedicated host, one compose stack. RR3 / RR4 / RR7 owner: `igortatarynovich` (single-person ownership carried as a named residual to OL-7).
> **2026-08-23:** Execution canon sealed — see **§ Locked execution sequence**. Product = [CL0](entity-field-composition-cl0-contract-seal.md). Engineering = **Reference Program Exit Gate** after R5 Gate PASS [#297](https://github.com/igortatarynovich/HostFlow/pull/297). R1 [#292](https://github.com/igortatarynovich/HostFlow/pull/292), R2 [#294](https://github.com/igortatarynovich/HostFlow/pull/294), R3 [#295](https://github.com/igortatarynovich/HostFlow/pull/295), R4 [#296](https://github.com/igortatarynovich/HostFlow/pull/296) complete. After CL0: **CL1**. **E8-bind unlocked** (not auto-scheduled). E8-eval after R5 ∧ E8-bind. **ADR-037** docs sealed. C2.4 frozen (**Epic C residual R1**).  
> **2026-08-22:** Epic C + A2 **PASS_WITH_CONSTRAINTS**. Forms C1–C6 ✅ / Foundation ✅ ([#250](https://github.com/igortatarynovich/HostFlow/pull/250)). Entity Workspace D1–D9 brief-complete ([#268](https://github.com/igortatarynovich/HostFlow/pull/268)) and **goal-incomplete** vs original D ([audit](../gates/platform-scope-completeness-audit.md)). E1 ✅ ([#270](https://github.com/igortatarynovich/HostFlow/pull/270)). E2 ✅ ([#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276)). **Workspace Capability Platform Completion** [COMPLETE](../gates/workspace-capability-platform-complete.md) (**PASS**) on [#274](https://github.com/igortatarynovich/HostFlow/pull/274); G4 PASS (Recruitment Application) — **not** the Documents proof. Intermediate #273: [PASS_WITH_CONSTRAINTS](../gates/workspace-capability-platform-g1-g5-closeout.md). **Product Track:** [Entity Field Composition CL0](entity-field-composition-cl0-contract-seal.md) — brief; feat locked; Page Type + two builder modes + Profile as role manifest. E7 ✅ ([#287](https://github.com/igortatarynovich/HostFlow/pull/287); named Document Requests Gate). E6 ✅ ([#285](https://github.com/igortatarynovich/HostFlow/pull/285); named Document Expiry Gate). E5 ✅ ([#282](https://github.com/igortatarynovich/HostFlow/pull/282); named Candidate Storage Bridge Gate). E4 ✅. Catalog unlock ≠ mass bind. Not mass D3–D9 bind. Not D10. Not a Recruitment rail patch. Not ListWorkspace. Entity Workspace ≠ Application Workspace. Documents Foundation stays 🔄. **Engineering Track** = **Reference R1** (active). Legacy pytest / Catalog RFC / Kit chrome = background.  
> Communication **C2.4 frozen** (**Epic C residual R1** — **not** Reference R1).  
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
| **Product** | **[MA-3](mapping-authority.md)** after Mapping Resolution Gate **PASS**. Brief; feat locked this PR. Not Mapping feat. Not External Intake. Not Hiring E2E. Not OCR. Do not invent CL8. Do not mark Foundation ✅ | Almost all capacity |
| **Engineering** | **DONE** — Reference Program Exit Gate **PASS** [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c` — [brief](platform-reference-identity-sot.md). No named Engineering successor this amendment. Never collapse with **Epic C residual R1** (C2.4) or **Acquisition R6**. [#127](https://github.com/igortatarynovich/HostFlow/pull/127) / pytest = background — **not** Active Engineering |
| **Launch-ops** | **[Operate & Launch](operate-and-launch.md)** — v1 blocker 6 (brief this amendment; **not scheduled**, no Active Launch-ops slice yet). Write-set: `deploy/`, `docs/runbooks/`, infra defaults, tenant-lifecycle surfaces. Occupies the second-track slot left free by Engineering DONE. Not an SRE programme. Not Billing | Second track, small share of capacity |

---

## Locked execution sequence (normative)

This section is the **only** “what Product slice starts next” SoT. **v1 in-scope vs later** is the [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md). Horizon A–G stays in the [roadmap](../architecture/platform-completion-roadmap.md) and does **not** override the Release Goal. If another doc disagrees with **slice schedule**, **this ladder wins**. If it disagrees with **v1 scope**, the Release Goal wins.

Reaching the program horizon of this section is **not** a release. Release-ready is declared only by the [Release Readiness Gate](../gates/release-readiness-gate.md), proven by the [acceptance suite](../journeys/release-readiness-acceptance-suite.md).

### Current execution header

| Role | Value |
|------|--------|
| **Active Product** | **[MA-3](mapping-authority.md)** after Mapping Resolution Gate **PASS**. Brief; feat locked this PR. External Intake / Hiring / min HR remain queued. |
| **Queued Product successor** | **MA-4** Consumer cutover after Mapping Operator Gate PASS — [brief](mapping-authority.md). Do not start MA-3 feat in this PR. External Intake / Hiring E2E / min HR remain **queued**. Hiring is unlocked by RPM close, **not** scheduled. Not OCR / packages / automation plane / extensions / Billing product / AI. Do not invent CL8. Do not mark Foundation ✅. |
| **Active Engineering** | **DONE** — Reference Program Exit Gate **PASS** [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c` (`ref-id-exit`). No named successor. |
| **Queued Engineering after Exit** | none this amendment. Pytest / [#127](https://github.com/igortatarynovich/HostFlow/pull/127) stay background |
| **Active Launch-ops** | **[OL-1](operate-and-launch.md) DONE** — [Launch Ownership Gate](../gates/launch-ownership-gate.md) `PASS_WITH_CONSTRAINTS` 2026-08-31. Production target for v1: **one dedicated host, one compose stack**. RR3 / RR4 / RR7 owner: **igortatarynovich** for all three, recorded as a named residual (OL1-C1), not as a solved question |
| **Queued Launch-ops** | **OL-2** Deploy, migrate & rollback — named successor, **starts in its own PR** (invariant 6), then OL-3…OL-7 — [brief](operate-and-launch.md). The migration blocker is **withdrawn** — measured 2026-08-31, `alembic upgrade heads` applies to a fresh DB in one command ([§ Correction](operate-and-launch.md)). CI has been proving the same on every push (`backend-ci.yml` job `alembic`, green). OL-2 still owns what replaced it: the **written** deploy/migrate procedure RC condition 4 asks for, a fresh instance that starts with no admin user, and a rollback whose first release is a **baseline**, not a predecessor ([OL-2D](operate-launch-ol2d-predecessor.md)) |
| **Phase E** | **E7 = DONE**. **E8-bind = DONE** (Gate PASS [#321] / `8246421f`). **E8-eval = DONE** (Gate PASS [#324] / `19c95ef6`). **RPM program = DONE** (Authority / Operator / 3A / 3B / Consumer Cutover `918274d1` + program close). **MA-1 Contract Gate = PASS**. **Mapping Resolution Gate = PASS**. **Product = MA-3** (not a Phase E leftover) |
| **Frozen** | C2.4 Scheduling (**Epic C residual R1** — not Reference R1) |

Historical markers (A2 active, Meta Intake next, Phase E active = E7 feat) live only in §8 History. They are **not** current execution instructions.

### Invariants (mandatory)

1. **One Active Product slice**, **or Product DONE with no named successor until amendment**. This amendment names **MA-3** after Mapping Resolution Gate PASS. Unlock ≠ silent schedule of Intake / Hiring. Do not open MA-3 editor in this PR.  
2. **One Active Engineering slice**, except the named fan-out window `{Reference R2, Reference R3}` after Reference R1 Gate, **or Engineering DONE with no named successor**. After Exit PASS with no successor, Engineering is DONE — do not promote pytest / [#127](https://github.com/igortatarynovich/HostFlow/pull/127) to Active Engineering.  
3. **Two named tracks maximum.** A track exists only when this section names it with an owner and a write-set; unlocked work never creates a stream by itself. Engineering is **DONE with no successor**, so this amendment assigns the second slot to **Launch-ops** ([Operate & Launch](operate-and-launch.md), v1 blocker 6). Reviving Engineering would require closing or parking Launch-ops first — never three concurrent tracks.  
4. **Unlock ≠ schedule.** A satisfied unlock condition does **not** auto-start the slice. Only the owning track’s queue may activate it.  
5. **One work = one unlock condition.** Two independent unlocks ⇒ two named slices.  
6. **Do not skip a named gate.** Do not start the next slice in the same PR as its predecessor.  
7. **Park, don’t substitute.** If the next *scheduled* Product slice waits on an Engineering gate, Product waits. Do not jump to Billing / Forms P3 / OCR / CL8.  
8. **Write-set guard.** Product CL and Reference R may run in parallel **only while write sets do not overlap.**  
   - CL0 docs-only ∥ Reference R1 — allowed.  
   - CL1 observe ∥ Reference R3 — allowed (CL1 does not canonize).  
   - CL runtime country fields ∥ Reference R2 — forbidden.  
   - CL document identity ∥ Reference R3 — forbidden.  
   - CL required-doc policy ∥ Reference R5 — forbidden.  
   - Vacancy Overlay ∥ Reference R5 pack / `tenant_delta` merge — forbidden. Overlay is vacancy-specific delta over Profile / Screening Pack, not R5 policy merge.  
   - Product ∥ **Launch-ops** OL-1…OL-5 / OL-7 — allowed (docs, `deploy/`, infra config, runbooks; no product-module writes).  
   - Product ∥ **Launch-ops OL-6** (tenant lifecycle as product) — allowed **only** while the Active Product slice writes a different module; OL-6 touches tenant / superadmin / export surfaces.  
   - Any Launch-ops slice ∥ a Product slice editing the same file — forbidden, as for every other track.  
9. **Naming.** Prose: **Reference Rn**, **Epic C residual R1**, **Acquisition R6**. Machine ids: `ref-id-r1` … `ref-id-r5`. Never a bare `R1` in execution text.

### Engineering ladder

```text
Reference R1
  → { Reference R2 ∥ Reference R3 }
  → R3 → Reference R4
  → (R2 PASS ∧ R4 PASS) → Reference R5
  → Reference Program Exit Gate
```

Fan-out is **only** `{R2, R3}`. Reference R5 is **not** a third concurrent Engineering slice. Draft branches for R5 before the join are not Active Engineering.

| # | Slice | Machine id | Gate (PASS =) | Depends on | Unlocks |
|---|--------|------------|----------------|------------|---------|
| **ER1** | [Reference R1](platform-reference-identity-sot.md) Country Registry completeness | `ref-id-r1` | **Reference R1 Country Registry Gate** — ISO set in registry; facade `identity` / `classifications` / `labels`; `en`+`pl`+`ru`; `XK` ∉ canon; `OTHER` ∉ registry; no unique `dial_code`; checksum deterministic. Proof: country identity **definition** exists. **PASS** [#292](https://github.com/igortatarynovich/HostFlow/pull/292) `882f323c`. | REF-4 Phase 1 ✅. **Not** REF-4 Phase 2 | fan-out {R2, R3} |
| **ER2** | Reference R2 Country runtime cutover | `ref-id-r2` | **Reference R2 Country Runtime Cutover Gate** — `/catalogs/*` + frontend country/dial from registry only; Q1–Q2 | **Reference R1 Gate**. This slice **is** REF-4 Phase 2 country adoption | R5 join (with R4). **PASS** [#294](https://github.com/igortatarynovich/HostFlow/pull/294) `5034a4b6` |
| **ER3** | Reference R3 Document type identity | `ref-id-r3` | **Reference R3 Document Identity Gate** — existence = `document-type-registry-v1.json` only; Q3 | **Reference R1 Gate** (parallel with R2) | Reference R4. **PASS** [#295](https://github.com/igortatarynovich/HostFlow/pull/295) `72d24b70` |
| **ER4** | Reference R4 Alias consolidation | `ref-id-r4` | **Reference R4 Alias Consolidation Gate** — scanner/UI/legacy use alias registry only; Q4 | **Reference R3 Gate** | E8-bind unlock; R5 join (with R2). **PASS** [#296](https://github.com/igortatarynovich/HostFlow/pull/296) `69a4b992` |
| **ER5** | Reference R5 Policy merge | `ref-id-r5` | **Reference R5 Policy Merge Gate** — `merge(pack, tenant_delta)`; overlay ≠ fork; pack codes ⊆ registry; Q5 (required docs) | **Reference R2 Gate ∧ Reference R4 Gate** | E8-eval unlock; DR1-runtime unlock; Program Exit Gate |
| **ER-X** | **Reference Program Exit Gate** | `ref-id-exit` | Q1–Q5 answered by **one** chain: Country Registry → Document Type Registry + aliases → resolved policy → evaluator. **PASS** [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c` | **Reference R5 Gate** (implies R2+R3+R4) | Reference program DONE |

**Now:** Engineering **DONE** (ER-X PASS). **Stop:** C2.4, tenant-minted document types, XK-in-canon, promoting pytest to Active Engineering, third concurrent Engineering slice.

### Product ladder

```text
CL0 → CL1 → LI-1 → DR1-contract → CL2 → CL3 → CL4 → CL5 → CL6 → CL7 → Vacancy Overlay Contract → DR1-runtime → E8-bind → E8-eval → RPM-1 → RPM-2 → RPM-3A → RPM-3B → Consumer Cutover Gate → RPM program close
DR1-runtime  also required  DR1-contract ∧ Reference R5   (PASS [#313](https://github.com/igortatarynovich/HostFlow/pull/313); E8-bind PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f`)
```

| # | Slice | Gate (PASS =) | Depends on | Unlocks |
|---|--------|----------------|------------|---------|
| **P0** | [CL0](entity-field-composition-cl0-contract-seal.md) contract seal | **CL0 Gate** — brief merged; queue/roadmap/AGENTS point here; no runtime | E7 ✅ | CL1 |
| **P1** | [CL1](entity-field-composition-cl1-candidate-inventory.md) Candidate inventory | **CL1 Gate** ✅ [#299](https://github.com/igortatarynovich/HostFlow/pull/299) / `b33ac205` — live Candidate fields / `document_configs` / screening-as-required **observed** (code, source, tenant/module, enabled, required-as-found, fields, consumers, legacy usage). Does **not** emit canonical / alias / invalid / migration-required — that is R3/R4 | **CL0 Gate** | LI-1 |
| **P2** | [LI-1](lifecycle-identity-l0-contract-seal.md) existence guard | **LI-1 Existence Guard Gate** ✅ [#300](https://github.com/igortatarynovich/HostFlow/pull/300) / `c9ca41cc` — one producer for “is stage X registered?”; no Funnel/UI cutover | **CL1 Gate** | DR1-contract. LI-2+ stay in the Lifecycle queue and do **not** block CL2+ |
| **P3** | [DR1-contract](engine-document-request-dr1-contract.md) Engine → Document Request contract | **DR1 Contract Gate** ✅ [#302](https://github.com/igortatarynovich/HostFlow/pull/302) — Engine→Hub outstanding-ask contract sealed; no mass generation | **CL1 Gate ∧ LI-1 Gate**. If the contract already names canonical type ids: also **Reference R3 Gate ∧ Reference R4 Gate** | CL2; DR1-runtime (join R5) |
| **P4** | [CL2](entity-field-composition-cl2-membership.md) Membership runtime | **CL2 Gate** ✅ [#303](https://github.com/igortatarynovich/HostFlow/pull/303) / `09dfea47` — `entity_profile_membership.v1`; driver_ce members + intake/card_save; screening pack as ref; no layout | **DR1-contract Gate** | CL3 |
| **P5** | [CL3](entity-field-composition-cl3-layout.md) Layout runtime | **CL3 Gate** — D4 Information zone places `entity_profile_layout.v1` / `candidate.card`; membership-filtered; no builder | **CL2 Gate** | CL4 |
| **P6** | [CL4](entity-field-composition-cl4-builder.md) Builder (two modes) | **CL4 Gate** ✅ [#305](https://github.com/igortatarynovich/HostFlow/pull/305) / `c49716e3` — card vs form compile over closed page types; D4 places card, not form | **CL3 Gate** | CL5 |
| **P7** | [CL5](entity-field-composition-cl5-qa.md) Q&A | **CL5 Gate** ✅ [#306](https://github.com/igortatarynovich/HostFlow/pull/306) / `5d8e1ae3` — qa_only from Lead/Application; map recognized not executed; D4 places Q&A zone | **CL4 Gate** | CL6 |
| **P8** | [CL6](entity-field-composition-cl6-flight-map.md) Flight mapping | **CL6 Gate** ✅ [#307](https://github.com/igortatarynovich/HostFlow/pull/307) / `8e2372db` — Map executes raw → member `qualified_code`; snapshot on Binding; dest = Profile, not Flight entity | **CL5 Gate** | CL7 |
| **P9** | [CL7](entity-field-composition-cl7-engine-eval.md) Requirement Engine evaluation | **CL7 Gate** ✅ [#309](https://github.com/igortatarynovich/HostFlow/pull/309) / `6f2289f1` — structured `ready`/`not_ready` + `blockers[]`; not boolean; not Hub ask generation | **CL6 Gate** | Vacancy Overlay Contract |
| **P10** | [Vacancy Overlay Contract](entity-profile-vacancy-overlay-contract.md) | **Vacancy Overlay Gate** ✅ [#311](https://github.com/igortatarynovich/HostFlow/pull/311) / `7649544d` — SoT + merge semantics for vacancy-specific requirement delta over Profile / Screening Pack; not CL8; not R5 pack merge | **CL7 Gate** | DR1-runtime |
| **P-DR** | [DR1-runtime](engine-document-request-dr1-runtime.md) Engine generation | **DR1 Runtime Gate** ✅ [#313](https://github.com/igortatarynovich/HostFlow/pull/313) / `e6978fe2` — Engine may create Hub outstanding asks; evaluation consumers may run; not mass generation; not E8 | **DR1-contract Gate ∧ Reference R5 Gate ∧ Vacancy Overlay Gate** | E8-bind ✅ [#321](https://github.com/igortatarynovich/HostFlow/pull/321) |
| **P-E8b** | [E8-bind](documents-platform-e8-bind.md) Canonical type bind | **Documents Platform E8 Canonical Type Bind Gate** ✅ [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` — remaining consumers bind to canonical document types; display/select canonical types; identity migration; not E8-eval; not mass D3–D9 bind | **Reference R3 Gate ∧ Reference R4 Gate ∧ DR1 Runtime Gate**. Scheduled after DR1 Runtime Gate PASS [#313](https://github.com/igortatarynovich/HostFlow/pull/313) (unlock ≠ silent schedule) | E8-eval ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) |
| **P-E8e** | [E8-eval](documents-platform-e8-eval.md) Required-doc evaluation | **Documents Platform E8 Required-Doc Evaluation Gate** ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6` — required / optional / applicability from R5 merge; canonical types only; not OCR product; not mass D3–D9 bind | **Reference R5 Gate ∧ E8-bind Gate**. Scheduled after E8-bind Gate PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` and queue amendment [#323](https://github.com/igortatarynovich/HostFlow/pull/323) (unlock ≠ silent schedule) | RPM-1 ✅ scheduled this amendment |
| **P-RPM1** | [RPM-1](requirement-policy-management.md) Authority contract | **Requirement Policy Authority Gate** ✅ — one operator question; one write authority; nine answerers classified. SoT: [requirement-policy-authority.md](../architecture/requirement-policy-authority.md). Feat locked. Not Mapping. Not Hiring E2E. Not CL8 | **E8-eval Gate** ∧ DAG review [#328](https://github.com/igortatarynovich/HostFlow/pull/328) | RPM-2 |
| **P-RPM2** | [RPM-2](requirement-policy-management.md) Operator overlay | **Requirement Policy Operator Gate** ✅ [#342](https://github.com/igortatarynovich/HostFlow/pull/342) / `5196ee64` — one job UI: base, override, reason, `resolved_policy`; writes RPM-1 authority; Documents domain first | **Requirement Policy Authority Gate** | RPM-3A |
| **P-RPM3A** | [RPM-3A](requirement-policy-management.md) Parallel authority retirement | **Requirement Policy Parallel Authority Retirement Gate** ✅ — A `document_policies`, C leftover ruleset writes, J P3B `document_required` only | **Requirement Policy Operator Gate** | RPM-3B |
| **P-RPM3B** | [RPM-3B](requirement-policy-management.md) Consumer parity | **Requirement Policy Consumer Parity Gate** ✅ — remaining consumers’ policy answer matches R5 required-set (base / require X / remove X) | **Requirement Policy Parallel Authority Retirement Gate** | Consumer Cutover Gate |
| **P-RPM3** | [RPM-3](requirement-policy-management.md) Consumer cutover close | **Requirement Policy Consumer Cutover Gate** ✅ `918274d1` — 3A ∧ 3B PASS; classified consumers read the same merge or are retired; D4 matches operator write | RPM-3A Gate ∧ RPM-3B Gate | RPM program close ✅ |
| **P-RPM-X** | [RPM](requirement-policy-management.md) program close | **RPM program DONE** — outcome + release delta; four-checks PASS (Documents domain) | Consumer Cutover Gate | MA-1 (this amendment). Hiring E2E unlocked, **not** scheduled |
| **P-MA1** | [MA-1](mapping-authority.md) Authority contract | **Mapping Authority Contract Gate** ✅ — one operator question; one write; twelve answerers classified; contract shape SoT; no fourth store. SoT: [mapping-authority-contract.md](../architecture/mapping-authority-contract.md). Feat locked. Not Mapping feat. Not Hiring E2E. Not CL8 | RPM program DONE | MA-2 |
| **P-MA2** | [MA-2](mapping-authority.md) Resolution runtime | **Mapping Resolution Gate** ✅ — exactly one store answers “which rule applies?”; leftover stores read-through or migrated; precedence chain removed. SoT: [mapping-authority-resolution.md](../architecture/mapping-authority-resolution.md) | Mapping Authority Contract Gate | MA-3 |

**Now:** Product **MA-3** (UX contract sealed; feat open this PR; Operator Gate not PASS) after Mapping Resolution Gate **PASS**. SoT: [mapping-authority-operator.md](../architecture/mapping-authority-operator.md). **v1 scope:** [Release Goal](../gates/hostflow-v1-release-goal.md). **Not** Mapping Operator Gate PASS. **Not** External Intake. **Not** Hiring E2E. **Not** OCR. Do not invent CL8. Do not mark Foundation ✅.

LI-1 is the **only** Lifecycle slice between CL1 and CL2. LI-2…LI-4 stay in [the Lifecycle brief](lifecycle-identity-l0-contract-seal.md) and do not stall Field Composition.

### Documents / E8 (two slices)

| Slice | Unlock (may start) | Schedule | Gate |
|-------|--------------------|----------|------|
| **E8-bind** | **Reference R3 Gate ∧ Reference R4 Gate ∧ DR1 Runtime Gate** | Product Track; **DONE** — Gate PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` after DR1 Runtime Gate PASS [#313](https://github.com/igortatarynovich/HostFlow/pull/313) | remaining consumers bind to **canonical** document types; display/select canonical types; identity migration. **Not** required/optional, applicability, candidate evaluation, packages, OCR↔requirement matching |
| **E8-eval** | **Reference R5 Gate ∧ E8-bind Gate** | Product Track; **DONE** — Gate PASS [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6` after E8-bind Gate PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` and queue amendment [#323](https://github.com/igortatarynovich/HostFlow/pull/323). Unlock was not auto-start | required/optional; applicability; candidate requirement evaluation from R5 merge. Consume existing packs as policy input. **Not** OCR product; **not** a packages Hub table |

E8-eval brief + feat **closed**. RPM program **DONE**. Mapping Resolution Gate **PASS**. Unlock does not schedule OCR / CL8 / Foundation. MA-3 editor stays locked this amendment.

### Join graph (checkable)

```text
Engineering:
  ref-id-r1 → { ref-id-r2 ∥ ref-id-r3 } → ref-id-r4
            → (r2 ∧ r4) → ref-id-r5 → ref-id-exit

Product:
  CL0 → CL1 → LI-1 → DR1-contract → CL2 → CL3 → CL4 → CL5 → CL6 → CL7 → Vacancy Overlay Contract → DR1-runtime → E8-bind → E8-eval → RPM-1 → RPM-2 → RPM-3A → RPM-3B → rpm-cutover → RPM program close → MA-1 → MA-2 → MA-3
  DR1-runtime also: DR1-contract ∧ ref-id-r5 (PASS [#313](https://github.com/igortatarynovich/HostFlow/pull/313))

Documents:
  r3 ∧ r4 ∧ DR1-runtime → E8-bind   PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f`
  r5 ∧ E8-bind → E8-eval   PASS [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6`
  E8-eval ∧ DAG review [#328] → RPM-1 → … → RPM program close → MA-1 → MA-2 → MA-3   (this amendment)
```

Program horizon of this amendment: **MA-4** (Mapping Authority program close). RPM program is **DONE**. Hiring E2E is unlocked, **not** scheduled. External Intake stays behind Mapping. Do not invent CL8. Do not auto-start OCR. Do not mark Foundation ✅.

### v1 blocker programs beyond this horizon (briefed, not scheduled)

Mapping Authority is **no longer in this table** — MA-3 is Active Product (brief; feat locked). A brief is **not** a schedule for the rows below: they exist so the release distance is countable. Activation still requires a queue amendment, one Active Product slice at a time.

| Program | Brief | Internal slices | Estimate | Startable after |
|---------|-------|-----------------|----------|-----------------|
| External Intake / Forms Publish | [external-intake-forms-publish.md](external-intake-forms-publish.md) | FP-1…FP-5 | 5–7 slices | Mapping program close (FP-5); earlier FP slices need a queue amendment |
| Hiring workflow E2E | [hiring-workflow-e2e.md](hiring-workflow-e2e.md) | HE-1…HE-4 | 4–6 slices | RPM program close ✅ (policy authority edge) — **unlocked, not scheduled** |
| Minimal Recruitment → HR handoff | [recruitment-hr-minimal-handoff.md](recruitment-hr-minimal-handoff.md) | HH-1…HH-4 | 4–6 slices | Hiring E2E program close |
| **Operate & Launch** (blocker 6, **Launch-ops track**) | [operate-and-launch.md](operate-and-launch.md) | OL-1…OL-7 | 10–14 slices | amendment naming OL-1 + RR3 / RR4 / RR7 owners |

Blocker 6 runs on the **second track**, so its slices do not extend the Product critical path — but they do extend the release distance, because the Release Candidate cannot exist without OL-2 (deploy + clean migrations) and the gate cannot pass without OL-5, OL-6 and OL-7.

**Estimate unit:** 1 slice = one docs PR + one feat PR on the trusted base, single concern. Slices are not calendar days.

### Release horizon roll-up (the queue’s number, consumed by the gate)

This is the **only** place where remaining release distance is totalled. The [Release Readiness Gate](../gates/release-readiness-gate.md) § Derived RC date consumes these numbers and never invents its own.

| Path | Programs | Slices |
|------|----------|--------|
| **Product critical path** | Mapping 4–6 · Forms Publish 5–7 · Hiring E2E 4–6 · min HR handoff 4–6 | **17–25** |
| **Launch-ops** | Operate & Launch OL-1…OL-7 | **10–14** |
| **Gate prerequisites** | ownership cards MOC-1…MOC-3 — **DONE** 2026-08-28 ([coverage record](../gates/module-ownership-coverage.md) §4) · [QB-1](stabilize-integration-pytest-baseline.md) — measured, routed and **reproducible** 2026-08-29; CI reproduction remains · [TI-1…TI-5](tenant-isolation-enforcement.md) tenant isolation enforcement (was U-6) — **TI-1…TI-4 DONE** 2026-08-29/30; TI-5 is the whole remainder and carries the role switch, whose precondition moved once the superadmin platform surface was measured | **6–9** |
| **Serialized-equivalent total** | both tracks share one delivery capacity today | **33–48** |

The Product path is a sum, not a max: the one-Active-Product invariant serialises it regardless of the DAG. Launch-ops is a second **track**, not second capacity — until a separate person or team owns it, its slices consume the same throughput, so the honest total is the sum.

**Measured velocity (for calibration, not a promise):** the 2026-08-14…2026-08-27 window recorded ≈29 Product slice gates in 14 days (~2/day), plus the Reference program in parallel. Those slices were predominantly contract and docs work with thin runtime. The remaining work is mostly runtime, infrastructure and executed procedures, so applying that rate unchanged would be dishonest.

| Scenario | Rate | Slice work | **RC can be tagged** | **Gate decision** |
|----------|------|-----------|----------------------|-------------------|
| S1 — recent pace holds | 2.0 slices/day | 17–24 days | 2026-09-21 … 2026-09-28 | 2026-10-05 … 2026-10-19 |
| S2 — runtime-heavy discount | 1.0 slices/day | 33–48 days | 2026-10-07 … 2026-10-22 | 2026-10-21 … 2026-11-12 |
| S3 — infrastructure reality | 0.5 slices/day | 66–96 days | 2026-11-09 … 2026-12-09 | 2026-11-23 … 2026-12-30 |

Computed from 2026-09-04 over **33–48** serialized-equivalent slices, adding a 7-day acceptance-suite execution window and a 7–14-day defect-fix window after RC. **S2 is the planning scenario**: S1 assumes contract-slice velocity survives contact with deploy pipelines, backups and publish runtime, which the [Operate & Launch](operate-and-launch.md) starting-point inventory contradicts.

**What can move these dates.** § D4 of the [unowned work register](../gates/v1-unowned-work-register.md) is empty, so nothing blocks gate entry today, but a new U-row may be opened at any time and would; RC condition 4 is half-satisfied rather than blocked — the fresh-database migration failure was measured false on 2026-08-31 and CI already proves the migration half on every push ([§ Correction](operate-and-launch.md)), so what OL-2 still owes is the documented procedure and a first-admin path; and the acceptance windows assume a non-developer operator is available, which is a staffing input, not an engineering one. A date quoted without this section behind it is not a release date.

**Mapping Resolution Gate PASS 2026-09-04.** Mapping remaining path is MA-3…MA-4. Serialized-equivalent stays **33–48** (no RC recut this amendment). Active Product → **MA-3** (brief; feat locked).

**MA-1 Contract Gate PASS 2026-09-04.** Mapping remaining path is MA-2…MA-4. Serialized-equivalent stays **33–48** (no RC recut this amendment). Active Product → **MA-2** (brief; feat locked).

**Moved −3–5 slices on 2026-09-04 after RPM program close.** RPM 3–5 remaining slices leave the Product critical path. Mapping 4–6 remains. Serialized-equivalent **33–48**. RC band 2026-10-07 … 2026-10-22 under S2. Active Product → **MA-1** (brief; feat locked).

**Moved +1 slice on 2026-08-30, again after delivery.** TI-4 closed the 102-table gap, which removes a slice; TI's estimate then rose from 7–10 to 9–12, which adds two. The cause is worth stating plainly, because it is the second consecutive revision driven by measurement rather than by scope: the coverage guard recognised tenant scope by the literal column name `tenant_id`, and three tables scoped through `agency_tenant_id` / `client_tenant_id` were therefore never measured — two of them with row-level security switched off entirely. Closing them was cheap; what is not cheap is the consumer the same investigation named, the superadmin `/api/v1/platform` surface, which reads and writes every tenant on an unbound session and must get a named elevated connection before the application role can be switched at all.

**Moved +1 slice on 2026-08-29, after delivery.** TI-1…TI-3 landed and QB-1 became reproducible — four slices of the prerequisite line — but connecting the restricted role for the first time measured what closing the gap actually costs, and TI's estimate rose from 5–8 to 7–10: 102 tables, 10 application paths that write with no tenant bound, 108 tests that write for a tenant other than the one they bind, and one security-canon decision about how identity lookup works once `users` carries a policy. The net is one slice, and it is the right direction of error: the previous number was measured from the schema, this one from the running system.

**Prior revisions:** 36–53 slices → RC 2026-10-05 … 2026-10-22 under S2 (2026-08-30); 35–52 → RC 2026-10-03 … 2026-10-20 (2026-08-29); 34–51 → RC 2026-10-01 … 2026-10-18 (2026-08-28); before that 30–44 → RC 2026-09-27 … 2026-10-11. Every increase through 2026-08-30 was the gate-prerequisite line; the 2026-09-04 drop is RPM leaving the remaining Product path.

### Naming (mandatory)

| Token | Machine id | Meaning |
|-------|------------|---------|
| **Reference R1…R5** | `ref-id-r1`…`ref-id-r5` | Platform Reference Identity SoT |
| **Reference Program Exit Gate** | `ref-id-exit` | Five-questions integration proof |
| **Epic C residual R1** | — | C2.4 Scheduling freeze |
| **Acquisition R6** | — | Acquisition table-cutover (out of this slice) |
| **E8-bind / E8-eval** | — | two Documents slices; never one E8 with two unlocks |
| **DR1-contract / DR1-runtime** | — | two Document Request slices |
| **RPM-1 / RPM-2 / RPM-3A / RPM-3B / RPM-3** | `rpm-authority` / `rpm-operator` / `rpm-cutover-writers` / `rpm-cutover-consumers` / `rpm-cutover` | Requirement Policy Management internal slices; not Mapping; not Hiring E2E |
| **MA-1…MA-4** | `map-authority` / `map-resolve` / `map-operator` / `map-cutover` | [Mapping Authority](mapping-authority.md) internal slices; not a fourth mapping editor |
| **FP-1…FP-5** | `fp-contract` / `fp-publish` / `fp-serve` / `fp-operator` / `fp-accept` | [External Intake / Forms Publish](external-intake-forms-publish.md) internal slices = Forms **P3**; never P4 Themes / P5 Analytics |
| **HE-1…HE-4** | `he-contract` / `he-stages` / `he-eligibility` / `he-accept` | [Hiring workflow E2E](hiring-workflow-e2e.md) internal slices; acceptance over existing machinery, not a Hiring Product |
| **HH-1…HH-4** | `hh-contract` / `hh-status` / `hh-reuse` / `hh-accept` | [Minimal Recruitment → HR handoff](recruitment-hr-minimal-handoff.md) internal slices; not full HR operations |
| **OL-1…OL-7** | `ol-contract` / `ol-deploy` / `ol-runtime` / `ol-signal` / `ol-recovery` / `ol-tenant` / `ol-support` | [Operate & Launch](operate-and-launch.md) internal slices on the **Launch-ops** track; not an SRE programme; never counted as Active Product |
| **TI-1…TI-4** | `ti-contract` / `ti-guard` / `ti-role` / `ti-coverage` | [Tenant isolation enforcement](tenant-isolation-enforcement.md); gate prerequisite for RR5, not a capability blocker; not RBAC, not the superadmin model |

### Exit test (this docs amendment)

A reader who has only this section can answer every item **yes**:

1. Exactly one **Active Product** slice, **or Product DONE with no named successor until amendment** (now: MA-3; brief; feat locked this PR).  
2. Exactly one **Active Engineering** slice, **or** the named fan-out `{Reference R2, Reference R3}` after Reference R1 Gate, **or Engineering DONE with no named successor** — never a third concurrent Engineering slice. Pytest is not Active Engineering.  
3. Every queued slice has a named predecessor.  
4. Every slice has an owner track. Unlocked work is not a third track.  
5. **One work = one unlock condition.** Independent unlocks ⇒ split into named slices.  
6. **Unlock ≠ schedule.** Satisfying an unlock does not auto-activate the slice.  
7. An integration gate (Reference Program Exit; E8-eval; DR1-runtime) depends on every domain it checks.  
8. No runtime consumer starts before the authoritative definition exists.  
9. Tenant cannot mint identity where a registry is existence SoT.  
10. Historical status lines do not contradict the **Current execution header**.  
11. The graph from **now** to program close is finite.

---

**Open product GAPs:**

- **Acquisition Stage 3E / Activity Timeline** ← **DONE** (#130–#133) — [timeline](acquisition-stage-3e-activity-timeline.md); deferred gaps — [deferred](acquisition-stage-3e-deferred.md)  
- **Acquisition Stage 4 / Flight Runtime** ← **Runtime DONE** (#136 / #148–#151) — [stage-4](acquisition-stage-4-flight-runtime.md)  
- **Acquisition UI Cutover** ← **PASS** — [cutover](acquisition-ui-cutover.md) · [C-7](acquisition-ui-cutover-c7-searches-decommission.md) (C-1…C-7 closed 2026-07-27; Stage 5 PR-2 may resume)
- **FlightAdBinding Ad-ID bind UI** ← **DONE** (#187) — Campaign Detail Ad→Flight panel  
- **Source Diagnostics** ← **PR1–PR9 ✅** (#196–#212) — [brief](acquisition-source-diagnostics.md); Wave-1 notifications closed (SPA-only)  
- **Acquisition Stage 5 / Optimization** ← PR-1 DONE · **PR-2 DONE** (#203) — [stage-5](acquisition-stage-5-optimization.md)  
- **Acquisition Stage 6 Analytics** ← **DONE** (PR-1…PR-6b) — [brief](acquisition-stage-6-analytics.md) · [ownership](../../modules/acquisition/outcome-commercial-value-ownership.md)  
- C2.3 Campaign Orchestrator ← **DONE** (landed on tip; #121–#126 superseded; **#219**)  
- C2.4 Scheduling ← **frozen** (**Epic C residual R1**; do not start; **not** Reference R1)  
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
- **Documents Platform E4 — Candidate Document Link** ← ✅ [#279](https://github.com/igortatarynovich/HostFlow/pull/279)/[#280](https://github.com/igortatarynovich/HostFlow/pull/280) — [brief](documents-platform-e4-candidate-document-link.md); D4 consume path = Document Link; named Candidate Document Link Gate  
- **Documents Platform E5 — Candidate Storage Bridge Retirement** ← ✅ [#281](https://github.com/igortatarynovich/HostFlow/pull/281)/[#282](https://github.com/igortatarynovich/HostFlow/pull/282) — [brief](documents-platform-e5-candidate-storage-bridge.md); drop `candidate_id`; named Candidate Storage Bridge Gate  
- **Documents Platform E6 — Document Expiry / Validity** ← ✅ [#284](https://github.com/igortatarynovich/HostFlow/pull/284)/[#285](https://github.com/igortatarynovich/HostFlow/pull/285) — [brief](documents-platform-e6-document-expiry.md); Hub validity SoT; named Document Expiry Gate  
- **Documents Platform E7 — Document Requests** ← ✅ [#286](https://github.com/igortatarynovich/HostFlow/pull/286)/[#287](https://github.com/igortatarynovich/HostFlow/pull/287) — [brief](documents-platform-e7-document-requests.md); Hub outstanding-ask SoT; named Document Requests Gate  
- **Entity Field Composition CL0 — Contract Seal** ← **PASS** (brief; treated PASS via #289) — [brief](entity-field-composition-cl0-contract-seal.md); Page Type + two builder modes; Profile = role manifest; four requirement kinds; Engine not boolean; `transition`/`handoff` off Profile field  
- **Reference R1–R5** ← **DONE** — Exit Gate **PASS** [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c` — [brief](platform-reference-identity-sot.md). No named Engineering successor this amendment. E8-bind unlock after R3∧R4 (PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321)). E8-eval after R5 ∧ E8-bind (PASS [#324](https://github.com/igortatarynovich/HostFlow/pull/324))
- **CL4** Entity Field Composition builder (two modes) ← **PASS** [#305](https://github.com/igortatarynovich/HostFlow/pull/305) / `c49716e3` — [brief](entity-field-composition-cl4-builder.md)
- **CL5** Recruiter Q&A ← **PASS** [#306](https://github.com/igortatarynovich/HostFlow/pull/306) / `5d8e1ae3` — [brief](entity-field-composition-cl5-qa.md)
- **CL6** Flight mapping ← **PASS** [#307](https://github.com/igortatarynovich/HostFlow/pull/307) / `8e2372db` — [brief](entity-field-composition-cl6-flight-map.md); `entity_profile_flight_map.v1`; Map executes onto Binding; dest = Profile members
- **CL7** Requirement Engine evaluation ← **PASS** [#309](https://github.com/igortatarynovich/HostFlow/pull/309) / `6f2289f1` — [brief](entity-field-composition-cl7-engine-eval.md); structured `ready`/`not_ready` + blockers; not boolean; not Hub ask generation
- **Vacancy Overlay Contract** ← **PASS** [#311](https://github.com/igortatarynovich/HostFlow/pull/311) / `7649544d` — [brief](entity-profile-vacancy-overlay-contract.md); SoT + merge semantics for vacancy-specific requirement delta over Profile / Screening Pack. Not CL8. Not Engine v2. Not Hub asks. Product ladder = **CL0 → CL1 → LI-1 → DR1-contract → CL2 → CL3 → CL4 → CL5 → CL6 → CL7 → Vacancy Overlay Contract → DR1-runtime → E8-bind…**
- **DR1-runtime** ← **PASS** [#313](https://github.com/igortatarynovich/HostFlow/pull/313) / `e6978fe2` — [brief](engine-document-request-dr1-runtime.md); Engine may create Hub outstanding asks. Not CL8. Not E8. Not mass generation.
- **Documents E8-bind** ← **PASS** [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` — [brief](documents-platform-e8-bind.md); remaining consumers bind to canonical document types. Not E8-eval. Not CL8. Not mass D3–D9 bind.
- **Lifecycle Identity** ← docs sealed; **LI-1 feat after CL1** (existence/identity guard only) — [brief](lifecycle-identity-l0-contract-seal.md) · [ADR-037](../architecture/ADR-037-lifecycle-identity-canon.md); LI-2+ do **not** block CL2+; Funnel ≠ existence SoT
- **DR1-contract** ← **PASS** [#302](https://github.com/igortatarynovich/HostFlow/pull/302) — [brief](engine-document-request-dr1-contract.md). **DR1-runtime** ← **PASS** [#313](https://github.com/igortatarynovich/HostFlow/pull/313)
- **Documents E8-eval** ← **PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6` — [brief](documents-platform-e8-eval.md); required / optional / applicability from R5 merge. Not OCR. Not CL8. Not mass D3–D9 bind. Successor = RPM program **DONE**.
- **Requirement Policy Management** ← **DONE** — RPM-1…3B PASS · Consumer Cutover Gate **PASS** `918274d1` · program close this amendment — [brief](requirement-policy-management.md). Hiring E2E unlocked, **not** scheduled. Not CL8.
- **Mapping Authority** ← **Active = MA-3** (brief; feat locked this PR) — [brief](mapping-authority.md). Mapping Resolution Gate **PASS**. MA-1 Contract Gate **PASS**. MA-3 editor not opened. External Intake / Hiring / min HR remain queued.
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
| **32** | **Documents Platform E4** Candidate Document Link | `docs/…` ✅ [#279](https://github.com/igortatarynovich/HostFlow/pull/279) · `feat/…` ✅ [#280](https://github.com/igortatarynovich/HostFlow/pull/280) | ✅ named Candidate Document Link Gate · merge `0af74913` |
| **33** | **Documents Platform E5** Candidate storage-bridge retirement | `docs/…` ✅ [#281](https://github.com/igortatarynovich/HostFlow/pull/281) · `feat/…` ✅ [#282](https://github.com/igortatarynovich/HostFlow/pull/282) | ✅ named Candidate Storage Bridge Gate · merge `702b922c` |
| **34** | **Documents Platform E6** Document expiry / validity | `docs/…` ✅ [#284](https://github.com/igortatarynovich/HostFlow/pull/284) · `feat/…` ✅ [#285](https://github.com/igortatarynovich/HostFlow/pull/285) | ✅ named Document Expiry Gate · merge `79e638c3` |
| **35** | **Documents Platform E7** Document requests | `docs/…` ✅ [#286](https://github.com/igortatarynovich/HostFlow/pull/286) · `feat/…` ✅ [#287](https://github.com/igortatarynovich/HostFlow/pull/287) | ✅ named Document Requests Gate · merge `ceafbd48` |
| **36** | **Entity Field Composition CL0** Contract seal | `docs/…` | **PASS** (brief; treated PASS via #289) — Page Type + two builder modes; Profile = role manifest |
| **37** | **Reference R1** Country registry | `feat/platform-reference-r1-country-registry` | ✅ [#292](https://github.com/igortatarynovich/HostFlow/pull/292) `882f323c` |
| **38** | **Reference R2** Country runtime cutover | `feat/platform-reference-r2-country-runtime-cutover` | ✅ [#294](https://github.com/igortatarynovich/HostFlow/pull/294) `5034a4b6` |
| **39** | **Reference R3** Document type identity | `feat/platform-reference-r3-document-identity` | ✅ [#295](https://github.com/igortatarynovich/HostFlow/pull/295) `72d24b70` |
| **40** | **Reference R4** Alias consolidation | `feat/platform-reference-r4-alias-consolidation` | ✅ [#296](https://github.com/igortatarynovich/HostFlow/pull/296) `69a4b992` |
| **41** | **Reference R5** Policy merge | `feat/platform-reference-r5-policy-merge` | ✅ [#297](https://github.com/igortatarynovich/HostFlow/pull/297) `6ce7d350` |
| **41b** | **Reference Program Exit Gate** | `feat/platform-reference-program-exit` | ✅ [#298](https://github.com/igortatarynovich/HostFlow/pull/298) `ff0b914c` — Q1–Q5 one chain; program DONE |
| **42** | **CL1** Field composition inventory | ✅ [#299](https://github.com/igortatarynovich/HostFlow/pull/299) `b33ac205` | after **CL0 Gate**; observed codes; did not canonize identity |
| **42b** | **LI-1** Existence guard (ADR-037) | ✅ [#300](https://github.com/igortatarynovich/HostFlow/pull/300) `c9ca41cc` — [brief](lifecycle-identity-li1-existence-guard.md) | after **CL1 Gate**; one existence producer; LI-2+ stay in [the Lifecycle brief](lifecycle-identity-l0-contract-seal.md) |
| **42c** | **CL2** Membership runtime | ✅ [#303](https://github.com/igortatarynovich/HostFlow/pull/303) `09dfea47` | after **DR1-contract Gate**; `entity_profile_membership.v1`; no layout |
| **43** | **DR1-contract** Engine → Document Request contract | ✅ [#302](https://github.com/igortatarynovich/HostFlow/pull/302) | after CL1 ∧ LI-1; also R3∧R4 if the contract already names canonical type ids |
| **43b** | **CL3** Layout runtime | ✅ [#304](https://github.com/igortatarynovich/HostFlow/pull/304) `8c04d696` | after **CL2 Gate**; D4 Information zone |
| **43c** | **CL4** Builder (two modes) | ✅ [#305](https://github.com/igortatarynovich/HostFlow/pull/305) `c49716e3` | after **CL3 Gate**; card vs form; closed page types; not Q&A |
| **43d** | **CL5** Recruiter Q&A | ✅ [#306](https://github.com/igortatarynovich/HostFlow/pull/306) `5d8e1ae3` | after **CL4 Gate**; qa_only from Lead/Application; not extra; map recognized not executed |
| **43e** | **CL6** Flight mapping | ✅ [#307](https://github.com/igortatarynovich/HostFlow/pull/307) `8e2372db` | after **CL5 Gate**; Map executes onto Binding; dest = Profile members; not Zapier / not Flight entity / not extra |
| **43f** | **CL7** Requirement Engine evaluation | ✅ [#309](https://github.com/igortatarynovich/HostFlow/pull/309) `6f2289f1` | after **CL6 Gate**; structured `ready`/`not_ready` + blockers; not boolean; not Hub ask generation |
| **43g** | **Vacancy Overlay Contract** | ✅ [#311](https://github.com/igortatarynovich/HostFlow/pull/311) `7649544d` | after **CL7 Gate**; SoT + merge semantics; not CL8; not Engine v2; not Hub asks |
| **44** | **DR1-runtime** Engine generation | ✅ [#313](https://github.com/igortatarynovich/HostFlow/pull/313) `e6978fe2` | after **DR1-contract Gate ∧ Reference R5 Gate ∧ Vacancy Overlay Gate**; Engine may create Hub outstanding asks; not CL8; not E8 |
| **45** | **E8-bind** Canonical type bind | [brief](documents-platform-e8-bind.md) | after **DR1 Runtime Gate**; **PASS** [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f`; not E8-eval; not CL8; not mass D3–D9 bind |
| **45b** | **E8-eval** Required-doc evaluation | [brief](documents-platform-e8-eval.md) | after **E8-bind Gate**; **PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6`; not OCR; not CL8; not mass D3–D9 bind |
| **45c** | **RPM-1** Authority contract | [brief](requirement-policy-management.md) · [authority SoT](../architecture/requirement-policy-authority.md) | after E8-eval Gate ∧ DAG review [#328](https://github.com/igortatarynovich/HostFlow/pull/328); **PASS** |
| **45d** | **RPM-2** Operator overlay | [brief](requirement-policy-management.md) | after RPM-1 Authority Gate; **PASS** [#342](https://github.com/igortatarynovich/HostFlow/pull/342) / `5196ee64` |
| **45e** | **RPM-3A** Parallel authority retirement | [brief](requirement-policy-management.md) | after RPM-2 Operator Gate; **PASS**; then RPM-3B |
| **45f** | **RPM-3B** Consumer parity | [brief](requirement-policy-management.md) | after RPM-3A Gate; **PASS**; then Consumer Cutover Gate |
| **45g** | **RPM-3** Consumer cutover close | [brief](requirement-policy-management.md) | after RPM-3A ∧ RPM-3B; **PASS** `918274d1` |
| **45h** | **RPM program close** | [brief](requirement-policy-management.md) | **DONE** this amendment — outcome + release delta |
| **46** | **MA-1** Authority contract | [brief](mapping-authority.md) · [authority SoT](../architecture/mapping-authority-contract.md) | after RPM program close; **PASS** |
| **46a** | **MA-2** Resolution runtime | [brief](mapping-authority.md) · [resolution SoT](../architecture/mapping-authority-resolution.md) | after MA-1 Contract Gate; **PASS** |
| **46b** | **MA-3** Operator surface | [brief](mapping-authority.md) · [UX SoT](../architecture/mapping-authority-operator.md) | after Mapping Resolution Gate; **Active** (feat `feat/mapping-authority-ma3-operator-surface` open this PR); Operator Gate not PASS |

**C0–C2.3** ✅. **C2.4 frozen (Epic C residual R1).** **Epic C — complete.** **A2 — PASS_WITH_CONSTRAINTS.** Forms Foundation ✅. D1–D9 brief-complete / goal-incomplete.  
**Active (Product):** **[MA-3](mapping-authority.md)** (UX contract sealed; feat open this PR; Operator Gate not PASS) after Mapping Resolution Gate **PASS**. SoT: [mapping-authority-operator.md](../architecture/mapping-authority-operator.md). E8-eval ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6`. **v1 scope:** [Release Goal](../gates/hostflow-v1-release-goal.md). **Not** Mapping feat. **Not** External Intake. **Not** Hiring E2E. Do not invent CL8. Do not mark Foundation ✅. E8-bind ✅ [#321](https://github.com/igortatarynovich/HostFlow/pull/321). DR1-runtime ✅ [#313](https://github.com/igortatarynovich/HostFlow/pull/313). Overlay ✅ [#311](https://github.com/igortatarynovich/HostFlow/pull/311). E7 ✅ [#287](https://github.com/igortatarynovich/HostFlow/pull/287). Foundation stays 🔄.  
**Active (Engineering):** **DONE** — Reference Program Exit Gate PASS [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c`. No named successor. Legacy full-repo pytest does **not** become Active Engineering.

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

### Documents Platform E4 — Candidate Document Link ← **DONE** (#279 / #280)

[documents-platform-e4-candidate-document-link.md](documents-platform-e4-candidate-document-link.md) [#279](https://github.com/igortatarynovich/HostFlow/pull/279)/[#280](https://github.com/igortatarynovich/HostFlow/pull/280). Candidate (D4) consume path = Hub `document_entity_links` (`candidate` / `primary`). Merge `0af74913`. Column stayed. Foundation stayed 🔄.

### Documents Platform E5 — Candidate Storage Bridge Retirement ← **DONE** (#281 / #282)

[documents-platform-e5-candidate-storage-bridge.md](documents-platform-e5-candidate-storage-bridge.md) [#281](https://github.com/igortatarynovich/HostFlow/pull/281)/[#282](https://github.com/igortatarynovich/HostFlow/pull/282). Drop `documents.candidate_id`. Writers persist Hub links. Merge `702b922c`. Foundation stayed 🔄.

### Documents Platform E6 — Document Expiry / Validity ← **DONE** (#284 / #285)

[documents-platform-e6-document-expiry.md](documents-platform-e6-document-expiry.md) [#284](https://github.com/igortatarynovich/HostFlow/pull/284)/[#285](https://github.com/igortatarynovich/HostFlow/pull/285). Hub `expires_at` / `expiry_state`. Merge `79e638c3`. Foundation stayed 🔄.

### Documents Platform E7 — Document Requests ← **DONE** (#286 / #287)

[documents-platform-e7-document-requests.md](documents-platform-e7-document-requests.md) [#286](https://github.com/igortatarynovich/HostFlow/pull/286)/[#287](https://github.com/igortatarynovich/HostFlow/pull/287). Hub outstanding-ask SoT. Merge `ceafbd48`. Foundation stayed 🔄.

### Entity Field Composition CL0 — Contract Seal ← **PASS** (brief; treated PASS via #289)

[entity-field-composition-cl0-contract-seal.md](entity-field-composition-cl0-contract-seal.md). Page Type + two builder modes. Entity Profile = role manifest. Four requirement kinds; Engine not boolean. `transition` / `handoff` off Profile field. Docs only. Not E8. Not D10. Not Forms P3. Proof later = D4 Information zone.

### CL1+ — Entity Field Composition remainder ← **CL0–CL7 / Overlay PASS**

After CL0: **CL1 → LI-1 → DR1-contract → CL2…CL7 → Vacancy Overlay Contract → DR1-runtime → E8-bind → E8-eval → RPM-1 → RPM-2 → RPM-3A → RPM-3B → Consumer Cutover Gate → RPM program close → MA-1**. CL1 observes live codes; it does **not** canonize country or document-type identity. **DR1-contract** is not a Field Composition slice. **DR1-runtime** is **PASS** [#313](https://github.com/igortatarynovich/HostFlow/pull/313). **E8-bind** is **PASS** [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f`. **E8-eval** is **PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6`. **RPM program DONE**. **MA-1 Contract Gate PASS**. **Mapping Resolution Gate PASS**. Product = **[MA-3](mapping-authority.md)** (brief; feat locked this PR). **CL7** is Engine evaluation, not Engine→Request. Vacancy Overlay leftover of the original CL0 chain is **PASS** — **not** CL8.

### Lifecycle Identity — LI-1 after CL1 (docs sealed; feat locked until CL1 Gate)

[lifecycle-identity-l0-contract-seal.md](lifecycle-identity-l0-contract-seal.md) · [ADR-037](../architecture/ADR-037-lifecycle-identity-canon.md). Module Stage Registry owns existence; Funnel = company overlay; PE = mechanism; Handoff ≠ FunnelTransition. **LI-1** is the only Lifecycle slice between CL1 and CL2: existence/identity guard. LI-2+ stay in the Lifecycle ladder and do **not** block CL2+. Do not universalize `FunnelStage.code`. Do not cut over Candidate/Sales/Client UI in LI-1.

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
**Product active (historical):** **A2 Platform Governance Review** — closed. **Current Product = CL0.** C2.1–C2.3 ✅; C2.4 = frozen (**Epic C residual R1**, not Reference R1).

C2 is **not** Communication v2. Sole responsibility: emit `CommunicationIntent` into the existing platform pipeline.  
Order: Template Platform → Automation → Campaigns → Scheduling → Complete Gate.  
Merge gates: Intent-only egress · no second pipeline · capability isolation · frozen Thread model.

---

## 5c. A2 — Platform Governance Review ← **PASS_WITH_CONSTRAINTS**

Short L0 gate — [platform-governance-review-a2.md](../gates/platform-governance-review-a2.md) (2026-08-03).  
Catalog Notifications↔Communication deferred to Architecture RFC (A2-F1). **Historical next (closed):** Meta Intake Completeness. **Current Product = CL0.**

---

## 6. Meta Intake Completeness (Phase B) ← **MERGED #222**

**Task:** [meta-intake-completeness.md](meta-intake-completeness.md)

Separate from Communication. Chain: Meta payload → Submission raw → normalized → SalesInquiry → UI. No answer may disappear before normalization (show as additional answers). Runs **after** A2 (now closed).

---

## 7. Development rule

Exactly **one Product Track** slice active. Engineering Track is either one Active slice (or the named `{R2, R3}` fan-out) **or DONE with no successor** — pytest does not become Active Engineering.

Next branch only after:

1. Current PR merged  
2. Fast-forward `integration/release-product-a-b`  
3. `make repo-health` **PASSED**  
4. Stale worktrees pruned  
5. One dedicated worktree  

**Do not** start C2.4 (frozen; **Epic C residual R1** — not Reference R1).  
**Do not** skip a named gate in § Locked execution sequence.  
**Do not** treat unlock as schedule. Unlocked work is not Active until the owning track queues it.  
**Do not** give one named slice two independent unlock conditions — split it.  
**Do not** run a third concurrent Engineering slice. Fan-out is only `{Reference R2, Reference R3}` after Reference R1 Gate; then collapse.  
**Do not** activate Reference R5 while Reference R2 is still open.  
**Do not** park later Product on Engineering DONE. Product is **MA-3** after Mapping Resolution Gate PASS (brief; feat locked this PR).  
**Do not** auto-start External Intake / Hiring E2E / min HR because Mapping is Active. Hiring is unlocked by RPM close — unlock ≠ schedule. Do not open MA-3 editor in this PR.  
**Do not** auto-start OCR / packages product / CL8 / ADR-019 automation plane / tenant extension marketplace / Billing product / AI. v1 blockers live in the [Release Goal](../gates/hostflow-v1-release-goal.md); unlock ≠ schedule.  
**Do not** start full Lifecycle / Funnel UI cutover as LI-1.  
**Do not** spend Product capacity on the 657 base-known pytest failures.  
**Do not** mix Stage 5 settings/enable-disable or Acquisition R6 table-cutover into Documents.  
**Do not** treat Shell/chrome or D1–D9 named gates as original Entity Platform done; **do not** mix E7 into an E6/E5/E4/E3/E2/WCP PR; **do not** multiply new entity/application screens, rails, or D10 cutovers; **do not** fold Application Workspace into Entity Workspace; **do not** treat E3 HR bind or E4 Candidate bind as mass D3–D9 `documents` bind; **do not** treat Shell `documents` nav, Vacancy docs section, HR dossier, CandidateCard, or Services billing tab as the D2 `documents` slot; **do not** treat Recruitment Application G4 as the Documents proof; **do not** start OCR / e-sign / packages / Forms **P4–P5** / self-service Billing / AI / ADR-019 plane / tenant extensions (Forms **Publish** is a v1 blocker in the Release Goal — not auto-scheduled here); **do not** put a request / reminder table in Document Hub; **do not** mint Catalog `document.requested`; **do not** leave `documents.candidate_id` as a nullable write target in E5; **do not** patch Recruitment RODO/comments as the platform fix; **do not** mix ListWorkspace into this close-out.  
**Do not** start LI-1 feat while CL0 holds Product Track; **do not** treat `funnels` / `FunnelStage.code` as stage-existence SoT; **do not** union `stages.py` + Lead literals + client FE lists into a new canon; **do not** let LI-2+ stall CL2+.  
**Do** apply [Goal Completion Gate](../gates/goal-completion-gate.md) before marking a future platform phase COMPLETE.  
**Do** require `**Phase class:** platform` + [Original Goal → Completion Proof](../gates/goal-completion-gate.md) on every new platform phase brief (problem to permanently remove + named consumer — not a deliverables list).  
**Do** apply [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) for in-scope vs later; every program close writes **program outcome** and **release delta**.  
**Do** route any “are we ready to launch?” claim to the [Release Readiness Gate](../gates/release-readiness-gate.md) — an empty queue, a closed program, or a green named gate is **not** release-ready.  
**Do** amend this queue when switching Product Active (this revision: live = **MA-3**; brief; feat locked this PR; Mapping Resolution Gate PASS).

---

## 8. History

- 2026-09-04: **MA-3 UX contract sealed.** SoT: [mapping-authority-operator.md](../architecture/mapping-authority-operator.md). One editor / many entry points; untrained-operator Gate criterion. Feat still locked. Mapping Operator Gate not PASS. External Intake / Hiring E2E / min HR remain queued.
- 2026-09-04: **Mapping Resolution Gate PASS.** One resolver (`resolve_mapping_authority`) over `intake_source_profiles.mapping_rules`. Leftover Meta stores read-through / migrated. Precedence chain removed. SoT: [mapping-authority-resolution.md](../architecture/mapping-authority-resolution.md). Active Product → **MA-3** (operator surface; not started this PR). External Intake / Hiring E2E / min HR remain queued. Not CL8. Foundation stays 🔄.
- 2026-09-04: **MA-1 Contract Gate PASS.** Operator question + one write (`intake_source_profiles.mapping_rules`) + twelve-row classification sealed in [mapping-authority-contract.md](../architecture/mapping-authority-contract.md) (`mapping_authority.v1`). Named CI + boundary guard. Feat still locked. Active Product → **MA-2** (resolution runtime; not started this PR). External Intake / Hiring E2E / min HR remain queued. Not CL8. Foundation stays 🔄.
- 2026-09-04: **RPM program close.** Consumer Cutover Gate **PASS** (`918274d1`). Program outcome + release delta recorded. RPM four-checks PASS (Documents domain). Active Product → **[MA-1](mapping-authority.md)** (brief; feat locked this PR). Mapping feat not opened. External Intake / Hiring E2E / min HR remain queued. Hiring unlocked, not scheduled. Not CL8. Foundation stays 🔄. HostFlow v1 is not release-ready.
- 2026-09-03: **RPM-3B Consumer Parity feat PASS.** Surviving consumers read the same R5 required-set (base / require X / remove X). Active Product → **Consumer Cutover Gate** (feat locked this PR). Mapping / Hiring E2E not auto-scheduled. Not CL8. Foundation stays 🔄.
- 2026-09-03: **RPM-3A docs lock.** RPM-2 Operator Gate **PASS** [#342](https://github.com/igortatarynovich/HostFlow/pull/342) / `5196ee64`. Active Product → **RPM-3A** (parallel authority retirement; A + C + P3B `document_required`; feat locked this PR). Internal ladder RPM-3A → RPM-3B → Consumer Cutover Gate. Mapping / Hiring E2E not auto-scheduled. Not CL8. Foundation stays 🔄.
- 2026-09-02: **RPM-1 Authority Gate PASS.** Operator question + one write + nine-row classification sealed in [requirement-policy-authority.md](../architecture/requirement-policy-authority.md) (`requirement_policy_authority.v1`). Named CI + boundary guard. Feat still locked. Active Product → **RPM-2** (operator overlay; not started this PR). Mapping / Hiring E2E / Intake / min HR not auto-scheduled. Not CL8. Foundation stays 🔄.
- 2026-08-31: **Launch-ops opened. Active Launch-ops = [OL-1](operate-and-launch.md)** (docs only), which is the amendment invariant 3 and the 2026-08-28 entry were waiting for. Two decisions the gate could not be closed without, both taken by the owner: the **production target for v1 is one dedicated host running one compose stack** (the brief permits this explicitly; `hostflow.cc` is the existing instance of that shape), and **RR3 / RR4 / RR7 are all owned by `igortatarynovich`**. The second is recorded as a **named residual, not a solved question** — a single person owning deploy, tenant lifecycle *and* the incident path means RR7's escalation step has nobody to escalate to, and that is exactly what RR7 asks. It is carried to **OL-7**, not waved away. What made this the next slice rather than a choice among equals: [TI-5](tenant-isolation-enforcement.md) closed with zero restricted-only failures, and its two remaining items are not development — the deployment role switch, and running the isolation suite under that role in CI. The latter is blocked by **OL-2**, which owns `alembic upgrade heads` failing on a fresh database. That same blocker is what prevents a Release Candidate from being defined at all, so OL-2 now sits on the critical path of both. Two tracks: Product **RPM-1** ∥ Launch-ops **OL-1**; write sets disjoint (docs, `deploy/`, `docs/runbooks/` vs product modules). Engineering stays **DONE** with no successor — reviving it would be a third track.
- 2026-08-30: **The previous entry's headline was wrong, and the correction is the finding.** "Every tenant-scoped table now carries a policy" was measured by a guard that recognised scope by the literal column name `tenant_id`. Three tables are scoped through `agency_tenant_id` / `client_tenant_id`: `candidate_handoffs` and `candidate_handoff_snapshots` had row-level security switched off entirely — cross-tenant candidate presentations and personal snapshot payloads, readable by any tenant for the whole duration of TI-1…TI-4 — and `tenant_links` carried read-only policies, which under enabled row-level security means every write is refused by default. All three are closed, the guard is widened in both dimensions, and two more application paths are fixed (the public client portal; tenant provisioning, which now moves scope explicitly for the tenant it is creating). One table stays open by decision: `tenants`, because the superadmin `/api/v1/platform` surface reads and writes every tenant on an unbound session and needs a named elevated connection first. That makes **TI-5**, not TI-4, the precondition for switching the application role. Roll-up **+1 slice** to 36–53; RC band 2026-10-05 … 2026-10-22 under S2. Active Product stays **RPM-1**; nothing scheduled.
- 2026-08-29: **TI-4 coverage closed — every tenant-scoped table now carries a policy.** 102 tables in seven migrations batched by owning module; the coverage guard's baseline is empty. Identity was decided rather than deferred (policies on `users` / `user_memberships`, authentication over one named owner connection), the nine broken application paths are fixed, and `FORCE ROW LEVEL SECURITY` gained a named, guarded exception for the 15 tables the owner must reach. The role is still not switched on: what stands between here and the switch is the test suite, not the product. Active Product stays **RPM-1**; nothing scheduled.
- 2026-08-29: **TI-3 delivered — database-level isolation works for the first time.** The isolation suite passes with the application connected as a non-superuser, non-owner role without `BYPASSRLS`; 126 policies that could raise instead of denying were rewritten; the connection is split so migrations and platform seeding run as the owner. Two findings that only a live restricted role could produce: the per-request tenant binding did not survive a commit (a session returns its connection to the pool there), so RLS could never have worked; and 10 application paths write with no tenant bound, now frozen by name in a guard. The role stays off until TI-4. Roll-up **+1 slice** to 35–52; RC band 2026-10-03 … 2026-10-20 under S2. Active Product stays **RPM-1**; nothing scheduled.
- 2026-08-29: **First gate-prerequisite code lands.** [TI-1 / TI-2](tenant-isolation-enforcement.md) delivered — isolation contract recorded, RLS coverage guard live with the 102-table gap frozen, and the restricted application role proven to make PostgreSQL refuse cross-tenant rows for the first time. Three of the four failing isolation tests turned out to be test defects, not isolation failures. [QB-1](stabilize-integration-pytest-baseline.md) became reproducible (identical 370-id set on two consecutive runs). Roll-up total unchanged at 34–51: the three delivered slices are offset by TI's estimate rising to 5–8. Active Product stays **RPM-1**; nothing scheduled.
- 2026-08-28: Docs-only. **All five undecided register rows decided by the owner; D4 is empty and EC-6 is met.** U-1 → [QB-1](stabilize-integration-pytest-baseline.md): measure once on an authorised scratch test database and freeze an enumerated, owned known-failure list (1–2 slices, added to the roll-up). U-2 → accepting ADR-022 moves **into** FP-1, which had excluded it (FP-1 grows to 1–1.5 slices). U-3 / U-4 / U-5 → declared residuals with owners, growth rules and the sentence a customer is told: unbound Documents consumer slots, module-local Entity Shell capabilities, and Publish shipping on the `TenantLeadForm` bridge with **no new writer allowed**. Active Product stays **RPM-1**; nothing scheduled.
- 2026-08-28: Docs-only. Ownership cards MOC-1…MOC-3 delivered for **Sales**, **Forms** and **Acquisition** — RR1 unblocked on the ownership dimension, roll-up back to 30–44 slices. The `leads` triple claim is adjudicated per concern in the [Acquisition card](../../modules/acquisition/module_ownership_card.md): Integrations owns channel ingest and credentials, Acquisition owns routing / provenance / diagnostics, Recruitment owns candidate conversion, Sales owns client and order conversion, and the `Lead` ORM plus the operational `/api/v1/leads` surface stay shared transport with no product owner until R6. No code moved, no package split, no certification claimed. Active Product stays **RPM-1**.
- 2026-08-28: Docs-only. Canon-hygiene pass. Nine stale slice statuses corrected against git evidence (Forms P1 / P2 → CLOSED-COMPLETE, C0.1b → COMPLETE `#101`, compliance outbound → COMPLETE, ADR-022 Phase 2 → CLOSED historical, Intake Runtime Split → CLOSED for R1–R5, Communication Context C1–C6 → PARKED with C6 unowned, pytest docker debt rescoped to dev-only, UI consistency → Phase 0–2B). Release authority ordered in [`hierarchy-of-truth.md`](../../governance/hierarchy-of-truth.md): `docs/SSOT.md`, `HOSTFLOW_AUDIT_AND_PLAN.md`, `docs/specs/roadmap.md`, `roadmap-hr-pr14-pr16.md` subordinated by precedence blocks. [Module ownership coverage](../gates/module-ownership-coverage.md) opened — MOC-1…MOC-3 (1.5 slices) required before RR1. Nothing scheduled; Active Product stays **RPM-1**.
- 2026-08-28: Docs-only. QB-1 measured on a clean worktree (`255279fc`, fresh scratch DB, repo root): **371 failed / 3164 passed**, 8 order-dependent; the number proved non-reproducible across working directory and database freshness, and two true negatives surfaced inside the baseline. Roll-up gate prerequisites grew to 4–7 slices (**34–51** serialized-equivalent, RC 2026-10-01…10-18 under S2) after [TI-1…TI-4](tenant-isolation-enforcement.md) was briefed. **U-6 opened and decided the same day** — close the isolation gap before RC — so § D4 is empty again and EC-6 is met. Known-failure routing accepted: blocker briefs take their own rows, TEST-INFRA and TI are fix-before-RC, 44 off-blocker failures tolerated to 2027-01-31.
- 2026-08-28: Docs-only. § Release horizon roll-up added — 20–30 Product slices + 10–14 Launch-ops slices = **30–44 serialized-equivalent**, with measured velocity, three rate scenarios and computed RC / gate-decision bands (planning scenario: RC 2026-09-27…10-11). [Unowned work register](../gates/v1-unowned-work-register.md) opened: 74 canon commitments dispositioned, five (U-1…U-5) undecided and now blocking gate entry via EC-6. RPM brief received an estimate; stale LI-1 status in the Lifecycle seal corrected to PASS.
- 2026-08-28: Docs-only. **Launch-ops** named as the second track (slot left free by Engineering DONE) with [Operate & Launch](operate-and-launch.md) as v1 blocker 6; invariant 3 amended from “no third track” to “two named tracks maximum”; write-set guard extended for OL slices. No Active Launch-ops slice — OL-1 still needs an amendment and named RR3 / RR4 / RR7 owners.
- 2026-08-28: Docs-only. All four remaining v1 blockers received briefs with internal ladders, named gates and estimates — [Mapping Authority](mapping-authority.md) · [External Intake / Forms Publish](external-intake-forms-publish.md) · [Hiring workflow E2E](hiring-workflow-e2e.md) · [min HR handoff](recruitment-hr-minimal-handoff.md). Forms **P3** reclassified from `LOCKED` to v1 blocker 3 in the [roadmap](../architecture/platform-completion-roadmap.md) and the [Forms epic](forms-product-layer-epic.md). Active Product stayed **RPM-1**; nothing scheduled; no feat unlocked.
- 2026-08-27: Queue amendment after DAG dependency-position [#328](https://github.com/igortatarynovich/HostFlow/pull/328) / `087ed286`. Product Track → **[RPM-1](requirement-policy-management.md)** (brief; feat locked). RPM-2 / RPM-3 queued. Mapping not auto-scheduled. Not Hiring E2E. Not CL8. Not Foundation ✅.
- 2026-08-26: [v1 Release DAG dependency-position](../gates/v1-release-dag-dependency-position.md) sealed [#328](https://github.com/igortatarynovich/HostFlow/pull/328). Product Track stayed **none**. RPM recommended first; no schedule; no RPM → Mapping edge.
- 2026-08-26: [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) sealed. Product Track stayed **none**. Five v1 blockers named as a Release DAG (not a linear program order); OCR / packages / AI / automation plane / extensions / self-service Billing explicitly later. No Product slice scheduled.
- 2026-08-25: Queue amendment after E8 Required-Doc Evaluation Gate PASS [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6` (feat `821adf33`). Product Track → **none this amendment**. Engineering Track → Reference program **DONE** (Exit PASS [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c`). Not OCR auto-start. Not CL8. Not Foundation ✅. Pytest stays background.
- 2026-08-25: E8-eval feat opened — D4 required / optional / blocked from R5 merge; Overlay as CL7 input. Named Documents Platform E8 Required-Doc Evaluation Gate. Product Track stays [E8-eval](documents-platform-e8-eval.md). Engineering stays DONE. Not OCR. Not CL8. Not mass D3–D9 bind.
- 2026-08-25: Queue amendment after E8 Canonical Type Bind Gate PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` and docs close-out [#322](https://github.com/igortatarynovich/HostFlow/pull/322) / `196aff39`. Product Track → [E8-eval](documents-platform-e8-eval.md) (brief; feat locked). Engineering Track → Reference program **DONE** (Exit PASS [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c`). Not OCR auto-start. Not CL8. Not mass D3–D9 bind. Pytest stays background.
- 2026-08-25: Queue amendment after E8 Canonical Type Bind Gate PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` (feat `b0129565`). Product Track → **none this amendment**. Engineering Track → Reference program **DONE** (Exit PASS [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c`). E8-eval unlocked (not scheduled; brief not opened). Not CL8. Not mass D3–D9 bind. Pytest stays background.
- 2026-08-25: E8-bind feat opened — D4 Documents display / select / persist canonical registry types; R4 aliases resolve-only. Named Documents Platform E8 Canonical Type Bind Gate. Product Track stays [E8-bind](documents-platform-e8-bind.md). Engineering stays DONE. Not E8-eval. Not CL8. Not mass D3–D9 bind.
- 2026-08-25: Queue amendment after DR1 Runtime Gate PASS [#313](https://github.com/igortatarynovich/HostFlow/pull/313) / `e6978fe2`. Product Track → [E8-bind](documents-platform-e8-bind.md) (brief; feat locked). Engineering Track → Reference program **DONE** (Exit PASS [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c`). Not E8-eval auto-start. Not CL8. Not mass D3–D9 bind. Pytest stays background.
- 2026-08-25: Queue amendment after Vacancy Overlay Gate PASS [#311](https://github.com/igortatarynovich/HostFlow/pull/311) / `7649544d`. Product Track → [DR1-runtime](engine-document-request-dr1-runtime.md) (brief; feat locked). Engineering Track → Reference program **DONE** (Exit PASS [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c`). Not CL8. Not E8 auto-start. Pytest stays background.
- 2026-08-25: Queue amendment after CL7 Gate PASS [#309](https://github.com/igortatarynovich/HostFlow/pull/309) / `6f2289f1`. Product Track → [Vacancy Overlay Contract](entity-profile-vacancy-overlay-contract.md) (brief; feat locked). Not CL8. Not DR1-runtime. Not E8.
- 2026-08-25: Queue amendment after CL6 Gate PASS [#307](https://github.com/igortatarynovich/HostFlow/pull/307) / `8e2372db`. Product Track → [CL7 Requirement Engine evaluation](entity-field-composition-cl7-engine-eval.md) (feat). Not DR1-runtime. Not E8. Vacancy overlay leftover. Do not invent CL8.
- 2026-08-23: Execution canon sealed — one work = one unlock; unlock ≠ schedule; Engineering fan-out only `{R2, R3}` then collapse; Product `CL0 → CL1 → LI-1 → DR1-contract → CL2…`; DR1-runtime parks on R5 without blocking CL2+; E8-bind / E8-eval split. Always **Reference Rn** vs **Epic C residual R1**.
- 2026-08-23: **ADR-037** + Lifecycle Identity L2 + brief — canon sealed. **LI-1 after CL1**, not after CL7 / not full Lifecycle ([brief](lifecycle-identity-l0-contract-seal.md)). Product Track **stays** [CL0](entity-field-composition-cl0-contract-seal.md).
- 2026-08-23: Platform Reference Identity SoT brief — normative contract Reference R1–R5. Engineering Track → **Reference R1** (parallel CL0 only). [brief](platform-reference-identity-sot.md). E8 split-gated. XK excluded from R1 ISO set.
- 2026-08-23: CL0 brief opened — Entity Field Composition contract seal. Product Track → [Entity Field Composition CL0](entity-field-composition-cl0-contract-seal.md) (feat locked). E7 ✅ [#287](https://github.com/igortatarynovich/HostFlow/pull/287) (`ceafbd48`). E8 stays locked. Foundation stays 🔄.
- 2026-08-23: E7 feat opened — Hub outstanding-ask read on public contract. Product Track stays [Documents Platform E7](documents-platform-e7-document-requests.md). E8+ locked. Foundation stays 🔄.
- 2026-08-23: E7 brief opened — Document requests. Product Track → [Documents Platform E7](documents-platform-e7-document-requests.md) (feat locked). E6 ✅ [#285](https://github.com/igortatarynovich/HostFlow/pull/285) (`79e638c3`). D3 / D5–D7 / D9 stay unbound. Foundation stays 🔄.
- 2026-08-23: E6 feat opened — Hub expiry read on public contract; workflow SoT leaves Candidate FK. Product Track stays [Documents Platform E6](documents-platform-e6-document-expiry.md). E7+ locked. Foundation stays 🔄.
- 2026-08-23: E6 brief opened — Document expiry / validity. Product Track → [Documents Platform E6](documents-platform-e6-document-expiry.md) (feat locked). E5 ✅ [#282](https://github.com/igortatarynovich/HostFlow/pull/282) (`702b922c`). D3 / D5–D7 / D9 stay unbound. Foundation stays 🔄.
- 2026-08-22: E5 feat opened — drop `documents.candidate_id`; Hub-only Candidate relationship. Product Track stays [Documents Platform E5](documents-platform-e5-candidate-storage-bridge.md). E6+ locked. Foundation stays 🔄.
- 2026-08-22: E5 brief opened — Candidate storage-bridge retirement (`candidate_id` drop). Product Track → [Documents Platform E5](documents-platform-e5-candidate-storage-bridge.md) (feat locked). E4 ✅ [#280](https://github.com/igortatarynovich/HostFlow/pull/280) (`0af74913`). D3 / D5–D7 / D9 stay unbound. Foundation stays 🔄.
- 2026-08-22: E4 feat opened — D4 bind + Candidate Document Link resolve on `documents.hub_adapter_v1`; named Candidate Document Link Gate. Product Track stays [Documents Platform E4](documents-platform-e4-candidate-document-link.md). E5+ locked. Foundation stays 🔄.
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
