# Alembic RLS downgrade tech debt

Status: **open** (integration base; not blocking Stage 1A)

## Problem

Several HR/workforce migrations use invalid PostgreSQL syntax in `downgrade()`:

```sql
ALTER TABLE <table> NO ROW LEVEL SECURITY;
```

PostgreSQL requires:

```sql
ALTER TABLE <table> DISABLE ROW LEVEL SECURITY;
```

Full `alembic downgrade base` therefore fails when these revisions run in reverse order.

## Impact

| Scenario | Blocked? |
|----------|----------|
| Fresh DB `alembic upgrade head` | No |
| Stage 1A local upgrade/downgrade range | No |
| Prerequisite (`202605121350`) roundtrip | No |
| Full historical `alembic downgrade base` | **Yes** |
| Future CI full roundtrip gate | **Yes** (if enabled) |

Stage 1A merge gate does **not** require full downgrade-to-base. This item must still be fixed on the integration line before any CI job enforces full roundtrip.

## Affected revisions

| Revision file | Table | Invalid statement |
|---------------|-------|-------------------|
| `202605151300_workforce_zus_workspace_tasks.py` | `workforce_zus_workspace_tasks` | `NO ROW LEVEL SECURITY` |
| `202605161400_workforce_work_eligibility_pr4.py` | `workforce_work_eligibility_profiles` | `NO ROW LEVEL SECURITY` |
| `202605170900_workforce_work_eligibility_payment_requirements.py` | `workforce_work_eligibility_payment_requirements` | `NO ROW LEVEL SECURITY` |

Canonical pattern elsewhere in the repo: `DISABLE ROW LEVEL SECURITY` (see `202605250001_hr_document_control_tasks.py`, `202605122000_hr_workforce_core_tables.py`).

## Required fix (separate task)

1. Replace `NO ROW LEVEL SECURITY` with `DISABLE ROW LEVEL SECURITY` in each affected `downgrade()`.
2. Keep policy drops (`DROP POLICY IF EXISTS ...`) before disable, matching working migrations.
3. Verify locally: `alembic upgrade head` then stepped downgrade through each affected revision on PostgreSQL.
4. Do **not** bundle into Stage 1A PRs; land on `feat/documents-runtime-expiry-engine` or a dedicated integration-base fix PR.

## Acceptance

- `alembic downgrade -1` from head through each listed revision succeeds on PostgreSQL.
- No change to `upgrade()` RLS enablement behavior.
- Document closed when fix merges and optional roundtrip CI waiver is removed.
