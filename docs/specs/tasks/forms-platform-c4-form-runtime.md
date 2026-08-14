# Forms Platform C4 — Form Runtime

**Status:** **COMPLETE** ([#245](https://github.com/igortatarynovich/HostFlow/pull/245)/[#246](https://github.com/igortatarynovich/HostFlow/pull/246) · `4427b110`)  
**Next:** [C5 Form Execution](forms-platform-c5-form-execution.md)  
**Branch (docs):** `docs/forms-platform-c4-form-runtime` ✅ [#245](https://github.com/igortatarynovich/HostFlow/pull/245)  
**Branch (code):** `feat/forms-platform-c4-form-runtime` ✅ [#246](https://github.com/igortatarynovich/HostFlow/pull/246)  
**Parents:** [C3 Builder Runtime](forms-platform-c3-builder-runtime.md) ✅ · [C2 runtime contract](forms-platform-c2-runtime-contract.md) · [C1 contract seal](forms-platform-c1-contract-seal.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase C](../architecture/platform-completion-roadmap.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [Forms Public Contract](../architecture/forms-public-contract.md)

> C4 is **Runtime, not an Engine**.  
> It does not know how the form was authored.  
> Sole input: frozen `FormPublicationVersion` (Adapter `resolve` DTO).  
> Sole output: **Runtime Model**.

**Naming (do not collapse):** this **Forms Platform C4** is not Communication Epic C4 (there is none — Communication **C2.4** stays frozen). It is not historical **P3 Publish UI**. It is not **P4 Themes**. It is not Phase C **C5 Form Execution** (submit). Historical `backend/tests/forms_platform/test_forms_platform_c4.py` is Sprint-era HTTP resolve — **not** this slice’s named gate.

---

## Four independent layers (locked)

After C4, Forms splits into four layers that must not collapse:

```text
C3  Authoring     FormDefinition ↔ Draft
C2  Publication   freeze + Contract Identity  (Adapter publish)
C4  Runtime       FormPublicationVersion → Runtime Model
C5  Execution     Runtime Model → Validation → Submission → Persistence
```

Mixing editor, publication, runtime, and execution in one package is forbidden.

---

## Why this slice

C1 sealed ids. C2 froze Contract Identity on every publication version. C3 bound Builder to `FormDefinition ↔ Draft` only ([#243](https://github.com/igortatarynovich/HostFlow/pull/243)/[#244](https://github.com/igortatarynovich/HostFlow/pull/244) · `638955d5`). Brief [#245](https://github.com/igortatarynovich/HostFlow/pull/245).

The remaining hole: serving a live form can still reach back into the editor, or grow a second Forms engine (lookup, schema rewrite, identity mint). If Runtime imported Builder, read a Dirty Draft, searched Manifest, or minted identity on a keystroke, C2’s freeze and C3’s boundary would collapse.

C4 closes that gap **without** teaching Runtime about drafts, and **without** opening Publish UI, Themes, or submit.

**Platform posture:** Forms remains a **platform capability**, not a product module.

---

## Locked principle — Runtime, not Engine

Runtime works only with the **frozen** model, then projects it:

```text
FormPublicationVersion  →  Runtime Model
```

Runtime **does not know** Draft, FormDefinition, Builder Session, Builder State, or Canvas. Those stay in C3.

Runtime **must not**:

- import Builder (`forms_platform.builder` / FormDefinition session)
- read or write Draft / `FormDefinition`
- call `save_session` / draft persist
- publish or call Adapter `publish` / `commit_publish`
- look up a publication (no Adapter import, no ledger, no Manifest scan)
- write Contract Identity or `schema_hash` (already frozen at C2 publish)
- accept submissions (C5)
- invent field types
- open P3 Publish UI or P4 Themes

Publish stays a **separate operation** on the C2 Adapter. Submit stays C5. Builder stays C3.

---

## Dual of C3

| Slice | Owns | Must not touch |
|-------|------|----------------|
| **C3 Builder Runtime** | `FormDefinition` ↔ Draft (mutable) | Publication version, identity, Adapter, **Runtime** |
| **C4 Form Runtime** | Frozen `FormPublicationVersion` → **Runtime Model** | FormDefinition, Draft, Builder session, lookup, publish, submit |

Dirty Draft and Saved Draft remain mutable **inside Builder**. They are not runtime inputs.

---

## Sole input

Runtime accepts **only**:

```text
FormPublicationVersion   (Adapter resolve DTO)
```

Not:

- Draft
- FormDefinition
- Builder Session
- Builder State
- Canvas

---

## Sole source — Adapter resolve (Runtime does not search)

```text
Resolve  →  Adapter  →  FormPublicationVersion  →  Runtime  →  Runtime Model
```

Forbidden:

```text
Builder   →  Runtime
Manifest  →  Runtime
Runtime   →  find publication
```

Callers compose: Adapter `resolve`, then `serve(publication)`. Runtime has no DB session and no second resolve engine.

---

## What Runtime does

Narrow:

1. Receive a frozen publication (Adapter resolve DTO).
2. Build **Runtime Model**.
3. Return it.

It does **not** save, publish, accept submission, recompute schema, or change identity.

Public operations are **read-only**. Caching, if added later, must not change the contract: Runtime mutates nothing.

---

## Runtime Model

Runtime never hands `FormPublicationVersion` to downstream work.

It first builds **Runtime Model** (`forms.runtime.model.v1`). Render, validation, and execution consume **that** model — not the publication ledger row.

This lets C5 (and later rendering) evolve without touching Publication.

| Model | Runtime |
|-------|---------|
| Adapter `resolve` DTO / `FormPublicationVersion` | **input only** (read; copy into Runtime Model) |
| **Runtime Model** | **output** — the only object downstream may use |
| `FormDefinition` / Draft / Builder session | forbidden |
| Adapter `publish` | forbidden |
| Submission / `validate_submission` | C5 — not this slice |

A publication without a complete Contract Identity **must not** be served (C2 fail-closed). Serving a draft as if it were published is forbidden.

Storage may remain `TenantLeadForm` pointer + `form_publication_versions`. C4 names the **serving model**, not a FormTemplate cutover.

---

## Dual Builder ↔ Runtime boundary

Named gate on **both** directions:

```text
Builder  ↛  Runtime
Runtime  ↛  Builder
```

The only legal chain:

```text
Builder  →  Publish (C2 Adapter)  →  FormPublicationVersion  →  Runtime
```

Nothing flows back.

C3 gate forbids importing `forms_platform.runtime`. C4 gate forbids importing `forms_platform.builder`.

---

## Where C4 ends and C5 begins

```text
C4  Resolve → Runtime Model → (representation for render)
        │
        │  Runtime stops here. It does not know Submission.
        ▼
C5  Runtime Model → Validation → Submission → Persistence
```

---

## Forbidden flow

```text
Runtime → read Draft / FormDefinition     ← forbidden (binds serving to editor)
Runtime → save draft                      ← forbidden
Runtime → publish                         ← forbidden (P3 / Adapter mutation)
Runtime → submit                          ← forbidden here (C5)
Runtime → search / second resolve engine  ← forbidden
```

## Required flow

```text
Builder (C3)
  → Save Draft
Publish (C2 Adapter)                      ← outside Builder and outside C4
  → new FormPublicationVersion
  → Freeze + Contract Identity
Adapter resolve
  → FormPublicationVersion
Form Runtime (C4)
  → Runtime Model
        │
        │  (Runtime stops here)
        ▼
Form Execution (C5)                       ← submit against that Runtime Model
```

---

## Form Runtime Gate (CI — mandatory)

Named step **Forms Platform C4 Form Runtime Gate**. Full-repo pytest red does not waive it. Historical `test_forms_platform_c4.py` is **not** this gate.

Runtime package (`backend/app/forms_platform/runtime/`):

- does **not** import Builder / Adapter / publication ledger / Manifest / submission
- `serve(publication)` is the only public entry — publication DTO in, Runtime Model out
- does **not** take `db` / `form_id` / `public_slug` (no lookup)
- does **not** call `save_session` / `publish` / `commit_publish` / `persist_submission`
- fail-closed when Contract Identity is missing, schema is missing, hash mismatches, or the payload is a draft
- does **not** re-mint identity (`freeze_contract_identity` is forbidden in Runtime)
- public API is read-only (`RuntimeModel` frozen)
- Builder package does **not** import Runtime

---

## What already exists (do not rebuild)

| Piece | Status | C4 use |
|-------|--------|--------|
| Adapter `resolve` / `resolve_publication` | Stable | **Sole producer** of the publication DTO — do not fork |
| C2 Contract Identity on publication versions | ✅ [#242](https://github.com/igortatarynovich/HostFlow/pull/242) | Required on every served version |
| C3 Builder Runtime | ✅ [#244](https://github.com/igortatarynovich/HostFlow/pull/244) | **Outside Runtime** — do not import |
| Sprint HTTP `test_forms_platform_c4.py` | Historical | Name collision only — not Phase C C4 |
| Public intake submit path | Shipped | **C5** — do not pull into C4 |

---

## Feat implementation order (mandatory)

1. Adapter resolve remains the only way to obtain `FormPublicationVersion`.  
2. Receive that publication (no lookup inside Runtime).  
3. Build **Runtime Model**.  
4. Read-only Runtime API (`serve`).  
5. Named Form Runtime Gate.  
6. Forbid Builder / Publish / Submission imports (and Builder ↛ Runtime).  

Do **not** add Publish UI, Themes, submit/Execution, or a second resolve HTTP.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Publish UI / calling Adapter `publish` from canvas | P3 — locked |
| Themes | P4 — locked |
| Form Execution / submit | C5 — after C4 feat PASS |
| C6 Optimization | After C5 |
| Autosave / collab UX | Consume C3 state machine later |
| Stage 5 settings / R6 / FormTemplate / ADR-022 | Unchanged |
| Entity Workspace Phase D | Unchanged |

Do **not** mix Themes, Publish UI, Builder, submit, Stage 5, or R6 into C4.

---

## Phase C ladder (locked)

| Slice | Focus | Status |
|-------|--------|--------|
| **C1** | Contract seal | ✅ [#239](https://github.com/igortatarynovich/HostFlow/pull/239) / [#240](https://github.com/igortatarynovich/HostFlow/pull/240) |
| **C2** | Runtime contract + gates | ✅ [#241](https://github.com/igortatarynovich/HostFlow/pull/241) / [#242](https://github.com/igortatarynovich/HostFlow/pull/242) |
| **C3** | Builder Runtime | ✅ [#243](https://github.com/igortatarynovich/HostFlow/pull/243) / [#244](https://github.com/igortatarynovich/HostFlow/pull/244) · `638955d5` |
| **C4** | Form Runtime (this) | ✅ [#245](https://github.com/igortatarynovich/HostFlow/pull/245) / [#246](https://github.com/igortatarynovich/HostFlow/pull/246) · `4427b110` |
| **C5** | Form Execution | [brief](forms-platform-c5-form-execution.md) ← next |
| **C6** | Optimization | After C5 |

---

## Architecture Review (L0 — this feat)

| # | Answer |
|---|--------|
| 1 Owner | Forms **platform** (ADR-007) |
| 2 Exists? | Yes — Adapter `resolve` + C2 identity; C4 names Form Runtime + Runtime Model over that DTO |
| 3 Adapter | Runtime **consumes** resolve DTO. It does not import Adapter or add an op |
| 4 Boundary | No Builder import; no draft; no publish; no submit; no lookup; no Themes. Builder ↛ Runtime |
| 5 Settings | No new Manifest keys |
| 6 SoT | Frozen `FormPublicationVersion` (C2) is input; **Runtime Model** is the serving SoT for downstream. Builder SoT stays C3 |
| 7 Events | Unchanged Experimental |
| 8 Requires | C2 identity + C3 Builder isolation |
| 9 License | None new |
| 10 Public contract | Additive naming of Form Runtime / Runtime Model. No Adapter DTO bump |

Does **not** amend L0 P-rules.

---

## Acceptance

- [x] Brief merged (docs PR [#245](https://github.com/igortatarynovich/HostFlow/pull/245))  
- [x] C3 marked **COMPLETE** in canon (#244 / `638955d5`)  
- [x] Named Form Runtime Gate green  
- [x] Runtime does not import Builder; Builder does not import Runtime  
- [x] `serve(publication)` only; read-only Runtime Model  
- [x] P3 Publish UI / P4 Themes / P5 Analytics / C5 remain locked until C5 brief  
- [x] Historical Sprint C4 HTTP tests not renamed as this gate  

**CI criterion:** named **Forms Platform C4 Form Runtime Gate**. Full-repo `Tests with coverage` is Engineering Track debt and does not block C4.

---

## DoD (this feat PR)

- [x] Runtime Model sealed  
- [x] Package `forms_platform/runtime/` + named gate  
- [x] Dual import boundary  
- [x] Publish UI, Themes, C5 Execution **not** started in this PR  

Package: `backend/app/forms_platform/runtime/` (`model.py`, `serve.py`). Gate: `backend/tests/forms_platform/test_forms_c4_form_runtime_gate.py`.

---

## History

- 2026-08-14: C3 Builder Runtime merged [#244](https://github.com/igortatarynovich/HostFlow/pull/244) (`638955d5`, PASS-ready `2e5f9720`). C4 Form Runtime brief opened (docs). Feat locked until this brief merges. Not P3 Publish UI / P4 Themes / C5 Execution / Sprint HTTP C4.
- 2026-08-14: Brief merged [#245](https://github.com/igortatarynovich/HostFlow/pull/245) (`16e0dfb6`). Feat locks **Runtime Model**: Runtime is not an Engine; Adapter resolve is the sole source; read-only `serve(publication)`; dual Builder boundary; C5 starts after Runtime Model.
- 2026-08-14: C4 feat merged [#246](https://github.com/igortatarynovich/HostFlow/pull/246) (`4427b110`; PASS-ready `626e5a9d`). Named C4 gate SUCCESS. Next = [C5 Form Execution](forms-platform-c5-form-execution.md).
