# ADR-037: Lifecycle Identity Canon

**Status:** Accepted (canon sealed; runtime not started)  
**Date:** 2026-08-23  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`lifecycle-identity-canon.md`](lifecycle-identity-canon.md) · [`process-engine.md`](../platform/process-engine.md) · [`module-owned-pipelines-p0.md`](module-owned-pipelines-p0.md) · [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md) · [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) · [`ADR-018`](ADR-018-requirement-policy-evaluation-model.md) · [`ADR-023`](ADR-023-recruitment-sales-module-separation.md) · [`ADR-025`](ADR-025-standard-adapter-boundary.md) · [`ADR-026`](ADR-026-capability-ownership.md) · [`handoff-contract.md`](handoff-contract.md) · queued brief [`lifecycle-identity-l0-contract-seal.md`](../tasks/lifecycle-identity-l0-contract-seal.md)

**L0 checklist:** No new P-rule; no Passport/Manifest shape change; no Architecture RFC. Applies **P-01** (adapter boundary), **P-02** (one owner), **INV-01** (one SoT), **INV-07** (compose, do not fork engines), **INV-16** (decision priority). Process Engine Catalog **Owns** stays evaluator / rules / profiles; this ADR **clarifies Non-Goals** (stage existence). Does not rewrite L0.

**Does not supersede:** ADR-002 (Recruitment ↛ Employee lifecycle), ADR-023 (Recruitment ↛ Sales Inquiry), module-owned-pipelines P0 (company-scoped funnel **configuration**). Amends *how* those boundaries are encoded: HR/Sales codes must not live as identities on another module’s entity.

---

## Context

HostFlow already has company-scoped `funnels` / `funnel_stages` (Recruitment P0, HR employee P0) and Process Engine system stages (`recruitment.*`, `hr.*`). Runtime still treats several independent lists as if they defined **what a stage is**:

- `constants/stages.py` + `/meta/stages` groups
- `FunnelStage.code` (free string)
- `LeadStage` Literal + frontend CRM lists
- Sales Application UI (`contacted | qualified | lost`) dual-writing `Lead.stage`
- `Company.client_stage` frontend list
- `candidate_stage_dict`
- vacancy `profile_stages`
- PE `pe_maps_to_*` (gate mapping, not existence)

That is the Country Registry failure mode: several physical lists, **no single owner of existence**. Declaring `funnels` the SoT would mint a **company catalog** — a fork per company, not a platform identity.

`Candidate.stage` historically became a process timeline across Recruitment → HR → client processing (`ready_for_hr` → `processing_by_hr` → `hired` → `processing_by_client`). ADR-002 already forbids Recruitment owning Employee lifecycle; the remaining leak is **identity on the same axis**.

Process Engine §3.1 “System Stage Registry” is close, but identity is `module.code` (no `entity_kind`), and the Recruitment manifest still registers `processing_by_hr` / `hired` / `processing_by_client` as **recruitment** stages. PE also mixes identity with template, terminal, and analytics bucket — the `COUNTRIES_IMMUTABLE` problem.

---

## Decision

### 1. Four contracts (do not collapse)

| Contract | Question | Must not own |
|----------|----------|----------------|
| **Module Stage Registry** | Does `{module}.{entity_kind}.{stage_key}` exist? | Company order, labels, gates |
| **Company Funnel Instance** | Which registered keys does this company use, in what order, with which allowed overlay? | Existence |
| **Process Engine** | Is this transition allowed, and what happens (template, requirements, evaluator)? | The list of identities |
| **Handoff / Conversion** | What is created/activated in **another** entity/module lifecycle? | A FunnelTransition on the source entity |

UI shows a **resolved projection** of funnel instance + registry labels + PE verdict. UI must not mint identity.

This is the same split as Document Type Registry (existence) vs policy pack (requirements) vs evaluator (verdict) — [ADR-018](ADR-018-requirement-policy-evaluation-model.md).

### 2. Canonical stage identity

```text
{module_key}.{entity_kind}.{stage_key}
```

Example: `recruitment.candidate.ready_for_handoff`.

