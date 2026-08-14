# Forms Platform C2 — Runtime Contract & Gates

**Status:** **COMPLETE** (C1 [#239](https://github.com/igortatarynovich/HostFlow/pull/239)/[#240](https://github.com/igortatarynovich/HostFlow/pull/240) · C2 [#241](https://github.com/igortatarynovich/HostFlow/pull/241)/[#242](https://github.com/igortatarynovich/HostFlow/pull/242))  
**Next:** [C3 Builder Runtime](forms-platform-c3-builder-runtime.md) ✅ · [C4 Form Runtime](forms-platform-c4-form-runtime.md) ← active (feat)  
**Parents:** [C1 contract seal](forms-platform-c1-contract-seal.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase C](../architecture/platform-completion-roadmap.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [Forms Public Contract](../architecture/forms-public-contract.md) · [Manifest](../architecture/capability-settings-manifest.md#forms)

> A **publication version** must not exist outside its contract.  
> C2 is runtime contract verification — not Builder, not authoring UX.  
> Builder (C3) ✅ [#244](https://github.com/igortatarynovich/HostFlow/pull/244). Form Runtime (C4) — [brief](forms-platform-c4-form-runtime.md).

**Naming (do not collapse):** this **Forms Platform C2** is not Communication Epic C2 / C2.4 Scheduling (frozen). Historical Forms “C4 HTTP resolve” (`test_forms_platform_c4.py`) is Sprint-era Stable HTTP — not Phase C **C4 Form Runtime**.

---

## Why this slice

C1 seals *which* Passport / Manifest / Public Contract / Adapter ids exist. That is not enough: a published form can still drift across versions (Manifest v1 + Public Contract v2 + Adapter v3 + Builder v1).

C2 makes **Contract Identity mandatory on every publication version**, CI-enforced, and **separate from publication lifecycle**. After C2, Manifest / Public Contract / Adapter changes are testable without rewriting history.

**Platform posture:** Forms is **not** a product module (Recruitment / HR / Fleet / Finance / Services). It is a **platform capability**, same class as EntityWorkspace, ListWorkspace, Analytics Kit, RBAC, and Automations. Every product module consumes one Forms Platform. Compatibility and quality bars are **stricter** than for product modules.

---

## Target model (normative)

```text
FormDefinition          → mutable schema (C3 edits this)
        │
        │ publish (freeze)
        ▼
FormPublicationVersion  → immutable schema snapshot
                        → immutable Contract Identity
                        → lifecycle_status (mutable, not identity)
        │
        │ submit
        ▼
FormSubmission          → immutable reference to that FormPublicationVersion
                        → validates against that version’s frozen schema only
```

Storage may remain the existing bridge (`TenantLeadForm` pointer + `form_publication_versions` ledger + submission envelope). C2 names the **model**, not a FormTemplate SoT refactor.

| Layer | Mutable? | Contract Identity |
|-------|----------|-------------------|
| Form definition / Builder draft | Yes — schema may change while editing | **Not** required as a frozen tuple. Draft must not be treated as a publication. |
| Publication version | **No** — schema + identity frozen at publish | **Required**, complete, immutable |
| Submission | Content immutable; processing status separate | References the exact publication version + its identity |

**Publish** is the freeze point: C3 edits definition; publish creates a new `FormPublicationVersion`; C5 always knows which schema accepted the submission.

---

## Goal

A publication version cannot **resolve**, **publish** (freeze), or **accept a submission** without a complete **Contract Identity**.  
`lifecycle_status` controls **whether that version is currently allowed** to perform the operation — it does not change identity.

Gates fail CI on Manifest / Public Contract / Adapter drift, undeclared compatibility, and identity/hash mismatch.

---

## Contract Identity (immutable)

Frozen on **every publication version** (ledger row + resolve DTO + submission pin). Missing any field = invalid publication version. Changing any field on an existing row is **forbidden** — that is a new version.

| Field | Meaning |
|-------|---------|
| `contract_id` | Public contract id lineage (`forms.public_contract.v1` until a successor) |
| `manifest_version` | Forms Manifest document version **at freeze** |
| `public_contract_version` | Public Contract version **at freeze** (lineage of `contract_id`) |
| `object_kind` | Platform object kind of this publication — **not** a module-local enum. Pin in Public Contract (feat PR). New L0 kind = Architecture RFC |
| `schema_hash` | SHA-256 of **canonical** frozen `field_schema` (see below) |
| `adapter_version` | Adapter id+version **bound at freeze** (`forms.endpoint_adapter_v1` lineage) |

**Not identity:** `lifecycle_status` (`draft` / `active` / `archived`). It is **Publication State**.

Draft → active → archived must **not** mint a new Contract Identity. Schema / contract / adapter did not change.

Existing Sprint 3–6 snapshots without the identity block: C2 feat **backfills or fail-closes** — no silent optional identity on publication versions.

---

## Publication State (mutable)

| Field | Meaning |
|-------|---------|
| `lifecycle_status` | Whether this publication is currently allowed to resolve / accept submissions (`draft` / `active` / `archived`) |

Rule:

> Publication cannot resolve, publish, or accept a submission without a complete Contract Identity.  
> Lifecycle controls whether the publication is **currently allowed** to perform the operation.

Examples: `archived` keeps identity and schema; it may refuse new submissions. `activate` / `deactivate` already exist as Stable ops — they must not rewrite `field_schema` or `schema_hash`.

---

## Publication version immutability

After a ledger row exists:

- `field_schema` and `schema_hash` **cannot** be rewritten or recalculated on that row.  
- Contract Identity fields **cannot** be patched.  
- A schema change **creates a new publication version** (new ledger row + new pointer).  
- Old submissions keep referencing the old version. Audit and replay are therefore real.

This is already the Sprint 3–4 ledger intent. C2 makes it an identity rule, not only a snapshot comment.

---

## Canonical `schema_hash`

`schema_hash` is a **contract field**, not an implementation detail.

1. **Input:** the frozen `field_schema` document of that publication version (`forms.field_schema.v1`). Not lifecycle, not adapter metadata, not pointer fields.  
2. **Canonical serialization:** [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) JSON Canonicalization Scheme (JCS) — UTF-8, lexicographic object keys, no insignificant whitespace. Equivalent JSON with different key order **must** hash equal.  
3. **Algorithm:** SHA-256 over those canonical bytes.  
4. **Encoding:** lowercase hex digest, stored as `schema_hash`.  
5. **Gate:** recompute from the stored schema; mismatch = fail (drift or non-canonical write).

Feat PR ships one canonical encoder used by publish, resolve, submission, and CI. Ad-hoc `json.dumps` is forbidden for hashing.

---

## Compatibility (declared, not “versions equal”)

Two different version planes:

| Plane | What it versions | Effect of a bump |
|-------|------------------|------------------|
| **Public Contract / API** | Adapter ops, error codes, DTO shape | New `public_contract_version` / `contract_id` lineage. CI fails if the API changes **without** that bump. |
| **Publication Contract Identity** | Frozen tuple on a ledger row | Stays forever. Historical publications are **not** rewritten. |

A new live `public_contract_version` **must not** invalidate old publication versions if the serving adapter still **declares** support for that identity lineage.

Compatibility tuple means:

> This exact combination (`manifest_version` × `public_contract_version` × `adapter_version` [× Builder surface version when C3 exists]) is **declared compatible**.

It does **not** mean “all four numbers must be identical” and it does **not** mean “every historical publication must jump to the latest API.”

The feat PR owns a **Forms-owned closed set of allowed tuples**. Fail-closed: undeclared combinations fail CI / runtime. Adapter may serve **multiple** frozen lineages.

This is **not** a new global registry framework. C2 does not extract a platform Compatibility Kit. If a second platform capability later needs the same model, that is the two-consumer test for extraction — not this slice.

**Forbidden:** mixed *undeclared* identity (Manifest v1 + Public Contract v2 + Adapter v3 + Builder v1 with no row in the table).

---

## Contract gates (CI — mandatory)

Named CI steps. Full-repo pytest red does not waive them.

### 1. Manifest Gate

- Unknown keys (not in sealed Manifest).  
- Removed required keys.  
- Structure / type / scope violations.  
- Incompatible `manifest_version` vs sealed baseline.

C1 froze the key **set**. C2 adds compatibility across versions (additive keys only with version bump; removals / type changes = fail).

### 2. Public Contract Gate

- Public Contract **API** ops / error codes / DTO shape vs sealed baseline.  
- Change **without** raising `public_contract_version` / `contract_id` lineage → **CI fail**.  
- Additive (new optional field, new Experimental event) requires an explicit version note; breaking change requires a new contract id.  
- This gate versions the **API**. It does **not** rewrite historical publication identities.

### 3. Adapter Gate

- Adapter implements exactly the Public Contract ops it claims.  
- Adapter must not accept payloads or keys absent from the **publication version’s** frozen schema + the contract lineage it was frozen under.  
- Serving adapter must **declare compatibility** with the publication’s `adapter_version` / identity lineage. It need not be the same numeric version as the live API.  
- Adapter must not accept what is not in the contract (no extra-contract fields).

### 4. Contract Identity Gate (primary)

- `publish` (freeze) persists a complete Contract Identity on the **new** publication version.  
- `resolve` of a publication version returns that identity (plus mutable `lifecycle_status`).  
- `submission` persists an immutable reference to that publication version and its identity; validation uses **that** frozen schema.  
- Live Builder **draft** is not required to carry a frozen identity tuple.  
- `schema_hash` matches canonical SHA-256 of that version’s `field_schema`.  
- Identity combination is in the declared compatibility table.  
- `object_kind` is the same platform kind for every publication of that type (no module-local dictionary).  
- Mutation of identity / `field_schema` / `schema_hash` on an existing ledger row fails.

---

## In scope (this docs PR)

1. This brief (identity vs lifecycle; publication vs draft; canonical hash; declared compatibility; version immutability).  
2. Queue / roadmap / AGENTS / C1 / Product Layer epic name C2 as **next** after C1; lock Phase C ladder C1→C6.  
3. Builder remains **locked until C2 feat PASSes** — not until “platform feels ready”.

## Feat implementation order (mandatory)

Do **not** start with CI gates or backfill. Runtime contract first, gates last.

1. `FormPublicationVersion` as frozen runtime-record: snapshot `field_schema` + immutable Contract Identity.  
2. Canonical serialization RFC 8785 JCS + SHA-256; forbid schema/identity mutation after freeze.  
3. Compatibility matrix `manifest_version` × `public_contract_version` × `adapter_version` — Forms-owned closed set, fail-closed. **Not** a global registry.  
4. Bind `resolve` to a specific publication version; check identity **and** lifecycle (lifecycle gates the operation, not the identity).  
5. Bind `publish` to freeze a **new** version — never mutate an existing ledger row.  
6. Bind `submission` to an immutable reference of that publication version.  
7. **Then** four named CI gates on the real runtime contract.  
8. **Last:** backfill legacy snapshots. Reconstruct identity **provably**, or fail-close. No `unknown` / `legacy but accepted`.

After C2 PASS:

- **C3** edits mutable `FormDefinition`.  
- **C4** serves frozen `FormPublicationVersion`.  
- **C5** executes and accepts data only against that pinned version.

## In scope (feat PR — after C1 merge + this brief)

1. Follow the order above.  
2. Additive Public Contract: identity on publication/submission DTOs; bump API version if required fields are new.  
3. Architecture Review Checklist in the feat PR description.

`TenantLeadForm` may remain the storage bridge; identity is **projected onto** the publication version, not a second form engine. Conceptual `FormDefinition` / `FormPublicationVersion` / `FormSubmission` do **not** require a FormTemplate cutover in C2.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| C3 Builder Runtime (editor of FormDefinition) | ✅ [#244](https://github.com/igortatarynovich/HostFlow/pull/244) |
| C4 Form Runtime / C5 Form Execution / C6 Optimization | [C4 brief](forms-platform-c4-form-runtime.md) |
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
| **C3** | Builder Runtime (edits **FormDefinition**) | Unlocked |
| **C4** | Form Runtime | — |
| **C5** | Form Execution (submissions pin a publication version) | — |
| **C6** | Optimization | — |

C3 is an **editor of definitions**. An editor must not open until the **publication format** it freezes is protected. C3 must not freeze a new identity on every keystroke.

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Forms **platform** (ADR-007) — not a product module |
| 2 Exists? | Yes — C1 seals ids; C2 enforces identity on publication versions |
| 3 Adapter | `forms.endpoint_adapter_v1` (**Stable**); C2 pins `adapter_version` **at freeze** and declared compatibility thereafter |
| 4 Boundary | No Builder C3, no module-owned form stacks, no Outcome/KPI |
| 5 Settings | Manifest Gate only; no new product settings UI |
| 6 SoT | Publication **version** identity on Forms ledger; lifecycle separate; modules consume Adapter |
| 7 Events | Unchanged Experimental this slice |
| 8 Requires | Endpoint, Submission; `object_kind` from Public Contract (RFC if new L0 kind) |
| 9 License | None new |
| 10 Public contract | **Additive** identity block on publication/submission DTOs; API version bump if required fields are new. Historical publications stay on their frozen identity. |

Does **not** amend L0 P-rules. Passport status only.

---

## Acceptance

- Product Track next after C1 = this brief.  
- No **publication version** can be frozen / resolved / submitted against without a complete Contract Identity.  
- `lifecycle_status` is not part of that identity; changing it does not mint a new identity.  
- Draft / FormDefinition is not required to carry a frozen identity tuple.  
- `schema_hash` is RFC 8785 JCS + SHA-256 of frozen `field_schema`.  
- Compatibility is a **Forms-owned closed set of tuples** (not a platform registry); a new Public Contract version does not invalidate historical publications the adapter still supports.  
- Existing publication versions are immutable (schema + identity); schema change = new version.  
- Four gates are named CI.  
- Builder stays locked until C2 feat PASSes.  
- Recruitment / HR / Fleet / Finance / Services still have **zero** private form runtimes.

---

## Likely files (feat PR)

| Area | Paths |
|------|--------|
| Identity + freeze | `forms_platform/publication_versions.py`, `adapter.py`, envelope |
| Canonical hash | shared encoder (JCS + SHA-256); used by publish / resolve / submit / CI |
| Compatibility | Forms-owned closed tuple set (`forms_platform/compatibility.py`) — not a platform registry |
| Gates | `backend/tests/forms_platform/test_forms_c2_*_gate.py` |
| CI | `.github/workflows/backend-ci.yml` named steps |
| Contract | `forms-public-contract.md` identity + hash + compatibility (additive) |

---

## DoD

- [x] Brief sealed with identity vs lifecycle, publication vs draft, canonical hash, declared compatibility, version immutability  
- [x] Queue + roadmap point at C2 as next after C1; Builder locked until C2  
- [x] Platform (not product module) posture explicit  
- [x] Feat PR after C1 merge ([#242](https://github.com/igortatarynovich/HostFlow/pull/242))  

---

## History

- 2026-08-13: Sealed C2 as next after C1 (identity + four gates + C1–C6).  
- 2026-08-13: Correction — `lifecycle_status` out of identity; identity on publication version only; JCS+SHA-256; declared compatibility; publication version immutable.  
- 2026-08-14: Feat order locked (runtime → gates → fail-closed backfill). Compatibility matrix stays Forms-owned; C3/C4/C5 boundary after PASS.  
