# REF-4 Phase 2 Integrations Slice Scan Report

Status: `PASS_WITH_BASELINE_NOTE`  
Date: 2026-05-29  
Slice: `REF-4.P2.5` (`Integrations`)

Related:
- `docs/specs/gates/ref4_phase2_integrations_slice_gate.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`

## 1. Target Scan

Command:

```bash
cd /opt/HostFlow && rg -n \
  "normalize|mapping|meta|webhook|intake|country|citizenship|document_type|ReferenceServiceFacade|from backend.app.modules|from backend.app.services\\.(hr_|recruitment_|workforce_)|dictionary|legacy|load_config\\(" \
  backend/app/api/public/intake.py \
  backend/app/api/v1/communications/_helpers/telegram_intake/*.py \
  backend/app/modules/leads/*.py \
  backend/app/modules/leads/service/*.py \
  backend/app/services/*intake*.py \
  backend/app/services/*lead*.py
```

## 2. Direct-Access Findings

`Must-fix / boundary gaps`:
1. `backend/app/api/public/intake.py`  
   blocker-1 fixed in this step: direct imports from `backend.app.modules.documents.*` replaced with `document_hub_delivery_contract` adapter calls.
2. `backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py`  
   blocker-1 fixed in this step: direct `backend.app.modules.documents.*` imports replaced with `document_hub_delivery_contract` adapter calls.
3. `backend/app/api/public/intake.py` and `backend/app/api/v1/communications/_helpers/telegram_intake/intake_state.py`  
   blocker-2 fixed in this step: inbound `citizenship`/country fields are normalized through integration-level helper backed by `ReferenceServiceFacade` (`normalize_country_alpha2`, `normalize_citizenship_alpha2`), replacing local `.upper()` assumptions in integration entrypoints.
4. `backend/app/modules/leads/normalizer.py` and related leads ingest paths  
   blocker-3 fixed in this step: country/geo-country mapping switched to integration inbound normalizer path (`integration_inbound_normalization.py`) to remove duplicate normalization surfaces in ingest entrypoints.

`Allowed baseline hits`:
1. local scalar normalizers for generic primitives (email/phone/bool/text cleanup) are not reference-layer violations by themselves;
2. module-internal imports within `backend.app.modules.leads` are expected and not cross-module violations.

## 3. Facade Adoption Gaps

1. integrations entrypoints for documents now use delivery contracts (blocker-1 closed);
2. canonical reference normalization for inbound `country/citizenship` now uses integration helper backed by facade (blocker-2 closed);
3. duplicate normalization surfaces for inbound country/citizenship in intake/leads/telegram paths are consolidated behind integration-level normalizer (blocker-3 closed).

## 4. Target Test Pack

Command:

```bash
cd /opt/HostFlow && pytest -q \
  backend/tests/services/test_phase1a_enforcement_guards.py \
  backend/tests/services/test_reference_service_facade.py \
  backend/tests/modules/test_meta_form_field_mapping.py \
  backend/tests/api/test_public_intake.py \
  backend/tests/api/admin/test_meta_leads.py
```

Result:
1. focused rerun after blocker-1: `20 passed`
2. focused rerun after blocker-2: `20 passed`
3. full integrations pack: pending (separate follow-up run)

## 5. Blocker-1 Remediation Evidence

Scope:
1. remove direct `backend.app.modules.documents.*` imports in integrations entrypoints;
2. switch calls to `document_hub_delivery_contract`;
3. keep intake/docs-bridge behavior unchanged.

Diff evidence:
1. `backend/app/api/public/intake.py` moved document hub calls to delivery contract (`ensure_ruleset_seed`, `list_candidate_documents`, `list_document_types`, `compute_owner_summary`, `compute_candidate_checklist`, synthetic docs builder, equivalent map, uploads helpers).
2. `backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py` moved document hub calls to delivery contract (`ensure_ruleset_seed`, `list_candidate_documents`, `compute_owner_summary`).
3. `backend/app/services/document_hub_delivery_contract.py` minimally expanded with required adapter methods.

Targeted scan evidence:
1. no `from backend.app.modules.documents` imports remain in:
   - `backend/app/api/public/intake.py`
   - `backend/app/api/v1/communications/_helpers/telegram_intake/docs_bridge.py`

## 6. Blocker-2 Remediation Evidence

Scope:
1. replace raw `citizenship/country` assumptions in integration inbound entrypoints only;
2. use integration-level inbound normalizer;
3. preserve intake/lead/telegram behavior.

Diff evidence:
1. added `backend/app/services/integration_inbound_normalization.py`;
2. helper delegates to `ReferenceServiceFacade.normalize_country_alpha2(...)` and `ReferenceServiceFacade.normalize_citizenship_alpha2(...)`;
3. `backend/app/api/public/intake.py` switched citizenship/country normalization and persistence paths to helper usage;
4. `backend/app/api/v1/communications/_helpers/telegram_intake/intake_state.py` switched citizenship parsing/persistence to helper usage.

Targeted scan evidence:
1. no local `.upper()`-based citizenship persistence remains in updated integration entrypoints;
2. normalization path is integration-helper -> reference facade.

## 7. Gate Decision

Decision: `PASS_WITH_BASELINE_NOTE`

Reason:
1. blocker-1 (`direct backend.app.modules.documents.* access`) is remediated via delivery contract;
2. blocker-2 (`raw citizenship/country handling`) is remediated via integration-level inbound normalizer backed by `ReferenceServiceFacade`;
3. blocker-3 (`duplicate normalization surfaces`) is remediated by unifying leads intake country/geo-country normalization through `integration_inbound_normalization.py`;
4. focused targeted tests are green (`20 passed`);
5. baseline note: full integrations target pack remains a follow-up run and does not affect this blocker diff decision.
