# ADR-022 Review Checklist

**ADR:** [ADR-022-intake-form-purpose-and-submission-policy-model.md](ADR-022-intake-form-purpose-and-submission-policy-model.md)  
**Status:** Proposed  
**Date:** 2026-07-15  
**PR:** backend foundation slice — [adr022-phase1-backend-pr-description.md](../tasks/adr022-phase1-backend-pr-description.md)

---

## Sign-off scope by role

| Role | Sign-off scope | Applies to |
|------|----------------|------------|
| **Architecture** | Model, component ownership, ADR consistency, no architectural drift | Backend PR merge |
| **Product** | Purpose/policy semantics, user scenarios, `match_or_create` behaviour, expected release flow | Backend PR merge (semantics only) |
| **Engineering** | Migration, concurrency, tests, reuse audit, no regression in candidate intake | Backend PR merge |
| **Security** | Tenant isolation, tokens, matching exposure | Backend PR merge |

Product **does not** sign off engineering implementation details (e.g. `SELECT FOR UPDATE`, migration DDL).  
Product **does** sign off that semantics and scenarios match ADR intent.

Full browser walkthrough (A/B/C) is **release gate** — after UI/publication slice, not backend PR merge.

---

## Architecture review

- [ ] **§2 Three axes:** Purpose, Target Entity Profile, Submission Policy are mandatory and orthogonal to Presentation
- [ ] **§2.1 Purpose ≠ outcome:** Purpose does not silently create Application; Policy determines behaviour
- [ ] **§3 Policy modes:** v1 enum set (`create`, `match_or_create`, `attach`, `review`, `ignore`, `notify`) accepted
- [ ] **§3.1 Review vs Application:** `review` creates Review Queue Item without domain Application; distinct from `lifecycle_status=new`
- [ ] **§4 Match Policy:** Matches Application projection, not ClientAccount/Candidate directly
- [ ] **§4.3 Three outcomes:** zero → create; strong single → attach; ambiguous → no auto-attach
- [ ] **§4.4 Match Matrix:** Product B auto-attach conditions accepted
- [ ] **§5 Publication / Invite:** Form default policy; Publication binds version + attribution; Invite forces attach
- [ ] **§5.5 Component ownership:** Reuse-first audit accepted; no second routing engine
- [ ] **§6 Versioning:** Published version immutable (design); Phase 1 honesty acknowledged
- [ ] **§7 Entity Profile:** Validates allowed purpose/policy combinations; form cannot set incompatible route_intent

## Product review (semantics — backend PR)

- [ ] Public acquisition default is `match_or_create`, not hard `create`
- [ ] Personal invite remains `attach` with known Application
- [ ] Scenario semantics A/B/C (§6 PR description) match product intent
- [ ] Expected release flow: backend foundation → UI slice → browser walkthrough
- [ ] Operator Submission attribution requirements understood for **release gate** (UI slice)

## Engineering review (backend PR)

- [ ] Phase 1 feasible on Lead transport + `submissions_v1[]` without `applications` table
- [ ] No breaking change to recruitment candidate intake in Phase 1 slice
- [ ] Migration `202607151000_adr022_form_purpose` roundtrip safe
- [ ] P1 fixes: gate, shared normalization, strict matcher, idempotent append, PATCH guard, abandoned isolation
- [ ] Backend contract scenarios A/B/C covered by API tests
- [ ] Effective policy resolver testable in isolation
- [ ] Reuse audit: Decision Layer / Outcome Executor / IntakeRouter not duplicated

## Security review

- [ ] Tenant isolation on Form Definition, Publication, Submission
- [ ] Invite token cannot attach to cross-tenant Application
- [ ] Match query scoped by tenant_id
- [ ] Policy snapshot stored on Submission prevents retroactive behaviour change

## Cross-ADR consistency

- [ ] Consistent with ADR-021 Application / Submission separation
- [ ] Consistent with ADR-007 publication bridge (extends, does not replace)
- [ ] ADR-021 §2.1 match ≠ merge respected in Match Policy

## Approval (backend PR merge gate)

| Role | Name | Date | Approved |
|------|------|------|----------|
| Architecture | | | ☐ |
| Product | | | ☐ |
| Engineering | | | ☐ |
| Security | | | ☐ |

**After sign-off:** set ADR-022 Status to **Accepted (L1)**, verify the already-implemented backend slice matches the accepted contract, and allow merge when the [backend merge gate](../tasks/adr022-phase1-backend-pr-description.md#8-merge-gate) is satisfied.

**Product UI acceptance** (full A/B/C browser walkthrough) is a separate **capability release gate** — see PR description §8.
