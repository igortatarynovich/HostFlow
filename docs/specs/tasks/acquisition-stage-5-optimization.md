# Acquisition Stage 5 — Optimization

**Status:** **PR-1 DONE** ✅ · **PR-2 IN PROGRESS** (`feat/acquisition-stage-5-pr2-signal-explainability`)  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §14 · §14.1  
**Depends on:** Stage **4 runtime** DONE · Stage **4 product/UI cutover** **PASS** · Source Diagnostics PR1–PR4 DONE  
**Parents:** [Stage 4 — Flight Runtime](acquisition-stage-4-flight-runtime.md) · Stage 3E Timeline  
**PR-1 merge:** [#153](https://github.com/igortatarynovich/HostFlow/pull/153) → `1bf3e7f4` on `integration/release-product-a-b` (2026-07-23)  
**Deferred (not Stage 5):** [acquisition-stage-3e-deferred.md](acquisition-stage-3e-deferred.md) (D1–D5 remain Instrumentation)  
**Product Track now:** **Stage 5 PR-2** (explainability + operator acknowledge/dismiss)  
**Next horizon:** Stage 6 Analytics (do not open while 5 incomplete)

> **Improve** rung of the maturity ladder — assisted / automatic optimization **on top of** Stage 4 controls + 3E Timeline.  
> Does **not** redefine Runtime commands or Timeline append contract.

---

## Acquisition maturity ladder

| Stage | Layer | Verb | Status |
|-------|--------|------|--------|
| **3E** | Observability | See | **DONE** (#130–#133) |
| **4** | Operations | Control | **Runtime DONE** · UI cutover [PASS](acquisition-ui-cutover.md) |
| **5** | Optimization | Improve | **PR-1 DONE** · **PR-2 UNBLOCKED** |
| **6** | Analytics | Decide | Future horizon |

---

## PR sequence

| PR | Scope | Status |
|----|--------|--------|
| **PR-1** | Optimization signals + `suggest_pause` (read-only) | **DONE** (#153 / `1bf3e7f4`) |
| **PR-2** | Signal explainability + operator dismiss/acknowledge (no Flight mutation) | **IN PROGRESS** — `feat/acquisition-stage-5-pr2-signal-explainability` |
| **PR-3+** | Auto-apply / auto-pause only with explicit operator/safety contract | Not opened |

**Do not start PR-2 implementation while Подборы / Sales-nested Marketing / Settings-only Form Builder remain the operator path.**  
**Hard ban until a later PR is explicitly accepted:** auto-pause, workers, schedulers, or any write that changes Campaign/Flight from an optimization signal.

---

## PR-1 — Optimization signals / pause recommendation — **DONE**

Merged [#153](https://github.com/igortatarynovich/HostFlow/pull/153) as `1bf3e7f4` (2026-07-23).  
**Architectural ban (still in force):** the signal may **explain and recommend only**. It must never mutate Campaign or Flight. No Activity append on GET.

### Delivered

1. **Signals contract** — typed Flight optimization signals composed from Stage 4 `get_flight_runtime_snapshot` (identity / status / KPI strip) + **windowed** Timeline counts (allowlist subset of Live Intake Monitor). No second metrics ledger.
2. **HTTP read** — `GET /api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/optimization?window_hours=`
3. **Tests** — `backend/tests/api/test_stage_5_pr1_optimization_signals.py`
4. **Thin UI** — Marketing detail banner when `recommended_action === suggest_pause` (`data-testid="marketing-optimization-suggest-pause"`); Pause remains Stage 4 control.
5. **Threat model** — [`docs/security/threat-models/acquisition-optimization-signals.md`](../../security/threat-models/acquisition-optimization-signals.md)

### Locked thresholds (PR-1 — frozen)

| Constant | Value | Rule |
|----------|-------|------|
| `MIN_DECISION_VOLUME` | **5** | Below → `insufficient_data` |
| `MIN_ROUTING_SAMPLE` | **5** | `routing_completed + routing_failed` |
| `ROUTING_FAIL_RATE_THRESHOLD` | **0.50** | Inclusive (`>=`) when sample ≥ min |
| `DELIVERY_ERROR_THRESHOLD` | **3** | Inclusive absolute `DeliveryErrorOccurred` count in window |

**Boundary rule (integer counts):** the product rule is **`routing_fail_rate >= 0.50`** with `routing_sample >= MIN_ROUTING_SAMPLE`. At `sample=5`, exact `0.50` is unreachable (needs 2.5 fails). Tests and smoke must prove the exact threshold on an **even** sample (e.g. **3/6 = 0.50** → `suggest_pause`), and may separately check `sample=5` with the nearest achievable rates (e.g. 2/5 = 0.40 → healthy, 3/5 = 0.60 → suggest_pause).

### Deploy / smoke (2026-07-23, tip `1bf3e7f4`)

Deploy: `integration/release-product-a-b` @ `1bf3e7f4`; rebuilt `backend` + `arq-worker`; `alembic upgrade heads` → `202607220002_acq_3e_imm` (head); frontend `npm ci` / build + `rebuild-frontend.sh`.

| Check | Result |
|-------|--------|
| Active Flight, zero window volume → `insufficient_data` | **PASS** |
| Sufficient volume, fail rate below threshold → `healthy` | **PASS** (4 completed / 2 failed) |
| Routing fail rate **exactly 0.50** (sample ≥ 5) → `suggest_pause` | **PASS** (3/6; sample 5 cannot be exact 0.50) |
| Delivery errors **exactly 3** → `suggest_pause` | **PASS** (3 errors + 2 submissions) |
| Paused / completed Flight → `insufficient_data` / `flight_not_active`, no mutation | **PASS** |
| Repeat GET → Activity count unchanged | **PASS** (10→10) |
| Cross-company optimization → 404 | **PASS** |
| Marketing UI banner present in dist only for suggest_pause path | **PASS** (`marketing-optimization-suggest-pause` in published assets) |
| `/health` → 200 | **PASS** |

**CI posture (same as Stage 4):** Stage 5 tests green; security/docs/qa-static green; full `backend-ci` red = accepted Engineering baseline debt ([stabilize-integration-pytest-baseline.md](stabilize-integration-pytest-baseline.md)). Merge used `--admin` on that basis.

---

## PR-2 — Signal explainability / operator acknowledge (**locked**)

Next Product PR. **Still read-only w.r.t. Campaign/Flight status.** No auto-pause.  
Branch (planned): `feat/acquisition-stage-5-pr2-signal-explainability`

### Hard boundaries

| Must | Must not |
|------|----------|
| Expose **reason codes** | Auto-pause / auto-resume |
| Expose **observed values** used in the decision | Change Flight or Campaign **status** |
| Echo **applied thresholds** (PR-1 frozen constants) | Let dismiss/acknowledge alter `assessment` / `recommended_action` |
| Provide a clear **why** for the recommendation | Workers / schedulers / Flight write commands |
| **Acknowledge / dismiss** as separate **operator state** | Treat dismiss as Pause |
| **Audit trail** of operator acknowledge/dismiss actions | Emit recommendation Activity on every GET (PR-1 ban remains) |

### IN

1. **Explainability contract** — structured payload: reason codes, observed values (e.g. routing failed/completed, fail rate, delivery error count, `decision_volume`, window bounds), applied thresholds, and a human-readable explanation of why the recommendation fired (or why data is insufficient / healthy).
2. **Operator dismiss / acknowledge** — separate operator state bound to recommendation identity (Flight + window / signal fingerprint as designed). Absence or presence of acknowledge/dismiss **must not** change the pure optimization assessment calculation (`evaluate_flight_optimization` remains side-effect free).
3. **Audit trail** — record operator acknowledge/dismiss actions (who / when / what was acknowledged) without mutating runtime status. Prefer an append-only operator action record; do **not** overload Timeline with per-GET recommendation noise.
4. **HTTP / UI** — extend optimization read (+ write only for acknowledge/dismiss operator state); Marketing detail shows explanation and acknowledge/dismiss controls. Pause remains Stage 4 command.
5. **Tests** — explainability fields; dismiss does not mutate Flight/Campaign status or assessment; audit row on dismiss; company/tenant scope; threshold boundary on even sample (3/6).

### OUT

- Auto-pause / auto-resume / workers / schedulers  
- Treating dismiss as Pause or any Flight/Campaign lifecycle transition  
- Changing PR-1 threshold constants without an explicit threshold-change decision  
- Stage 6 analytics  
- Coupling assessment output to UI dismiss state  

---

## Out of scope (Stage 5 epic initial)

- Stage 6 strategic dashboards as substitute for Timeline  
- Provider Ads Manager replacement  
- Reopening Stage 4 command matrix  

---

## History

- 2026-07-23: Opened after Stage 4 DONE merge (#148–#151); **PR-1 locked** as read-only optimization signals.
- 2026-07-23: Locked PR-1 inputs/thresholds/assessments; no Activity on GET; compose runtime + windowed Timeline only.
- 2026-07-23: **PR-1 DONE** — merged #153 as `1bf3e7f4`; deploy + smoke PASS; **PR-2 locked** as explainability + dismiss/acknowledge (no Flight mutation; no auto-pause).
- 2026-07-23: PR-2 boundaries refined — reason codes, observed values, applied thresholds, operator acknowledge/dismiss + audit trail; assessment independent of dismiss; integer-sample note (`>= 0.50`, exact boundary on even sample e.g. 3/6).
- 2026-07-23: **PR-2 PAUSED** — Product Track switches to [Acquisition UI Cutover](acquisition-ui-cutover.md); Stage 4 runtime DONE but product/UI cutover NOT DONE.
- 2026-07-27: **PR-2 UNBLOCKED** — [C-7 PASS](acquisition-ui-cutover-c7-searches-decommission.md); Product Track → Ad-ID bind UI; Stage 5 PR-2 may resume.
- 2026-07-29: Source Diagnostics PR1–PR4 closed (#196–#201); **Product Track → Stage 5 PR-2** explainability + operator acknowledge/dismiss.
