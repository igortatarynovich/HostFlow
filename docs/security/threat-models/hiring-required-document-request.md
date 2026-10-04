# Threat Model — Required document request and employment manifest (HE-4)

**Surface:** authenticated required-document request, candidate public-status upload of that request, and `ready_for_employment.v1` on an internal-HR handoff.  
**Not:** legal employability matrix, handoff accept, employee creation, auto-accept, min HR.

## Assets

- Outstanding required set: RPM `r5_required_set` minus already satisfied requirements.
- Document row in status `requested`, with `meta.request_kind` and `meta.requirement_code`.
- Existing candidate status-share token (`/public/status/{token}`).
- Handoff snapshot payload `ready_for_employment.v1` while status stays `pending_review`.

## Trust boundaries

- Authenticated recruiter with the existing candidate write guard ↔ tenant-scoped candidate.
- Holder of the existing status-share token ↔ that candidate’s public upload route. No new token type.
- Internal-HR handoff emit ↔ operator who can already create the handoff. Emit does not accept the handoff.

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| HD-1 | Non-outstanding code becomes a vacancy requirement | `POST .../requirements/{code}/request` for a code outside the outstanding set |
| HD-2 | Manual ask impersonates policy | Generic document create with `status=requested` supplies `requirement_code` |
| HD-3 | Public upload drops request identity | Candidate upload replaces meta and the required request becomes unlabeled |
| HD-4 | Status token used as a new capability | Request returns the existing status link; email is best-effort and is not the authority |
| HD-5 | Manifest treated as a completed hire | Emit of `ready_for_employment.v1` is read as accept, employee create, or auto-accept |
| HD-6 | Emit without a vacancy | Internal-HR handoff for a candidate with no vacancy still publishes the manifest |
| HD-7 | Cross-tenant request or handoff | Existing candidate / handoff tenant guards (unchanged) |

## Митигации (HE-4)

- Required request is created only when the code is outstanding. Otherwise **409** `not_outstanding_requirement` and no document row.
- Generic create that lands in `requested` is forced to `request_kind=ad_hoc`. `requirement_code` is removed. An ad-hoc ask does not enter `r5_required_set`.
- Public upload onto an existing document copies `request_kind` and `requirement_code` into the replacement meta.
- The candidate link is the existing status-share token. No new public route and no new token store.
- `ready_for_employment.v1` is written only when destination is internal HR **and** `candidate.vacancy_id` is set. Handoff status stays `pending_review`. Accept and employee creation are not called.
- `documents.candidate_id` stays dropped (E5). The status column rename does not add a candidate ownership column.

## Тесты

- Hiring E2E acceptance walk (`315cb710`, clean database): outstanding request, outsider 409, ad-hoc visa does not enter eligibility, public upload keeps request identity, operator upload without a request row, transfer emits a validated manifest and does not accept.

## Связанные спеки

- [`hiring-workflow-e2e.md`](../../specs/tasks/hiring-workflow-e2e.md)
- [`hiring-acceptance-contract.md`](../../specs/architecture/hiring-acceptance-contract.md) (`hiring_acceptance.v1`)
- [`legal-eligibility-requirement-policy.md`](../../specs/tasks/legal-eligibility-requirement-policy.md) — not this surface

## History

- 2026-09-30: HE-4 acknowledgement. A vacancy-driven request exists only for an outstanding RPM requirement. The employment manifest does not accept the handoff.
