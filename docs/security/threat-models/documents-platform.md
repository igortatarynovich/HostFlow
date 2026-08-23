# Threat Model — Documents Platform (E3–E7 public resolve)

## Assets

- Authenticated resolve DTO (`GET /api/v1/platform/documents/resolve`) — Hub document **metadata** + Document Link ids + Hub validity (`expires_at` / `expiry_state`) + Hub outstanding asks (`outstanding_asks`)  
- Hub table `document_entity_links` (relationship SoT for named consumers)  
- Document Hub rows (`documents`) scoped by tenant — **no** `candidate_id` column  
- Public contract / adapter ids: `documents.public_contract.v1` / `documents.hub_adapter_v1`

This model covers the **platform capability** consume path sealed in E3–E7: HR employee (D8) reads reused documents via Document Link (`workforce_employee` / `reused_for_hr`); Candidate (D4) reads via Document Link (`candidate` / `primary`). E6 adds Hub expiry fields on the same DTO. E7 adds Hub outstanding-ask projection (required type vs linked docs). Neither consumer uses a page-local widget as the D2 path. Candidate relationship storage is Hub links only — **not** `documents.candidate_id`. Validity is on the Document, not on a Candidate status machine. The outstanding ask is Hub required type + entity, not Candidate stage / HR JSON / Activity `document_request`. File bytes, signed URLs, and upload remain [`document-uploads.md`](./document-uploads.md). Candidate portal uploads remain [`candidate-portal.md`](./candidate-portal.md). Handoff copy-vs-link remains [`handoff.md`](./handoff.md) — E3–E7 do not add a file-copy path.

Not this surface: OCR / e-sign / packages, D3 / D5–D7 / D9 bind, Foundation close, anonymous public links, Hub-owned reminder / request table, Catalog `document.requested`.

## Trust boundaries

- Authenticated tenant operator → platform Documents APIs (JWT + `X-Tenant-Id` + RLS via `get_db_with_tenant`)  
- Adapter (`documents.hub_adapter_v1`) is the only consumer contract; hosts must not import `modules.documents.crud`, `HrEmployeeDocumentsSection`, or CandidateCard documents as the D2 consume path  
- Entity/relation closed set for this HTTP: `workforce_employee` / `reused_for_hr` **and** `candidate` / `primary`  
- Resolve returns metadata (id / title / type / status / expiry / expiry_state / outstanding_asks / link). It is **not** a file download and must not mint a signed URL  
- `documents.candidate_id` is dropped. Writers persist Hub `candidate` / `primary` links. Listing still goes through `document_entity_links`  
- Expiry evaluation is Documents-owned (`document_expiry_engine`). Outstanding ask is Documents-owned (`project_outstanding_asks_via_contract`). Activity / reminders stay in ADR-012 — Hub does not own a task / request table

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| DP-1 | Cross-tenant link leak | Resolve by `linked_entity_id` without tenant bind / RLS |
| DP-2 | JWT / header tenant mismatch | Token tenant ≠ `X-Tenant-Id` still returns another tenant’s links |
| DP-3 | Open entity/relation types | Arbitrary `linked_entity_type` / `relation_type` enumerates other Hub graphs |
| DP-4 | File bytes on resolve | Endpoint returns storage path, signed URL, or raw object |
| DP-5 | Second Adapter / local join | HR or Candidate consumes via workforce/candidate document lists, a new adapter id, or synthesized dataclass links as SoT |
| DP-6 | Public / anonymous resolve | Treating this path as a public-link or portal token |
| DP-7 | Handoff copy | Creating a second file instead of a Document Link |
| DP-8 | Candidate-id consume for D2 | Using a leftover FK / `owner_id` shortcut as the D4 or D8 D2 path |
| DP-9 | Nullable FK leftover | Leaving `documents.candidate_id` as a write target after E5 |
| DP-10 | Candidate-status as expiry SoT | Treating pipeline auto-flip / `next_action` / a Hub reminder table as the Documents validity contract |
| DP-11 | Module silo as request SoT | Treating Candidate stage / HR JSON / Activity `document_request` / a Hub request table as the Documents outstanding-ask contract |

## Митигации

- HTTP resolve uses `get_current_user` + `get_db_with_tenant`; token tenant must match session tenant (`403`).  
- Adapter filters `document_entity_links` and `documents` by `tenant_id`. Missing / other-tenant ids return an empty list, not a cross-tenant row.  
- Unknown entity/relation types fail closed (`400`). Closed set is E3 pair **and** E4 pair only — client / vacancy / sales / services stay rejected.  
- Response schema is Hub view + link ids + Hub expiry fields only. Upload, download, and signed URL stay on existing document routes.  
- Same adapter id as E2. Named **Documents Platform E6 Document Expiry Gate** fails if expiry is not on the Hub view, if D4/D8 unbind, if D3 / D5–D7 / D9 bind `documents`, or if a Hub reminder table appears.  
- Named **Documents Platform E7 Document Requests Gate** fails if `outstanding_asks` is missing from the Hub resolve, if a Hub request table appears, if Catalog `document.requested` is minted, or if D3 / D5–D7 / D9 bind `documents`.  
- No new security events. Catalog events stay `document.created` / `linked` / `verified` / `expired`.

## Тесты

- `backend/tests/platform/test_documents_e7_document_requests_gate.py`  
- `backend/tests/platform/test_documents_e6_document_expiry_gate.py`  
- `backend/tests/platform/test_documents_e5_candidate_storage_bridge_gate.py`  
- `backend/tests/platform/test_documents_e4_candidate_document_link_gate.py`  
- `backend/tests/platform/test_documents_e3_first_consumer_bind_gate.py`  
- `backend/tests/platform/test_documents_e2_public_contract_gate.py`  
- `backend/tests/platform/test_entity_workspace_d4_cutover_gate.py`  
- `backend/tests/platform/test_entity_workspace_d8_cutover_gate.py`

## Связанные спеки

- `docs/specs/architecture/documents-public-contract.md`  
- `docs/specs/workflows/document_expiry.md`  
- `docs/specs/tasks/documents-platform-e7-document-requests.md`  
- `docs/specs/tasks/documents-platform-e6-document-expiry.md`  
- `docs/specs/tasks/documents-platform-e5-candidate-storage-bridge.md`  
- `docs/specs/tasks/documents-platform-e4-candidate-document-link.md`  
- `docs/specs/tasks/documents-platform-e3-first-consumer-bind.md`  
- `docs/specs/architecture/ADR-009-document-hub-platform-layer.md`  
- `docs/specs/architecture/ADR-012-activity-notification-operating-layer.md`  
- `docs/specs/architecture/ADR-014-document-hub-access-model.md`
