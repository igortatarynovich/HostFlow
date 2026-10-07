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

`kwestionariusz osobowy` is a representation of that canonical employee data. It is not a second copy of the person. This contract names the representation and does not design the form. The HR surface that places those owners into groups is [HR Employee Record Projection](hr-employee-record-projection.md). That projection adds no fact.

Who already owns each person fact is [Employee Data ownership](#employee-data-ownership). That section adds no store.

### Employment terms

The facts of this relationship include the employer, the position or profession, the employment basis or type, the workplace, the start date, the working time, and the remuneration, plus any further term the relationship needs. This opening names those facts and adds no column.

Where each of those facts already lives is [Employment Terms discovery](#employment-terms-discovery). The agreed-terms model is [Employment Terms Contract Gate](#employment-terms-contract-gate). Neither section adds a column.

### Pre-employment requirements

Once the data and the terms the policy needs are present, policy forms the requirements for this Employment. Each requirement is `satisfied`, `waived`, or `blocking`. A requirement may depend on another requirement. Independent requirements may proceed together.

A later company policy may express a Polish sequence such as a medical examination, BHP, occupational-risk acknowledgements, an agreement, declarations, and company requirements. This contract does not canonize a Polish pre-employment document list. A draft agreement need not wait for a medical examination; that is an example of a dependency, not a required order.

What already exists, and the two axes of one Employment's requirements, are [Pre-employment Requirements discovery](#pre-employment-requirements-discovery) and [Pre-employment Requirements Contract Gate](#pre-employment-requirements-contract-gate). Neither section adds a column. Neither fixes a physical enum.

### Ready to Start Gate

This gate is the permission to move `preparing → active`. The four inputs, the aggregation, and the stale rule are [Ready to Start Gate Contract](#ready-to-start-gate-contract). This opening does not evaluate them and does not perform the transition.

A blocked input holds the Employment at `preparing`. It does not add an Employment state.

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

---

## Employee Data ownership

This section names the live owner of each person fact the HR process reads. It adds no table, no column, and no runtime module. It does not close a schema gate and it does not close a runtime gate. The sentences in this file that say no schema is written, and that no runtime module is authorized, stay in force.

The layer uses the Employee context already linked to the current `Employment(preparing)`. `kwestionariusz osobowy` is a view of the owners below. It is not a stored questionnaire.

### One owner

A person fact has one live owner. HR reads that owner. A missing fact, or a fact that must be brought up to date, is written on that owner. The address of the person is that one owner. An employee address and a kwestionariusz address are not opened beside it.

`Candidate` remains the temporary identity anchor. No Person table is authorized.

### Live person facts

| Fact | Live owner | Copies that are not the owner |
|---|---|---|
| Legal name | `candidates.first_name`, `candidates.last_name` (`recruitment.candidate.first_name`, `recruitment.candidate.last_name`) | `WorkforceEmployee.display_name` is the HR label. `CandidateHandoffSnapshot.payload` and `hr_employments.candidate_snapshot` are the snapshot already saved for the handoff |
| Latin name | `candidates.first_name_latin`, `candidates.last_name_latin` | the same snapshot |
| Phone, phone country code, email | columns `candidates.phone`, `candidates.phone_country_code`, `candidates.email` | `candidates.contacts` may repeat them. That JSON owns `preferred_messenger` |
| Birth date | `candidates.personal_data.birth_date` (`platform.identity.birth_date`) | the property setter also writes `extra.birth_date`. That extra key is the legacy mirror of the same write |
| Citizenship | `candidates.personal_data.citizenship` (`platform.identity.citizenship`) | `extra.citizenship`. `workforce_work_eligibility_profiles.citizenship` is a legalization projection. The legalization truth stays `legal_eligibility.v1` |
| Address, city, country, latin address | `candidates.personal_data` keys `address`, `city`, `country_code`, `city_latin`, `address_latin`. `platform.identity.address` is the address | the property setter also writes `extra`. The Employee row has no address column, and this section adds none |
| Languages | `candidates.languages` | |
| PESEL | `candidates.personal_data.pesel` | no PESEL column exists. Readers also look at `extra.pesel`, `employee.meta.pesel`, and the snapshot. Those paths are not a second PESEL. This section adds no column and does not move the copies |
| Residency status, current location, in Poland | `candidates.personal_data` under `recruitment.candidate.personal.residency_status`, `personal.current_location`, `personal.in_poland` | not an Employment term |

The number, issue date, and expiry of an identity document belong to that `documents` row (`number`, `issue_date`, `expire_date`, `meta`). Employee Data may refer to the document. It does not copy those values onto the Employee or into a questionnaire row.

`candidate_evidence` records which variant satisfies a recruitment requirement. It is not a person store. Evidence already held stays on the existing evidence model.

`workforce_hr_verified_fields.verified_value` records who confirmed a value and from which document. The confirmation is not the person.

`CandidateHandoffSnapshot.payload` is the snapshot already saved at handoff. `hr_employments.candidate_snapshot` holds that payload for the Employment. This layer does not make another copy of the person or of the evidence, and the snapshot does not become the live owner.

### Outside this layer

| Store | What it owns |
|---|---|
| `hr_employments` | `client_company_id`, `vacancy_id`, `started_on`, `ended_on`, the recruiter, and the handoff. `started_on` and `ended_on` stay empty in this layer. Substantive terms are [Employment Terms discovery](#employment-terms-discovery) |
| `workforce_employments` | the contract card: type, rate, schedule, card dates, `lifecycle_status` |
| `WorkforceEmployee` | the HR context: `candidate_id`, `own_company_id`, `display_name`, `status`, `notes`. `status` stays the other plane |
| `candidate_profiles`, `ep_entity_profiles` | which fields a card or an intake shows. They store no person value |
| `candidate_employments` | prior jobs captured at intake. A view may read them. This layer does not copy them, and they are not this Employment |
| `workforce_tax_profiles`, `workforce_insurance_profiles`, `workforce_zus_profiles`, `workforce_payroll_profiles`, `workforce_work_eligibility_profiles` | tax, insurance, ZUS, payroll, and work-eligibility process. This layer does not re-home them and does not read them as the person. Pay and the bank account wait with terms or payroll. ZUS registration stays a post-start obligation |
| Candidate stage, source, recruiter, vacancy, agreements, experience | Recruitment participation of that person |

Parents' names, place of birth, and a maiden name are not stored as canonical fields. This section does not take them from a Polish form and does not add a key for them. A later completeness rule that needs a missing person fact writes it once on `candidates.personal_data`.

### Gate question

The only question of this layer is: is the person-fact set sufficient to continue the HR process for this `Employment(preparing)`?

The reading uses the owners above. HR fills only a fact that is missing or that must be brought up to date, and writes it on its owner. An insufficient set leaves the Employment `preparing`. A sufficient set leaves the Employment `preparing`. It does not move the Employment to `active`. It is not the Ready to Start Gate. Employment terms, pre-employment requirements, and Ready to Start wait.

The order around `preparing` stays: HR Legal Eligibility PASS, then Employee Data sufficient, then Employment terms, then pre-employment requirements, then the Ready to Start Gate, then `active`.

A later kwestionariusz osobowy document may be generated from these owners. The PDF, a template, and Polish document policy are not the source of truth.

This section writes no schema and authorizes no runtime module. `backend/app/reference/employee_data.py` is not created. Feat stays locked. HostFlow v1 is not release-ready.

---

## Employment Terms discovery

This section reads the columns that already exist. It adds no table, no column, and no runtime module. It does not close a schema gate and it does not close a runtime gate. It does not list which terms a Polish `umowa` requires, and it does not name a document to generate.

Three layers stay distinct.

A vacancy holds the offer: title, location, `employment_type`, and a salary range. Those values may default a later agreement. They are not the agreed terms of one Employment.

The agreed terms belong to that Employment. The relationship context already has columns on `hr_employments`. The substantive terms have no second table. Where a substantive term already has one column, that column is the current store. This section does not open a parallel salary, FTE, workplace, or contract-type field.

`workforce_employments` is the contract card. It represents an agreement document and its `lifecycle_status`. It is not the Employment. One Employment has many cards.

### Relationship context

| Fact | Canonical owner | What else is stored |
|---|---|---|
| Employer / workspace | `workforce_employees.own_company_id`, inside the tenant | `vacancies.own_company_id` is the vacancy's workspace. `workforce_employments.employer_name` is a free label on the card. Neither is a second employer |
| Client | `hr_employments.client_company_id` | There is no `hr_employments.company_id`. `hr.employee.company_id` reads `client_company_id`. `vacancies.company_id` is the client of the offer |
| Vacancy of this hire | `hr_employments.vacancy_id` | `workforce_employments.vacancy_id` is a copy on the card. It is not a second vacancy |
| Start of the relationship | `hr_employments.started_on` | `workforce_employments.start_date` is the start printed on that card. The two dates are different facts |
| End of the relationship | `hr_employments.ended_on` | `workforce_employments.end_date` and `expiry_date` are dates of that card |
| Recruiter and handoff | `hr_employments.recruiter_user_id`, `handoff_at`, `handoff_by_user_id`, `handoff_id`, `candidate_snapshot` | The snapshot remains the payload already saved at handoff |

`started_on` and `ended_on` stay empty while this layer only names them. Writing those dates is not this slice.

### Substantive terms

| Fact | Where a value lives today | Canonical reading |
|---|---|---|
| Position of this Employment | No position column on `hr_employments` or on `workforce_employments`. `vacancies.title` is the offer title. `position_category` appears in candidate extra and on `workforce_work_eligibility_profiles`. `conditions_text` is free text on the card | The agreed position belongs to this Employment. The offer title may default it. This section adds no position column |
| Contract basis | `workforce_employments.contract_type`, default `unknown`. `vacancies.employment_type` is `full_time`, `part_time`, or `b2b`. `workforce_work_eligibility_profiles.contract_type` and `workforce_zus_profiles.employment_basis` are other strings | The card's `contract_type` is the current store of the agreed basis. The vacancy enum is the offer shape. The eligibility and ZUS strings are process copies. This section adds no second contract-type column |
| Working time | No FTE column. `vacancies.employment_type` is the coarse offer. `workforce_employments.schedule` is an unstructured JSON | Agreed working time belongs to this Employment. The current blob, when present, is `schedule` on the card. This section adds no FTE column and does not define the JSON |
| Workplace | No workplace column. `vacancies.location` is the offer location | The agreed workplace belongs to this Employment. The vacancy location may default it. This section adds no workplace column |
| Remuneration, currency, period | `vacancies.salary_from`, `salary_to`, and `currency` are offer strings. `workforce_employments.rate_model` is an unstructured JSON with no amount, currency, or period keys. `workforce_payroll_profiles.base_rate`, `currency`, and `pay_type` are the payroll satellite. `sales_order_lines.unit_rate` is the client commercial rate | Agreed pay belongs to this Employment. The current HR store is `rate_model` on the card. The vacancy range is the offer. Payroll is a later copy. The sales rate is not the worker's pay. This section adds no salary column and does not define `rate_model` |
| Fixed or indefinite term | No such flag. `ended_on`, `end_date`, and `expiry_date` are dates | An empty end date is not defined as indefinite. This section adds no flag |
| Probation | `workforce_employments.probation_end` only. `workforce_employees` has no `probation_end` column. `hr.employee.probation_end` reads the card | Probation is a term of that contract card. It is not `started_on` and it is not an Employment state. This section does not copy it onto `hr_employments` |

`lifecycle_status`, `signed_at`, `latest_annex_ref`, `next_action`, and `conditions_text` stay document facts of the card.

### Gate question

The only question of this layer is: are the terms of this Employment defined enough to continue to pre-employment requirements?

A complete reading and an incomplete reading both leave `hr_employments.state` at `preparing`. Neither moves the Employment to `active`. Neither is the Ready to Start Gate. Pre-employment requirements stay the next layer.

This section writes no schema and authorizes no runtime module. `backend/app/reference/employment_terms.py` is not created. Feat stays locked. HostFlow v1 is not release-ready.

---

## Employment Terms Contract Gate

**Machine id:** `employment_terms.v1` — named here. No runtime module.  
**Outcome:** **PASS**. The model below is the agreed terms of one Employment. This section adds no table and no column. It does not choose a store. It does not close a schema gate and it does not close a runtime gate.

The discovery found the bytes that exist today. None of them is a snapshot of the agreement. This gate defines that snapshot and the mapping. A later schema slice chooses whether the snapshot is columns on `hr_employments`, a separate terms structure, or another store.

### Agreed terms

The agreed terms belong to one Employment. They are the snapshot of what was agreed for that Employment. They are not a live reading of the vacancy. They are not the contract card.

| Term | Semantics | Mapping of what exists today |
|---|---|---|
| Position | The position agreed for this Employment | `vacancies.title` may be copied once as the default. After the snapshot exists, the vacancy title is not the position |
| Contract basis | The canonical type of this relationship. The vocabulary is not `vacancies.employment_type` | `full_time`, `part_time`, and `b2b` stay the offer shape. `workforce_employments.contract_type`, `workforce_work_eligibility_profiles.contract_type`, and `workforce_zus_profiles.employment_basis` are other strings. This contract does not list `umowa` types |
| Work time | A structured magnitude and unit | `workforce_employments.schedule` is an unstructured blob. It is not this pair. This contract does not close the unit vocabulary and does not parse the blob |
| Workplace | The place of work agreed for this Employment | `vacancies.location` may be copied once as the default |
| Compensation | Amount, currency, and unit or period | `vacancies.salary_from`, `salary_to`, and `currency` are an offer range. `workforce_employments.rate_model` has no amount, currency, or period keys. `workforce_payroll_profiles.base_rate` is payroll. `sales_order_lines.unit_rate` is the client rate |
| Duration | `fixed` or `indefinite` | No flag exists today. An empty `hr_employments.ended_on` does not mean `indefinite`. An empty card `end_date` does not mean `indefinite` |
| Fixed-term end | The agreed end date of a fixed term. Present when duration is `fixed`. Absent when duration is `indefinite` | `hr_employments.ended_on` is the end of the relationship. `workforce_employments.end_date` and `expiry_date` are dates of the card |
| Probation | A term of this Employment. An agreed end date, or an explicit none | `workforce_employments.probation_end` may show that date on a card. The card date is not the source of truth |

### Snapshot

A default is copied at the moment of agreement, and only then. Position may start from `vacancies.title`. Workplace may start from `vacancies.location`. The salary range does not become the compensation amount. `employment_type` does not become the contract basis. `schedule` does not become work time. `rate_model` does not become compensation.

After the snapshot exists, a change to `vacancies.title`, `vacancies.location`, `vacancies.salary_from`, `vacancies.salary_to`, `vacancies.currency`, or `vacancies.employment_type` leaves the agreed terms as they were.

A contract card may be filled from the snapshot when the document is created. A later edit of that card, including `contract_type`, `rate_model`, `schedule`, `probation_end`, `start_date`, `end_date`, and `conditions_text`, does not write the agreed terms.

### Complete

Employment Terms complete means this Employment holds a sufficient structured set of agreed terms, independent of the current vacancy and independent of the contract document.

The set is sufficient when position, contract basis, work time, workplace, compensation, and duration are present, probation is an agreed end date or an explicit none, and the fixed-term end is present only when duration is `fixed`.

An incomplete set leaves `hr_employments.state` at `preparing`. A complete set leaves `hr_employments.state` at `preparing`. Completeness is the permission to continue to pre-employment requirements. It does not open that layer. It does not move the Employment to `active`. It is not the Ready to Start Gate.

### Store

No column and no JSON in the current model is this snapshot. Employment Terms Schema is the indicated next slice. It will choose the store. This section does not open that slice and does not write it.

This section writes no schema and authorizes no runtime module. `backend/app/reference/employment_terms.py` is not created. Feat stays locked. HostFlow v1 is not release-ready.

---

## Employment Terms Schema

The store is `hr_employment_terms`. One row is one `employment_terms.v1` snapshot and it belongs to one `hr_employments` row. `hr_employments` keeps the identity and the lifecycle of the relationship. At most one row for an Employment has `is_current`. A later row may record an earlier snapshot with `is_current` false. This section writes that table. It does not authorize a runtime module.

The row holds position, contract basis, work-time value and unit, workplace, compensation amount, currency, and unit or period, duration, the conditional fixed-term end, and probation. Duration is `fixed` or `indefinite`. A fixed-term end is stored when duration is `fixed` and is absent when duration is `indefinite`. That absence is the duration value. It is not read from `hr_employments.ended_on`.

Probation status is `dated` with an end date, `none` with no end date, or `undetermined` with no end date. `none` is an agreed absence. `undetermined` is not yet decided. An Employment with no `hr_employment_terms` row is Terms incomplete. This migration copies nothing from a vacancy and nothing from a contract card.

`default_vacancy_id` may record which vacancy supplied a default. It is not a foreign key. The agreed columns are not read from that vacancy.

`workforce_employments` is not this table and gains no term column. This slice has no writer from a contract card, a vacancy, a payroll profile, or from `hr_employments.state` into the snapshot.

The next slice is Employment Terms Runtime: one-time defaults from the vacancy, an operator confirmation or change, then the snapshot, then Terms complete. That runtime is not this slice. A complete set and an incomplete set both leave `hr_employments.state` at `preparing`.

Feat stays locked. HostFlow v1 is not release-ready. Pre-employment requirements stay closed.

---

## Employment Terms Runtime

`is_current` is the latest confirmed agreement. It is not the latest edit. An unresolved operator input stays on the proposal. It is not a row in `hr_employment_terms`, and it does not clear the current snapshot.

`propose_employment_terms_defaults` reads `vacancies.title` into position and `vacancies.location` into workplace, once. `default_vacancy_id` records that vacancy as provenance. `salary_from` and `salary_to` stay off the proposal. `employment_type` stays off the proposal. The proposal is not a live binding.

`confirm_employment_terms` writes a new current row only when the confirmation resolves position, contract basis, work time, workplace, compensation, duration, the fixed-term end, and probation as `none` or `dated`. `probation_status = undetermined` is refused. A refusal writes nothing. When a current row already exists, that row becomes `is_current` false and keeps its values. The new row is current.

`evaluate_employment_terms` reads that current row. No current row is incomplete. A row that is not current is incomplete. `undetermined` probation is incomplete. Vacancy, the contract card, and payroll are not inputs. The result does not write `hr_employments.state`.

Confirmation does not move `hr_employments.state`. It does not insert `workforce_employments`. It does not open pre-employment requirements or Ready to Start.

The next slice is Pre-employment Requirements. Feat stays locked. HostFlow v1 is not release-ready.

---

## Pre-employment Requirements discovery

This section reads the requirement, checklist, compliance, and task mechanisms that already exist. It adds no table, no column, no boolean on Employee or Employment, and no runtime module. It does not close a schema gate and it does not close a runtime gate. It does not fix a physical enum. It does not open a Polish pre-employment sequence.

Three readings stay distinct. A requirement definition is policy. A requirement instance belongs to one Employment. A resolution points at evidence or records a waiver. None of the stores below is all three for one `hr_employments` row.

| Mechanism | What it already is | What it is not |
|---|---|---|
| Requirement Rules policy and `r5_required_set` | The system required set for a candidate. Policy supplies the definition. `dependency_rules` can exclude, activate, or satisfy codes in that candidate graph. Applicability is `RequirementApplicability`: `applicable`, `not_applicable`, `unresolved` | The pre-employment set of one Employment. This layer does not write `r5_required_set` |
| `RequirementEvaluationStatus` | A computed candidate-stage reading: `fulfilled`, `missing`, `pending_review`, `invalid`, `expired`, `not_applicable`, `not_required_yet`, `not_selected`, `process_pending`, `waived`, `unresolved`. `not_applicable` also sits on the applicability enum | The resolution enum of an Employment requirement. `pending_review` is not `blocking`. This section does not adopt the enum |
| `requirement_type_definitions` | A tenant catalog of recruitment codes such as `id_evidence`, `code95_evidence`, and `right_to_work_basis`, with `satisfaction_rules` | An instance hanging on `hr_employments` |
| `tenant_requirement_overrides` | A policy edit: `relax`, `add`, or `severity`, level `blocking` or `warning`, with reason and `approved_by_user_id` | A waiver of one Employment's requirement. `blocking` here is severity of a rule |
| `candidate_evidence` and `candidate_evidence_documents` | Recruitment's chosen variant for one `candidate_id` and one `requirement_code`. Status is `CandidateEvidenceStatus`: `draft`, `selected`, `pending_review`, `approved`, `rejected`, `superseded`. The document link is `document_id` | An Employment instance. The table has no `employment_id`. `approved` is not this layer's `satisfied`. A later Employment does not inherit the row |
| Legal Eligibility and Work Authorization | `legal_eligibility.v1` and submission requirements with provenance `work_authorization_submission`. `waive_requirement` lifts one requirement for one candidate and one process, with actor, time, and reason, and does not rewrite the policy. `override_readiness` leaves the blocker in place | HR Legal Eligibility Gate, and not this set. The gate row is `hr_legal_eligibility_gate_decisions`, bound to `employment_id`, outcome `pass`, `fail`, or `blocked` |
| Hub `outstanding_asks` | A document request: a required type for an entity through Document Link | A pre-employment requirement row. This layer does not mint a second request table |
| `workforce_onboarding_tasks` | An operational checklist on `employee_id`: `title`, `status` default `open`, `due_at`, `completed_at` | A definition, an evidence link, a waiver, or an Employment instance. Fee tasks from work-eligibility automation stay in that process |
| `workforce_hr_document_control_tasks` | One open control row per `employee_id` and `document_code` | A requirement instance |
| `workforce_compliance_states` | One rollup per employee: counts and `cannot_work` | A set of requirements |
| HR profiles | `workforce_work_eligibility_profiles`, tax, insurance, ZUS, and payroll. Each hangs on `employee_id` | Requirement rows. Work eligibility remains the legalization projection |
| `automation_rules` | A tenant trigger with conditions and actions | A requirement graph |

No current table is a requirement instance of one Employment. `candidate_evidence` has no `employment_id`. Onboarding tasks, document-control tasks, compliance, and the HR profiles hang on the employee. The legal-eligibility gate decision is the upstream checkpoint, not a member of this set.

The evaluator already separates applicability from status, and then stores `not_applicable` on both. That split is evidence that one status word cannot carry both axes. This section records the split and does not choose the stored spellings.

### Gate question

For this `Employment(preparing)`, is the applicable set of pre-employment requirements defined, and is every requirement that blocks Ready to Start resolved?

A yes and a no both leave `hr_employments.state` at `preparing`. Neither moves the Employment to `active`. A yes is the entrance to the Ready to Start Gate. It is not that gate.

This section writes no schema and authorizes no runtime module. `backend/app/reference/pre_employment_requirements.py` is not created. Feat stays locked. HostFlow v1 is not release-ready.

---

## Pre-employment Requirements Contract Gate

**Machine id:** `pre_employment_requirements.v1` — named here. No runtime module.  
**Outcome:** **PASS**. The model below is the pre-employment requirements of one Employment. This section adds no table, no column, and no boolean. It does not fix a physical enum. It does not choose a store. It does not close a schema gate and it does not close a runtime gate. It does not open a Polish pre-employment sequence.

HR Legal Eligibility PASS, Employee Data complete, and Employment Terms complete stay upstream gates. They are the permission to begin this layer. They are not three requirements inside it.

### Three readings

| Reading | Semantics |
|---|---|
| Definition | Policy or configuration names the requirement. The code is not a column of Employee and not a column of Employment |
| Instance | One applicable or not-applicable occurrence for one Employment. A later Employment gets its own instances |
| Resolution | How that applicable instance stands: a link to existing evidence or a document, a waiver, a blocking finding, or not yet resolved |

### Axes

Applicability and resolution stay two axes.

An instance is applicable or not applicable for this Employment from policy and from this Employment's context. Not applicable is outside the set that Ready to Start reads. It is not a resolution, and it is not `blocking`.

Resolution of an applicable instance uses the business words already named for this lifecycle. `satisfied` is a link to existing evidence or an existing document. The file is not copied. `waived` is an explicit decision with actor, time, and reason. It does not rewrite the definition. `blocking` is a found problem that holds Ready to Start. Not yet resolved means none of those three has been recorded. Not yet resolved is not `blocking`, and `blocking` is not a synonym of pending.

`RequirementEvaluationStatus`, `RequirementApplicability`, and `CandidateEvidenceStatus` stay the enums of their own mechanisms. This contract does not adopt them as the stored values of `pre_employment_requirements.v1`.

### Answers

| Question | Required semantics |
|---|---|
| What does a requirement belong to? | One Employment. The instance is not a flag on the Employee and not a flag on `hr_employments` |
| Where does it come from? | Policy or configuration. Not a hard-coded column |
| Which words are already fixed? | `satisfied`, `waived`, and `blocking`, read on the resolution axis. Applicability is the other axis |
| What is evidence? | A reference to existing evidence or an existing document. Not a copy |
| What is a waiver? | An explicit decision for this instance, with actor, time, and reason. `override_readiness` is not this waiver. A `tenant_requirement_overrides` row is not this waiver |
| May one requirement depend on another? | Yes, on another requirement of this same Employment. Independent requirements may proceed together. `dependency_rules` on the candidate policy graph are not copied here |
| May a requirement be not applicable? | Yes. Context of this Employment can make a defined requirement not applicable. Not applicable does not block Ready to Start |
| What does a repeat hire get? | The new Employment gets its own instances |
| What does Employee history do? | It does not mark a new Employment's instance `satisfied`. A document already held may be linked later, as a resolution of this instance |
| What happens to Employment state? | Every applicability and every resolution leaves `hr_employments.state` at `preparing` |

### Gate

The gate question is the discovery question. Every applicable instance must be `satisfied` or `waived` before that entrance is open. An applicable `unresolved` instance keeps the entrance closed. An applicable `blocking` instance keeps it closed because a problem was found. A `not_applicable` instance stores no resolution and stays outside the check.

A yes does not move the Employment to `active`. It is the entrance to the Ready to Start Gate. Ready to Start remains a separate gate.

### Store

No column and no JSON in the current model is this instance. `candidate_evidence` has no `employment_id`. A later schema slice chooses the store. This section does not open that slice, does not write it, and does not fix the physical enum.

This section writes no schema and authorizes no runtime module. `backend/app/reference/pre_employment_requirements.py` is not created. Feat stays locked. HostFlow v1 is not release-ready.

---

## Pre-employment Requirements Schema

The store is `hr_employment_requirements`. One row is one `pre_employment_requirements.v1` instance and it belongs to one `hr_employments` row. `definition_key` is the stable policy identity. `policy_id` and `policy_version` record provenance. Neither is a foreign key. Uniqueness is (`employment_id`, `definition_key`). The table has no `employee_id`. Two Employments of one person can hold the same `definition_key` as two rows.

Applicability and resolution are separate columns. Applicability is `applicable` or `not_applicable`. `applicability_basis` may record why. Resolution is stored only for an applicable row, and then it is `unresolved`, `satisfied`, `waived`, or `blocking`. A `not_applicable` row has no resolution. `RequirementEvaluationStatus` is not this column.

`satisfied` stores `satisfaction_evidence_id` or `satisfaction_document_id`, or both. Those columns are foreign keys to `candidate_evidence` and `documents`. They are references. The row does not copy the evidence. `waived` stores `waiver_actor_id`, `waiver_at`, and `waiver_reason`. `blocking` stores `blocking_reason`, the reason and context of the finding. `unresolved` stores none of those payloads. A payload that belongs to another resolution is absent.

Ready to Start, when a later slice evaluates it, admits an applicable row only when resolution is `satisfied` or `waived`. `unresolved` refuses that entrance because the requirement is still open. `blocking` refuses it because a problem was found. This section does not evaluate that entrance.

This migration inserts nothing. It does not generate instances from policy, does not copy `candidate_evidence`, does not list a Polish set, does not write `hr_employments.state`, and does not create `workforce_onboarding_tasks` or `workforce_employments`.

The next slice is Pre-employment Requirements Runtime: materialize the applicable set from policy, resolve an instance through existing evidence or a document or a waiver, tell `unresolved` from `blocking`, and compute completeness of the set. That runtime is not this slice. The Ready to Start Gate Contract is not this slice. A stored row leaves `hr_employments.state` at `preparing`.

Feat stays locked. HostFlow v1 is not release-ready.

---

## Pre-employment Requirements Runtime

The materialized set of one Employment is stable. `materialize_pre_employment_requirements` writes it once, from the policy reading supplied for that `Employment(preparing)`. Each definition carries `definition_key`, `policy_id`, `policy_version`, applicability, and `applicability_basis`. Those three provenance fields are the policy and the context of the applicability decision. An applicable row starts at `unresolved`. A `not_applicable` row stores no resolution. An empty reading does not define the set and writes nothing.

A later call for the same Employment returns the stored rows and does not write. A later policy does not add a definition, does not delete one, and does not rewrite applicability, `policy_id`, `policy_version`, `applicability_basis`, or resolution. The stored provenance remains the way to see which policy and context decided the row. Reconciliation of a changed policy is not this runtime. Another Employment of the same person receives its own rows. Employee history does not write them.

`satisfy_pre_employment_requirement` links an applicable `unresolved` or `blocking` row to an existing `candidate_evidence` row, an existing `documents` row, or both. The link is the id the caller names. The runtime does not search the Employee for a similar document and does not copy the evidence. `waive_pre_employment_requirement` records actor, time, and a non-empty reason on an applicable `unresolved` or `blocking` row. `block_pre_employment_requirement` records the reason of a found problem on an applicable `unresolved` row. `unresolved` is not that finding. A `not_applicable` row accepts none of these acts. A `satisfied` or `waived` row is not rewritten. A second waive with a different reason is refused.

`evaluate_pre_employment_requirements` is true only when that set is defined and every applicable row is `satisfied` or `waived`. `not_applicable` stays outside the check. `unresolved` and `blocking` are both false, and the row keeps which of the two it is. The result does not write `hr_employments.state`. It does not insert `workforce_onboarding_tasks` or `workforce_employments`. It does not list a Polish set. It does not open the Ready to Start Gate.

A true result is one input of that gate. This runtime does not aggregate the other inputs and does not move the Employment to `active`. An Employment that is not `preparing` is not materialized and is not resolved. Feat stays locked. HostFlow v1 is not release-ready.

---

## Ready to Start Gate Contract

**Machine id:** `ready_to_start.v1` — named here. No runtime module.  
**Outcome:** **PASS**. The model below is the permission for one `Employment(preparing)` to move to `active`. This section adds no table, no column, and no boolean. It does not choose a store. It does not perform the transition. It does not close a schema gate and it does not close a runtime gate. It does not open a Polish pre-employment sequence.

This gate aggregates. It does not re-decide legal eligibility, person facts, agreed terms, or requirement resolution. Each input is the canonical reading of that layer. A second checklist of the same facts is not this gate.

### Four inputs

| Input | PASS | What this gate reads | What a miss is |
|---|---|---|---|
| HR Legal Eligibility | A recorded decision for this Employment has outcome `pass`, and `decision_is_current` still matches the chain and this Employment context | That decision and its fingerprint. Not a new derivation of `citizenship_class`, `stay_basis`, `work_authorization_basis`, or `valid_for_this_employment` | No decision, a legal `fail`, a legal `blocked`, or a stale fingerprint |
| Employee Data | The person-fact set of Employee Data ownership is complete for this Employment | That sufficient-set answer. Not a second list of person facts, and not a write onto an owner | The set is not complete |
| Employment Terms | The current `employment_terms.v1` row exists and `evaluate_employment_terms` on it is complete | That current row only. Not the vacancy, and not the contract card | No current row, or the current row is incomplete |
| Pre-employment Requirements | The set is materialized and `evaluate_pre_employment_requirements` is true | That boolean. Not a new resolution of any row | The set is not defined, or an applicable row is `unresolved` or `blocking` |

`not_applicable` stays outside the requirements reading, as that evaluator already defines. HR Legal Eligibility PASS, Employee Data complete, and Employment Terms complete are not rows of the requirements set. This gate still reads them as their own inputs.

### Outcome

The outcome of this gate is `pass` or `blocked`.

`pass` means all four inputs pass for this `Employment(preparing)` at the time of the decision. `blocked` means at least one input does not. Missing data, a stale legal decision, a legal `fail`, no current terms, an incomplete current snapshot, an unmaterialized requirements set, an applicable `unresolved` row, and an applicable `blocking` row are blocked reasons. They are why the Employment cannot start now. They are not Employment states. A legal `fail` stays the outcome of the legal gate. On this gate it is a blocked reason.

One decision may carry more than one blocked reason. The gate does not stop at the first.

An Employment that is not `preparing` is outside the question. The outcome is not `pass`, and the state is not changed.

### Audit

A decision records `employment_id`, the outcome, the actor, the time, the result of each of the four inputs, and the blocked reasons. The legal result includes the fingerprint that `decision_is_current` compares. This section does not decide whether that record is its own table. A later slice chooses the store. This section does not open that slice, does not write it, and does not fix a physical enum.

### Stale

A recorded `pass` is permission only while the four readings still match the readings captured on that decision. A later change of the legal chain or of this Employment context, of Employee Data completeness, of the current terms snapshot, or of requirements readiness makes that `pass` stale.

The move `preparing → active` is allowed only when a `pass` is current against those upstream readings at the moment of the move. A stale `pass` is not that permission. The move itself is not this slice.

### Boundary

The question is: may this `Employment(preparing)` move to `active`?

A `pass` answers yes and leaves `hr_employments.state` at `preparing`. A `blocked` answers no and leaves it at `preparing`. Neither inserts `workforce_employments` or `workforce_onboarding_tasks`. Neither canonizes a Polish pre-employment document list.

The next slice is Ready to Start persistence and runtime together with Activation Runtime. That slice stores the decision, re-reads the four evaluators at activation, and is the only writer of `preparing → active`. It is not this slice. Migrations onto a shared database, and a manual path from handoff to `active`, wait until that slice exists.

This section writes no schema and authorizes no runtime module. `backend/app/reference/ready_to_start.py` is not created. Feat stays locked. HostFlow v1 is not release-ready.

---

## Ready to Start Persistence and Activation

The store is `hr_ready_to_start_decisions`. One row is one `ready_to_start.v1` decision for one `hr_employments` row. Rows are appended. A later decision does not update an earlier row. There is no unique current row. The latest row is the one with the latest `decided_at`.

The row stores `employment_id`, the outcome `pass` or `blocked`, the actor, the time, the result of each of the four inputs, the blocked reasons, and the version of each input. The legal version is `legal_decision_id` and `legal_fingerprint`. Employee Data stores the fingerprint from `read_employee_data_set`. Terms store `terms_id` and a fingerprint of that current snapshot. Requirements store a fingerprint of the materialized rows. `read_employee_data_set` returns the ownership answer and that fingerprint. It does not choose which person facts are required.

`record_ready_to_start` calls `decision_is_current`, `read_employee_data_set`, `evaluate_employment_terms`, and `evaluate_pre_employment_requirements`. It does not derive the legal chain, does not list person facts, does not judge a term field, and does not resolve a requirement. A `pass` is written only when all four readings pass. Any miss is `blocked`, including a legal `fail`, and the reasons are stored. The call does not write `hr_employments.state`.

`ready_to_start_is_current` is true only for a stored `pass` whose four results and four fingerprints still match a fresh call of those same readings.

`activate_employment` is the only writer of `preparing → active`. It locks the Employment, reads the latest decision, calls the four readings again, and updates the state only when that decision is a current `pass`. The check and the update are one transaction: this function does not commit between them. A missing decision, a `blocked` decision, and a stale `pass` leave the state at `preparing`. Activation does not record a replacement decision and does not fill a legal decision, a person fact, a terms snapshot, or a requirement. It does not insert `workforce_employments` or `workforce_onboarding_tasks`.

An Employment that is not `preparing` is not recorded and is not activated. Feat stays locked. HostFlow v1 is not release-ready. The manual path from handoff to `active` is the next integration, not this slice.
