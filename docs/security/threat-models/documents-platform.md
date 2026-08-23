# Threat Model — Documents Platform (E3–E5 public resolve)

## Assets

- Authenticated resolve DTO (`GET /api/v1/platform/documents/resolve`) — Hub document **metadata** + Document Link ids  
- Hub table `document_entity_links` (relationship SoT for named consumers)  
- Document Hub rows (`documents`) scoped by tenant — **no** `candidate_id` column  
- Public contract / adapter ids: `documents.public_contract.v1` / `documents.hub_adapter_v1`

This model covers the **platform capability** consume path sealed in E3–E5: HR employee (D8) reads reused documents via Document Link (`workforce_employee` / `reused_for_hr`); Candidate (D4) reads via Document Link (`candidate` / `primary`). Neither consumer uses a page-local widget as the D2 path. Candidate relationship storage is Hub links only — **not** `documents.candidate_id`. File bytes, signed URLs, and upload remain [`document-uploads.md`](./document-uploads.md). Candidate portal uploads remain [`candidate-portal.md`](./candidate-portal.md). Handoff copy-vs-link remains [`handoff.md`](./handoff.md) — E3–E5 do not add a file-copy path.

Not this surface: OCR / e-sign / packages, D3 / D5–D7 / D9 bind, Foundation close, anonymous public links.

## Trust boundaries

- Authenticated tenant operator → platform Documents APIs (JWT + `X-Tenant-Id` + RLS via `get_db_with_tenant`)  
- Adapter (`documents.hub_adapter_v1`) is the only consumer contract; hosts must not import `modules.documents.crud`, `HrEmployeeDocumentsSection`, or CandidateCard documents as the D2 consume path  
- Entity/relation closed set for this HTTP: `workforce_employee` / `reused_for_hr` **and** `candidate` / `primary`  
- Resolve returns metadata (id / title / type / status / expiry / link). It is **not** a file download and must not mint a signed URL  
- `documents.candidate_id` is dropped. Writers persist Hub `candidate` / `primary` links. Ensure-on-read from an FK is gone. Listing still goes through `document_entity_links`

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

## Митигации

- HTTP resolve uses `get_current_user` + `get_db_with_tenant`; token tenant must match session tenant (`403`).  
- Adapter filters `document_entity_links` and `documents` by `tenant_id`. Missing / other-tenant ids return an empty list, not a cross-tenant row.  
- Unknown entity/relation types fail closed (`400`). Closed set is E3 pair **and** E4 pair only — client / vacancy / sales / services stay rejected.  
- Response schema is Hub view + link ids only. Upload, download, and signed URL stay on existing document routes.  
- Same adapter id as E2. Named **Documents Platform E5 Candidate Storage Bridge Gate** fails if the FK column remains, if D4/D8 unbind, or if D3 / D5–D7 / D9 bind `documents`.  
- No new security events. Catalog events stay `document.created` / `linked` / `verified` / `expired`.

## Тесты

- `backend/tests/platform/test_documents_e5_candidate_storage_bridge_gate.py`  
- `backend/tests/platform/test_documents_e4_candidate_document_link_gate.py`  
- `backend/tests/platform/test_documents_e3_first_consumer_bind_gate.py`  
- `backend/tests/platform/test_documents_e2_public_contract_gate.py`  
- `backend/tests/platform/test_entity_workspace_d4_cutover_gate.py`  
- `backend/tests/platform/test_entity_workspace_d8_cutover_gate.py`

## Связанные спеки

- `docs/specs/architecture/documents-public-contract.md`  
- `docs/specs/tasks/documents-platform-e5-candidate-storage-bridge.md`  
- `docs/specs/tasks/documents-platform-e4-candidate-document-link.md`  
- `docs/specs/tasks/documents-platform-e3-first-consumer-bind.md`  
- `docs/specs/architecture/ADR-009-document-hub-platform-layer.md`  
- `docs/specs/architecture/ADR-014-document-hub-access-model.md`
