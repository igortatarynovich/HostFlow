# Documents Platform E5 — Candidate Storage Bridge Retirement (Phase E)

**Status:** **COMPLETE** ([#281](https://github.com/igortatarynovich/HostFlow/pull/281)/[#282](https://github.com/igortatarynovich/HostFlow/pull/282) · merge `702b922c`)  
**Next:** [Documents Platform E6](documents-platform-e6-document-expiry.md) ✅ → [Documents Platform E7 — Document Requests](documents-platform-e7-document-requests.md) (feat)  
**Phase class:** platform  
**Branch (docs):** `docs/documents-platform-e5-candidate-storage-bridge` ✅ [#281](https://github.com/igortatarynovich/HostFlow/pull/281)  
**Branch (code):** `feat/documents-platform-e5-candidate-storage-bridge` ✅ [#282](https://github.com/igortatarynovich/HostFlow/pull/282)  
**Parents:** [Documents Platform E4](documents-platform-e4-candidate-document-link.md) [#279](https://github.com/igortatarynovich/HostFlow/pull/279)/[#280](https://github.com/igortatarynovich/HostFlow/pull/280) · [E3](documents-platform-e3-first-consumer-bind.md) ✅ · [E2](documents-platform-e2-public-contract.md) ✅ · [E1](documents-platform-e1-contract-seal.md) ✅ · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) ✅ · [D2 Composition Contract](entity-workspace-d2-composition-contract.md) ✅ · [Workspace Capability Platform COMPLETE](../gates/workspace-capability-platform-complete.md) [#274](https://github.com/igortatarynovich/HostFlow/pull/274) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase E](../architecture/platform-completion-roadmap.md) · [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · [ADR-014](../architecture/ADR-014-document-hub-access-model.md) · [ADR-025](../architecture/ADR-025-standard-adapter-boundary.md) · [Capability Contract](../architecture/capability-contract.md) · [Documents Public Contract](../architecture/documents-public-contract.md) · [Document Hub scope](../../document-hub/module-scope.md) · [A2-F8](../gates/platform-governance-review-a2.md)

> E4 bound D2 `documents` on Candidate through Capability Host + Document Link ([#280](https://github.com/igortatarynovich/HostFlow/pull/280) · merge `0af74913`). Consume path is Hub `document_entity_links` (`candidate` / `primary`). `documents.candidate_id` stayed a required storage FK. Foundation stayed 🔄.  
> E5 retires that **storage bridge**. Same adapter. Same two consumers (D4 + D8). Not mass D3–D9 bind. Not lifecycle / OCR / Foundation close.  
> E5 does **not** bind D3 / D5–D7 / D9, reopen G4, treat Shell `documents` nav as the D2 slot, open OCR / e-sign / packages, or mark Foundation ✅.

**Naming (do not collapse):** this **Documents Platform E5** is not E4 Candidate Document Link bind, not E3 first-consumer bind, not E2 catalog unlock, not E1 contract seal, not a D-series chrome cutover, not Shell `documents` nav, not CandidateCard, not Recruitment Application (G4), not OCR / e-sign product, not document packages, not Billing Platform Phase F. Storage-bridge retirement ≠ mass D3–D9 bind. Column drop ≠ Foundation ✅. Document Hub remains a **platform capability** (ADR-009), **not** a sixth product module.

---

## Why this slice

After [#278](https://github.com/igortatarynovich/HostFlow/pull/278)/[#280](https://github.com/igortatarynovich/HostFlow/pull/280) Documents is consumable on two hosts and still split in storage:

| Layer | After E4 | Hole E5 closes |
|-------|----------|----------------|
| D8 HR employee | D2 `documents` live via `document_entity_links` (`workforce_employee` / `reused_for_hr`) | Leave as-is |
| D4 Candidate consume | Hub `document_entity_links` (`candidate` / `primary`) | Leave as-is |
| `documents.candidate_id` | Required FK; ensure-on-read still mints links from it | Competing storage SoT — Document is still a Candidate child row |
| `list_candidate_documents_via_contract` | Legacy bridge still on the façade | Must not remain a public consume path after the column is gone |
| Synthesized dataclass links | Projection from `candidate_id` | Must not become the replacement SoT |
| D3 / D5–D7 / D9 | Omit `documents` | Stay omit — this slice is not mass bind |
| Foundation | 🔄 | Stays 🔄 — column drop ≠ lifecycle close |

Without E5, the next PR will either (a) bind every remaining consumer because “two hosts already work”, or (b) keep writing `candidate_id` and call Document Link complete, or (c) mark Foundation ✅ while a required Candidate FK still owns the row.

E5 exists to prove **Document is not a Candidate-owned row**, not to decorate another Entity Workspace and not to finish Phase E.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After E5, a Document row **cannot** require `documents.candidate_id`. Writers **cannot** treat that FK as Hub SoT. D4 **cannot** fall back to `list_candidate_documents_via_contract` or a synthesized dataclass “link”. Relationship SoT is Hub `document_entity_links` only. D8 bind stays. Catalog-enabled-plus-two-consumers-plus-a-required-FK is no longer a valid reading of “Document Link is done”.

**Completion proof (named consumer):**  
**Candidate Entity Workspace** — D4 `CandidateEntityWorkspacePanel` / `/app/candidates/:id`. Locked; feat does **not** choose Recruitment Application, a new screen, mass D3–D9 bind, or Foundation close instead.

```text
Candidate Entity Workspace (D4 host)
  + D2 documents surface still bound (E4)
  + documents.hub_adapter_v1 (same adapter — no second Adapter)
  + Document Link SoT: document_entity_links (candidate / primary)
  + documents.candidate_id column dropped (not nullable leftover)
  + create/update dual-writes Hub links; no FK write
  + list_candidate_documents_via_contract retired as public consume
  + D8 HR employee bind unchanged
  + D3 / D5–D7 / D9 still omit documents
```

Recruitment Application is **not** this proof (closed G4). HR employee is **not** this proof (closed E3). Client / Vacancy / Sales / Services are **not** this proof. Lifecycle / OCR is **not** this proof.

**False close (reject):** column nullable but still written; ensure-on-read from FK kept as the mint path; dataclass as SoT; mass D3–D9 bind; Foundation ✅; OCR/e-sign/packages; G4 reused.

---

## Consumer decision (normative)

E4 left the column on purpose: consume path had to move first. Remaining Entity consumers still have no operational Candidate-origin Hub rows.

Shipped after E4:

| Artifact | Owner | What it is today |
|----------|--------|------------------|
| D8 / D4 D2 bind | Document Hub + hosts | Live via `documents.hub_adapter_v1` |
| Candidate relationship SoT (consume) | `document_entity_links` | `candidate` / `primary` |
| Candidate relationship SoT (storage) | `documents.candidate_id` (required FK) | Competing model |
| Adapter Candidate op | `list_candidate_documents_via_contract` | Legacy bridge |
| Ensure-on-read | `ensure_candidate_primary_document_links` | Mints Hub rows **from the FK** |
| Synthesized links | `document_data_contract.DocumentEntityLink` dataclass | Projection from `candidate_id` — **not** the Hub table |

**Decision: this slice = retire the Candidate storage bridge.** Proof consumer stays **Candidate (D4)** — the same host that E4 bound. E5 does not add a third D2 consumer.

| Remaining Entity consumers (D3 / D5–D7 / D9) | No operational Hub rows; would mint new `linked_entity_type` values — later named slices |
|-----------------------------------------------|------------------------------------------------------------------------------------------|
| Lifecycle / OCR / packages | Horizon — Foundation close, not this |
| Recruitment Application | Closed G4 — proves Workspace Capability, not Documents |

Feat **must** backfill Hub `candidate` / `primary` rows for every remaining `documents.candidate_id` value, dual-write Hub links on create, then **drop** the column. Nullable leftover is not the proof.

---

## Goal

Prove three things on Candidate storage:

1. **Document is a Hub object** — no required `documents.candidate_id`.  
2. **Document Link is the only Candidate relationship** — Hub table, not FK, not dataclass.  
3. **Same platform contract** — `documents.public_contract.v1` / `documents.hub_adapter_v1`; no second Adapter; D4 + D8 binds unchanged; D3 / D5–D7 / D9 still omit `documents`.

---

## Locked principle

```text
E1  → who owns Documents Platform + Hub ≠ dossier ≠ D2 enable
E2  → documents.public_contract.v1 + documents.hub_adapter_v1
    → D2 documents catalog unlock (reserved → enabled)
E3  → first consumer bind = HR employee (D8)
    → Document Link SoT for that consumer
E4  → Candidate Document Link bind (D4)
    → consume path = document_entity_links (candidate / primary)
    → candidate_id remains storage bridge
E5 (this)
    → drop documents.candidate_id
    → writers persist Hub links; no FK
    → retire list_candidate_documents_via_contract as public consume
    → D4 + D8 stay bound; D3 / D5–D7 / D9 stay unbound
    → same adapter; no second Adapter
E6
    → Document expiry / validity — [brief](documents-platform-e6-document-expiry.md) ✅
E7
    → Document requests — [brief](documents-platform-e7-document-requests.md)
E8+
    → remaining consumers / later lifecycle (locked until E7 feat)
```

E5 **must not**:

- bind `documents` on Sales Inquiry / Client / Sales Order / Vacancy / Services order  
- unbind or rewrite the D8 / D4 consume paths  
- reopen Recruitment Application as G4 or as the Documents proof  
- collapse Shell `EntityWorkspaceSectionId` `documents` into `compositionSlots.ts`  
- leave `documents.candidate_id` as a nullable write target  
- treat `document_data_contract.DocumentEntityLink` dataclass as the Hub table  
- mint a second Adapter, a second public-contract id, or a local Candidate document table  
- open OCR, e-sign, packages, approvals automation, or Hub UI rebuild  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- mark Documents Foundation ✅ (stays 🔄)

---

## Storage SoT (Candidate — this is the column drop)

| Layer | E4 | E5 (this) |
|-------|----|-----------|
| Relationship SoT for Candidate | `document_entity_links` (consume) + `candidate_id` (storage) | `document_entity_links` only |
| Adapter resolve for Candidate | entity-link resolve (`candidate` / `primary`) | **Same** — no second Adapter |
| `documents.candidate_id` | Required storage bridge | **Dropped** |
| Ensure-on-read from FK | Allowed | **Gone** (no FK to read) |
| Synthesized dataclass links | Not SoT | Still not SoT |
| D4 / D8 | Bound | Bound (unchanged) |
| Other consumers | Unbound | Unbound |

**Invariants:**

1. One Document; many Links. Handoff remains links + permissions, never copy (ADR-009).  
2. Modules consume only the public contract / adapter (Architecture Rule 2).  
3. No new local type / status dictionaries (Architecture Rule 1).  
4. D2 `documents` on D4 still renders via the adapter only.  
5. Create of a Candidate-scoped document writes Hub `candidate` / `primary` links. It does not write `candidate_id`.  
6. Tenant / own-company scope after the drop goes through Document Link + existing ADR-014 access — not a new Candidate FK shortcut.

---

## D2 bind (unchanged — not mass bind)

E4 bound D4. **This slice does not bind another consumer.**

| Layer | E4 | E5 (this) |
|-------|----|-----------|
| D8 `hrEmployeeConsumer` slot list | includes `documents` | **still includes** |
| D4 `candidateConsumer` slot list | includes `documents` | **still includes** |
| D3 / D5–D7 / D9 slot lists | omit `documents` | **still omit** |
| Shell `EntityWorkspaceSectionId` `documents` | ≠ D2 slot | still ≠ D2 slot |

---

## Phase E ladder

| Slice | Focus | Status |
|-------|--------|--------|
| **E1** | Contract seal (ownership / Hub ≠ dossier / D2 still reserved) | ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269)/[#270](https://github.com/igortatarynovich/HostFlow/pull/270) · merge `f37deff1` |
| **E2** | Public contract / D2 `documents` catalog enable | ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276) · merge `826877b5` |
| **E3** | First consumer bind (HR employee) + Document Link SoT | ✅ [#277](https://github.com/igortatarynovich/HostFlow/pull/277)/[#278](https://github.com/igortatarynovich/HostFlow/pull/278) · merge `cc106a38` |
| **E4** | Candidate Document Link bind (D4) | ✅ [#279](https://github.com/igortatarynovich/HostFlow/pull/279)/[#280](https://github.com/igortatarynovich/HostFlow/pull/280) · merge `0af74913` |
| **E5** | Candidate storage-bridge retirement (`candidate_id` drop) | ✅ [#281](https://github.com/igortatarynovich/HostFlow/pull/281)/[#282](https://github.com/igortatarynovich/HostFlow/pull/282) · merge `702b922c` |
| **E6** | Document expiry / validity | ✅ [#284](https://github.com/igortatarynovich/HostFlow/pull/284)/[#285](https://github.com/igortatarynovich/HostFlow/pull/285) · merge `79e638c3` |
| **E7** | Document requests | [brief](documents-platform-e7-document-requests.md) (feat) |

Roadmap lifecycle themes (expiry, requests, packages, OCR, approvals, automation) stay **horizon**. Documents Foundation stays 🔄.

---

## In scope (this docs PR)

1. This brief — storage-bridge decision + Original Goal → Completion Proof.  
2. Close **Documents Platform E4** as **COMPLETE** after [#279](https://github.com/igortatarynovich/HostFlow/pull/279)/[#280](https://github.com/igortatarynovich/HostFlow/pull/280) (`0af74913`).  
3. Point Product Track / queue / roadmap / AGENTS / maturity / Hub scope / D2 / D4 / D8 here.  
4. Feat locked until this brief merges.

## In scope (feat PR — after this brief)

1. Alembic: backfill Hub `candidate` / `primary` links; drop `documents.candidate_id`. Nullable leftover is not the proof.  
2. Writers persist Document + Hub link. No FK write. Own-company / ADR-014 scope must not grow a new Candidate shortcut.  
3. Retire `list_candidate_documents_via_contract` and `ensure_candidate_primary_document_links` as the Candidate path. Same adapter; no contract id bump.  
4. D4 + D8 still consume via `GET /api/v1/platform/documents/resolve`.  
5. Named **Documents Platform E5 Candidate Storage Bridge Gate** — column gone; D4/D8 still bound; D3 / D5–D7 / D9 unbound; adapter still `documents.hub_adapter_v1`; Foundation 🔄; G4 unchanged.  
6. E1 / E2 / E3 / E4 / D1–D9 / WCP named gates stay green (amend only assertions that froze “`candidate_id` must remain”).  
7. Architecture Review Checklist (10 questions) + Goal Completion G1–G5 in the feat PR description.  
8. Pointers stay on E5 until E6 brief opens.

---

## Documents Platform E5 Candidate Storage Bridge Gate (CI — mandatory)

Named step: **Documents Platform E5 Candidate Storage Bridge Gate**  
(`tests/platform/test_documents_e5_candidate_storage_bridge_gate.py`). Full-repo pytest red does not waive it. E1 / E2 / E3 / E4 / D1–D9 / WCP gates stay green.

- `documents.candidate_id` column is absent  
- D4 and D8 consumer slot lists still include `documents`  
- D3 / D5–D7 / D9 consumer slot lists still omit `documents`  
- Proof surface consumes via `documents.public_contract.v1` / `documents.hub_adapter_v1`  
- Adapter resolve for D4 still goes through `document_entity_links` (`candidate` / `primary`)  
- `list_candidate_documents_via_contract` is not the public consume path  
- No second Adapter; no new public-contract id  
- Shell `documents` nav ≠ D2 slot  
- Recruitment Application G4 path unchanged  
- Documents Foundation maturity stays 🔄  
- No OCR / e-sign / packages product unlock; no Catalog shape rewrite  

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| D3 / D5 / D6 / D7 / D9 `documents` bind | Later named E slices — **not** this PR |
| OCR / e-sign / packages / approvals automation | Later E / Advanced |
| Hub control-center UI rebuild | Later E Workspace |
| Forms P3 / P4 / P5 | Locked |
| Billing Platform | Phase F |
| Stage 5 settings / R6 | Unchanged |
| C2.4 Scheduling | Frozen |
| Entity Catalog Passport | Unchanged |
| Documents Foundation ✅ | Later E close (lifecycle still open) |
| Reopen G4 Recruitment Application | Forbidden |
| Reopen E3 D8 / E4 D4 bind | Forbidden |

Do **not** mix mass bind, OCR, Billing, AI, or Forms product unlocks into E5.

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Documents platform (ADR-009); Candidate host **places** only. Not Recruitment / a sixth product module |
| 2 Exists? | Public contract + adapter + D2 slot + D4/D8 binds + Hub table yes; column drop **new** (this); Foundation **no** |
| 3 Adapter | Same `documents.hub_adapter_v1`; no second Adapter |
| 4 Boundary | Storage retirement only. D4/D8 stay. No D3 / D5–D7 / D9 bind. No OCR/e-sign product. No Billing/AI. No Forms P3–P5. No G4 reopen |
| 5 Settings | Existing Manifest IA only; no new keys in E5 |
| 6 SoT | Document Hub + Document Link table; `candidate_id` gone |
| 7 Events | Catalog `document.created` / `linked` / `verified` / `expired` — no new events this slice |
| 8 Requires | E4 ✅ [#280](https://github.com/igortatarynovich/HostFlow/pull/280) · E3 ✅ · E2 ✅ · E1 ✅ · D4 ✅ · WCP COMPLETE [#274](https://github.com/igortatarynovich/HostFlow/pull/274) · ADR-009 / ADR-014 / ADR-025 |
| 9 License | None new (Basic = platform; Advanced = existing addon flags) |
| 10 Public contract | No id bump; retire Candidate FK list from the façade; no Catalog shape change; no L0 P-rule change |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- Product Track = this brief; Documents Platform E4 is closed (#280 / `0af74913`).  
- Operators / agents cannot treat D4 bind, a nullable `candidate_id`, CandidateCard, Shell `documents` nav, or Recruitment Application as this proof.  
- Feat locked until this brief merges.  
- D3 / D5–D7 / D9 remain unbound on `documents`; D4 / D8 stay bound; Forms P3–P5, OCR, and Billing stay out of Product Track.  
- Documents Foundation stays 🔄.

---

## Likely files (feat PR)

| Area | Paths |
|------|--------|
| Schema | Alembic drop `documents.candidate_id`; backfill Hub links first |
| Model | `backend/app/models/document.py` — column gone |
| Adapter | `document_hub_delivery_contract.py` — retire FK list / ensure-on-read |
| Writers | Document create / upload paths persist Hub `candidate` / `primary` links |
| Access | ADR-014 / own-company scope via links, not a new FK shortcut |
| Public contract note | `docs/specs/architecture/documents-public-contract.md` — storage bridge gone |
| Gate | `backend/tests/platform/test_documents_e5_candidate_storage_bridge_gate.py` |
| Prior gates | E2 / E3 / E4 assertions that froze “`candidate_id` must remain” |
| Pointers | queue / roadmap / AGENTS / maturity stay on E5 until E6 |

---

## DoD

- [x] Brief sealed with storage-bridge decision / Document Link ownership / in/out + Original Goal → Completion Proof  
- [x] Queue + roadmap + AGENTS + maturity pointed at this brief (this docs PR)  
- [x] E4 marked **COMPLETE** with #280 / `0af74913`  
- [x] Feat PR — column drop + Hub-only writes ([#282](https://github.com/igortatarynovich/HostFlow/pull/282) · `702b922c`)

---

## History

- 2026-08-23: E5 feat ✅ [#282](https://github.com/igortatarynovich/HostFlow/pull/282) (`702b922c`) — drop `documents.candidate_id`; Hub-only Candidate relationship; named Candidate Storage Bridge Gate. Product Track → [E6](documents-platform-e6-document-expiry.md). Foundation stays 🔄.
- 2026-08-22: E5 feat opened — drop `documents.candidate_id`; Hub-only Candidate relationship; named Candidate Storage Bridge Gate. Brief ✅ [#281](https://github.com/igortatarynovich/HostFlow/pull/281) (`0a40b5cd`). D3 / D5–D7 / D9 stay unbound. Foundation stays 🔄.
- 2026-08-22: E5 brief opened — Candidate storage-bridge retirement (`candidate_id` drop). Product Track → this brief (feat locked). E4 ✅ [#280](https://github.com/igortatarynovich/HostFlow/pull/280) (`0af74913`). D3 / D5–D7 / D9 stay unbound. Foundation stays 🔄.
