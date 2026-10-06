# HR operator flow — driver on one Employment

**Status:** operator reading. The employee page `#hr-verification` is the HR Driver Operator Surface. No preset row.  
**Date:** 2026-10-05  
**Parents:** [Legal Eligibility](../architecture/legal-eligibility-contract.md) (`legal_eligibility.v1`) · [Employee Record & Employment Lifecycle](../architecture/employee-record-employment-lifecycle-contract.md) · [Work Authorization Procedure](../architecture/work-authorization-procedure-contract.md) (`work_authorization_procedure.v1`)

> The card answers facts. A document is the evidence of a fact. A checklist of files is not the spine of the card.  
> The driver rows below are one reading of applicability. They are not a list for every employee, and they are not a policy preset.  
> `#hr-verification` is the HR Driver Operator Surface for one `Employment(preparing)`. HostFlow v1 is not release-ready.

---

## What the operator is deciding

For one person and one `Employment(preparing)`, HR walks facts in this order. A later fact may be looked at while an earlier gate is still open. Opening a later fact does not pass the earlier gate.

```text
Identity
→ Legal stay
→ Work eligibility for this Employment
→ Professional readiness
→ Employment terms
→ Formality actions
→ Ready to Start
→ Active
```

Which professional facts and which formality actions apply comes from the country, the profession, the citizenship class, the type of this Employment, and the situation of this case. A fact that policy marks not applicable is not shown as missing.

## Identity

The first facts are who the person is.

| Fact | Owner already named |
|---|---|
| Legal name | `candidates.first_name`, `candidates.last_name` |
| Birth date | `candidates.personal_data.birth_date` |
| Citizenship | `candidates.personal_data.citizenship` |

`WorkforceEmployee.display_name` stays the HR label. These three facts are the inputs the legal chain reads. They are not a Legal Eligibility outcome. A missing citizenship stops the chain. It does not become `third_country`.

The number, issue date, and expiry of the passport stay on the `documents` row that evidences identity. The person row does not copy them.

## Legal stay

Legal stay is the second step of `legal_eligibility.v1`: `citizenship_class → stay_basis`.

The operator reads the basis, the document that evidences it, that document's number, and the date it is valid until. The number and the date stay on the document. The chain stores the basis, not a second copy of the card.

`none` means there is no stay basis yet. It is not a refusal. A work authorization does not replace a stay basis. `pl` and `eu_eea_ch` on ordinary employment in Poland have stay `not_required`.

## Work eligibility for this Employment

Work eligibility is the rest of the same chain: `work_authorization_basis → valid_for_this_employment`.

The operator reads the basis of the right to work, the permit or the exemption that evidences it, the employer and the profession or occupation code named on that authorization, the date it is valid until, and whether those conditions are this Employment.

`valid_for_this_employment` is `yes`, `no`, or `operator_verification`. When a separate authorization is required and no later rule has matched it to this Employment, the step stays `operator_verification`. The chain does not take `kod zawodu` as an input. Driving licence, Code 95, and the profession preset are not this step.

The HR Legal Eligibility Gate is PASS only when the chain is determined and `valid_for_this_employment` holds for this Employment. A stay that is known, with work still unmatched, leaves the gate blocked and the Employment `preparing`. HR does not invent the chain.

## Professional readiness

After identity and the legal chain are readable, HR confirms the professional facts this Employment needs. Each fact is a requirement instance. The document is the evidence linked to that instance. Confirming the fact is `satisfied`. A found problem is `blocking`. Not yet looked at is `unresolved`, and `unresolved` is not `blocking`. Policy can mark the instance `not_applicable`.

One document may satisfy more than one fact. A driving licence that carries Code 95 satisfies the licence fact and the Code 95 fact. A licence without Code 95 satisfies only the licence. Code 95 then stays its own unresolved fact when policy requires it. The same rule is already stated for evidence in Legal Eligibility. This file does not add a driver preset and does not encode a Code 95 statute.

For a driver the operator expects these facts, in this order, each only when applicable:

| Fact | What is confirmed | Evidence the operator looks at |
|---|---|---|
| Passport | Identity document number, issuing country, expiry | Passport |
| Driving licence | Number, country, categories, issue, expiry, whether Code 95 is printed on it | Driving licence |
| Code 95 | Present and in date, or not applicable because the licence already carries it | Qualification card, or the same licence |
| Tachograph card | Number and expiry | Tachograph card |
| Medical | Result and validity | Medical certificate |
| Psychological | Result and validity | Psychological tests |
| Occupational medicine | Fitness for this work, and validity | Occupational medicine (`medycyna pracy`) |

