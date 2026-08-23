# Documents Platform E7 — Document Requests (Phase E)

**Status:** **IN PROGRESS** (brief; feat locked)  
**Phase class:** platform  
**Branch (docs):** `docs/documents-platform-e7-document-requests`  
**Branch (code):** `feat/documents-platform-e7-document-requests` *(locked until this brief merges)*  
**Parents:** [Documents Platform E6](documents-platform-e6-document-expiry.md) [#284](https://github.com/igortatarynovich/HostFlow/pull/284)/[#285](https://github.com/igortatarynovich/HostFlow/pull/285) · [E5](documents-platform-e5-candidate-storage-bridge.md) ✅ · [E4](documents-platform-e4-candidate-document-link.md) ✅ · [E3](documents-platform-e3-first-consumer-bind.md) ✅ · [E2](documents-platform-e2-public-contract.md) ✅ · [E1](documents-platform-e1-contract-seal.md) ✅ · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) ✅ · [D8 HR Employee Cutover](entity-workspace-d8-hr-employee-cutover.md) ✅ · [Workspace Capability Platform COMPLETE](../gates/workspace-capability-platform-complete.md) [#274](https://github.com/igortatarynovich/HostFlow/pull/274) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase E](../architecture/platform-completion-roadmap.md) · [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · [ADR-012](../architecture/ADR-012-activity-notification-operating-layer.md) · [ADR-014](../architecture/ADR-014-document-hub-access-model.md) · [ADR-025](../architecture/ADR-025-standard-adapter-boundary.md) · [Capability Contract](../architecture/capability-contract.md) · [Documents Public Contract](../architecture/documents-public-contract.md) · [Document Hub scope](../../document-hub/module-scope.md) · [Activity operating layer](../architecture/activity-notification-operating-layer.md) · [A2-F8](../gates/platform-governance-review-a2.md)

> E6 sealed expiry / validity as Hub `expires_at` / `expiry_state` on the same adapter ([#285](https://github.com/igortatarynovich/HostFlow/pull/285) · merge `79e638c3`). D4 and D8 stay bound. Foundation stayed 🔄.  
> E7 seals **document request as a Hub-owned outstanding requirement** (required type + entity via Document Link) consumed through the public contract — not a Candidate stage, not an HR JSON silo, not an Activity row as Documents SoT, not mass D3–D9 bind, not packages / OCR / Foundation close.  
> E7 does **not** bind D3 / D5–D7 / D9, reopen G4, put a request / reminder / task table inside Document Hub, mint a new Catalog event, treat `next_action` or Candidate pipeline as Documents SoT, open packages / OCR / e-sign, or mark Foundation ✅.

**Naming (do not collapse):** this **Documents Platform E7** is not E6 expiry / validity, not E5 storage-bridge retirement, not E4 Candidate Document Link bind, not E3 first-consumer bind, not a D-series chrome cutover, not Shell `documents` nav, not Recruitment Application (G4), not OCR / e-sign product, not document packages, not remaining-consumer mass bind, not Billing Platform Phase F. Request seal ≠ Foundation ✅. Remaining Entity consumers stay unbound. Document Hub remains a **platform capability** (ADR-009), **not** a sixth product module.

---

## Why this slice

After [#285](https://github.com/igortatarynovich/HostFlow/pull/285) (`79e638c3`) validity belongs to the Document. Phase E’s next horizon theme is still split: **“ask for a document”** lives in module silos, not on the Documents public contract.

| Layer | After E6 | Hole E7 closes |
|-------|----------|----------------|
| D4 / D8 consume | Hub links + Hub `expires_at` / `expiry_state` | Leave bind as-is |
| Public `set_resolution` | Packs / checklist / Hub requirements already mapped | Not sealed as **the** outstanding-ask SoT |
| Candidate stage `Ожидаем документы` | Flips pipeline; Activity `document_request` (`source_module='candidates'`) | Module UX — not Documents SoT |
| HR `hr_document_requests` | `decision_basis_json` + `postHrAdditionalDocumentRequest` | Module verification UX — not Documents SoT |
| `DocumentStatus.requested` | Status on a row that may not exist | Projection, not the ask itself |
| `DocumentRequestedFrom` | Who provides (driver / employer / agency) | Provider hint — **not** the request product |
| Email `send_document_requested_email_to_candidate` | Candidate notification | Communication consume — not Documents SoT |
| `pe_document_requirements` | Process Engine table | Local PE dictionary — Architecture Rule 1 forbids promoting it |
| Catalog events | `document.created` / `linked` / `verified` / `expired` | No `document.requested` — **do not mint** this slice |
| D3 / D5–D7 / D9 | Omit `documents` | Stay omit — request ≠ mass bind |
| Foundation | 🔄 | Stays 🔄 — request ≠ packages / OCR / Foundation close |

Without E7, the next PR will either (a) bind every remaining consumer because “expiry already works”, or (b) keep driving “we asked for a document” from Candidate stage / HR JSON / Activity rows and call lifecycle done, or (c) mint a Hub request table (forbidden by ADR-012) or a new Catalog event without RFC.

E7 exists to prove **the ask belongs to Documents**, not to decorate another Entity Workspace and not to finish Phase E.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After E7, “request a document” **cannot** be a Candidate-owned stage machine, an HR `decision_basis_json` silo, a Process Engine dictionary, or an Activity row treated as Documents SoT. Public consume of an outstanding ask is Hub required type + entity (Document Link) through `documents.public_contract.v1` / `documents.hub_adapter_v1`. D4 and D8 still place `documents`; they do not own the requirement. Activity / reminders stay in the Activity & Notification operating layer (ADR-012) — Document Hub **publishes**, it does not own a request / task table. Catalog stays `document.created` / `linked` / `verified` / `expired` — E7 does **not** mint `document.requested`. D3 / D5–D7 / D9 stay unbound. Expiry-plus-two-consumers is no longer a valid reading of “Documents lifecycle is done”.

**Completion proof (named consumer):**  
**Candidate Entity Workspace** — D4 `CandidateEntityWorkspacePanel` / `/app/candidates/:id`. Locked; feat does **not** choose Recruitment Application, a new Hub control-center, HR as the proof, mass D3–D9 bind, or Foundation close instead.

```text
Candidate Entity Workspace (D4 host)
  + D2 documents surface still bound (E4)
  + documents.hub_adapter_v1 (same adapter — no second Adapter)
  + outstanding ask = Hub required type + entity via Document Link
  + public consume via set_resolution / owner_summary (additive; no contract id bump)
  + Activity type document_request may be published / consumed — Hub does not own a request table
  + Candidate stage / HR JSON / PE table / email are not Documents SoT
  + D8 HR employee bind unchanged
  + D3 / D5–D7 / D9 still omit documents
```

Recruitment Application is **not** this proof (closed G4). HR employee is **not** this proof (closed E3). Client / Vacancy / Sales / Services are **not** this proof. Packages / OCR / e-sign are **not** this proof.

**False close (reject):** Candidate stage auto-flip as Documents SoT; HR `hr_document_requests` as Documents SoT; Activity `document_request` as Documents SoT; reminder / request table inside Document Hub; `next_action` as the public contract; minting Catalog `document.requested` without Architecture RFC; mass D3–D9 bind; Foundation ✅; OCR / e-sign / packages; G4 reused; second Adapter / `public_contract.v2`.

---

## Consumer decision (normative)

E6 left remaining Entity consumers unbound on purpose: they still need new `linked_entity_type` values. Binding them now would be the false close E5 named (“two hosts already work”).

Shipped after E6:

| Artifact | Owner | What it is today |
|----------|--------|------------------|
| D8 / D4 D2 bind | Document Hub + hosts | Live via `documents.hub_adapter_v1` |
| Candidate relationship | `document_entity_links` (`candidate` / `primary`) | Storage + consume |
| Validity | Hub `expire_date` / public `expires_at` | Sealed E6 |
| `set_resolution` | Public contract | Packs / checklist / Hub requirements — unsealed as **the ask** |
| Activity `document_request` | ADR-012 | Candidate / comms consume — not Documents SoT |
| HR additional request | HR verification | `decision_basis_json.hr_document_requests` |
| `DocumentStatus.requested` | Document row | Status projection |
| Email | Candidate notifications | Communication consume |
| Process Engine `pe_document_requirements` | Process Engine | Local table — not Hub types |

**Decision: this slice = Document Requests.** Proof consumer stays **Candidate (D4)** — the bound host that actually gets asked for documents. E7 does not add a third D2 consumer.

| Remaining Entity consumers (D3 / D5–D7 / D9) | Later named slices — **not** this PR |
| Packages / OCR / approvals / automation | Later E / Advanced — **not** this PR |
| Recruitment Application | Closed G4 — proves Workspace Capability, not Documents |

Feat **must** seal outstanding-ask consume on the public contract / adapter (read path; additive; no id bump). It must retire Candidate-stage / HR-JSON / Activity-as-SoT language from Documents. It must **not** move request / reminder ownership into Document Hub. It must **not** mint a Catalog event.

---

## Goal

Prove three things on the ask:

1. **A document request is a Hub outstanding requirement** — required type + entity via Document Link, not a Candidate column, not a person-status machine, not HR JSON.  
2. **Same platform contract** — `documents.public_contract.v1` / `documents.hub_adapter_v1`; no second Adapter; no new public-contract id. Prefer additive read on existing `set_resolution` / `owner_summary` over a new op.  
3. **Activity stays downstream** — Document Hub may publish; ADR-012 owns Activity type `document_request` / reminders / tasks. Catalog is not rewritten. D4 + D8 stay bound; D3 / D5–D7 / D9 still omit `documents`.

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
E5  → drop documents.candidate_id
    → writers persist Hub links; no FK
E6  → expiry / validity is Hub document property
    → public consume via same adapter; Catalog document.expired
E7 (this)
    → outstanding ask is Hub required type + entity via Document Link
    → public consume via same adapter (set_resolution / owner_summary)
    → Activity layer consumes document_request; Hub does not own a request table
    → no new Catalog event; no public-contract id bump
    → D4 + D8 stay bound; D3 / D5–D7 / D9 stay unbound
    → same adapter; no second Adapter
E8+
    → remaining consumers / later lifecycle (locked until E7 feat)
```

E7 **must not**:

- bind `documents` on Sales Inquiry / Client / Sales Order / Vacancy / Services order  
- unbind or rewrite the D8 / D4 consume paths  
- reopen Recruitment Application as G4 or as the Documents proof  
- treat Candidate stage / HR JSON / Activity `document_request` / `next_action` as Documents SoT  
- put a request / reminder / task table inside Document Hub (ADR-012 owns that)  
- mint Catalog `document.requested` or any new Catalog event (shape change needs Architecture RFC)  
- mint a second Adapter, a second public-contract id, or a local Candidate / HR request table promoted as Hub SoT  
- promote `pe_document_requirements` or a new type dictionary (Architecture Rule 1)  
- open OCR, e-sign, packages, approvals automation, or Hub UI rebuild  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- mark Documents Foundation ✅ (stays 🔄)

---

## Request SoT (this is the ask seal)

| Layer | E6 | E7 (this) |
|-------|----|-----------|
| Relationship SoT | `document_entity_links` only | **Same** |
| Validity SoT | Hub `expire_date` / public `expires_at` | **Same** |
| Outstanding-ask SoT | Unsealed checklist leftover + Candidate/HR silos | Hub required type + entity via Document Link |
| Adapter | `documents.hub_adapter_v1` | **Same** — additive request read, no second Adapter |
| Catalog event | `document.expired` consumed | **No new event** — Activity `document_request` stays Activity-owned |
| Reminders / tasks | Activity layer (ADR-012) | **Same** — Hub does not own a request table |
| D4 / D8 | Bound | Bound (unchanged) |
| Other consumers | Unbound | Unbound |

**Invariants:**

1. One Document; many Links. The ask is “this entity still owes this Hub type”, not a person-status.  
2. Modules consume only the public contract / adapter (Architecture Rule 2).  
3. No new local type / status / request dictionaries (Architecture Rule 1). Hub types already exist.  
4. D2 `documents` on D4 still renders via the adapter only.  
5. Hub does not own request / reminder / task rows.  
6. `DocumentRequestedFrom` remains a provider hint on a Document / type — it is not the request product.  
7. `DocumentStatus.requested` may remain a row projection — it is not the outstanding-ask SoT (an ask can exist with no row yet).

---

## D2 bind (unchanged — not mass bind)

E6 did not bind another consumer. **This slice does not either.**

| Layer | E6 | E7 (this) |
|-------|----|-----------|
| D8 / D4 slot lists | include `documents` | **still include** |
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
| **E7** | Document requests | ← **active** (brief; feat locked) |
| **E8+** | Remaining consumers / later lifecycle | locked until E7 feat |

Roadmap later themes (packages, OCR, approvals, automation, remaining D3 / D5–D7 / D9 bind) stay **horizon**. Documents Foundation stays 🔄.

---

## In scope (this docs PR)

1. This brief — request decision + Original Goal → Completion Proof.  
2. Close **Documents Platform E6** as **COMPLETE** after [#284](https://github.com/igortatarynovich/HostFlow/pull/284)/[#285](https://github.com/igortatarynovich/HostFlow/pull/285) (`79e638c3`).  
3. Point Product Track / queue / roadmap / AGENTS / maturity / Hub scope / D2 / D4 / D8 here. Split E7 (requests) from E8+ (remaining consumers / later lifecycle).  
4. Feat locked until this brief merges.

## In scope (feat PR — after this brief)

1. Public contract / adapter: outstanding-ask read is Hub required type + entity; additive on `set_resolution` / `owner_summary`; no Candidate stage / HR JSON as SoT.  
2. Retire Candidate-stage / HR-JSON / Activity-as-Documents-SoT language from Documents canon that this slice owns.  
3. Keep Activity type `document_request` in ADR-012; do not mint a Hub request table; do not mint Catalog `document.requested`.  
4. D4 + D8 still consume via `GET /api/v1/platform/documents/resolve`.  
5. Named **Documents Platform E7 Document Requests Gate** — Hub outstanding-ask SoT; D4/D8 still bound; D3 / D5–D7 / D9 unbound; adapter still `documents.hub_adapter_v1`; no new Catalog event; Foundation 🔄; G4 unchanged.  
6. E1–E6 / D1–D9 / WCP named gates stay green.  
7. Architecture Review Checklist (10 questions) + Goal Completion G1–G5 in the feat PR description.  
8. Pointers stay on E7 until E8 brief opens.

---

## Documents Platform E7 Document Requests Gate (CI — mandatory)

Named step: **Documents Platform E7 Document Requests Gate**  
(`tests/platform/test_documents_e7_document_requests_gate.py`). Full-repo pytest red does not waive it. E1–E6 / D1–D9 / WCP gates stay green.

- Public consume of outstanding ask goes through `documents.public_contract.v1` / `documents.hub_adapter_v1`  
- Candidate stage / HR JSON / Activity `document_request` are not Documents SoT  
- No Hub request / reminder / task table  
- No new Catalog event; no public-contract id bump  
- D4 and D8 consumer slot lists still include `documents`  
- D3 / D5–D7 / D9 consumer slot lists still omit `documents`  
- No second Adapter  
- Shell `documents` nav ≠ D2 slot  
- Recruitment Application G4 path unchanged  
- Documents Foundation maturity stays 🔄  
- No OCR / e-sign / packages product unlock; no Catalog shape rewrite  

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| D3 / D5 / D6 / D7 / D9 `documents` bind | Later named E slices — **not** this PR |
| Document packages / OCR / e-sign / approvals automation | Later E / Advanced |
| Catalog `document.requested` | Architecture RFC if ever needed — **not** this PR |
| Hub control-center UI rebuild | Later E Workspace |
| Forms P3 / P4 / P5 | Locked |
| Billing Platform | Phase F |
| Stage 5 settings / R6 | Unchanged |
| C2.4 Scheduling | Frozen |
| Documents Foundation ✅ | Later E close (packages / OCR still open) |
| Reopen G4 Recruitment Application | Forbidden |
| Reopen E3 D8 / E4 D4 / E5 column drop / E6 expiry | Forbidden |

Do **not** mix mass bind, OCR, packages, Billing, AI, or Forms product unlocks into E7.

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Documents platform (ADR-009); Activity layer (ADR-012) owns `document_request` / reminders. Candidate host **places** only |
| 2 Exists? | Public contract + adapter + D2 slot + D4/D8 binds + Hub types + `set_resolution` yes; request seal **new** (this); Foundation **no** |
| 3 Adapter | Same `documents.hub_adapter_v1`; no second Adapter |
| 4 Boundary | Outstanding ask only. D4/D8 stay. No D3 / D5–D7 / D9 bind. No OCR/e-sign/packages. No Billing/AI. No Forms P3–P5. No G4 reopen |
| 5 Settings | Existing Manifest IA only; no new keys in E7 |
| 6 SoT | Document Hub required type + entity via Document Link; Activity layer for tasks |
| 7 Events | No new Catalog events this slice. Activity type `document_request` already named (ADR-012) |
| 8 Requires | E6 ✅ [#285](https://github.com/igortatarynovich/HostFlow/pull/285) · E5 ✅ · E4 ✅ · E3 ✅ · E2 ✅ · E1 ✅ · D4 ✅ · D8 ✅ · WCP COMPLETE [#274](https://github.com/igortatarynovich/HostFlow/pull/274) · ADR-009 / ADR-012 / ADR-014 / ADR-025 |
| 9 License | None new (Basic = upload/link/status/expiry/required sets; Advanced = existing addon flags) |
| 10 Public contract | No id bump; additive outstanding-ask read on `set_resolution` / `owner_summary`; no Catalog shape change; no L0 P-rule change |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- Product Track = this brief (feat locked). Documents Platform E6 is closed (#285 / `79e638c3`).  
- Operators / agents cannot treat D4 bind, column drop, expiry fields, CandidateCard, Shell `documents` nav, Candidate stage, HR JSON, Activity `document_request`, `next_action`, or Recruitment Application as this proof.  
- D3 / D5–D7 / D9 remain unbound on `documents`; D4 / D8 stay bound; Forms P3–P5, OCR, packages, and Billing stay out of Product Track.  
- Documents Foundation stays 🔄.

---

## Likely files (feat PR)

| Area | Paths |
|------|--------|
| Public contract | `docs/specs/architecture/documents-public-contract.md` — outstanding-ask read on `set_resolution` / `owner_summary` |
| Adapter | `document_hub_delivery_contract.py` — same façade; additive projection |
| Activity | keep `document_request` in ADR-012; do not mint Hub table |
| Gate | `backend/tests/platform/test_documents_e7_document_requests_gate.py` |
| Pointers | queue / roadmap / AGENTS / maturity stay on E7 until E8 |

---

## DoD

- [x] Brief sealed with request decision / Activity-layer boundary / in/out + Original Goal → Completion Proof  
- [x] Queue + roadmap + AGENTS + maturity pointed at this brief (this docs PR)  
- [x] E6 marked **COMPLETE** with #285 / `79e638c3`  
- [ ] Feat PR — outstanding-ask public-contract seal (after this brief merges)

---

## History

- 2026-08-23: E7 brief opened — Document requests. Product Track → this brief (feat locked). E6 ✅ [#285](https://github.com/igortatarynovich/HostFlow/pull/285) (`79e638c3`). D3 / D5–D7 / D9 stay unbound. Foundation stays 🔄.
