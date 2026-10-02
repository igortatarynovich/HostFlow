# Legal Eligibility Matrix

**Status:** **Opened** — structure only. Legal Eligibility Matrix Gate **not PASS**.  
**Date:** 2026-10-02  
**Trusted base:** `integration/release-product-a-b` @ `9cec4895` ([#398](https://github.com/igortatarynovich/HostFlow/pull/398))  
**Contract:** [legal-eligibility-contract.md](legal-eligibility-contract.md) (`legal_eligibility.v1`, Legal Eligibility Contract Gate **PASS**). This file does not amend that contract. It adds no fact, no legal-policy token, and no alias.  
**Machine id:** none. No runtime module.

> A cell key is exactly the contract's six closed facts, in the contract's order.  
> This opening shows that `visa_d`, `karta_pobytu`, and `stay_basis` `''` are different coordinates. It does not assign `required_set_override` or `candidate_default` to any of them, and it names no document.  
> A filled cell may hand RPM only that cell's outcome id, not a required document set. This opening hands nothing: every cell is **unassigned**. `r5_required_set` stays the sole writer of the required set.  
> Feat stays locked. Runtime is not authorized. Minimal Recruitment → HR stays not scheduled. HostFlow v1 is not release-ready.

---

## Cell

A cell key is exactly these six facts, in this order, and no other key:

1. `stay_basis`
2. `citizenship`
3. `employment_country`
4. `residence_permit_country`
5. `licence_issuing_country`
6. `qualification_jurisdiction`

`residence_permit_type` is not a key. `eu_member` and `oswiadczenie_eligible_alpha2` are not keys.

`stay_basis` uses only the card vocabulary already closed by the contract: `''`, `visa_d`, `visa_c`, `karta_pobytu`, `eu_citizen`, `waiting_for_trc`, `other`. The cell keeps that card token. This opening does not rewrite `visa_d` as `visa`, `karta_pobytu` as `card`, or `''` as `none` or `no_residence_card`. It does not list legal-policy tokens and does not map a card token onto a pack token.

`stay_basis` is never **absent**. Its empty recorded state is the card value `''`. **absent** is a coordinate only for `citizenship`, `employment_country`, `residence_permit_country`, `licence_issuing_country`, and `qualification_jurisdiction`, and only when that fact is not recorded. **absent** is not `''`. It is not a card token, not a pack token, and not a legal-policy token.

Two cells differ when any key differs. Holding the other five keys **absent**, these three `stay_basis` values are three coordinates. The word absent in that column is those other keys, not `stay_basis`:

| `stay_basis` | other five keys | outcome slot |
|---|---|---|
| `visa_d` | absent | **unassigned** |
| `karta_pobytu` | absent | **unassigned** |
| `''` | absent | **unassigned** |

The key space can hold every other combination of the six facts. This opening does not enumerate them and does not add a default cell.

**unassigned** is the state of every cell in this opening. It means the cell has no outcome id. It is not an outcome id. It is not `candidate_default` and it is not `required_set_override`.

---

## Selection

A recorded fact set matches at most one cell. The match key is the six-tuple above. `stay_basis` contributes its card value, and `''` is that value when the card records empty. Each of the other five facts contributes its recorded value or **absent**. Two cells cannot share one six-tuple. A six-tuple that is not one of the three cells in the table matches no cell.

---

## Payload to RPM

When a cell has an outcome id, RPM receives that outcome id. RPM does not receive the required document set from the matrix. `r5_required_set` consumes the outcome and stays the sole writer of the required set. The matrix does not answer “must this candidate provide type X?”. Eligibility and transfer keep consuming `r5_required_set`. They do not read the matrix.

`required_set_override` and `candidate_default` are future outcome schema. They are assigned to no cell.

| Outcome id | Schema, not a live payload | This opening |
|---|---|---|
| `required_set_override` | a require list and a remove list, the contract shape | assigned to no cell |
| `candidate_default` | no legal-fact override; `r5_required_set` keeps the path it already uses when no legal override matches | assigned to no cell |

An **unassigned** cell hands RPM nothing. That is not the `candidate_default` schema.

```text
recorded six-tuple
  → at most one cell
  → that cell's outcome id, only when one is assigned
  → RPM r5_required_set writes the required set
  → eligibility / transfer consume that set
```

This opening stops before the outcome id. The arrow into RPM is the later handoff shape. It is not a payload sent now.

---

## Legal Eligibility Matrix Gate

**Outcome:** **not PASS**. This opening is the structure, not the filled rules.

PASS when, and only when, all of the following hold:

1. This file is **Accepted** and the cell key is still exactly the contract's closed fact set.  
2. `visa_d`, `karta_pobytu`, and `''` remain three cells when the other keys are equal.  
3. Every cell the business rules include has exactly one assigned outcome id, `required_set_override` or `candidate_default`. **Unassigned** is no longer the live slot.  
4. A `required_set_override` cell names its require list and its remove list in the RPM document-type vocabulary. Those lists are the matrix content. This opening has none.  
5. The payload path above is unchanged. `r5_required_set` is still the only required-document authority.  
6. No new fact, no new legal-policy token, no alias, no pack change, no engine change, no new column, and no runtime module. Feat stays locked. Minimal Recruitment → HR is not scheduled. HostFlow v1 is not declared release-ready.

That PASS assigns outcome ids to the business cells. It does not authorize a runtime module, a pack change, an engine change, or a change to eligibility, transfer, `ready_for_employment.v1`, HR, or the database schema. Feat stays locked after that PASS. Minimal Recruitment → HR stays not scheduled. HostFlow v1 stays not release-ready. Implementation remains a later queue step.

Evidence for that future PASS is an Accepted matrix whose cells satisfy 2–5, plus a test that reads those cells and does not find a second writer. This opening does not produce that evidence.

---

## Out of this opening

- Assigning `required_set_override` or `candidate_default` to any legal fact.  
- Any require list or remove list.  
- A legal-policy token list, or a map from `visa_d` onto `visa`.  
- Normalization into pack inputs, pack edits, engine edits, runtime, eligibility, transfer, `ready_for_employment.v1`, HR, or a database column.  
- Unlocking feat. Scheduling Minimal Recruitment → HR.
