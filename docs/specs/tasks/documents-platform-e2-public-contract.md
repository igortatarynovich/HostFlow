# Documents Platform E2 — Public contract & D2 slot enable (Phase E)

**Status:** **COMPLETE** ([#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276) · merge `826877b5`)  
**Next:** [Documents Platform E3](documents-platform-e3-first-consumer-bind.md) ✅ → [Documents Platform E4](documents-platform-e4-candidate-document-link.md) ✅ → [Documents Platform E5](documents-platform-e5-candidate-storage-bridge.md) ✅ → [Documents Platform E6 — Document Expiry / Validity](documents-platform-e6-document-expiry.md) (brief; feat locked)  
**Branch (docs):** `docs/documents-platform-e2-public-contract` ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271)  
**Branch (code):** `feat/documents-platform-e2-public-contract` ✅ [#276](https://github.com/igortatarynovich/HostFlow/pull/276)  
**Parents:** [Documents Platform E1](documents-platform-e1-contract-seal.md) [#269](https://github.com/igortatarynovich/HostFlow/pull/269)/[#270](https://github.com/igortatarynovich/HostFlow/pull/270) · [D2 Composition Contract](entity-workspace-d2-composition-contract.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase E](../architecture/platform-completion-roadmap.md) · [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · [ADR-014](../architecture/ADR-014-document-hub-access-model.md) · [ADR-025](../architecture/ADR-025-standard-adapter-boundary.md) · [Capability Contract](../architecture/capability-contract.md) · [Forms Public Contract](../architecture/forms-public-contract.md) (pattern) · [Document Hub scope](../../document-hub/module-scope.md) · [Catalog Documents](../architecture/platform-capability-catalog.md#documents) · [A2-F8](../gates/platform-governance-review-a2.md)

> E1 sealed ownership: Hub ≠ Candidate/HR dossier ≠ Shell `documents` nav ≠ D2 enable ([#270](https://github.com/igortatarynovich/HostFlow/pull/270) · merge `f37deff1`).  
> E2 seals **`documents.public_contract.v1`** and unlocks the D2 `documents` **catalog slot**.  
> E2 does **not** bind D3–D9 consumers, replace `candidate_id` with Document Link, open OCR / packages, or mark Foundation ✅.

**Naming (do not collapse):** this **Documents Platform E2** is not E1 contract seal, not a D-series consumer cutover, not Shell `documents` nav, not Candidate / HR dossier, not Recruitment document slots, not OCR / e-sign product, not document packages, not Billing Platform Phase F. Catalog unlock ≠ consumer bind. Document Hub remains a **platform capability** (ADR-009), **not** a sixth product module.

---

## Why this slice

E1 froze two holes on purpose: no sealed public-contract id, and D2 `documents` reserved. Without E2, the next PR will either treat the E1-era façade as `documents.public_contract.v1`, or flip every D3–D9 consumer onto a documents slot because “Phase E started”.

Shipped runtime vs canon after E1:

| Artifact | After E1 | Drift E2 closes |
|----------|----------|-----------------|
| Passport | Catalog [Documents](../architecture/platform-capability-catalog.md#documents) | Exposes unnamed; no `documents.public_contract.v1` |
| Manifest | [`capability-settings-manifest.md`](../architecture/capability-settings-manifest.md#documents) | Illustrative keys only — **unchanged this slice** |
| Public Contract | Catalog Exposes: Document Adapter / Verification Adapter / document set resolution (**Stable**) | No contract id (unlike Forms `forms.public_contract.v1`) |
| Adapter | `document_hub_delivery_contract.py` (E1-era façade) | No adapter id; not Document Link SoT |
| D2 slot | `compositionSlots.ts` `documents` **reserved** | Named unlock after E1 = this slice |
| Consumers | D3–D9 bind enabled slots **without** `documents` | Stay unbound; catalog unlock ≠ cutover |

[A2-F8](../gates/platform-governance-review-a2.md): Foundation stays 🔄 until public contract + lifecycle settle. E2 is contract + slot catalog — not Foundation close.

---

## Goal

Seal Documents **Public Contract v1** (ops + adapter id + events + invariants) and mark D2 `documents` as an **enabled platform slot** that consumers may compose **only via that contract**. D3–D9 slot lists stay without `documents` until a named later E slice. Do not invent a second document store.

This slice does **not** replace the candidate-owned row with Document Link, rebuild Hub UI, or treat Candidate/HR dossier as the D2 slot.

---

## Locked principle

```text
E1  → who owns Documents Platform + Hub ≠ dossier ≠ D2 enable
E2 (this)
  → documents.public_contract.v1 + documents.hub_adapter_v1
  → D2 documents catalog unlock (reserved → enabled platform slot)
  → D3–D9 consumers still omit documents
E3
  → first consumer bind (HR employee) / Document Link SoT ([documents-platform-e3-first-consumer-bind.md](documents-platform-e3-first-consumer-bind.md))
```

E2 **must not**:

- bind `documents` on Sales Inquiry / Candidate / Client / Sales Order / Vacancy / HR employee / Services order  
- collapse Shell `EntityWorkspaceSectionId` `documents` into `compositionSlots.ts`  
- treat Candidate docs panel / HR dossier / Vacancy docs / Services billing as the D2 slot  
- cut over `candidate_id` rows to Document Link SoT  
- mint Entity Catalog Passport or rewrite L0 Catalog shape  
- open OCR, e-sign, packages, approvals automation, or Hub UI rebuild  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- cut over `HrHandoffDetailPage`  
- invent a second document store or local type dictionary  
- copy files across Recruitment ↔ HR as the handoff path  
- mark Documents Foundation ✅ (stays 🔄)

---

## Public contract inventory (normative for feat)

Feat writes / wrote `docs/specs/architecture/documents-public-contract.md` (architecture supplementary; inbound from Catalog Exposes + this brief). Pattern: [`forms-public-contract.md`](../architecture/forms-public-contract.md).

| Field | Value |
|-------|--------|
| **Capability id** | `documents` |
| **Contract id** | `documents.public_contract.v1` |
| **Adapter id** | `documents.hub_adapter_v1` |
| **Implementation (E2)** | Existing `document_hub_delivery_contract.py` façade **bound** to those ids — still the candidate-centric bridge, **not** ADR-009 Document Link SoT |
| **Passport** | Catalog [Documents](../architecture/platform-capability-catalog.md#documents) — additive Exposes ids only |

### Stable operations (v1)

Catalog Exposes already name Document Adapter / Verification Adapter / document set resolution as **Stable**. E2 names the ops; it does not add OCR to the public surface.

| Op | Stability | Maps from façade (today) | Notes |
|----|-----------|--------------------------|--------|
| `list` / `resolve` | **Stable** | `list_candidate_documents_via_contract` | Entity-scoped read. E2 input may stay candidate-centric; output is Hub document view, not a module file row |
| `set_resolution` | **Stable** | `project_document_packs_via_contract` · `compute_candidate_checklist_via_contract` · `evaluate_document_hub_requirements_via_contract` | Document set / pack / checklist projection |
| `owner_summary` | **Stable** | `compute_owner_summary_via_contract` · `merge_document_hub_requirements_into_summary_via_contract` | Read model for compose |
| `verification_status` | **Stable** | Review fields on owner summary / list | Verification Adapter read — no new review engine |
| `list_types` | **Stable** | `list_document_types_via_contract` · `list_canonical_document_type_codes_via_contract` | Hub types only (Architecture Rule 1) |

**Not public v1 (Internal / deferred):** OCR internals · e-sign · `get_uploads_root` / `sanitize_filename` · reminder work-queue projection as a product API · ruleset seed writes · synthetic checklist row builders as a consumer API.

### Events

Catalog already publishes `document.created` / `linked` / `verified` / `expired`. E2 does **not** mint events or bump stability.

### Invariants

1. Modules consume **only** `documents.public_contract.v1` / `documents.hub_adapter_v1` — no `modules.documents.crud` imports from other modules (Architecture Rule 2).  
2. File is a version; Document is the business object (ADR-009). Handoff is **links + permissions**, never copy.  
3. Legacy `documents.candidate_id` remains a **bridge**, not Hub SoT.  
4. D2 `documents` slot, when a later slice binds it, renders via this adapter only — not Shell nav, not dossier pages.  
5. No new local type / status dictionaries.

### Catalog (additive only)

Feat may add contract/adapter ids under existing Documents **Exposes**. It must **not** change Catalog shape (Owns / Configures / Exposes / Consumes columns), mint Entity Workspace passport, or rewrite Notifications↔Communication (A2-F1).

---

## D2 enable (catalog unlock — not consumer cutover)

D2 already named `documents` as reserved until a named Phase E slice **after E1**. **This is that slice.**

| Layer | E1 | E2 (this) |
|-------|----|-----------|
| `ENTITY_WORKSPACE_SLOT_CATALOG` | includes `documents` | unchanged |
| `ENTITY_WORKSPACE_RESERVED_SLOT_IDS` | `['documents']` | **empty** |
| `ENTITY_WORKSPACE_ENABLED_SLOT_IDS` | without `documents` | **includes** `documents` |
| `ENTITY_WORKSPACE_SLOT_KIND.documents` | `platform-reserved` | `platform` |
| D3–D9 `*_COMPOSITION_SLOTS` | omit `documents` (throw if passed) | **still omit**; throw becomes “not bound this slice”, not “reserved” |
| Shell `EntityWorkspaceSectionId` `documents` | ≠ D2 slot | still ≠ D2 slot |

`EntityWorkspaceCompositionHost` may accept `documents` once it is in the enabled catalog. E2 feat did **not** add `documents` to any D3–D9 consumer slot list. First consumer bind = [E3](documents-platform-e3-first-consumer-bind.md) ✅ (HR employee). Candidate bind = [E4](documents-platform-e4-candidate-document-link.md) ✅. Storage-bridge retirement = [E5](documents-platform-e5-candidate-storage-bridge.md). D3 / D5–D7 / D9 stay unbound.

D2 / E1 / D3–D9 named gates stay in CI. E2 feat **amends** assertions that freeze E1-era “no contract id” and “documents reserved”. Ownership / Hub ≠ dossier / Shell ≠ D2 / Foundation 🔄 stay enforced.

---

## Phase E ladder

| Slice | Focus | Status |
|-------|--------|--------|
| **E1** | Contract seal (ownership / Hub ≠ dossier / D2 still reserved) | ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269)/[#270](https://github.com/igortatarynovich/HostFlow/pull/270) · merge `f37deff1` |
| **E2** | Public contract / D2 `documents` catalog enable | ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276) · merge `826877b5` |
| **E3** | First consumer bind (HR employee) + Document Link SoT | ✅ [#277](https://github.com/igortatarynovich/HostFlow/pull/277)/[#278](https://github.com/igortatarynovich/HostFlow/pull/278) · merge `cc106a38` |
| **E4** | Candidate Document Link bind (D4) | ✅ [#279](https://github.com/igortatarynovich/HostFlow/pull/279)/[#280](https://github.com/igortatarynovich/HostFlow/pull/280) · merge `0af74913` |
| **E5** | Candidate storage-bridge retirement (`candidate_id` drop) | ✅ [#281](https://github.com/igortatarynovich/HostFlow/pull/281)/[#282](https://github.com/igortatarynovich/HostFlow/pull/282) · merge `702b922c` |
| **E6** | Document expiry / validity | [brief](documents-platform-e6-document-expiry.md) (feat locked) |

Roadmap lifecycle themes (expiry, requests, packages, OCR, approvals, automation) stay **horizon**.

---

## In scope (this docs PR)

1. This brief.  
2. Close **Documents Platform E1** as **COMPLETE** after [#269](https://github.com/igortatarynovich/HostFlow/pull/269)/[#270](https://github.com/igortatarynovich/HostFlow/pull/270) (`f37deff1`).  
3. Point Product Track / queue / roadmap / AGENTS / maturity / Hub scope here.  
4. Amend D2 composition contract: reserved-until-after-E1 → unlock = E2. Feat locked until this brief merges.

## In scope (feat PR — after this brief)

1. `docs/specs/architecture/documents-public-contract.md` with the inventory above.  
2. Bind `PUBLIC_CONTRACT_ID` / adapter id on the existing delivery façade — no second Adapter.  
3. Additive Catalog Exposes ids; [`capability-contract.md`](../architecture/capability-contract.md) pointer.  
4. `compositionSlots.ts`: `documents` enabled platform slot; reserved empty.  
5. Named **Documents Platform E2 Public Contract Gate** — contract id + adapter id + D2 unlock + D3–D9 still unbound; E1/D1–D9 gates still green (amended where E1 froze “no id / reserved”); Documents Foundation stays 🔄.  
6. Architecture Review Checklist (10 questions) in the feat PR description.  
7. Pointers stay on E2 until E3 brief opens. ← done [E3 brief](documents-platform-e3-first-consumer-bind.md)

---

## Documents Platform E2 Public Contract Gate (CI — mandatory)

Named step: **Documents Platform E2 Public Contract Gate**  
(`tests/platform/test_documents_e2_public_contract_gate.py`). Full-repo pytest red does not waive it. E1 and D1–D9 gates stay green.

- Brief names contract id `documents.public_contract.v1` and adapter id `documents.hub_adapter_v1`  
- Public contract doc exists and is referenced from Catalog Exposes  
- Delivery façade binds those ids; still not Document Link SoT  
- D2 `documents` is enabled in `compositionSlots.ts`; reserved list empty  
- No D3–D9 consumer slot list includes `documents`  
- Shell `documents` nav ≠ D2 slot  
- Documents Foundation maturity stays 🔄  
- No OCR / e-sign / packages product unlock; no Catalog shape rewrite  

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| First D2 `documents` consumer bind (HR employee) + Document Link SoT | [E3](documents-platform-e3-first-consumer-bind.md) |
| Candidate Document Link bind (replace `candidate_id` consume path) | Later E slice |
| OCR / e-sign / packages / approvals automation | Later E / Advanced |
| Hub control-center UI rebuild | Later E Workspace |
| `HrHandoffDetailPage` cutover | Out (not E2) |
| Forms P3 / P4 / P5 | Locked |
| Billing Platform | Phase F |
| Stage 5 settings / R6 | Unchanged |
| C2.4 Scheduling | Frozen |
| Entity Catalog Passport | Unchanged (D-series residual) |
| Documents Foundation ✅ | Later E close |

Do **not** mix consumer cutover, OCR, Billing, AI, or Forms product unlocks into E2.

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Documents platform (ADR-009); not Recruitment / HR / a sixth product module |
| 2 Exists? | Hub + Catalog passport + E1-era façade yes; public-contract id **new** (this); Foundation **no** |
| 3 Adapter | `documents.hub_adapter_v1` on existing `document_hub_delivery_contract.py`; no second Adapter |
| 4 Boundary | Catalog unlock only; no D3–D9 bind; no dossier-as-slot; no OCR/e-sign product; no Billing/AI; no Forms P3–P5; no file-copy handoff; no Document Link table cutover |
| 5 Settings | Existing Manifest IA only; no new keys in E2 |
| 6 SoT | Document Hub (ADR-009); candidate-owned `documents` remains legacy bridge |
| 7 Events | Catalog `document.created` / `linked` / `verified` / `expired` — no new events this slice |
| 8 Requires | E1 ✅ [#270](https://github.com/igortatarynovich/HostFlow/pull/270) · D9 ✅ · D2 slot named · ADR-009 / ADR-014 / ADR-025 · Forms Foundation ✅ |
| 9 License | None new (Basic = platform; Advanced = existing addon flags) |
| 10 Public contract | Additive `documents.public_contract.v1`; no DTO bump of Catalog shape; no L0 P-rule change |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- Product Track = this brief; Documents Platform E1 is closed (#270 / `f37deff1`).  
- Operators / agents cannot treat Candidate/HR dossier, Shell `documents` nav, or “slot now enabled” as consumer cutover or Foundation done.  
- Feat locked until this brief merges.  
- D3–D9 remain unbound on `documents`; Forms P3–P5 and Billing stay out of Product Track.

---

## Likely files (feat PR)

| Area | Paths |
|------|--------|
| Public contract | `docs/specs/architecture/documents-public-contract.md` |
| Adapter bind | `backend/app/services/document_hub_delivery_contract.py` (`PUBLIC_CONTRACT_ID` / adapter id) |
| Catalog / capability-contract | Exposes ids additive; pointer only |
| Slot unlock | `hostflow-frontend/src/platform/entity-workspace/compositionSlots.ts` |
| Consumers | D3–D9 `*Consumer.ts` — keep omitting `documents`; retitle the throw |
| Gate | `backend/tests/platform/test_documents_e2_public_contract_gate.py` |
| Prior gates | E1 + D2 assertions that froze “no id / reserved” |
| Pointers | queue / roadmap / AGENTS / maturity → [E3](documents-platform-e3-first-consumer-bind.md) |

---

## DoD

- [x] Brief sealed with ownership / contract inventory / D2 unlock vs bind / in/out + acceptance  
- [x] Queue + roadmap + AGENTS + maturity pointed at this brief at merge; **2026-08-20:** Product Track moved to [Workspace Capability Platform Completion](workspace-capability-platform-completion.md); this feat stays locked  
- [x] E1 marked **COMPLETE** with #270 / `f37deff1`  
- [x] Feat PR — public contract + catalog unlock ([#276](https://github.com/igortatarynovich/HostFlow/pull/276) · merge `826877b5`)

---

## History

- 2026-08-22: E5 brief opened — Candidate storage-bridge retirement (`candidate_id` drop); Product Track → [E5](documents-platform-e5-candidate-storage-bridge.md) (feat locked). E4 ✅ [#280](https://github.com/igortatarynovich/HostFlow/pull/280) (`0af74913`). This slice ✅ [#276](https://github.com/igortatarynovich/HostFlow/pull/276) (`826877b5`).
- 2026-08-22: E4 brief opened — Candidate Document Link (D4); Product Track → [E4](documents-platform-e4-candidate-document-link.md) (feat locked). E3 ✅ [#278](https://github.com/igortatarynovich/HostFlow/pull/278) (`cc106a38`). This slice ✅ [#276](https://github.com/igortatarynovich/HostFlow/pull/276) (`826877b5`).
- 2026-08-22: E2 feat — `documents.public_contract.v1` / `documents.hub_adapter_v1`; D2 `documents` catalog enabled; D3–D9 unbound; named Public Contract Gate. Foundation stays 🔄. Stacked after [#273](https://github.com/igortatarynovich/HostFlow/pull/273)/[#274](https://github.com/igortatarynovich/HostFlow/pull/274) merge `84a2ea94`.
- 2026-08-21: WCP program **COMPLETE** ([#274](https://github.com/igortatarynovich/HostFlow/pull/274) · [record](../gates/workspace-capability-platform-complete.md)). Feat **unlocked**. Product Track → this brief. D2 `documents` still reserved until the E2 feat. G4 did not unlock this.
- 2026-08-21: WCP G1–G5 **PASS_WITH_CONSTRAINTS** ([#273](https://github.com/igortatarynovich/HostFlow/pull/273)). G4 PASS. Feat remains **locked** until program **COMPLETE**, not until G4. Next: [host runtime-equivalence](workspace-capability-host-runtime-equivalence.md).
- 2026-08-20: Product Track → [Entity Platform Completion](workspace-capability-platform-completion.md). This brief stays ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271); **feat locked** until that program’s Goal Completion. Same-day Shared UI Capabilities draft superseded. Not a Notes/Consent-only seal — queue hygiene until Entity Shell is restored.
- 2026-08-20: Program retitled Workspace Capability Platform Completion; feat remains locked until Recruitment Application proof.
- 2026-08-18: E1 feat [#270](https://github.com/igortatarynovich/HostFlow/pull/270) (`f37deff1`). CI: named Contract Seal Gate **11 passed**; full Tests with coverage **484 failed / 2740 passed** (Engineering Track, same as D9). Product Track → this brief [#271](https://github.com/igortatarynovich/HostFlow/pull/271). Feat locked. Not consumer bind / not OCR / not Forms P3–P5 / not Billing.
