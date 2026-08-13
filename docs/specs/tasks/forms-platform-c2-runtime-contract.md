# Forms Platform C2 — Runtime Contract & Gates

**Status:** **IN PROGRESS** (docs — this brief)  
**Branch (docs):** `docs/forms-platform-c2-runtime-contract`  
**Branch (code):** `feat/forms-platform-c2-runtime-contract` (after this brief **and** C1 [#239](https://github.com/igortatarynovich/HostFlow/pull/239) / [#240](https://github.com/igortatarynovich/HostFlow/pull/240) merge)  
**Parents:** [C1 contract seal](forms-platform-c1-contract-seal.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase C](../architecture/platform-completion-roadmap.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [Forms Public Contract](../architecture/forms-public-contract.md) · [Manifest](../architecture/capability-settings-manifest.md#forms)

> A form **must not exist outside its contract**.  
> C2 is runtime contract verification — not Builder, not authoring UX.  
> Builder (C3) opens only after these gates hold.

**Naming (do not collapse):** this **Forms Platform C2** is not Communication Epic C2 / C2.4 Scheduling (frozen). Historical Forms “C4 HTTP resolve” (`test_forms_platform_c4.py`) is Sprint-era Stable HTTP — not Phase C **C4 Form Runtime**.

---

## Why this slice

C1 seals *which* Passport / Manifest / Public Contract / Adapter ids exist. That is not enough: a published form can still drift across versions (Manifest v1 + Public Contract v2 + Adapter v3 + Builder v1).

C2 makes identity **mandatory on every form** and **CI-enforced**. After C2, any Manifest or Public Contract change is automatically testable.

**Platform posture:** Forms is **not** a product module (Recruitment / HR / Fleet / Finance / Services). It is a **platform capability**, same class as EntityWorkspace, ListWorkspace, Analytics Kit, RBAC, and Automations. Every product module consumes one Forms Platform. Compatibility and quality bars are **stricter** than for product modules.

---

## Goal

No HostFlow Form publication may resolve, publish, or accept a submission unless it carries one frozen **contract identity**. Gates fail CI when Manifest, Public Contract, Adapter, and identity disagree.

---

## Mandatory identity (every form)

Immutable set on every published form (publication DTO + ledger snapshot + envelope). Missing any field = invalid form.

| Field | Meaning |
|-------|---------|
| `contract_id` | Public contract id (`forms.public_contract.v1` until a versioned successor) |
| `manifest_version` | Forms Manifest document version |
| `public_contract_version` | Public Contract version (must match `contract_id` lineage) |
| `object_kind` | Platform object kind of this publication — **not** a module-local enum. Pin a Forms Public Contract kind (feat PR). New L0 kind = Architecture RFC |
| `lifecycle_status` | Publication lifecycle (`draft` / `active` / `archived`) |
| `schema_hash` | Hash of the frozen `field_schema` (drift detector) |
| `adapter_version` | Adapter id+version that may serve this publication (`forms.endpoint_adapter_v1` lineage) |

**Forbidden:** a live form with mixed identity (Manifest v1 / Public Contract v2 / Adapter v3 / Builder v1). All four planes must be **one agreed tuple**.

Existing Sprint 3–6 snapshots without the block: C2 feat **backfills or fail-closes** — no silent optional identity.

---

## Contract gates (CI — mandatory)

Named CI steps. Full-repo pytest red does not waive them.

### 1. Manifest Gate

- Unknown keys (not in sealed Manifest).  
- Removed required keys.  
- Structure / type / scope violations.  
- Incompatible `manifest_version` vs sealed baseline.

C1 already froze the key **set**. C2 adds compatibility rules across versions (additive keys allowed only with version bump; removals / type changes = fail).

### 2. Public Contract Gate

- Public Contract ops / error codes / DTO shape vs sealed baseline.  
- Change **without** raising `public_contract_version` / `contract_id` lineage → **CI fail**.  
- Additive (new optional field, new Experimental event) requires an explicit version note; breaking change requires a new contract id.

### 3. Adapter Gate

- Adapter implements exactly the Public Contract ops it claims.  
- Adapter must not accept payloads or keys absent from Manifest + Public Contract.  
- `adapter_version` on a publication must match the Adapter that serves it.

### 4. Contract Identity Gate (primary)

- Every `resolve` / `publish` / `submission` path returns or persists the full identity tuple.  
- Cross-check: `manifest_version` × `public_contract_version` × `adapter_version` × Builder surface version (when Builder exists) are **compatible**.  
- `schema_hash` matches the frozen schema on that publication version.  
- `object_kind` is the same platform kind for every publication of that type (no module-local dictionary).

---

## In scope (this docs PR)

1. This brief.  
2. Queue / roadmap / AGENTS / C1 / Product Layer epic name C2 as **next** after C1; lock Phase C ladder C1→C6.  
3. Builder remains **locked until C2 feat PASSes** — not until “platform feels ready”.

## In scope (feat PR — after C1 merge + this brief)

1. Persist identity on publication ledger / resolve DTO / submission envelope (additive Public Contract; bump version if the DTO becomes required).  
2. Four named CI gates above.  
3. Backfill or fail-closed policy for pre-C2 snapshots (documented in the feat PR).  
4. Architecture Review Checklist in the feat PR description.

`TenantLeadForm` may remain the storage bridge; identity is **projected onto** the publication, not a second form engine.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| C3 Builder Runtime (editor) | After C2 feat PASS |
| C4 Form Runtime / C5 Form Execution / C6 Optimization | After C3 |
| Stage 5 settings / enable-disable | ADR-005 / ADR-035 — not Forms |
| R6 table-cutover | [intake-runtime-split-v1.md](intake-runtime-split-v1.md) |
| FormTemplate SoT (replace `TenantLeadForm`) | Later Phase C (not C2) |
| Accept ADR-022 | Later Phase C |
| Meta → `FormSubmissionEnvelope` | Later Phase C |
| New L0 object kind | Architecture RFC — C2 must not invent a local kind dictionary |
| Entity Workspace Phase D | Unchanged |

Do **not** mix Builder product, Stage 5 settings, or R6 into C2.

---

## Phase C ladder (locked)

| Slice | Focus | Builder |
|-------|--------|---------|
| **C1** | Contract seal (ids / drift docs) | Locked |
| **C2** | Runtime contract + gates (this) | Locked until PASS |
| **C3** | Builder Runtime (editor over sealed format) | Unlocked |
| **C4** | Form Runtime | — |
| **C5** | Form Execution | — |
| **C6** | Optimization | — |

C3 is an **editor**. An editor must not open until the format it edits is protected.

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Forms **platform** (ADR-007) — not a product module |
| 2 Exists? | Yes — C1 seals ids; C2 enforces them at runtime |
| 3 Adapter | `forms.endpoint_adapter_v1` (**Stable**); C2 pins `adapter_version` |
| 4 Boundary | No Builder C3, no module-owned form stacks, no Outcome/KPI |
| 5 Settings | Manifest Gate only; no new product settings UI |
| 6 SoT | Publication identity on Forms ledger; modules consume Adapter |
| 7 Events | Unchanged Experimental this slice |
| 8 Requires | Endpoint, Submission; `object_kind` from Public Contract (RFC if new L0 kind) |
| 9 License | None new |
| 10 Public contract | **Additive** identity block; version bump if required fields are new |

Does **not** amend L0 P-rules. Passport status only.

---

## Acceptance

- Product Track next after C1 = this brief.  
- No form can be published/resolved/submitted without the identity tuple.  
- Four gates are named CI and fail on drift / mixed versions.  
- Builder stays locked until C2 feat PASSes.  
- Recruitment / HR / Fleet / Finance / Services still have **zero** private form runtimes.

---

## Likely files (feat PR)

| Area | Paths |
|------|--------|
| Identity | `forms_platform/publication_versions.py`, `adapter.py`, envelope |
| Gates | `backend/tests/forms_platform/test_forms_c2_*_gate.py` |
| CI | `.github/workflows/backend-ci.yml` named steps |
| Contract | `forms-public-contract.md` identity section (additive) |

---

## DoD

- [x] Brief sealed with identity + four gates + C1–C6 ladder  
- [x] Queue + roadmap point at C2 as next after C1; Builder locked until C2  
- [x] Platform (not product module) posture explicit  
- [ ] Feat PR after C1 merge  
