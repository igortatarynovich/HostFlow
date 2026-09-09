# Employment Spine Orchestrator v1

**Status:** **BRIEF** — package SoT frozen on RSO-1 (**PASS**); ESO runtime not started. Contract: [ready-for-employment-contract.md](../architecture/ready-for-employment-contract.md).  
**Phase class:** product  
**Module owner:** **Employment / HR** (independent of Recruitment)  
**Parents:** [Recruitment Spine Orchestrator v1](recruitment-spine-orchestrator-v1.md) · [Ready for employment contract](../architecture/ready-for-employment-contract.md) (`ready_for_employment.v1`) · [Recruitment → HR minimal handoff](recruitment-hr-minimal-handoff.md) · [Hiring workflow E2E](hiring-workflow-e2e.md) · [ADR-017](../../adr/ADR-017-work-eligibility-gates-zus.md) · Strategy Lock  
**Estimate:** TBD after RSO-1 handoff package shape freezes  

> Recruitment ends when the **Ready for employment contract** (handoff package) is emitted. This program **starts** there.  
> Not a Recruitment feature. Not “Recruitment create+accept Employee”.  
> User journey stays continuous; ownership does not.  
> **Seamless UX ≠ shared ownership.**

---

## Acceptance gates (every subsequent change)

1. **RSO does not know how to employ** — Employment receives a package; it does not inherit a Recruitment “employ” API.  
2. **ESO does not re-ask Recruitment.** Anything authoritative in the package (identity, employer/vacancy, recruitment facts, evidence) is **reused**. Additional prompts are **employment missing** only. Re-prompting package facts without a conflict reason is a product FAIL.  
3. **Operator does not service the boundary.** After **Передать на трудоустройство**, work continues on the same person; Accept/init are Employment-internal (auto when gates pass, else concrete blockers — never ritual Accept).

Gate 2 is the usual failure mode: citizenship asked twice, employer re-selected, documents re-uploaded. Domain boundary splits responsibility, not data for the user.

Machine gate: `backend/tests/platform/test_ready_for_employment_contract_gate.py`.

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
From **Передать на трудоустройство**, Employment receives a valid package → **employment missing** + employability → one next_action → **Оформить** under Employment policy (auto-materialize only if gates pass; else concrete blockers) → **Подтвердить выход** → Started. Audit shows Employment started after Recruitment completed.

**False close (reject):** Recruitment calling `accept_handoff` as its completion; Ready for employment as status-only; Employment re-asking recruitment qualification; ritual Accept when gates already pass.

---

## Employment orchestrator pipeline (sketch)

1. **accept_handoff** (Employment policy: auto when gates satisfied vs review).  
2. **evaluate_employment_missing** — only employment/legalization/contract needs.  
3. **evaluate_employability** — can / cannot / options (before or at formalize; LLM-OFF for pathway).  
4. **formalize** — Employee when gates pass; else blockers.  
5. **confirm_start** → Started.  

ADR-017 post-hire ZUS journeys remain satellites — they do not replace step 3.

---

## Ladder (placeholder until RSO-1 package frozen)

| Slice | Gate (named later) | Depends |
|-------|--------------------|---------|
| **ESO-1** | Employment orchestrator contract + accept policy | RSO-1 handoff package |
| **ESO-2** | Early employability SoT (Employment-owned) | ESO-1 |
| **ESO-3** | Formalize gate (auto materialize **or** blockers) | ESO-2 |
| **ESO-4** | Started confirm | ESO-3 |

---

## Non-goals

- Rebuilding Recruitment qualification.  
- Mapping Authority.  
- Full Legalization Engine v1 breadth (thin employability first is OK).

---

## Next

RSO-1 package shape is frozen (`ready_for_employment.v1`). **ESO-1:** accept policy that **reuses** package facts (gate 2) + auto-init when Employment gates pass. Then ESO-2 employability SoT (ownership card if Rule 3 requires).
