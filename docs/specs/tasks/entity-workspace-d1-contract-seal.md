# Entity Workspace D1 — Contract Seal (Phase D)

**Status:** **COMPLETE** ([#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252) · `3375adf1` · merge `f0572257`)  
**Next:** [D2 Composition Contract](entity-workspace-d2-composition-contract.md) ← active (docs; feat locked)  
**Branch (docs):** `docs/entity-workspace-phase-d-contract-seal` ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251)  
**Branch (code):** `feat/entity-workspace-d1-contract-seal` ✅ [#252](https://github.com/igortatarynovich/HostFlow/pull/252)  
**Parents:** [Forms Platform C6 Optimization](forms-platform-c6-optimization.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase D](../architecture/platform-completion-roadmap.md) · [ADR-010 Unified Resource List Shell](../architecture/ADR-010-unified-resource-list-shell.md) · [A2 gate A2-F7](../gates/platform-governance-review-a2.md) · [UI constitution §3.3](../architecture/ui-constitution-v1.md)

> Phase C Forms **Foundation** closed via C6 ([#250](https://github.com/igortatarynovich/HostFlow/pull/250)).  
> D1 seals what **Universal Entity Workspace** owns — before composition runtime.  
> D1 does **not** mint a Catalog Passport, does **not** invent a fifth shell, and does **not** open Documents Phase E.

**Naming (do not collapse):** this **Entity Workspace D1** is not PX **minimal EntityWorkspace chrome** (header / actions / rail). It is not Recruitment / HR / Vacancy / Candidate Workspace. It is not Forms C6 / Communication C1 Inbox.

---

## Why this slice

[A2-F7](../gates/platform-governance-review-a2.md): Entity Workspace is **not yet a platform SoT**.  
On tip: `platform/entity-workspace` **EntityWorkspaceShell** (passport adapter) exists. Public chrome **SoT path** is `components/ui/EntityWorkspace` (kit file may land with Kit Baseline sync — absence must not be read as Phase D done). Adapter + reserved chrome path stop a fifth shell — they do **not** compose Communication + Forms (+ later Documents) onto one entity.

Without a sealed Phase D contract, product work will either:

- treat adapter Shell / future chrome as “Universal Entity Workspace done”, or  
- grow another module-owned workspace beside the kit.

D1 seals ownership, boundary, and the Phase D ladder start. Runtime composition comes in later D slices.

---

## Ownership card (required before domain promotion)

| Field | Value |
|-------|--------|
| **Domain name** | Universal Entity Workspace (Phase D platform capability) |
| **Owner** | Platform UI / Workspace layer ([ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) · [UI constitution](../architecture/ui-constitution-v1.md)) |
| **Source of truth** | Kit public chrome path (`components/ui/EntityWorkspace`) + **future** Phase D composition contract. Module workspaces are **not** SoT. Shell = passport adapter only |
| **Consumers** | Recruitment, Sales, HR, Fleet, Finance, Services — via kit compose + module adapters only |
| **Delivery contract** | Chrome SoT path reserved; Shell adapter on tip; Phase D composition contract sealed in later D slices before runtime cutover |
| **Versioning** | Kit Baseline when chrome lands; composition contract versioned when introduced — no silent fork |
| **Override policy** | Modules **must not** ship a parallel entity shell / side-panel product when kit chrome exists |
| **Enforcement** | Named **Entity Workspace D1 Contract Seal Gate**; no Catalog Passport in D1 |

Catalog Passport / Manifest for Entity Workspace = **later D slice**. Minting a Catalog row is an Architecture checklist item (and RFC if it changes L0 Catalog shape). D1 does **not** rewrite the Catalog.

---

## Locked principle

```text
PX / kit EntityWorkspace chrome (SoT path: components/ui/EntityWorkspace)
  → header / actions / summary / nav / content / rail
EntityWorkspaceShell (platform/entity-workspace)
  → passport adapter onto kit chrome — not a second public shell
Phase D Universal Entity Workspace
  → compose platform surfaces onto one entity (Communication, Forms, …)
Module workspaces (Recruitment / HR / Candidate / …)
  → stay module-owned; never promoted into the kit
```

D1 **must not**:

- treat Shell adapter or chrome-as-file as Phase D Universal complete  
- invent a second public entity shell beside `components/ui/EntityWorkspace`  
- promote Recruitment / HR / Vacancy / Candidate Workspace into the platform kit  
- open Documents Phase E, Billing, or AI  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- mint Entity Catalog Passport / Manifest  

---

## Phase D ladder (locked start)

| Slice | Focus | Status |
|-------|--------|--------|
| **D1** | Contract seal (ownership / boundary / PX ≠ Phase D) | ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252) |
| **D2** | Composition contract (platform slots on one entity) | ← active ([brief](entity-workspace-d2-composition-contract.md)) |
| **D3+** | Consumer cutover / enforcement gates | locked |

---

## Entity Workspace D1 Contract Seal Gate (CI — mandatory)

Named step: **Entity Workspace D1 Contract Seal Gate**  
(`tests/platform/test_entity_workspace_d1_contract_seal.py`). Full-repo pytest red does not waive it.

- Ownership / PX ≠ Universal locked in brief  
- Entity Foundation maturity stays 🔄 (not ✅)  
- `EntityWorkspaceShell` adapter exists under `platform/entity-workspace`  
- Public chrome SoT path = `components/ui/EntityWorkspace`; Shell not re-exported from kit barrel  
- Kit barrel excludes module workspaces  
- No Entity Catalog Passport mint  

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Composition runtime (threads / forms / docs on one entity) | D2+ |
| Catalog Passport / Manifest for Entity Workspace | Later D slice (+ RFC if Catalog shape) |
| Kit Baseline chrome file land (if missing on tip) | Engineering / Kit sync — not Universal composition |
| Documents lifecycle platform | Phase E |
| Forms P3 / P4 / P5 | Locked |
| Stage 5 settings / R6 | Unchanged |
| Module workspace restyles | Module-owned — not Phase D |

Do **not** mix Documents Phase E, Billing, AI, or Forms product unlocks into D1.

---

## Architecture Review (L0 — this feat)

| # | Answer |
|---|--------|
| 1 Owner | Platform UI / Workspace ([ADR-010](../architecture/ADR-010-unified-resource-list-shell.md)); not a product module |
| 2 Exists? | Shell adapter yes; public chrome SoT path reserved; Universal composition **no** |
| 3 Adapter | `EntityWorkspaceShell` passport adapter; no second Adapter |
| 4 Boundary | No fifth shell; no module-workspace promotion; no Documents/Billing/AI; no Forms P3–P5 |
| 5 Settings | No new Manifest keys |
| 6 SoT | Chrome path = kit public API; Universal composition SoT = not yet (A2-F7) |
| 7 Events | None new |
| 8 Requires | Forms Foundation ✅ (C6) · ADR-010 / UI constitution |
| 9 License | None new |
| 10 Public contract | Additive enforcement gate only; no DTO bump; no Catalog Passport |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- [x] Brief merged ([#251](https://github.com/igortatarynovich/HostFlow/pull/251))  
- [x] Named Entity Workspace D1 Contract Seal Gate  
- [x] Forms C6 remains closed; P3–P5 / Documents Phase E stay out  
- [x] No Catalog Passport mint  
- [x] Entity Foundation maturity remains 🔄  

---

## DoD

- [x] Brief sealed with ownership card + in/out + acceptance  
- [x] Queue + roadmap + AGENTS + maturity point at this brief  
- [x] C6 marked **COMPLETE** in canon  
- [x] Feat PR — boundary gates  

---

## History

- 2026-08-14: Forms C6 Optimization merged [#250](https://github.com/igortatarynovich/HostFlow/pull/250) (`e81e2a08` / merge `9933a835`). Forms Foundation ✅. Product Track → Entity Workspace D1 contract seal (brief). Feat locked.
- 2026-08-14: D1 brief merged [#251](https://github.com/igortatarynovich/HostFlow/pull/251) (`658c63b0`). Feat: named Contract Seal Gate; ownership / Shell-adapter / SoT-path / no Passport.
- 2026-08-14: D1 feat merged [#252](https://github.com/igortatarynovich/HostFlow/pull/252) (`3375adf1` / merge `f0572257`). Product Track → [D2 Composition Contract](entity-workspace-d2-composition-contract.md).
