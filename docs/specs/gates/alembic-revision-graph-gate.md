# Alembic revision-graph gate

**Status:** ACTIVE  
**Related:** `backend/scripts/check_alembic_heads.py` · `backend/scripts/check_alembic_revision_graph.py` · `scripts/deploy/alembic_preflight.py`  

---

## Problem

Partial migration checkouts break Alembic before any DDL runs:

* child revision file present (e.g. R5)
* `down_revision` points at a parent file that is absent (e.g. R4)
* `alembic upgrade head` raises `KeyError` while building the revision map

Copying individual migration files between mismatched checkouts is **emergency recovery only**, not a development workflow.

---

## Mandatory order for `/opt/HostFlow` (and any deploy host)

1. Check active branch and local changes (`git status`)
2. `git fetch`
3. Sync the **whole** target branch (`origin/integration/release-product-a-b`)
4. Confirm every migration file in the chain is present
5. Confirm exactly one Alembic head
6. Only then `alembic upgrade head`

Do not mix application code from one PR with a migration chain from another tree state.

---

## CI / architecture checks

| Check | Tool |
|-------|------|
| Exactly one head | `check_alembic_heads.py` |
| Every `down_revision` exists + no cycles + single head | `check_alembic_revision_graph.py` |
| ScriptDirectory builds (same path as upgrade) | `check_alembic_revision_graph.py --with-alembic` |
| Upgrade on clean Postgres | `backend-ci` → `alembic upgrade head` |

Pre-commit runs both heads + graph guards when `backend/alembic/versions/*.py` change.

---

## Deploy preflight

```bash
python3 scripts/deploy/alembic_preflight.py
# optional: fail on dirty tree
python3 scripts/deploy/alembic_preflight.py --require-clean-tree
```

Reports: git commit · branch · status · alembic current/heads (if DB URL set) · revision-graph result.

---

## History

- 2026-07-19: Gate added after `/opt/HostFlow` failed on missing `202607190002_sales_inquiries_r4` while R5 was present; also restored missing `202607160001` / `202607160002` on the integration chain.
