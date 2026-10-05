# CE, Code 95, and the Issuing Country

**Status:** **Accepted** — CE + Code 95 Issuing Country Gate **PASS**. No country list. No legal rule. No document type. No runtime module.  
**Date:** 2026-10-05  
**Line:** `6e4b7906` (ancestor `docs/requirement-resolution-contract`)  
**Case of:** [Requirement Resolution](requirement-resolution-contract.md) (`requirement_resolution.v1`). No second machine id.  
**Parents:** [Requirement Resolution Contract](requirement-resolution-contract.md) · [ADR-016](ADR-016-requirement-evidence-document-separation.md) · [Requirement and Evidence model](../platform/requirement-evidence-model-p0.md) · [Legal Eligibility](legal-eligibility-contract.md) (`legal_eligibility.v1`) · [Pre-employment requirements](employee-record-employment-lifecycle-contract.md) (`pre_employment_requirements.v1`)

**L0 checklist:** No new P-rule. No Passport or Manifest shape change. No Architecture RFC. Applies **P-02** and **INV-01**: one authority still answers whether this candidate must provide canonical type X, and that authority stays RPM `r5_required_set`. This case does not rewrite L0.

> For one Employment, the issuing country of the driving licence selects the facts still missing for the CE requirement and the Code 95 requirement, and whether one document is shared evidence for both rows or the two proofs stay separate. A REQUIRED row holds the Ready to Start entrance until it is `satisfied` or `waived`. A PREFERRED row is recorded and shown, and does not hold that entrance.

The sequential queue is unchanged. Employee Record & Employment Lifecycle stays the active product. Feat stays locked. HostFlow v1 is not release-ready.

---

## Question

The vacancy or profession source has already named a CE requirement and a Code 95 requirement on this Employment, each with its level. The issuing country is known, or it is not.

Which facts are still missing, is the proof one shared document or two separate documents, and which of those rows holds the Ready to Start entrance?

This case does not decide that CE or Code 95 is required. It does not author the required set. It does not enter Legal Eligibility.

---

## Issuing country

The issuing country is a fact of the driving licence. It selects the facts and the evidence shape. It does not select whether the row applies. Applicability and level travel with the definition from its source.

`licence_issuing_country` stays outside the Legal Eligibility chain. This case adds no chain value, fills no matrix cell, and assigns no require list and no remove list.

| Issuing country | Progress | What is asked | Stored resolution |
|---|---|---|---|
| Unknown, and at least one of the two rows is applicable | `needs_input` | the issuing country, once, for both rows | `unresolved`. No document is requested |
| Known | the shape below | the facts of that shape | `unresolved` until the proof of that shape is accepted for the row |

The two applicable rows share that one missing fact. The country is not asked twice, and it is not asked as a file.

A row at `NOT_REQUIRED` is not applicable. It does not ask for the country and it does not ask for a file. When both rows are `NOT_REQUIRED`, the country is not asked.

---

## Two shapes

A known issuing country selects one shape. The shapes are closed. This file contains no country row. The country is the selector. Accepted Evidence already names the two shapes.

### Shared evidence

The licence of that country carries Code 95.

The facts are the CE entitlement on that licence, and Code 95 on that same licence.

One document instance. Two evidence links, one on each applicable row. A second upload is not created because the same file is the proof of both rows.

A licence that does not carry Code 95 may satisfy the CE row only. The Code 95 row stays `needs_evidence`. Its proof is still missing. Missing proof stays `unresolved`.

### Separate evidence

That country keeps Code 95 off the licence.

The facts are the CE entitlement on the licence, and Code 95 on a qualification card.

Two document instances. The CE row links the licence. The Code 95 row links the card. The licence does not satisfy Code 95. The card does not satisfy the CE row.

---

## blocking

`blocking` stays a resolved negative outcome. Missing proof stays `unresolved`.

