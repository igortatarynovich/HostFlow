# Epic P — integration base-known CI failures

**Status:** evidence record for Epic P DoD (PR-4)  
**Purpose:** prove that CI `UNSTABLE` on Epic P PRs against `integration/release-product-a-b` is caused by **pre-existing base failures**, not by Stage 3D.

Epic P DoD does **not** require fixing the entire integration CI surface. It requires:

1. Epic P contract suites green.  
2. No **new** failures introduced by Epic P paths.  
3. Known base failures are named and reproducible.

---

## Evidence source

PR [#31](https://github.com/igortatarynovich/HostFlow/pull/31) CI (mergeable but `UNSTABLE`) on base `integration/release-product-a-b`:

| Check | Fingerprint (outside Epic P) |
|-------|------------------------------|
| `backend-ci` / SPA path literals | `app/modules/leads/schemas.py` · `app/services/communication_deliveries/questionnaire_email.py` · `app/services/recruitment_setup_readiness.py` · `app/services/search_workspace_service.py` — `/app/...` literals |
| `docs-gates` | Broken links in `ADR-018`, `ADR-023` (`sales/module-scope.md`, `client-to-cash-flow…`), `intake-form-purpose-phase1-backend.md` |
| `security-gates` / Threat model docs | Pre-existing docs gate on integration (not Epic P migrations/services) |

These files are **not** part of Epic P Stage 3D code (see gate test `test_base_known_ci_failures_still_outside_epic_p_surface`).

---

## Epic P non-regression rule

Epic P owned paths must not add:

- SPA `/app/...` string literals  
- new docs governance broken links in Epic P docs (relative links must resolve)  
- additional Alembic heads  

Enforced by: `backend/tests/api/test_stage_3d_epic_p_gates.py`.

---

## Required green suites (DoD)

```text
test_stage_3a_campaign_foundation.py
test_stage_3b_form_intake_binding.py
test_stage_3c_universal_submission_routing.py
test_stage_3d_outcome_attribution.py
test_stage_3d_outcome_lifecycle.py
test_stage_3d_kpi_aggregates.py
test_stage_3d_epic_p_contract.py
test_stage_3d_epic_p_gates.py
```

Full-repo green is **not** a hard Epic P DoD while integration carries the base-known failures above.

---

## History

- 2026-07-18: Recorded as PR-4 DoD evidence after merge of #31–#33.
