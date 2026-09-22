# Hiring Stage Authority Consumption

**Status:** **Accepted** (L2 contract — Stage Authority Consumption Gate)  
**Date:** 2026-09-21  
**Trusted base:** `integration/release-product-a-b` @ `34a1db6b`  
**Related:** [`hiring-acceptance-contract.md`](hiring-acceptance-contract.md) (`hiring_acceptance.v1`) · [`../tasks/hiring-workflow-e2e.md`](../tasks/hiring-workflow-e2e.md) · [`ADR-037`](ADR-037-lifecycle-identity-canon.md) · [`../tasks/lifecycle-identity-li1-existence-guard.md`](../tasks/lifecycle-identity-li1-existence-guard.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (LI-1 stays existence owner), **INV-01** (one SoT per walk-step question), **INV-16** (HE-1 contract before this consumption). Does not rewrite L0. Does not mint a Hiring Product, a second stage registry, or a new stage machine. Not a new Hiring Product.

> This file is the **SoT** for HE-2: the stage portion of the hiring walk consumes LI-1.  
> Parent walk classification stays [hiring-acceptance-contract.md](hiring-acceptance-contract.md).  
> Machine copy: `hiring_stage_authority.v1` in `backend/app/reference/hiring_stage_authority.py`.  
> This slice does **not** implement a new Hiring Product. Not a new Hiring Product. It does **not** collapse eligibility, execute RS-7, or open min HR.

---

## Operator questions (stage phase only)

| Question | Authority | Role |
|----------|-----------|------|
| Which stages exist for this hiring path? | LI-1 `is_stage_registered` | **authority** (consumers cut over) |
| Which stage is this candidate on? | `Candidate.stage` | **authority** (occupancy; Funnel ≠ occupancy) |
| May this candidate move A→B? | Transition-order rule `forward_moves_guarded_jumps_rejected` | **authority** (stated and enforced on the hiring path) |

Requirements/docs disposition, eligibility leftovers, and transfer emit stay on [hiring_acceptance.v1](hiring-acceptance-contract.md). HE-2 does not reopen them.

---

## Existence consumption

Every **production hiring-path** existence reader asks LI-1:

```text
is_stage_registered("recruitment", "candidate", stage_key)
```

Hiring-path consumers (write + forward-guard normalize):

- `backend/app/api/v1/candidates/helpers.py`
- `backend/app/api/v1/candidates/service.py`
- `backend/app/services/candidate_doc_pipeline_guard.py`

**Leftover existence answerers stop answering this question on the hiring path.** They may remain as files (labels, Funnel configuration, tenant dictionary UI, `/stages` listing). They must not grant a writable stage identity.

| Leftover (HE-1 classification) | May still do | Must not do on hiring path |
|--------------------------------|--------------|----------------------------|
| Static `new → hired` list (`api/v1/stages.py`, `constants/stages.py`) | Labels / kanban chrome | Answer “does this stage exist?” for a candidate write |
| Tenant `candidate_stages` dictionary | Tenant dictionary CRUD | Grant occupancy or existence |
| `funnel_stages` as existence | Company Funnel **configuration** (ADR-037) | Accept a funnel-local code as a writable candidate stage |

Aliases may **point at** a registered key. They must not mint identity.

---

## Occupancy

Occupancy SoT remains **`Candidate.stage`**. Funnel row, tenant dictionary row, and static list membership are not occupancy.

An unregistered occupancy string already on the row may move **onto** a registered key (escape). It may not move onto another leftover-only code.

---

## Transition-order rule (production)

Machine id: `forward_moves_guarded_jumps_rejected`.

1. **Target existence** = LI-1 only. Empty target → 422. Unregistered / leftover-granted target → **jump**, 422 `Unknown stage`.  
2. **Occupancy** = caller’s `Candidate.stage`. HE-2 does not ask leftovers what the candidate is on.  
3. **Same** registered key: allowed.  
4. **Backward** along `TRANSITION_ORDER`: allowed.  
5. **Forward** along `TRANSITION_ORDER`: allowed as an **order** move. Existing leftover pipeline guards (documents / vacancy / contact attempts — HE-3 leftovers) continue to guard forward moves. HE-2 does not collapse those answerers and does not mint an adjacent-only stage machine.  
6. **Jump** = a write whose existence would only be granted by a leftover registry. Rejected.

`TRANSITION_ORDER` is the unique sequence of already-registered LI-1 keys used to classify forward vs back. Every key in that tuple must be `is_stage_registered`. Adding a key that is not registered is a gate fail.

---

## Architecture review (L0 — ten questions)

| # | Answer |
|---|--------|
| 1 | **Owner:** stage existence stays LI-1. Occupancy stays Candidate. Transition-order rule is a Hiring-path consumer of those two, not a new registry. Recruitment consumes; it does not mint a Hiring Product. |
| 2 | Not a new capability. Cuts HE-1 leftovers off the existence question. |
| 3 | No new adapter. Existence API remains `is_stage_registered`. |
| 4 | No HE-3 collapse, no RS-7, no min HR, no LI-2+ funnel schema, no `/meta/stages` cutover, no new stage machine, no CL8, no Catalog rewrite. |
| 5 | Tenant dictionary / Funnel / static list remain leftover configuration, not a second overlay product. |
| 6 | SoT for hiring-path existence = LI-1. SoT for occupancy = `Candidate.stage`. SoT for order = this file + `hiring_stage_authority.v1`. Parent walk SoT remains `hiring_acceptance.v1`. |
| 7 | No new event family. |
| 8 | **Requires:** HE-1 Gate PASS, LI-1 ✅. **Optional:** leftover label maps as aliases onto registered keys. |
| 9 | No new licence. |
| 10 | Public contract **additive** for hiring-path writes: funnel-local and short-list-only codes 422. No breaking Hub/Passport change. |

**INV-01:** one SoT per stage question. **INV-16:** HE-1 before this consumption.

---

## False close

Reject: documenting leftovers as “still how candidate PATCH works”; a second existence API; treating Funnel as occupancy; minting a new stage machine; deleting leftover files “while we are here”; collapsing eligibility; executing RS-7; opening min HR; `/meta/stages` cutover; LI-2 registry loader; Foundation ✅.

---

## Consequences

- HE-3 composes one eligibility decision with one operator-readable reason; leftover pipeline guards remain classified until then.  
- HE-4 walks RS-7. Feat `feat/hiring-e2e-he4-acceptance-walk` is open. Hiring E2E Acceptance Gate is **not PASS**. This stamp does not execute RS-7.  
- LI-2+ still owns Funnel UI rework and `/meta/stages` cutover.

---

## History

- 2026-09-22: **HE-4 Acceptance walk feat opened.** Active Product → **HE-4**. Hiring E2E Acceptance Gate **not PASS**. Not a change to this stage-authority contract. min HR remains queued.
- 2026-09-21: Stage Authority Consumption Gate **PASS**. Hiring-path existence consumes LI-1. Occupancy stays `Candidate.stage`. Transition-order rule `forward_moves_guarded_jumps_rejected` is production. Active Product → **HE-2**. HE-3 feat locked. min HR remains queued.
