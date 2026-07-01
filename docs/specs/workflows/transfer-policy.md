# Transfer Policy — canonical handoff readiness

**Status:** Implemented (resolver + API + settings hub). **Strategic layer:** [`process-engine.md`](../platform/process-engine.md) — Transfer Policy is the **tactical Recruitment slice** of Process Engine runtime; migrate to platform evaluator without changing product semantics.  
**Related:** [PR16](../PR16-recruitment-package-pre-hr.md), [handoff-contract.md](specs/architecture/handoff-contract.md), [hr-verification-plan.md](specs/workflows/hr-verification-plan.md).

---

## Problem

Handoff rules were spread across document packs, ruleset, candidate profiles, pipeline gates, tenant links, recruiter confirmations, and pipeline overrides. Each layer was correct in isolation but product-risky: UI, stage change, and handoff create could disagree.

## Solution

**Transfer Policy** is the aggregation layer — not a replacement storage for underlying rules.

| Concern | Canonical resolver field | Underlying storage (unchanged) |
|---------|--------------------------|--------------------------------|
| What is required | `required_documents`, `missing_documents`, `missing_data_fields` | `ref_packs`, overrides, PR16 dossier blocks |
| Who confirms | `required_confirmations` | `candidate.extra.recruitment_dossier_confirmed_blocks` |
| Where to transfer | `destinations_allowed` | `tenant_links.features_json` |
| When allowed | `transfer_allowed`, `stage_gate` | eligibility + package + confirmations |
| Exceptions | `approved_overrides` | `candidate_pipeline_overrides` (scope `both`) |
| Why blocked | `blocking_reasons`, `source_layers` | computed |

**Legacy ruleset** (`document_ruleset_versions`) remains for recruitment checklist compatibility only — **not** a handoff-gate source of truth.

---

## Backend

### `TransferPolicyResolver`

- Path: `backend/app/services/transfer_policy_resolver.py`
- Entry: `TransferPolicyResolver.resolve(db, tenant_id=..., candidate_id=..., require_destination=False|True)`

Returns:

- `transfer_allowed` — stage move to `ready_for_handoff` (documents + package + recruiter confirmations)
- `handoff_create_allowed` — same + enabled tenant-link destination
- `blocking_reasons[]` — each with `code`, `message`, `source_layer`
- `warnings[]` — non-blocking (e.g. missing destination when checking stage only)

### API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/candidates/:id/transfer-readiness` | **Canonical** per-candidate report |
| GET | `/api/v1/candidates/:id/recruitment-package` | Backward-compat; embeds `transfer_readiness` summary |
| GET | `/api/v1/settings/team/transfer-policy` | Tenant-level aggregated policy view |

### Consumers (migrated)

- `_enforce_docs_ready_for_handoff_stage` → `assert_transfer_allowed(require_destination=False)`
- `assert_recruitment_package_ready_for_handoff` → `assert_transfer_allowed(require_destination=True)`
- Frontend candidate card → `GET transfer-readiness`

---

## Frontend

- **Settings → Transfer Policy** (`/app/settings/transfer-policy`) — read-only hub linking to layer-specific settings + governance matrix.
- Candidate card uses `useTransferReadiness` hook.
- **`TransferReadinessReport`** panel on candidate card (`docs_got`, `ready_for_handoff`, `processing_by_hr`) — display-only; gates read `transfer_allowed` / `handoff_create_allowed` from the same API response.

---

## Governance (who changes what)

| Action | Role |
|--------|------|
| Enable document pack | Tenant Administrator |
| Document type override | Tenant Administrator / Compliance Admin |
| Per-candidate override | Recruiter request → Supervisor/Admin approve |
| Handoff route | Agency Administrator (tenant link) |
| Confirm dossier block | Recruiter |
| HR final accept | HR officer |
| Platform packs | Platform administrator |

---

## Migration notes

1. New integrations must call **`transfer-readiness`**, not recompose packs + package locally.
2. `recruitment-package` remains until all clients migrate; do not add new logic there.
3. Future: document pack enablement UI should link from Transfer Policy settings hub.

---

## Regression scenarios

Automated coverage lives in:

| Layer | Path |
|-------|------|
| Unit (resolver) | `backend/tests/services/test_transfer_policy_regression_scenarios.py` |
| API / stage gate | `backend/tests/api/test_transfer_policy_regression.py` |
| Frontend display | `hostflow-frontend/src/components/candidate/__tests__/TransferReadinessReport.test.tsx` |

Shared resolver mocks: `backend/tests/test_support/transfer_policy_mocks.py`.

| Scenario | Expected outcome | Test |
|----------|------------------|------|
| Missing required document | `transfer_allowed=false`; blocker `source_layer=document_packs` | `test_regression_missing_required_document_blocks_stage` |
| Document uploaded, not verified | `transfer_allowed=false`; `pending_verification_documents`; code `pending_document_verification` | `test_regression_pending_verification_blocks_stage` |
| Missing phone / email / address | `transfer_allowed=false`; blockers from `recruitment_package` (`missing_data_field`) | `test_regression_missing_contact_data_blocks_recruitment_package` |
| Docs verified, dossier blocks not confirmed | `transfer_allowed=false`; `required_confirmations`; code `unconfirmed_block` | `test_regression_unconfirmed_blocks_block_transfer` |
| Stage OK, handoff route disabled | `transfer_allowed=true`, `handoff_create_allowed=false`; `no_destination` in **warnings** (stage check) | `test_regression_stage_allowed_handoff_route_disabled` |
| Approved override | Document blocker cleared; `approved_overrides` populated; `pipeline_override` in `source_layers` | `test_regression_approved_override_clears_document_blocker` |
| Legacy ruleset requires document | **Does not** block handoff — resolver gate must not reference ruleset | `test_regression_legacy_ruleset_not_used_in_resolver_gate` |
| Tenant link disabled | Stage allowed; handoff blocked only (`no_destination` in **blocking_reasons** when `require_destination=true`) | `test_regression_tenant_link_disabled_blocks_handoff_only` |
| Candidate in HR processing | Report resolves without error on `processing_by_hr` stage | `test_regression_processing_by_hr_stage_report_resolves` |
| Full green path | `transfer_allowed=true`, `handoff_create_allowed=true`; `assert_transfer_allowed` returns `{}` | `test_regression_full_green_allows_stage_and_handoff` |
| Stage gate integration | PATCH stage `ready_for_handoff` returns 409 until policy allows, then 200 | `test_stage_change_blocked_until_transfer_policy_allows` |
| Transfer-readiness API | Returns `policy_version` + grouped `blocking_reasons` contract | `test_transfer_readiness_endpoint_returns_policy_contract` |

### Manual smoke (optional)

1. Open candidate on `docs_got` — **Transfer readiness** panel loads.
2. Attempt stage → **Ready for handoff** while red — toast + scroll to `#section-transfer-readiness`.
3. Fix blockers (upload, verify, confirm block) — panel turns green; stage change succeeds.
4. Disable tenant link handoff — stage still allowed; **Create handoff** shows blocked.