| Established fact | Row | Resolution |
|---|---|---|
| The entitlement is known and is not CE | CE | `blocking` |
| Code 95 is known and has expired | Code 95 | `blocking` |
| The country is missing, or the file of the selected shape is missing | the row that still lacks proof | `unresolved` |

`needs_input`, `needs_evidence`, and `under_review` are readings of an unresolved row. They are not `blocking`. A REQUIRED definition is not the stored word `blocking`.

---

## Ready to Start

Ready to Start reads the stored result of these rows. It does not recompute this case. The level is the definition's level.

| Level | The applicable row | The entrance |
|---|---|---|
| REQUIRED | holds the entrance until the row is `satisfied` or `waived`. `needs_input`, `needs_evidence`, `under_review`, and `blocking` all hold it | held |
| PREFERRED | may be recorded and shown, including when the row is `unresolved` or `blocking` | not held |
| NOT_REQUIRED | is not applicable | outside the check |

A REQUIRED CE row holds the entrance while the issuing country is still missing. A PREFERRED Code 95 row does not hold the entrance, including when that Code 95 is known, expired, and the row is `blocking`. The finding stays on the row.

When both rows are REQUIRED, shared evidence leaves both rows holding the entrance until the one file carries both facts and both links are accepted. Separate evidence leaves each REQUIRED row holding the entrance until its own file is accepted. One of the two files leaves the other REQUIRED row holding the entrance.

When the CE row is REQUIRED and the Code 95 row is PREFERRED, an accepted CE row no longer holds the entrance. The Code 95 row may stay unresolved and is still shown.

This case does not append a Ready to Start decision and does not move `preparing` to `active`.

---

## Authority

| Question | Authority |
|---|---|
| Does this Employment name a CE requirement and a Code 95 requirement, and at which level? | the vacancy or profession source that already names them |
| Which facts are still missing, and is the proof shared or separate? | this case, under `requirement_resolution.v1` |
| Which document shapes may prove a requirement? | Accepted Evidence |
| Must this candidate provide canonical type X? | RPM `r5_required_set` |
| Is this Employment row satisfied, waived, or blocking? | `pre_employment_requirements.v1` stores the result. This case does not write the row |
| May this Employment start? | Ready to Start reads its four canonical results |

Legal Eligibility keeps `citizenship_class` → `stay_basis` → `work_authorization_basis` → `valid_for_this_employment`. Driving licence, Code 95, and the issuing country stay outside that chain. `visa_d` is not mapped onto `visa`.

---

## CE + Code 95 Issuing Country Gate

**Outcome:** **PASS**. Evidence is this file.

PASS holds because all of the following are true:

1. The issuing country is the fact that selects the missing facts and the evidence shape. While it is unknown, progress is `needs_input` and no document is requested.  
2. A known country selects shared evidence or separate evidence, and only those two. One file may satisfy both rows only in the shared shape.  
3. A REQUIRED row holds the Ready to Start entrance until it is `satisfied` or `waived`. A PREFERRED row does not hold that entrance.  
4. No country list is written. No legal rule is encoded. The Legal Eligibility Matrix Gate is not passed by this file. No document type is created. No pack change. No column. No definition key. No runtime module.  
5. The sequential queue is unchanged. HostFlow v1 is not declared release-ready.

This PASS does not choose a country for a person, does not link a file, and does not move an Employment.

---

## Out of this slice

- A list of which issuing country selects which shape. The country is the selector. This file contains no country row.  
- Reading Code 95 off a scan.  
- ADR, a tachograph card, a medical certificate, or a psychotest. The [operator facts surface](operator-candidate-employment-facts.md) may record a tachograph card and ADR as professional facts. It does not resolve them in this case.  
- A change to `hr_employment_requirements`, Ready to Start persistence, or the legal chain.  
- A Python or JSON machine copy of an HR row.  
- The recruitment runtime of `requirement_resolution.v1` executes this case. It does not open an HR requirement.

Feat stays locked. HostFlow v1 is not release-ready.
