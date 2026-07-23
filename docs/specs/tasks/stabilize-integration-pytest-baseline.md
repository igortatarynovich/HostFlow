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

## Two tracks

1. **Product Track (active):** [acquisition-stage-3e-activity-timeline.md](acquisition-stage-3e-activity-timeline.md)  
2. **Engineering Track (background):** this doc + [#127](https://github.com/igortatarynovich/HostFlow/pull/127) when capacity allows; then opportunistic C2.3 stack merge.

C2.4 remains **frozen**.

## Clustering (kept for Engineering Track)

Evidence: [CI run 29832741203](https://github.com/igortatarynovich/HostFlow/actions/runs/29832741203) — 657 failed / 1926 passed.

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

## Explicitly out of Product Track

- Mass xfail/skip to fake green  
- Stopping Acquisition 3E / Flight Runtime for this debt  
- Mixing stabilize work into Flights PRs  
