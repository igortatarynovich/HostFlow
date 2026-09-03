# ADR-041: Verified self-service signup (SignupIntent → Tenant trial)

**Status:** Accepted (canon sealed; runtime not started)
**Date:** 2026-09-03
**Trusted base:** `integration/release-product-a-b`
**Does not supersede:** [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md) · [`ADR-034`](ADR-034-self-service-public-funnels.md) · [`ADR-036`](ADR-036-four-trust-roles-rbac.md) · [`ADR-039`](ADR-039-tenant-data-lifecycle.md)
**Related:** [`../plans-matrix.md`](../plans-matrix.md) · [`../journeys/self-service-success-path.md`](../journeys/self-service-success-path.md) · [`../own-company-model.md`](../own-company-model.md) · [`../modules/tenants.md`](../modules/tenants.md) · [`verified-self-service-signup.md`](../../security/threat-models/verified-self-service-signup.md) · [`hostflow-v1-release-goal.md`](../gates/hostflow-v1-release-goal.md)

**L0 checklist:** No new L0 P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-01** (Auth public contract as the only Growth tenant-create adapter), **P-02** (Users / Roles / Permissions owns identity; Tenant Lifecycle owns Provision; Finance does not own trial clocks), **P-03** (composes existing Tenant + OwnCompany + TenantLicense; no second signup capability), **P-04/P-05** (no new settings dump; trial knobs stay on existing license/billing surfaces). **INV-01** (one SoT per concern), **INV-04** (business modules do not own signup), **INV-05** (SignupIntent table is not a public API), **INV-07** (no second magic-link or trial engine), **INV-16** (convenience of a one-shot `/register` does not outrank verified identity), **INV-17** (this slice does not add a business-module SMTP path). Adding Catalog prose for an existing Core area is L1 application of L0, not a constitution rewrite.

**(1)** Owner = Platform Users / Roles / Permissions for identity + tokens; Platform Tenant Lifecycle (**ADR-039 Provision**) for the atomic create; Security owner co-signs the public surface. **(2)** No new Catalog capability — SignupIntent is a pre-tenant persistence artifact, not a Passport. **(3)** Delivery via a **Stable** Auth public contract (`intent` → `verify` → `complete` → `resend`). **(4)** Does not push recruitment/HR/billing behavior into System Layer. **(5)** No duplicate trial settings: `Tenant.status=trial` and `TenantLicense.plan=trial` remain the only trial authority ([`plans-matrix.md`](../plans-matrix.md)). **(6)** SoT: User email identity stays `users.email`; trial stays TenantLicense; operating company stays OwnCompany. **(7)** Security events via `emit_security_event_v1` only; new `event_type` values require a **taxonomy PR** before runtime ([`security-events-governance.md`](../../security/security-events-governance.md)). **(8)** Requires: existing password-reset token pattern, Turnstile, signup rate limit, Country Registry (country code), OwnCompany bootstrap. **(9)** No new licence SKU; trial is not `trial_full` and is not a paid plan_code. **(10)** Public contract change is **breaking after cutover**: Growth must not keep `POST /api/v1/auth/register` as a second tenant-create path.

---

## Context

Today Growth signup is a single `POST /api/v1/auth/register`: email + password + workspace name + consents create User + Tenant + `TenantLicense(plan=trial)` + membership `administrator` in one shot. Email is not verified. A welcome mail is best-effort and must not fail the request. Trial clocks start at that insert. The SPA then logs the user in and sends them to `/app/platform/setup` for company identity ([ADR-034](ADR-034-self-service-public-funnels.md)).

That path has three architectural defects for a B2B SaaS:

1. Unverified email becomes a User and a Tenant. Abandoned and bot signups pollute identity and billing boundaries.
2. The 30-day trial is bound to the moment of form submit, so a buyer who verifies later (once verification exists) would burn calendar days before first use.
3. Identity, workspace, operating company, and entitlement are collapsed into one handler, which makes invite-join, trial reuse, and post-trial login policy harder to keep consistent.

HostFlow already has the right *authorities* once a tenant exists: trial is a **tenant** entitlement (`TenantLicense.plan=trial`, `Tenant.status=trial`), invited users join an existing tenant, and expiry must not lock login ([`plans-matrix.md`](../plans-matrix.md) §6, `billing_restrictions`). What is missing is a pre-tenant identity object and a public contract that creates the tenant only after a verified email and a completed registration.

