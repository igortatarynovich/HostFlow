# DR1 Runtime Gate — trusted-base reproduction (2026-08-31)

**Status:** measured, **FAIL** on current trusted base — not a gate decision, not a fix
**Parents:** [DR1-runtime brief](../tasks/engine-document-request-dr1-runtime.md) · `backend-ci.yml` job `DR1 Runtime Gate`
**Trusted base at measurement:** `9762e173`

> Forensic pass only. Does not reopen DR1-runtime. Does not belong to Launch-ops / OL-2.

---

## What was asked

`backend-ci` has been red on `integration/release-product-a-b` since 2026-08-28. The failing job on run [#326](https://github.com/igortatarynovich/HostFlow/actions/runs/33169406846) is **DR1 Runtime Gate**. GitHub no longer returns that run's step logs (`gh run view --log-failed` is empty), so the cause cannot be read from CI. This note records a local reproduction of the **same command path** the workflow uses.

---

## Command path

CI (`backend-ci.yml` → job `dr1-runtime-gate` → `.github/actions/backend-pytest`):

```text
working-directory: backend
HOSTFLOW_ALLOW_NON_TEST_DB=1
HOSTFLOW_SKIP_ALEMBIC_UPGRADE=1
HOSTFLOW_SQLALCHEMY_NULL_POOL=1
pytest -q tests/requirement_rules/test_dr1_runtime_gate.py
```

The test module states **no Postgres required**. Local run used a dummy `DATABASE_URL` on a closed port so the production database was never contacted.

---

## Result (current trusted base)

| Item | Value |
|---|---|
| Commit | `9762e173` |
| Command | same as CI, against `backend/tests/requirement_rules/test_dr1_runtime_gate.py` |
| Outcome | **1 failed, 9 passed** in 0.34s |
| Failing test | `test_dr1_runtime_classifies_requested_and_problem_states` |

The test feeds Hub evidence as `code95` / `tacho_card` (legacy aliases mapped in [`document-type-legacy-aliases-v1.json`](../platform/document-type-legacy-aliases-v1.json) to `driver_qualification_card` / `tachograph_card`) and asserts those canonical types are **absent** from outstanding asks. Observed `outstanding_asks` instead:

```text
driver_qualification_card = missing
tachograph_card           = missing
passport                  = requested   (matches)
driver_license            = problem     (matches)
```

So the two alias-backed types are still required as `missing`, which is exactly the assertion that fails. The request/problem classification for passport and licence still holds.

This is a **current** failure on the trusted base, not a reconstruction of 2026-08-28. It is sufficient to explain why the named job is red today; it is **not** proof that the 2026-08-28 failure was the same assertion, because those logs are gone.

---

## What this is not

- Not a fix and not a slice. Alias resolution vs. evidence matching is the DR1-runtime owner's problem.
- Not a migration or deploy issue. The test never touched a database.
- Not an OL-2 item. Launch-ops does not own this gate.

---

## History

- 2026-08-31: Local reproduction recorded. Same pytest target as CI; 1/10 fail; failing assertion names the two alias-backed document types as still `missing`.
