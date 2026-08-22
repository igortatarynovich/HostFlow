# Documents Public Contract v1 — E2 seal

**Status:** canonical · **ACTIVE**  
**Capability id:** `documents`  
**Contract id:** `documents.public_contract.v1`  
**Adapter id:** `documents.hub_adapter_v1`  
**Passport:** [`platform-capability-catalog.md`](platform-capability-catalog.md#documents)  
**Tasks:** [`documents-platform-e1-contract-seal.md`](../tasks/documents-platform-e1-contract-seal.md) ✅ · [`documents-platform-e2-public-contract.md`](../tasks/documents-platform-e2-public-contract.md) ✅ · [`documents-platform-e3-first-consumer-bind.md`](../tasks/documents-platform-e3-first-consumer-bind.md) (feat locked)  
**Normative:** [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`ADR-014`](ADR-014-document-hub-access-model.md) · [`ADR-025`](ADR-025-standard-adapter-boundary.md)

---

## Identity

Documents владеет **Document Hub** (registry, versions, types, required sets, verification, links).  
Candidate / HR dossier pages, Shell `documents` nav, and Entity Workspace D2 `documents` **consumer bind** — **не** Documents SoT.

Storage bridge: existing `document_hub_delivery_contract.py` façade over `modules.documents` (candidate-centric after E2). **Document Link SoT for the first consumer** is [E3](../tasks/documents-platform-e3-first-consumer-bind.md) (HR employee / `document_entity_links`). `documents.candidate_id` remains a legacy bridge until a later Candidate bind.

---

## Public operations

Catalog Exposes already name Document Adapter / Verification Adapter / document set resolution as **Stable**. E2 names the ops; it does not add OCR to the public surface.

| Op | Stability | Maps from façade (today) | Description |
|----|-----------|--------------------------|-------------|
| `list` / `resolve` | **Stable** | `list_candidate_documents_via_contract` | Entity-scoped read. E2 input may stay candidate-centric; output is Hub document view, not a module file row |
| `set_resolution` | **Stable** | `project_document_packs_via_contract` · `compute_candidate_checklist_via_contract` · `evaluate_document_hub_requirements_via_contract` | Document set / pack / checklist projection |
| `owner_summary` | **Stable** | `compute_owner_summary_via_contract` · `merge_document_hub_requirements_into_summary_via_contract` | Read model for compose |
| `verification_status` | **Stable** | Review fields on owner summary / list | Verification Adapter read — no new review engine |
| `list_types` | **Stable** | `list_document_types_via_contract` · `list_canonical_document_type_codes_via_contract` | Hub types only (Architecture Rule 1) |

**Not public v1 (Internal / deferred):** OCR internals · e-sign · `get_uploads_root` / `sanitize_filename` · reminder work-queue projection as a product API · ruleset seed writes · synthetic checklist row builders as a consumer API.

### Error semantics

Façade errors stay as today (module / HTTP layer). E2 does **not** mint a second error vocabulary.

---

## Events

Catalog already publishes `document.created` / `linked` / `verified` / `expired`. E2 does **not** mint events or bump stability.

---

## Invariants

1. Modules consume **only** `documents.public_contract.v1` / `documents.hub_adapter_v1` — no `modules.documents.crud` imports from other modules (Architecture Rule 2).  
2. File is a version; Document is the business object (ADR-009). Handoff is **links + permissions**, never copy.  
3. Legacy `documents.candidate_id` remains a **bridge**, not Hub SoT.  
4. D2 `documents` slot, when a later slice binds it, renders via this adapter only — not Shell nav, not dossier pages.  
5. No new local type / status dictionaries.

---

## Adapter binding

| Field | Value |
|-------|--------|
| **Implementation (E2)** | Existing `backend/app/services/document_hub_delivery_contract.py` bound to the ids above |
| **Second Adapter** | Forbidden |
| **Document Link SoT** | [E3](../tasks/documents-platform-e3-first-consumer-bind.md) — first consumer (HR employee) via `document_entity_links`; not this E2 seal |

---

## D2 catalog unlock (not consumer cutover)

E2 marks D2 `documents` as an **enabled platform slot**. First consumer bind is [E3](../tasks/documents-platform-e3-first-consumer-bind.md) (HR employee). D3–D7 / D9 stay unbound. Catalog unlock ≠ bind. Shell `EntityWorkspaceSectionId` `documents` ≠ this slot.

---

## Contract tests

`backend/tests/platform/test_documents_e2_public_contract_gate.py` — named **Documents Platform E2 Public Contract Gate**. E1 and D1–D9 gates stay green (amended where they froze “no id / reserved”).

---

## History

- 2026-08-22: E3 brief — first consumer bind / Document Link SoT named; this contract stays v1 (no id bump). Entity-link resolve is E3 feat.
- 2026-08-22: E2 feat — sealed `documents.public_contract.v1` / `documents.hub_adapter_v1`; D2 `documents` catalog enabled; D3–D9 unbound; Foundation stays 🔄. After WCP COMPLETE [#274](https://github.com/igortatarynovich/HostFlow/pull/274) merge `84a2ea94`.
