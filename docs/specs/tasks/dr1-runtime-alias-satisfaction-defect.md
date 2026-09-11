# Defect — DR1 runtime alias satisfaction

**Status:** **OPEN** — measured 2026-08-31, not scheduled, not Launch-ops
**Phase class:** defect (named-gate regression)
**Owners:** Documents / Engine (DR1-runtime) — **not** Operate & Launch
**Parents:** [DR1-runtime brief](engine-document-request-dr1-runtime.md) (slice remains PASS [#313](https://github.com/igortatarynovich/HostFlow/pull/313); this is a later failure of its gate) · [trusted-base reproduction](../gates/dr1-runtime-trusted-base-repro.md)

> A reproducible current failure of the **DR1 Runtime Gate** on the trusted base.
> Not a historical guess: GitHub logs for run #326 are gone; the same pytest target fails today 1/10.
> **Not** an OL-2 item. Do not fold this into a deploy/runbook PR.

---

## What is broken

`test_dr1_runtime_classifies_requested_and_problem_states` supplies Hub evidence as legacy aliases `code95` and `tacho_card` (mapped in [`document-type-legacy-aliases-v1.json`](../platform/document-type-legacy-aliases-v1.json) to `driver_qualification_card` / `tachograph_card`) and asserts those canonical types are **absent** from outstanding asks.

Observed on `9762e173`:

| doc_type | expected | observed |
|---|---|---|
| passport | requested | requested |
| driver_license | problem | problem |
| driver_qualification_card | absent (satisfied via `code95`) | **missing** |
| tachograph_card | absent (satisfied via `tacho_card`) | **missing** |

Command path = CI (`backend-ci.yml` job `dr1-runtime-gate` → `pytest tests/requirement_rules/test_dr1_runtime_gate.py`). No Postgres required; local run used a dummy DSN on a closed port.

## What closing this looks like

The same test is green on the trusted base, and the reason is that alias-backed evidence satisfies the canonical required type — not that the assertion was weakened.

## Out of scope

OL-2 / deploy / migrations / RR6. Reopening DR1-runtime as a platform slice. Changing the alias map without an Engine/Documents owner.

---

## History

- 2026-08-31: Opened from the local reproduction recorded in [dr1-runtime-trusted-base-repro.md](../gates/dr1-runtime-trusted-base-repro.md).
