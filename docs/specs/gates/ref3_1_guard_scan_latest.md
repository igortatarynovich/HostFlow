# REF-3.1 Guard Scan Report

- Findings: 6
- New violations vs baseline: 0

## New Violations
- none

## Baseline Keys
- `DIRECT_APPLICABILITY_RESOLVER` | `backend/app/api/v1/candidates/service.py`
- `DIRECT_APPLICABILITY_RESOLVER` | `backend/app/services/hr_expected_documents_resolver.py`
- `DIRECT_REFERENCE_MODEL_IMPORT` | `backend/app/entity_profile/hr_employment_policy.py`
- `DIRECT_REFERENCE_MODEL_IMPORT` | `backend/app/entity_profile/publication_versions.py`
- `DIRECT_REFERENCE_MODEL_IMPORT` | `backend/app/entity_profile/recruitment_policy.py`
- `DIRECT_REFERENCE_MODEL_IMPORT` | `backend/app/services/hr_expected_documents_resolver.py`
- `DIRECT_REFERENCE_MODEL_IMPORT` | `backend/app/services/recruitment_candidate_document_declarations.py`
- `DIRECT_TYPE_RUNTIME_RESOLVER` | `backend/app/services/handoff_snapshot.py`
- `DIRECT_TYPE_RUNTIME_RESOLVER` | `backend/app/services/hr_review_document_resolution.py`
- `DIRECT_TYPE_RUNTIME_RESOLVER` | `backend/app/services/ready_for_employment_emit.py`
- `DIRECT_TYPE_RUNTIME_RESOLVER` | `backend/app/services/status_transitions.py`

## Raw Findings
- `DIRECT_REFERENCE_MODEL_IMPORT` `backend/app/entity_profile/hr_employment_policy.py:22` :: `from backend.app.models.ref_document_type import (`
- `DIRECT_REFERENCE_MODEL_IMPORT` `backend/app/entity_profile/publication_versions.py:26` :: `from backend.app.models.ref_document_type import RefDocumentTypeVersion`
- `DIRECT_REFERENCE_MODEL_IMPORT` `backend/app/entity_profile/recruitment_policy.py:21` :: `from backend.app.models.ref_document_type import (`
- `DIRECT_TYPE_RUNTIME_RESOLVER` `backend/app/services/ready_for_employment_emit.py:25` :: `from backend.app.services.document_type_runtime_resolver import DocumentTypeRuntimeResolver`
- `DIRECT_TYPE_RUNTIME_RESOLVER` `backend/app/services/ready_for_employment_emit.py:159` :: `runtime_ref = await DocumentTypeRuntimeResolver.resolve_for_document(db, d)`
- `DIRECT_REFERENCE_MODEL_IMPORT` `backend/app/services/recruitment_candidate_document_declarations.py:18` :: `from backend.app.models.ref_document_type import RefDocumentType, RefDocumentTypeVersion`
