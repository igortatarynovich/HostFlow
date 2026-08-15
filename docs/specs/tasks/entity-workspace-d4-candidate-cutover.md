# Entity Workspace D4 — Candidate Cutover (Phase D)

**Status:** **COMPLETE** ([#257](https://github.com/igortatarynovich/HostFlow/pull/257)/[#258](https://github.com/igortatarynovich/HostFlow/pull/258) · `0ab40717` · merge `b5f1f00a`)  
**Next:** [D5 Client Cutover](entity-workspace-d5-client-cutover.md) (brief; feat locked)  
**Branch (docs):** `docs/entity-workspace-d4-candidate-cutover` ✅ [#257](https://github.com/igortatarynovich/HostFlow/pull/257)  
**Branch (code):** `feat/entity-workspace-d4-candidate-cutover` ✅ [#258](https://github.com/igortatarynovich/HostFlow/pull/258)  
**Parents:** [D3 Consumer Cutover](entity-workspace-d3-consumer-cutover.md) ✅ · [D2 Composition Contract](entity-workspace-d2-composition-contract.md) ✅ · [D1 Contract Seal](entity-workspace-d1-contract-seal.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase D](../architecture/platform-completion-roadmap.md) · [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) · [A2-F7](../gates/platform-governance-review-a2.md) · [UI constitution §3.3](../architecture/ui-constitution-v1.md)

> D3 bound Sales Inquiry to the D2 slot catalog.  
> D4 binds **Candidate Entity Workspace** to that catalog — without collapsing Shell navigation into composition slots.  
> D4 does **not** enable D2 `documents`, mint Catalog Passport, or cut over HR / Vacancy / Client / Order.

**Naming (do not collapse):** this **Entity Workspace D4** is not D3 Sales Inquiry cutover, not D2 composition contract, not D1 contract seal, not PX chrome land, not Documents Phase E. Shell `documents` **nav section** ≠ D2 `documents` **composition slot**.

---

## Why this slice

D3 locked Sales Inquiry onto `overview` · `timeline` · `communication` · `forms` · `context-rail`.  
The remaining hole: Candidate already uses D1 `EntityWorkspaceShell` with Shell `EntityWorkspaceSectionId` (`overview` / `contacts` / `documents` / `timeline` / `relations` / `tasks` / `outcome`). Those ids look like composition slots and are not.

On tip today:

| Surface | What it is | D4 status |
|---------|------------|-----------|
| Sales Inquiry (`ApplicationSalesDetailPanel`) | D3 first consumer | ✅ leave as-is |
| Candidate `EntityWorkspacePage` | D1 Shell adapter; Shell nav includes `documents` | **this consumer** |
| HR / Vacancy / Client / Order | module workspaces | **Out of D4** |

Without an explicit Candidate binding, reviewers will treat Shell `documents` as D2 `documents` enable (forbidden until Phase E) or invent extra platform slot kinds (`contacts` / `relations` / `tasks`).

---

## Goal

Candidate composes D2 **enabled** slots; Shell nav stays adapter-only:

```text
Candidate EntityWorkspaceShell (D1 adapter chrome)
  ├── Shell nav (EntityWorkspaceSectionId)     ← adapter; not composition SoT
  │     contacts / relations / tasks / outcome / documents-nav
  └── D2 composition slots
        ├── overview          ← required; Recruitment-owned body
        ├── timeline          ← content slot (not a second Activity product)
        ├── communication     ← Communication public contracts / adapters only
        ├── forms             ← Forms public contracts only
        ├── documents         ← reserved empty (Phase E) — NOT the Shell nav section
        └── context-rail      ← D1 chrome slot
```

**Hard distinction:**

| Id | Contract | D4 rule |
|----|----------|---------|
| Shell `documents` | `EntityWorkspaceSectionId` adapter nav → existing Candidate docs panel | May remain as **module nav**; not a D2 slot |
| D2 `documents` | `compositionSlots.ts` platform slot | **Must stay reserved** until Phase E |

D4 **must not** map Shell `documents` → `ENTITY_WORKSPACE_ENABLED_SLOT_IDS`.

---

## Consumer (normative)

**Candidate** is the D4 cutover target.

**Cutover means:**

1. Candidate workspace declares D2 enabled slots ⊆ `{overview, timeline, communication, forms, context-rail}`.  
2. Platform slots (`communication`, `forms`) go through public adapters only (Architecture Rule 2).  
3. Shell `EntityWorkspaceSectionId` is not collapsed into `EntityWorkspaceSlotId`.  
4. D2 `documents` stays reserved / cannot be enabled.  
5. No parallel Candidate workspace / fifth shell beside `EntityWorkspaceShell`.

**Cutover does not mean:** Documents Phase E; Catalog Passport; HR/Vacancy/Client/Order cutover; Kit Baseline chrome file land; Forms P3–P5; deleting Shell nav (`contacts` / `tasks` / …).

---

## Locked principle

```text
D1  → who owns Entity Workspace + chrome/adapter boundary
D2  → which slots exist and how platforms compose
D3  → first consumer (Sales Inquiry)
D4  → Candidate binds to D2 slots; Shell nav ≠ composition (this)
D5+ → remaining consumers (HR / Vacancy / Client / Order)
```

D4 **must not**:

- enable D2 `documents` or treat Shell `documents` nav as that enable  
- collapse `EntityWorkspaceSectionId` into `compositionSlots.ts`  
- cut over HR / Vacancy / Client / Order  
- mint Entity Catalog Passport / Manifest  
- land Kit Baseline chrome as a substitute for cutover  
- open Documents Phase E, Billing, or AI  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- invent a second Candidate shell or promote Candidate Workspace into the kit  

---

## Phase D ladder

| Slice | Focus | Status |
|-------|--------|--------|
| **D1** | Contract seal | ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252) |
| **D2** | Composition contract (slots) | ✅ [#253](https://github.com/igortatarynovich/HostFlow/pull/253)/[#254](https://github.com/igortatarynovich/HostFlow/pull/254) |
| **D3** | First consumer (Sales Inquiry) | ✅ [#255](https://github.com/igortatarynovich/HostFlow/pull/255)/[#256](https://github.com/igortatarynovich/HostFlow/pull/256) |
| **D4** | Candidate cutover (Shell ≠ D2 slots) | ✅ [#257](https://github.com/igortatarynovich/HostFlow/pull/257)/[#258](https://github.com/igortatarynovich/HostFlow/pull/258) |
| **D5+** | HR / Vacancy / Client / Order | D5 = [Client](entity-workspace-d5-client-cutover.md) (brief; feat locked) |

---

## Entity Workspace D4 Cutover Gate (CI — mandatory after feat)

Named step: **Entity Workspace D4 Cutover Gate**  
(`tests/platform/test_entity_workspace_d4_cutover_gate.py`). Full-repo pytest red does not waive it. D1 / D2 / D3 gates stay green.

- Consumer = Candidate; HR / Vacancy / Client / Order not cut over  
- D2 slot catalog unchanged; D2 `documents` still cannot be enabled  
- Shell `EntityWorkspaceSectionId` not collapsed into composition slots  
- Shell `documents` nav ≠ D2 `documents` enable  
- No Entity Catalog Passport mint  
- Entity Foundation maturity stays 🔄 (not ✅)

---

## In scope (this docs PR)

1. This brief.  
2. Close D3 with merge refs [#255](https://github.com/igortatarynovich/HostFlow/pull/255)/[#256](https://github.com/igortatarynovich/HostFlow/pull/256).  
3. Point Product Track / queue / roadmap / AGENTS here.  
4. Feat locked until this brief merges.

## In scope (feat PR — after this brief)

1. Named **Entity Workspace D4 Cutover Gate** — Candidate bound to D2 enabled slots; reserved D2 `documents` cannot be enabled; Shell nav not collapsed; no Catalog Passport; D1–D3 gates still green.  
2. Architecture Review Checklist (10 questions) in the feat PR description.  
3. Candidate `EntityWorkspacePage` composes D2 slots via public adapters — **no** HR/Vacancy cutover, **no** D2 `documents` enable.  
4. Pointers stay on D4 until D5 brief opens.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| HR / Vacancy / Client / Order cutover | D5+ |
| D2 `documents` enable / Documents lifecycle | Phase E |
| Catalog Passport / Manifest | Later D slice (+ RFC if Catalog shape) |
| Kit Baseline chrome file land | Engineering / Kit sync |
| Forms P3 / P4 / P5 | Locked |
| Stage 5 settings / R6 | Unchanged |

---

## Architecture Review (L0 — this feat)

| # | Answer |
|---|--------|
| 1 Owner | Platform UI / Workspace (ADR-010); Recruitment owns Candidate overview body; platform slots owned by their platforms |
| 2 Exists? | D1 Shell adapter yes; D2 catalog yes; Candidate D2 compose **new** (this); Sales Inquiry D3 already bound |
| 3 Adapter | EntityWorkspaceShell unchanged; Communication / Forms via their public adapters only |
| 4 Boundary | No HR/Vacancy/Client/Order; no Shell/D2 collapse; no D2 `documents` enable; no Passport; no Forms P3–P5; no fifth shell |
| 5 Settings | No new Manifest keys |
| 6 SoT | Slot catalog = D2 + `compositionSlots.ts`; Shell nav = adapter; Candidate overview body stays module-owned |
| 7 Events | None new |
| 8 Requires | D3 ✅ · D2 ✅ · D1 ✅ · Forms Foundation ✅ · Communication foundation for compose |
| 9 License | None new |
| 10 Public contract | Additive Candidate binding; no Catalog Passport; no DTO bump |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- [x] Brief merged ([#257](https://github.com/igortatarynovich/HostFlow/pull/257))
- [x] Named Entity Workspace D4 Cutover Gate (feat)
- [x] Consumer = Candidate; HR / Vacancy / Client / Order not cut over
- [x] D2 `documents` cannot be enabled; Shell `documents` nav is not that enable
- [x] Shell `EntityWorkspaceSectionId` not collapsed into D2 slots
- [x] No Catalog Passport mint
- [x] D1–D3 gates still green; Entity Foundation remains 🔄
- [x] Forms P3–P5 and Documents Phase E stay out of Product Track
- Product Track → [D5 Client Cutover](entity-workspace-d5-client-cutover.md) (brief; feat locked)

---

## DoD

- [x] Brief sealed with Candidate consumer + Shell≠D2 distinction + in/out + acceptance
- [x] Queue + roadmap + AGENTS point at this brief
- [x] D3 marked complete with #256 merge ref
- [x] Feat: Candidate bound to D2 enabled slots; named Cutover Gate

---

## History

- 2026-08-15: D4 ✅ [#257](https://github.com/igortatarynovich/HostFlow/pull/257)/[#258](https://github.com/igortatarynovich/HostFlow/pull/258) (`0ab40717` / merge `b5f1f00a`). Next = [D5 Client Cutover](entity-workspace-d5-client-cutover.md) (brief; feat locked).
- 2026-08-15: D4 feat — named **Entity Workspace D4 Cutover Gate**; Candidate bound to D2 enabled slots; Shell `documents` nav ≠ D2 `documents` enable; HR/Vacancy/Client/Order out; no Passport. Next = D5 brief (locked).
- 2026-08-15: D4 brief opened — Candidate cutover; Shell `documents` nav ≠ D2 `documents` enable; D5+ remaining consumers locked. Feat locked. D3 ✅ [#255](https://github.com/igortatarynovich/HostFlow/pull/255)/[#256](https://github.com/igortatarynovich/HostFlow/pull/256) (`bdaeb47b` / merge `c30b07f8`).
