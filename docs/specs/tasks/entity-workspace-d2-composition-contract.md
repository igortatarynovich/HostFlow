# Entity Workspace D2 — Composition Contract (Phase D)

**Status:** **IN PROGRESS** (docs — this brief)  
**Branch (docs):** `docs/entity-workspace-d2-composition-contract`  
**Branch (code):** `feat/entity-workspace-d2-composition-contract` (after this brief merges)  
**Parents:** [D1 Contract Seal](entity-workspace-d1-contract-seal.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase D](../architecture/platform-completion-roadmap.md) · [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) · [A2-F7](../gates/platform-governance-review-a2.md) · [UI constitution §3.3](../architecture/ui-constitution-v1.md) · [Forms Public Contract](../architecture/forms-public-contract.md) · [Communication foundation](../architecture/communication-platform-foundation.md)

> D1 sealed ownership and Shell ≠ Universal.  
> D2 seals **which platform surfaces** may compose onto one entity — the composition contract — before any consumer cutover.  
> D2 does **not** ship Universal runtime UI, mint Catalog Passport, or open Documents Phase E.

**Naming (do not collapse):** this **Entity Workspace D2** is not D1 contract seal, not PX chrome land, not Communication C1 Inbox, not Forms C3–C6, not Documents Phase E.

---

## Why this slice

D1 locked: owner, chrome SoT path, Shell adapter, no module-workspace promotion, Entity Foundation 🔄.  
The remaining hole: product screens will invent ad-hoc “slots” (thread panel here, form embed there, docs drawer elsewhere) without a shared composition contract — recreating temporary side panels that Phase D forbids.

D2 names the **slot set** and **compose rules**. Runtime cutover is D3+.

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
  │     └── documents (reserved — empty until Phase E)
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
| `documents` | platform (reserved) | Documents (Phase E) | **Empty / unavailable** until Phase E unlocks |
| `context-rail` | chrome | Kit / Shell adapter | Already D1 chrome; not a new platform SoT |

**Rules:**

1. New slot kinds require amending this contract (and Architecture Review) — no silent product slots.  
2. Platform slots consume **public contracts / adapters** only — no cross-module internal imports (Architecture Rule 2).  
3. `documents` may appear in the catalog as reserved; enabling it in product UI before Phase E is **forbidden**.  
4. Timeline stays a **content slot**, not a separate Activity Workspace product.

---

## Locked principle

```text
D1  → who owns Entity Workspace + chrome/adapter boundary
D2  → which slots exist and how platforms compose (this)
D3+ → consumer cutover / enforcement on real screens
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
| **D2** | Composition contract (slots) | ← **active** (this brief; feat locked) |
| **D3+** | Consumer cutover / enforcement | locked until D2 feat |

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
4. Pointers stay on D2 until D3 brief opens.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Consumer cutover (Sales Inquiry / Candidate / …) | D3+ |
| Catalog Passport / Manifest | Later D slice (+ RFC if Catalog shape) |
| Kit Baseline chrome file land | Engineering / Kit sync |
| Documents lifecycle | Phase E |
| Forms P3 / P4 / P5 | Locked |
| Stage 5 settings / R6 | Unchanged |

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Platform UI / Workspace (ADR-010); platform slots owned by their platforms |
| 2 Exists? | Chrome/Shell (D1); composition slot catalog **new** (this); Universal runtime **no** |
| 3 Adapter | Shell adapter unchanged; Communication / Forms via their public adapters only |
| 4 Boundary | No cutover UI; no Passport; no Documents enable; no Forms P3–P5; no fifth shell |
| 5 Settings | No new Manifest keys in D2 docs |
| 6 SoT | Slot catalog = this brief until feat freezes ids; module overview body stays module-owned |
| 7 Events | None new |
| 8 Requires | D1 ✅ · Forms Foundation ✅ · Communication foundation available for later compose |
| 9 License | None new |
| 10 Public contract | Docs-only this PR; feat may freeze slot-id allowlist without Catalog Passport |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- Product Track = this brief; D1 is closed (#251 / #252).  
- Operators cannot treat Shell/chrome as Universal complete or enable Documents slot early.  
- Feat locked until this brief merges.  
- Forms P3–P5 and Documents Phase E remain out of Product Track.

---

## DoD

- [x] Brief sealed with slot catalog + in/out + acceptance  
- [x] Queue + roadmap + AGENTS point at this brief  
- [x] D1 marked complete with #252 merge ref  
- [ ] Feat PR — Composition Gate (after brief merge)

---

## History

- 2026-08-14: D1 ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252) (`3375adf1` / merge `f0572257`). Product Track → Entity Workspace D2 composition contract (this brief). Feat locked.
