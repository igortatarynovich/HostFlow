# ADR-042: Operator host boundary (Application → Candidate → HR)

**Status:** Accepted (L2 hosting contract). Runtime cutover **not this slice**.  
**Date:** 2026-09-10  
**Trusted base:** `feat/eso4-formalize` @ `f3eaab2b`  
**Does not supersede:** [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md) · [`ADR-037`](ADR-037-lifecycle-identity-canon.md) · RSO-1 package · ESO-1…5 policies  
**Related:** [`../tasks/recruitment-spine-orchestrator-v1.md`](../tasks/recruitment-spine-orchestrator-v1.md) · [`../tasks/employment-spine-orchestrator-v1.md`](../tasks/employment-spine-orchestrator-v1.md) · [`../gates/intake-readiness-gate.md`](../gates/intake-readiness-gate.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (Recruitment vs Employment ownership), **INV-01** (one SoT per concern), **INV-16** (one-card convenience does not outrank ownership / contracts). Hosting is L2. Does not merge ESO into `integration`. Does not promote [#359](https://github.com/igortatarynovich/HostFlow/pull/359).

**(1)** Hosts: Recruitment owns Application and Candidate workspaces; Employment / HR owns the Employment workspace after handoff. **(2)** No new Catalog capability. **(3)** Delivery stays existing Application / Candidate / HR surfaces. **(4)** Does not push Employment behavior into the System Layer. **(5)** No new settings. **(6)** SoT: person identity stays Candidate/Person; Employment case after Transfer is HR-owned. **(7)** No new security events. **(8)** Requires existing RSO package + ESO-1…5. **(9)** No new licence. **(10)** Public contract additive for hosting; one-card Application journey is **withdrawn**, not a second product.

---

## Context

[#359](https://github.com/igortatarynovich/HostFlow/pull/359) / Full Spine Gate treated **process continuity** as **one UI card forever**:

Отклик → Подходит → Передать → Оформить → Подтвердить выход → Вышел.

That collapsed three operator hosts into the Meta application. Fits was treated as the end of Recruitment. Employment actions (`Оформить`, `Подтвердить выход`, Started) were hosted on Application Workspace so the operator would not change screens.

That is the wrong product contract.

**Seamless handoff** means HostFlow creates or finds the next case with known context. It does **not** mean Employment workflow stays inside a Meta-отклик so the user never leaves. Changing workspace when owner and process change is normal. Forcing Create Employee → pick Candidate → pick vacancy → copy facts is not.

Strategy Lock: complexity belongs to the system. Business process does not. Zero-choice applies **inside** each host, not by deleting Recruitment, HR, or real human decisions.

---

## Decision

### 1. Three hosts (hard)

| Host | Object | Operator question | Next |
|------|--------|-------------------|------|
| **Отклики** | Application | Take this inbound? Vacancy, Person, recruitment facts, Fits | Не подходит → close. **Подходит → Candidate** |
| **Кандидаты** | Candidate | Recruitment process for this vacancy/company (Zero-choice inside the process) | **Ready for employment** → **Передать на трудоустройство** |
| **HR** | Employment case / Employee | Employability, employment missing, Formalize, Employee, Started | **Вышел** |

Canonical spine (product boundary, not a UX variation):

```text
Отклик → Fits → Кандидат → Recruitment → Ready for employment
      → Transfer → HR / Employment → ESO-1…5 → Started
```

**Negative locks (hard):**

1. **Fits ≠ Ready for employment.** Fits only enters Candidates. Recruitment is not finished.  
2. **Fits ≠ Transfer.** **Передать на трудоустройство** is allowed only after Ready for employment on the Candidate.  
3. **Seamless handoff ≠ same UI host.** Seamless = HostFlow creates or finds the next case with known context. It does not keep Employment on the Application card.

**Передать на трудоустройство** lives on the Candidate after Recruitment is actually done (`ready_for_employment.v1` package). That is the Recruitment → Employment boundary.

After Transfer the person **appears in HR**. Accept / employability / missing / Formalize / Employee / Started are HR-owned. They must not be required controls on the Application card.

### 2. What stays (RSO / ESO)

Keep:

- `ready_for_employment.v1` as the inter-module contract.  
- ESO-1…5: Accept → Employability → Missing resolution → Formalize → Employee → Started.  
- Gate 2: do not re-ask package facts.  
- Gate 3: operator does not assemble the boundary by hand.  
- Employee created ≠ Started.

Withdraw:

- Full Spine Gate PASS as one Application card.  
- Application `next_action` driving Formalize / Started.  
- Hosting `workspace.module.hr.employment` on `recruitment_application` as the Employment happy path.

### 3. Zero-choice (corrected)

Zero-choice = one current blocker or one next action **inside the current host**. It does not delete the host.

Forbidden on the happy path remains: stage/status/pathway dropdown as the next click; ritual Create candidate; re-picking known vacancy/employer; re-upload of package evidence.

Allowed and required: leaving Отклики for Кандидаты after Fits; leaving Кандидаты for HR after Transfer, into an **already prepared** Employment case.

---

## Consequences

- [#359](https://github.com/igortatarynovich/HostFlow/pull/359) must **not** be taken to Full Spine PASS in its current formulation.  
- Intake Readiness stays: Meta inbound → actionable Application whose next action is Fits — not Transfer, not Formalize.  
- RSO-2 must be re-hosted: Fits prep may still assemble facts; **Transfer is not the immediate next verb after Fits** unless Recruitment on that Candidate is already complete.  
- Employment UI after handoff is an HR surface (inbox / employment case), not Application Workspace.  
- Runtime cutover of hosting is a later feat PR; this ADR seals the contract.

---

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| Keep one Application card; hide HR nav | Proved on 2026-09-10: operator cannot tell where Recruitment ended or why Employment lives on a Meta lead. |
| Merge Recruitment + HR ownership | Violates P-02 / ADR-002. Seamless ≠ shared ownership. |
| Treat this as L0 RFC | Hosting is L2. Ownership of Employment after handoff already exists. |

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
Operator journey that treats a Meta Application as the Employment workspace and Fits as the end of Recruitment.

**Completion proof (named consumer):**  
This ADR + RSO/ESO brief errata. Named consumer of the **runtime** cutover is a later feat: Application Fits → Candidate Recruitment → Transfer → HR Formalize → Started, without Employment verbs on the Application card.

**False close (reject):** green #359 operator walk on one Application URL; claiming Full Spine PASS; deleting ESO-1…5.

---

## Cross-references

- Update [`recruitment-spine-orchestrator-v1.md`](../tasks/recruitment-spine-orchestrator-v1.md) — Fits = Application → Candidate; Transfer after Ready for employment.  
- Update [`employment-spine-orchestrator-v1.md`](../tasks/employment-spine-orchestrator-v1.md) — Employment host = HR after Transfer.  
- Link from [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) and [`hostflow-core-domain-map-v1.md`](hostflow-core-domain-map-v1.md).  
- Full Spine Gate one-card PASS: **STOP** (wrong contract). Machine ESO walk may remain; operator PASS of Application-hosted Employment is forbidden.
