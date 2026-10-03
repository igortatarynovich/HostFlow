# Employee Record & Employment Lifecycle

**Status:** **Accepted** — Employee Record & Employment Lifecycle — Contract Gate **PASS**. No schema is written in this file. The next slice is Employment Persistence Schema. No runtime module.  
**Date:** 2026-10-03  
**Machine id:** `employee_record_employment_lifecycle.v1` — named here. No runtime module.  
**Parents:** [brief](../tasks/employee-record-employment-lifecycle.md) · [ready_for_employment.v1](ready-for-employment-contract.md) · [handoff contract](handoff-contract.md) · [legal_eligibility.v1](legal-eligibility-contract.md)

> Employment has three states: `preparing → active → ended`.  
> Legal eligibility, employee data, employment terms, and pre-employment requirements are gates and process state around `preparing`. They are not further Employment states.  
> HR handoff transfers process ownership of the next process for the same person. It does not create a person and it does not copy person or evidence data.  
> Creating `WorkforceEmployee` is the current runtime of opening the HR context. It is not the canonical meaning of the handoff.  
> Employment moves only `preparing → active → ended`. Ready to Start is the only path into `active`. There is no reverse transition.  
> `workforce_employments` stays the contract card. One Employment has many cards. The repository already stores them that way.  
> This file adds no table, no column, no screen, and no document requirement. It does not merge Lead, Candidate, and Employee into one table.  
> Legal Eligibility and Work Authorization stay the upstream authorities. HR reads them at its own checkpoint and does not grow a second legalization engine.  
> Feat stays locked. HostFlow v1 is not release-ready.

---

## Question

After Recruitment has a person who is ready for employment, what does the HR handoff transfer, which HR records exist, which states does one Employment have, and which checks sit around the state before Active?

This contract answers that. It does not answer which HR documents a company requires. It does not decide that Lead, Candidate, and Employee share one table.

---

## Discovery

The names below are the records the repository already stores. This opening does not change them.

| Stored record | What it is today | What it is not |
|---|---|---|
| `Candidate` | The Recruitment context of a person. `accept_handoff` for `internal_hr` sets the candidate stage to `processing_by_hr` and leaves the row in place. Today this row is also the temporary identity anchor in storage | An Employee, and not a person created by the handoff |
| `ready_for_employment.v1` | The package Recruitment emits. Its forbidden keys include `employee_id` and `create_employee` | An Employee create, and not an Employment |
| `CandidateHandoff` with `destination = internal_hr` | The HR handoff record. `accept_handoff` then calls `accept_internal_hr_handoff` | A client-portal transfer. `client_portal` is outside this product. Also not the creation of a person |
| `WorkforceEmployee` | The current runtime of the HR context. `candidate_id` links it to the Candidate. `handoff_from_candidate` returns the existing row for that candidate in the tenant or inserts one. That insert opens the HR context in today's store | A new person. It is not the canonical meaning of the handoff. Also not a labour relationship of its own |
| `WorkforceEmployee.status` | One column. The allowed words include `onboarding`, `active`, `on_sick_leave`, `on_vacation`, `on_leave`, `suspended`, `contract_ending`, and `terminated` | The Employment state machine of this contract. That column is another plane |
| `hire_date` and `termination_date` on `WorkforceEmployee` | Dates on the `WorkforceEmployee` row | A separate Employment row |
| `CandidateEmployment` | Prior jobs captured on the candidate | The Employment this product names |
| `delayed_hr_workforce_creation_enabled` | A tenant flag. When it is on, accept opens an HR review and does not create the workforce row yet | A state of Employee or Employment. This contract does not choose the flag |
| `legal_eligibility.v1` | The decision chain `citizenship_class → stay_basis → work_authorization_basis → valid_for_this_employment` | An HR-owned legalization engine |

`handoff_from_candidate` is idempotent for one candidate in one tenant. The store therefore holds at most one `WorkforceEmployee` for that pair. That key is today's link. The canonical identity is the person. This opening adds no Person table and does not retarget the link. [Person](person-identity-layer-and-roadmap.md) stays deferred as persistence.

