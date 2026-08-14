# Forms Platform C3 — Builder Runtime

**Status:** **COMPLETE** ([#243](https://github.com/igortatarynovich/HostFlow/pull/243)/[#244](https://github.com/igortatarynovich/HostFlow/pull/244) · `638955d5`)  
**Next:** [C4 Form Runtime](forms-platform-c4-form-runtime.md)  
**Branch (docs):** `docs/forms-platform-c3-builder-runtime` ✅ [#243](https://github.com/igortatarynovich/HostFlow/pull/243)  
**Branch (code):** `feat/forms-platform-c3-builder-runtime` ✅ [#244](https://github.com/igortatarynovich/HostFlow/pull/244)  
**Parents:** [C2 runtime contract](forms-platform-c2-runtime-contract.md) · [C1 contract seal](forms-platform-c1-contract-seal.md) · [P2 Builder](forms-product-p2-builder.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase C](../architecture/platform-completion-roadmap.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [Forms Public Contract](../architecture/forms-public-contract.md)

> C3 edits **only** `FormDefinition`.  
> Builder responsibility is `FormDefinition ↔ Draft`.  
> Builder must not know publications, submissions, Adapter, resolve, or identity.

**Naming (do not collapse):** this **Forms Platform C3** is not Communication Context C3 (policy ports). It is not historical **P3 Publish UI**. P2 Builder MVP already exists; C3 binds that editor to `FormDefinition` and a draft state machine. Phase C **C4 Form Runtime** is next — [brief](forms-platform-c4-form-runtime.md).

---

## Why this slice

C1 sealed ids. C2 made every **publication version** carry an immutable Contract Identity. [#239](https://github.com/igortatarynovich/HostFlow/pull/239)–[#243](https://github.com/igortatarynovich/HostFlow/pull/243) are merged.

P2 shipped composition commands, draft persistence, and a minimal canvas. That editor still has no **FormDefinition** term and no draft state machine. If Builder ever called Adapter `publish` on save, editor and runtime would fuse — the hole C2 exists to prevent.

C3 closes that gap **without** teaching Builder about freeze.

**Platform posture:** Forms remains a **platform capability**, not a product module.

---

## Locked principle

Builder works only with the **mutable** model:

```text
FormDefinition  ↔  Draft
```

`FormDefinition` is the **only** model Builder may change. Every other Forms model is readonly from Builder’s point of view (and in practice: unreachable — Builder must not import those modules).

Builder **must not**:

- change `FormPublicationVersion`
- recompute `schema_hash`
- write or read Contract Identity
- publish
- accept submissions
- resolve a publication
- import Adapter (`forms.endpoint_adapter_v1` / `forms_platform.adapter`)

Publish stays a **separate operation** on the C2 Adapter. It is not a Builder command.

---

## Forbidden flow

```text
Builder → Save → Publish     ← forbidden (binds editor to runtime)
```

## Required flow

```text
Builder
  → Save Draft
  → Draft exists (still mutable)
Publish (C2 Adapter)          ← outside Builder
  → new FormPublicationVersion
  → Freeze
  → Contract Identity
  → Resolve
  → Submission
```

Builder **ends exactly before Publish**.

After C3 the layers are:

```text
Builder Layer
  FormDefinition · Draft · Validation · Autosave (later)
        │
        │  (Builder stops here)
        ▼
Publish Layer (C2 Adapter)
        ▼
FormPublicationVersion → Contract Identity → Resolve → Submission
```

---

## FormDefinition (Definition Contract)

`FormDefinition` is the sole mutable document the editor owns (composition of Catalog instances + definition id). Storage may still be `TenantLeadForm` pointer + `form_builder_drafts`; C3 names the **model**, not a FormTemplate cutover.

| Model | Builder |
|-------|---------|
| `FormDefinition` | **read/write** |
| Draft (session + persistence of that definition) | **read/write** |
| `FormPublicationVersion` | forbidden |
| Contract Identity / `schema_hash` | forbidden |
| Submission | forbidden |
| Adapter resolve / publish | forbidden |

---

## Draft states (Dirty vs Saved)

Two persistence-facing kinds, both **mutable**:

| Kind | Meaning |
|------|---------|
| **Dirty Draft** | Being edited. Everything on the definition may change. Not yet the saved tip. |
| **Saved Draft** | Persisted. Still mutable. Not a publication. |

Only **Publish** (C2, outside Builder) creates:

| Kind | Meaning |
|------|---------|
| **Publication Version** | Immutable snapshot + Contract Identity |

---

## Builder State Machine (contract, not UI)

Not a canvas. Not autosave UX. A closed set of session states:

| State | Meaning |
|-------|---------|
| `new` | Definition created, not persisted |
| `dirty` | Dirty Draft — local edits vs last saved tip |
| `saving` | Persist in flight |
| `saved` | Saved Draft — tip matches last successful persist |
| `validation_error` | Catalog / composition validation failed on save or edit |
| `conflict` | Optimistic revision mismatch (future collab) |
| `closed` | Archived / session closed |

Illegal transitions fail closed. Autosave, joint editing, and Publish UI consume this machine later — they do not expand it in C3.

---

## Builder Runtime Gate (CI — mandatory)

Named step. Full-repo pytest red does not waive it.

Builder package (`backend/app/forms_platform/builder/`):

- does **not** import Adapter / `publication_versions` / `contract_identity` / `submission_envelope` / `canonical` (schema hash)
- does **not** call `publish` / `commit_publish` / `resolve_publication`
- does **not** write Contract Identity or publication ledger rows
- save draft never creates a `FormPublicationVersion`
- unknown Catalog component still fails (P2 `require_catalog=True`); failed save lands in `validation_error` / `conflict` with the session attached to the typed error
- state machine: `new`/`dirty`/`saving`/`saved`/`validation_error`/`conflict`/`closed`; Dirty and Saved remain mutable
- `FormDefinition` is the only domain document Builder mutates

---

## What already exists (do not rebuild)

| Piece | Status | C3 use |
|-------|--------|--------|
| P2.1–P2.5 Builder MVP | ✅ COMPLETE | Canvas / commands / draft persistence |
| `forms.builder.composition_commands.v1` | Shipped | Editor command surface |
| Field Catalog v1 | FROZEN | Only legal component ids |
| Adapter `publish` / C2 identity | ✅ [#242](https://github.com/igortatarynovich/HostFlow/pull/242) | **Outside Builder** — do not call from C3 |

---

## Feat implementation order (mandatory)

1. `FormDefinition` as the mutable record.  
2. Draft state machine (`new` → `dirty` → `saving` → `saved` / `validation_error` / `conflict` / `closed`).  
3. Draft save isolated from the publication ledger (P2.4 persist; no Adapter).  
4. Catalog-only enforcement remains a runtime rule.  
5. **Then** named Builder Runtime Gate (import + save + state).  
6. Do **not** add Publish, resolve, Themes, or C4.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Publish UI / calling Adapter `publish` | Later — not Builder |
| C4 Form Runtime / C5 Execution / C6 | [C4 brief](forms-platform-c4-form-runtime.md) — after this COMPLETE |
| P3 Publish UI · P4 Themes · P5 Analytics | Locked |
| Autosave / collab UX | Consume the state machine later |
| Stage 5 settings / R6 / FormTemplate / ADR-022 | Unchanged |
| Entity Workspace Phase D | Unchanged |

Do **not** mix Themes, Publish UI, public Form Runtime, Stage 5, or R6 into C3.

---

## Phase C ladder (locked)

| Slice | Focus | Status |
|-------|--------|--------|
| **C1** | Contract seal | ✅ [#239](https://github.com/igortatarynovich/HostFlow/pull/239) / [#240](https://github.com/igortatarynovich/HostFlow/pull/240) |
| **C2** | Runtime contract + gates | ✅ [#241](https://github.com/igortatarynovich/HostFlow/pull/241) / [#242](https://github.com/igortatarynovich/HostFlow/pull/242) |
| **C3** | Builder Runtime (this) | ✅ [#243](https://github.com/igortatarynovich/HostFlow/pull/243) / [#244](https://github.com/igortatarynovich/HostFlow/pull/244) |
| **C4** | Form Runtime | [brief](forms-platform-c4-form-runtime.md) ← next |
| **C5** | Form Execution | After C4 |
| **C6** | Optimization | After C5 |

---

## Architecture Review (L0 — this feat)

| # | Answer |
|---|--------|
| 1 Owner | Forms **platform** (ADR-007) |
| 2 Exists? | Yes — P2 MVP; C3 adds FormDefinition + draft state machine |
| 3 Adapter | Builder **does not import** Adapter. Publish remains C2 Adapter-only, outside this package |
| 4 Boundary | No publish/resolve/identity; no C4; no Themes; no module builders |
| 5 Settings | No new Manifest keys |
| 6 SoT | FormDefinition (mutable, Builder); publication identity stays C2 ledger |
| 7 Events | Unchanged Experimental |
| 8 Requires | Catalog v1 frozen. Endpoint/Submission exist but Builder does not call them |
| 9 License | None new |
| 10 Public contract | Additive: Builder Draft API ≠ Adapter. No Adapter DTO bump |

Does **not** amend L0 P-rules.

---

## Acceptance

- Builder mutates only `FormDefinition` / Draft.  
- Builder does not import Adapter and cannot publish, resolve, or write identity.  
- Dirty Draft and Saved Draft are both mutable; Publication Version appears only after C2 Publish.  
- Named Builder Runtime Gate in CI.  
- P3 Publish UI / P4 / P5 / C4 remain locked.  
- Queue unchanged (still C3).

---

## Likely files (feat PR)

| Area | Paths |
|------|--------|
| Definition + state | `forms_platform/builder/definition.py`, `state.py` |
| Persist | `forms_platform/builder/draft_persistence.py` (no Adapter) |
| Gate | `backend/tests/forms_platform/test_forms_c3_builder_runtime_gate.py` |
| CI | `.github/workflows/backend-ci.yml` named step |
| Brief | this file (boundary seal vs #243) |

---

## DoD

- [x] Brief #243 merged  
- [x] Boundary sealed: FormDefinition-only; no Adapter; Publish outside Builder  
- [x] Feat: FormDefinition + state machine + named gate — [#244](https://github.com/igortatarynovich/HostFlow/pull/244) · `638955d5`  

---

## History

- 2026-08-14: C1 [#239](https://github.com/igortatarynovich/HostFlow/pull/239)/[#240](https://github.com/igortatarynovich/HostFlow/pull/240) + C2 [#241](https://github.com/igortatarynovich/HostFlow/pull/241)/[#242](https://github.com/igortatarynovich/HostFlow/pull/242) merged. C3 opened as Builder Runtime (not Publish UI) — [#243](https://github.com/igortatarynovich/HostFlow/pull/243).  
- 2026-08-14: Boundary correction — Builder = FormDefinition ↔ Draft only; no Adapter import; Publish remains C2; draft state machine (`new`/`dirty`/`saving`/`saved`/`validation_error`/`conflict`/`closed`).
- 2026-08-14: Feat — failed save attaches `validation_error`/`conflict` session; named gate covers unknown Catalog and revision conflict.
- 2026-08-14: HTTP draft save/load goes through FormDefinition session (`save_session_async`); still not Publish UI.  
- 2026-08-14: Threat model [`forms-platform.md`](../../security/threat-models/forms-platform.md) covers C3 (FP-11…FP-13); named C3 gate remains the CI criterion.  
- 2026-08-14: Existing P2.5 canvas reads `builder_state` from Draft API; no autosave, no Publish UI.
- 2026-08-14: C3 feat merged [#244](https://github.com/igortatarynovich/HostFlow/pull/244) (`638955d5`; PASS-ready `2e5f9720`). Named C3 gate / docs-gates / security-gates / frontend-static-qa SUCCESS. Next = [C4 Form Runtime](forms-platform-c4-form-runtime.md).
