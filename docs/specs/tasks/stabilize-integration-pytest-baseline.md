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

**Figures on this line are historical.** The sequence recorded was 657 failed / 1926 passed (2026-07-21) → 484 failed / 2740 passed (E1 close-out) → **397 failed / 3136 passed (2026-08-28)**, i.e. the aggregate moved three times without anyone owning the delta. An aggregate that drifts is not a baseline: [Release Readiness Gate](../gates/release-readiness-gate.md) **RR6** requires an *enumerated, frozen, owned, non-growing* known-failure list plus a named set of suites that must be green for a release build. **Re-measured 2026-08-28 on an authorised scratch database — see § QB-1 § Measurement record.** `backend/tests/conftest.py` refuses to run against a DB whose name does not contain `test` (guard `_assert_not_production_db`), so no figure may be taken from a developer's dev database.

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
| Commit | `8d594e3f` (`integration/release-product-a-b`) |
| Database | `hostflow_qb1_test` — production **schema only** (267 tables) stamped at head `202608250002_merge_e5_drop_and_adr036_heads`, **no production data** |
| Command | `pytest -q --tb=no -rf` from `backend/`, `PYTHONPATH=<repo>:<repo>/backend` |
| Result | **397 failed · 3136 passed · 7 skipped**, 663 s |
| Enumerated list | [`qb1-known-failures.tsv`](qb1-known-failures.tsv) — 397 rows: test id, area, isolated re-run outcome |

The stale **«~657, dated 2026-07-21»** figure is retired. It is replaced by an enumerated list, and the count is **397**, not 657.

**The single most important finding: 54 of the 397 pass when re-run alone.** A second run of exactly those 397 ids gave 343 failed / 54 passed. Those 54 are not broken code — they are order-dependent, because the suite shares one database and accumulates rows across tests.

**Cause clusters** (from a `--tb=line` re-run of the 397):

| Cluster | Count | Reading |
|---|---|---|
| Plan / quota limits reached (`monthly_leads_limit_reached`, `lead_sources_limit_reached`, `communication_channels_limit_reached`, `seat_limit_reached`) | ~100 | **Shared-state artifact.** One case shows `"limit":3,"current":79` — earlier tests exhausted the tenant plan. This is the suite polluting itself, not a defect |
| `Internal Server Error` (500) | 21 | Real defects, need per-endpoint triage |
| `IntegrityError` on insert | 17 | Fixture collisions on the shared database |
| `Method Not Allowed` (405) | 14 | Tests expect routes that do not exist — either stale tests or unshipped endpoints |
| `SimpleNamespace has no attribute 'get'` and similar | ~12 | Test-double drift against changed signatures |
| Requirement / document runtime («Missing runtime item for passport», «No blocker for passport», linked-document validity) | ~23 | Requirement rules and document runtime; overlaps RPM and Documents |
| `MissingGreenlet` | 5 | Async lifecycle in sync context |
| Remaining long tail | ~100 | Individually small signatures |

**Areas:** `tests/api` 243 (52 order-dependent) · `tests/services` 41 · `tests` 31 · `tests/document_runtime` 24 · `tests/requirement_rules` 23 · `tests/modules` 10 · the rest ≤5 each.

**Caveats that must be stated with any use of this number.** The measurement ran on a data-less schema copy, so anything that depends on seeded plan or licence rows starts from a different place than CI does; and the suite shares one database, which is itself the cause of the largest cluster. The list is therefore the **measurement of record for this environment** and the correct starting point for RR6 — not yet the frozen list. Freezing requires two things this run cannot supply: the same measurement in the CI environment, and a per-cluster owner verdict.

**What remains for QB-1:** per-cluster owner and verdict (`tolerated for v1` / `must be fixed before RC`) with expiry on the tolerated set; the same run reproduced in CI; and the named required-green workflows. Fixing the shared-database accumulation would delete the largest cluster outright and is the highest-value single action.

## Explicitly out of Product Track

- Mass xfail/skip to fake green  
- Stopping Acquisition 3E / Flight Runtime for this debt  
- Mixing stabilize work into Flights PRs  
