# ADR-022 Review Checklist

**ADR:** [ADR-022-intake-form-purpose-and-submission-policy-model.md](ADR-022-intake-form-purpose-and-submission-policy-model.md)  
**Status:** Accepted  
**Date:** 2026-07-15  
**Accepted:** 2026-09-20 — FP-1 Forms Publish Contract Gate (U-2). Phase 1 backend already on the trusted base. Purpose / Policy / Match Matrix were **not** rewritten.  
**PR:** backend foundation slice — [adr022-phase1-backend-pr-description.md](../tasks/adr022-phase1-backend-pr-description.md) · accept — [forms-publish-contract.md](forms-publish-contract.md)

---

## Sign-off scope by role

| Role | Sign-off scope | Applies to |
|------|----------------|------------|
| **Architecture** | Model, component ownership, ADR consistency, no architectural drift | Backend PR merge; FP-1 accept |
| **Product** | Purpose/policy semantics, user scenarios, `match_or_create` behaviour, expected release flow | Backend PR merge (semantics only); FP-1 accept |
| **Engineering** | Migration, concurrency, tests, reuse audit, no regression in candidate intake | Backend PR merge (already shipped) |
| **Security** | Tenant isolation, tokens, matching exposure | Backend PR merge (already shipped) |

Product **does not** sign off engineering implementation details (e.g. `SELECT FOR UPDATE`, migration DDL).  
Product **does** sign off that semantics and scenarios match ADR intent.

Full browser walkthrough (A/B/C) is **release gate** — after UI/publication slice (FP-4 / FP-5), not this accept.

---

## Architecture review

- [x] **§2 Three axes:** Purpose, Target Entity Profile, Submission Policy are mandatory and orthogonal to Presentation
- [x] **§2.1 Purpose ≠ outcome:** Purpose does not silently create Application; Policy determines behaviour
- [x] **§3 Policy modes:** v1 enum set (`create`, `match_or_create`, `attach`, `review`, `ignore`, `notify`) accepted
- [x] **§3.1 Review vs Application:** `review` creates Review Queue Item without domain Application; distinct from `lifecycle_status=new`
- [x] **§4 Match Policy:** Matches Application projection, not ClientAccount/Candidate directly
- [x] **§4.3 Three outcomes:** zero → create; strong single → attach; ambiguous → no auto-attach
- [x] **§4.4 Match Matrix:** Product B auto-attach conditions accepted
- [x] **§5 Publication / Invite:** Form default policy; Publication binds version + attribution; Invite forces attach
- [x] **§5.5 Component ownership:** Reuse-first audit accepted; no second routing engine
- [x] **§5.2 Publication contract:** one Form → many Publications; attribution scales to multi-channel ops
- [x] **§6 Versioning:** Published version immutable; publish definition sealed by [forms-publish-contract.md](forms-publish-contract.md) (`forms_publish.v1`); operator route is FP-2
- [x] **Multi-form scalability (PR §9):** dozens of forms/publications per tenant — model yes; Phase 1 ops gaps explicit
- [x] **§7 Entity Profile:** Validates allowed purpose/policy combinations; form cannot set incompatible route_intent

## Product review (semantics — backend PR)

- [x] Public acquisition default is `match_or_create`, not hard `create`
- [x] Personal invite remains `attach` with known Application
- [x] Scenario semantics A/B/C (§6 PR description) match product intent
- [x] Expected release flow: backend foundation → UI slice → browser walkthrough
- [ ] Operator Submission attribution requirements understood for **release gate** (UI slice — FP-4 / FP-5)

## Engineering review (backend PR)

- [x] Phase 1 feasible on Lead transport + `submissions_v1[]` without `applications` table
- [x] No breaking change to recruitment candidate intake in Phase 1 slice
- [x] Migration `202607151000_adr022_form_purpose` roundtrip safe
- [x] P1 fixes: gate, shared normalization, strict matcher, idempotent append, PATCH guard, abandoned isolation
- [x] Backend contract scenarios A/B/C covered by API tests
- [x] Effective policy resolver testable in isolation
- [x] Reuse audit: Decision Layer / Outcome Executor / IntakeRouter not duplicated

## Security review

- [x] Tenant isolation on Form Definition, Publication, Submission
- [x] Invite token cannot attach to cross-tenant Application
- [x] Match query scoped by tenant_id
- [x] Policy snapshot stored on Submission prevents retroactive behaviour change

## Cross-ADR consistency

- [x] Consistent with ADR-021 Application / Submission separation
- [x] Consistent with ADR-007 publication bridge (extends, does not replace)
- [x] ADR-021 §2.1 match ≠ merge respected in Match Policy

## Approval (backend PR merge gate)

| Role | Name | Date | Approved |
|------|------|------|----------|
| Architecture | FP-1 contract seal (U-2) | 2026-09-20 | ☑ |
| Product | FP-1 contract seal (U-2) | 2026-09-20 | ☑ |
| Engineering | Phase 1 backend already on trusted base | 2026-09-20 | ☑ |
| Security | Phase 1 isolation already on trusted base | 2026-09-20 | ☑ |

**After sign-off:** ADR-022 Status is **Accepted (L1)**. Publish definition SoT is [forms-publish-contract.md](forms-publish-contract.md). This accept did **not** expand Purpose / Policy / Match Matrix.

**Product UI acceptance** (full A/B/C browser walkthrough) remains a separate **capability release gate** — FP-4 / FP-5, not this PR.