- `module_key` — ADR-004 product key (`recruitment`, `sales`, `hr`, `fleet`, …).
- `entity_kind` — lifecycle-managed entity **inside** that module (`lead`, `candidate`, `application`, `client`, `employee`, …). Not a global enum of `lead | candidate | client` without module.
- `stage_key` — stable slug unique **within** `(module_key, entity_kind)`.

`qualified` in Recruitment Lead and `qualified` in Sales Application are **two identities**. Same local slug is allowed; shared business semantics are not implied.

### 3. Existence owner

For any `(module_key, entity_kind, stage_key)` there is exactly one authoritative answer: **registered / not registered**.

Only the **owning module’s Stage Registry** may register that identity (platform seed via module manifest / registry loader). The following **must not** create identity:

- funnel presets / bootstrap
- `funnel_stages.code`
- `constants/stages.py`
- frontend literals
- PE mapping / templates / analytics buckets
- vacancy `profile_stages`
- tenant `candidate_stage_dict`
- alias tables (aliases **point at** a registered key)

Physical storage of the registry may be JSON → loader → DB seed (one SoT + projections). Multiple tables are allowed; **one existence owner** is not optional.

### 4. Funnel is configuration, not a catalog

`funnels` / `funnel_stages` remain the **company-scoped process configuration** primitive (shape, resolver, validation) from [module-owned-pipelines-p0.md](module-owned-pipelines-p0.md).

A funnel row belongs to **exactly one** `(module_key, entity_kind)`. A `funnel_stages` row **references** a registered stage key; it does not assert that the stage exists.

Company may (within canon):

- include/exclude registered keys for that entity kind
- set order
- overlay display label
- overlay allowed lifecycle attributes (initial / terminal / outcome) **if** the registry permits overlay on that attribute

Company must not:

- invent `random_stage_x`
- attach `hr.employee.active` to a Recruitment Candidate funnel
- attach `sales.application.qualified` to a Recruitment Lead funnel

### 5. Process Engine is mechanism

PE **consumes** registered stage keys. It owns transition/handoff **rules**, process profiles, pipeline templates as **maps_to registry keys**, and the evaluator.

PE `system_stage` rows that today mix identity + `template_id` + `terminal` + analytics bucket are a **strangler**. Target axes:

| Axis | Owner |
|------|--------|
| Identity | Module Stage Registry |
| Lifecycle attributes | Registry defaults; optional company overlay |
| Analytics mapping | Declared mapping (not identity) |
| Presentation | Funnel overlay / UI projection |
| PE semantics | Templates, transition rules, evaluator hooks |

Do **not** mint a third existence catalog beside PE *and* this registry. First runtime must either (a) promote PE system-stage rows into registry identities **with `entity_kind`**, stripping template/analytics from identity, or (b) keep PE templates keyed by registry id. Canon forbids both claiming existence.

### 6. Handoff / Conversion ≠ FunnelTransition

Cross-module / cross-entity moves are **Handoff** or **Conversion** ([`handoff-contract.md`](handoff-contract.md), PE handoff evaluator). They are not `from_stage → to_stage` on one machine.

Recruitment Candidate lifecycle **ends inside Recruitment** (terminal or handoff-ready stage). Then PE Handoff may create/activate `hr.employee.*`. `hired` on Candidate is **not** `hr.employee.active`.

Sales: `sales.application.*` and `sales.client.*` are new namespaces. `Lead.stage` and `Company.client_stage` become **legacy projections** until cutover deletes them. Recruitment Lead identity must not be reused as Sales lifecycle SoT ([ADR-023](ADR-023-recruitment-sales-module-separation.md)).

### 7. Custom stages — out of first runtime

**P0 / first slices:** company selects and configures **only** registered module stages. No tenant extension registry.

If product later needs custom stages, that is a **separate ADR**: `tenant:{scope}.{module}.{entity_kind}.{key}` with mandatory semantics/transition/analytics rules. A free string on `funnel_stages` is never that model.

### 8. Which entities are funnel-managed

Each module **declares** which of its entities have a configurable lifecycle. Not every status field is a funnel stage (availability vs technical vs assignment on Fleet; `Lead.status` vs stage). Fleet/Finance entities are **not** registered until the module declares them.

Declared namespaces (existence catalog may be empty until the module’s registry slice):

