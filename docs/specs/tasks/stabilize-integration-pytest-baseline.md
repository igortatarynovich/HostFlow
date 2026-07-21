# stabilize(integration): restore full backend pytest baseline

**Status:** Active — failure clustering complete; infrastructure fixes next  
**Branch:** `stabilize/integration-pytest-baseline`  
**Base:** `integration/release-product-a-b`  
**Frozen:** C2.4 Scheduling — do not start until this slice merges, then #127, then C2.3 stack (#121–#126)

## Goal

Restore **full** `backend-ci` pytest on `integration/release-product-a-b` to green **without** changing C2.3 product behavior.  
Do **not** weaken the merge gate, mass-xfail, or expand allowlists without a documented reason.

## Evidence source

| Item | Value |
|------|--------|
| CI run | [29832741203](https://github.com/igortatarynovich/HostFlow/actions/runs/29832741203) |
| Context | PR [#127](https://github.com/igortatarynovich/HostFlow/pull/127) (`chore/ci-unblock-c2-3-stack`) after SPA/docs/axios unblocked earlier steps |
| Totals | **657 failed**, 1926 passed, 116 skipped, **5 errors** (~10 min) |
| Note | Proxy for integration debt: early gates (SPA, Alembic heads, REF-3.1) already green on that run; pytest is the remaining red |

Parsed summary lines: **662** (FAILED + ERROR).

## Failure clustering

| Cluster | Count | Root cause | Fix direction (SoT first) |
|---------|------:|------------|---------------------------|
| asyncpg / event-loop lifecycle | 244 | Test infrastructure: connection/session reused across loops; `another operation is in progress` / Future on different loop | Shared async fixture lifecycle: one engine/loop policy, dispose between tests; **do not** rewrite product code to silence |
| residual assertions (secondary) | 130 | Mixed symptoms after cascades | Re-run after layers 1–4; re-bucket before local patches |
| generic HTTP 500 (secondary) | 113 | Mixed — often schema/funnel/modules underneath | Same: secondary triage after bootstrap layers |
| document runtime / hub bridges | 30 | Depends on `documents` schema + runtime contracts | After schema layer green |
| Forbidden / Not Found / ACL | 25 | Fixtures: roles, permissions, routes | Canonical ACL bootstrap |
| schema drift: other UndefinedColumn | 19 | Model ↔ DB mismatch | Inventory columns vs Alembic; migration or model SoT |
| company modules: hr not enabled | 18 | Default company fixture lacks `hr` module | Enable required modules on canonical company factory |
| funnel resolver / missing funnel | 17 | Missing seeded recruitment/HR funnels | Seed funnels in company/tenant fixture per resolver SoT |
| communications / dispatch | 13 | Fixtures / session cascade | Re-check after asyncpg layer |
| handoff / transfer policy | 12 | Funnel + docs + policy deps | After schema + funnel |
| next_action suites | 8 | Likely asyncpg/session cascade | Expect collapse after lifecycle fix; do not rewrite NA expectations first |
| billing / seat_limit_reached | 6 | Plan/license fixture defaults → `limit: 0` | Canonical plan with non-zero seats |
| schema drift: `documents.status` | 5 | Model has `Document.status`; DB/migration path incomplete or not applied in failing contexts | Align Alembic ↔ `Document` model; verify `upgrade head` on clean Postgres |
| ERROR setup/teardown | 5 | Fixture cleanup = same asyncpg class | Lifecycle fix |
| HR/workforce contracts | 4 | Module enablement | Same as hr-not-enabled |
| billing / lead_sources_limit | 3 | Plan entitlements for Meta sources | Canonical entitlements in bootstrap |
| ADR-022 intake fixtures | 3 | Intake form/policy seed incomplete | Seed per ADR-022; do not weaken assertions |
| analytics funnel path tests | 3 | Tests open `Path("backend/app/...")` with `cwd=backend` → false FileNotFoundError (files exist) | Fix test paths to repo-root or `app/...` — not delete product code |
| leads CSV import | 2 | Often depends on funnel/plan | After G/E |
| meta webhook signature | 1 | Test client missing signature headers | Sign per current security contract |
| working-hours / timeoff / planner | 1 | Time policy / tz | After datetime + fixtures |

### Exception signature frequency (log hits, not unique tests)

| Signature | Hits (approx.) | Maps to |
|-----------|---------------:|---------|
| asyncpg `another operation is in progress` | 588 | Lifecycle |
| `relation "documents" does not exist` | 261 | Schema bootstrap / migration apply |
| asyncio Future on different loop | 196 | Lifecycle |
| `column documents.status does not exist` | 143 | Schema drift |
| FileNotFoundError (source contract paths) | 58 | Path cwd (analytics cluster) |
| `hr module is not enabled` | 36 | Module defaults |
| naive vs aware datetime | 16 | Shared time utilities |
| `seat_limit_reached` | 12 | Plan seats |
| `lead_sources_limit_reached` | 6 | Plan entitlements |
| RecruitmentFunnelNotFound | 3 | Funnel seed |
| `require_elevated_reason_or_raise` arity | 2 | Real API call-site regression |
| Missing signature header | 2 | Meta webhook test headers |

## Source of truth (before changing tests)

| Cluster | Model / code SoT | Migrations | Docs | Test bootstrap |
|---------|------------------|------------|------|----------------|
| `documents` / `documents.status` | `backend/app/models/document.py` (`Document.status`) | `cd530c0f2042_initial_schema` + later doc migrations; single head `202607210002_comm_automation_domain_c2_2` | Document Hub / ADR-009 family | Must `alembic upgrade head` on CI Postgres; investigate why relation missing mid-suite |
| Seats / lead sources | License/plan models + billing gates | Plan seed migrations | Billing / plan docs | `conftest` + factories must set non-zero seats/entitlements |
| HR module | Company `enabled_modules` | Module settings | ADR-002 / HR module-scope | Default company factory enables `hr` where HR tests require it |
| Funnels | Funnel resolver services | Funnel tables | Recruitment funnel docs | Seed agency funnel for default company |
| Async lifecycle | `backend/app/db/session.py` | n/a | n/a | `backend/tests/conftest.py` — **primary fix target** |
| Analytics path tests | Files **exist** under `backend/app/...` | n/a | M5 analytics | Fix Path cwd — tests are wrong, not product |

**Rule:** do not rewrite expectations to match a broken DB/fixture. Fix bootstrap or product to match SoT.

## Fix layers (locked order)

1. **Alembic + schema bootstrap** — clean `upgrade head`; `documents` (+ `status`) present; single head retained  
2. **Async DB lifecycle** — kill the 244+ asyncpg/loop failures (and many ERROR teardown)  
3. **Shared fixtures/factories** — seats, modules (`hr`), funnels, plan entitlements  
4. **Shared policies/defaults** — datetime tz, elevated-reason call sites if still broken  
5. **Real module regressions** — only what remains after 1–4  
6. **Singletons** — meta signature header, path-based analytics tests, leftovers  

One infrastructure fix should clear tens/hundreds of failures. Prefer that over 657 local patches.

## Definition of Done

- [ ] Full backend pytest green on this branch (CI `backend-ci`)  
- [ ] Alembic single head; clean Postgres `upgrade head`  
- [ ] Suite order-independent (re-run twice)  
- [ ] Merge this PR into `integration/release-product-a-b`  
- [ ] Rebase/merge [#127](https://github.com/igortatarynovich/HostFlow/pull/127)  
- [ ] Rebase [#121](https://github.com/igortatarynovich/HostFlow/pull/121)–[#126](https://github.com/igortatarynovich/HostFlow/pull/126); green CI  
- [ ] Only then: C2.3 Closed; C2.4 may start  

## Explicitly out of scope

- C2.4 Scheduling product work  
- Weakening full pytest merge gate  
- Mass `xfail` / `skip`  
- Campaign UI / C2.3 feature changes  
- Allowlist expansion without a documented exception (REF-3.1 style)
