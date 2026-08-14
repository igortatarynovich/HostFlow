# Entity Workspace D1 — Contract Seal (Phase D)

**Status:** **IN PROGRESS** (docs — this brief)  
**Branch (docs):** `docs/entity-workspace-phase-d-contract-seal`  
**Branch (code):** `feat/entity-workspace-d1-contract-seal` (after this brief merges)  
**Parents:** [Forms Platform C6 Optimization](forms-platform-c6-optimization.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase D](../architecture/platform-completion-roadmap.md) · [ADR-010 Unified Resource List Shell](../architecture/ADR-010-unified-resource-list-shell.md) · [A2 gate A2-F7](../gates/platform-governance-review-a2.md) · [UI constitution §3.3](../architecture/ui-constitution-v1.md)

> Phase C Forms **Foundation** closed via C6 ([#250](https://github.com/igortatarynovich/HostFlow/pull/250)).  
> Phase D starts here: seal what **Universal Entity Workspace** owns — before any composition runtime.  
> D1 does **not** mint a Catalog Passport, does **not** invent a fifth shell, and does **not** open Documents Phase E.

**Naming (do not collapse):** this **Entity Workspace D1** is not PX **minimal EntityWorkspace chrome** (Baseline v1 header / actions / rail). It is not Recruitment / HR / Vacancy / Candidate Workspace. It is not Forms C6 / Communication C1 Inbox.

---

## Why this slice

[A2-F7](../gates/platform-governance-review-a2.md): Entity Workspace is **not yet a platform SoT**.  
Kit Gate shipped **chrome only** (`components/ui/EntityWorkspace` + passport adapter). That stops Stage 3 from inventing a fifth card shell — it does **not** compose Communication + Forms (+ later Documents) onto one entity.

Without a sealed Phase D contract, product work will either:

- treat PX chrome as “Universal Entity Workspace done”, or  
- grow another module-owned workspace beside the kit.

D1 seals ownership, boundary, and the Phase D ladder start. Runtime composition comes in later D slices.

---

## Ownership card (required before domain promotion)

| Field | Value |
|-------|--------|
| **Domain name** | Universal Entity Workspace (Phase D platform capability) |
| **Owner** | Platform UI / Workspace layer ([ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) · [UI constitution](../architecture/ui-constitution-v1.md)) |
| **Source of truth** | Kit public chrome (`components/ui/EntityWorkspace`) + **future** Phase D composition contract (slots / adapters). Module workspaces are **not** SoT |
| **Consumers** | Recruitment, Sales, HR, Fleet, Finance, Services — via kit compose + module adapters only |
| **Delivery contract** | Baseline v1 chrome today; Phase D composition contract sealed in later D slices before runtime cutover |
| **Versioning** | Kit Baseline (v1 now); composition contract versioned when introduced — no silent fork |
| **Override policy** | Modules **must not** ship a parallel entity shell / side-panel product when kit chrome exists |
| **Enforcement** | Kit Gate inventory + named D gates (feat); no Catalog Passport in D1 |

Catalog Passport / Manifest for Entity Workspace = **later D slice**. Minting a Catalog row is an Architecture checklist item (and RFC if it changes L0 Catalog shape). D1 does **not** rewrite the Catalog.

---

## Locked principle

```text
PX EntityWorkspace chrome (Baseline v1)
  → header / actions / summary / nav / content / rail
Phase D Universal Entity Workspace
  → compose platform surfaces onto one entity (Communication, Forms, …)
Module workspaces (Recruitment / HR / Candidate / …)
  → stay module-owned; never promoted into the kit
```

D1 **must not**:

- treat PX chrome as Phase D complete  
- invent a second public entity shell beside `components/ui/EntityWorkspace`  
- promote Recruitment / HR / Vacancy / Candidate Workspace into the platform kit  
- open Documents Phase E, Billing, or AI  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- mint Entity Catalog Passport / Manifest in this docs PR  

---

## Phase D ladder (locked start)

| Slice | Focus | Status |
|-------|--------|--------|
| **D1** | Contract seal (ownership / boundary / PX ≠ Phase D) | ← **active** (this brief; feat locked) |
| **D2** | Composition contract (platform slots on one entity) | locked until D1 feat |
| **D3+** | Consumer cutover / enforcement gates | locked |

Exact D2+ DoD stays deferred until D1 feat closes — same pattern as Forms C1 → C2.

---

## In scope (this docs PR)

1. This brief.  
2. Close **Forms Platform C6** as **COMPLETE** after [#250](https://github.com/igortatarynovich/HostFlow/pull/250) (`9933a835` / `e81e2a08`).  
3. Point Product Track / queue / roadmap / AGENTS / maturity here.  
4. Clarify roadmap Phase D vs PX chrome; Documents remain Phase E (slots may stay empty until then).

## In scope (feat PR — after this brief)

1. Named gate: Phase D ≠ PX-chrome-complete; no second shell import path for new product screens that need entity chrome.  
2. Architecture Review Checklist (10 questions) in the feat PR description.  
3. Pointers stay on D1 until D2 brief opens.  
4. **No** Catalog Passport mint unless checklist + (if needed) Architecture RFC explicitly allow it.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Composition runtime (threads / forms / docs on one entity) | D2+ |
| Catalog Passport / Manifest for Entity Workspace | Later D slice (+ RFC if Catalog shape) |
| Documents lifecycle platform | Phase E |
| Forms P3 / P4 / P5 | Locked |
| Stage 5 settings / R6 | Unchanged |
| Module workspace restyles | Module-owned — not Phase D |

Do **not** mix Documents Phase E, Billing, AI, or Forms product unlocks into D1.

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Platform UI / Workspace ([ADR-010](../architecture/ADR-010-unified-resource-list-shell.md)); not a product module |
| 2 Exists? | Chrome yes (`components/ui/EntityWorkspace`); Universal composition **no** — that is Phase D |
| 3 Adapter | Kit `EntityWorkspace` + existing `EntityWorkspaceShell` passport adapter; no second Adapter in D1 |
| 4 Boundary | No fifth shell; no module-workspace promotion; no Documents/Billing/AI; no Forms P3–P5 |
| 5 Settings | No new Manifest keys in D1 |
| 6 SoT | Chrome SoT = kit public API; Universal composition SoT = not yet (A2-F7) — sealed as Phase D goal, not invented here |
| 7 Events | None new |
| 8 Requires | Forms Foundation ✅ (C6) · Communication available for later slots · ADR-010 / UI constitution |
| 9 License | None new |
| 10 Public contract | Docs-only this PR; feat may add enforcement tests without DTO bump |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- Product Track = this brief; Forms C6 is closed (#250).  
- Operators / agents cannot treat PX chrome or module Candidate/HR shells as Phase D done.  
- Feat locked until this brief merges.  
- Forms P3 / P4 / P5 and Documents Phase E remain out of Product Track.

---

## DoD

- [x] Brief sealed with ownership card + in/out + acceptance  
- [x] Queue + roadmap + AGENTS + maturity point at this brief  
- [x] C6 marked **COMPLETE** in canon  
- [ ] Feat PR — boundary gates (after brief merge)

---

## History

- 2026-08-14: Forms C6 Optimization merged [#250](https://github.com/igortatarynovich/HostFlow/pull/250) (`e81e2a08` / merge `9933a835`). Forms Foundation ✅. Product Track → Entity Workspace D1 contract seal (this brief). Feat locked. Not PX-chrome-as-done / not Documents Phase E / not Forms P3–P5.
