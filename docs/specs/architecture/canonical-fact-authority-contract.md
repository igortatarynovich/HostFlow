# Canonical Fact Authority Contract

**Status:** **Accepted** (L2 contract — Canonical Fact Authority Contract Gate **PASS**).  
**Date:** 2026-10-05  
**Machine id:** `canonical_fact_authority.v1` — named here. No runtime module in this slice.  
**Parents:** [Employee Data ownership](employee-record-employment-lifecycle-contract.md#employee-data-ownership) · [ADR-016](ADR-016-requirement-evidence-document-separation.md) · [ADR-036](ADR-036-four-trust-roles-rbac.md) · [handoff contract](handoff-contract.md) · [HR Driver Operator Surface](../workflows/hr-driver-operator-flow.md)

**L0 checklist:** No new P-rule. No Passport or Manifest shape change. No Architecture RFC. Applies **P-02** and **INV-01**: one live address for a value. Does not rewrite L0. Does not replace ADR-036. Does not replace the handoff stage contract.

> Handoff does not transfer a person, card, field or value. Handoff changes process context and capabilities over canonical facts.  
> This contract names that mechanism. It does not assign the capability set of any fact.  
> The [Contract Gate](#canonical-fact-authority-contract-gate) **PASS** is the proof that the mechanism is sufficient. It does not enforce a field capability.  
> No schema is written. No runtime module is authorized.  
> HostFlow v1 is not release-ready.

---

## Question

For one canonical fact, where does the value live, and which capabilities does a process hold over that same value now?

Ownership and authority are two readings. A module is neither of them.

```text
Canonical Fact → Evidence → Authority → Process → Projection
```

Lead, Recruitment, HR, Legal, and Payroll are processes and projections. They are not stores of the person.

---

## Ownership

Ownership is the physical address of the value. The addresses already named stay the addresses.

| Kind of fact | Address already named |
|---|---|
| Person facts such as legal name, birth date, citizenship, phone | The live owners in [Employee Data ownership](employee-record-employment-lifecycle-contract.md#employee-data-ownership). `Candidate` is the temporary identity anchor |
| Document number, issue date, expiry | The `documents` row. Employee Data may point at it |
| Licence and Code 95 evidence | The existing evidence or document that supports those facts. One evidence object may support more than one fact |
| Employment facts such as planned start, work system, compensation | `employment_terms.v1` on the current terms row of that Employment |
| Work authorization for this Employment | The legal process and `legal_eligibility.v1` for that Employment |

A projection may show the value. `WorkforceEmployee.display_name`, a handoff snapshot, and a work-eligibility profile are not a second owner of the person fact. `workforce_hr_verified_fields` records a confirmation. The confirmation is not the value.

This contract adds no address.

---

## Authority

Authority is the capability set a process holds over that address at this moment. The set is drawn from these verbs. A verb does not imply another verb.

| Capability | What it allows |
|---|---|
| `view` | Read the current value and its evidence |
| `create` | Write a fact that has no value yet |
| `edit` | Change an existing value |
| `verify` | Confirm the value or its evidence. The confirmation does not create a second copy of the value |
| `invalidate` | Remove trust or currency. The history of the value stays |
| `delete` | Remove the value only where policy allows physical deletion |

`edit` does not mean `verify`. `verify` does not mean `edit`. `invalidate` does not mean `delete`.

A process may hold any subset, including an empty subset. Two processes may hold different subsets of the same fact at the same time. Recruitment may keep `view` after HR receives `view` and `edit`. Legal may hold `view` and `verify` on citizenship and hold no capability on compensation. Payroll may hold `view` on compensation and on identity and hold no `edit` on citizenship.

The cells below show the shape of that reading. They are not an assignment. A later policy assigns the set for a fact and a transition. This contract does not.

| Fact | Canonical owner | Recruitment | HR | Legal | Payroll |
|---|---|---|---|---|---|
| `legal_name` | Person / Candidate | view, edit | view, edit | view | view |
| `citizenship` | Person / Candidate | view, edit | view, edit | view, verify | view |
| CE categories | licence evidence | view, edit, verify | view, verify | view | — |
| Code 95 | professional fact / evidence | view, verify | view, verify | view | — |
| `planned_start` | Employment Terms | view | view, edit | view | view |
| compensation | Employment Terms | view | view, edit | — | view |
| work authorization | Legal process | view | view, verify | view, edit, verify | — |

---

## Handoff

A handoff does not move a person, a card, a field, or a value.

```text
Recruitment process
→ handoff accepted
→ HR process becomes active
→ capability set is recalculated
```

The policy of that fact and of that transition decides the new set. The previous process does not lose every capability by default.

Before an accepted handoff, Recruitment may hold `citizenship` as `view` and `edit`. After it, the same value can be read as:

| Process | `citizenship` |
|---|---|
| Recruitment | `view` |
| HR | `view`, `edit` |
| Legal | `view`, `verify` |

`citizenship` itself is unchanged. The [handoff contract](handoff-contract.md) still names the stage and the accept path. This contract does not replace that path and does not make `WorkforceEmployee` the owner of the person.

---

## A fact changed after the handoff

The value has one address. A process that still holds `edit` writes that address.

If Recruitment changes `citizenship` from Ukraine to Poland, HR and Legal do not receive a copy to update. Their next read of `citizenship` is Poland.

A recorded decision becomes stale when a fresh reading of the facts it captured no longer matches its fingerprint. The decision is not repaired by copying the new value into another module. Legal Eligibility becomes not current when the chain it captured no longer matches, including a citizenship class that the new citizenship changes. Ready to Start becomes not current when that legal reading, or any of its other three readings, no longer matches. Both of those fingerprints already exist. This contract adds none.

```text
canonical fact changed → dependent decisions become stale
```

---

## Who the decision is about

A capability decision is one answer for one tuple.

```text
actor + process context + tenant + canonical fact address + capability
```

The actor is the principal attempting the operation. Process context is the process in which that attempt happens, including whether a handoff has made that process active. Tenant bounds the value. The canonical fact address is the owner named above, and for an employment-scoped fact it includes that Employment. The capability is one verb.

Two HR operators are two actors. Two companies are two tenants. The word HR is not the subject. This contract does not assign a verb to a named person, and it does not open an RBAC matrix.

---

## Canonical Fact Authority Contract Gate

**Outcome:** **PASS**.

The mechanism is sufficient. Each sentence below is an invariant of `canonical_fact_authority.v1`. None of them assigns a capability, writes a store, or authorizes enforcement.

One address serves several processes. Recruitment and HR read one `citizenship`. There is no `recruitment.citizenship` and no `hr.citizenship`.

Handoff changes authority, not ownership. Before and after the handoff the canonical address stays the same.

Capabilities are independent. `edit` does not mean `verify`. `verify` does not mean `edit`. `invalidate` does not mean `delete`.

Concurrent authority is allowed. Handoff does not have to make the previous process read-only. Policy decides.

A finished process does not freeze the value. When policy allows another process to change the fact, one value changes and dependent decisions become stale.

Evidence is not the fact. `verify` on `citizenship` does not grant `edit` or `delete` on the passport.

An employment-scoped fact does not become a person fact. `compensation` and `planned_start` belong to one Employment even when several modules display them.

Authority does not decide applicability. An HR `edit` on Code 95 does not mean this Employment requires Code 95.

A missing capability forbids the operation. The module does not create a local copy in its place.

A projection is not an owner. No UI or API DTO becomes a canonical address.

The subject of a capability decision is `actor + process context + tenant + canonical fact address + capability`.

No schema is written. No runtime module is authorized. No field-permissions subsystem is authorized. The reading of current RBAC is not opened. Feat stays locked. HostFlow v1 is not release-ready.

---

## Out of this contract

No Person table is authorized. Candidate fields are not moved. No `canonical_facts` store is authorized. Employment Terms are not rewritten. The HR Driver Operator Surface is not rewritten.

ADR-036 remains the trust-role ceiling. This gate does not enforce a field capability. A later reading may see where existing role, process, and tenant permissions already answer the tuple, and where one sensitive operation still needs its own check. That reading is not this gate. An ACL on every field is not indicated.
