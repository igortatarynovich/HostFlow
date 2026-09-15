# Employment start_allowed — ESO-5 Confirm enforcement (slice 4)

**Status:** **PASS**  
**Phase class:** product  
**Opened:** 2026-09-15  
**PASS stamp:** 2026-09-15 · implementation under test `b8c9dd04` · machine gates `employment-start-allowed-eso5-enforcement-gate` **10 passed** + `employment-started-gate` **14 passed** (+ mint-cutover regression; combined **40 passed**) · Confirm blocked when `start_allowed != true` · `start_allowed=true` ≠ Started · human Confirm remains · mint-on-confirm retired · Full Spine **CLOSED** · **STOP** before Full Spine  
**Depends on:**  
- Slice 3 PASS: [`employment-start-allowed-hr-host-binding.md`](employment-start-allowed-hr-host-binding.md)  
- Boundary E2E PASS: [`recruitment-employment-handoff-boundary-e2e-proof.md`](recruitment-employment-handoff-boundary-e2e-proof.md) · handoff `e9ef16f2-1ab6-49d0-91dd-aa7676995081`  
- Architecture: [`../architecture/employment-start-allowed.md`](../architecture/employment-start-allowed.md) (**Accepted** — ESO-5 requires `start_allowed`)  
- Adaptation design: [`../../analysis/employment-start-allowed-adaptation-design.md`](../../analysis/employment-start-allowed-adaptation-design.md) (**Accepted** · slice 4)  
- ESO-5 contract: [`../architecture/employment-started.md`](../architecture/employment-started.md) (`employment_started.v1` on integration)  
**Named gate (this slice):** `employment-start-allowed-eso5-enforcement-gate`  
**Does not open:** Full Spine Gate · Hiring E2E program · new admit-to-work host · operator-set `start_allowed`

> **Slice 4 of 4 (PEM-1 start_allowed program) — PASS.**  
> **Decision (locked):** ESO-5 Confirm physical start is **forbidden** unless `start_allowed=true`.  
> Retire PEM-1 **mint-on-confirm** — Employee must already exist (ESA2 Formalize→ensure).  
> **Not** Full Spine. **Not** auto-Started from admit-to-work.

---

## Original Goal → Completion Proof

**Problem this slice must permanently remove:**  
Operator can Confirm physical start (`Подтвердить выход` / `employment_started.v1`) while admit-to-work is still false, or mint Employee as a side effect of Confirm — collapsing admit-to-work into Started.

**Completion proof (named consumer):**

```text
Employee exists (handoff-linked; Formalize→ensure)
  → employment_start_allowed.v1 → start_allowed=true
  → POST /handoffs/{id}/employment-started confirm
       → started / already_started
  → same confirm with start_allowed=false → blocked (start_allowed_required)
  → Confirm never calls handoff_from_candidate (no mint-on-confirm)
```

**False close (reject):** UI-only disable without API gate; `force_start` / Allow anyway; mint Employee inside Confirm; claiming Full Spine; treating ESO-1 `employment_started` audit as physical start; opening Hiring E2E.

---

## Decision (accepted)

| Question | Answer |
|----------|--------|
| May ESO-5 Confirm succeed when `start_allowed != true`? | **No** |
| Who mints Employee for PEM-1? | Formalize authoritative apply → `ensure_employee_after_formalize_apply` only |
| Does `start_allowed=true` auto-Confirm Started? | **No** — human Confirm remains |
| Full Spine? | **Closed** |

---

## Scope (in)

1. Port ESO-5 Confirm surface onto trusted integration line (`employment_started.v1` + orchestrator + `POST …/employment-started`) if absent.  
2. Gate Confirm: require fresh/handoff `start_allowed=true` before first physical start.  
3. Remove PEM-1 mint-on-confirm (`handoff_from_candidate` / `ensure_employee` mint path in Confirm).  
4. Named machine gate + CI wire.  
5. Update parent Next pointers; **STOP** before Full Spine.

## Scope (out)

| Out | Owner |
|-----|--------|
| Full Spine Gate / three-host declare | **Closed** |
| Expanding Formalize / evidence authorities | **Closed** |
| Operator-set `start_allowed` | **Forbidden** |
| Hiring workflow E2E / RS-7 | **Not this brief** |
| ZUS / Insurance lifecycle | Post-Started (later) |

---

## PASS criteria (witness)

- [x] `POST /handoffs/{id}/employment-started` with confirm + `start_allowed=false` → **blocked** (`start_allowed_required`)  
- [x] Same path with `start_allowed=true` + known date/context → **started** (first) / **already_started** (replay)  
- [x] Confirm orchestrator **does not** call `handoff_from_candidate` / mint  
- [x] Missing Employee → blocked (`employee_required`); not mint-via-Confirm  
- [x] Idempotent replay does **not** require re-proving admit when already Started  
- [x] Full Spine **not** claimed  
- [x] Named gate green (`employment-start-allowed-eso5-enforcement-gate` 10 + `employment-started-gate` 14)

---

## After PASS

1. ~~Stamp this brief.~~ **Done** (2026-09-15).  
2. **STOP.** Do not open Full Spine in the same change.  
3. Separate decision: Three-host Full Spine Gate.

---

## Implementation map

| Concern | Location |
|---------|----------|
| Contract | `backend/app/reference/employment_started.py` |
| Runtime | `backend/app/services/employment_started_orchestrator.py` |
| Admit check | `evaluate_start_allowed_for_handoff` (ESA-3) |
| HTTP | `POST /api/v1/handoffs/{id}/employment-started` |
| Gate | `backend/tests/platform/test_employment_start_allowed_eso5_enforcement_gate.py` |
| Arch | `docs/specs/architecture/employment-started.md` |
| CI | `.github/workflows/backend-ci.yml` (`esa4` / `eso5` → `employment-start-allowed-eso5-enforcement-gate`) |
