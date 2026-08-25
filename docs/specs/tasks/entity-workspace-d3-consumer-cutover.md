# Entity Workspace D3 — Consumer Cutover (Phase D)

**Status:** **COMPLETE** ([#255](https://github.com/igortatarynovich/HostFlow/pull/255)/[#256](https://github.com/igortatarynovich/HostFlow/pull/256) · `bdaeb47b` · merge `c30b07f8`)  
**Next:** [D5 Client Cutover](entity-workspace-d5-client-cutover.md) (brief; feat locked)  
**Branch (docs):** `docs/entity-workspace-d3-consumer-cutover` ✅ [#255](https://github.com/igortatarynovich/HostFlow/pull/255)  
**Branch (code):** `feat/entity-workspace-d3-consumer-cutover` ✅ [#256](https://github.com/igortatarynovich/HostFlow/pull/256)  
**Parents:** [D2 Composition Contract](entity-workspace-d2-composition-contract.md) ✅ · [D1 Contract Seal](entity-workspace-d1-contract-seal.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase D](../architecture/platform-completion-roadmap.md) · [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) · [A2-F7](../gates/platform-governance-review-a2.md) · [UI constitution §3.3](../architecture/ui-constitution-v1.md) · [Forms Public Contract](../architecture/forms-public-contract.md) · [Communication foundation](../architecture/communication-platform-foundation.md)

> D2 froze the slot catalog.  
> D3 binds the **first consumer** to that catalog — before remaining modules cut over.  
> D3 does **not** mint Catalog Passport, enable `documents`, collapse Shell `EntityWorkspaceSectionId` into composition slots, or cut over Candidate / HR / all modules.

**Naming (do not collapse):** this **Entity Workspace D3** is not D2 composition contract, not D1 contract seal, not PX chrome land, not Candidate Shell adapter already on tip, not Documents Phase E.

---

## Why this slice

D2 locked: slot ids `overview` · `timeline` · `communication` · `forms` · `documents` (reserved) · `context-rail`.  
The remaining hole: product screens still compose ad-hoc surfaces beside that catalog.

On tip today:

| Surface | What it is | D3 status |
|---------|------------|-----------|
| Sales Inquiry detail (`ApplicationSalesDetailPanel`) | First consumer bound to D2 slots | **this feat** |
| Candidate `EntityWorkspacePage` | D1 Shell adapter using Shell `EntityWorkspaceSectionId` (incl. a `documents` **nav section**) | **Out of D3** — do not collapse Shell sections into D2 slots here |
| Kit chrome file | Engineering / Kit Baseline sync | Unchanged |

Without a first-consumer contract, Sales will keep a parallel inquiry shell, and Candidate’s Shell `documents` section will be misread as D2 `documents` enable (forbidden until Phase E).

---

## Goal

One first consumer on the D2 composition model:

```text
Sales Inquiry (module-owned overview body)
  ├── overview          ← required; Sales-owned
  ├── timeline          ← content slot (existing inquiry timeline; not a second Activity product)
  ├── communication     ← Communication public contracts / adapters only
  ├── forms             ← Forms public contracts (HostFlow Form / submissions) only
  ├── documents         ← reserved empty (Phase E)
  └── context-rail      ← D1 chrome slot
```

Modules configure **which enabled slots** they turn on. They do **not** invent new platform slot kinds. Shell `EntityWorkspaceSectionId` (`contacts` / `relations` / `tasks` / …) stays adapter navigation — **not** the composition SoT.

---

## First consumer (normative)

**Sales Inquiry** is the D3 cutover target.

Rationale: sequential Product Track is Sales → Communication; inquiry detail is still a local panel stack — the hole D2 named. Candidate already consumes D1 Shell chrome; collapsing its Shell sections (especially `documents` nav) is **D4+**.

**Cutover means:**

1. Sales Inquiry detail composes only D2 catalog slots (`compositionSlots.ts`).  
2. Enabled slots ⊆ `{overview, timeline, communication, forms, context-rail}`.  
3. `documents` stays reserved / cannot be enabled.  
4. Platform slots (`communication`, `forms`) go through public adapters only (Architecture Rule 2).  
5. No parallel Sales Inquiry workspace / side-panel product beside this compose.

**Cutover does not mean:** full Kit chrome file land; Universal Entity Workspace done; Candidate/HR/Vacancy cutover; Catalog Passport; Forms P3–P5.

---

## Locked principle

```text
D1  → who owns Entity Workspace + chrome/adapter boundary
D2  → which slots exist and how platforms compose
D3  → first consumer (Sales Inquiry) binds to D2 slots (this)
D4+ → remaining consumers (Candidate Shell section collapse, HR, …)
```

D3 **must not**:

- cut over Candidate / HR / Vacancy / Client / Order workspaces  
- collapse Shell `EntityWorkspaceSectionId` into D2 slot ids  
- treat Candidate `documents` nav section as D2 `documents` enable  
- mint Entity Catalog Passport / Manifest  
- land Kit Baseline chrome as a substitute for cutover  
- open Documents Phase E, Billing, or AI  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- invent a second shell or promote module workspaces into the kit  

---

## Phase D ladder

| Slice | Focus | Status |
|-------|--------|--------|
| **D1** | Contract seal | ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252) |
| **D2** | Composition contract (slots) | ✅ [#253](https://github.com/igortatarynovich/HostFlow/pull/253)/[#254](https://github.com/igortatarynovich/HostFlow/pull/254) |
| **D3** | First consumer cutover (Sales Inquiry) | ✅ [#255](https://github.com/igortatarynovich/HostFlow/pull/255)/[#256](https://github.com/igortatarynovich/HostFlow/pull/256) |
| **D4** | Candidate cutover (Shell ≠ D2 slots) | [brief](entity-workspace-d4-candidate-cutover.md) (feat locked) |
| **D5+** | HR / Vacancy / Client / Order | locked until D5 brief |

---

## Entity Workspace D3 Cutover Gate (CI — mandatory)

Named step: **Entity Workspace D3 Cutover Gate**  
(`tests/platform/test_entity_workspace_d3_cutover_gate.py`). Full-repo pytest red does not waive it. D1 Contract Seal Gate and D2 Composition Gate stay green.

- First consumer = Sales Inquiry; remaining modules not cut over  
- D2 slot catalog unchanged; `documents` still cannot be enabled  
- Shell `EntityWorkspaceSectionId` not collapsed into composition slots  
- No Entity Catalog Passport mint  
- Entity Foundation maturity stays 🔄 (not ✅)

---

## In scope (this docs PR)

1. This brief.  
2. Close D2 with merge refs [#253](https://github.com/igortatarynovich/HostFlow/pull/253)/[#254](https://github.com/igortatarynovich/HostFlow/pull/254).  
3. Point Product Track / queue / roadmap / AGENTS here.  
4. Feat locked until this brief merges.

## In scope (feat PR — after this brief)

1. Named **Entity Workspace D3 Cutover Gate** — first consumer Sales Inquiry bound to D2 enabled slots; reserved `documents` cannot be enabled; no Catalog Passport; D1+D2 gates still green.  
2. Architecture Review Checklist (10 questions) in the feat PR description.  
3. Sales Inquiry detail composes D2 slots (overview / timeline / communication / forms / context-rail) via public adapters — **no** Candidate/HR cutover, **no** Shell section collapse.  
4. Pointers stay on D3 until D4 brief opens.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Candidate / HR / Vacancy / Client / Order cutover | D4+ |
| Collapse Shell `EntityWorkspaceSectionId` into D2 slots | D4+ |
| Catalog Passport / Manifest | Later D slice (+ RFC if Catalog shape) |
| Kit Baseline chrome file land | Engineering / Kit sync |
| Documents lifecycle / `documents` enable | Phase E |
| Forms P3 / P4 / P5 | Locked |
| Stage 5 settings / R6 | Unchanged |

---

## Architecture Review (L0 — this feat)

| # | Answer |
|---|--------|
| 1 Owner | Platform UI / Workspace (ADR-010); Sales owns Inquiry overview body; platform slots owned by their platforms |
| 2 Exists? | D2 slot catalog yes; Sales Inquiry D2 compose **new** (this); Candidate Shell adapter already D1 — **not** this |
| 3 Adapter | Shell adapter unchanged; Communication / Forms via their public adapters only |
| 4 Boundary | No Candidate/HR cutover; no Shell/D2 collapse; no Passport; no Documents enable; no Forms P3–P5; no fifth shell |
| 5 Settings | No new Manifest keys |
| 6 SoT | Slot catalog = D2 brief + `compositionSlots.ts`; Sales Inquiry overview body stays Sales-owned |
| 7 Events | None new |
| 8 Requires | D2 ✅ · D1 ✅ · Forms Foundation ✅ · Communication foundation for compose |
| 9 License | None new |
| 10 Public contract | Additive first-consumer binding; no Catalog Passport; no DTO bump |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- [x] Brief merged ([#255](https://github.com/igortatarynovich/HostFlow/pull/255))
- [x] Named Entity Workspace D3 Cutover Gate (feat)
- [x] First consumer = Sales Inquiry; Candidate/HR not cut over
- [x] Reserved `documents` cannot be enabled
- [x] Shell `EntityWorkspaceSectionId` not collapsed into D2 slots
- [x] No Catalog Passport mint
- [x] D1+D2 gates still green; Entity Foundation remains 🔄
- [x] Forms P3–P5 and Documents Phase E stay out of Product Track
- Product Track → D4 brief (feat locked)

---

## DoD

- [x] Brief sealed with first consumer + in/out + acceptance  
- [x] Queue + roadmap + AGENTS point at this brief  
- [x] D2 marked complete with #254 merge ref  
- [x] Feat PR — Cutover Gate [#256](https://github.com/igortatarynovich/HostFlow/pull/256)

---

## History

- 2026-08-15: D3 feat ✅ [#256](https://github.com/igortatarynovich/HostFlow/pull/256) (`bdaeb47b` / merge `c30b07f8`). Product Track → Entity Workspace D4 Candidate cutover brief (feat locked).
- 2026-08-15: D3 feat — named **Entity Workspace D3 Cutover Gate**; Sales Inquiry bound to D2 slots; Candidate/HR out; `documents` reserved; no Passport. Next = D4 brief (locked).
- 2026-08-15: D3 brief opened — first consumer = Sales Inquiry; D4+ remaining consumers locked. Feat locked. D2 ✅ [#253](https://github.com/igortatarynovich/HostFlow/pull/253)/[#254](https://github.com/igortatarynovich/HostFlow/pull/254) (`42bd51b7` / merge `a61543cf`).
