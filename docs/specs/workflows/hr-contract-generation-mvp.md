# HR Contract Generation MVP (PR9)

## Goal

Generate **draft/preview** employment contract documents from merge templates using **only** `trusted_identity.*` placeholders.

## API

`POST /api/v1/workforce/employees/{employee_id}/contract-generation/preview`

Body: `template_id` or `template_code`, optional `variable_bindings` (non-identity keys only).

Response: `ContractDraftPreviewOut` with `log_id`, `document_id`, `status=draft_preview`, `preview_url`, `trusted_identity_bindings`.

## Rules

1. `contract_generation` consumer must be allowed (else **422** `TRUSTED_IDENTITY_*`).
2. Template body/filename must use `trusted_identity.*` for person/legal data — no `candidate.*`, no bare `legal_name`, no `employee.*`.
3. Client cannot override `trusted_identity.*` via `variable_bindings`.
4. Employee must be linked to `candidate_id` (document storage model).
5. Log status `draft_preview`; document meta marks `contract_draft_preview`, `automation.send/sign/epuap=false`.

## Out of scope

- Sending, ePUAP, qualified signature
- Payroll / ZUS
- Final legally binding issuance workflow

## Templates

Example:

```
Employment contract for {{ trusted_identity.legal_name }}
PESEL: {{ trusted_identity.pesel }}
Citizenship: {{ trusted_identity.citizenship }}
Permit valid until: {{ trusted_identity.permit_expiry }}
```
