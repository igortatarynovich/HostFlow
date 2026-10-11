# HR Employee Record Projection

**Status:** **Accepted** (L2 contract — HR Employee Record Projection Contract Gate **PASS**).  
**Date:** 2026-10-05  
**Machine id:** `hr_employee_record_projection.v1` — named here. No runtime module in this slice.  
**Parents:** [Canonical Fact Authority](canonical-fact-authority-contract.md) (`canonical_fact_authority.v1`) · [Employee Record & Employment Lifecycle](employee-record-employment-lifecycle-contract.md) · [HR Driver Operator Surface](../workflows/hr-driver-operator-flow.md) · [Legal Eligibility](legal-eligibility-contract.md) (`legal_eligibility.v1`)

**L0 checklist:** No new P-rule. No Passport or Manifest shape change. No Architecture RFC. Applies **P-02** and **INV-01**: one live address for a value. Does not rewrite L0. Does not replace Canonical Fact Authority. Does not replace `legal_eligibility.v1`.

> One canonical fact may have different projections. Recruitment presents it as an element of a conditional decision flow. HR presents it as an element of a stable hierarchical employee record. Neither projection owns the fact. Neither projection determines policy.  
> The information architecture below is where HR expects to find a fact. It does not depend on the stage the person is in.  
> It is not the Legal Eligibility vertical. It does not implement legal evidence.  
> `#hr-verification` is not rewritten.  
> No schema is written. No runtime module is authorized.  
> HostFlow v1 is not release-ready.

---

## Three levels

A fact is read at three levels. They are not the same decision.

Canonical Fact Authority is where the fact lives. One `citizenship`, one address for driving categories, one address for Code 95. Recruitment and HR do not create their own copies. That contract is already **PASS**. This slice does not reopen it.

Process policy is why the process reads the fact.

Projection is how the module shows the fact.

---

## Process policy

Recruitment reads facts to decide, in order, who the candidate is, whether they can legally work, whether they have the required qualifications, whether they match the vacancy, what still must be obtained or checked, and whether they can move forward.

HR reads the same facts to keep the person and the Employment. That question sequence does not determine the HR screen.

Process policy is not a projection, and it is not the address of the value. Applicability stays with the policy that already owns it. An HR group that can show Code 95 does not mean this Employment requires Code 95.

---

## Information architecture

The HR employee record is a stable information architecture. It is not a workflow. It is not a wizard and it is not a list of questions.

The hierarchy is assigned from the nature of the fact. It is not taken from Recruitment. It is not taken from `#hr-verification`.

The groups stay in place. A missing A1 does not become the question Czy ma A1. The group shows no applicable element, or it shows the status of that process.

| Group | What HR looks for here |
|---|---|
| Dane osobowe | Legal name, birth date, citizenship, contacts, address, PESEL, and the other permanent person facts |
| Legalizacja / Prawo do pracy | Stay basis, legal stay evidence, work basis, permit or exemption, the dates, and fit to this Employment |
| Kwalifikacje i uprawnienia | Licence, categories, Code 95, tachograph, professional qualifications, and experience |
| Badania i zdolność do pracy | Medical examinations, psychological tests, occupational medicine, and the other applicable requirements of that kind |
| Zatrudnienie | Employer, position, planned start, actual start, contract, work time, work system, workplace, compensation, duration, and probation. These facts belong to one Employment |
| Formalności | ZUS, A1, and the other formalization actions of the applicable process |
| Dokumenty | One access to the evidence and document objects of the person and the Employment. Not a second source of facts |
| Historia | Handoffs, Employment history, verification, invalidation, and the significant process events |

The address of each fact stays the owner already named. Dane osobowe adds no column. Legalizacja / Prawo do pracy reads `legal_eligibility.v1` and its evidence. Zatrudnienie reads `employment_terms.v1` and the Employment row. Formalności does not turn ZUS or A1 into a person fact. Dokumenty does not copy a document.

```text
Dane osobowe
→ Legalizacja / Prawo do pracy
→ Kwalifikacje i uprawnienia
→ Badania i zdolność do pracy
→ Zatrudnienie
→ Formalności
→ Dokumenty
→ Historia
```

### Fact row

Inside a group, one fact uses one row.

```text
Label → canonical value → status → evidence → permitted actions
```

Obywatelstwo | Białoruś | Verified | Paszport | Edytuj

Kod 95 | ważny do 12.06.2028 | Verified | Prawo jazdy | Unieważnij

A permitted action is shown because `canonical_fact_authority.v1` grants that capability to the current actor and process. The projection does not choose the button.

In Recruitment, citizenship Belarus can be the question Obywatelstwo, answered Białoruś, followed by the question of the stay basis.

In HR, Dane osobowe shows Obywatelstwo: Białoruś. The residence card, its term, the decision, and verification sit in Legalizacja / Prawo do pracy and in Dokumenty. HR does not ask the stay basis again as a recruitment step.

---

## Employee Record and Current Process

Employee Record answers what is known about this person and this Employment.

The process surface answers what to do now.

They are two views of the same facts. They are not two data systems.

Current action stays outside the groups. Verification is not placed inside Dane osobowe or Legalizacja / Prawo do pracy. The process surface may say `Next action: Verify legal stay → Open`, and that opens the fact in the group that holds it.

`#hr-verification` is the current process and verification surface. It is not the final HR employee record. It does not grow by adding sections until the surface becomes that hierarchy. A later product rebuilds HR as Employee Record plus Current Process. That rebuild is not this gate.

---

## HR Employee Record Projection Contract Gate

**Outcome:** **PASS**.

The information architecture is assigned. The fact row is assigned. Employee Record and Current Process stay two views. None of these sentences writes a store, assigns a capability, or rebuilds the screen.

One canonical fact may have different projections. Recruitment presents it as an element of a conditional decision flow. HR presents it as an element of a stable hierarchical employee record. Neither projection owns the fact. Neither projection determines policy.

The false close is that the HR screen displays every Recruitment question.

No schema is written. No runtime module is authorized. This slice does not amend `legal_eligibility.v1`. This slice does not implement legal evidence. Canonical Fact Authority is not reopened. No capability is assigned. The reading of current RBAC is not opened. The HR Driver Operator Surface is not rewritten. Feat stays locked. HostFlow v1 is not release-ready.

---

## Out of this slice

Employment Terms are not rewritten. No Person table is authorized. No `canonical_facts` store is authorized.