`workforce_employments` (`WorkforceEmployment`) is a separate table. `ensure_hr_profiles_bundle` inserts one placeholder row (`contract_type = unknown`) when the employee has none. Its `lifecycle_status` defaults to `issued`. The contract-control path also reads `signed`, `active`, `expiring`, `renewed`, and `terminated`. Those words are the lifecycle of a contract document. They are not `preparing`, `active`, and `ended`.

The `WorkforceEmployee` row also holds `hire_date`, `termination_date`, `probation_end`, `company_id`, `vacancy_id`, `recruiter_user_id`, `handoff_at`, and `handoff_by_user_id`. `workforce_employments` holds `start_date`, `end_date`, and `probation_end` as dates of that contract card. Those contract dates are not the bounds of the labour relationship.

The structural gap in the store is that the canonical Employment is not yet a table. `WorkforceEmployee` carries the HR context and the relationship dates together. `workforce_employments` carries contract terms and a document lifecycle, and it points only at `employee_id`. The persistence section defines the table and the backfill that close that gap. This file does not create the table.

---

## Path

```text
Person
→ Candidate context
→ ready_for_employment.v1
→ HR handoff accepted (internal_hr)
→ HR process ownership opened for that Person
→ Employee context activated
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
→ Employee context remains
→ Person remains
```

A hire that does not pass through Recruitment:

```text
existing Employee context
→ create a new Employment in preparing
```

That path creates no Candidate and no person.

The Employment machine inside that path is only:

```text
preparing → active → ended
```

---

## What the handoff transfers

The handoff transfers responsibility for the next process. The person already exists. The evidence already exists. [ADR-037](ADR-037-lifecycle-identity-canon.md) already allows a handoff to create or activate `hr.employee.*`. Activation of the HR context is the canonical effect. The `WorkforceEmployee` insert, when the row is absent, is how today's runtime performs that activation. The operational steps stay in the [handoff contract](handoff-contract.md).

| Carried | Meaning |
|---|---|
| Who | A reference to the person. Today that reference is the Candidate. It is not a copy of the person |
| From | The Recruitment process and the vacancy, when the handoff comes from Recruitment |
| Why | `ready_for_employment.v1` |
| To | `internal_hr` |
| For | Starting one employment preparation |
| Context | The employer, vacancy, position, and start parameters already known. A parameter that is not known stays absent |
| Evidence | Links to existing evidence. Not copies |
| Provenance | Who transferred it and when, and who accepted it and when |

Acceptance gives HR the right and the duty to continue that process.

Ownership sits on the process instance. The Recruitment process has its operator. Employment preparation has its operator. A legalization process has its operator. The person has no single owner, because one person may stand in more than one process at the same time.

The operator works inside the module that owns the process. A recruiter opening the person sees the Recruitment surface: vacancy, pipeline, source, communication, interviews, recruitment documents, and readiness. An HR operator opening the same person sees the HR surface: the Employee context, Employment, the legal gate, employee data, employment terms, requirements, and the later workforce obligations. A manager may see only the part of Employment that the permissions allow. The card may be one. Its surface is the operator's role, the active process contexts, the permissions, and the tenant or company scope. This contract does not merge the module screens. Each module keeps the interface of its own process.

Lead, Candidate, and Employee name process contexts of one person. Lead is the intake context. Candidate is that person's participation in Recruitment. Employee is that person's participation in the company's HR context. Employment is one labour relationship of that Employee with an employer. This contract does not decide that those contexts are one physical table. Whether today's `Lead`, `Candidate`, and `WorkforceEmployee` rows are three person stores or three projections of one identity is a later check. It is not this opening.

A first hire runs Person, then a Candidate context, then the handoff, then the Employee context, then Employment. After that Employment has ended, the Employee context remains. A later hire through Recruitment opens a new Candidate context, reuses that Employee context, and creates Employment again. A later hire that does not go through Recruitment reuses the Employee context and creates Employment again, and it creates no Candidate.

---

## Terms

