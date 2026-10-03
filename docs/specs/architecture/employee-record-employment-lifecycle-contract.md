# Employee Record & Employment Lifecycle

**Status:** **Opened** — Employee Record & Employment Lifecycle — Contract Gate **not PASS**. No schema. No runtime module.  
**Date:** 2026-10-03  
**Machine id:** `employee_record_employment_lifecycle.v1` — named here. No runtime module.  
**Parents:** [brief](../tasks/employee-record-employment-lifecycle.md) · [ready_for_employment.v1](ready-for-employment-contract.md) · [handoff contract](handoff-contract.md) · [legal_eligibility.v1](legal-eligibility-contract.md)

> Employment has three states: `preparing → active → ended`.  
> Legal eligibility, employee data, employment terms, and pre-employment requirements are gates and process state around `preparing`. They are not further Employment states.  
> This file adds no table, no column, no screen, and no document requirement.  
> Legal Eligibility and Work Authorization stay the upstream authorities. HR reads them at its own checkpoint and does not grow a second legalization engine.  
> Feat stays locked. HostFlow v1 is not release-ready.

---

## Question

After Recruitment has a person who is ready for employment, which HR records exist, which states does one Employment have, and which checks sit around the state before Active?

This contract answers that. It does not answer which HR documents a company requires.

---

## Discovery

The names below are the records the repository already stores. This opening does not change them.

| Stored record | What it is today | What it is not |
|---|---|---|
| `Candidate` | The recruitment person. `accept_handoff` for `internal_hr` sets the candidate stage to `processing_by_hr` and leaves the row in place | An Employee |
| `ready_for_employment.v1` | The package Recruitment emits. Its forbidden keys include `employee_id` and `create_employee` | An Employee create, and not an Employment |
| `CandidateHandoff` with `destination = internal_hr` | The HR handoff record. `accept_handoff` then calls `accept_internal_hr_handoff` | A client-portal transfer. `client_portal` is outside this product |
| `WorkforceEmployee` | The HR person. `candidate_id` links it to the Candidate. `handoff_from_candidate` returns the existing row for that candidate in the tenant or inserts one | A second copy of the Candidate. Also not a labour relationship of its own |
| `WorkforceEmployee.status` | One column. The allowed words include `onboarding`, `active`, `on_sick_leave`, `on_vacation`, `on_leave`, `suspended`, `contract_ending`, and `terminated` | The Employment state machine of this contract. That column is another plane |
| `hire_date` and `termination_date` on `WorkforceEmployee` | Dates on the person row | A separate Employment row |
| `CandidateEmployment` | Prior jobs captured on the candidate | The Employment this product names |
| `delayed_hr_workforce_creation_enabled` | A tenant flag. When it is on, accept opens an HR review and does not create the workforce row yet | A state of Employee or Employment. This contract does not choose the flag |
| `legal_eligibility.v1` | The decision chain `citizenship_class → stay_basis → work_authorization_basis → valid_for_this_employment` | An HR-owned legalization engine |

`handoff_from_candidate` is idempotent for one candidate in one tenant. The store therefore holds at most one `WorkforceEmployee` for that pair.

`workforce_employments` (`WorkforceEmployment`) is a separate table. `ensure_hr_profiles_bundle` inserts one placeholder row (`contract_type = unknown`) when the employee has none. Its `lifecycle_status` defaults to `issued`. The contract-control path also reads `signed`, `active`, `expiring`, `renewed`, and `terminated`. Those words are the lifecycle of a contract document. They are not `preparing`, `active`, and `ended`.

The same labour relationship is also stored on the person row: `hire_date`, `termination_date`, `probation_end`, `company_id`, `vacancy_id`, `recruiter_user_id`, `handoff_at`, and `handoff_by_user_id`. `start_date`, `end_date`, and `probation_end` exist again on `workforce_employments`.

The structural gap is that the canonical Employment is not a persistence entity. `WorkforceEmployee` carries the person and the relationship dates together. `workforce_employments` carries contract terms and a document lifecycle.

---

## Path

