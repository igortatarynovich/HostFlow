# Forms Platform C6 — Optimization

**Status:** **IN PROGRESS** (docs — brief seal; feat locked until this brief merges)  
**Branch (docs):** `docs/forms-platform-c6-optimization`  
**Parents:** [C5 Form Execution](forms-platform-c5-form-execution.md) ✅ · [C4 Form Runtime](forms-platform-c4-form-runtime.md) ✅ · [C3 Builder Runtime](forms-platform-c3-builder-runtime.md) · [C2 runtime contract](forms-platform-c2-runtime-contract.md) · [C1 contract seal](forms-platform-c1-contract-seal.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase C](../architecture/platform-completion-roadmap.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [Forms Public Contract](../architecture/forms-public-contract.md) · [Platform Capability Maturity](../architecture/platform-capability-maturity.md)

> C6 **closes Forms Foundation**.  
> Optimization = production HostFlow Form submit must run  
> `resolve → serve (C4) → execute (C5)` on the Shared Intake write path — no parallel validate/persist bypass.  
> C6 does **not** open Publish UI, Themes, Analytics, or a second submit engine.

**Naming (do not collapse):** this **Forms Platform C6** is not Acquisition Stage 5 Optimization. It is not Communication Context C6. It is not historical **P3 Publish UI** / **P4 Themes** / **P5 Analytics**. It is the last Phase C ladder slice before Entity Workspace (Phase D).

---

## Why this slice

C1 sealed ids. C2 froze Contract Identity. C3 bound Builder to Draft. C4 projected publications into **Runtime Model**. C5 named Execution and bound validate/pin/persist to that model ([#247](https://github.com/igortatarynovich/HostFlow/pull/247)/[#248](https://github.com/igortatarynovich/HostFlow/pull/248) · `f6bbe03f` · PASS-ready `c24bdc18`).

The remaining hole: production Shared Intake can still accept a HostFlow Form submission **without** composing Adapter `resolve` → C4 `serve` → C5 `execute`. If public submit validates a draft, a raw ledger row, or a soft `pre_schema` path, C4/C5 boundaries stay documentation-only.

C6 closes that gap **without** opening Publish UI, Themes, Analytics, FormTemplate SoT cutover, or ADR-022 acceptance.

**Platform posture:** Forms remains a **platform capability**, not a product module.  
**Maturity:** Forms **Foundation** may mark ✅ only when this slice’s feat closes ([maturity matrix](../architecture/platform-capability-maturity.md)).

---

## Locked principle

Production HostFlow Form submit uses the frozen chain only:

```text
Adapter resolve
  → FormPublicationVersion
C4 serve
  → Runtime Model
C5 execute
  → Validation → Submission pin → Persistence
Shared Intake
  → /api/v1/public/intake  (unchanged HTTP)
```

Optimization **must not**:

- invent a second public Forms submit HTTP / engine
- import Builder / read Draft / `FormDefinition` on the write path
- publish or call Adapter `publish` / `commit_publish`
- re-mint Contract Identity (`freeze_contract_identity` on submit)
- validate against live draft or presentation-as-SoT
- open P3 Publish UI, P4 Themes, or P5 Analytics
- replace `TenantLeadForm` bridge with FormTemplate SoT (later)
- accept ADR-022 as this slice’s goal

Builder stays C3. Publish stays C2 Adapter. Serve stays C4. Execute stays C5. C6 **wires** them on the production intake path and **gates** the bypass.

---

## Dual of C5

| Slice | Owns | Must not touch |
|-------|------|----------------|
| **C5 Form Execution** | Runtime Model → validate → pin → persist (package + named gate) | Builder, publish, identity mint, second HTTP |
| **C6 Optimization** | Production binding of that chain on Shared Intake + Foundation close | Builder, Publish UI, Themes, Analytics, FormTemplate SoT, ADR-022 |

C5 delivered the Execution contract. C6 makes it the **only** HostFlow Form write path.

---

## Forbidden flow

```text
Public intake → validate draft / FormDefinition     ← forbidden
Public intake → validate ledger row only (skip serve) ← forbidden
Public intake → soft pre_schema accept for published HostFlow Form ← forbidden
C6 → second /forms/submit HTTP                      ← forbidden
C6 → Publish UI / Themes / Analytics                ← forbidden
```

## Required flow

```text
Builder (C3) → Draft
Publish (C2 Adapter) → FormPublicationVersion + identity
Public Shared Intake (existing HTTP)
  → resolve publication
  → C4 serve → Runtime Model
  → C5 execute → validate / pin / persist_submission_envelope
  → destination dispatch (unchanged)
```

---

## Form Optimization Gate (CI — mandatory on the later feat)

Named step: **Forms Platform C6 Optimization Gate**. Full-repo pytest red does not waive it.

- HostFlow Form public submit path composes `serve` → Execution (or equivalent fail-closed)
- no Builder import on that path
- no `freeze_contract_identity` on submit
- no second Forms submit engine / public HTTP
- Forms Foundation maturity ready to mark ✅ when gate is green

This docs PR does **not** add that gate. The feat PR does.

---

## What already exists (do not rebuild)

| Piece | Status | C6 use |
|-------|--------|--------|
| C4 Runtime Model + `serve` | ✅ [#246](https://github.com/igortatarynovich/HostFlow/pull/246) | Required input |
| C5 Execution (`forms_platform/execution/`) | ✅ [#248](https://github.com/igortatarynovich/HostFlow/pull/248) | Required execute surface |
| Shared Intake `POST /api/v1/public/intake` | Shipped | **Keep** — wire, do not fork |
| `persist_submission_envelope` | Shipped | Persist |
| C1–C3 | ✅ | Outside Optimization write path |

---

## Feat implementation order (mandatory — after this brief merges)

1. Wire HostFlow Form Shared Intake submit through `resolve → serve → execute`.  
2. Fail-closed when a published HostFlow Form would skip Runtime Model / Execution.  
3. **Then** named Forms Platform C6 Optimization Gate.  
4. Mark Forms **Foundation** ✅ in the maturity matrix.  
5. Do **not** open Publish UI, Themes, Analytics, FormTemplate SoT, or ADR-022.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| C6 **feat** (wiring + named gate + Foundation ✅) | After this brief merges |
| Publish UI | P3 — locked |
| Themes | P4 — locked |
| Analytics | P5 — locked |
| FormTemplate SoT / `TenantLeadForm` bridge removal | Later |
| Accept ADR-022 | Later |
| Entity Workspace Phase D | After Phase C |
| Stage 5 settings / R6 | Unchanged |

Do **not** mix Themes, Publish UI, Builder product, Analytics, Stage 5, or R6 into C6.

---

## Phase C ladder (locked)

| Slice | Focus | Status |
|-------|--------|--------|
| **C1** | Contract seal | ✅ [#239](https://github.com/igortatarynovich/HostFlow/pull/239) / [#240](https://github.com/igortatarynovich/HostFlow/pull/240) |
| **C2** | Runtime contract + gates | ✅ [#241](https://github.com/igortatarynovich/HostFlow/pull/241) / [#242](https://github.com/igortatarynovich/HostFlow/pull/242) |
| **C3** | Builder Runtime | ✅ [#243](https://github.com/igortatarynovich/HostFlow/pull/243) / [#244](https://github.com/igortatarynovich/HostFlow/pull/244) |
| **C4** | Form Runtime | ✅ [#245](https://github.com/igortatarynovich/HostFlow/pull/245) / [#246](https://github.com/igortatarynovich/HostFlow/pull/246) · `4427b110` |
| **C5** | Form Execution | ✅ [#247](https://github.com/igortatarynovich/HostFlow/pull/247) / [#248](https://github.com/igortatarynovich/HostFlow/pull/248) · `f6bbe03f` · PASS-ready `c24bdc18` |
| **C6** | Optimization (this) | **active** (brief; feat locked) |

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Forms **platform** (ADR-007) |
| 2 Exists? | Yes — C4 serve + C5 Execution + Shared Intake; C6 wires them |
| 3 Adapter | Consume resolve / existing submission surface. No second Adapter |
| 4 Boundary | No Builder; no publish UI; no Themes / Analytics; no second submit HTTP |
| 5 Settings | No new Manifest keys |
| 6 SoT | Runtime Model remains validation SoT; Shared Intake remains write HTTP |
| 7 Events | Unchanged Experimental this docs PR |
| 8 Requires | C5 Execution + C4 Runtime Model |
| 9 License | None new |
| 10 Public contract | Additive production binding. No Adapter DTO bump in this docs PR |

Does **not** amend L0 P-rules.

---

## Acceptance

- [ ] This brief merged (docs PR)  
- [ ] C5 marked **COMPLETE** in canon (#248 / `f6bbe03f` · PASS-ready `c24bdc18`)  
- [ ] Product Track points here; C6 feat not opened in this PR  
- [ ] P3 Publish UI / P4 Themes / P5 Analytics remain locked  
- [ ] No second Forms submit engine named as this slice  
- [ ] Forms Foundation ✅ deferred until C6 feat (not this docs PR)

Feat DoD (later PR, not this one): named Forms Platform C6 Optimization Gate green; production HostFlow Form submit uses serve→execute; Foundation maturity ✅.

**CI criterion for the later feat:** named **Forms Platform C6 Optimization Gate**. Full-repo `Tests with coverage` is Engineering Track debt and does not block C6.

---

## DoD (this docs PR)

- [ ] Brief sealed; inbound refs from queue / roadmap / AGENTS / ADR-007 / Public Contract / maturity  
- [ ] C5 closed COMPLETE  
- [ ] C6 feat, Publish UI, Themes, Analytics **not** started  

---

## History

- 2026-08-14: C5 Form Execution merged [#248](https://github.com/igortatarynovich/HostFlow/pull/248) (`f6bbe03f`, PASS-ready `c24bdc18`). C6 Optimization brief opened (docs). Feat locked until this brief merges. Not P3 Publish UI / P4 Themes / P5 Analytics / second Forms submit engine / Acquisition Stage 5.
