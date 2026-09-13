# Employment Spine Orchestrator v1

**Status:** **Machine ESO-1…5 PASS** — contracts + orchestrators + named CI on tip; **HR UI:** ESO-1 PASS @ `b6735b9b` / `04f31a74`; **ESO-2+3 Decision Surface PASS** @ `fb61a7b1`; **ESO-4 Formalize HR Binding PASS** @ `68762f13`; **ESO-5 Started HR Binding PASS** @ `0a30595c`. Inventory: [`../../analysis/hr-employment-eso-inventory.md`](../../analysis/hr-employment-eso-inventory.md).  
**Phase class:** product  
**Module owner:** **Employment / HR** (independent of Recruitment)  
**Parents:** [Recruitment Spine Orchestrator v1](recruitment-spine-orchestrator-v1.md) · [Recruitment Architecture CLOSED](../gates/recruitment-architecture-closed.md) · [Ready for employment contract](../architecture/ready-for-employment-contract.md) · [Employment accept policy](../architecture/employment-accept-policy.md) · [Early employability](../architecture/early-employability.md) · [Employment missing resolution](../architecture/employment-missing-resolution.md) · [Employment formalize](../architecture/employment-formalize.md) · [Employment started](../architecture/employment-started.md) · [Recruitment → HR minimal handoff](recruitment-hr-minimal-handoff.md) · [Hiring workflow E2E](hiring-workflow-e2e.md) · [ADR-017](../../adr/ADR-017-work-eligibility-gates-zus.md) · Strategy Lock  
**Machine:** accept / employability / missing-resolution / formalize / started · gates ESO-1…ESO-5 · CI `eso1`…`eso5-started-gate` — **runtime machine complete** (ESO-5 Started Gate sealed; see [employment-started.md](../architecture/employment-started.md)).  
**Estimate:** TBD for Formalize/Started HR UI  

> Recruitment ends when the **Ready for employment contract** (handoff package) is emitted from the **Candidate**. This program **starts** there.  
> **Recruitment Architecture = CLOSED** ([`../gates/recruitment-architecture-closed.md`](../gates/recruitment-architecture-closed.md) @ `61cbc3eb`). Formalize → Started is **HR/Employment scope**, not Recruitment debt.  
> Not a Recruitment feature. Not “Recruitment create+accept Employee”.  
> **Host ([`ADR-042`](../architecture/ADR-042-operator-host-boundary.md)):** after **Передать**, the operator continues in **HR**. Formalize / confirm start / Started are not Application Workspace chrome.  
> **ESO-5 Started HR Binding PASS** @ `0a30595c` closes the Started operator surface on `/app/hr/handoffs/:id`. It does **not** declare Full Spine PASS or Employment program complete.  
> Seamless handoff = prepared Employment case with known context. Not “same screen forever”.  
> **Seamless UX ≠ shared ownership.**  
> **Inventory (L3):** machine ESO-1…5 ready; ESO-1…5 HR UI PASS on `/app/hr/handoffs/:id` ([`../../analysis/hr-employment-eso-inventory.md`](../../analysis/hr-employment-eso-inventory.md)).

---

## Acceptance gates (every subsequent change)

1. **RSO does not know how to employ** — Employment receives a package; it does not inherit a Recruitment “employ” API.  
2. **ESO does not re-ask Recruitment.** Anything authoritative in the package (identity, employer/vacancy, recruitment facts, evidence) is **reused**. Additional prompts are **employment missing** only. Re-prompting package facts without a conflict reason is a product FAIL.  
3. **Operator does not service the boundary.** After **Передать на трудоустройство**, the operator opens an already-prepared **HR** case for the same person (no Create Employee / re-pick vacancy / copy facts). Accept/init are Employment-internal (auto when gates pass, else concrete blockers — never ritual Accept). Do not keep ESO actions on the Application card.

Gate 2 is the usual failure mode: citizenship asked twice, employer re-selected, documents re-uploaded. Domain boundary splits responsibility, not data for the user.

Machine gates: `backend/tests/platform/test_ready_for_employment_contract_gate.py` · `backend/tests/platform/test_employment_accept_policy_gate.py` · `backend/tests/platform/test_early_employability_gate.py` · `backend/tests/platform/test_employment_missing_resolution_gate.py` · `backend/tests/platform/test_employment_formalize_gate.py` · `backend/tests/platform/test_employment_started_gate.py`.

---

## Boundary

**Ready for employment** = inter-module **contract** (handoff package + audit: Recruitment completed → Employment started), not a candidate status alone.

| Recruitment delivers | Employment owns |
|----------------------|-----------------|
| Handoff package: who, target work/employer, recruitment facts, evidence/source, Fits reason | Accept / reject handoff (**Employment policy**) |
| **Recruitment missing** only (fit + package) | **Employment missing** (employability, legalization, contract, formalize) |
| Qualification / fits | Employability / legalization / Employee / Started |