This ADR seals that contract. It does not start runtime.

---

## Decision

### 1. Slice boundary (hard)

This is a **platform Auth / Provision slice**. It owns only:

| In | Out |
|----|-----|
| Pre-tenant `SignupIntent` | Candidate / public `magic_links` |
| Public contract `intent` → `verify` → `complete` → `resend` | Stripe Checkout / self-service Billing (v1 later) |
| Atomic create: User + Tenant + membership(`administrator`) + `TenantLicense(plan=trial)` + first OwnCompany | Long onboarding (phone, NIP/VAT, headcount, industry, traffic source, Meta, invites) |
| Trial clock start **on successful complete** | Starting trial on email submit or on verify |
| Cutover: Growth has **one** public tenant-create path | Keeping `POST /api/v1/auth/register` as a parallel Growth path after cutover |
| Invite-accept continues to join an existing tenant | Invite creating a tenant or a second trial |

Operator-assisted provision (`POST /api/v1/platform/tenants`) remains ADR-039 Provision and is **not** this Growth path.

Passwordless / Google / Microsoft identity providers are **later**. MVP complete requires a password. They must attach to the same User, not invent a second signup pipeline.

### 2. Four objects stay distinct

```text
SignupIntent  ≠  User  ≠  Tenant  ≠  TenantLicense/trial  ≠  OwnCompany
```

| Object | Role | When it exists |
|--------|------|----------------|
| **SignupIntent** | Pre-tenant registration draft | Email submit |
| **User** | Login identity (`users.email` globally unique) | Successful complete |
| **Tenant** | Workspace / billing boundary (ADR-003) | Same commit as User |
| **Membership** | Trust role `administrator` (ADR-036; `owner` is an alias, not a stored role) | Same commit |
| **TenantLicense** | Entitlement SoT; `plan=trial`, `expires_at = date(now)+30` | Same commit; **this** is trial start |
| **OwnCompany** | Operating company (not billing) | Same commit (name + country) |

`Tenant.status=trial` is set in that same commit. It is a tenant access flag, **not** a SignupIntent state and **not** a User flag (`is_trial` is forbidden).

Do not invent `plan=trial_full`. Feature gates already treat `plan=trial` as Team-tier with trial caps ([`plans-matrix.md`](../plans-matrix.md)).

### 3. SignupIntent (pre-tenant)

SignupIntent is a **GLOBAL / platform** row. It **must not** have `tenant_id`. It is not a CRM entity, not RLS-tenant-scoped, and not a User.

This is the same class of exception as `password_reset_tokens`: platform identity state before (or beside) a tenant session. Access is only by high-entropy token (hashed) or by an opaque registration session bound to the intent. Superadmin inspection is an elevated path, not a tenant API.

**Intent states (only these):**

| State | Meaning |
|-------|---------|
| `EMAIL_SUBMITTED` | Email accepted; verification token outstanding |
| `EMAIL_VERIFIED` | Email proved; User/Tenant/trial **do not** exist yet |
| `ACCOUNT_CREATED` | Atomic complete succeeded; intent is terminal |
| `EXPIRED` | Abandoned intent (cleanup TTL, not the 30–60 minute link TTL) |
| `CANCELLED` | User or operator abort |
| `BLOCKED` | Abuse / security hold |

`REGISTRATION_IN_PROGRESS` is **not** a stored state: `EMAIL_VERIFIED` without `ACCOUNT_CREATED` is in-progress. `TRIAL_ACTIVE` is **not** an intent state: it is TenantLicense / `Tenant.status`.

**Token rules:**

- Store **hash only** (same pattern as `password_reset_tokens`).
- High entropy; one-time; TTL **30–60 minutes**.
- Resend **invalidates** the previous token and issues a new hash. Intent state does not reset to a new email.
- Expired **link** does not require re-typing email: show “link expired → send a new one” for the same intent.
- Intent-level `EXPIRED` is a longer abandoned-intent TTL (runtime may choose 7–30 days) for cleanup. After that the buyer submits email again.

**One open intent per normalized email.** Normalized email = trim + lowercase. A new intent for the same email while `EMAIL_SUBMITTED` or `EMAIL_VERIFIED` reuses or replaces the open row; it must not create two completable intents.

### 4. Public contract

Canonical Growth API (names are the contract; URL prefix stays `/api/v1/auth`):

