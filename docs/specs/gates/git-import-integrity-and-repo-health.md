# GIT-IMPORT-INTEGRITY & Repository Health Gate

## Why

Twice in July 2026, `integration` imported modules that were not in the tree
(`deployHosts.ts` / `ModuleHostAuthRedirect.tsx`, then `csrf.ts`), while several
CI jobs still passed. Vite build or runtime failed later. Relative-path typos
produced the same class of failure.

## GIT-IMPORT-INTEGRITY

Script: `hostflow-frontend/scripts/check_ts_import_integrity.py`

- Walks all `src/**/*.ts(x)`
- Resolves relative imports and aliases from `vite.config.ts` / `tsconfig.app.json`
- Fails if the target file/directory index does not exist
- Wired into `frontend-static-qa` **before** `npm ci`

## Repository Health Gate

Script: `scripts/repo_health_gate.py`

Run **before starting any new Product PR**:

```bash
python3 scripts/repo_health_gate.py --strict-worktrees
```

Checks: clean tree, allowed branch, FF with `origin/integration/release-product-a-b`
(when on integration), single Alembic head, no stale worktrees, no untracked
migrations, import integrity.

Exit non-zero ⇒ do not start product work; restore integrity first.
