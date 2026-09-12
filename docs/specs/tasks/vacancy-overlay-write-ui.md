# Vacancy Overlay Write UI

**Status:** **Accepted** (L2 runtime slice). **Vacancy Overlay Write UI Gate = PASS** on immutable revision `18bef9f0` ([#368](https://github.com/igortatarynovich/HostFlow/pull/368)). Requirements SoT is closed from operator write through evaluator read.  
**Phase class:** product  
**Module owner:** **Recruitment**  
**Date:** 2026-09-11  
**Trusted base:** `feat/vacancy-requirements-evaluator` (Vacancy Requirements Evaluator Gate **PASS** `6d2586a5` / [#367](https://github.com/igortatarynovich/HostFlow/pull/367))  
**Parents:** [Vacancy Recruitment Requirements SoT](vacancy-recruitment-requirements-sot.md) · [Vacancy Requirements Evaluator](vacancy-requirements-evaluator.md) · [Vacancy Overlay](entity-profile-vacancy-overlay-contract.md) · [Canonical Facts Completeness](canonical-facts-completeness.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02**, **INV-01**, **INV-16**. Does not mint a second requirements store. Does not write RPM `tenant_delta`. Does not grow `lead_criteria_v1`. Does not open rates / contracts / legalization / Employment requirements.

> Operator answers: **what is required for this vacancy?**  
> System writes Entity Profile bind + Vacancy Overlay delta. Evaluator already consumes that SoT.

---

## Operator question (one)

When creating or editing a vacancy, what must be true of a person for Recruitment on **this** vacancy — beyond the base Profile / Screening Pack — without opening a matching-parameters layer?

---

## Original Goal → Completion Proof

**Problem:** Requirements live in leftover Profiling (`lead_criteria_v1` / Candidate Requirements tab) or rich text, while the evaluator expects Overlay merge.

**Completion proof:** Named **Vacancy Overlay Write UI Gate** green: vacancy create/edit → Overlay write → `resolve_overlay` / `merge` → evaluator verdict changes. No write to `lead_criteria_v1` or RPM `tenant_delta`. UI shows human **effective** requirements only (no overlay/predicate ids). Edit is **round-trip safe**: only necessary Overlay delta is persisted.

**False close:** new matching-parameters table; growing Candidate Requirements / `lead_criteria_v1`; writing RPM `tenant_delta`; description-as-SoT; rates/contracts/legalization in this UI; exposing overlay predicate ids to the operator; copying full Profile/Pack requirements into vacancy Overlay on every save.

---

## Named Acceptance Gate — Vacancy Overlay Write UI

**Status:** **PASS** on `18bef9f0` ([#368](https://github.com/igortatarynovich/HostFlow/pull/368))  
**Machine:** `backend/tests/platform/test_vacancy_overlay_write_ui_gate.py`  
**CI:** named job `Vacancy Overlay Write UI Gate` (`.github/workflows/backend-ci.yml`)

### Acceptance

1. UI / API write only `Vacancy.candidate_profile_id` + Overlay delta in `Vacancy.extra` (`entity_profile_vacancy_overlay.v1`).  
2. Base requirements come from Profile / Pack; vacancy write only tightens / adds.  
3. Operator fields are human requirements (years CE min, required documents, …) — not predicate ids.  
4. Edit is **round-trip safe**: open existing vacancy → see **effective** requirements in human language → change one requirement → persist **only necessary Overlay delta**; inherited Profile/Pack requirements are **not** copied wholesale into vacancy.  
5. `description` remains non-decision (unused by evaluator).  
6. After save, existing evaluator sees changed merge / verdict.  
7. No `lead_criteria_v1` write; no RPM `tenant_delta`.  
8. Rates, contract subtype, legalization, Employment requirements out of scope / not in this UI.

### Named proof

```text
Profile/Pack
  → Vacancy UI effective requirements
  → operator changes requirement
  → minimal Overlay delta
  → resolve_overlay / merge
  → vacancy_requirements evaluator → changed verdict
```

### Negative checks (machine)

- Unchanged inherited requirement → **not** in Overlay delta.  
- Reset to inherited value → corresponding delta **disappears**.  
- `lead_criteria_v1` is not written.  
- RPM `tenant_delta` is not written.  
- `description` is not used by the evaluator.  
- Employment / legalization requirements do not appear in this UI.

**PASS evidence (`18bef9f0`):**
- Named CI **Vacancy Overlay Write UI Gate** green on [#368](https://github.com/igortatarynovich/HostFlow/pull/368)
- Diff recheck: round-trip safe (unchanged inherited ∉ delta; reset clears delta); FE sends human intent; backend persists only minimal Overlay delta; GET projects effective + inherited; evaluator verdict changes after save; no `lead_criteria_v1` / RPM `tenant_delta`; Employment / legalization / rates out of write path
- Baseline Bandit / scorecard / SPA guards unchanged (not introduced by this diff; same as parent `e0277edf`)

---

## Non-goals

- Leftover `lead_criteria_v1` full retirement migration of historical rows  
- RPM operator UI  
- Employment / rates / permits / contract subtype  
- Changing Application evaluator chrome (already PASS)  

