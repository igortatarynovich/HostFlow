# Recovery material from `/tmp` plain copies (2026-07-20)

Captured from unregistered directories after HostFlow worktree audit.
**Do not merge these paths into the live Alembic chain or production app paths without a dedicated review.**

## Sources

| Source path | Contents |
|-------------|----------|
| `/tmp/hostflow-mig-stash/` | 4 Alembic revision drafts not present in any git blob |
| `/tmp/HostFlow/` | Sparse tree (5 files). Two blobs absent from object DB |

## Files

### `tmp-hostflow-mig-stash/` (unique — not in git object DB)

- `202607081200_service_orders_employee_beneficiary.py`
- `202607081300_service_order_customer_beneficiary.py`
- `202607081400_meta_form_route_service_code.py`
- `202608250001_adr018_requirement_policy_pin.py`

Note: matching `.pyc` names existed under `backend/alembic/versions/__pycache__/` on a prior local checkout, but `.py` sources were missing from the tree and from all refs.

### `tmp-HostFlow/` 

| Relative path | In object DB? | Notes |
|---------------|---------------|-------|
| `backend/app/modules/leads/admin_service.py` | **No** | Unique content — preserve |
| `hostflow-frontend/src/api/metaLeads.ts` | **No** | Unique content — preserve |
| `backend/tests/conftest.py` | Yes | Blob exists; not identical to current integration tip |
| `backend/app/core/settings.py` | Yes | Matches some `backup/adr022-*` tips |
| `scripts/check_meta_oauth_env.py` | Yes | Matches some `backup/adr022-*` tips |

## Next review steps

1. Diff each mig-stash revision against current Alembic heads and models.
2. Decide cherry-pick vs discard for `admin_service.py` / `metaLeads.ts`.
3. Only then delete the original `/tmp` directories.


## Review (2026-07-20)

See `docs/specs/gates/recovery-tmp-unique-20260720-review.md` on integration
(after merge of the integrity PR). Summary: mig-stash drafts are **not** safe
to apply on the current Alembic head; `admin_service.py` / `metaLeads.ts` /
`conftest.py` are **older** than live; `settings.py` and `check_meta_oauth_env.py`
are identical. Keep this branch as archive only.
