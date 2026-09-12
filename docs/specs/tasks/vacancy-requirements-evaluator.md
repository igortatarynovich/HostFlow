# Vacancy Requirements Evaluator

**Status:** **Accepted** (L2 runtime slice). **Vacancy Requirements Evaluator Gate = PASS** on immutable revision `6d2586a5` ([#367](https://github.com/igortatarynovich/HostFlow/pull/367)). Overlay vacancy write UI is a separate slice — **PASS** `18bef9f0` / [#368](https://github.com/igortatarynovich/HostFlow/pull/368).  
**Phase class:** product  
**Module owner:** **Recruitment**  
**Date:** 2026-09-11  
**Trusted base:** `feat/canonical-facts-occupancy-cutover` (Canonical Facts Occupancy Gate **PASS** `bd0bf284` / [#366](https://github.com/igortatarynovich/HostFlow/pull/366))  
**Parents:** [Vacancy Recruitment Requirements SoT](vacancy-recruitment-requirements-sot.md) · [Canonical Facts Completeness](canonical-facts-completeness.md) · [Vacancy Overlay](entity-profile-vacancy-overlay-contract.md) · [ADR-042](../architecture/ADR-042-operator-host-boundary.md) · [RSO v1](recruitment-spine-orchestrator-v1.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02**, **INV-01**, **INV-16**. Does not write Overlay at vacancy create (later). Does not grow `lead_criteria_v1`. Does not wait on HR UI. Does not claim Full Spine PASS.

> System answers **fit / missing / not_fit** from Vacancy Requirements SoT × canonical facts. Operator gets **one** next action. Evaluator does not create Candidate, Ready, or Transfer.

---

## Operator question (one)

Given this vacancy’s requirements and this person’s **canonical** facts, is the person **fit**, **missing**, or **not_fit** — with an explanation per requirement — and what is the **one** next action?

---

## Original Goal → Completion Proof

**Problem:** Application still offers ritual «Создать кандидата» without a system requirements verdict grounded in Overlay + canonical occupancy.

**Completion proof:** Named **Vacancy Requirements Evaluator Gate** green on four classes (all met / required missing / hard mismatch / source-independent). Application detail shows verdict + one next action; **Подходит** only when fit; no Candidate/Ready/Transfer side effects inside the evaluator.

**False close:** three outcome buttons; renaming Create; reading `field_answers` / `lead.normalized` / `lead_criteria_v1` as authority; auto-Transfer; vacancy Overlay write UI in this PR; changing Candidate Recruitment after Подходит.

---

## Named Acceptance Gate — Vacancy Requirements Evaluator

**Status:** **PASS** on `6d2586a5` ([#367](https://github.com/igortatarynovich/HostFlow/pull/367))  
**Machine:** `backend/tests/platform/test_vacancy_requirements_eval_gate.py`  
**CI:** named job `Vacancy Requirements Evaluator Gate` (`.github/workflows/backend-ci.yml`)

### Acceptance (all must hold)

1. Evaluator reads requirements only via Overlay `resolve_overlay` → `merge` (Vacancy Requirements SoT).  
2. Facts only via `backend.app.field_registry.canonical_facts` (occupancy PASS).  
3. No fallback to `lead_criteria_v1`, `field_answers`, or `lead.normalized` as decision authority.  
4. `normalized.documents[]` is not evidence SoT — Hub/evidence type set only.  
5. Result is explainable per requirement (`explanation[]` with human `requirement` + canonical `qualified_code` / `document_type_code`).  
6. **fit** → one next action **Подходит** (`fits` → existing process).  
7. **missing** → one next action collect the named missing fact (`fact_code` = canonical key; `requirement` = human label — not source field / overlay predicate id).  
8. **not_fit** → one next action **Не подходит** / close (`reject`).  
9. Evaluator does not create Candidate, set Ready, or Transfer.  
10. Application only displays verdict + next action; Candidate Recruitment after Подходит unchanged.

### Four machine classes

| Class | Assert |
|-------|--------|
| all requirements met | `status=fit`, `next_action.code=fits` |
| required fact missing | `status=missing`, explanation names fact/doc |
| hard mismatch | `status=not_fit` (e.g. years_ce present but below min) |
| source-independent | same canonical occupancy via different intake reps → same status |

**PASS evidence (`6d2586a5`):**
- Named CI **Vacancy Requirements Evaluator Gate** green
- Diff recheck: no source-local decision authority; no `lead_criteria` SoT; fit ≠ Ready/Transfer; missing = canonical `fact_code` + human `requirement`; not_fit explains hard mismatch; Application UI displays verdict + one action; no Candidate Recruitment module edits
- Baseline Bandit / scorecard / SPA guards unchanged (not introduced by this diff)

---

## Non-goals

- Vacancy Overlay create/edit UI  
- Leftover `lead_criteria_v1` retirement runtime  
- HR host / Full Spine  
- Changing Candidate Recruitment chrome after Подходит

## Next

- **Overlay vacancy write UI** — **PASS** `18bef9f0` / [#368](https://github.com/igortatarynovich/HostFlow/pull/368) — [`vacancy-overlay-write-ui.md`](vacancy-overlay-write-ui.md).
