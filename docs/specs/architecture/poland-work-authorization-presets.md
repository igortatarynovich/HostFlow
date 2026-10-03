# Poland Work Authorization Presets

**Status:** **Accepted** — Poland Work Authorization Presets Gate **PASS**. No `kod_zawodu` row. Feat stays locked. Runtime is not authorized.  
**Date:** 2026-10-02  
**Trusted base:** `integration/release-product-a-b` @ `020cb4e5` ([#402](https://github.com/igortatarynovich/HostFlow/pull/402))  
**Parents:** [brief](../tasks/poland-work-authorization-presets.md) · [Work Authorization Procedure contract](work-authorization-procedure-contract.md) (`work_authorization_procedure.v1`, Contract Gate **PASS**)

> For country `PL`, this file names the closed `procedure_type` set and the shape of a preset.  
> A `procedure_type` is a procedure. It is not a document code and it is not an evidence type.  
> Many `kod_zawodu` values resolve to one preset. `kod_zawodu` is not a source of requirements.  
> The two baselines are filled. No `kod_zawodu` row is written. `r5_required_set` stays the sole writer. Feat stays locked. Runtime is not authorized.

---

## Closed set

Country is `PL`. The set has exactly these two values, and no other.

| `procedure_type` | The procedure the product already selects | Not this id |
|---|---|---|
| `employer_declaration` | `derive_document_applicability_decision` sets `work_permit_type` to `oswiadczenie` | document code `oswiadczenie`; catalog token `declaration` |
| `work_permit_a` | the same function sets `work_permit_type` to `zezwolenie_A` | document code `zezwolenie_A`; catalog token `type_a` |

`procedure_type`, `work_permit_type`, and a document or evidence code are three different things. `employer_declaration` is not the stored string `oswiadczenie` and is not the catalog token `declaration`. `work_permit_a` is not the stored string `zezwolenie_A` and is not the catalog token `type_a`. `work_permit_type` is the field the product stores today. It is not the procedure type. A document code is evidence identity. They are not aliases of these two values.

The list is closed. `type_b`, `type_c`, and `other` appear in the `work_permit_types` reference domain. `type_b` also appears in `PERMIT_TYPES_CANONICAL`. No operator or runtime path starts a Poland work-authorization procedure with those values, and they are not members of the set.

---

## Entry points

The closed set is the procedures a candidate and an employment can actually start. It is not only the automatic choice.

| Path | What it can start |
|---|---|
| `derive_document_applicability_decision` and the document auto-apply that reads it | `oswiadczenie`, `zezwolenie_A`, or no work-permit choice |
| HR work-eligibility edit | citizenship, whether a permit is required, application status, and red-paper status. It does not offer a procedure type |
| Work-permit document field | a select of `type_a` and `declaration` on document metadata. It does not start `type_b`, `type_c`, or `other` |
| Workforce profile column `work_permit_type` | any short string may be stored, and the journey uses that string only as a portal-url key. The write does not start a procedure |
| `work_permit_types` and `PERMIT_TYPES_CANONICAL` | catalog rows. They are not a start action |
| Document type `work_permit` | one evidence type. Its aliases are `oswiadczenie` and `zezwolenie_a` |

No path starts `type_b`, `type_c`, `other`, or a procedure value other than the two in the closed set.

`work_permit_type is None` is not a third procedure type. Legal Eligibility already records work authorization `not_required` for `pl` and `eu_eea_ch`. This file does not add a procedure for that case.

Red paper, a visa, and a stay basis are not procedure types.

---

## Resolution

The accepted selector stays `country` + `procedure_type` + `kod_zawodu` → one preset. This file does not reopen that contract.

For `PL`, that one preset is the baseline of the procedure. Many `kod_zawodu` values resolve to the same preset. A separate row per code is not the model. This file does not choose `kod_zawodu`. It does not assign a HostFlow document type. No `kod_zawodu` row is written.

`kod_zawodu` stays an attribute of the application and the key that identifies the profession. It is not a source of the document list. The profession is then tested by a separate rule: is this a regulated profession? Only that rule adds qualification evidence. This file does not write the regulated-profession rule and does not write a code table.

If the selector does not match one of the two procedure types, the accepted contract still adds no submission requirement. This opening does not guess one.

```text
procedure_type → one baseline
kod_zawodu → profession → regulated? → qualification evidence
```

---

## Preset schema

A Polish submission package is not only a list of files. Each of `employer_declaration` and `work_permit_a` has one baseline of the same shape. The baseline is shared by every `kod_zawodu` of that procedure. The two baselines below are that fill.

| Kind | What it is | What it is not |
|---|---|---|
| Document or evidence requirement | A proof the package must contain, such as the travel document or proof of payment | A second upload when that proof is already evidence |
| Declaration or attestation | A statement of the employer. It may be completed in the portal | A candidate document |
| Evidence constraint | A rule on evidence that is already required, such as a sworn translation of a foreign-language proof | Another required document |
| Conditional requirement | A proof that appears only when a stated condition holds, such as a temporary-agency agreement, or qualification evidence when the profession is regulated | A row for each `kod_zawodu` |
| Authority-requested extra | A requirement the operator adds after the office asks for a further proof | A member of the closed preset |

Proof of payment is a document or evidence requirement. Its amount belongs to the procedure and is not a separate document. A sworn translation is an evidence constraint. An office request under § 8 ust. 3 of the attachment regulation (Dz.U. 2025 poz. 1629) is an authority-requested extra. It is not written into the preset in advance.

Existing evidence satisfies a document or evidence requirement without a second upload. `r5_required_set` remains the only writer. `procedure_type`, `work_permit_type`, and a document or evidence code stay three different things.

The two baselines are filled. They do not copy one baseline into a row per `kod_zawodu`.

---

## Baselines

Both baselines use only the attachment regulation (Dz.U. 2025 poz. 1629) and the fee regulation (Dz.U. 2025 poz. 1622). A document already held as evidence satisfies a document or evidence requirement. It does not open a second upload slot.

An authority-requested extra is not a baseline requirement. § 8 ust. 3 lets the office ask for a further proof. The operator adds that requirement when the office asks. It is not written into the preset in advance.

### `employer_declaration`

| Requirement | Kind | When | Evidence | Source |
|---|---|---|---|---|
| `travel_document` | document/evidence | always | the existing passport evidence; no second upload | poz. 1629 § 7 pkt 1 |
| `payment_proof` | document/evidence | always | proof of payment that names the foreigner. Amount: 400 zł | poz. 1629 § 7 pkt 4; poz. 1622 § 2 pkt 5 |
| `employer_circumstances` | declaration/attestation | always | the employer's statement on art. 13 ust. 1 pkt 1 lit. c–g, signed not earlier than 30 days before filing. It may be completed in the portal | ustawa art. 62 ust. 3 |
| `comparable_remuneration` | declaration/attestation | always | the employer's statement that the stated pay is not lower than pay for comparable work | poz. 1629 § 8 ust. 5 |
| `financial_means` | declaration/attestation | always | the employer's statement of means or income to cover the obligations | poz. 1629 § 8 ust. 6 |
| `foreigner_document_offence` | declaration/attestation | always | the employer's statement on whether the foreigner was convicted under art. 270–273 or 275 of the Penal Code | poz. 1629 § 8 ust. 7 |
| `sworn_translation` | evidence_constraint | a foreign-language proof other than the travel document | a constraint on that proof. Not a document | poz. 1629 § 8 ust. 8 |
| `temporary_agency_agreement` | conditional | `employer_is_temporary_work_agency = true` | the user-employer's agreement on the assignment | poz. 1629 § 7 pkt 2 |

### `work_permit_a`

| Requirement | Kind | When | Evidence | Source |
|---|---|---|---|---|
| `travel_document` | document/evidence | always | the existing passport evidence; no second upload | poz. 1629 § 2 pkt 1 |
| `payment_proof` | document/evidence | always | proof of payment that names the foreigner. Amount: 200 zł when the intended period does not exceed 3 months; 400 zł when it exceeds 3 months. The period is a parameter of this procedure, not of the profession | poz. 1629 § 2 pkt 4; poz. 1622 § 2 pkt 1 and 2 |
| `employer_circumstances` | declaration/attestation | always | the same statement as on `employer_declaration`. The attaching article is art. 9 ust. 4 | ustawa art. 9 ust. 4 |
| `comparable_remuneration` | declaration/attestation | always | the same statement as on `employer_declaration` | poz. 1629 § 8 ust. 5 |
| `financial_means` | declaration/attestation | always | the same statement as on `employer_declaration` | poz. 1629 § 8 ust. 6 |
| `foreigner_document_offence` | declaration/attestation | always | the same statement as on `employer_declaration` | poz. 1629 § 8 ust. 7 |
| `sworn_translation` | evidence_constraint | a foreign-language proof other than the travel document | the same constraint as on `employer_declaration` | poz. 1629 § 8 ust. 8 |
| `temporary_agency_agreement` | conditional | `employer_is_temporary_work_agency = true` | the same agreement as on `employer_declaration` | poz. 1629 § 2 pkt 2 |

### How the two baselines differ

The declaration set is the same four statements. The active conditional is the temporary-agency agreement. The evidence constraint is the same. The difference is the payment proof:

| Baseline | Payment amount |
|---|---|
| `employer_declaration` | 400 zł |
| `work_permit_a` | 200 zł up to 3 months; 400 zł above 3 months |

`employer_circumstances` is attached by art. 62 ust. 3 on the declaration and by art. 9 ust. 4 on the permit. It is one declaration, not a profession rule.

### Not in either baseline

These are not submission requirements of either procedure. `auto_apply_rules` is not a source: `prawo_jazdy`, `karta_tachografu`, `badania_lekarskie`, `swiadectwo_kierowcy`, `visa_D`, and `umowa_o_prace` are not baseline requirements. Code 95 and ADR are not baseline requirements. The outcome cards `oswiadczenie` and `zezwolenie_A` are not attachments. A copy of the employment contract after the grant, an employer-registry extract, and a power of attorney are not in § 2 or § 7. The local occupation refusal list in art. 31 is not a document.

§ 2 pkt 3 and § 7 pkt 3 name qualification evidence when the work is in a regulated profession. That condition is optional. It is not an active baseline row. HostFlow does not evaluate it, and an unevaluated condition does not keep the ordinary package from `submission_ready`. A company may turn it on, or a later reliable rule may. This gate does not wait for that rule.

---

## Recorded drift, not this slice

Who may use `employer_declaration` is a country rule, not a preset row. The in-force rule is the regulation of 21 November 2025 (Dz.U. 2025 poz. 1617; [ELI DU/2025/1617](https://eli.gov.pl/eli/DU/2025/1617/ogl)), in force since 1 December 2025. Its § 2 names Armenia, Belarus, Moldova, and Ukraine. Its § 3 is only a continuation for a declaration already entered before that date.

The product lists do not match that rule. `citizenship_rules.json` `oswiadczenie_list` includes Georgia. The pack set `oswiadczenie_eligible_alpha2` includes Georgia and does not include Armenia. This slice does not correct either list and does not copy either list into a preset. The blocker is [oswiadczenie-country-set-drift.md](../tasks/oswiadczenie-country-set-drift.md). It is not a baseline requirement.

---

## What this opening does not assign

This file does not choose `kod_zawodu`. It does not assign a HostFlow document type. No `kod_zawodu` row is written. It does not copy `citizenship_rules.json` or `oswiadczenie_eligible_alpha2` into a new country rule.

---

## Profession resolver

`kod_zawodu` identifies a profession. It does not decide `profession_is_regulated`.

The profession identity is the code in the classification of occupations and specialties for the labour market, in the version effective on the decision date. The classification in force from 27 November 2025 is the regulation of 21 October 2025 (Dz.U. 2025 poz. 1534). Its annex is a code and a name. It has no regulated flag. The ministry states that this regulation is not a basis for a right to practise a profession. § 3 of that regulation keeps some symbols only until 31 December 2025 and applies the replacement symbols from 1 January 2026. The same digits can name a different occupation after that date. A decision therefore stores the classification instrument, its effective date, and the code. A later classification does not rewrite that decision.

Regulated status is a different question. The work-permit act uses „zawód regulowany” and does not define it and does not publish a code list. The definition in Polish law is art. 5 pkt 4 of the act on recognition of professional qualifications (consolidated text, Dz.U. 2026 poz. 166): professional activities whose exercise depends on formal qualifications set by regulatory provisions. That definition does not attach a boolean to a classification code. Each profession's regulatory provisions sit in their own statute.

These official lists are not a resolver from `kod_zawodu`:

| Source | What it is | Why it is not the resolver |
|---|---|---|
| Dz.U. 2024 poz. 170 | Names of regulated professions and activities for which a prior check may start on a first cross-border service, because of health or public safety | A subset, listed by title, not by classification code. Absence from the list is not `not_regulated` |
| Dz.U. 2026 poz. 166 art. 57 | A further list the Prime Minister may issue for IMI alerts | Not a classification-code map, and not the work-permit attachment rule |
| EU Regulated Professions Database | Notifications under Directive 2005/36/EC | Names and sometimes an ISCO group. Not a versioned Polish classification code. A name match would be a heuristic |

No official Polish source maps a versioned classification code to `regulated` or `not_regulated`. Driver requirements, Code 95, and ADR are not that source.

The KZiS resolver identifies the profession only. It does not derive `profession_is_regulated`. The absence of an automatic rule is never `no`. `profession_is_regulated` is an optional condition. It does not block this gate. An unresolved value does not keep the ordinary package from `submission_ready`.

This determination writes no KZiS to regulated mapping, no heuristic, and no qualification-document mapping. Further research of `profession_is_regulated` stops here.

---

## How a package is composed

The official baselines above are the system Poland preset. Anything less definite is company policy. HostFlow does not issue a legal conclusion for it.

```text
official procedure baseline
+ profession preset
+ vacancy overrides
+ operator-added requirements
− waivers
= effective readiness
```

`r5_required_set` remains the only writer of that union. Existing evidence satisfies a requirement without a second upload.

A profession-preset requirement has one purpose. The company sets it. HostFlow may ship a transport default, and the company may change it.

| Purpose | Meaning |
|---|---|
| `employment` | needed for the vacancy or for admission to the work. Not an official attachment of these procedures |
| `submission` | the company wants it before filing |
| `both` | used in both |

A Driver CE default may name a CE driving licence, Code 95, a tachograph card, a medical certificate, and a psychotest. That default is not a claim that those five documents are attachments required by Dz.U. 2025 poz. 1629. The attachment regulation states the regulated-profession condition and does not name a driving licence or Code 95 for these two procedures. Where another driving procedure names those documents, it names them itself.

If the company sets the CE licence purpose to `submission` or `both`, the work-permit package reports it when it is missing. A `waive_requirement` lifts it for this candidate and this process. An administrator may remove it from the preset. Neither step needs a statute that proves the licence is unnecessary. `override_readiness` remains the audited way to continue while a blocker stays.

An authority-requested extra stays an operator-added requirement. It is not written into the preset in advance.

Every requirement that can affect readiness keeps one origin:

| Origin | Meaning |
|---|---|
| Official baseline | HostFlow takes it from the regulation already recorded above |
| Company configuration | the company's or the office's working practice |
| Authority request | the office asked for a further proof |
| Operator-added | the specialist adds it for this case |

---

## Filing workflow

The product boundary is the legalization path, not a closed legal list of attachments. HostFlow knows who files, which path, which official formularz, where it is filed, which data the formularz needs, which attachments are usual, and what happens after filing.

```text
candidate + employer + vacancy or employment
→ procedure
→ data for the official formularz
→ filled formularz
→ available evidence attached
→ handoff to praca.gov.pl
→ stored case identifier and status
→ later actions
```

The formularz is filled from data HostFlow already holds: employer, foreigner, employment dates, contract type, remuneration, place of work, profession and `kod_zawodu`, and the other fields of that formularz. A published field schema for these two formularze was not found. The public description of an oświadczenie names employer, foreigner, start and period, contract, gross pay, PKD subclass, profession, and place of work ([Wortal PSZ](https://psz.praca.gov.pl/dla-bezrobotnych-i-poszukujacych-pracy/dla-cudzoziemcow/oswiadczenia-o-powierzeniu)).

| `procedure_type` | Formularz on praca.gov.pl | What it is not |
|---|---|---|
| `employer_declaration` | `PSZ-OPPC` | not `PSZ-OPWP` and not `PSZ-OPWPA`; those were replaced on 1 June 2026 |
| `work_permit_a` | `ZC-WWZPP` | not `ZC-WWZ`, and not catalog token `type_a` |

`PSZ-ONKP` is the employer's statement under art. 13 ust. 1 pkt 1 lit. c–g. From 1 June 2026 it is filled in the organization account on praca.gov.pl and attached to the filing. It is not a new procedure type. Later notices are not new procedure types: `PSZ-PPPC`, `PSZ-PNPC`, and `PSZ-PZPC` follow an oświadczenie; `ZC-PNPC`, `ZC-PPPC`, and `ZC-PZPC` follow a work permit. The portal lists them under Zatrudnianie cudzoziemców ([portal help](https://www.praca.gov.pl/eurzad/html/pomoc/zatrudnianie_cudzoziemcow.htm)).

The filer works in the organization context, chooses the office, and signs with a qualified electronic signature, a personal signature, or a trusted profile ([addressee help](https://www.praca.gov.pl/eurzad/html/pomoc/wybor_adresata_2_2.htm); [FAQ](https://www.praca.gov.pl/eurzad/faq)).

Readiness can show the formularz data, the attachment count, a missing configured attachment, the fee, and that `override_readiness` remains available. It still means ready to hand off, not an authority's decision.

### How a filing can leave HostFlow

No public REST API was found on which any SaaS receives a token and submits `PSZ-OPPC` or `ZC-WWZPP`.

The portal help says work-permit applications are submitted by means of Broker SI PSZ into the system Zatrudnianie Cudzoziemców. The vendor describes Broker as the communication layer among PSZ domain systems and state registers. In the 2023 maintenance tender the ministry made the Broker user and technical documentation available to bidders on a written request. That is not a published client contract for a commercial SaaS.

Public interfaces that do exist do not file these applications:

| Interface | What it does |
|---|---|
| `https://broker.praca.gov.pl/api/` KZiS XML and JSON | occupation classification download |
| ePraca WebService for offers and events | read access; the ministry assigns a partner name |
| KRAZ REST at `storapi.praca.gov.pl` | public employment-agency register |

The published compliance procedure, version 4.0, certifies software used in the public employment services. The certificate listed there is Syriusz Std ([Dla integratorów](https://psz.praca.gov.pl/dla-integratorow)). It is not an onboarding path for an HR product.

HRappka's public guide says the user's login.gov.pl username and password are entered in the user settings, a draft is confirmed by SMS to the trusted-profile phone, and the draft is written to Dokumenty Robocze on praca.gov.pl. The user then opens that draft and sends it ([HRappka guide](https://pomoc.hrappka.pl/baza-wiedzy/jak-wysylac-wnioski-o-legalizacje-cudzoziemcow-z-systemu-hrappka-integracja-z-praca-gov-pl/), updated 2026-09-24). That is the employer's own portal session. HostFlow does not take that session as its integration. Browser automation is not the first path.

The open question is the ministry's procedure for connecting an external system to Broker SI PSZ for these formularze: whether an interface is offered, how an integrator is onboarded, which authentication and signature that interface uses, and whether message schemas for `PSZ-OPPC` and `ZC-WWZPP` are provided. This slice does not implement that connection.

---

## Poland Work Authorization Presets Gate

**Outcome:** **PASS**. Evidence is the closed procedure set, the two official baselines, and the boundary that a profession preset is company policy.

- The closed procedure types are `employer_declaration` and `work_permit_a`.
- The two baselines share one requirement schema. The fee policy differs.
- `temporary_agency_agreement` is conditional on `employer_is_temporary_work_agency = true`.
- `profession_is_regulated` is an optional condition. It does not block this gate.
- An authority-requested extra is not a baseline requirement.
- No `kod_zawodu` row is written.
- Existing evidence satisfies a document or evidence requirement without a second upload.
- `r5_required_set` remains the only writer.
- The country-set drift stays a separate blocker. This PASS does not correct it.

Feat stays locked. Runtime is not authorized. The Work Authorization Procedure contract stays accepted. The Legal Eligibility chain is unchanged. The Legal Eligibility Matrix Gate is not passed.