```text
Candidate
→ ready_for_employment.v1
→ HR handoff (internal_hr)
→ find the existing Employee, or create one
→ create a new Employment in preparing
→ HR Legal Eligibility Gate
→ when blocked: continue the existing Legal Eligibility / Work Authorization process
→ Legal Eligibility PASS for this Employment
→ employee data completion
→ Employment terms
→ pre-employment requirements
→ Ready to Start Gate
→ Employment active
→ post-start obligations
→ Employment ended
→ Employee remains
```

The Employment machine inside that path is only:

```text
preparing → active → ended
```

---

## Terms

| Term | Meaning |
|---|---|
| Candidate | The recruitment person. The row stays a candidate after the handoff |
| `ready_for_employment.v1` | The package the handoff consumes. This contract does not redefine it |
| HR handoff | `CandidateHandoff` whose destination is `internal_hr`. Accept finds or creates the HR-side identity. It does not turn the Candidate row into an Employee, and it does not delete the Candidate |
| Employee | The person in the company's HR context. The stored plane is `WorkforceEmployee`, linked by `candidate_id`. A person who returns uses the existing Employee |
| Employment | One labour relationship of that Employee with the employer. One Employee may have more than one over time. A return creates a new Employment and runs the applicable workflow again |
| `preparing` | The Employment exists and is not yet in force. HR conducts the gates below against this object |
| `active` | That Employment is in force. Active is the start of the labour relationship. It is not `onboarding`, and it is not "HR has begun the paperwork" |
| `ended` | That Employment has finished. The Employee remains. The Candidate remains. Evidence already held remains. The Employment row remains |

`onboarding`, sick leave, leave, vacation, and `suspended` live on `WorkforceEmployee.status`. They do not define the Employment lifecycle, and this contract does not map them onto `preparing`, `active`, or `ended`.

---

## Gates around `preparing`

These checkpoints are process state. Each one can be open, blocked, or passed while the Employment stays `preparing`. None of them is an Employment state.

### HR Legal Eligibility Gate

HR reads the same policy and the same source of truth as Recruitment: `legal_eligibility.v1`, chain `citizenship_class → stay_basis → work_authorization_basis → valid_for_this_employment`. The checkpoint is operational and belongs to this Employment.

The gate is PASS when that chain is determined and `valid_for_this_employment` holds for this Employment.

When a fact or an outcome is missing, the Employment stays `preparing` and is blocked on the legalization requirement. The existing Legal Eligibility / Work Authorization workflow continues, the missing evidence or outcome appears, and this gate is calculated again. HR does not decide the chain itself.

A material change to the Employment terms can require this gate again, because the Employment has to match the legalization basis.

### Employee data

After Legal Eligibility PASS, HR completes the employee data the later formalities need. Facts HostFlow already holds are not entered again. Missing facts are requested or filled.

`kwestionariusz osobowy` is a representation of that canonical employee data. It is not a second copy of the person. This contract names the representation and does not design the form.

### Employment terms

The facts of this relationship include the employer, the position or profession, the employment basis or type, the workplace, the start date, the working time, and the remuneration, plus any further term the relationship needs. This opening names those facts and adds no column.

### Pre-employment requirements

Once the data and the terms the policy needs are present, policy forms the requirements for this Employment. Each requirement is `satisfied`, `waived`, or `blocking`. A requirement may depend on another requirement. Independent requirements may proceed together.

A later company policy may express a Polish sequence such as a medical examination, BHP, occupational-risk acknowledgements, an agreement, declarations, and company requirements. This contract does not canonize a Polish pre-employment document list. A draft agreement need not wait for a medical examination; that is an example of a dependency, not a required order.

### Ready to Start Gate

This gate is the permission to move `preparing → active`. It can require, at the moment of the check:

- HR Legal Eligibility Gate PASS for this Employment now
- every required pre-start requirement `satisfied` or `waived`
- Employment terms complete
- the agreements and formalities that policy marks as required for start, done

A `blocking` pre-start requirement holds this gate. It does not add an Employment state.

---

## After Active

Obligations that begin once the relationship is in force attach to the `active` Employment. Their own progress, such as due, submitted, or confirmed, is process state. It does not sit between `preparing` and `active`.

