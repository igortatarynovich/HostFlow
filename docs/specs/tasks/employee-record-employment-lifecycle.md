# Employee Record & Employment Lifecycle

**Status:** **OPENED** — contract opened. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime. Feat locked.  
**Phase class:** platform  
**Date:** 2026-10-03  
**Trusted base:** Poland Work Authorization Presets program close `37439bc5` on `integration/release-product-a-b` @ `020cb4e5` ([#402](https://github.com/igortatarynovich/HostFlow/pull/402))  
**Parents:** [contract](../architecture/employee-record-employment-lifecycle-contract.md) (`employee_record_employment_lifecycle.v1`) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Hiring workflow E2E](hiring-workflow-e2e.md) · superseded [Minimal Recruitment → HR handoff](recruitment-hr-minimal-handoff.md)

> The [contract](../architecture/employee-record-employment-lifecycle-contract.md) is opened. The Contract Gate is **not PASS**. This brief does not write a schema or a runtime.  
> Candidate and Employee stay different entities. A handoff creates the HR-side identity. It does not turn the Candidate row into an Employee.  
> Legal Eligibility and Work Authorization stay upstream. This product does not become a second legalization engine.  
> HostFlow v1 is not release-ready. Release readiness stays a separate gate.

---

## Problem

A candidate can be accepted for employment, and HostFlow still has no canonical Employee and Employment on which later HR documents and processes can hang. The older [Minimal Recruitment → HR handoff](recruitment-hr-minimal-handoff.md) names a hire that creates or links an employee. That brief is superseded here so the queue does not carry two HR products.

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**
An accepted candidate has no canonical Employee and no Employment that can become Active and later Ended, so later HR documents have nowhere stable to hang.

**Completion proof (named consumer):**
One accepted candidate can be read along `Candidate → ready_for_employment → HR handoff → Employee → Employment (preparing) → Active → Ended`. The Candidate row remains a candidate. The Employee is the person in the company's HR context. The Employment is one labour relationship, and one Employee may have more than one over time. Evidence already held, including the passport, stays on the existing evidence model. Ended keeps the Employee and the evidence.

**False close (reject):** turning the Candidate row into the Employee; copying person or evidence into a second store; a Polish HR document pack written into the Employee domain; a second legalization decision inside HR; deleting the Employee or the evidence when the Employment ends.

## Order

1. This brief. The chain and the two entities are named. Employee Record & Employment Lifecycle — Contract Gate **not PASS**.
2. The [contract](../architecture/employee-record-employment-lifecycle-contract.md) is opened. Employee, Employment, the HR handoff, and `preparing → active → ended` are named. Legal eligibility, data, terms, and requirements are gates around `preparing`. Employee Record & Employment Lifecycle — Contract Gate **not PASS**.
3. Runtime. Not authorized.

## Chain

```text
Candidate
→ ready_for_employment
→ HR handoff
→ Employee
→ Employment (preparing)
→ Active
→ Ended
```

The [contract](../architecture/employee-record-employment-lifecycle-contract.md) is the source for the path around those states. Employment states are `preparing → active → ended`. The HR Legal Eligibility Gate, employee data, employment terms, pre-employment requirements, and the Ready to Start Gate sit around `preparing`. They are not further Employment states. `WorkforceEmployee.status` stays another plane. The persistence boundary names `hire_date` and `termination_date` as Employment facts. `workforce_employments` is the contract-terms satellite, not the canonical Employment. No schema is written.

| Term | What it is |
|---|---|
| Candidate | The recruitment person. The row stays a candidate after the handoff |
| `ready_for_employment` | The hiring outcome the handoff consumes. This brief does not redefine it |
| HR handoff | The act that creates or initiates the HR-side identity |
| Employee | The person in the company's HR context |
| Employment | One labour relationship of that Employee. An Employee may have more than one over time |
| `preparing` | The Employment exists and is not yet in force |
| Active | The Employment is in force |
| Ended | The Employment has finished. The Employee and the evidence remain |

## What this opening does not assign

No schema is written. No runtime module is authorized. Polish HR documents are not a list inside Employee. A later policy may attach, to an Employment, an employment contract (`umowa`), ZUS, BHP, risk assessment (`ocena ryzyka`), confidentiality (`tajemnica`), medical examinations (`badania`), a work certificate (`świadectwo pracy`), and other company-defined requirements. Those defaults are configuration. They are not fields of this domain.

Person and evidence already collected are not copied. HR reads them through the existing evidence model.

Legal Eligibility and Work Authorization remain upstream facts and processes. Their outcomes may be read. They are not re-decided here.

## What stays closed

| Slice | State |
|---|---|
| [Minimal Recruitment → HR handoff](recruitment-hr-minimal-handoff.md) | **SUPERSEDED** by this brief. HH-1…HH-4 are not a second product |
| Poland Work Authorization Presets | program close recorded; Gate **PASS**; not reopened |
| Legal Eligibility | Contract Gate **PASS**; Matrix Gate **not PASS** |
| Work Authorization Procedure | Contract Gate **PASS** |
| Contract | opened; Employee Record & Employment Lifecycle — Contract Gate **not PASS** |
| Schema and runtime | not authorized; feat locked |
| Release readiness | separate; this opening does not declare v1 ready |

## History

- 2026-10-03: **Persistence boundary recorded.** `hire_date` and `termination_date` belong to Employment. `workforce_employments` stays the contract-terms satellite and is not the canonical Employment. Employee Record & Employment Lifecycle — Contract Gate **not PASS** for that one reason. No schema. No runtime. No HR document policy. Feat locked.
- 2026-10-03: **Employment states recorded.** The contract names `preparing → active → ended`. The HR Legal Eligibility Gate, employee data, employment terms, pre-employment requirements, and the Ready to Start Gate are process state around `preparing`. A requirement is `satisfied`, `waived`, or `blocking`. This contract does not canonize a Polish pre-employment document list. ZUS registration is a post-start obligation. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime. Feat locked.
- 2026-10-03: **Contract opened.** [employee-record-employment-lifecycle-contract.md](../architecture/employee-record-employment-lifecycle-contract.md) names Employee, Employment, the `internal_hr` handoff, and Active → Ended. `CandidateEmployment` is not that Employment. `WorkforceEmployee.status` is not that state machine. No schema. No runtime. No HR document requirement. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. Feat locked.
- 2026-10-03: **Brief opened.** Active Product moves here from the Poland Work Authorization Presets program close. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime. The minimal handoff brief is superseded. Feat locked.
