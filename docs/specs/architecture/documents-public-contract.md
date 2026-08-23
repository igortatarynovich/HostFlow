# Documents Public Contract v1 — E2 seal

**Status:** canonical · **ACTIVE**  
**Capability id:** `documents`  
**Contract id:** `documents.public_contract.v1`  
**Adapter id:** `documents.hub_adapter_v1`  
**Passport:** [`platform-capability-catalog.md`](platform-capability-catalog.md#documents)  
**Tasks:** [`documents-platform-e1-contract-seal.md`](../tasks/documents-platform-e1-contract-seal.md) ✅ · [`documents-platform-e2-public-contract.md`](../tasks/documents-platform-e2-public-contract.md) ✅ · [`documents-platform-e3-first-consumer-bind.md`](../tasks/documents-platform-e3-first-consumer-bind.md) ✅ · [`documents-platform-e4-candidate-document-link.md`](../tasks/documents-platform-e4-candidate-document-link.md) ✅ · [`documents-platform-e5-candidate-storage-bridge.md`](../tasks/documents-platform-e5-candidate-storage-bridge.md) (feat)  
**Normative:** [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`ADR-014`](ADR-014-document-hub-access-model.md) · [`ADR-025`](ADR-025-standard-adapter-boundary.md)

---

## Identity

Documents владеет **Document Hub** (registry, versions, types, required sets, verification, links).  
Candidate / HR dossier pages, Shell `documents` nav, and Entity Workspace D2 `documents` **consumer bind** — **не** Documents SoT.

Storage bridge: existing `document_hub_delivery_contract.py` façade over `modules.documents`. E3 adds **entity-link resolve** on the same adapter for HR employee (`workforce_employee` / `reused_for_hr`) via Hub table `document_entity_links`. E4 adds Candidate entity-link resolve (`candidate` / `primary`) on the same adapter. E5 retires `documents.candidate_id` (storage-bridge drop).

---

## Public operations

Catalog Exposes already name Document Adapter / Verification Adapter / document set resolution as **Stable**. E2 names the ops; it does not add OCR to the public surface.

| Op | Stability | Maps from façade (today) | Description |
|----|-----------|--------------------------|-------------|
| `list` / `resolve` | **Stable** | `list_entity_link_documents_via_contract` | Entity-scoped read. E3 D8 and E4 D4 consume paths are entity-link resolve. E5 dropped the Candidate FK list as public consume. Output is Hub document view, not a module file row |
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
3. Legacy `documents.candidate_id` is **dropped** in [E5](../tasks/documents-platform-e5-candidate-storage-bridge.md). Candidate relationship SoT is Hub `document_entity_links` only.  
4. D2 `documents` slot on D8 and D4 renders via this adapter only — not Shell nav, not dossier pages, not `HrEmployeeDocumentsSection`, not CandidateCard.  
5. No new local type / status dictionaries.

---

## Adapter binding

| Field | Value |
|-------|--------|
| **Implementation (E2)** | Existing `backend/app/services/document_hub_delivery_contract.py` bound to the ids above |
| **E3 resolve** | Same adapter: `list_entity_link_documents_via_contract` (`workforce_employee` / `reused_for_hr`). HTTP: `GET /api/v1/platform/documents/resolve` |
| **E4 resolve** | Same adapter: `list_entity_link_documents_via_contract` (`candidate` / `primary`). HTTP: `GET /api/v1/platform/documents/resolve`. No second Adapter |
| **E5 storage** | Same adapter. Drop `documents.candidate_id`. No second Adapter |
| **Second Adapter** | Forbidden |
| **Document Link SoT** | E3 HR employee + E4 Candidate via `document_entity_links`. E5 drops the Candidate storage FK |

---

## D2 catalog unlock + consumer binds

E2 marked D2 `documents` as an **enabled platform slot**. E3 binds it on **HR employee (D8)**. E4 binds it on **Candidate (D4)** through Document Link. E5 does not add a consumer. D3 / D5–D7 / D9 stay unbound. Catalog unlock ≠ mass bind. Shell `EntityWorkspaceSectionId` `documents` ≠ this slot.

---

## Contract tests

`backend/tests/platform/test_documents_e2_public_contract_gate.py` — named **Documents Platform E2 Public Contract Gate**.  
`backend/tests/platform/test_documents_e3_first_consumer_bind_gate.py` — named **Documents Platform E3 First Consumer Bind Gate**.  
`backend/tests/platform/test_documents_e4_candidate_document_link_gate.py` — named **Documents Platform E4 Candidate Document Link Gate**.  
`backend/tests/platform/test_documents_e5_candidate_storage_bridge_gate.py` — named **Documents Platform E5 Candidate Storage Bridge Gate**.  
E1 / E2 / E3 / E4 / D1–D9 / WCP gates stay green (amended where they froze “`candidate_id` must remain”).

---

## History

- 2026-08-22: E5 feat — drop `documents.candidate_id`; writers persist Hub `candidate` / `primary` links; this contract stays v1 (no id bump). Foundation stays 🔄.
- 2026-08-22: E5 brief — Candidate storage-bridge retirement (`candidate_id` drop) named; this contract stays v1 (no id bump).
- 2026-08-22: E4 feat — Candidate entity-link resolve (`candidate` / `primary`) on `documents.hub_adapter_v1`; D4 bind; column stays; Foundation stays 🔄.
- 2026-08-22: E4 brief — Candidate Document Link (`candidate` / `primary`) named; this contract stays v1 (no id bump). Column drop stays later.
- 2026-08-22: E3 feat — entity-link resolve on `documents.hub_adapter_v1`; D8 first consumer bind; Document Link SoT for HR employee; Foundation stays 🔄.
- 2026-08-22: E3 brief — first consumer bind / Document Link SoT named; this contract stays v1 (no id bump). Entity-link resolve is E3 feat.
- 2026-08-22: E2 feat — sealed `documents.public_contract.v1` / `documents.hub_adapter_v1`; D2 `documents` catalog enabled; D3–D9 unbound; Foundation stays 🔄. After WCP COMPLETE [#274](https://github.com/igortatarynovich/HostFlow/pull/274) merge `84a2ea94`.