| Term | Meaning |
|---|---|
| Person | The identity of the human. Shared name, contacts, and passport evidence belong to this identity and to the shared evidence model. No Person table is authorized. Today the temporary identity anchor in storage is still `Candidate` |
| Candidate | That person's participation in Recruitment. The row stays a candidate after the handoff |
| `ready_for_employment.v1` | The package the handoff consumes. This contract does not redefine it |
| HR handoff | `CandidateHandoff` whose destination is `internal_hr`. Accept opens HR process ownership for the existing person and activates the Employee context. It does not create a person, it does not copy person or evidence data, it does not turn the Candidate row into an Employee, and it does not delete the Candidate |
| Employee | The HR context of that person in the company's HR scope. It carries the HR identity in that scope, HR provenance, and HR operational state. The stored plane today is `WorkforceEmployee`, linked by `candidate_id`. A person who returns uses the existing Employee context. Shared person facts are not written here again |
| Employment | One labour relationship of that Employee with the employer. One Employee may have more than one over time. A return creates a new Employment and runs the applicable workflow again. A return through Recruitment uses a new Candidate context. A return that does not go through Recruitment creates no Candidate |
| `preparing` | The Employment exists and is not yet in force. HR conducts the gates below against this object |
| `active` | That Employment is in force. Active is the start of the labour relationship. It is not `onboarding`, and it is not "HR has begun the paperwork" |
| `ended` | That Employment has finished. The Employee remains. The Person remains. The Candidate remains when the hire came through Recruitment. Evidence already held remains. The Employment row remains |

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

When the relationship finishes, `active → ended`. Termination requirements, such as a reason, a work certificate, or a ZUS deregistration, may follow. They do not delete the Employment, the Employee context, the Person, the Candidate, or the evidence.

---

## What this opening does not assign

No schema is written. No runtime module is authorized. No screen is changed.

This file does not merge Lead, Candidate, and Employee into one table. It does not authorize a Person table and it does not open a Person domain. Creating `WorkforceEmployee` on accept stays the current runtime. This contract does not retarget that insert and does not remove it.

This file writes no HR document requirement. An employment contract, ZUS, BHP, a risk assessment, a confidentiality undertaking, a medical examination, a work certificate, and any company-defined requirement stay later configuration. They are not fields of Employee and they are not states of Employment.

Person facts and evidence already held stay on the existing evidence model. HR may read them. This contract does not copy them into a second store.

---

## Persistence boundary

This section names ownership. It adds no table, no column, and no migration. `workforce_employments` stays the contract-terms satellite. It is not renamed into the canonical Employment.

The cardinality is Employee 1:N Employment 1:N contract/terms records. It is not Employment 1:1 `workforce_employments`.

One Employee has many Employments. One Employment has many contract/terms records: the first agreement, a renewal, a replacement agreement, or another change of contractual terms. A new contract record does not create a new Employment and does not move that Employment to `ended`. A repeat hire inserts a new Employment in `preparing` and attaches new contract/terms records to that Employment. The previous Employment and its contract records stay as they were.

Finding the existing `WorkforceEmployee` for a candidate in a tenant is the current runtime link. The canonical rule is one Employee context for the person in that company's HR scope. A later Employment does not create a person. When the later hire does not come from Recruitment, it does not require a new Candidate. This boundary does not change the `candidate_id` column. Creating the labour relationship is a different insert. The auto-bundle placeholder is one contract/terms record, not that insert, and not the only record an Employment may have. `latest_annex_ref` on a single row does not make the link one-to-one.

Today each `workforce_employments` row points at `employee_id` only. The link this boundary names, and does not add, is from the contract/terms record to the Employment it belongs to.

