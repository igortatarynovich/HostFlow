# stabilize(integration): restore full backend pytest baseline

**Status:** Deferred for the *fix*; **QB-1 (freeze the known-failure list) is owned and release-relevant** — see § QB-1. Engineering Track; does not block Product Track  
**Branch:** `stabilize/integration-pytest-baseline` ([PR #128](https://github.com/igortatarynovich/HostFlow/pull/128) — parked)  
**Base:** `integration/release-product-a-b`

## Verdict (2026-07-21 · confirmed 2026-07-23)

The **~650+** full-suite failures observed after SPA/docs/axios unblocked (and again after Stage 4 CI unblocks on #148–#151) are **base-known integration debt**, same class as [`acquisition-epic-p-base-known-ci-failures.md`](acquisition-epic-p-base-known-ci-failures.md):

**Stage 4 attribution (2026-07-23):** Stage 4 contract suites pass; Stage 4 security/docs/frontend gates pass; full `backend-ci` suite remains red **before and outside** Stage 4 product scope. Repo owner accepted merge of #148–#151 without attributing that suite debt to Flight Runtime.

| Check | Finding |
|-------|---------|
| Caused by C2.3 / Flights product PRs? | **No** — failures are on integration tip + CI-unblock; not Campaign product code |
| Alembic single head? | **Yes** — `check_alembic_heads` OK |
| Clean deploy / new module bootstrap broken by us? | **No evidence** — cluster is legacy schema/fixture/async lifecycle |
| Blocks Product Track (Flights / Acquisition 3E)? | **No** |

Therefore: **do not** spend a product week fixing 657 historical tests. Keep full pytest as the long-term Engineering gate; do **not** weaken it with mass xfail — just **do not stop Flights** for it.

**CI posture (2026-08-23):** full suite + coverage ratchet moved off the PR path into [`.github/workflows/backend-regression.yml`](../../../.github/workflows/backend-regression.yml) (nightly / `integration` push). Named gates stay in [`backend-ci.yml`](../../../.github/workflows/backend-ci.yml) as parallel path-filtered jobs. See [`ci_gates.md`](../quality/ci_gates.md). This does **not** close the stabilize slice.

## Two tracks

1. **Product Track (active):** [acquisition-stage-3e-activity-timeline.md](acquisition-stage-3e-activity-timeline.md)  
2. **Engineering Track (background):** this doc + [#127](https://github.com/igortatarynovich/HostFlow/pull/127) when capacity allows; then opportunistic C2.3 stack merge.

C2.4 remains **frozen**.

## Clustering (kept for Engineering Track)

Evidence: [CI run 29832741203](https://github.com/igortatarynovich/HostFlow/actions/runs/29832741203) — 657 failed / 1926 passed.

**Figures on this line are historical.** The sequence recorded was 657 failed / 1926 passed (2026-07-21) → 484 failed / 2740 passed (E1 close-out) → **371 failed / 3164 passed (2026-08-28, `255279fc`)**, i.e. the aggregate moved three times without anyone owning the delta. An aggregate that drifts is not a baseline: [Release Readiness Gate](../gates/release-readiness-gate.md) **RR6** requires an *enumerated, frozen, owned, non-growing* known-failure list plus a named set of suites that must be green for a release build. **Re-measured 2026-08-28 on an authorised scratch database — see § QB-1 § Measurement record.** `backend/tests/conftest.py` refuses to run against a DB whose name does not contain `test` (guard `_assert_not_production_db`), so no figure may be taken from a developer's dev database.

| Cluster | Count | Root cause | Fix layer (when Engineering resumes) |
|---------|------:|------------|--------------------------------------|
| asyncpg / event-loop lifecycle | 244 | test session/loop | `conftest` lifecycle |
| residual / generic 500 (secondary) | ~243 | cascade symptoms | after infra |
| documents schema / runtime | ~35+ | schema bootstrap | Alembic ↔ model |
| hr / funnels / seats fixtures | ~44 | outdated defaults | canonical factories |
| analytics path cwd / misc | small | stale paths / headers | targeted |

Full exception-hit notes live in the clustering commit history on PR #128.

## When to resume

Resume this slice only if:

- clean Postgres `upgrade head` fails on a product branch we own, or  
- a **new** module cannot deploy, or  
- failures are proven introduced by a Product PR (not base-known).

### Resume condition may already be met (open question, 2026-08-28)

[`AGENTS.md`](../../../AGENTS.md) § “Migration caveats” states that `alembic upgrade heads` does **not** apply cleanly to a freshly created database, and documents a manual repair sequence (pre-create `alembic_version` with a wider column, apply parallel branch tips in dependency order, skip a double-`CREATE TYPE` revision by stamping, then patch an enum value and a column default for the bootstrap seed).

If that is still true, the **first** resume condition above is satisfied and this slice is no longer merely deferred debt: [Release Readiness Gate](../gates/release-readiness-gate.md) § Release Candidate requires migrations to apply to a freshly created database **without manual repair steps**, so a fresh-install failure is a release blocker rather than background debt.

This must be **measured, not assumed** — on a scratch database, on the current trusted base — and the result recorded here. The owning slice for the fix belongs to the launch/operations program (fresh-install bootstrap), not to this brief; this brief keeps the pytest side.

## QB-1 — freeze the known-failure list (RR6 evidence, decided 2026-08-28)

**Status:** owned, not scheduled. Decision recorded in the [unowned work register](../gates/v1-unowned-work-register.md) (was U-1).
**Owner:** Engineering lead.
**Estimate:** 1–2 slices.

RR6 asks whether the set of tolerated known failures is **enumerated, frozen, owned and non-growing**. Today the answer is an aggregate («~657, dated 2026-07-21»), which is not an answer: an aggregate cannot be frozen, and a number nobody owns cannot be shown not to grow. This slice replaces the number with a list.

**Authorised:** a dedicated scratch **test** database. `backend/tests/conftest.py` refuses to run against a database that does not look like a test database, which is why the figure could not be re-measured. The cheap path is a template copy of the migrated dev database rather than a fresh migration run — a fresh run hits the bootstrap failure described above, which is **OL-2's** problem, not this slice's.

**Done when:**

1. one full-suite run on the current trusted base is recorded here with date, commit and command;
2. every failure appears in a list — test id and cluster — not only in a count;
3. each cluster has a named owner and a verdict: `tolerated for v1` or `must be fixed before RC`;
4. the list is frozen: a merge that adds a failing test outside it fails the quality question, and the required-green CI workflows are named;
5. the `tolerated for v1` set has an expiry date, because a tolerated failure without an expiry becomes permanent.

**Not this slice:** fixing the failures, mass xfail, or the fresh-database bootstrap repair.

### Measurement record — 2026-08-28

| | |
|---|---|
| Commit | `255279fc` — **clean detached worktree**, no uncommitted changes |
| Database | `hostflow_qb1_test` — dev **schema only** (267 tables) stamped at head `202608250002_merge_e5_drop_and_adr036_heads`, **no data**, recreated immediately before the run |
| Command | `pytest -q --tb=no -rf -c backend/pytest.ini backend/tests`, cwd = **repo root**, `PYTHONPATH=<root>:<root>/backend` |
| Result | **371 failed · 3164 passed · 8 skipped · 4 errors**, 671 s (3543 collected) |
| Enumerated list | [`qb1-known-failures.tsv`](qb1-known-failures.tsv) — 371 rows: test id, area, cluster, hard/order-dependent, proposed owner, reason |

The stale **«~657, dated 2026-07-21»** figure is retired, and so is the intermediate 397 figure taken earlier the same day on a dirty tree from the wrong working directory.

**Three conditions had to be fixed before any number was meaningful, and each one moved the count.**

| Condition | Wrong way | Effect |
|---|---|---|
| Database freshness | reuse the scratch DB for a second run | **467 failed instead of 371.** The extra ~96 are all plan-quota errors: `monthly_leads_limit_reached`, `"limit":1500,"current":2740`. Tenant quota counters accumulate across runs, so a reused database inflates the count |
| Working directory | run from `backend/` | **+25 failures.** Those 25 read source files by repo-relative path (`Path('backend/app/api/v1/analytics.py')`) and pass from the repo root. `AGENTS.md` prescribes `backend/`, so the documented command cannot produce a clean run. **Fixed** — see below |
| Tree cleanliness | measure a dirty tree | ±1–2 tests; small, but it makes the figure non-citable |

**Order dependence is far smaller than it first appeared.** Re-running exactly the 371 ids on a *fresh* database gives 363 failed / 8 passed: only **8** are order-dependent. The earlier «54 order-dependent» reading was itself an artifact of a polluted database.

**Cause clusters** (371 rows):

| Cluster | Count | Reading |
|---|---|---|
| Assertion mismatch, behavioural | 205 | The long tail. Spread over 160 files; only 16 files have ≥5 failures, so no single fix collapses it |
| Requirement / document runtime | 38 | «Missing runtime item for passport», linked-document validity — RPM and Documents surface |
| `Internal Server Error` (500) | 27 | Customer-visible failures; per-endpoint triage |
| Test-double / API drift | 21 | Tests stale against changed signatures |
| `IntegrityError` on shared fixtures | 17 | Fixture collisions on the one shared database |
| Plan / quota exhausted | 14 | Residual self-pollution *within* a single run |
| `Method Not Allowed` (405) | 11 | Tests expect routes that do not exist |
| `Not Found` (404) | 7 | Same, for resources |
| Authz / module gate | 6 | Role or module-enablement expectations |
| `MissingGreenlet` | 5 | Async lifecycle in sync context |
| Stale pinned alembic head | 2 | `test_alembic_has_single_head` asserts the literal revision `202607131402` is head. **Alembic really does have one head** — the tests pin an obsolete id |
| Model re-import collision, SQL schema mismatch, `ImportError`, misc | ~18 | Individually small |

**Proposed owner routing.** The failures concentrate in exactly the v1 blocker paths, so they are routed to the briefs that will touch that code rather than to one stabilisation task:

| Proposed owner | Rows | Verdict proposed |
|---|---|---|
| [HH — Recruitment → HR handoff](recruitment-hr-minimal-handoff.md) | 100 | triage inside the brief; blocker path |
| [RPM-1 / Documents](requirement-policy-management.md) | 61 | triage inside the brief; blocker path |
| [HE — Hiring E2E](hiring-workflow-e2e.md) | 52 | triage inside the brief; blocker path |
| [MA — Mapping Authority](mapping-authority.md) | 45 | triage inside the brief; blocker path |
| TEST-INFRA — Engineering lead | 42 | **must be fixed before RC** — quota accumulation, fixture collisions, stale head pins, order dependence. These make the suite unmeasurable, which is the RR6 obstacle itself |
| [FP — Forms Publish](external-intake-forms-publish.md) | 22 | triage inside the brief; blocker path |
| [TI — isolation & boundary enforcement](tenant-isolation-enforcement.md) | 5 | **must be fixed before RC** — see that brief; these are true negatives |
| UNROUTED | 44 | Fleet, calendar, invoices, analytics, org units, company module settings — outside the six blockers. **`tolerated for v1`, decided 2026-08-28, expiry 2027-01-31**, owner Engineering lead, non-growing ([register](../gates/v1-unowned-work-register.md) § Quality debt) |

**Two findings inside the noise that are not noise.** A 371-failure baseline hides true negatives, and two were found by reading the tail:

1. `tests/api/test_tenant_isolation.py` — «Should NOT see tenant 2's candidate with tenant 1 context». This is real; see [tenant-isolation-enforcement.md](tenant-isolation-enforcement.md).
2. `tests/module_registry/…::test_p2_no_new_direct_legacy_module_flag_reads` — an architecture guard that is currently red, i.e. a live boundary violation. It is the enforcement gap that [module-ownership-coverage.md](../gates/module-ownership-coverage.md) predicted.

This is the argument for RR6 in one line: while the baseline is an unowned aggregate, a security regression and a red architecture guard are indistinguishable from 369 other red lines.

**Caveats to state with any use of these numbers.** The run used a data-less schema copy, so anything depending on seeded plan or licence rows starts differently from CI; four collection **errors** are counted separately from the 371 and still need naming; and the whole measurement is single-environment. It is the **measurement of record**, and the correct input to RR6 — not yet the frozen list.

**Routing accepted 2026-08-28.** Each blocker brief takes the failing tests on its own path as an entry condition; TEST-INFRA (42) and TI (5) are fix-before-RC; the 44 unrouted are tolerated to 2027-01-31 and may not grow.

### TEST-INFRA progress

**Working-directory independence and stale head pins — fixed** on `fix/test-suite-reproducibility` (2026-08-29, based on `b67fe4e2`):

| Change | Effect |
|---|---|
| 27 repo-relative `Path("backend/…")` source reads in 10 test files now resolve through `backend/tests/test_support/repo_paths.py`, anchored on `__file__` | The suite returns the **same** failure set from `backend/` and from the repo root. The `FileNotFoundError` cluster is gone (25 → 0) |
| Three tests asserted that *their own* migration is the current head (`202607131402`, `202607180009_forms_s6`, the Stage-3E revision). They now assert a single head plus reachability in `alembic history` | Two of them go green; the third had been silently **skipping** whenever `.venv312` was not at the expected path, and now resolves the executable via `PATH` so it actually runs |

Verification: full suite from `backend/` on a freshly created database gives **370 failed / 3169 passed** against the 371 measured from the repo root — the two sets differ only by the two repaired head-pin tests, plus one unrelated Sales regression that arrived in `b67fe4e2` (see below). Before the change the same command from `backend/` gave 397.

**Not fixed, and now understood:** four migration round-trip tests (`test_forms_sprint6_alembic_roundtrip`, `test_forms_sprint3_alembic_roundtrip`, `test_alembic_downgrade_upgrade_roundtrip`, `test_epic_p_alembic_pr3_downgrade_upgrade_roundtrip`) cannot pass in the shared suite at all: each downgrades to its own predecessor, which on today's graph unwinds every later migration, and the downgrade aborts on `ck_users_supervisor_role` because the database holds rows. They can only assert reversibility on a throwaway database, which depends on fresh-database migrations working — **OL-2**. They stay in the tolerated set with that dependency named, not as mystery failures.

**Regression found while verifying (not part of this fix):** `b67fe4e2` «fix(sales): open existing client instead of creating a duplicate» makes `tests/modules/sales/test_convert_entrypoints_contract.py::test_missing_review_blocks_both_endpoints` fail with «DID NOT RAISE HTTPException». The file passes 9/9 at `255279fc` and 8/9 at `b67fe4e2` on an identical fresh database, so the guard that blocked conversion without a review is no longer firing. Owner: whoever owns the Sales convert entrypoints.

**Monthly lead quota — fixed** on the same branch. The cap counts `leads` rows created in the current calendar month and the suite never deletes them, so every run inherited the previous run's total: a second run against the same database reported **467** failures instead of 371, 152 of them `monthly_leads_limit_reached`. The test tenant is now granted quota through the product's own `pack_addons_v1.monthly_leads_cap` field in `backend/tests/conftest.py`, so `resolve_monthly_leads_cap` is still exercised exactly as in production and the unit tests that pin the plan caps are untouched.

**Measurement protocol — scripted.** `scripts/testing/measure-known-failures.sh` recreates a scratch database from the schema of an already-migrated one, runs the full suite from the repo root, and writes a sorted failure-id list. The schema is cloned rather than migrated because `alembic upgrade heads` still does not apply to an empty database (**OL-2**); when that is fixed the script should migrate instead.

**Reproducibility — proven.** Two consecutive runs of that script on commit `9c8296d4` produced **370 failed / 3172 passed / 7 skipped / 4 errors** with **identical** failure-id sets. This is the reproducible measurement RR6 asks for, and it replaces the 371 recorded at `255279fc`: two alembic-pin tests were repaired and one Sales regression arrived in `b67fe4e2`.

**Newly exposed, not fixed — the database is still shared state.** With the quota accumulation gone, a *reused* database no longer inflates the count but still does not match a fresh one: 54 tests fail on a fresh database and pass on a warm one (HR dashboard, workforce, handoff, ZUS), and 20 fail only on a warm one (Meta credentials, communication accounts, funnel and document-type fallback resolvers). Both directions are the same defect — tests depend on, and mutate, rows that outlive the run — and the fresh-database result is the honest one. Hence the protocol above is normative for any figure quoted at a gate: **a number measured on a reused database is not evidence.** Removing the coupling itself is separate quality debt, tracked in the [unowned work register](../gates/v1-unowned-work-register.md).

**What remains for QB-1:** the same run reproduced in CI on a freshly created database, and the named required-green workflows. Until CI reproduces it, the list is the measurement of record but not yet frozen.

## Explicitly out of Product Track

- Mass xfail/skip to fake green  
- Stopping Acquisition 3E / Flight Runtime for this debt  
- Mixing stabilize work into Flights PRs  
