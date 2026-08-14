# Forms Platform C5 — Form Execution

**Status:** **IN PROGRESS** (docs — brief seal; feat locked until this brief merges)  
**Branch (docs):** `docs/forms-platform-c5-form-execution`  
**Parents:** [C4 Form Runtime](forms-platform-c4-form-runtime.md) ✅ · [C3 Builder Runtime](forms-platform-c3-builder-runtime.md) · [C2 runtime contract](forms-platform-c2-runtime-contract.md) · [C1 contract seal](forms-platform-c1-contract-seal.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase C](../architecture/platform-completion-roadmap.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [Forms Public Contract](../architecture/forms-public-contract.md)

> C5 **executes against** frozen **Runtime Model** only.  
> Execution responsibility is `Runtime Model → Validation → Submission → Persistence`.  
> Execution must not know drafts, Builder, FormDefinition mutation, Publish UI, or re-mint identity.

**Naming (do not collapse):** this **Forms Platform C5** is not Acquisition UI cutover C-5. It is not historical **P3 Publish UI**. It is not **P4 Themes**. It is not **P5 Analytics**. It is not Phase C **C4 Form Runtime** (serve). Sprint `validate_submission` / public intake write path already exist — C5 **binds** them to Runtime Model; it does **not** invent a second Forms submit engine.

---

## Why this slice

C1 sealed ids. C2 froze Contract Identity on every publication version. C3 bound Builder to `FormDefinition ↔ Draft` only. C4 projected frozen publications into **Runtime Model** ([#245](https://github.com/igortatarynovich/HostFlow/pull/245)/[#246](https://github.com/igortatarynovich/HostFlow/pull/246) · `4427b110` · PASS-ready `626e5a9d`).

The remaining hole: submit can still validate against a live draft, a ledger row bypassing Runtime Model, or a parallel “Forms engine” that rewrites schema / identity on the write path. If Execution imported Builder, skipped `serve`, or minted identity on submit, C2’s freeze and C4’s read-only boundary would collapse.

C5 closes that gap **without** teaching Execution about drafts, and **without** opening Publish UI, Themes, or Analytics.

**Platform posture:** Forms remains a **platform capability**, not a product module.

---

## Locked principle

Execution works only with the **Runtime Model**:

```text
Runtime Model  →  Validation  →  Submission  →  Persistence
```

`forms.runtime.model.v1` (plus its immutable Contract Identity copy) is the **only** model Execution may validate against. Every Builder model is unreachable — Execution must not import those modules. Publication ledger rows are **not** Execution inputs; callers compose Adapter `resolve` → C4 `serve` → C5 execute.

Execution **must not**:

- import Builder (`forms_platform.builder` / FormDefinition session)
- read or write Draft / `FormDefinition`
- call `save_session` / draft persist
- publish or call Adapter `publish` / `commit_publish`
- write Contract Identity or `schema_hash` (already frozen at C2 publish; copied into Runtime Model at C4)
- re-mint identity or rewrite `field_schema` on submit
- invent field types
- open P3 Publish UI, P4 Themes, or P5 Analytics
- invent a second public Forms submit HTTP / engine beside Shared Intake

Publish stays a **separate operation** on the C2 Adapter. Serve stays C4. Builder stays C3.

---

## Dual of C4

| Slice | Owns | Must not touch |
|-------|------|----------------|
| **C4 Form Runtime** | Frozen publication → **Runtime Model** (read-only) | FormDefinition, Draft, Builder, submit |
| **C5 Form Execution** | Runtime Model → Validation → Submission → Persistence | FormDefinition, Draft, Builder, publish, identity mint |

Runtime Model remains immutable **inside Execution**. Execution may fail closed; it must not mutate the model.

---

## Forbidden flow

```text
Execution → read Draft / FormDefinition     ← forbidden (binds submit to editor)
Execution → save draft                      ← forbidden
Execution → publish                         ← forbidden (P3 / Adapter mutation)
Execution → validate against ledger row only ← forbidden (must use Runtime Model)
Execution → second Forms submit engine      ← forbidden (Shared Intake remains write path)
```

## Required flow

```text
Builder (C3)
  → Save Draft
Publish (C2 Adapter)                      ← outside Builder / Runtime / Execution
  → new FormPublicationVersion
  → Freeze + Contract Identity
Adapter resolve
  → FormPublicationVersion
Form Runtime (C4)
  → Runtime Model
        │
        │  (Runtime stops here)
        ▼
Form Execution (C5)
  → validate against Runtime Model
  → Submission envelope + pin
  → Persistence (Shared Intake / submission_store)
```

Execution **starts exactly after Runtime Model**.

After C5 the layers are:

```text
Builder Layer (C3)
  FormDefinition · Draft · Validation
        │
        │  (Builder stops here)
        ▼
Publish Layer (C2 Adapter)
        ▼
FormPublicationVersion → Contract Identity
        ▼
Form Runtime (C4) → Runtime Model
        ▼
Form Execution (C5) → Validation → Submission → Persistence
```

---

## Form Execution (submit contract)

C5 **names** Form Execution. It does **not** add a second public Forms submit surface and does **not** replace Shared Intake.

Existing Stable pieces stay the implementation spine:

| Piece | Role in C5 |
|-------|------------|
| Runtime Model (`forms.runtime.model.v1`) | **sole validation input** |
| Adapter `validate_submission` / `normalize_answers` | Consume — bind to Runtime Model `field_schema` + identity |
| Adapter `submission` + version pin | Consume — pin `form_id` + `published_version` (+ identity copy) |
| `persist_submission_envelope` / Shared Intake | Consume — write path remains `/api/v1/public/intake` + `intake_platform.submission_store` |
| Adapter `publish` / Builder / C4 `serve` mutation | Forbidden |

A Runtime Model without a complete Contract Identity **must not** accept submission (C2 fail-closed). Validating a draft as if it were published is forbidden. Lifecycle / inactive / archived gates stay Publication State rules — Execution does not invent a parallel policy.

---

## Form Execution Gate (CI — mandatory on the later feat)

Named step. Full-repo pytest red does not waive it.

Execution path / package:

- does **not** import `forms_platform.builder`
- does **not** read or write Draft / `FormDefinition`
- does **not** call `save_session` / `publish` / `commit_publish`
- validates only against a Runtime Model (or an equivalent constructed solely from C4 `serve` output)
- fail-closed when Contract Identity is missing, incompatible, or `schema_hash` mismatches
- does **not** re-mint identity (`freeze_contract_identity` forbidden on execute)
- does **not** add a second Forms submit engine / public HTTP

This docs PR does **not** add that gate. The feat PR does.

---

## What already exists (do not rebuild)

| Piece | Status | C5 use |
|-------|--------|--------|
| Adapter `validate_submission` / `normalize_answers` | Stable | Consume — bind to Runtime Model |
| Adapter `submission` + version pin | Stable | Consume |
| Submission envelope / Shared Intake write path | Shipped | Persist — do not fork |
| C4 Runtime Model + `serve` | ✅ [#246](https://github.com/igortatarynovich/HostFlow/pull/246) | **Required input** |
| C3 Builder Runtime | ✅ [#244](https://github.com/igortatarynovich/HostFlow/pull/244) | **Outside Execution** — do not import |
| Public intake HTTP | Shipped | Keep as write path — no second Forms submit |

---

## Feat implementation order (mandatory — after this brief merges)

1. Name Form Execution as the submit contract over **Runtime Model**.  
2. Bind validate / normalize / pin / persist to that model (no draft path).  
3. Fail-closed on missing / incompatible identity (reuse C2 rules; do not re-mint).  
4. **Then** named Form Execution Gate.  
5. Do **not** add Publish UI, Themes, Analytics, Builder, or a second submit HTTP.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| C5 **feat** (binding + named gate) | After this brief merges |
| Publish UI / calling Adapter `publish` from canvas | P3 — locked |
| Themes | P4 — locked |
| Analytics | P5 — locked |
| C6 Optimization | After C5 |
| Stage 5 settings / R6 / FormTemplate / ADR-022 | Unchanged |
| Entity Workspace Phase D | Unchanged |

Do **not** mix Themes, Publish UI, Builder, Analytics, Stage 5, or R6 into C5.

---

## Phase C ladder (locked)

| Slice | Focus | Status |
|-------|--------|--------|
| **C1** | Contract seal | ✅ [#239](https://github.com/igortatarynovich/HostFlow/pull/239) / [#240](https://github.com/igortatarynovich/HostFlow/pull/240) |
| **C2** | Runtime contract + gates | ✅ [#241](https://github.com/igortatarynovich/HostFlow/pull/241) / [#242](https://github.com/igortatarynovich/HostFlow/pull/242) |
| **C3** | Builder Runtime | ✅ [#243](https://github.com/igortatarynovich/HostFlow/pull/243) / [#244](https://github.com/igortatarynovich/HostFlow/pull/244) · `638955d5` |
| **C4** | Form Runtime | ✅ [#245](https://github.com/igortatarynovich/HostFlow/pull/245) / [#246](https://github.com/igortatarynovich/HostFlow/pull/246) · `4427b110` |
| **C5** | Form Execution (this) | **active** (brief; feat locked) |
| **C6** | Optimization | After C5 |

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Forms **platform** (ADR-007) |
| 2 Exists? | Yes — Adapter validate/submission + Shared Intake; C5 binds them to Runtime Model |
| 3 Adapter | Execution **consumes** `validate_submission` / `submission`. It does not add `publish` or a second Adapter |
| 4 Boundary | No Builder import; no draft; no publish; no identity mint; no Themes / Publish UI / Analytics |
| 5 Settings | No new Manifest keys |
| 6 SoT | Runtime Model (C4) is validation SoT; Builder SoT stays C3; publication freeze stays C2 |
| 7 Events | Unchanged Experimental (`form.submission_received`) |
| 8 Requires | C4 Runtime Model + C2 identity |
| 9 License | None new |
| 10 Public contract | Additive naming of Form Execution over existing validate/submission. No Adapter DTO bump in this docs PR |

Does **not** amend L0 P-rules.

---

## Acceptance

- [ ] This brief merged (docs PR)  
- [ ] C4 marked **COMPLETE** in canon (#246 / `4427b110` · PASS-ready `626e5a9d`)  
- [ ] Product Track points here; C5 feat not opened in this PR  
- [ ] P3 Publish UI / P4 Themes / P5 Analytics remain locked  
- [ ] No second Forms submit engine named as this slice  

Feat DoD (later PR, not this one): named Form Execution Gate green; Execution does not import Builder; validate/submit only against Runtime Model.

**CI criterion for the later feat:** named **Forms Platform C5 Form Execution Gate**. Full-repo `Tests with coverage` is Engineering Track debt and does not block C5.

---

## DoD (this docs PR)

- [ ] Brief sealed; inbound refs from queue / roadmap / AGENTS / ADR-007 / Public Contract  
- [ ] C4 closed COMPLETE  
- [ ] C5 feat, Publish UI, Themes, Analytics **not** started  

---

## History

- 2026-08-14: C4 Form Runtime merged [#246](https://github.com/igortatarynovich/HostFlow/pull/246) (`4427b110`, PASS-ready `626e5a9d`). C5 Form Execution brief opened (docs). Feat locked until this brief merges. Not P3 Publish UI / P4 Themes / P5 Analytics / second Forms submit engine.
