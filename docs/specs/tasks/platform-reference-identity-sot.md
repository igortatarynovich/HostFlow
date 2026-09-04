# Platform Reference Identity SoT (R1–R5)

**Status:** **PASS** (R1–R5 Gates PASS; Reference Program Exit Gate **PASS** [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c`; Engineering = **DONE**)  
**Phase class:** platform  
**Branch (docs):** `docs/platform-reference-r1-gate-seal`  
**Branch (code):** R1–R5 + Exit merged  
**Track:** **Engineering DONE** (no named successor this amendment; pytest stays background)  
**Parents:** [Platform Completion Roadmap § Phase E](../architecture/platform-completion-roadmap.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Entity Field Composition CL0](entity-field-composition-cl0-contract-seal.md) (parallel Product while R1 ran) · [REF-4 Phase 1 closeout](../gates/ref4_phase1_final_closeout.md) · [REF-4 Phase 2 start gate](../gates/ref4_phase2_start_gate.md) · [Reference delivery contract](../reference_delivery_contract_standard.md) · [Reference layer architecture](../architecture/reference-layer-and-applicability-packs.md) · [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md) · [`document-type-registry-v1.json`](../platform/document-type-registry-v1.json) · [`document-type-legacy-aliases-v1.json`](../platform/document-type-legacy-aliases-v1.json) · [Document type model standard](../architecture/document-type-model-standard.md) · [AGENTS.md](../../../AGENTS.md) (Architecture Rule 1)

> **R1–R5 Gates PASS** — Country Registry, runtime cutover (R2), document identity (R3), alias consolidation (R4), policy merge (R5). **Reference Program Exit Gate PASS** [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c`. Engineering = **DONE**.  
> **E8-eval Gate PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6` after E8 Canonical Type Bind Gate PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f`. RPM program **DONE**. Product = **[MA-1](mapping-authority.md)** (brief; feat locked). OCR stays locked.

**Naming (do not collapse):** this program is **Reference R1–R5**. It is **not** Documents E8, not Entity Field Composition CL0, not **Epic C residual R1** (C2.4 freeze), not Acquisition R6, not a second document-type catalog in `definitions.py`, not REF-4 Phase 1 re-open, not REF-4 Phase 2 (that is **Reference R2**), not tenant-owned document type lists, not a monolithic “catalog of everything”, not L0 Catalog rewrite, not Billing / AI / Forms P3–P5.

---

## Why this program

Runtime today answers the same questions from different places:

| Question | Current risk |
|----------|----------------|
| Does country `XX` exist? | `constants/catalogs.py`, `core_immutable_catalogs` (3 rows), frontend `COUNTRY_CODES`, dead `countries` table |
| Dial code for `PL`? | `DIAL_CODES` dict — not tied to identity contract |
| Does document type `foo` exist? | `document-type-registry-v1.json`, `document_reference_sync._seed_types()`, `definitions.py`, `legal_document_catalogs` stub |
| Is `residence_permit` = `residence_card`? | Scanner, frontend `EQUIVALENT_TYPE_GROUPS`, module packs — independent answers |
| Must candidate provide `residence_card`? | Tenant ruleset JSON, `sample_ruleset.json`, packs, applicability policy — parallel policy engines |

Without R1–R5 the Platform Reference Layer becomes **documentation-only** while modules keep forking dictionaries — violating Architecture Rule 1 and ADR-018.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After R1–R5, **no module, API, or frontend path** may treat a local dict, tenant row, or module file as the **authoritative definition** of country identity, document type identity, or document policy semantics. Each domain has exactly one owner; all other representations are **projection**, **overlay**, or **alias normalization**.

**Completion proof (named consumer):**  
**ReferenceServiceFacade + `/catalogs/*` + Requirement Evaluation path** for Recruitment candidate document checklist:

1. Country/dial options served only from **Country Registry** projection (R2 gate).  
2. Document type existence resolved only from **`document-type-registry-v1.json`** → `ref_document_types` (R3 gate).  
3. Required document types for a candidate context resolved only from **resolved policy** (`merge(platform_pack, tenant_delta)`) → evaluator (R5 gate).  
4. Five architectural questions (below) have **one** answer each — enforced by convergence guards.

```text
Authoritative definition (one per domain)
  → deterministic seed / migration (projection)
  → facade / API DTO (delivery)
  → module consumer (read-only)
```

**False close (reject):** union of legacy lists declared canon without ISO validation; `OTHER` in Country Registry; unique constraint on `dial_code`; tenant `document_types` as existence SoT; tenant full ruleset fork; `definitions.py` minting new types; `immutable` in new public API; reference layer executing policy; mixing R1 with CL0 / E8 in one PR.

---

## Authoritative-definition principle

For every domain:

| Role | Meaning |
|------|---------|
| **Authoritative definition** | Single owner of semantic identity / policy base |
| **Projection** | Materialized read model (DB seed, API, facade DTO) — **not** a second SoT |
| **Overlay** | Tenant-scoped **delta** on top of platform base — bounded, auditable |
| **Alias boundary** | Input normalization only — never policy, never existence |

**Allowed physical representations:** JSON registry → DB tables → API response.  
**Forbidden:** two independent editors of the same meaning without merge contract.

### Domain ownership table

| Domain | Authoritative definition | Runtime projection | Overlay / alias |
|--------|------------------------|--------------------|-----------------|
| Country identity | **Platform Country Registry** | `ReferenceServiceFacade`, `/catalogs/countries*` | — |
| Country dial / EU / Schengen | **classifications** on same registry entry | same APIs | classifications may change over time |
| Document type **existence** | [`document-type-registry-v1.json`](../platform/document-type-registry-v1.json) | `ref_document_types`, facade | — |
| Document type **module config** | module catalog (`definitions.py`) | tenant presentation rows | labels / UI only; `canonical_ref_code` required |
| Document **policy** | versioned **platform rule packs** | resolved ruleset DTO | tenant delta |
| Tenant customization | overlay tables / JSON delta | merged view | not fork |
| Legacy codes | [`document-type-legacy-aliases-v1.json`](../platform/document-type-legacy-aliases-v1.json) | normalization at API boundary | forbidden in evaluator matching |

**Tenant rule:** tenant stores **rule sets / overlays**, not a private catalog of document types. Document types belong to the **platform**.

---

## Three-layer contract (Reference → Policy → Evaluation)

```text
Reference    — what exists (country, document type identity)
Policy       — what is required (packs + tenant delta)
Evaluation   — is requirement satisfied (requirement_rules / evaluator)
```

| Layer | Answers | Must not |
|-------|---------|----------|
| **Reference** | existence, labels, classifications | execute rules, decide required docs |
| **Policy** | applicability, required/optional/blocked | mint document type codes |
| **Evaluation** | verdict, blockers, evidence | own registries |

`requirement_rules` **executes** policy; it does **not** own country or document type catalogs (ADR-018).

---

## Country Registry contract

### Terminology guard (mandatory)

- **Do not** use `immutable` in **new** public/domain API names or DTO fields.  
- Legacy `core_immutable_*` paths are **transitional implementation shims** only until R2 cutover removes them.  
- New contract vocabulary: `country_registry`, `country_reference`, `identity`, `classifications`, `labels`.

### Identity block (ISO anchor)

Per country:

- `alpha2`, `alpha3`, `numeric` — canonical identity keys  
- `labels`: minimum **`en`**, **`pl`**, **`ru`** (do not regress below existing `name_pl` / `name_en` coverage)

**Invariant:** registry identity set ⊆ **official ISO 3166-1 alpha-2** approved set.

### Classifications block (same entry, separate contract semantics)

Not identity — may change over time:

- `dial_code` — attribute of country; **not** identity  
- `eu_member`, `schengen_member` (future: `eea_member`, `efta_member` same block)

**Dial code invariants:**

- ✅ every dial option in UI/API originates from Country Registry  
- ✅ `PL → +48`, `US → +1`, `CA → +1`  
- ❌ **no** unique DB/API constraint on `dial_code`  
- ❌ **no** assumption dial_code → single country (frontend/backend)

### Exceptional identities (`approved_non_iso`)

Codes such as **`XK`** (Kosovo) are **not** in the R1 ISO-approved set.

- R1: **exclude** `XK` from canonical identity  
- R1 guard: discovery union must **not** auto-promote `XK` into canon  
- Future: explicit product decision may add `approved_non_iso` entries — separate gate, not discovery union

### `OTHER` — presentation only

`OTHER` is **not** a country. It may exist only as UI/input behavior (e.g. `withOtherCountryOption`) — **never** in Country Registry.

### Migration discovery vs canon

Union of legacy lists (`constants/catalogs.py`, `DIAL_CODES`, frontend `COUNTRY_CODES`) is **discovery input only** — to determine coverage gaps.

**Canon validation:**

- subset of official ISO alpha-2 (plus explicit `approved_non_iso` when later approved)  
- `UK` → alias to `GB`, not parallel identity  
- deprecated ISO codes — explicit decision, not auto-inclusion  
- discovery union **cannot** extend canon automatically

### Implementation note (R1)

Single module file acceptable (e.g. `country_registry.py`) if contract exposes `identity` | `classifications` | `labels` separately in facade DTO — physical unity ≠ semantic unity.

---

## Document Type Registry ownership

**Existence SoT:** [`document-type-registry-v1.json`](../platform/document-type-registry-v1.json) (ADR-018).

Flow:

```text
document-type-registry-v1.json
  → registry loader (backend/app/document_types/registry.py)
  → ref_document_types (DB projection)
  → module definitions / scanner / UI (configuration & aliases only)
```

### `definitions.py` — configuration only

After **R3**, a row in `document_types/definitions.py` is allowed **only** with `canonical_ref_code` ∈ registry.

It may own:

- supported fields, UI schema, file behavior, extraction, module presentation

It **must not** assert:

- “this document type exists” — **existence belongs to registry only**

### Tenant `document_types` table

Tenant rows are **overlay** (labels, enablement, presentation) — **not** existence SoT. Platform seeds types; tenant does not maintain a private type encyclopedia.

### Deprecated parallel catalogs (convergence targets)

| Artifact | R3+ fate |
|----------|----------|
| `legal_document_catalogs.DOCUMENT_TYPES_CANONICAL` | remove or read-only projection from registry |
| `document_reference_sync._seed_types()` hardcoded list | generate from registry JSON |
| `constants/documents.py` `DEFAULT_DOCS` | delete |
| scanner `DOCUMENT_TYPES` own codes | alias map only (R4) |

---

## Policy layer — tenant overlay ≠ fork

### Merge semantics (R5 acceptance)

```text
Platform rule pack     → base policy
Tenant overlay         → allowed delta only
Resolved policy        → deterministic merge(base, overlay)
```

**STOP:** tenant `document_ruleset_versions` row that is a **complete independent ruleset** (fork).

Tenant stores **rule set references + deltas**, not a parallel policy encyclopedia.

`sample_ruleset.json` = **platform pack seed/fixture**, not a second runtime evaluator.

Pack `document_codes` ⊆ registry codes (CI guard).

EU / oświadczenie country sets ⊆ Country Registry `classifications` — no module-local `EU_COUNTRIES` frozensets after R5.

---

## Alias-boundary rule

[`document-type-legacy-aliases-v1.json`](../platform/document-type-legacy-aliases-v1.json):

| Allowed | Forbidden |
|---------|-----------|
| API input normalization | requirement evaluation matching |
| migration / audit | pack policy identity |
| sync `document_type_id` resolution | scanner minting parallel canonical codes |

Scanner and frontend equivalence groups (**R4**) must derive from alias registry — not invent taxonomy.

---

## Five architectural questions (convergence gate)

After R1–R5, each question must have **exactly one** authoritative answer:

| # | Question | Sole authority |
|---|----------|--------------|
| 1 | Does country `XX` exist? | Country Registry |
| 2 | What is the dial code for `PL`? | Country Registry (`classifications`) |
| 3 | Does document type `foo` exist? | Document Type Registry |
| 4 | Is `residence_permit` the same type as `residence_card`? | Registry + alias registry |
| 5 | Must this candidate provide `residence_card`? | Resolved policy → evaluator |

**Fail:** two independent modules answer differently.

---

## Slice ladder (Reference R1–R5)

```text
Reference R1 → { Reference R2 ∥ Reference R3 } → R3 → Reference R4
  → (R2 PASS ∧ R4 PASS) → Reference R5 → Reference Program Exit Gate
```

Fan-out is **only** `{R2, R3}`. R5 is **not** a third concurrent Engineering slice.

| Slice | Focus | Track | Depends on | Unlocks |
|-------|--------|-------|------------|---------|
| **Reference R1** | Country Registry completeness (identity + classifications contract); facade snapshot; ISO validation; no runtime cutover | Engineering | REF-4 Phase 1 ✅. **Not** REF-4 Phase 2 start gate | fan-out {R2, R3} |
| **Reference R2** | Country runtime cutover — `/catalogs/*`, frontend lists killed; dial from registry. **This slice is REF-4 Phase 2 country adoption**. Proof: Q1–Q2 | Engineering | **Reference R1 Gate** | R5 join (with R4) |
| **Reference R3** | Document identity — registry JSON sole existence; seed sync; kill parallel stubs. Proof: Q3 | Engineering | **Reference R1 Gate** (parallel R2) | Reference R4 |
| **Reference R4** | Alias consolidation — scanner, UI equivalence, legacy paths. Proof: Q4 | Engineering | **Reference R3 Gate** | E8-bind unlock; R5 join (with R2) |
| **Reference R5** | Policy merge — packs + tenant delta; overlay ≠ fork; pack codes ⊆ registry. Proof: Q5 only | Engineering | **Reference R2 Gate ∧ Reference R4 Gate** | E8-eval unlock; DR1-runtime unlock; Program Exit |
| **Reference Program Exit Gate** | Q1–Q5 answered by one chain | Engineering | **Reference R5 Gate** | Reference program DONE |

**Parallelism (only this):**

- **CL0** (Product) continues independently while R1 has **no** runtime cutover.  
- **Reference R1** may run **now** (parallel CL0).  
- After **Reference R1 Gate**: fan-out **{R2 ∥ R3}** only. Then collapse.  
- **E8-bind** **PASS** [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f`.  
- **E8-eval** **PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6`. Does **not** start OCR. RPM program **DONE**. Product = **[MA-1](mapping-authority.md)** (brief; feat locked).  
- **DR1-runtime** is **PASS** [#313](https://github.com/igortatarynovich/HostFlow/pull/313). It does **not** park later CL (CL2+ already PASS).

### R1 gate (named)

**Reference R1 Country Registry Gate**

Pass requires:

1. Full ISO-approved country set in registry (discovery-informed, ISO-validated).  
2. Facade exposes `identity` | `classifications` | `labels` — no `immutable` in new public fields.  
3. Labels include `en`, `pl`, `ru`.  
4. Guard: `XK` ∉ canon; `OTHER` ∉ registry; no unique `dial_code` constraint.  
5. Zero runtime consumer cutover (catalogs.py untouched as SoT).  
6. Reference tests green; seed checksum deterministic.

---

## Convergence guards (final enforcement)

CI / guard tests (introduced incrementally; full set required at R5 close):

| Guard | Introduced |
|-------|------------|
| No second `COUNTRIES` / `DIAL_CODES` dict as runtime SoT | R2 |
| No frontend `COUNTRY_CODES` as identity fallback after cutover | R2 |
| `definitions.py` codes ⊆ registry via `canonical_ref_code` | R3 |
| `document_reference_sync` seeds ⊆ registry JSON | R3 |
| Pack codes ⊆ registry | R5 |
| No module `EU_COUNTRIES` frozenset | R5 |
| Tenant ruleset validates as overlay/delta schema | R5 |
| Five questions — single-answer integration test | Reference Program Exit Gate |

Existing: `backend/scripts/check_document_type_registry.py` — extend per slice.

---

## Explicit out-of-scope / STOP (all slices)

| STOP | Reason |
|------|--------|
| CL0 feat / Entity Profile runtime in R1–R5 PRs | Product track |
| Documents **E8-eval** before **Reference R5 Gate** and E8-bind | remaining consumers evaluate required docs; type identity alone is not enough |
| Documents **E8-bind** before **Reference R3 Gate ∧ R4 Gate** | bind needs canonical identity + alias boundary |
| Activating **Reference R5** while **Reference R2** is still open | fan-out window is only {R2, R3} |
| Hub request table / E7 semantics | closed ✅ |
| Reference layer executing policy | REF-4 Phase 1 rule |
| New document types without registry JSON change | ADR-018 |
| `immutable` in new public API | terminology guard |
| L0 Catalog rewrite | Architecture RFC only |
| Forms P3–P5, Billing, AI | roadmap locked |
| Mass D3–D9 documents bind | separate slices |
| Tenant-minted document types / `tenant_custom` during R1–R5 | deferred; strict mode only until a later named gate |
| Including `XK` in R1 ISO set | breaks registry ⊆ ISO invariant |

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Platform Reference (`platform-reference` / core) |
| 2 Exists? | REF-4 Phase 1 baseline ✅; runtime adoption incomplete — this program completes identity convergence |
| 3 Adapter | `ReferenceServiceFacade` + existing `/catalogs/*` (R2 cutover) |
| 4 Boundary | Reference passive; policy in packs; evaluation in requirement_rules |
| 5 Settings | No new tenant Manifest keys in R1 |
| 6 SoT | This brief — authoritative-definition table |
| 7 Events | No new Catalog events |
| 8 Requires | REF-4 Phase 1 PASS; ADR-018 registry JSON; CL0 not blocking R1 |
| 9 License | None new |
| 10 Public contract | No Documents public contract id bump in R1 |

Does **not** amend L0. Does **not** rewrite Catalog Passport.

---

## Acceptance (program close)

- [x] R1 gate PASS — Country Registry authoritative definition exists ([`country-registry-v1.json`](../platform/country-registry-v1.json); facade snapshot `identity` / `classifications` / `labels`)  
- [x] R2 gate PASS — no parallel country/dial runtime lists  
- [x] R3 gate PASS — document type existence = registry JSON only  
- [x] R4 gate PASS — scanner/UI use alias registry only  
- [x] R5 gate PASS — policy merge semantics; tenant overlay ≠ fork  
- [x] Five architectural questions — single answer enforced at **Reference Program Exit Gate** [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c`  
- [x] E8-bind unlock after R3∧R4; E8-eval unlock after R5 ∧ E8-bind; unlock ≠ schedule; CL0/E7 unaffected  

---

## History

- 2026-08-25: E8 Required-Doc Evaluation Gate PASS [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6`. Product = **none this amendment**. Engineering stays **DONE**. OCR stays locked.
- 2026-08-25: Queue amendment after E8-bind Gate PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` names **E8-eval** Active Product. Engineering stays **DONE**. OCR stays locked.
- 2026-08-25: Queue amendment after E8 Canonical Type Bind Gate PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f`. Product = **none this amendment**. Engineering stays **DONE**. E8-eval unlocked (not scheduled).
- 2026-08-25: Queue amendment after DR1 Runtime Gate PASS [#313](https://github.com/igortatarynovich/HostFlow/pull/313) names **E8-bind** Active Product. Engineering stays **DONE**. No named Engineering successor.
- 2026-08-25: Reference Program Exit Gate **PASS** [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c`. Engineering = **DONE**. No named successor this amendment. DR1-runtime becomes Active Product after Overlay Gate.
- 2026-08-23: R1 feat — full ISO 3166-1 Country Registry JSON + facade snapshot + seed checksum; `catalogs.py` remains runtime SoT; XK/OTHER/UK excluded from canon.
- 2026-08-23: Sequence sealed with queue — Engineering `R1 → {R2 ∥ R3} → R4 → (R2 ∧ R4) → R5 → Program Exit`. E8-bind / E8-eval split. DR1-runtime (not CL7) joins R5. REF-4 Phase 2 = R2, not R1. Always **Reference Rn**.
- 2026-08-23: Normative brief opened — Platform Reference Identity SoT R1–R5. R1 may run parallel CL0. XK excluded from R1 ISO set.