| Fact stored today | Where it sits | Owner |
|---|---|---|
| `tenant_id`, `candidate_id`, `display_name`, `notes` | `workforce_employees` | Employee. `candidate_id` is the link. The Candidate row stays a candidate |
| `own_company_id` | `workforce_employees` | Employee. The HR workspace company copied from the candidate |
| `status` (`onboarding`, `on_sick_leave`, `on_vacation`, `on_leave`, `suspended`, and the other allowed words) | `workforce_employees` | Employee operational plane. Not `preparing`, `active`, or `ended` |
| `candidate_snapshot` | `workforce_employees` | The handoff that started one Employment. A later hire does not overwrite the only copy on the person as its canonical home |
| `hire_date` | `workforce_employees` | Employment. The start of this labour relationship. Not `workforce_employments.start_date` |
| `termination_date` | `workforce_employees` | Employment. The end of this labour relationship. Not `workforce_employments.end_date` |
| `company_id` | `workforce_employees` | Employment. The client of this hire. The directory reads `company_id` as the client and `own_company_id` as the employer. They are not the same column |
| `vacancy_id` | both rows | Employment. The vacancy this hire came from. The copy on a contract row is not a second vacancy |
| `recruiter_user_id` | `workforce_employees` | Employment. The recruiter of this hire |
| `handoff_at`, `handoff_by_user_id` | `workforce_employees` | Employment. The handoff that initiated this relationship. `meta.internal_hr_handoff_id` is that handoff's id |
| `start_date`, `end_date`, `expiry_date`, `signed_at`, `probation_end` | `workforce_employments` | That contract/terms record. A contract may begin and end inside one Employment. `probation_end` on the person row is the same kind of term, not an Employment state |
| `contract_type`, `employer_name`, `rate_model`, `schedule`, `conditions_text`, `latest_annex_ref` | `workforce_employments` | That contract/terms record. Already off the person row. This boundary does not move them |
| `WorkforceEmployment.lifecycle_status` | `workforce_employments` | Contract-document lifecycle, default `issued`. Words include `signed`, `active`, `expiring`, `renewed`, and `terminated`. Not `preparing`, `active`, or `ended` on the Employment |

The canonical Employment owns `employee_id`, the state `preparing | active | ended`, the client company, the start and the end of the relationship, the vacancy of the hire, the recruiter of the hire, and the initiating handoff. `own_company_id` stays the HR workspace company on the Employee context. Its contract/terms records own the contractual terms. Position, workplace, working time, and remuneration are such terms. They are not columns of `workforce_employees` today, and this boundary adds no column for them.

`meta` on `workforce_employees` mixes the handoff id with the HR pipeline. This boundary assigns `internal_hr_handoff_id` to the Employment and does not split the rest of the blob.

Tax, insurance, compliance, work eligibility, payroll, ZUS, document context, onboarding tasks, absences, leave, and lifecycle events stay employee-scoped satellites. This boundary does not re-home them. HR document policy stays untouched.

---

## Repository discovery

This reading is of the schema and of the writers and readers. It is not a count of live rows.

`workforce_employments` has no unique constraint on `employee_id`. `ix_workforce_employments_tenant_employee` is not unique. The model allows a history of rows for one employee.

`ensure_hr_profiles_bundle` inserts one row only when the employee has none. That row has `contract_type = unknown` and `meta.source = auto_bundle`. `create_employment` and `POST /employees/{id}/employments` always insert another row. A renewal can instead set `lifecycle_status` to `renewed` on the existing row. `latest_annex_ref` stays on that row.

`get_hr_bundle` returns every row, newest `created_at` first. The directory, document merge, and the operational profile take that newest row when they need one value. The operational profile also counts every row as `contracts_total` and lists each row. `is_active` on that list is `start_date` and `end_date` of the card. Contract-control tasks and the ledger are per card: `contract:{id}`, `contract_issued`, `contract_signed`, `contract_renewed`, `contract_terminated`, `contract_expiring`. The employee rail shows the rows as contracts. The journey marks the contract step done when the list is not empty.

`lifecycle_status` defaults to `issued`. The patch path also writes `signed`, `active`, `expiring`, `renewed`, and `terminated`. Those words are the contract document.

The card holds `contract_type`, `employer_name`, `rate_model`, `schedule`, `start_date`, `end_date`, `probation_end`, `signed_at`, `latest_annex_ref`, `expiry_date`, `next_action`, `conditions_text`, `vacancy_id`, and `meta`. It has no relationship state, no recruiter, and no handoff id. `employer_name` is a free string. It is not `company_id` and it is not `own_company_id`.

The relationship facts on `workforce_employees` are single-valued. `handoff_from_candidate` writes them when it inserts the employee: `own_company_id`, `company_id`, `vacancy_id`, `recruiter_user_id`, `hire_date`, `handoff_at`, `handoff_by_user_id`, and `candidate_snapshot`. A later accept updates `handoff_at`, `handoff_by_user_id`, and `candidate_snapshot` only when the status is `returned` or `returned_to_recruitment`. It does not insert a second relationship and it does not change `hire_date`. `PATCH` of the employee writes `termination_date` and `status`. It can stamp `candidate.extra.workforce_termination`. It does not end a contract card.