A Driver CE profession layer may name a CE licence, Code 95, and a tachograph card. Medical, psychological, and occupational medicine are further facts of this reading. None of these rows is written here as a `requirement_type_definitions` code or as an `hr_employment_requirements` seed.

## Employment terms

The agreed terms of this Employment are the current `employment_terms.v1` snapshot. The operator agrees them with the person. A vacancy may supply a one-time default. It is not the agreement.

The snapshot holds position, contract basis, structured work time, work system, workplace, compensation (amount, currency, period), duration (`fixed` or `indefinite`), the fixed-term end when duration is `fixed`, probation (`dated` or `none`), and the intended start date.

The intended start date is the plan. `hr_employments.started_on` is the day the Employment actually starts. Confirming or reconfirming the plan does not write `started_on`. If the authorization arrives later, HR reconfirms the plan and the Employment stays `preparing`.

Terms can be confirmed while Legal Eligibility is still blocked. Confirmation still does not move the Employment to `active`.

## Two branches

The walk is not one line for every case. The branch is whether a work authorization that matches this Employment already exists.

**Authorization already matches.** Stay is determined, `valid_for_this_employment` is `yes`, and the HR Legal Eligibility Gate can PASS. Professional facts are confirmed. Terms are confirmed. Formality actions that apply to this Employment come next. Ready to Start still waits for its four readings.

**Authorization is not yet obtained.** Stay may already be determined. `work_authorization_basis` is `separate_required` or the chain is on an operator hold, and `valid_for_this_employment` is not `yes`. The gate stays blocked. HR still agrees the terms, because the later submission needs the start, the work time, and the compensation. When the procedure cannot be ordered until the person is registered with ZUS, ZUS registration is the next action, then the [Work Authorization Procedure](../architecture/work-authorization-procedure-contract.md) for this country, procedure type, and occupation code. A permit that then matches this Employment is what lets the legal chain reach `yes`. Only then can the HR Legal Eligibility Gate PASS.

Lawful stay alone does not select the work basis, and it does not pass the gate.

## Formality actions

ZUS registration and an A1 are actions. They are not person facts, and they are not sections that stay open on the card for the life of the Employee. `workforce_zus_profiles` remains the ZUS process store. This reading does not re-home it.

An action is shown when it is the next one whose preconditions hold. The card states that one action, the readings it needed, and the start date the operator will use. Completing it closes it. The next applicable action replaces it.

A1 is applicable when this Employment needs it. It is not a row for every driver.

Preconditions are readings the other layers already produce. The action does not re-decide legal eligibility, does not rewrite the terms snapshot, and does not copy a document.

## Ready to Start

`ready_to_start.v1` still asks whether this `Employment(preparing)` may move to `active`. It still reads a current legal `pass`, Employee Data complete, a current complete terms snapshot, and a materialized requirements set that evaluates true. It does not recompute those four. A stale `pass` is not permission to move. `activate_employment` remains the only `preparing → active`.

Professional facts and formality actions participate in that question only through the layer that owns them. This file does not add a fifth input and does not put ZUS or A1 inside `employment_terms.v1`.

## Where this reading sits on the contracts

| Operator block | Layer that already owns it | What that layer already says |
|---|---|---|
| Name, birth date, citizenship | Employee Data | One live owner on `Candidate`. The kwestionariusz is a view |
| Legal stay, work basis, match to this Employment | `legal_eligibility.v1` and the HR Legal Eligibility Gate | Chain stops when the previous step is ambiguous. PASS does not activate the Employment |
| Passport, licence, Code 95, tachograph, medical, psychological, occupational medicine | Profession / vacancy layer, then an Employment requirement instance when the fact belongs to this Employment | Not inputs of the legal chain. One evidence object may satisfy two facts. Applicability and resolution are two axes |
| Position, basis, work time, workplace, pay, duration, probation | `employment_terms.v1` | A confirmed snapshot. Completeness leaves state `preparing` |
| Work-authorization submission | `work_authorization_procedure.v1` | `country` + `procedure_type` + `kod_zawodu`. No preset row in that contract |
| ZUS, A1 | An action with preconditions | Not employee data. Not a permanent block on the card |
| Move to active | `ready_to_start.v1` | Four readings. Activation re-checks freshness |

## Employment Preparation Dependency Amendment

