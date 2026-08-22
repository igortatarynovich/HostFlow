# Entity Workspace D2 — Composition Contract (Phase D)

**Status:** **COMPLETE** ([#253](https://github.com/igortatarynovich/HostFlow/pull/253)/[#254](https://github.com/igortatarynovich/HostFlow/pull/254) · `42bd51b7` · merge `a61543cf`)  
**Next:** [D3 Consumer Cutover](entity-workspace-d3-consumer-cutover.md) (brief; feat locked)  
**Branch (docs):** `docs/entity-workspace-d2-composition-contract` ✅ [#253](https://github.com/igortatarynovich/HostFlow/pull/253)  
**Branch (code):** `feat/entity-workspace-d2-composition-contract` ✅ [#254](https://github.com/igortatarynovich/HostFlow/pull/254)  
**Parents:** [D1 Contract Seal](entity-workspace-d1-contract-seal.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase D](../architecture/platform-completion-roadmap.md) · [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) · [A2-F7](../gates/platform-governance-review-a2.md) · [UI constitution §3.3](../architecture/ui-constitution-v1.md) · [Forms Public Contract](../architecture/forms-public-contract.md) · [Communication foundation](../architecture/communication-platform-foundation.md)

> D1 sealed ownership and Shell ≠ Universal.  
> D2 seals **which platform surfaces** may compose onto one entity — the composition contract — before any consumer cutover.  
> D2 does **not** ship Universal runtime UI, mint Catalog Passport, or open Documents Phase E.

**Naming (do not collapse):** this **Entity Workspace D2** is not D1 contract seal, not PX chrome land, not Communication C1 Inbox, not Forms C3–C6, not Documents Phase E.

---

## Why this slice

D1 locked: owner, chrome SoT path, Shell adapter, no module-workspace promotion, Entity Foundation 🔄.  
The remaining hole: product screens will invent ad-hoc “slots” (thread panel here, form embed there, docs drawer elsewhere) without a shared composition contract — recreating temporary side panels that Phase D forbids.

D2 names the **slot set** and **compose rules**. Runtime cutover starts at [D3](entity-workspace-d3-consumer-cutover.md) (Sales Inquiry first).

---

## Goal

One normative composition model:

```text
EntityWorkspace chrome (SoT path: components/ui/EntityWorkspace)
  ├── header / actions / summary / navigation   ← chrome (D1)
  ├── content slots                             ← D2 contract
  │     ├── overview (module-owned body)
  │     ├── timeline (content slot — not a second product)
  │     ├── communication (platform surface)
  │     ├── forms (platform surface — HostFlow Form / submissions)
  │     └── documents (platform — catalog-enabled in [E2](documents-platform-e2-public-contract.md) ✅; first bind = [E3](documents-platform-e3-first-consumer-bind.md) HR employee ✅; Candidate = [E4](documents-platform-e4-candidate-document-link.md) ✅; storage-bridge retirement = [E5](documents-platform-e5-candidate-storage-bridge.md))
  └── context rail                              ← chrome slot (D1)
EntityWorkspaceShell                            ← passport adapter only
```

Modules configure **which slots are enabled** and supply overview body. They do **not** own parallel shells or invent new platform slot kinds without amending this contract.

---

## Slot catalog (normative for D2)

| Slot id | Kind | Owner of surface | D2 status |
|---------|------|------------------|-----------|
| `overview` | content | Consuming module | Required in contract; body = module |
| `timeline` | content | Platform chrome slot | Named; not a second Activity product |
| `communication` | platform | Communication platform | Contracted; compose via public contracts only |
| `forms` | platform | Forms platform (ADR-007) | Contracted; HostFlow Form / envelope — no second form stack |
| `documents` | platform | Documents (Phase E) | Catalog-enabled in [E2](documents-platform-e2-public-contract.md) ✅. First consumer bind = [E3](documents-platform-e3-first-consumer-bind.md) (HR employee) ✅. Candidate Document Link = [E4](documents-platform-e4-candidate-document-link.md). D3 / D5–D7 / D9 stay unbound |
| `context-rail` | chrome | Kit / Shell adapter | Already D1 chrome; not a new platform SoT |

**Rules:**

1. New slot kinds require amending this contract (and Architecture Review) — no silent product slots.  
2. Platform slots consume **public contracts / adapters** only — no cross-module internal imports (Architecture Rule 2).  
3. `documents` is a named platform slot. Enabling it in the **catalog** is [E2](documents-platform-e2-public-contract.md) ✅. First consumer bind is [E3](documents-platform-e3-first-consumer-bind.md) (HR employee) ✅. Candidate bind is [E4](documents-platform-e4-candidate-document-link.md). Binding D3 / D5–D7 / D9 before a later named E slice is **forbidden**. E1 contract seal is not enable.  
4. Timeline stays a **content slot**, not a separate Activity Workspace product.

---

## Locked principle

```text
D1  → who owns Entity Workspace + chrome/adapter boundary
D2  → which slots exist and how platforms compose (this)
D3  → first consumer (Sales Inquiry) binds to D2 slots
D4+ → remaining consumers
```

D2 **must not**:

- implement Universal Entity Workspace UI cutover for Recruitment / Sales / HR  
- mint Entity Catalog Passport / Manifest  
- land Kit Baseline chrome as a substitute for composition (Engineering sync stays separate)  
- open Documents Phase E, Billing, or AI  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- invent a second shell or promote Candidate / HR / Vacancy Workspace into the kit  

---

## Phase D ladder

| Slice | Focus | Status |
|-------|--------|--------|
| **D1** | Contract seal | ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252) |
| **D2** | Composition contract (slots) | ✅ [#253](https://github.com/igortatarynovich/HostFlow/pull/253)/[#254](https://github.com/igortatarynovich/HostFlow/pull/254) |
| **D3** | First consumer cutover (Sales Inquiry) | [brief](entity-workspace-d3-consumer-cutover.md) (feat locked) |
| **D4+** | Remaining consumers | locked until D4 brief |

---

## Entity Workspace D2 Composition Gate (CI — mandatory)

Named step: **Entity Workspace D2 Composition Gate**  
(`tests/platform/test_entity_workspace_d2_composition_gate.py`). Full-repo pytest red does not waive it. D1 Contract Seal Gate stays green.

- Slot catalog frozen: `overview` · `timeline` · `communication` · `forms` · `documents` · `context-rail`
- Typed allowlist: `hostflow-frontend/src/platform/entity-workspace/compositionSlots.ts` (not Shell `EntityWorkspaceSectionId`)
Until [E2](documents-platform-e2-public-contract.md) feat, runtime was **Empty / unavailable** (reserved in `compositionSlots.ts`). E2 feat enabled the catalog slot. First consumer bind is [E3](documents-platform-e3-first-consumer-bind.md) (HR employee) ✅; Candidate bind is [E4](documents-platform-e4-candidate-document-link.md); D3 / D5–D7 / D9 stay unbound.
- No Entity Catalog Passport mint
- No consumer cutover screens
- Entity Foundation maturity stays 🔄 (not ✅)

---

## In scope (this docs PR)

1. This brief.  
2. Close D1 with merge refs [#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252).  
3. Point Product Track / queue / roadmap / AGENTS here.  
4. Feat locked until this brief merges.

## In scope (feat PR — after this brief)

1. Named **Entity Workspace D2 Composition Gate** — slot catalog frozen in docs + tests; reserved `documents` cannot be enabled; no Catalog Passport; D1 gate still green.  
2. Architecture Review Checklist (10 questions) in the feat PR description.  
3. Optional: typed slot-id constant / allowlist in frontend platform types — **no** consumer cutover screens.  
4. Pointers stay on D3 until D4 brief opens.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Consumer cutover (Sales Inquiry first) | [D3](entity-workspace-d3-consumer-cutover.md) |
| Remaining consumers (Candidate / HR / …) | D4+ |
| Catalog Passport / Manifest | Later D slice (+ RFC if Catalog shape) |
| Kit Baseline chrome file land | Engineering / Kit sync |
| Documents lifecycle | Phase E |
| Forms P3 / P4 / P5 | Locked |
| Stage 5 settings / R6 | Unchanged |

---

## Architecture Review (L0 — this feat)

| # | Answer |
|---|--------|
| 1 Owner | Platform UI / Workspace (ADR-010); platform slots owned by their platforms |
| 2 Exists? | Chrome/Shell (D1); composition slot catalog **new** (this); Universal runtime **no** |
| 3 Adapter | Shell adapter unchanged; Communication / Forms via their public adapters only |
| 4 Boundary | No cutover UI; no Passport; no Documents enable; no Forms P3–P5; no fifth shell |
| 5 Settings | No new Manifest keys |
| 6 SoT | Slot catalog = this brief + `compositionSlots.ts` allowlist; module overview body stays module-owned |
| 7 Events | None new |
| 8 Requires | D1 ✅ · Forms Foundation ✅ · Communication foundation available for later compose |
| 9 License | None new |
| 10 Public contract | Additive slot-id allowlist freeze; no Catalog Passport; no DTO bump |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- [x] Brief merged ([#253](https://github.com/igortatarynovich/HostFlow/pull/253))
- [x] Named Entity Workspace D2 Composition Gate
- [x] Reserved `documents` cannot be enabled
- [x] No Catalog Passport mint
- [x] No consumer cutover UI
- [x] D1 gate still green; Entity Foundation remains 🔄
- [x] Forms P3–P5 and Documents Phase E stay out of Product Track
- Product Track → D3 brief (feat locked)

---

## DoD

- [x] Brief sealed with slot catalog + in/out + acceptance  
- [x] Queue + roadmap + AGENTS point at this brief  
- [x] D1 marked complete with #252 merge ref  
- [x] Feat PR — Composition Gate [#254](https://github.com/igortatarynovich/HostFlow/pull/254)

---

## History

- 2026-08-22: E4 brief — Candidate Document Link ([documents-platform-e4-candidate-document-link.md](documents-platform-e4-candidate-document-link.md)). D3 / D5–D7 / D9 stay unbound.
- 2026-08-22: E3 brief — first D2 `documents` consumer bind = HR employee ([documents-platform-e3-first-consumer-bind.md](documents-platform-e3-first-consumer-bind.md)). D3–D7 / D9 stay unbound.
- 2026-08-18: E2 brief — D2 `documents` catalog unlock is [E2](documents-platform-e2-public-contract.md) (feat locked). E1 stays not-enable. D3–D9 stay unbound.
- 2026-08-18: Phase E opened at E1 — D2 `documents` stays reserved; unlock is a later named E slice, not E1.
- 2026-08-15: D2 feat ✅ [#254](https://github.com/igortatarynovich/HostFlow/pull/254) (`42bd51b7` / merge `a61543cf`). Product Track → Entity Workspace D3 consumer cutover brief (feat locked).
- 2026-08-15: D2 feat — named **Entity Workspace D2 Composition Gate**; slot allowlist frozen; `documents` reserved; no Passport; no cutover UI. Next = D3 cutover brief (locked).
- 2026-08-14: D1 ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252) (`3375adf1` / merge `f0572257`). Product Track → Entity Workspace D2 composition contract (this brief). Feat locked.
