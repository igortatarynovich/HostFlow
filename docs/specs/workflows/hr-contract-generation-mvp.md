# HR Contract Generation MVP (PR9)

**Status:** Implemented (backend PR9 + frontend preview panel).  
**Related:** [Read adapter](hr-employment-identity-read-adapter.md), [Data verification](hr-data-verification-workspace.md).

## Goal

Generate **draft/preview** employment contract documents from merge templates using **only** `trusted_identity.*` placeholders.

## API

`POST /api/v1/workforce/employees/{employee_id}/contract-generation/preview`

Body: `template_id` or `template_code`, optional `variable_bindings` (non-identity keys only).

Response: `ContractDraftPreviewOut` — `log_id`, `document_id`, `status=draft_preview`, `preview_url`, `trusted_identity_bindings`, `automation.send/sign/epuap=false`.

`GET …/trusted-identity/prep-status` — use before preview to explain blocks.

## Rules

1. `contract_generation` consumer allowed (else **422** `TRUSTED_IDENTITY_*`).  
2. Template must use `trusted_identity.*` for person/legal data — no `candidate.*`, bare `legal_name`, `employee.*`.  
3. Client cannot override `trusted_identity.*` in `variable_bindings`.  
4. Employee linked to `candidate_id` for document storage.  
5. Log `draft_preview`; no send / sign / ePUAP.

## UI

- `HrContractPreviewPanel` — prep-status gate, template select, generate, open `preview_url`, `trusted_identity_bindings`  
- `hostflow-frontend/src/api/workforce.ts` — `getTrustedIdentityPrepStatus`, `postContractDraftPreview`  
- Placement: collapsed **Contract draft preview** (`<details>`) on employee case + handoff review (after data verification / checklist)  
- **Not** inside Data Verification workspace — preview only after trusted identity is ready  

## Out of scope

- Sending, ePUAP, qualified signature  
- Payroll / ZUS from this endpoint  
- Legally binding issuance / finalization workflow  

## Example template

```text
Employment contract for {{ trusted_identity.legal_name }}
PESEL: {{ trusted_identity.pesel }}
Citizenship: {{ trusted_identity.citizenship }}
Permit valid until: {{ trusted_identity.permit_expiry }}
```