Employment answers: *What is required to lawfully and actually employ this person in this context?*  

Facade: Employment may expose **read** preview before handoff; writes stay in Employment.  
Do not re-collect recruitment facts already in the package.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After handoff, cold start (ritual Accept, re-entry of known facts, eligibility only after Employee) — or Recruitment materializes Employee / Employment docs leak into ATS.

**Completion proof (named consumer):**  
From **Передать на трудоустройство** on the Candidate, Employment receives a valid package. Operator continues in **HR**: **employment missing** + employability → one next_action → **Оформить** under Employment policy (auto-materialize only if gates pass; else concrete blockers) → **Подтвердить выход** → Started. Audit shows Employment started after Recruitment completed.

**False close (reject):** Recruitment calling `accept_handoff` as its completion; Ready for employment as status-only; Employment re-asking recruitment qualification; ritual Accept when gates already pass; Formalize / Started required on the Meta Application card ([#359](https://github.com/igortatarynovich/HostFlow/pull/359) one-card PASS).

---

## Employment orchestrator pipeline (sketch)

1. **accept_handoff** (Employment policy: auto when gates satisfied vs review).  
2. **evaluate_employability** — employable / blocked / insufficient_facts (LLM-OFF; unique pathway).  
3. **resolve employment missing** — minimal active path → patch → auto re-eval → ready_to_formalize.  
4. **formalize** — required formal actions for context → `ready_to_create_employee` (Employee mint only after threshold). Hosted in **HR** after Transfer, not on the Application.  
5. **confirm_start** → Started (physical start).  

ADR-017 post-hire ZUS journeys remain satellites — they do not replace step 2–3.

---

## Ladder

| Slice | Gate | Depends |
|-------|------|---------|
| **ESO-1** | **Employment Accept Policy Gate** — `employment_accept_policy.v1` + auto-accept via `accept_handoff` when gates pass (no ritual Accept; gate 2 reuse) | RSO-1 package |
| **ESO-2** | **Early Employability Gate** — `early_employability.v1` (employable / blocked / insufficient_facts; unique pathway; no Employee) | ESO-1 |
| **ESO-3** | **Employment Missing / Resolution Gate** — `employment_missing_resolution.v1` (minimal active path → patch → auto re-eval → ready_to_formalize; no checklist dump; no Employee) | ESO-2 |
| **ESO-4** | **Employment Formalize Gate** — `employment_formalize.v1` (context formal actions → complete/missing/blocked; `ready_to_create_employee`; no Employee mint / no HR card) | ESO-3 |
| **ESO-5** | **Employment Started Gate** — `employment_started.v1` (explicit start date + context; Employee created ≠ Started; idempotent `employee_physical_start`; spine Employee → Started) | ESO-4 |

---

## Non-goals

- Rebuilding Recruitment qualification.  
- Mapping Authority.  
- Full Legalization Engine v1 breadth (thin employability first is OK).

---

## Next

1. **ESO-2 + ESO-3 Employment Decision Surface** — **PASS** @ `fb61a7b1` (one surface on `/app/hr/handoffs/:id`; three-branch + zero-choice proofs).  
2. **ESO-1 HR host binding** — **PASS** @ `b6735b9b` / merge `04f31a74`.  
3. **ESO-4 Formalize HR Binding** — **PASS** @ `68762f13` (named UI gate 16/16 + `eso4-formalize-gate` 10/10 + diff review; [#371](https://github.com/igortatarynovich/HostFlow/pull/371)).  
4. **ESO-5 Started HR Binding** — **PASS** @ `0a30595c` (entry = `ready_to_create_employee=true`; human `confirm_physical_start`; terminal on HR handoff host; machine unchanged). **Not** Full Spine PASS.  
5. **Employment Formalization Coverage Audit** — next after this stamp.  
6. New Full Spine Gate (three-host) — later; do **not** open from ESO-5 alone; do **not** retune the withdrawn one-card Full Spine Gate.  
7. RSO-2 Transfer remains Recruitment-owned (Candidate, after Ready for employment) and must **not** call Employment accept / employability / resolution / formalize / started. After Transfer the operator continues in HR ([`ADR-042`](../architecture/ADR-042-operator-host-boundary.md)). Do not pursue [#359](https://github.com/igortatarynovich/HostFlow/pull/359) one-card PASS.  
8. **Canonical Facts Completeness** — [`canonical-facts-completeness.md`](canonical-facts-completeness.md): Employment consumers (ESO-1…2 identity/citizenship) stay on one Person/package projection read path; no Employment-local copy of Recruitment facts.
