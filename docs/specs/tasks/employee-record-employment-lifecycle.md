# Employee Record & Employment Lifecycle

**Status:** **OPENED** — contract opened. Employee Record & Employment Lifecycle — Contract Gate **PASS**. Employment Persistence Schema opened. Employment Runtime opened: an accepted `internal_hr` handoff creates `Employment(preparing)` on the existing Employee. HR Legal Eligibility Gate opened on that Employment. PASS does not move it to active. Employee Data / kwestionariusz ownership opened: one live owner per person fact; the kwestionariusz is a view; a sufficient set leaves Employment `preparing`. Employment Terms discovery opened: agreed terms of this Employment; the contract card represents them; complete and incomplete leave state `preparing`. Employment Terms Contract Gate **PASS** (`employment_terms.v1`): the agreed terms are a snapshot of this Employment. Completeness leaves state `preparing` and permits pre-employment requirements. Employment Terms Schema is indicated and is not opened. Feat locked.  
**Phase class:** platform  
**Date:** 2026-10-03  
**Trusted base:** Poland Work Authorization Presets program close `37439bc5` on `integration/release-product-a-b` @ `020cb4e5` ([#402](https://github.com/igortatarynovich/HostFlow/pull/402))  
**Parents:** [contract](../architecture/employee-record-employment-lifecycle-contract.md) (`employee_record_employment_lifecycle.v1`) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Hiring workflow E2E](hiring-workflow-e2e.md) · superseded [Minimal Recruitment → HR handoff](recruitment-hr-minimal-handoff.md)

> The [contract](../architecture/employee-record-employment-lifecycle-contract.md) is opened. The Contract Gate is **PASS**. Employment Persistence Schema is the migration and the storage proofs. Employment Runtime opens `Employment(preparing)` when an `internal_hr` handoff is accepted. The HR Legal Eligibility Gate reads `legal_eligibility.v1` for that Employment. PASS does not move it to active. Employee Data / kwestionariusz ownership is opened. One live owner per person fact. The kwestionariusz is a view. A sufficient set leaves Employment `preparing`. Employment Terms discovery is opened. Agreed terms belong to this Employment. The contract card represents them. Complete and incomplete leave state `preparing`. Employment Terms Contract Gate **PASS** (`employment_terms.v1`). The snapshot is independent of the live vacancy and of the contract card. Employment Terms Schema is indicated and is not opened. Pre-employment requirements wait.  
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

1. This brief. The chain and the contexts are named.
2. The [contract](../architecture/employee-record-employment-lifecycle-contract.md) is opened. Person, the Employee context, Employment, the HR handoff, and `preparing → active → ended` are named. The handoff is a process and context transition over the same person identity. Legal eligibility, data, terms, and requirements are gates around `preparing`. `workforce_employments` is the contract card, 1:N under Employment. The backfill is one Employment per existing employee. Employee Record & Employment Lifecycle — Contract Gate **PASS**.
3. Employment Persistence Schema is opened. It is the persistence model, the migration and backfill, and the storage proofs.
4. Employment Runtime is opened. An accepted `internal_hr` handoff finds the existing Employee context and creates a new `Employment(preparing)`. A repeat hire adds another Employment and leaves the previous one unchanged. A contract card does not create an Employment.
5. HR Legal Eligibility Gate is opened on that `Employment(preparing)`. It reads `legal_eligibility.v1` (`citizenship_class → stay_basis → work_authorization_basis → valid_for_this_employment`) and the Employment context. It does not copy evidence and it does not create a second legalization model. PASS, FAIL, and BLOCKED leave the Employment `preparing`. A later change of the chain or of that Employment context makes the recorded decision stale.
6. Employee Data / kwestionariusz ownership is opened on that Employee context. Each person fact has one live owner, and today that anchor is `Candidate`. The kwestionariusz is a view of those owners. HR writes a missing or updated fact on its owner. Evidence is not copied. An insufficient set leaves the Employment `preparing`. A sufficient set leaves it `preparing` and is not Ready to Start.
7. Employment Terms discovery is opened for that Employment. The client is `hr_employments.client_company_id`. The workspace stays `workforce_employees.own_company_id`. Vacancy, `started_on`, `ended_on`, and handoff provenance stay on `hr_employments`. Position, workplace, working time, pay, and a fixed-or-indefinite flag have no second column. `contract_type`, `rate_model`, `schedule`, and `probation_end` stay on the contract card as the current store. The card is not the Employment. A vacancy may default an offer and is not the agreed term. Complete and incomplete leave `hr_employments.state` at `preparing`. No Polish `umowa` policy.
8. Employment Terms Contract Gate **PASS**. `employment_terms.v1` names position, contract basis, structured work time, workplace, compensation, duration (`fixed` or `indefinite`), fixed-term end, and probation. Vacancy fields are a one-time default. The contract card may display the snapshot and does not rewrite it. A later edit of the vacancy or of the card leaves the snapshot as it was. No current column is that snapshot. Employment Terms Schema is indicated and is not opened. Completeness leaves `hr_employments.state` at `preparing` and is the permission to continue to pre-employment requirements. Ready to Start waits. Feat locked.

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
| Ended | The Employment has finished. The Employee and the evidence remain. The Person remains |

## What this opening does not assign

The contract writes no schema. Employment Persistence Schema is the migration in this slice. No runtime module is authorized. Polish HR documents are not a list inside Employee. A later policy may attach, to an Employment, an employment contract (`umowa`), ZUS, BHP, risk assessment (`ocena ryzyka`), confidentiality (`tajemnica`), medical examinations (`badania`), a work certificate (`świadectwo pracy`), and other company-defined requirements. Those defaults are configuration. They are not fields of this domain.

Person and evidence already collected are not copied. HR reads them through the existing evidence model.

Legal Eligibility and Work Authorization remain upstream facts and processes. Their outcomes may be read. They are not re-decided here.

## What stays closed

| Slice | State |
|---|---|
| [Minimal Recruitment → HR handoff](recruitment-hr-minimal-handoff.md) | **SUPERSEDED** by this brief. HH-1…HH-4 are not a second product |
| Poland Work Authorization Presets | program close recorded; Gate **PASS**; not reopened |
| Legal Eligibility | Contract Gate **PASS**; Matrix Gate **not PASS** |
| Work Authorization Procedure | Contract Gate **PASS** |
| Contract | opened; Employee Record & Employment Lifecycle — Contract Gate **PASS**. Employment Persistence Schema opened. Employment Runtime opened |
| Schema | opened; migration and storage proofs |
| Employment Runtime | opened; accepted `internal_hr` handoff creates `Employment(preparing)`. Feat locked |
| HR Legal Eligibility Gate | opened on `Employment(preparing)`. Reads `legal_eligibility.v1`. PASS does not move the Employment to active. Feat locked |
| Employee Data | ownership opened. One live owner per person fact. The kwestionariusz is a view. A sufficient set leaves Employment `preparing`. Feat locked |
| Employment Terms | discovery opened. Employment Terms Contract Gate **PASS** (`employment_terms.v1`). The agreed terms are a snapshot of this Employment. Completeness leaves state `preparing`. Employment Terms Schema is indicated and is not opened. Feat locked |
| Release readiness | separate; this opening does not declare v1 ready |

## History

- 2026-10-04: **Employment Terms Contract Gate PASS.** `employment_terms.v1` is the snapshot of agreed terms for one Employment. Vacancy defaults are copied once. The contract card does not rewrite the snapshot. No current store holds it. Employment Terms Schema is indicated and is not opened. Completeness leaves state `preparing`. No schema. No runtime. Feat locked.
- 2026-10-04: **Employment Terms discovery opened.** Relationship context stays on `hr_employments` and `workforce_employees.own_company_id`. The client column is `client_company_id`. Substantive terms that already have a column stay on the contract card. No parallel salary, FTE, workplace, or contract-type field. Complete and incomplete leave state `preparing`. No schema. No runtime. Feat locked.
- 2026-10-04: **Employee Data ownership opened.** Person facts keep the owners already in the store. `Candidate` is the temporary identity anchor. The kwestionariusz is a view, not a stored questionnaire. A sufficient set leaves the Employment `preparing` and is not Ready to Start. Employment terms wait. No schema. No runtime. Feat locked.
- 2026-10-04: **HR Legal Eligibility Gate opened.** The checkpoint is bound to one `Employment(preparing)`. It reads `legal_eligibility.v1` and does not copy evidence. PASS does not move the Employment to active. FAIL and BLOCKED leave it `preparing`. A change of the chain or of the Employment context makes the recorded decision stale. Next layer is Employee Data / kwestionariusz. Feat locked.
- 2026-10-03: **Employment Runtime opened.** An accepted `internal_hr` handoff creates `Employment(preparing)` on the existing Employee. A repeat handoff adds another Employment and does not rewrite the previous one. HR Legal Eligibility Gate is not this slice. Feat locked.
- 2026-10-03: **Employment Persistence Schema opened.** `hr_employments` is the labour relationship. `workforce_employments.employment_id` points at it. One backfilled Employment per existing employee. Accepted handoff does not create an Employment. No runtime of that creation. Feat locked.
- 2026-10-03: **Contract Gate PASS.** Repository discovery: `workforce_employments` is already 1:N contract history per employee, not the labour relationship. Backfill is one Employment per existing `WorkforceEmployee`, with those cards attached. Relationship facts move to Employment in the same migration. `hire_date` does not choose `active`. Ready to Start is the only `preparing → active`. No reverse edge. Next slice is Employment Persistence Schema. No schema. No runtime. Feat locked.
- 2026-10-03: **Handoff recorded as a process transition.** The handoff opens HR process ownership for the existing person and activates the Employee context. It does not create a person and it does not copy person or evidence data. Creating `WorkforceEmployee` stays the current runtime of that transition. Lead, Candidate, and Employee are not merged into one table. A later hire without Recruitment creates no Candidate. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime. Feat locked.
- 2026-10-03: **Contract cardinality recorded.** Employee 1:N Employment 1:N contract/terms records. `workforce_employments` stays the contract card of one Employment. A renewal does not create an Employment and does not end one. `hire_date` is not `start_date`. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime. Feat locked.
- 2026-10-03: **Persistence boundary recorded.** `hire_date` and `termination_date` belong to Employment. `workforce_employments` stays the contract-terms satellite and is not the canonical Employment. Employee Record & Employment Lifecycle — Contract Gate **not PASS** for that one reason. No schema. No runtime. No HR document policy. Feat locked.
- 2026-10-03: **Employment states recorded.** The contract names `preparing → active → ended`. The HR Legal Eligibility Gate, employee data, employment terms, pre-employment requirements, and the Ready to Start Gate are process state around `preparing`. A requirement is `satisfied`, `waived`, or `blocking`. This contract does not canonize a Polish pre-employment document list. ZUS registration is a post-start obligation. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime. Feat locked.
- 2026-10-03: **Contract opened.** [employee-record-employment-lifecycle-contract.md](../architecture/employee-record-employment-lifecycle-contract.md) names Employee, Employment, the `internal_hr` handoff, and Active → Ended. `CandidateEmployment` is not that Employment. `WorkforceEmployee.status` is not that state machine. No schema. No runtime. No HR document requirement. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. Feat locked.
- 2026-10-03: **Brief opened.** Active Product moves here from the Poland Work Authorization Presets program close. Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime. The minimal handoff brief is superseded. Feat locked.
