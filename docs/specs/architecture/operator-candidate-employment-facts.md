# Operator Candidate and Employment Facts

**Status:** **Accepted** — Operator Facts Surface Gate **PASS**. Implementation and UI acceptance **PASS** (2026-10-05). No new chain value. No matrix cell. No document requirement. No new column.  
**Date:** 2026-10-05  
**Line:** `9d841cc8` (ancestor `docs/requirement-resolution-contract`)  
**Machine id:** none. This is a surface over facts already named. It is not a domain and it is not a resolver.  
**Parents:** [Legal Eligibility](legal-eligibility-contract.md) (`legal_eligibility.v1`) · [Legal Eligibility matrix](legal-eligibility-matrix.md) · [Work Authorization Procedure](work-authorization-procedure-contract.md) (`work_authorization_procedure.v1`) · [Poland Work Authorization Presets](poland-work-authorization-presets.md) · [Requirement Resolution](requirement-resolution-contract.md) (`requirement_resolution.v1`) · [CE, Code 95, and the Issuing Country](ce-code95-issuing-country.md) · [Employee Data ownership](employee-record-employment-lifecycle-contract.md#employee-data-ownership)

**L0 checklist:** No new P-rule. No Passport or Manifest shape change. No Architecture RFC. Applies **P-02** and **INV-01**: one authority still answers whether this candidate must provide canonical type X, and that authority stays RPM `r5_required_set`. This surface does not rewrite L0.

> The operator fills facts the contracts already name, through ordinary choices. A choice stores an existing value. It does not add a chain value, a procedure type, or a document requirement. Legal Eligibility evidence stays on the matrix, which this surface does not fill. CE and Code 95 may use the accepted evidence shape. Tachograph and ADR stay professional facts.

The sequential queue is unchanged. Employee Record & Employment Lifecycle stays the active product. Feat stays locked. HostFlow v1 is not release-ready.

---

## Question

For one candidate and one Employment, which existing facts does the operator record, in which order, and what does each recorded fact allow the system to do next?

The surface does not decide a legal rule, does not author a required set, and does not choose an evidence variant the accepted CE case has not already closed.

---

## Order

```text
Citizenship
  → Stay basis + the parameters the chain already needs
  → Work authorization basis + procedure parameters
  → Driving licence facts
  → Code 95 facts
  → Tachograph facts
  → ADR facts
```

Citizenship, stay, and the work basis follow the Legal Eligibility chain. The driving blocks are not steps of that chain. A missing driving fact is its own question. The legal chain does not have to be complete before a driving fact is recorded.

A step the chain has already determined is not shown.

| Recorded citizenship class | Stay | Work |
|---|---|---|
| `pl` | `not_required`, not shown | `not_required`, not shown. `valid_for_this_employment` is `yes` |
| `eu_eea_ch` | `not_required`, not shown | `not_required`, not shown. `valid_for_this_employment` is `yes` |
| absent | the citizenship question. Stay and work are not shown as a third-country path | the same |
| `third_country` | the stay question | the work question, after stay no longer withholds it |

`not_required` is the determined chain value. It is not the card token `eu_citizen` and it is not empty `stay_basis`.

---

## What is saved

The operator's words are labels. The stored fact is the value already closed by its contract.

| Block | Stored fact | Next |
|---|---|---|
| Citizenship | a country on the live owner `candidates.personal_data.citizenship` | `citizenship_class` is computed: `pl`, `eu_eea_ch`, or `third_country`. The class is not stored as the citizenship |
| Stay | chain `stay_basis`, plus the parameters that chain already requires before the next step | Legal Eligibility continues. This surface assigns no evidence |
| Work | chain `work_authorization_basis`, plus `procedure_type` when the basis is `separate_required` | `valid_for_this_employment` stays the chain's value. This surface does not match a permit to the Employment |
| Driving licence | issuing country, categories, validity | the CE requirement receives those facts |
| Code 95 | presence, one of the two closed forms, issuing country, validity | shared evidence or separate evidence, as the [CE case](ce-code95-issuing-country.md) already closed |
| Tachograph | presence, issuing country, validity | a professional fact. No evidence shape |
| ADR | presence, issuing country, validity | a professional fact. No evidence shape |

The country list is the platform country registry. Citizenship class is computed from that registry. Stay choices and work labels are the `legal_eligibility.v1` vocabulary. The card renders the codes the view returns and translates them. This surface publishes no country list, no EU/EEA/Swiss list, and no second stay or work list. The card token `eu_citizen` is not `citizenship_class`.

Chain `stay_basis` stays `not_required`, `visa_d`, `visa_c`, `karta_pobytu`, `visa_free`, `waiting_for_trc`, `special_protection`, `other`, `none`. This surface adds no value. `visa_d` is not pack token `visa`. `visa_c` is not `visa_d`. Empty card `stay_basis` (`''`) is not `none`, not `not_required`, not `visa_d`, and not `karta_pobytu`. `residence_permit_type` stays not a fact key.

Parameters are only the details recorded under a chosen stay. `visa_d` and `visa_c` are the visa type. This surface does not ask for another type or a purpose. For `karta_pobytu` the card alone does not determine the right to work. This surface does not publish a parameter catalog and does not add a column.

`work_authorization_basis` stays `not_required`, `included_in_stay`, `separate_required`. An operator hold is not a fourth value and names no document.

---

## Projections

Two labels store an existing basis together with an existing procedure type.

| Operator label | `work_authorization_basis` | `procedure_type` |
|---|---|---|
| Work permit | `separate_required` | `work_permit_a` |
| Oświadczenie | `separate_required` | `employer_declaration` |

`procedure_type`, `work_permit_type`, and a document code stay three different things. The label does not store `oswiadczenie`, `zezwolenie_A`, `declaration`, or `type_a`. Powiadomienie is not a projection. `type_b`, `type_c`, and `other` are not projections.

`included_in_stay` is recorded when the operator states that the stay decision includes the right to work for this Employment. The stored value is `included_in_stay`. A residence-permit name is not a new basis.

`kod_zawodu` stays an attribute of the Employment and the vacancy. It is not a Legal Eligibility input and it is not a source of requirements. Employer, dates, and conditions may be recorded as the details a later match would read. This surface does not perform that match. While the basis is `included_in_stay` or `separate_required`, `valid_for_this_employment` stays `operator_verification`. A recorded `no` is the chain value `no` and names no document.

---

## Unknown

An unknown control stores no value. The fact stays absent. Progress is `needs_input`.

`unknown` is not a value of `citizenship_class`, `stay_basis`, `work_authorization_basis`, or `procedure_type`. Absent citizenship is not `third_country`. Absent stay is not `none`.

---

## Three rules

1. A question the previous fact has already determined is not shown.  
2. An unknown fact asks the question. It does not ask for a file.  
3. An established negative fact yields the negative result the owning contract already names. It does not ask for a file.

For the CE requirement and the Code 95 requirement, that negative result is `blocking` where the [CE case](ce-code95-issuing-country.md) already uses it: the entitlement is known and is not CE, or Code 95 is known and has expired, or presence is known and the required qualification is absent. Missing proof stays `unresolved`. A REQUIRED row holds the Ready to Start entrance until `satisfied` or `waived`. A PREFERRED row does not.

Stay `none`, empty stay, and an operator hold name no document. They are not requirement `blocking`.

---

## Evidence

Legal Eligibility evidence is the matrix. The matrix is not filled here. Recording citizenship, stay, or the work basis does not request a document and does not assign `required_set_override` or `candidate_default`.

The driving licence and Code 95 may name the accepted evidence shape. Shared evidence is one document and two links. Separate evidence is the licence for CE and the qualification card for Code 95. The operator's form is one of those two. A third form is not a choice. While the issuing country is absent, progress is `needs_input` and no file is requested. This surface does not link a file and does not write the Employment requirement row.

Tachograph and ADR are stored as professional facts. When the operator says one exists, the document type registry asks `tachograph_card` or `adr_certificate`. A medical certificate asks `medical_certificate`. Psychological tests ask `psychological_certificate`. Polish citizenship asks `national_identity_card`. Every other citizenship asks `passport`. A residence card asks `temporary_residence_decision`. An extra file asks the catalog type `additional_document` when the operator says it exists. This does not fill the matrix and does not ask for a visa, the residence card itself, or a work permit.

---

## Authority

| Question | Authority |
|---|---|
| Which country is this person's citizenship? | the live owner `candidates.personal_data.citizenship`. This surface writes that owner and does not open a second citizenship |
| What is `citizenship_class`, `stay_basis`, `work_authorization_basis`, and `valid_for_this_employment`? | `legal_eligibility.v1` |
| Which procedure type is selected for Poland? | the closed pair `employer_declaration` and `work_permit_a` |
| Which evidence shape may prove CE and Code 95? | the CE case, under `requirement_resolution.v1` |
| Must this candidate provide canonical type X? | RPM `r5_required_set` |
| May this Employment start? | Ready to Start reads its four canonical results |

This surface is not a source of requirements. `r5_required_set` stays the sole writer of the required set. `visa_d` is not mapped onto `visa`.

Citizenship is a person fact. Stay is a person fact. The work basis and `valid_for_this_employment` belong to this Employment. Satisfaction of a requirement stays on the Employment row. A new Employment does not inherit `satisfied`.

This surface adds no column. It chooses no table for the facts whose contracts have not already named an owner.

---

## Operator Facts Surface Gate

**Outcome:** **PASS**. Evidence is this file.

PASS holds because all of the following are true:

1. The surface records facts the contracts already name. Operator labels are projections onto those values.  
2. A determined chain step is not shown. An absent fact is `needs_input` and asks no file. An established negative uses the negative result already named, and asks no file.  
3. Legal Eligibility evidence is not assigned. The Matrix Gate is not passed by this file.  
4. CE and Code 95 use the two evidence shapes already accepted. Tachograph and ADR are facts without a resolver and without a document request.  
5. No chain value, procedure type, fact key, document type, or column is added. Authority is unchanged. `r5_required_set` stays the sole writer.  
6. The sequential queue is unchanged. HostFlow v1 is not declared release-ready.

This PASS does not build a screen, does not write a requirement row, and does not move an Employment.

---

## UI acceptance

Each fact has one edit place on the candidate card. Another surface may show the stored value. It does not ask the operator to choose that fact again.

The driver facts are one sequence. The right to work for this Employment is the neighboring block, not a field inside the driver sequence.

```text
Dane i uprawnienia kierowcy
  Obywatelstwo
  Na jakiej podstawie przebywa w Polsce?    when the chain still shows stay
    parameters of that stay                 visa validity, or the card validity

Prawo do pracy                              after stay no longer withholds it
  Na jakiej podstawie może pracować?
    parameters of that basis                dates and conditions of the permit or oświadczenie

Uprawnienia kierowcy
  Prawo jazdy              issuing country, then category, then validity
  Code 95                  presence, then validity
  Karta kierowcy           presence, then country, then validity
  ADR                      presence, then country, then validity
```

The procedure code and the Legal Eligibility outcome stay off this surface. The stored values are unchanged.

Operator nie może być proszony o ponowny wybór faktu, który został już zapisany w innym miejscu. Każdy fakt ma jedno miejsce edycji; pozostałe powierzchnie mogą go wyłącznie odczytywać. Powiązane fakty kierowcy muszą być prezentowane razem, a nie rozproszone pomiędzy kartą kandydata, checklistą dokumentów i Legal Eligibility.

The document checklist does not edit these facts. Legal Eligibility status in the work block is the reading already produced. It is not a second citizenship, stay, or work control.

---

## Implementation and UI acceptance

**Outcome:** **PASS**. 2026-10-05. The Operator Facts Surface Gate above stays the contract PASS. This section records the implementation that followed it, and the operator card.

The live path is HTTP, then Postgres, then the candidate card. A fact is stored on the owner the contracts already name. Citizenship stays `personal_data.citizenship`. Stay and the professional facts stay in `personal_data.operator_facts`. The work basis is keyed by the preparing Employment. No column was added.

Unknown stores nothing and asks no file. PL and EU/EEA/CH hide stay and work. A third-country chain is citizenship, then stay, then work. A work label projects onto `separate_required` with `work_permit_a` or `employer_declaration`. A legally significant change on Employment(preparing) runs `legal_eligibility.v1` and leaves Employment.state where it is. Driver documents wait until the issuing country is known and a recruitment requirement has named CE or Code 95. A Poland or EU/EEA/CH licence is shared evidence: the resolved ask is `driver_license`. A licence from outside that set is separate evidence: `driver_license` and `driver_qualification_card`. A recorded `karta_pobytu` asks the checklist for the residence card and the voivodeship decision. A recorded medical presence asks `medical_certificate`. A recorded psychological presence asks `psychological_certificate`. An unknown or negative answer asks for none of those. Passport, an identity card, a tachograph card, ADR, and an extra file stay only when recruitment policy already named them and `r5_required_set` materialized them.

On the candidate card each fact has one edit place. The operator answers citizenship, then the stay question when the chain still shows it, then the parameters of that stay, then the work question and the parameters of that basis. Driver qualifications follow: the licence country, then the category and validity, then Code 95, the tachograph card, and ADR. The checklist is the consequence of those facts. It is not a second place that edits them. The procedure code and the Legal Eligibility outcome are not labels on this surface.

One presentation note stays outside this close. The stage guard and the checklist both name the registry type `driver_license` for the shared file. A later change may align any remaining stage text that still names a module code. It does not reopen this surface.

After deploy, production is a smoke of this behavior. It is not a new design.

Feat stays locked. HostFlow v1 is not release-ready.

---

## Out of this slice

- The Legal Eligibility matrix, and any document request that would come from citizenship, stay, or the work basis.  
- A parameter catalog, a permit-type key, and a match of a permit onto this Employment.  
- A country list, and a third Code 95 form.  
- Evidence shapes for a tachograph card or ADR.  
- A passport, a medical certificate, or a psychotest.  
- A column. The stage-guard label `driver_license` for the shared file the checklist shows as `driver_license_code95`.

Feat stays locked. HostFlow v1 is not release-ready.