| Operation | Responsibility |
|-----------|----------------|
| `POST .../signup/intent` | Email + terms/privacy + Turnstile. Always the same success envelope. Creates/reuses SignupIntent. Sends mail. **Does not** create User/Tenant/License. |
| `GET .../signup/verify` | Consumes one-time token. On success: `EMAIL_VERIFIED` + short-lived **registration session**. **Does not** create User/Tenant/License and **does not** start trial. |
| `POST .../signup/complete` | Requires registration session. Body: given name / family name (or full name), password, company name, country code, optional workspace label. **Only** this operation may reach `ACCOUNT_CREATED`. |
| `POST .../signup/resend` | Rate-limited. Rotates token. Same enumeration-safe envelope as intent. |

Frontend Growth entry remains `/signup` (ADR-034). After cutover it is email-first, then check-email, then complete. `/signup?plan=` may still carry a **preferred paid plan** for post-trial UX; it must not create a paid license at complete and must not skip verification.

**Registration session** (after verify, before complete):

- Opaque, bound to `SignupIntent.id`, not a tenant JWT.
- HttpOnly + Secure + SameSite; not usable as application auth.
- TTL aligned with the verification window (30–60 minutes).
- Expiry while `EMAIL_VERIFIED`: resend a new link; do not complete from email knowledge alone.
- Must not become the logged-in app session. Complete mints the normal Auth session.

**Mandatory complete fields (only):**

- Name (given + family, or one `full_name` equivalent)
- Password (MVP)
- Company name → first **OwnCompany** (and Tenant display name / workspace label may copy it)
- Country → OwnCompany country via **Platform Reference Country Registry** (no local country dictionary)
- Consents: terms + privacy **must** be true before `ACCOUNT_CREATED` (collected at intent; complete may reaffirm, not skip)

Optional later (in-app readiness, not complete): phone, NIP/VAT, size, industry, source, activity / `business_type`, Meta, invites.

Tenant `type` stays today’s self-service default (`agency`) unless a later ADR changes it. This slice does not add a type picker.

Country and company on complete **satisfy** ADR-034’s short company-identity form. After a successful complete, `/app/platform/setup` is not a second mandatory identity gate. It remains a **fallback** only if OwnCompany is missing (legacy/incomplete rows).

### 5. Atomic complete (the only create)

`ACCOUNT_CREATED` is reached **only** after a single successful database commit that inserts:

1. User (`email` verified, `password_hash`, `role=administrator`, `preferences={}`)
2. Tenant (`status=trial`, workspace label)
3. `user_memberships` role `administrator`
4. `TenantLicense` `plan=trial`, `expires_at` from `now()` + 30 days, Team-equivalent trial caps already defined in plans-matrix / current trial license defaults
5. First OwnCompany (name + country)

Then, and only then:

- `trial_started_at` conceptually = commit time (persisted as license `expires_at` and existing billing subscription fields; do not add a parallel trial table)
- Intent → `ACCOUNT_CREATED`
- App session issued; buyer lands in the product readiness UI (ADR-034), not an 8-step wizard

Failure of any insert rolls back **all**. Partial User-without-Tenant or Tenant-without-license is a defect.

Complete is **idempotent** for the same verified intent: a second complete after `ACCOUNT_CREATED` returns the existing account (or a safe “already created, log in”) and must not mint a second tenant or a second trial.

Concurrent completes take a row lock on the intent (or equivalent unique constraint) so only one commit wins.

### 6. Email collisions: existing User vs pending invite

`users.email` remains **globally unique**.

| Situation at intent / resend / verify / complete | Required behavior |
|--------------------------------------------------|-------------------|
| No User, no pending invite | Normal verification → complete → new tenant + trial |
| User already exists | Enumeration-safe HTTP envelope. Mail is “you already have an account” / login or reset. **No** new Tenant, **no** new trial |
| Pending `UserInvite` for that email | Enumeration-safe HTTP envelope. Mail is join/invite, not create-workspace. Complete **must not** create a tenant. Invite-accept remains the join path |
| Both User and invite | Join/login path; never a second trial |

Invite-accept **never** creates a Tenant or a `TenantLicense(plan=trial)`. Invited users consume the existing tenant entitlement.

### 7. Enumeration and abuse (normative)

