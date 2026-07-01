# CI Gates (Phase 0 #7)

HostFlow's CI enforces three quality floors on every PR:

1. **Backend test coverage** — ratchet baseline (target 60%).
2. **Frontend test coverage** — ratchet baseline (target 40%).
3. **Frontend bundle-size budget** — total + per-chunk budget (no target; just
   no regressions without explicit review).

All three use the same philosophy: **never silently regress**. Each gate reads
a committed baseline; the baseline can only be bumped via a reviewable PR.

## Backend coverage

*Source of truth*: `backend/.coverage-baseline` (single float, 0-100).

*Tool chain*: `pytest-cov` → `coverage.xml` (Cobertura) → custom gate.

```
# CI step (see .github/workflows/backend-ci.yml)
pytest -q \
  --cov=backend/app \
  --cov-config=.coveragerc \
  --cov-report=term \
  --cov-report=xml:coverage.xml
python backend/scripts/check_coverage.py
```

Config:
- `backend/.coveragerc` — declares source scope (`backend/app`) and excludes
  auto-generated / deprecated files.
- `backend/scripts/check_coverage.py` — reads `coverage.xml`, compares against
  `.coverage-baseline` with a 0.5pp tolerance, prints the gap to the
  aspirational target (60%).

Ratchet workflow:
```
# after adding tests
pytest --cov=backend/app --cov-report=xml:backend/coverage.xml
python backend/scripts/check_coverage.py --write-baseline
git commit -m "chore(ci): ratchet backend coverage baseline to X%"
```

## Frontend coverage

*Source of truth*: `hostflow-frontend/.coverage-baseline`.

*Tool chain*: `@vitest/coverage-v8` → `coverage/coverage-summary.json` →
custom gate.

```
# CI step (see .github/workflows/frontend-static-qa.yml)
npm run test:coverage      # vitest run --coverage
npm run coverage:check     # node scripts/check-coverage.mjs
```

Config:
- `hostflow-frontend/vitest.config.ts` — `coverage.provider='v8'`,
  `reporter=['text','json-summary']`. The `json-summary` reporter emits
  `coverage/coverage-summary.json` which the gate consumes (total.lines.pct).
- `hostflow-frontend/scripts/check-coverage.mjs` — same ratchet semantics as
  the backend.

Ratchet workflow:
```
npm run test:coverage && npm run coverage:check -- --write
git commit -m "chore(ci): ratchet frontend coverage baseline to X%"
```

## Bundle-size budget

*Source of truth*: `hostflow-frontend/.bundle-budget.json`.

*Tool chain*: `vite build` → `dist/assets/*.js` → custom gate.

```
# CI step (see .github/workflows/frontend-static-qa.yml)
# qa:static already runs `npm run build`
npm run bundle:check       # node scripts/check-bundle-size.mjs
```

The budget file declares two layers:

1. **`total`** — caps combined `raw` and `gzipped` size across every chunk.
   Triggers whenever a dependency upgrade balloons the total payload.
2. **`entryPoints[]`** — per-chunk budgets matched by regex on the hashless
   filename (e.g. `^index-`, `^vendor-react-core-`,
   `^routeBundleCrmCore-`). Catches single-chunk regressions that hide
   inside a stable total.

Current numbers (2026-04-18 post Phase 0):

| layer | raw | gzipped |
| --- | ---: | ---: |
| total | 7.67 MB | 1.50 MB |
| budget (total) | 8.00 MB | 1.60 MB |
| `index-*` (main entry) | 1.99 MB | 495.8 KB |
| `vendor-recharts-*` | 891.5 KB | 200.7 KB |
| `routeBundleCrmCore-*` | 983.6 KB | 160.5 KB |

Raising a budget requires a reviewer who can justify the perf cost. Typical
mitigations before raising:

- Lazy-load routes (`React.lazy` + `Suspense`).
- Tree-shake icons / date-fns / lodash per-import.
- Dedupe dependency versions (`npm dedupe`; fix peer-range drift).
- Move analytics-heavy pages off the critical entry.

## Aspirational targets vs. baselines

The audit plan (`docs/HOSTFLOW_AUDIT_AND_PLAN.md` → Phase 0 #7) sets:

| gate | current baseline | target |
| --- | ---: | ---: |
| backend coverage | **35.00%** | 60% |
| frontend coverage | **5.00%** | 40% |
| bundle-size (total raw) | 8.00 MB | trend down |
| bundle-size (total gzipped) | 1.60 MB | trend down |

The gap to target is printed in every CI run — no need to track it externally.

## Adding tests that count toward coverage

- **Backend**: any file under `backend/app/**` reached by tests in
  `backend/tests/` counts. Migrations, `app.main.py`, and `app.scanner/*` are
  explicitly excluded in `.coveragerc` because they are exercised only by
  integration flows we cannot run inside unit-test CI.
- **Frontend**: any `src/**/*.{ts,tsx}` reached by a `*.test.{ts,tsx}` under
  `src/` counts. Generated code, setup files, and test files themselves are
  excluded (see `vitest.config.ts`).

Rule of thumb: aim every new module to ship with at least one unit test
covering the happy path and one for the most obvious failure — this alone
should close the gap to the 60%/40% targets within a quarter of PRs.