The lifecycle contract records this reading. While the Employment is `preparing`, Employee Data, Legal Eligibility, Employment Terms, applicable professional requirements, and formality actions proceed by their own prerequisites. Legal Eligibility PASS can be a result of that preparation. None of those layers activates the Employment.

ZUS is a formality action of the applicable process. It is not universally pre-start or post-start. A missing work permit does not by itself block ZUS registration. The runtime rule that blocked a third-country driver until the permit path was closed is withdrawn in [work-eligibility-pr4.md](../architecture/work-eligibility-pr4.md).

Applicable requirements may be materialized and resolved before Legal Eligibility PASS. Ready to Start is where the final applicable set must be ready. The four inputs of `ready_to_start.v1` stay. Work Authorization is read through the legal decision. A formality action is read through the requirement or the process result that owns it.

The intended start date and the work system are terms of `employment_terms.v1`. `started_on` is the actual start.

`#hr-verification` is not this amendment.

## HR Driver Operator Surface

The employee page `#hr-verification` assembles the owners in the table above for one Employment. A blocked earlier gate does not hide a later fact. The fact stays on its tab. One next action is the open working step, and its order comes from the prerequisites of this case. Ready to Start is the four existing readings. After a current pass, Start employment calls `activate_employment`.

The surface does not add a driver-card store, an Employment status, a second legal model, or a document list for the screen. It is a projection. Authority over the same facts is [Canonical Fact Authority](../architecture/canonical-fact-authority-contract.md). Canonical Fact Authority Contract Gate **PASS**. That contract does not assign a capability and does not rewrite this surface.

The employee page renders three levels: Status Summary, Record tabs, and the operational sidebar. [HR Employee Record Projection](../architecture/hr-employee-record-projection.md) Contract Gate **PASS** assigns the eight groups. Tabs are a navigation projection of those groups: Dane osobowe, Legalizacja, Kwalifikacje with Badania, Zatrudnienie, Formalności, and Dokumenty. History is not a tab. Status Summary is computed from the existing employment state, the current action, blockers, and evidence expiry. It is not a stored status. The sidebar holds the system task widget and the existing reminder modal, the existing notes widget, and history. Dokumenty mounts the candidate document surface for this person. Passport, residence card, visa, and permit stay on that surface; Legalizacja reads their evidence and does not edit them as documents. Current Process is that status line and, when a concrete action exists, one task. Dane osobowe, Legalizacja, and Zatrudnienie edit through the owners that already hold those facts: the candidate person fields, the legal eligibility reading, and the employment-terms confirmation. The task opens that action. Qualifications and medical show the requirement and an evidence indicator taken from the existing document status. Categories and term are read from the linked evidence because that document owns those fields. One document may cover more than one fact. They do not add a dictionary, a file editor, or a document control. The Dokumenty card is a count and a link to the Document Hub. Current Process is one next action. When the case is returned to Recruitment, that action opens the recruitment case and does not ask HR to keep verifying. HR does not edit the record, notes, or tasks while Recruitment holds the case. Legacy verification, checklists, and debug projections are not rendered on this page. The page does not store a fact.

## Evidence boundary

A person fact and an Employment fact keep their owners. Employee Record shows that value. The evidence relation shows coverage. Document Hub manages the evidence.

A value is read from the linked evidence only when that evidence is the canonical owner. Licence number, categories, and term are that case. Citizenship stays a person fact. A passport may evidence citizenship. It does not own citizenship.

These readings stay as they are until a browser walk of the deployed page:

- Employee Record does not upload, replace, preview, or delete a document.
- Document Hub manages the document and its fields. After a change, Employee Record re-reads the result.
- One evidence may cover N facts.
- `missing` means the fact has no required evidence. It does not mean a separate file is mandatory.
- `expired` and `rejected` stay those statuses. Evidence exists and is unfit. They are not `missing`.
- Handoff changes authority over the same document. It does not create an HR copy.
- Badges, dictionaries, document statuses, and UI primitives stay the system ones.

The browser walk is Dane osobowe, Legalizacja, Zatrudnienie, Kwalifikacje and Badania, the Documents summary, Current Process, and Ready to Start. The E2E is not PASS. That walk names the next red. This file does not add a further action on the record.

## Out of this reading

No seed of driver requirements. No Polish document list. No change to `r5_required_set`. The Legal Eligibility Matrix Gate is not passed. Work Authorization Procedure gains no preset. Ready to Start gains no input.
