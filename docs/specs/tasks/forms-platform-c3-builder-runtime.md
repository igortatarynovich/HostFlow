# Forms Platform C3 — Builder Runtime

**Status:** **IN PROGRESS** (docs — this brief)  
**Branch (docs):** `docs/forms-platform-c3-builder-runtime`  
**Branch (code):** `feat/forms-platform-c3-builder-runtime` (after this brief merges)  
**Parents:** [C2 runtime contract](forms-platform-c2-runtime-contract.md) · [C1 contract seal](forms-platform-c1-contract-seal.md) · [P2 Builder](forms-product-p2-builder.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase C](../architecture/platform-completion-roadmap.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [Forms Public Contract](../architecture/forms-public-contract.md)

> C3 is the **editor of FormDefinition**.  
> Draft save is not publish. Keystroke must not freeze Contract Identity.  
> C2 already protects the publication format; C3 must not bypass it.

**Naming (do not collapse):** this **Forms Platform C3** is not Communication Context C3 (policy ports). It is not historical **P3 Publish UI** (wizard / version-management chrome). P2 Builder MVP already exists; C3 binds that editor to the C2 model. Phase C **C4 Form Runtime** stays locked.

---

## Why this slice

C1 sealed ids. C2 made every **publication version** carry an immutable Contract Identity (JCS+SHA-256, declared compatibility, fail-closed backfill). [#239](https://github.com/igortatarynovich/HostFlow/pull/239)–[#242](https://github.com/igortatarynovich/HostFlow/pull/242) are merged.

P2 shipped composition commands, draft persistence, and a minimal canvas. That editor still has no **runtime contract** against FormDefinition vs FormPublicationVersion: a save could be mistaken for freeze, and a freeze on every edit would mint identities that C2 forbade.

C3 closes that gap. After C3, C4 can serve a frozen version without caring how the definition was authored.

**Platform posture:** Forms remains a **platform capability**, not a product module. Recruitment / HR / Fleet / Finance / Services still have zero private builders.

---

## Target model (normative — unchanged from C2)

```text
FormDefinition          → mutable schema (C3 edits this)
        │
        │ publish (freeze) — explicit command only
        ▼
FormPublicationVersion  → immutable schema snapshot + Contract Identity
        │
        │ submit
        ▼
FormSubmission          → pin to that publication version
```

| Layer | C3 may | C3 must not |
|-------|--------|-------------|
| FormDefinition / Builder draft | Add / reorder / remove Catalog instances; save draft; dirty + revision | Freeze identity; write `form_publication_versions`; invent field types |
| Publication version | Call existing Adapter `publish` as **one explicit command** | Patch frozen schema / identity; auto-publish on save |
| Submission / public serve | — | Open C4 Form Runtime or C5 execution |

Storage may remain `TenantLeadForm` + builder draft tables. C3 names the **editor contract**, not a FormTemplate cutover.

---

## Goal

A Builder session can change a definition without creating a publication version.  
The only freeze point is an explicit **publish** that goes through C2 (`commit_publish` / Adapter).  
Field types come only from the frozen Field Catalog.

---

## What already exists (do not rebuild)

| Piece | Status | C3 use |
|-------|--------|--------|
| P2.1–P2.5 Builder MVP | ✅ COMPLETE | Canvas / commands / draft persistence |
| `forms.builder.composition_commands.v1` | Shipped | Editor command surface |
| Field Catalog v1 | FROZEN | Only legal component ids |
| Adapter `publish` / C2 identity | ✅ [#242](https://github.com/igortatarynovich/HostFlow/pull/242) | Explicit freeze |

C3 is **runtime contract + gates** over that stack, not a second builder.

---

## Builder Runtime rules

1. **Draft save ≠ publish.** Persistence of composition / draft revision must not insert a ledger row or mint Contract Identity.  
2. **No identity on live draft.** Resolve of an unpublished definition stays identity-less (C2 already: draft `contract_identity is None`).  
3. **Catalog only.** `add_instance` / config must fail on unknown `component_id` (P2 `require_catalog=True` — C3 gates it). Builder must not invent field types.  
4. **Explicit publish.** One Adapter `publish` call freezes current definition → new `FormPublicationVersion` + identity. Repeat publish after schema change → **new** version (C2 immutability).  
5. **Builder surface version** (when declared): pin `forms.builder.composition_commands.v1` (or successor) on the Forms-owned compatibility tuple **at freeze**. Do not mint a new tuple on every keystroke.  
6. **No module-owned builders.** Product modules consume this editor/Adapter; they do not fork a form canvas.

---

## Contract gates (CI — feat PR)

Named step. Full-repo pytest red does not waive it.

### Builder Runtime Gate

- Draft save does not write `form_publication_versions` / Contract Identity.  
- Unpublished resolve has `contract_identity is None`.  
- Unknown Catalog component → fail.  
- Explicit publish creates a new frozen version with complete C2 identity; second schema edit + publish → different `schema_hash` / new version.  
- Auto-publish-on-save is forbidden.

---

## In scope (this docs PR)

1. This brief (editor vs freeze; C3 ≠ P3 Publish UI; C3 ≠ Communication C3).  
2. Queue / roadmap / AGENTS / C2 / Product Layer epic: C1+C2 ✅; **active = C3**; C4 locked.  
3. Old P3 Publish UI / P4 Themes / P5 Analytics stay **out** (not unlocked by C3).

## Feat implementation order (mandatory)

1. FormDefinition as the mutable record the Builder writes (bridge storage OK).  
2. Draft save / composition commands isolated from the publication ledger.  
3. Catalog-only enforcement as a runtime gate (not only a P2 unit test).  
4. Explicit publish command → existing C2 freeze.  
5. **Then** named Builder Runtime Gate.  
6. Do **not** start C4 (serve frozen version to public runtime) in this slice.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| C4 Form Runtime (serve frozen publication) | After C3 feat PASS |
| C5 Form Execution / C6 Optimization | After C4 |
| P3 Publish UI (wizard / version chrome / preview) | Later Phase C — not this editor contract |
| P4 Themes / P5 Analytics | Locked |
| Stage 5 settings / enable-disable | ADR-005 / ADR-035 |
| R6 table-cutover | [intake-runtime-split-v1.md](intake-runtime-split-v1.md) |
| FormTemplate SoT | Later Phase C |
| Accept ADR-022 · Meta → envelope | Later Phase C |
| Entity Workspace Phase D | Unchanged |

Do **not** mix Themes, public Form Runtime, Stage 5, or R6 into C3.

---

## Phase C ladder (locked)

| Slice | Focus | Status |
|-------|--------|--------|
| **C1** | Contract seal | ✅ [#239](https://github.com/igortatarynovich/HostFlow/pull/239) / [#240](https://github.com/igortatarynovich/HostFlow/pull/240) |
| **C2** | Runtime contract + gates | ✅ [#241](https://github.com/igortatarynovich/HostFlow/pull/241) / [#242](https://github.com/igortatarynovich/HostFlow/pull/242) |
| **C3** | Builder Runtime (this) | **active** |
| **C4** | Form Runtime | Locked until C3 feat PASS |
| **C5** | Form Execution | After C4 |
| **C6** | Optimization | After C5 |

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Forms **platform** (ADR-007) |
| 2 Exists? | Yes — P2 MVP + C2 freeze; C3 binds editor to definition |
| 3 Adapter | `forms.endpoint_adapter_v1`; publish remains Adapter-only |
| 4 Boundary | No C4 public runtime, no Themes/Analytics, no module builders, no Outcome/KPI |
| 5 Settings | No new Manifest keys this slice (Builder flag already UNLOCKED) |
| 6 SoT | FormDefinition (mutable, Builder); publication identity stays C2 ledger |
| 7 Events | Unchanged Experimental |
| 8 Requires | Endpoint, Submission; Catalog v1 frozen |
| 9 License | None new |
| 10 Public contract | Additive at most (builder surface version on freeze tuple). No breaking DTO change required to open the editor contract. |

Does **not** amend L0 P-rules.

---

## Acceptance

- Product Track active = this brief.  
- Draft save never freezes a publication version.  
- Explicit publish uses C2 identity; schema change → new version.  
- Catalog-only field types.  
- Named Builder Runtime Gate in the feat PR.  
- P3 Publish UI / P4 / P5 / C4 remain locked.  
- Zero private builders in product modules.

---

## Likely files (feat PR)

| Area | Paths |
|------|--------|
| Editor | `forms_platform/builder/*` |
| Freeze | Adapter `commit_publish` (C2 — call, do not reimplement) |
| Gate | `backend/tests/forms_platform/test_forms_c3_builder_runtime_gate.py` |
| CI | `.github/workflows/backend-ci.yml` named step |

---

## DoD

- [x] Brief sealed: editor vs freeze; C3 ≠ P3; C3 ≠ Communication C3  
- [x] Queue + roadmap point at C3; C4 locked  
- [ ] Feat PR after this brief merges  

---

## History

- 2026-08-14: C1 [#239](https://github.com/igortatarynovich/HostFlow/pull/239)/[#240](https://github.com/igortatarynovich/HostFlow/pull/240) + C2 [#241](https://github.com/igortatarynovich/HostFlow/pull/241)/[#242](https://github.com/igortatarynovich/HostFlow/pull/242) merged. C3 opened as Builder Runtime (not Publish UI).
