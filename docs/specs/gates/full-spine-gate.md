# Full Spine Gate

**Status:** **Accepted** (L2 contract — Full Spine Gate freeze). Named gate **not PASS** until Operator / Zero-choice evidence is recorded.  
**Date:** 2026-09-09  
**Trusted base:** `feat/eso4-formalize` @ `18a2ee42` (ESO-1…5 stacked; not yet on `integration`)  
**Related:** [Recruitment Spine Orchestrator v1](../tasks/recruitment-spine-orchestrator-v1.md) · [Employment Spine Orchestrator v1](../tasks/employment-spine-orchestrator-v1.md) · [Ready for employment contract](../architecture/ready-for-employment-contract.md) · [Employment accept policy](../architecture/employment-accept-policy.md) · [Early employability](../architecture/early-employability.md) · [Employment missing resolution](../architecture/employment-missing-resolution.md) · [Employment formalize](../architecture/employment-formalize.md) · [Employment started](../architecture/employment-started.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02**. Does not rewrite L0. Does not open ESO-6. Does not schedule Hiring E2E (HE-*). Does not merge this stack into `integration`. Does not treat base CI noise (guards / threat-model / scorecard) as this gate.

> This file is the **SoT** for proving the assembled spine as **one operator journey**.  
> Machine copy: `full_spine.v1` in `backend/app/reference/full_spine.py`.  
> Gate tests: `backend/tests/platform/test_full_spine_gate.py`.  
> CI: `full-spine-gate` (this job only — not umbrella backend-ci noise).

---

## Operator question (one)

Can an untrained operator take **one incoming lead** to **Started** on a single continuous person, without servicing module boundaries, without re-entering known facts, and without choosing stage / status / pathway — seeing only the current blocker or one next action?

No second question is this gate. Mapping Authority, Forms Publish, Hiring E2E (HE-*), ZUS satellites, and HR-card chrome are other programs.

---

## Spine (frozen)

```text
Source → Recruitment (Fits) → Handoff package
      → Employment Accept → Employability → Missing Resolution
      → Formalize → Employee → Started
```

| Step | Owner | Machine |
|------|-------|---------|
| Source / application | Acquisition + Recruitment | inbound lead with known vacancy |
| Fits → Transfer | Recruitment (RSO-2) | `ready_for_employment.v1` emit + pending handoff |
| Accept | Employment (ESO-1) | `employment_accept_policy.v1` auto-accept when gates pass |
| Employability | Employment (ESO-2) | `early_employability.v1` |
| Missing resolution | Employment (ESO-3) | `employment_missing_resolution.v1` |
| Formalize | Employment (ESO-4) | `employment_formalize.v1` → `ready_to_create_employee` |
| Employee | Employment (ESO-5 mint, distinct fact) | allowed only after ESO-4 |
| Started | Employment (ESO-5) | `employment_started.v1` + `employee_physical_start` |

RSO-2 runtime may still sit on a parallel branch until stacked. This gate **names** it as the Recruitment surface of the same journey. It does not re-implement Transfer, and it does not let Recruitment call Employment APIs.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
The backend spine is assembled as separate named slices, but a new operator can still feel two products, re-type known vacancy/person/context, pick stage/status/pathway, or be blocked by a ritual the system already knows.

**Completion proof (named consumer):**  
One Meta (or equivalent inbound) application with known vacancy and person facts: Call → **Подходит** → **Передать на трудоустройство** → Employment continues the same person → **Оформить** (only if a current formal item remains) → **Подтвердить выход** → Started. A new operator completes it **without documentation**. Audit shows Recruitment completed, then Employment case-accept (`employment_started`), then physical start (`employee_physical_start`). Replay of Transfer / Started does not create a second handoff or second start event.

**False close (reject):** green ESO-1…5 unit gates alone; API state without UI flow; operator still uses Create candidate / vacancy bind / stage or pathway dropdown on the happy path; treating Employee create as Started; claiming PASS because CI umbrellas are red/green for unrelated jobs.

---

## Hard locks (bind every change)

1. **One real happy path** — inbound lead → Started. Not a gallery of slice demos.  
2. **No manual action the system can determine** — known vacancy, person, employer, exact duplicate, auto-accept, unique legal pathway are internal.  
3. **Known vacancy / person / context are not re-asked.** Gate 2. Re-prompt without `conflict_reason` is FAIL.  
4. **No stage / status / pathway dropdown on the happy path.** Pathway is computed (LLM-OFF). Stage rails are not the operator’s next click.  
5. **Recruitment and Employment are one journey, two owners.** Same person; no cold start; seamless UX ≠ shared ownership.  
6. **One current blocker or one next action.** Never a checklist dump.  
7. **Backend transitions, audit, and idempotency are proven with the UI flow**, not instead of it.  
8. **PASS requires a new operator without documentation**, not only DB/API assertions.

---

## Operator / Zero-choice UI audit (required for PASS)

Happy-path operator verbs only:

| When | Operator sees |
|------|----------------|
| Qualification | **Позвонить** → **Подходит** (or Перезвонить / Не подходит — not a stage menu) |
| Package ready | **Передать на трудоустройство** |
| After Transfer | Same person in Employment context. No ritual Accept when policy is `auto_accept`. |
| Formal item outstanding | The **one** current formal action (e.g. confirm contract basis) |
| Formalization complete + start facts known | **Подтвердить выход** (do not re-collect known date/context) |
| Already Started | No second confirm chore; replay is silent/idempotent |

**Forbidden on this happy path**

- Create candidate as a ritual  
- Vacancy / employer picker when already known  
- Stage, status, or legal-pathway `<select>` / dropdown as the next action  
- Re-upload of package evidence  
- Separate “open HR card” / profile enrichment as a required step  
- Recruitment UI calling accept / employability / formalize / started APIs  

---

## Machine evidence (this freeze)

`walk_full_spine_happy_path_v1` must, on a valid `ready_for_employment.v1` package with known PL EU facts and start date:

1. Validate the package (Recruitment terminal).  
2. Auto-accept (`pending_review` → policy `auto_accept`).  
3. Evaluate employable with a unique pathway (no pathway prompt).  
4. Resolution → `ready_to_formalize` without a universal checklist.  
5. Formalize confirm → `ready_to_create_employee` and **`employee_created=false`**.  
6. Started confirm → `started=true` with **one** `employee_physical_start` intent; Employee created still ≠ the start fact until confirm.  
7. Second Started confirm → `already_started`, no second event.  
8. Injecting a package-authoritative re-ask (e.g. `citizenship` without `conflict_reason`) is a FAIL.

This machine walk is **necessary** and **not sufficient** for Gate PASS.

---

## Operator Test protocol (required for Gate PASS)

Witness: a person who did not write this spine, **no** briefing doc in hand.

1. Inbound lead, vacancy known, identity on the package.  
2. Call → Подходит.  
3. Transfer.  
4. Continue without re-selecting vacancy/person.  
5. Confirm only what is still missing; then Подтвердить выход.  
6. Repeat Transfer and Started: still one handoff, one physical-start event.

**FAIL** if they need a wiki, a stage picker, or a second product to finish.

Record the witness run under this heading before promoting the gate to **PASS**. Until then the outcome is **contract freeze only**.

---

## Non-goals

- ESO-6 or any new Employment capability.  
- Merging Recruitment and Employment ownership.  
- Integrating `feat/eso4-formalize` into `integration` in this slice.  
- Repairing pre-existing backend-ci / security-gates noise.  
- HR employee card chrome.  
- Hiring workflow E2E (HE-1…HE-4).  
- Mapping Authority.

---

## Completion of this freeze

**This slice PASSes as a contract freeze** when this document + `full_spine.v1` + `test_full_spine_gate.py` + CI job `full-spine-gate` exist, RSO/ESO briefs name the Full Spine Gate, and the machine walk holds.

**Full Spine Gate PASS** (promotion) additionally requires the Operator Test witness above plus Zero-choice UI audit with no forbidden happy-path controls. That evidence is **required before integrating the ESO-1…5 stack**.
