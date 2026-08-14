# Forms Platform C4 — Form Runtime

**Status:** **IN PROGRESS** (docs — brief seal; feat locked until this brief merges)  
**Branch (docs):** `docs/forms-platform-c4-form-runtime`  
**Parents:** [C3 Builder Runtime](forms-platform-c3-builder-runtime.md) ✅ · [C2 runtime contract](forms-platform-c2-runtime-contract.md) · [C1 contract seal](forms-platform-c1-contract-seal.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase C](../architecture/platform-completion-roadmap.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [Forms Public Contract](../architecture/forms-public-contract.md)

> C4 **serves only** frozen `FormPublicationVersion`.  
> Runtime responsibility is `FormPublicationVersion → Runtime view`.  
> Runtime must not know drafts, Builder, FormDefinition mutation, or Publish UI.

**Naming (do not collapse):** this **Forms Platform C4** is not Communication Epic C4 (there is none — Communication **C2.4** stays frozen). It is not historical **P3 Publish UI**. It is not **P4 Themes**. It is not Phase C **C5 Form Execution** (submit). Historical `backend/tests/forms_platform/test_forms_platform_c4.py` is Sprint-era HTTP resolve — **not** this slice’s named gate.

---

## Why this slice

C1 sealed ids. C2 froze Contract Identity on every publication version. C3 bound Builder to `FormDefinition ↔ Draft` only ([#243](https://github.com/igortatarynovich/HostFlow/pull/243)/[#244](https://github.com/igortatarynovich/HostFlow/pull/244) · `638955d5`).

The remaining hole: serving a live form can still reach back into the editor. If Runtime imported Builder, read a Dirty Draft, or minted identity on a keystroke, C2’s freeze and C3’s boundary would collapse.

C4 closes that gap **without** teaching Runtime about drafts, and **without** opening Publish UI, Themes, or submit.

**Platform posture:** Forms remains a **platform capability**, not a product module.

---

## Locked principle

Runtime works only with the **frozen** model:

```text
FormPublicationVersion  →  Runtime view
```

`FormPublicationVersion` (plus its immutable Contract Identity) is the **only** model Runtime may serve. Every Builder model is unreachable — Runtime must not import those modules.

Runtime **must not**:

- import Builder (`forms_platform.builder` / FormDefinition session)
- read or write Draft / `FormDefinition`
- call `save_session` / draft persist
- publish or call Adapter `publish` / `commit_publish`
- write Contract Identity or `schema_hash` (already frozen at C2 publish)
- accept submissions (C5)
- invent field types
- open P3 Publish UI or P4 Themes

Publish stays a **separate operation** on the C2 Adapter. Submit stays C5. Builder stays C3.

---

## Dual of C3

| Slice | Owns | Must not touch |
|-------|------|----------------|
| **C3 Builder Runtime** | `FormDefinition` ↔ Draft (mutable) | Publication version, identity, Adapter publish/resolve |
| **C4 Form Runtime** | Frozen `FormPublicationVersion` (immutable schema + identity) | FormDefinition, Draft, Builder session |

Dirty Draft and Saved Draft remain mutable **inside Builder**. They are not runtime inputs.

---

## Forbidden flow

```text
Runtime → read Draft / FormDefinition     ← forbidden (binds serving to editor)
Runtime → save draft                      ← forbidden
Runtime → publish                         ← forbidden (P3 / Adapter mutation)
Runtime → submit                          ← forbidden here (C5)
```

## Required flow

```text
Builder (C3)
  → Save Draft
Publish (C2 Adapter)                      ← outside Builder and outside C4
  → new FormPublicationVersion
  → Freeze + Contract Identity
Form Runtime (C4)
  → resolve / serve that frozen version
        │
        │  (Runtime stops here)
        ▼
Form Execution (C5)                       ← submit against that version
```

Runtime **ends exactly before submit**.

After C4 the layers are:

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
Form Runtime (C4) → serve frozen view
        ▼
Form Execution (C5) → Submission
```

---

## Form Runtime (serving contract)

C4 **names** Form Runtime. It does **not** add a second resolve engine and does **not** add a second public HTTP form.

Adapter `resolve` (`forms.endpoint_adapter_v1`) is already **Stable**. C4 binds the serving path to that frozen publication view:

| Model | Runtime |
|-------|---------|
| `FormPublicationVersion` + Contract Identity | **read-only** |
| Adapter `resolve` DTO | **consume** (no new Adapter op) |
| `FormDefinition` / Draft / Builder session | forbidden |
| Adapter `publish` | forbidden |
| Submission / `validate_submission` | C5 — not this slice |

A publication without a complete Contract Identity **must not** be served (C2 fail-closed). Serving a draft as if it were published is forbidden.

Storage may remain `TenantLeadForm` pointer + `form_publication_versions`. C4 names the **serving model**, not a FormTemplate cutover.

---

## Form Runtime Gate (CI — mandatory on the later feat)

Named step. Full-repo pytest red does not waive it. Historical `test_forms_platform_c4.py` is **not** this gate.

Runtime package / serving path:

- does **not** import `forms_platform.builder`
- does **not** read or write Draft / `FormDefinition`
- does **not** call `save_session` / `publish` / `commit_publish`
- serves only a frozen `FormPublicationVersion`
- fail-closed when Contract Identity is missing or incompatible
- does **not** accept submissions

This docs PR does **not** add that gate. The feat PR does.

---

## What already exists (do not rebuild)

| Piece | Status | C4 use |
|-------|--------|--------|
| Adapter `resolve` / `resolve_publication` | Stable | Consume — do not fork |
| C2 Contract Identity on publication versions | ✅ [#242](https://github.com/igortatarynovich/HostFlow/pull/242) | Required on every served version |
| C3 Builder Runtime | ✅ [#244](https://github.com/igortatarynovich/HostFlow/pull/244) | **Outside Runtime** — do not import |
| Sprint HTTP `test_forms_platform_c4.py` | Historical | Name collision only — not Phase C C4 |
| Public intake submit path | Shipped | **C5** — do not pull into C4 |

---

## Feat implementation order (mandatory — after this brief merges)

1. Name Form Runtime as the serving contract over frozen `FormPublicationVersion`.  
2. Isolate the serving path from Builder (no `forms_platform.builder` import).  
3. Fail-closed when identity is missing (reuse C2 rules; do not re-mint).  
4. **Then** named Form Runtime Gate.  
5. Do **not** add Publish UI, Themes, submit/Execution, or a second resolve HTTP.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| C4 **feat** (package + named gate) | After this brief merges |
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
| **C4** | Form Runtime (this) | **active** (brief; feat locked) |
| **C5** | Form Execution | After C4 feat PASS |
| **C6** | Optimization | After C5 |

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Forms **platform** (ADR-007) |
| 2 Exists? | Yes — Adapter `resolve` + C2 identity; C4 names the serving runtime |
| 3 Adapter | Runtime **consumes** `resolve`. It does not add `publish` or a second Adapter |
| 4 Boundary | No Builder import; no draft; no publish; no submit; no Themes |
| 5 Settings | No new Manifest keys |
| 6 SoT | Frozen `FormPublicationVersion` (C2); Builder SoT stays C3 |
| 7 Events | Unchanged Experimental |
| 8 Requires | C2 identity + C3 Builder isolation |
| 9 License | None new |
| 10 Public contract | Additive naming of Form Runtime over existing `resolve`. No Adapter DTO bump in this docs PR |

Does **not** amend L0 P-rules.

---

## Acceptance

- [ ] This brief merged (docs PR)  
- [ ] C3 marked **COMPLETE** in canon (#244 / `638955d5`)  
- [ ] Product Track points here; C4 feat not opened in this PR  
- [ ] P3 Publish UI / P4 Themes / P5 Analytics / C5 remain locked  
- [ ] Historical Sprint C4 HTTP tests not renamed as this gate  

Feat DoD (later PR, not this one): named Form Runtime Gate green; Runtime does not import Builder; serve frozen publication only.

**CI criterion for the later feat:** named **Forms Platform C4 Form Runtime Gate**. Full-repo `Tests with coverage` is Engineering Track debt and does not block C4.

---

## DoD (this docs PR)

- [ ] Brief sealed; inbound refs from queue / roadmap / AGENTS / ADR-007 / Public Contract  
- [ ] C3 closed COMPLETE  
- [ ] C4 feat, Publish UI, Themes, C5 Execution **not** started  

---

## History

- 2026-08-14: C3 Builder Runtime merged [#244](https://github.com/igortatarynovich/HostFlow/pull/244) (`638955d5`, PASS-ready `2e5f9720`). C4 Form Runtime brief opened (docs). Feat locked until this brief merges. Not P3 Publish UI / P4 Themes / C5 Execution / Sprint HTTP C4.
