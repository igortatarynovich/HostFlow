# Employee Record & Employment Lifecycle

**Status:** **OPENED** — contract opened. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime. Feat locked.  
**Phase class:** platform  
**Date:** 2026-10-03  
**Trusted base:** Poland Work Authorization Presets program close `37439bc5` on `integration/release-product-a-b` @ `020cb4e5` ([#402](https://github.com/igortatarynovich/HostFlow/pull/402))  
**Parents:** [contract](../architecture/employee-record-employment-lifecycle-contract.md) (`employee_record_employment_lifecycle.v1`) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Hiring workflow E2E](hiring-workflow-e2e.md) · superseded [Minimal Recruitment → HR handoff](recruitment-hr-minimal-handoff.md)

> The [contract](../architecture/employee-record-employment-lifecycle-contract.md) is opened. The Contract Gate is **not PASS**. This brief does not write a schema or a runtime.  
> HR handoff opens HR process ownership for the existing person and activates the Employee context. It does not create a person, it does not copy person or evidence data, and it does not turn the Candidate row into an Employee.  
> Creating `WorkforceEmployee` is the current runtime of that transition. It is not the canonical meaning of the handoff. Lead, Candidate, and Employee are not merged into one table.  
> Legal Eligibility and Work Authorization stay upstream. This product does not become a second legalization engine.  
> HostFlow v1 is not release-ready. Release readiness stays a separate gate.

---

## Problem

A candidate can be accepted for employment, and HostFlow still has no canonical Employment on which later HR documents and processes can hang. The handoff must be read as process ownership of the next process for the same person. The older [Minimal Recruitment → HR handoff](recruitment-hr-minimal-handoff.md) names a hire that creates or links an employee. That brief is superseded here so the queue does not carry two HR products.

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**
An accepted candidate has no canonical Employment that can become Active and later Ended, so later HR documents have nowhere stable to hang. Reading the handoff as the creation of a new person leaves that Employment designed around a second copy of the human.

**Completion proof (named consumer):**
One accepted candidate can be read along `Person + Candidate context → ready_for_employment → HR handoff accepted → HR process ownership opened → Employee context activated → Employment (preparing) → Active → Ended`. The handoff does not create a person. The Candidate row remains a candidate. The Employee context is that person's participation in the company's HR. The Employment is one labour relationship, and one Employee may have more than one over time. A later hire that does not go through Recruitment opens a new Employment on the existing Employee context and creates no Candidate. Evidence already held, including the passport, stays on the existing evidence model. Ended keeps the Employee context, the Person, and the evidence.

**False close (reject):** turning the Candidate row into the Employee; creating a person at the handoff; copying person or evidence into a second store; treating the `WorkforceEmployee` insert as the canonical meaning of the handoff; merging Lead, Candidate, and Employee into one table in this opening; a Polish HR document pack written into the Employee domain; a second legalization decision inside HR; deleting the Employee context, the Person, or the evidence when the Employment ends.

## Order

1. This brief. The chain and the contexts are named. Employee Record & Employment Lifecycle — Contract Gate **not PASS**.
2. The [contract](../architecture/employee-record-employment-lifecycle-contract.md) is opened. Person, the Employee context, Employment, the HR handoff, and `preparing → active → ended` are named. The handoff is a process and context transition over the same person identity. Legal eligibility, data, terms, and requirements are gates around `preparing`. Employee Record & Employment Lifecycle — Contract Gate **not PASS**.
3. Runtime. Not authorized.

## Chain

```text
Person + Candidate context
→ ready_for_employment
→ HR handoff accepted
→ HR process ownership opened
→ Employee context activated
→ Employment (preparing)
→ Active
→ Ended
```

A hire that does not pass through Recruitment starts at the existing Employee context and creates a new Employment. It creates no Candidate.

The [contract](../architecture/employee-record-employment-lifecycle-contract.md) is the source for the path around those states. Employment states are `preparing → active → ended`. The HR Legal Eligibility Gate, employee data, employment terms, pre-employment requirements, and the Ready to Start Gate sit around `preparing`. They are not further Employment states. `WorkforceEmployee.status` stays another plane. The persistence boundary names `hire_date` and `termination_date` as Employment facts. `workforce_employments` is the contract-terms satellite, not the canonical Employment. The cardinality is Employee 1:N Employment 1:N contract/terms records. Creating `WorkforceEmployee` is the current runtime of activating the Employee context. It is not the canonical meaning of the handoff. No schema is written.

| Term | What it is |
|---|---|
| Person | The identity of the human. No Person table is authorized |
| Candidate | That person's participation in Recruitment. The row stays a candidate after the handoff |
| `ready_for_employment` | The hiring outcome the handoff consumes. This brief does not redefine it |
| HR handoff | The act that opens HR process ownership for the existing person. It does not create a person |
| Employee | The HR context of that person in the company's HR scope. Not a second copy of the person |
| Employment | One labour relationship of that Employee. An Employee may have more than one over time |
| `preparing` | The Employment exists and is not yet in force |
| Active | The Employment is in force |
| Ended | The Employment has finished. The Employee context, the Person, and the evidence remain |

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

- 2026-10-03: **Handoff recorded as a process transition.** The handoff opens HR process ownership for the existing person and activates the Employee context. It does not create a person and it does not copy person or evidence data. Creating `WorkforceEmployee` stays the current runtime of that transition. Lead, Candidate, and Employee are not merged into one table. A later hire without Recruitment creates no Candidate. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime. Feat locked.
- 2026-10-03: **Contract cardinality recorded.** Employee 1:N Employment 1:N contract/terms records. `workforce_employments` stays the contract card of one Employment. A renewal does not create an Employment and does not end one. `hire_date` is not `start_date`. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime. Feat locked.
- 2026-10-03: **Persistence boundary recorded.** `hire_date` and `termination_date` belong to Employment. `workforce_employments` stays the contract-terms satellite and is not the canonical Employment. Employee Record & Employment Lifecycle — Contract Gate **not PASS** for that one reason. No schema. No runtime. No HR document policy. Feat locked.
- 2026-10-03: **Employment states recorded.** The contract names `preparing → active → ended`. The HR Legal Eligibility Gate, employee data, employment terms, pre-employment requirements, and the Ready to Start Gate are process state around `preparing`. A requirement is `satisfied`, `waived`, or `blocking`. This contract does not canonize a Polish pre-employment document list. ZUS registration is a post-start obligation. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime. Feat locked.
- 2026-10-03: **Contract opened.** [employee-record-employment-lifecycle-contract.md](../architecture/employee-record-employment-lifecycle-contract.md) names Employee, Employment, the `internal_hr` handoff, and Active → Ended. `CandidateEmployment` is not that Employment. `WorkforceEmployee.status` is not that state machine. No schema. No runtime. No HR document requirement. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. Feat locked.
- 2026-10-03: **Brief opened.** Active Product moves here from the Poland Work Authorization Presets program close. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime. The minimal handoff brief is superseded. Feat locked.
