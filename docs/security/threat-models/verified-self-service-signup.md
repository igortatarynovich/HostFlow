# Threat Model — Verified self-service signup (ADR-041)

**Surface:** public Growth Auth — SignupIntent, verification links, registration session, atomic tenant provision, cutover of `POST /api/v1/auth/register`.
**Parent ADR:** [`docs/specs/architecture/ADR-041-verified-self-service-signup.md`](../../specs/architecture/ADR-041-verified-self-service-signup.md)
**Related:** [`public-links.md`](./public-links.md) · [`candidate-portal.md`](./candidate-portal.md) (do **not** reuse) · [`rbac-trust-roles.md`](./rbac-trust-roles.md) · [`interactive-demo.md`](./interactive-demo.md) · [`security-events-governance.md`](../security-events-governance.md)

**Status:** Contract Seal DONE (ADR-041 Accepted); runtime **NOT STARTED**. Deepen this file in the same PR that starts runtime; do not reopen the signup boundary for a new design round.

Runtime of this surface is a **security-perimeter** change (unauthenticated routes, email tokens, cookies). **STOP** on Adapter/UI without this model, rate limits, Turnstile, hashed one-time tokens, and `emit_security_event_v1` taxonomy for intent / verify / complete / resend / deny. Taxonomy PR is the **first** runtime step.

Candidate `magic_links`, password-reset tokens, and invite tokens are **adjacent** surfaces. They must not share tables, cookies, or token namespaces with SignupIntent.

## Assets

- SignupIntent rows (email, state, consent timestamps) — pre-tenant, CLASS 2
- Verification token (email URL) — secret, short TTL
- Registration session cookie — secret, short TTL, not an app JWT
- Password at complete — CLASS 2/3 credential
- Created User, Tenant, membership, TenantLicense, OwnCompany
- Trial entitlement (30-day full Team-tier window)
- Mail contents (verification URL)

## Trust boundaries

- Anonymous internet → `intent` / `resend` / `verify`
- Email channel (forwarding, shared inboxes, logs, referrers)
- Browser holding the registration session (XSS, extensions, CSRF)
- Verified-but-not-completed registrant → `complete` (password + company)
- Existing User / pending invite vs new buyer (must not leak which)
- Invite-accept (authenticated join) vs Growth complete (new tenant)
- Superadmin provision vs Growth self-service
- Legacy `POST /auth/register` until retired **in the same cutover** as the new flow (bypass if left live)

SignupIntent is **not** inside tenant RLS. Compromise of the platform DB exposes all open intents. Treat as platform-secret storage: hash tokens, minimise TTL, restrict superadmin read + audit.

## Threats

| ID | Threat | Vector |
|----|--------|--------|
| SI-1 | Email enumeration | Distinct HTTP status/body/timing on intent or resend for unknown vs registered vs invited vs blocked |
| SI-2 | Token theft | Verification URL in email, Referer, proxy logs, analytics, screenshots |
| SI-3 | Token replay | Reuse of a consumed or rotated token to mint another session or complete twice |
| SI-4 | Resend abuse | Flood victim inbox; use resend as oracle; keep old tokens valid |
| SI-5 | Turnstile bypass | Intent/resend without captcha when enabled; bot farms creating intents |
| SI-6 | Concurrent complete | Two parallel completes on one verified intent → two Tenants / two trials |
| SI-7 | Duplicate intent race | Two open intents for one email both completable |
| SI-8 | Existing User takeover | Complete creates a second User or resets password because intent ignored `users.email` |
| SI-9 | Pending invite bypass | Complete creates a **new** tenant/trial instead of joining the invited tenant |
| SI-10 | CSRF / session fixation | Attacker-fixed registration cookie; CSRF on complete from another origin; registration session accepted as app JWT |
| SI-11 | Password brute force | Unbounded complete attempts on a stolen/valid registration session |
| SI-12 | Trial farming | New emails / old `/register` / verify-without-complete clocks / User-level trial flags to stack 30-day windows |
| SI-13 | Legacy register bypass | After SPA cutover, `POST /auth/register` still creates Tenant+trial without verification |
| SI-14 | Privilege at birth | Complete persists `owner` / `superadmin` / `employee` instead of `administrator` |
| SI-15 | Pre-tenant data leak | Listing intents by email; verify returning whether User exists; logs with plaintext token |
| SI-16 | Mail / open redirect | Verification link host not bound to `FRONTEND_URL`; token in query copied to third-party scripts |

## Controls (baseline — required before runtime)

**Enumeration (SI-1, SI-15).** Intent and resend always return the same success envelope. Branching (existing User, pending invite, new intent) happens in the mail job. Tests cover unknown / registered / invited emails.

**Tokens (SI-2, SI-3, SI-4, SI-16).** Hash at rest; one-time; 30–60 minute TTL; resend invalidates previous hash; consumed token cannot mint a second registration session. Link host allowlisted to the configured frontend origin. Do not put tokens in client-side analytics. Replay → fail closed (401/410), no new session.

