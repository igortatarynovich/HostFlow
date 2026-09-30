# Legal Eligibility / Requirement Policy Normalization

**Status:** **QUEUED** — not scheduled. Not Active Product.  
**Date:** 2026-09-29  
**Parents:** [Hiring workflow E2E](hiring-workflow-e2e.md) · [document policy platform pack](../platform/document-policy-platform-pack-v1.json) · [Requirement Policy Management](requirement-policy-management.md)

> Hiring E2E Acceptance Gate **PASS** does **not** prove a legal employability matrix.  
> This slice is the place that matrix is defined. It is not started here.

---

## Problem

`r5_required_set` is the requirement authority the hiring walk consumes. It branches on `residency_status` values `eu_citizen`, `visa`, `none`, `no_residence_card`, and `card`.

The candidate card stores `poland_stay_basis` as `eu_citizen`, `visa_d`, `visa_c`, `karta_pobytu`, `waiting_for_trc`, and `other`. Only `eu_citizen` matches the pack. Two candidates on one vacancy, one with a Polish visa D and one with a residence card, therefore receive the same required set as a candidate with no stay basis.

Citizenship alone, employment country, residence-permit country and type, driving-licence issuing country, and Code 95 / qualification-card jurisdiction do not change the set. `eu_member` and `oswiadczenie_eligible` country lists are not read by the required-set path.

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**
A recruiter cannot rely on the required set to tell an EU citizen from a non-EU candidate, or a visa-D stay from a residence card, because product legal facts and the policy vocabulary are not the same model.

**Completion proof (named consumer):**
Two candidates on one vacancy, with different recorded legal facts, receive different outstanding requirements when the business rules say they must, and the same set when the rules say they must not. The required-request flow already consumes `r5_required_set`; this slice changes that set, not the request state machine.

**False close (reject):** mapping `visa_d` onto the pack token `visa` without a written rule for which document that stay basis actually requires.

## Order

1. Write the business rules: citizenship, employment country, residency/work basis, permit type, document issuing jurisdiction, and licence / Code 95 jurisdiction where the rule needs them.
2. Normalize those facts into the inputs `r5_required_set` already evaluates.
3. Only then change the pack or the engine.

Unlock does not schedule this slice. Minimal Recruitment → HR stays behind Hiring E2E program close and is not this slice.