- Intent and resend **must not** reveal whether the email is new, registered, invited, or blocked. Same status/shape (and no distinguishable error body).
- Timing should not be an oracle; work that differs by case belongs after the response (mail job).
- Turnstile + existing signup rate limit on intent and resend. Complete is gated by registration session + rate limit (password brute force).
- Verification tokens never logged in plaintext; CLASS 2 email in security events is redacted per canon.
- Domain-level “one trial per company” beyond unique email is **not** this slice. Public mailbox domains must not be blocked. A later policy may use non-public domain + billing identity (NIP / Stripe customer). Residual: see threat model SI-12.

### 8. Cutover of `POST /api/v1/auth/register`

Until runtime cutover, the current handler is the **legacy** Growth path and is known-inconsistent with this ADR.

After cutover:

- Growth has exactly one public tenant-create: `signup/complete`.
- `POST /api/v1/auth/register` is **retired** as a public path (410 or removed). It must not remain as a verification bypass.
- Enforcement: contract tests + a guard that no other unauthenticated route creates Tenant + trial license.
- Superadmin / operator provision is unchanged.

Shipping intent/verify while still exposing the old register as a working Growth CTA is a **process fail** for this slice.

### 9. Mail

Verification mail is a **platform identity message**, the same class as password-reset. It:

- does not create a business-module Communications thread;
- does not add SMTP inside Recruitment/Sales/HR;
- reuses the platform system-email channel already used by password reset / welcome;
- is not a Catalog Notifications rewrite.

INV-17 is not waived for modules. Aligning platform system mail with the Communication Pipeline is **out of this slice** (same residual as password-reset).

Welcome-to-trial mail, if any, is sent **after** complete, not after verify.

### 10. Sealed invariants

These are defects if a runtime PR violates them:

1. **SignupIntent has no `tenant_id`.**
2. **`EMAIL_VERIFIED` does not create User or Tenant and does not start trial.**
3. **`ACCOUNT_CREATED` is reached only after the atomic commit in §5.**
4. **Invite-path never creates a new Tenant or a new trial.**
5. **Intent/resend do not enumerate emails.**
6. **Verification token is stored as hash only, is one-time, and is invalidated by resend.**
7. **`Tenant.status=trial` and `TenantLicense.plan=trial` are the only trial authority.** No User-level trial flag; no `trial_full` plan_code; no second entitlement table for this slice.
8. **`administrator` is the only starting tenant trust role** (ADR-036). Do not persist `owner`.
9. **OwnCompany ≠ Tenant.** Trial/billing belong to Tenant; name/country of the firm belong to OwnCompany. Complete may copy the company name onto Tenant display fields; it must not treat Tenant as the operating-data owner.
10. **After cutover, legacy `/auth/register` is not a second public tenant-create.**

### 11. Enforcement (Rule 7)

| Rule | Enforcement (runtime slice, not this PR) |
|------|------------------------------------------|
| No User/Tenant on intent/verify | Tests: intent/verify leave `users` / `tenants` / `tenant_licenses` unchanged |
| Trial clock = complete commit | Tests: license `expires_at` unset until complete; then `now+30d` |
| Token hash / one-time / resend rotate | Tests: plaintext absent; replay 410/401; resend invalidates old |
| Enumeration | Tests: unknown / existing / invited emails share envelope |
| Invite does not trial | Tests: accept-invite creates no TenantLicense trial row |
| Single public create path after cutover | Tests + guard: unauthenticated tenant+trial create only via complete |
| Concurrent complete | Unique email + intent row lock; one tenant |
| Atomicity | Transaction test: forced failure leaves zero of the five objects |
| Role | Complete membership role is `administrator` |
| Country | Country code from Platform Reference; no new dictionary table |
| Security telemetry | Taxonomy PR, then `emit_security_event_v1` on intent/verify/complete/resend/deny |

Runtime order after this docs seal (normative sequence, not scheduled here):

1. Persistence (SignupIntent)
2. API contract + enforcement (rate limit, Turnstile, token hash)
3. Atomic completion
4. Mail delivery
5. Frontend cutover (`/signup` email-first)
6. Retirement of public `/auth/register`
7. Tests listed above

Do not start (5) or (6) before (3). Do not leave (6) undone if (5) is the live Growth CTA.

---

## Consequences