**Abuse (SI-4, SI-5, SI-11).** Turnstile on intent and resend when enabled. Existing `auth:signup` rate limit applies to intent, resend, and complete. Password policy unchanged (min length already on register). Lock or slow down complete after N failures per intent.

**Atomicity (SI-6, SI-7, RG-2).** One open intent per normalized email (unique partial index or equivalent). Complete: `SELECT … FOR UPDATE` (or equivalent) on the intent row; unique `users.email`; single transaction for the five objects. A **retry of the same valid registration session** after commit may return the created account. Complete keyed only by `intent_id` without that session **must not** mint a JWT.

**Identity collisions (SI-8, SI-9, RG-3).** Existing User → no Tenant create. Applicable pending invite = Users **`UserInvite` authority only** (revoked/accepted/expiry predicates the invite owner already uses). Signup consumes that read; it does not scan questionnaire invites, candidate `magic_links`, or other invite-shaped tables. Complete refuses `ACCOUNT_CREATED` when that authority says pending. Invite-accept remains the join path.

**Session (SI-10, RG-2).** Registration session is opaque, intent-bound, HttpOnly, Secure, SameSite, not a tenant JWT, not usable on `/api/v1` business routes. Complete is SameSite-protected; if cookie auth is used, require a custom header or equivalent CSRF defense. Successful complete **replaces** the registration cookie with the normal Auth session (do not keep both). Verify must not accept an attacker-supplied session id as “already verified”. Idempotent complete is not a second way to mint JWT without proving that session.

**Trial (SI-12, SI-13, RG-1).** Trial starts only in the complete commit via `TenantLicense.plan=trial` + `Tenant.status=trial`. `expires_at` is **calendar** `date(now_utc)+30` (`Date` column). No datetime twin; gates keep reading that date through existing `billing_restrictions`. No trial on intent/verify. Frontend cutover and legacy `/register` retirement are the **same** cutover; until then the verification flow is not a security boundary. Invite-accept does not write a trial license. Domain-wide farming is residual (below).

**Birth role (SI-14).** Complete membership/user role is `administrator` only (ADR-036). Contract test.

**Telemetry.** Taxonomy PR first. Then `emit_security_event_v1` on intent created, verify success/fail, complete success/fail, resend, legacy-register deny. Redact email / token. Pre-tenant events have no `tenant_id` until complete succeeds.

**Mail.** Platform system-email path only; no module SMTP. Failure to send after a 202 must not become an enumeration oracle (same envelope).

## Residual / follow-up

- Shared corporate domains (`igor@`, `hr@` on the same non-public domain) can each take a trial until billing identity exists. Do **not** block public mailbox domains in this slice.
- Platform DB readers can see intent emails (CLASS 2). Retention/cleanup of abandoned intents is operational (intent `EXPIRED`), not a substitute for erasure (ADR-039).
- Email-channel forwarding: whoever can read the inbox can complete. Acceptable for B2B MVP; not a second factor.
- Aligning platform system mail with the Communication Pipeline (INV-17 for modules) is out of slice.
- Passwordless / OAuth later must not reopen an unverified tenant-create path.

## Tests (when runtime starts)

- Intent / verify do not insert User, Tenant, or TenantLicense
- Verify does not set license `expires_at` / trial clocks
- Complete sets `plan=trial` and calendar `expires_at = date(now_utc)+30` (`Date`), not a datetime `now+30d`
- Replay token after verify or resend → deny
- Resend invalidates the prior token
- Unknown vs existing vs invited email: identical HTTP envelope
- Existing User cannot complete a new tenant
- Pending `UserInvite` (Users authority only) cannot complete a new tenant; accept-invite creates no trial license
- Parallel complete: one tenant
- Forced mid-transaction failure: zero leftover rows of the five objects
- Registration session rejected on business APIs
- Complete without session → deny (including after `ACCOUNT_CREATED`: no JWT)
- Same registration session retry after commit may return the created result
- After **same** cutover: `POST /auth/register` does not create a tenant (410 or absent)
- Turnstile required when enabled
- Rate limit on intent/resend/complete
- Role at birth is `administrator`

## Related specs

- [`ADR-041`](../../specs/architecture/ADR-041-verified-self-service-signup.md)
- [`ADR-034`](../../specs/architecture/ADR-034-self-service-public-funnels.md)
- [`ADR-036`](../../specs/architecture/ADR-036-four-trust-roles-rbac.md)
- [`ADR-039`](../../specs/architecture/ADR-039-tenant-data-lifecycle.md)
- [`plans-matrix.md`](../../specs/plans-matrix.md)
- [`security-review-checklist.md`](../security-review-checklist.md)
- [`security-ssot.md`](../security-ssot.md)
