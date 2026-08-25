# Documents Public Contract v1 — E2 seal

**Status:** canonical · **ACTIVE**  
**Capability id:** `documents`  
**Contract id:** `documents.public_contract.v1`  
**Adapter id:** `documents.hub_adapter_v1`  
**Passport:** [`platform-capability-catalog.md`](platform-capability-catalog.md#documents)  
**Tasks:** [`documents-platform-e1-contract-seal.md`](../tasks/documents-platform-e1-contract-seal.md) ✅ · [`documents-platform-e2-public-contract.md`](../tasks/documents-platform-e2-public-contract.md) ✅ · [`documents-platform-e3-first-consumer-bind.md`](../tasks/documents-platform-e3-first-consumer-bind.md) ✅ · [`documents-platform-e4-candidate-document-link.md`](../tasks/documents-platform-e4-candidate-document-link.md) ✅ · [`documents-platform-e5-candidate-storage-bridge.md`](../tasks/documents-platform-e5-candidate-storage-bridge.md) ✅ · [`documents-platform-e6-document-expiry.md`](../tasks/documents-platform-e6-document-expiry.md) ✅ · [`documents-platform-e7-document-requests.md`](../tasks/documents-platform-e7-document-requests.md) ✅ · [`documents-platform-e8-bind.md`](../tasks/documents-platform-e8-bind.md) ✅ [#321](https://github.com/igortatarynovich/HostFlow/pull/321) · [`documents-platform-e8-eval.md`](../tasks/documents-platform-e8-eval.md) ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324)  
**Normative:** [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`ADR-014`](ADR-014-document-hub-access-model.md) · [`ADR-025`](ADR-025-standard-adapter-boundary.md)

---

## Identity

Documents владеет **Document Hub** (registry, versions, types, required sets, verification, links).  
Candidate / HR dossier pages, Shell `documents` nav, and Entity Workspace D2 `documents` **consumer bind** — **не** Documents SoT.

Storage bridge: existing `document_hub_delivery_contract.py` façade over `modules.documents`. E3 adds **entity-link resolve** on the same adapter for HR employee (`workforce_employee` / `reused_for_hr`) via Hub table `document_entity_links`. E4 adds Candidate entity-link resolve (`candidate` / `primary`) on the same adapter. E5 retires `documents.candidate_id` (storage-bridge drop). E6 seals expiry / validity as Hub `expires_at` + `expiry_state` on the same adapter. E7 seals outstanding ask (required type + entity via Document Link) as additive `outstanding_asks` on resolve / `owner_summary`. Candidate stage / HR JSON / Activity `document_request` are not Documents SoT. No Hub request table. No Catalog `document.requested`. E8-bind seals display / select / persist of Hub `document_type_code` as canonical registry codes; R4 aliases are resolve-only. E8-eval seals required / optional / blocked applicability of those codes from R5 `merge(pack, tenant_delta)` (+ Overlay as existing CL7 input).

---

## Public operations

Catalog Exposes already name Document Adapter / Verification Adapter / document set resolution as **Stable**. E2 names the ops; it does not add OCR to the public surface.

| Op | Stability | Maps from façade (today) | Description |
|----|-----------|--------------------------|-------------|
| `list` / `resolve` | **Stable** | `list_entity_link_documents_via_contract` · `project_outstanding_asks_via_contract` · `load_outstanding_asks_via_contract` · `list_canonical_types_for_select_via_contract` · `project_required_doc_applicability_via_contract` | Entity-scoped read. E3 D8 and E4 D4 consume paths are entity-link resolve. E5 dropped the Candidate FK list as public consume. E6 adds Hub validity fields on the same view: `expires_at` / `expiry_state` / `days_left` (from `document_expiry_engine`). E7 adds `outstanding_asks` (Hub required type vs linked docs). DR1-runtime may persist Engine-projected asks on the same adapter; resolve prefers those rows when present. E8-bind adds `canonical_types` (registry codes for select) and canonicalizes `doc_type` on items / asks. E8-eval adds `applicability` (`required` / `optional` / `blocked` from R5 merge). Output is Hub document view + outstanding-ask + applicability projection, not a module file row |
| `set_resolution` | **Stable** | `project_document_packs_via_contract` · `compute_candidate_checklist_via_contract` · `evaluate_document_hub_requirements_via_contract` | Document set / pack / checklist projection. Outstanding-ask SoT is Hub required type + entity — not Candidate stage / HR JSON |
| `owner_summary` | **Stable** | `compute_owner_summary_via_contract` · `merge_document_hub_requirements_into_summary_via_contract` | Read model for compose. E7 adds `outstanding_asks` from Hub required buckets |
| `verification_status` | **Stable** | Review fields on owner summary / list | Verification Adapter read — no new review engine |
| `list_types` | **Stable** | `list_document_types_via_contract` · `list_canonical_document_type_codes_via_contract` · `list_canonical_types_for_select_via_contract` | Hub types only (Architecture Rule 1). Select / persist identity is registry canonical; R4 aliases are resolve-only |

**Not public v1 (Internal / deferred):** OCR internals · e-sign · `get_uploads_root` / `sanitize_filename` · reminder / request work-queue projection as a product API · ruleset seed writes · synthetic checklist row builders as a consumer API · Candidate status auto-flip as Documents SoT · HR `hr_document_requests` JSON as Documents SoT.

### Error semantics

Façade errors stay as today (module / HTTP layer). E2 does **not** mint a second error vocabulary.

---

## Events

Catalog already publishes `document.created` / `linked` / `verified` / `expired`. E6 **consumes** `document.expired`; E7 does **not** mint `document.requested`. Reminders / Activity `document_request` stay in ADR-012.

---

## Invariants

1. Modules consume **only** `documents.public_contract.v1` / `documents.hub_adapter_v1` — no `modules.documents.crud` imports from other modules (Architecture Rule 2).  
2. File is a version; Document is the business object (ADR-009). Handoff is **links + permissions**, never copy.  
3. Legacy `documents.candidate_id` is **dropped** in [E5](../tasks/documents-platform-e5-candidate-storage-bridge.md). Candidate relationship SoT is Hub `document_entity_links` only.  
4. D2 `documents` slot on D8 and D4 renders via this adapter only — not Shell nav, not dossier pages, not `HrEmployeeDocumentsSection`, not CandidateCard.  
5. No new local type / status dictionaries.  
6. Validity SoT is Hub `expire_date` / public `expires_at`. Expiry evaluation is Documents-owned. Document Hub does not own a reminder / task table.  
7. Outstanding-ask SoT is Hub required type + entity via Document Link (`outstanding_asks`). Candidate stage / HR JSON / Activity `document_request` are not Documents SoT. Document Hub does not own a request table.

---

## Adapter binding

| Field | Value |
|-------|--------|
| **Implementation (E2)** | Existing `backend/app/services/document_hub_delivery_contract.py` bound to the ids above |
| **E3 resolve** | Same adapter: `list_entity_link_documents_via_contract` (`workforce_employee` / `reused_for_hr`). HTTP: `GET /api/v1/platform/documents/resolve` |
| **E4 resolve** | Same adapter: `list_entity_link_documents_via_contract` (`candidate` / `primary`). HTTP: `GET /api/v1/platform/documents/resolve`. No second Adapter |
| **E5 storage** | Same adapter. Drop `documents.candidate_id`. No second Adapter |
| **E6 expiry** | Same adapter. Hub `expires_at` / `expiry_state` / `days_left` on resolve. `document_expiry_engine` is evaluation only — not a Hub reminder table. No second Adapter |
| **E7 requests** | Same adapter. Hub `outstanding_asks` on resolve / owner_summary. No Hub request table. No Catalog `document.requested`. No second Adapter |
| **DR1-runtime** | Same adapter. Engine may persist outstanding asks keyed by Document Link identity. No Hub request table. No Catalog `document.requested`. No second Adapter |
| **E8-bind** | Same adapter. Display / select / persist canonical registry `document_type_code`. R4 aliases resolve-only. Additive `canonical_types` on resolve. No second Adapter. **PASS** [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f`. Not E8-eval. Not mass D3–D9 bind |
| **E8-eval** | Same adapter. Required / optional / blocked applicability of canonical types from R5 `merge(pack, tenant_delta)` (+ Overlay as existing CL7 input). Additive `applicability` on resolve. No second Adapter. No Hub packages table. Not OCR. Not mass D3–D9 bind. **PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6`. Brief: [`documents-platform-e8-eval.md`](../tasks/documents-platform-e8-eval.md) |
| **Second Adapter** | Forbidden |
| **Document Link SoT** | E3 HR employee + E4 Candidate via `document_entity_links`. E5 drops the Candidate storage FK. E6 / E7 do not add a consumer |

---

## D2 catalog unlock + consumer binds

E2 marked D2 `documents` as an **enabled platform slot**. E3 binds it on **HR employee (D8)**. E4 binds it on **Candidate (D4)** through Document Link. E5 / E6 / E7 / E8-bind / E8-eval do not add a consumer. D3 / D5–D7 / D9 stay unbound. Catalog unlock ≠ mass bind. Shell `EntityWorkspaceSectionId` `documents` ≠ this slot.

---

## Contract tests

`backend/tests/platform/test_documents_e2_public_contract_gate.py` — named **Documents Platform E2 Public Contract Gate**.  
`backend/tests/platform/test_documents_e3_first_consumer_bind_gate.py` — named **Documents Platform E3 First Consumer Bind Gate**.  
`backend/tests/platform/test_documents_e4_candidate_document_link_gate.py` — named **Documents Platform E4 Candidate Document Link Gate**.  
`backend/tests/platform/test_documents_e5_candidate_storage_bridge_gate.py` — named **Documents Platform E5 Candidate Storage Bridge Gate**.  
`backend/tests/platform/test_documents_e6_document_expiry_gate.py` — named **Documents Platform E6 Document Expiry Gate**.  
`backend/tests/platform/test_documents_e7_document_requests_gate.py` — named **Documents Platform E7 Document Requests Gate**.  
`backend/tests/platform/test_documents_e8_canonical_type_bind_gate.py` — named **Documents Platform E8 Canonical Type Bind Gate**.  
`backend/tests/platform/test_documents_e8_required_doc_eval_gate.py` — named **Documents Platform E8 Required-Doc Evaluation Gate**.  
E1 / E2 / E3 / E4 / E5 / E6 / E7 / E8 / D1–D9 / WCP gates stay green.

---

## History

- 2026-08-25: E8 Required-Doc Evaluation Gate **PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6`. Additive `applicability`; no contract id bump. Foundation stays 🔄. Product = **none this amendment**.
- 2026-08-25: E8-eval feat — D4 required / optional / blocked from R5 merge on `documents.hub_adapter_v1` (additive `applicability`; no id bump). Foundation stays 🔄.
- 2026-08-25: Queue amendment names **E8-eval** Active Product after E8-bind Gate PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321). Same adapter. Not OCR. Not packages table. Foundation stays 🔄.
- 2026-08-25: E8 Canonical Type Bind Gate **PASS** [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f`. Additive `canonical_types`; no contract id bump. Foundation stays 🔄. E8-eval unlocked (not scheduled).
- 2026-08-25: E8-bind feat — D4 Documents display / select / persist canonical registry types; R4 aliases resolve-only; additive `canonical_types` on `documents.hub_adapter_v1` (no id bump). Foundation stays 🔄.
- 2026-08-25: DR1-runtime feat — Engine may persist Hub `outstanding_asks` on `documents.hub_adapter_v1` (Document Link identity; no request table; no Catalog `document.requested`; no id bump). Foundation stays 🔄.
- 2026-08-23: E7 feat — Hub `outstanding_asks` on `documents.hub_adapter_v1` resolve / owner_summary; no Catalog `document.requested`; no Hub request table; this contract stays v1 (no id bump). Foundation stays 🔄.
- 2026-08-23: E6 feat — Hub expiry read (`expires_at` / `expiry_state`) on `documents.hub_adapter_v1`; workflow SoT leaves Candidate FK / Candidate-status; this contract stays v1 (no id bump). Foundation stays 🔄.
- 2026-08-22: E5 feat — drop `documents.candidate_id`; writers persist Hub `candidate` / `primary` links; this contract stays v1 (no id bump). Foundation stays 🔄.
- 2026-08-22: E5 brief — Candidate storage-bridge retirement (`candidate_id` drop) named; this contract stays v1 (no id bump).
- 2026-08-22: E4 feat — Candidate entity-link resolve (`candidate` / `primary`) on `documents.hub_adapter_v1`; D4 bind; column stays; Foundation stays 🔄.
- 2026-08-22: E4 brief — Candidate Document Link (`candidate` / `primary`) named; this contract stays v1 (no id bump). Column drop stays later.
- 2026-08-22: E3 feat — entity-link resolve on `documents.hub_adapter_v1`; D8 first consumer bind; Document Link SoT for HR employee; Foundation stays 🔄.
- 2026-08-22: E3 brief — first consumer bind / Document Link SoT named; this contract stays v1 (no id bump). Entity-link resolve is E3 feat.
- 2026-08-22: E2 feat — sealed `documents.public_contract.v1` / `documents.hub_adapter_v1`; D2 `documents` catalog enabled; D3–D9 unbound; Foundation stays 🔄. After WCP COMPLETE [#274](https://github.com/igortatarynovich/HostFlow/pull/274) merge `84a2ea94`.