**Positive.** Verified email before workspace. Trial days are product days. Bots and abandoned emails stay off `users` / `tenants`. Invite and self-serve stay separate. ADR-034 Success Path gets lighter (`email → mail → short complete → app`). Existing trial gates, post-trial login, and TenantLicense remain SoT.

**Negative / cost.** Extra round-trip and mail dependency. Registration session is a new public-cookie surface (threat model). Cutover must kill the old register or the ADR is fiction. Domain-level trial farming is only partly mitigated (unique email).

**Security perimeter.** Public unauthenticated routes, tokens in email, session cookies. Implementing PRs are S0 and must attach [`security-review-checklist.md`](../../security/security-review-checklist.md) plus [`threat-models/verified-self-service-signup.md`](../../security/threat-models/verified-self-service-signup.md).

**Not decided here.** Exact abandoned-intent cleanup TTL; mail vendor; passwordless/OAuth; domain-join UX; Stripe checkout; changing default `Tenant.type`; moving platform system mail onto the Communication Pipeline.

---

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| Keep one-shot `/register` and add verification later | User/Tenant already exist; trial already ticking; contradicts §10 |
| Start trial at verify | Buyer can confirm email and disappear; burns trial without product use |
| Create User at verify, Tenant at complete | Pollutes `users` with unverified-completion drop-off; collides with global unique email and invites |
| Reuse candidate `magic_links` | Different trust boundary, tenant-scoped, CLASS 2/3 candidate PII ([`candidate-portal.md`](../../security/threat-models/candidate-portal.md)) |
| `is_trial` on User or `plan=trial_full` | Splits entitlement SoT from TenantLicense / plans-matrix |
| Persist role `owner` | Violates ADR-036; `owner` is an alias of `administrator` |
| Collect NIP/size/industry before first product screen | Violates ADR-034 (no 8-step wizard; identity form stays short) |
| New Catalog capability “Signup” | INV-07 / P-03 — this is Auth + Provision, not a new Owns |
| Leave old `/register` live “for API clients” after SPA cutover | Second public trial mint; threat SI-13 |

---

## Ownership card (Rule 3)

This slice does **not** create a new domain. It specifies how existing domains are used on the public Growth path.

| Field | Value |
|-------|-------|
| **Domain** | Users / Roles / Permissions (identity + SignupIntent) composing Tenant Data Lifecycle **Provision** |
| **Owner** | Platform identity / Auth owner; Tenant Lifecycle owner for the atomic create; Security owner co-signs |
| **Source of truth** | This ADR for the Growth signup contract; ADR-036 for roles; ADR-039 for provision verbs; plans-matrix for trial entitlements; OwnCompany model for the firm |
| **Consumers** | Growth `/signup` (ADR-034), login, billing banners, invite-accept, superadmin provision (not a consumer of SignupIntent) |
| **Delivery contract** | Auth public contract in §4 (**Stable** after runtime seal) |
| **Versioning** | Additive fields on complete are allowed if optional; removing verification or reopening `/register` requires an ADR amendment |
| **Override policy** | Superadmin provision may create tenants without SignupIntent; it must not be callable as Growth self-service |
| **Enforcement** | §11 |

---

## Cross-references

- Funnel IA: [`ADR-034`](ADR-034-self-service-public-funnels.md) (Growth still ends at `/signup`; this ADR owns what `/signup` does)
- Journey: [`self-service-success-path.md`](../journeys/self-service-success-path.md)
- Tenant vs Company: [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md)
- Provision verb: [`ADR-039`](ADR-039-tenant-data-lifecycle.md)
- Trust roles: [`ADR-036`](ADR-036-four-trust-roles-rbac.md)
- Trial entitlements: [`plans-matrix.md`](../plans-matrix.md)
- OwnCompany: [`own-company-model.md`](../own-company-model.md)
- Catalog: [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)
- Domain map: [`hostflow-core-domain-map-v1.md`](hostflow-core-domain-map-v1.md)
- Threat model: [`verified-self-service-signup.md`](../../security/threat-models/verified-self-service-signup.md)
- v1 Billing: self-service checkout remains later ([`hostflow-v1-release-goal.md`](../gates/hostflow-v1-release-goal.md))

---

## History

- 2026-09-03: Accepted (canon sealed; runtime not started). SignupIntent pre-tenant; trial starts only on atomic complete; legacy `/auth/register` retired at cutover; candidate magic links, Billing checkout, and long onboarding out of slice.
