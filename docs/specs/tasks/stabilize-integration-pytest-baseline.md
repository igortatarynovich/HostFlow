# stabilize(integration): restore full backend pytest baseline

**Status:** Deferred — **Engineering Track** (does not block Product Track)  
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

**Figures are dated (2026-07-21) and must be re-measured before any release claim.** Later recorded observation on the E1 slice was **484 failed / 2740 passed** (see [queue](sales-to-comms-sequential-queue.md) § E1 close-out), i.e. the aggregate moved without anyone owning the delta. An aggregate that drifts is not a baseline: [Release Readiness Gate](../gates/release-readiness-gate.md) **RR6** requires an *enumerated, frozen, owned, non-growing* known-failure list plus a named set of suites that must be green for a release build. Re-measurement needs a scratch database — `backend/tests/conftest.py` refuses to run against a DB whose name does not contain `test` (guard `_assert_not_production_db`), so the number cannot be taken from a developer’s dev database.

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

## Explicitly out of Product Track

- Mass xfail/skip to fake green  
- Stopping Acquisition 3E / Flight Runtime for this debt  
- Mixing stabilize work into Flights PRs  