The directory calls `own_company_id` the employer and `company_id` the client. A displayed start date is the newest card `start_date`, otherwise `hire_date`. `probation_end` is stored on both rows. `meta.internal_hr_handoff_id` sits in the employee `meta` beside the HR pipeline.

The store already has many contract cards for one employee, and one set of relationship facts on that employee. It has no second labour relationship. Several cards are the contract history of that one hire.

---

## Employment persistence

This section defines the entity and the backfill. It adds no table and no migration. The next slice is Employment Persistence Schema. That slice writes the table, runs this backfill, and cuts readers over to the new owner. The HR Legal Eligibility Gate, the kwestionariusz, employment-terms editing, requirements, and the Ready to Start runtime wait until Employment exists.

### Creation

An accepted `internal_hr` handoff opens one new Employment in `preparing` on the Employee context. A repeat hire opens another Employment in `preparing` on the existing Employee context. The previous Employment stays as it was. The handoff does not create a person.

### Ownership

Employment owns `employee_id`, the state `preparing | active | ended`, the client company, the start, the end, the vacancy of the hire, the recruiter of the hire, the handoff provenance, and the candidate snapshot of that handoff.

`own_company_id` stays on the Employee context. It is the HR workspace company. `WorkforceEmployee.status` stays on the Employee context. After the backfill it does not move Employment.

`workforce_employments` stays the contract card. The cardinality is Employee 1:N Employment 1:N contract cards. Each card links to the Employment it belongs to. A new card, or a change of `lifecycle_status` on a card, does not create an Employment and does not end one. `lifecycle_status` is not mapped onto `preparing`, `active`, or `ended`.

`hire_date` is the start of the relationship. It is not `workforce_employments.start_date`. `termination_date` is the end of the relationship. It is not `workforce_employments.end_date`. `probation_end` is a term of the card.

### Lifecycle

The only edges are `preparing → active` and `active → ended`.

`preparing → active` happens only through the Ready to Start Gate. `active → ended` is the end of that relationship. No reverse edge exists.

### Backfill

Each existing `WorkforceEmployee` becomes one Employment. Every `workforce_employments` row of that employee attaches to that Employment, including the `auto_bundle` placeholder. The rows are not split across Employments and they are not deleted.

The backfill state is:

- `ended` when `termination_date` is set, or `status` is `terminated`, `returned`, or `returned_to_recruitment`
- `active` when `status` is `active`, `on_sick_leave`, `on_vacation`, `on_leave`, `suspended`, or `contract_ending`
- `preparing` otherwise, including `onboarding`

`hire_date` does not choose that state. A date on an employee who is still `onboarding` is the intended start. The Employment stays `preparing`. This reading of `status` is the backfill only.

The same migration copies the relationship facts onto Employment and then they cease to be owners on `workforce_employees`. The columns `hire_date`, `termination_date`, `company_id`, `vacancy_id`, `recruiter_user_id`, `handoff_at`, `handoff_by_user_id`, and `candidate_snapshot` are dropped in that migration after the copy. `meta.internal_hr_handoff_id` is removed from the employee `meta`. The rest of `meta` stays. A `vacancy_id` on a contract card stays on the card. When `probation_end` is set on the employee and the newest card has none, the value is copied onto that card and the employee column is dropped with the others. A second populated copy on the employee is forbidden. The history remains on the Employment and on the contract cards.

---

## Employee Record & Employment Lifecycle — Contract Gate

The handoff is a process and context transition over the same person identity. Creating `WorkforceEmployee` is the current runtime of opening the HR context and is not the canonical meaning of the handoff.

The repository discovery fixes the card. `workforce_employments` is already 1:N contract history per employee. It is not the labour relationship and it is not 1:1 with Employment. The backfill gives each existing employee one Employment, attaches those cards, and moves the relationship facts to that Employment in the same migration. That is the single owner. The structural gap closes when that migration runs. This file does not run it.

**Outcome:** **PASS**. The next slice is Employment Persistence Schema. This file writes no table.

Feat stays locked. Runtime is not authorized. The HR Legal Eligibility Gate is not this slice.