| Identity prefix | Owner module | Notes |
|-----------------|--------------|--------|
| `recruitment.lead.*` | Recruitment | Acquisition lead lifecycle — not Sales |
| `recruitment.candidate.*` | Recruitment | Ends at Recruitment terminal / handoff-ready |
| `sales.application.*` | Sales | SalesInquiry product lifecycle |
| `sales.client.*` | Sales | ClientAccount / party client lifecycle |
| `hr.employee.*` | HR | Independent of Candidate.stage |

---

## Architecture review (ten questions)

| # | Answer |
|---|--------|
| 1 Owner | **Module** owns stage identities for its `entity_kind`. **Platform Funnel primitive** owns configuration shape + resolver. **Process Engine** owns evaluation/rules. |
| 2 Existing capability? | Extends Process Engine + Funnel P0; does **not** add a sold product. Clarifies existence vs configuration vs evaluation. |
| 3 Adapter | Later public contract (queued); no new adapter in this ADR. |
| 4 Boundary | PE Non-Goals += stage existence. Funnel Non-Goals += minting identity. |
| 5 Settings | Company funnel overlay stays CMS / funnels API; no second settings SoT. |
| 6 SoT | One existence SoT per `(module, entity_kind)`. Funnel and PE are not existence SoT. |
| 7 Events | No new Catalog event. Handoff/conversion events stay module/PE contracts. |
| 8 Requires | Process Engine (mechanism); module manifests. |
| 9 License | None — platform composition (INV-07). |
| 10 Public contract | Additive later. This ADR is canon only; no breaking runtime. |

---

## Consequences

- **Immediate (docs):** `FunnelStage.code` is not allowed to be described as stage identity. New stage literals in product PRs are a process fail unless they reference a registered key (enforced when the queued existence test lands).
- **ADR-002:** boundary stands; encoding HR progress as Candidate stage codes is **strangler**, not target. Recruiter still must not PATCH HR-owned work; target is Handoff → `hr.employee.*`, not a longer Candidate lane.
- **Sales:** dual-write `Lead.stage` is strangler. Product SoT for inquiry lifecycle is `sales.application.*` after the Sales registry slice.
- **Runtime** is **not** authorized by this ADR alone. Slices go on the [sequential queue](../tasks/sales-to-comms-sequential-queue.md) **after** Entity Field Composition CL0. Do not start Funnel Engine “universalization”, Candidate UI cutover, or Country-style union of current lists as canon.
- **No INV-18** in [`architecture-invariants.md`](architecture-invariants.md) (L0 freeze). The existence rule lives in this ADR until an Architecture RFC promotes it.

---

## Alternatives considered

| Alternative | Reject |
|-------------|--------|
| `funnels` / `FunnelStage.code` as SoT | Per-company catalogs; same fork as historical country lists |
| Current PE `module.code` as SoT as-is | No `entity_kind`; Recruitment manifest still holds HR/client identities; identity mixed with templates |
| Global `entity_type = lead \| candidate \| client` | Cross-module name collision; violates module independence (P-02 / ADR-004) |
| Custom codes on funnel rows in P0 | Unregistered identity; analytics/PE cannot bind |
| Start Candidate/Sales UI cutover now | Moves dictionaries without an existence owner |

---

## Cross-references (updated with this ADR)

- [`lifecycle-identity-canon.md`](lifecycle-identity-canon.md) — L2 operating contract
- [`process-engine.md`](../platform/process-engine.md) §3.1 — PE ≠ existence owner
- [`module-owned-pipelines-p0.md`](module-owned-pipelines-p0.md) — funnel = configuration
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)
- [`platform-capability-catalog.md`](platform-capability-catalog.md) — Process Engine Non-Goals
- [`platform-architecture-principles.md`](platform-architecture-principles.md) §6
- [`../../recruitment/module-scope.md`](../../recruitment/module-scope.md)
- [`../../hr/module-scope.md`](../../hr/module-scope.md)
- [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md) — strangler note
- Queue / roadmap: [`lifecycle-identity-l0-contract-seal.md`](../tasks/lifecycle-identity-l0-contract-seal.md)

---

## History

- 2026-08-23: Accepted — Lifecycle Identity Canon; Module Stage Registry owns existence; Funnel = company configuration; PE = mechanism; Handoff ≠ FunnelTransition; custom stages out of first runtime; implementation queued after CL0.