ZUS registration is a post-start obligation. It is not a universal precondition of Active. Payroll, attendance, leave, renewals, and expirations are the same kind of later process.

When the relationship finishes, `active → ended`. Termination requirements, such as a reason, a work certificate, or a ZUS deregistration, may follow. They do not delete the Employment, the Employee, the Candidate, or the evidence.

---

## What this opening does not assign

No schema is written. No runtime module is authorized. No screen is changed.

This file writes no HR document requirement. An employment contract, ZUS, BHP, a risk assessment, a confidentiality undertaking, a medical examination, a work certificate, and any company-defined requirement stay later configuration. They are not fields of Employee and they are not states of Employment.

Person facts and evidence already held stay on the existing evidence model. HR may read them. This contract does not copy them into a second store.

---

## Persistence boundary

This section names ownership. It adds no table, no column, and no migration. `workforce_employments` stays the contract-terms satellite. It is not renamed into the canonical Employment.

One Employee has many Employments. Finding the existing `WorkforceEmployee` for a candidate in a tenant remains the Employee identity rule. Creating the labour relationship is a different insert. The auto-bundle placeholder is not that insert.

| Fact stored today | Where it sits | Owner |
|---|---|---|
| `tenant_id`, `candidate_id`, `display_name`, `notes` | `workforce_employees` | Employee. `candidate_id` is the link. The Candidate row stays a candidate |
| `own_company_id` | `workforce_employees` | Employee. The HR workspace company copied from the candidate |
| `status` (`onboarding`, `on_sick_leave`, `on_vacation`, `on_leave`, `suspended`, and the other allowed words) | `workforce_employees` | Employee operational plane. Not `preparing`, `active`, or `ended` |
| `candidate_snapshot` | `workforce_employees` | The handoff that started one Employment. A later hire does not overwrite the only copy on the person as its canonical home |
| `hire_date` | `workforce_employees` | Employment. The start of this relationship. The same fact as `workforce_employments.start_date` |
| `termination_date` | `workforce_employees` | Employment. The end of this relationship. The same fact as `workforce_employments.end_date` |
| `probation_end` | both rows | Employment. A term of this relationship, not a lifecycle state |
| `company_id` | `workforce_employees` | Employment. The employer of this hire |
| `vacancy_id` | both rows | Employment. The vacancy this hire came from |
| `recruiter_user_id` | `workforce_employees` | Employment. The recruiter of this hire |
| `handoff_at`, `handoff_by_user_id` | `workforce_employees` | Employment. The handoff that initiated this relationship. `meta.internal_hr_handoff_id` is that handoff's id |
| `contract_type`, `employer_name`, `rate_model`, `schedule`, `signed_at`, `conditions_text`, `expiry_date`, `latest_annex_ref` | `workforce_employments` | Employment terms. Already off the person row. This boundary does not move them |
| `WorkforceEmployment.lifecycle_status` | `workforce_employments` | Contract-document lifecycle, default `issued`. Not the Employment state |

The canonical Employment, once persisted, owns `employee_id`, the state `preparing | active | ended`, the employer, the start, the end, the initiating handoff, and the terms listed above. Position, workplace, and working time are terms of that relationship. They are not columns of `workforce_employees` today, and this boundary adds no column for them.

`meta` on `workforce_employees` mixes the handoff id with the HR pipeline. This boundary assigns `internal_hr_handoff_id` to the Employment and does not split the rest of the blob.

Tax, insurance, compliance, work eligibility, payroll, ZUS, document context, onboarding tasks, absences, leave, and lifecycle events stay employee-scoped satellites. This boundary does not re-home them. HR document policy stays untouched.

---

## Employee Record & Employment Lifecycle — Contract Gate

**Outcome:** **not PASS**. One reason: the canonical Employment is defined above and is not a persistence entity. `WorkforceEmployee` still holds the relationship dates, and `workforce_employments` is the contract-terms satellite. This opening does not authorize the schema or a runtime that would separate them.

Feat stays locked. Runtime is not authorized.
