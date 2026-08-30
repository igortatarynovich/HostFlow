# Tenant Isolation Enforcement

**Status:** **QUEUED · disposition decided 2026-08-28 — close the gap before RC** (brief only; **not scheduled**). Gate prerequisite for RR5, counted in the [queue roll-up](sales-to-comms-sequential-queue.md#release-horizon-roll-up-the-queues-number-consumed-by-the-gate)
**Phase class:** platform
**Track:** proposed **Launch-ops** (write-set: alembic migrations, DB role provisioning, `docs/security/**`, one guard test — disjoint from the Product Track)
**Branch (docs):** `docs/v1-blocker-briefs`
**Branch (code):** none — later slices `feat/tenant-isolation-tiN-…`
**Parents:** [Release Readiness Gate](../gates/release-readiness-gate.md) **RR5** · [Security SSOT](../../security/security-ssot.md) §10 · [Unowned work register](../gates/v1-unowned-work-register.md) · [QB-1 measurement](stabilize-integration-pytest-baseline.md) · [Acceptance suite](../journeys/release-readiness-acceptance-suite.md)
**Estimate:** 7–10 slices. TI-1…TI-3 are delivered; the whole remainder is TI-4, whose size is now measured rather than assumed: 102 tables to cover, 10 application paths that write with no tenant bound, 108 tests that write for a tenant other than the one they bind, and one security-canon decision about identity lookup. Raised from 3–5 (2026-08-28) → 5–8 (policy rewrites and coverage measured) → 7–10 (2026-08-29, once the restricted role was actually connected).
**Owner:** proposed Security canon owner (decision) + Engineering lead (execution)

> The database-level tenant isolation that the security canon names as the primary control is **not in force**. Application-level filtering is doing the work alone.
> **Not** a rewrite of the access model, **not** RBAC work, **not** the superadmin model, **not** an audit-coverage programme.

---

## Original Goal → Completion Proof

**Problem this must permanently remove:**
[`security-ssot.md`](../../security/security-ssot.md) §10 states the rule without qualification: «**PostgreSQL RLS** на всех tenant-scoped таблицах; новые таблицы с `tenant_id` не мержатся без политики», and §19 sets `RLS coverage (tenant tables)` at **100%**. `AGENTS.md` repeats it as a platform invariant. Measurement contradicts all three: policies are missing on almost half of the tenant-scoped tables, and for the role the application actually connects as, the existing policies do not apply at all. Nothing in the repository provisions a role for which they would apply, and no test or CI gate measures coverage — so the gap can widen with every migration without anyone noticing.

**Completion proof (named consumer):**
**RR5 answered with evidence**, plus a guard that keeps it answered: a coverage check that fails CI when a table carrying `tenant_id` has no policy, and an isolation test that passes while connected as the **production-shaped role** (not a superuser). The two `test_tenant_isolation.py` cases below go green for the right reason — because the database refused the read, not because the ORM filtered it.

**False close (reject):** deleting or `xfail`-ing the failing isolation tests; adding policies to the 102 tables while the application role keeps `BYPASSRLS`; declaring it fixed on the strength of application-level filters; lowering the §19 KPI to match reality without a decision record; a coverage number measured once by hand instead of by a guard.

---

## Starting point (measured, not assumed)

Measured 2026-08-28 on the dev cluster (`hostflow`), schema at head `202608250002_merge_e5_drop_and_adr036_heads`.

| Fact | Value | How it was measured |
|---|---|---|
| Tables carrying `tenant_id` | **226** | `pg_attribute` join over `public` base tables |
| …of those, with RLS enabled | **124** | `pg_class.relrowsecurity` |
| …of those, **without any RLS** | **102** | same — includes `acq_campaigns`, `activity_events`, `automation_rules`, `calendar_*`, `candidate_tasks`, `candidate_permits`, `client_accounts`, `communication_*` (≈25 tables), `candidate_pipeline_overrides` |
| Policies defined | 130 | `pg_policies` |
| Tables with `FORCE ROW LEVEL SECURITY` | **0** | `pg_class.relforcerowsecurity` |
| Application role `hostflow` | **`rolsuper = true`, `rolbypassrls = true`**, and **owner of every table** | `pg_roles`, `pg_class.relowner` |
| Role provisioning in the repository | **none** | no `CREATE ROLE` / `ALTER ROLE` / `NOBYPASSRLS` / `FORCE ROW LEVEL SECURITY` anywhere in the tree |
| Migrations that touch RLS | 36 files | `backend/alembic/versions` |

**What this means, precisely.** RLS is bypassed twice over for the role the application uses: once because the role is superuser with `BYPASSRLS`, and again because a table **owner** bypasses its own policies unless `FORCE ROW LEVEL SECURITY` is set — and it is set nowhere. So even a correctly-policied table is unprotected for this role. Two of the three facts are properties of the **migration set** and therefore reproduce in any environment (the 102 uncovered tables, zero `FORCE`); the superuser/`BYPASSRLS` fact is a property of **this cluster's role**, and cannot be checked against production because no runbook or script defines how the production role is created ([runbook index](../../runbooks/README.md) — RB-1 MISSING).

**The mechanism itself is real and correctly wired.** `backend/app/db/deps.py` sets `app.tenant_id` via `set_config` and verifies it round-trips, refusing to proceed on silent failure; policies read `current_setting('app.tenant_id')`. This is not a design gap — it is an enforcement gap.

**Evidence that it is already failing, and was already visible.** From the [QB-1 list](qb1-known-failures.tsv):

| Test | Reason |
|---|---|
| `tests/api/test_tenant_isolation.py::test_rls_enforcement_at_db_level` | «Should NOT see tenant 2's candidate with tenant 1 context» |
| `tests/api/test_tenant_isolation.py::test_cross_tenant_creation_blocked` | «Should block cross-tenant resource creation» |
| `tests/api/test_tenant_isolation.py::test_tenant_isolation_list_endpoints` | `TypeError` — the test itself needs repair |
| `tests/api/test_tenant_isolation.py::test_tenant_isolation_documents` | `Method Not Allowed` — route drift, needs repair |
| `tests/module_registry/…::test_p2_no_new_direct_legacy_module_flag_reads` | A live boundary violation: «New module availability checks must use `backend.app.module_registry.resolver`» |

The first two are **true negatives that were sitting inside a 371-failure baseline**. This is the concrete case for RR6: an unfrozen baseline made a security regression indistinguishable from noise.

---

## TI-1 contract (decided 2026-08-29)

| Question | Decision |
|---|---|
| Which tables are in scope | Any `public` base table with a `tenant_id` column. No allow-list of *permanently* exempt tables: the only allow-list is the frozen record of the current gap (`backend/tests/security/rls_uncovered_tables.txt`), which may shrink and never grow. |
| Canonical policy form | `tenant_id = current_setting('app.tenant_id')` — text against text. **Not** `(tenant_id)::uuid = current_setting('app.tenant_id')::uuid`: every one of the 228 `tenant_id` columns is `character varying`, so the uuid form raises `invalid input syntax for type uuid` on a malformed value instead of denying the row — a table-wide outage rather than a filter. Delivered 2026-08-29 for all 83 affected policies (see § TI-3 progress). |
| Policy form for platform-scope tables | The `ep_*`, `fr_*` and `pe_*` tables store platform-owned rows next to tenant rows, marked with the sentinel `PLATFORM_TENANT_SCOPE = ""` — 143 such rows today, including the 78 canonical fields and 31 system stages. Their policies must read `USING (tenant_id = current_setting('app.tenant_id') OR tenant_id = '')`, otherwise enabling RLS makes the platform reference data disappear for every tenant. `WITH CHECK` must **exclude** the sentinel, so a tenant cannot mint a row visible to all tenants. Counted as 15 when written; the exact set is **13**, established by prefix when TI-4 closed them. |
| What the production role must look like | Not superuser, no `BYPASSRLS`, not the owner of the tables. Provisioned by `scripts/security/provision_app_role.sql`; migrations and test bootstrap keep running as the owner role. `FORCE ROW LEVEL SECURITY` is applied to every policied table anyway, so ownership can never silently re-open the bypass. |
| §19's «RLS coverage 100%» | Kept as the target. The canon is not amended downwards; the runtime is raised to it (this was the U-6 decision). Until TI-4 closes, the honest number is published by the guard, not by the KPI table. |
| What «enforced» means for evidence | Coverage **and** role. A policy count is not evidence: the measurement below shows a fully-policied table (`candidates`, RLS enabled, 3 policies) returning every tenant's rows because the connecting role was exempt three times over. |

---

## Progress (2026-08-29)

**TI-2 delivered — the gap can no longer grow.** `backend/tests/security/test_rls_coverage_guard.py` measures the live schema and compares it with the frozen list of 102 uncovered tables. It fails in all three directions that matter: a new uncovered table, a baseline entry that is now covered (the list must shrink), and a baseline entry that no longer exists. Verified by creating a table with `tenant_id` and no policy — the guard failed and named it — then dropping it.

**TI-1 tests — three of the four failures were false alarms.** They had been sitting in the 371-failure baseline, indistinguishable from the real one:

| Test | Verdict |
|---|---|
| `test_tenant_isolation_documents` | Test defect. The collection `POST` is mounted only with a trailing slash; the test posted to `/api/v1/documents` and read `405` as an isolation failure. |
| `test_tenant_isolation_list_endpoints` | Test defect. `GET /api/v1/candidates` returns `{total, items}`; the test iterated the envelope. It now also asserts that tenant 2 sees its own candidate, so an empty list cannot pass it. |
| `test_cross_tenant_creation_blocked` | **The product is correct.** Creating a candidate against another tenant's `company_id` is rejected with `422 company not found`, which is also the right disclosure answer; the test only accepted `400/403/404`. |
| `test_rls_enforcement_at_db_level` | **Genuine.** Still red, and now reports why: `role=hostflow superuser=True bypassrls=True owns_table=True; candidates: rls_enabled=True forced=False policies=3`. |

The helper that set the tenant context swallowed every exception, so a context that failed to bind looked like a passing test; it now verifies the round-trip the way `bind_tenant_context_to_session` does in production.

**TI-3 groundwork — the restricted role works, and the database does refuse.** With `scripts/security/provision_app_role.sql` applied to a scratch database and a session connected as `hostflow_app` (not superuser, no `BYPASSRLS`, not owner) under tenant 1's context, `SELECT DISTINCT tenant_id FROM candidates` returned **only tenant 1**, where the same query as `hostflow` returned five tenants. That is the first evidence in this repository of isolation being enforced by PostgreSQL rather than by application code.

**Where the guard runs, and where it does not.** `backend-regression.yml` provisions Postgres, runs `alembic upgrade head` and then `pytest -q tests/security`, so the guard is already executed there without a workflow change. That workflow is explicitly **not a PR merge gate**, and the merge-gate workflow (`backend-ci.yml`) runs its named gates with `HOSTFLOW_SKIP_ALEMBIC_UPGRADE=1` and no database at all. Promoting the guard to a blocking check therefore needs a migrated database in CI, which is **OL-2**. Until then, per Rule 7, the coverage rule is enforced locally and advisory in CI — stated here rather than claimed as enforcement.

**Three blockers measured before TI-3 can land:**

1. **The test harness needs DDL.** `backend/tests/conftest.py` runs `CREATE TABLE IF NOT EXISTS candidate_permits` during bootstrap, so under a role without `CREATE` on `public` the whole suite errors at setup. Running the suite under the production-shaped role requires splitting the connection: owner for migrations and bootstrap, restricted role for everything the application does. That split is TI-3's real content.
2. **78 policies would error instead of deny** (see the canonical form above). One row with `tenant_id = 'p4-job-tenant'`, created by a test, made `candidates` unreadable for its own tenant the moment policies started applying.
3. **The 102 uncovered tables stay cross-tenant readable** even under the restricted role — RLS that is not enabled restricts nothing. Closing the role gap raises 124 tables to real enforcement and leaves 102 on application filtering, which is why TI-4 is not optional.

---

## TI-3 progress (2026-08-29)

**No policy can raise instead of denying any more.** Migration `202608290001_rls_text_cmp` reads each policy back from `pg_policy`, substitutes only the two unsafe shapes, and re-issues `ALTER POLICY`, so every other condition — handoff clauses, agency links, the client-vacancy join — keeps its exact form. It then refuses to finish while any policy can still raise, so the hazard cannot be left half-closed. Measured on a scratch database cloned from dev: **126 of 130 policies rewritten, 0 unsafe expressions remaining, all 130 policies intact.** Two hazards, one class:

| Unsafe shape | Count | What it did under a role RLS applies to |
|---|---|---|
| `(tenant_id)::uuid = (current_setting('app.tenant_id'))::uuid` | 83 | one row with a non-uuid `tenant_id` makes the whole table raise `invalid input syntax for type uuid` — the tenant cannot read its own data |
| `current_setting('app.tenant_id')` with one argument | 126 | any statement issued without a bound tenant raises `unrecognized configuration parameter` instead of returning nothing |

The second one was not predicted — it was found by connecting the restricted role and watching `POST /api/v1/documents/` answer 500. The two-argument form returns NULL, the comparison is unknown, and the row is refused: an unbound statement now reads as "no rows", which is the safe direction, since nothing becomes visible that was not visible before.

`downgrade()` is deliberately a no-op, and says why: after the rewrite, policies that were always safe are indistinguishable from the ones that were changed, and a mechanical inverse produced `(tenant_id)::(text)::uuid` when it was tried.

**Proof that this removes a real outage.** With the restricted role connected and tenant 1 bound, a `candidates` table containing a row whose `tenant_id` is `'p4-job-tenant'`:

| Query as `hostflow_app`, tenant 1 context | Before the migration | After |
|---|---|---|
| `SELECT count(*) FROM candidates` | `ERROR: invalid input syntax for type uuid: "p4-job-tenant"` — the tenant cannot read **its own** data | 1 row (its own), no error |
| the malformed row | — (query failed) | hidden |
| another tenant's row | — (query failed) | hidden |
| platform-scope reference row (`tenant_id = ''`) | readable | readable |

**Regression check.** Full suite on a fresh database: **369 failed / 3170 passed**, against the frozen 370-id baseline. The delta is entirely accounted for: three isolation tests fixed, and two tests that pin a literal alembic head id now fail because this migration moves the head. Those two are already repaired on `fix/test-suite-reproducibility` to assert a single head plus reachability, so **this branch must not merge before that one** — otherwise the merge-gate suite gains two failures that nobody introduced.

**One blocker left before the role can be switched, and it is not a policy.** `run_seed(db)` executes at application startup (`backend/app/main.py:544`) and writes platform-scope rows (`tenant_id = ''`) with no tenant context bound. Under the restricted role with policies on those 15 tables, that write is refused — correctly, since `WITH CHECK` must forbid a tenant minting platform rows. So the connection split has **three** consumers, not two:

| Consumer | Role | Why |
|---|---|---|
| Alembic migrations | owner | DDL |
| Test bootstrap and platform seeding | owner | performs DDL (`CREATE TABLE IF NOT EXISTS candidate_permits`) and writes platform-scope rows |
| Everything serving a request | restricted | must be subject to policies |

Moving platform reference seeding out of runtime and into migrations would be the architecturally correct end state — reference data is closer to schema than to tenant data — but that is an [ADR](../architecture/) decision, not a slice detail. For v1 the smaller path is to name the seeding connection explicitly as an owner connection.

---

## TI-3 part two — the connection split, and the reason RLS could never have worked (2026-08-29)

The split itself is small. `PRIVILEGED_DATABASE_URL` names an owner connection; when it is unset it resolves to the application's own URL, so an environment that does not separate the roles behaves exactly as before. `privileged_session_maker` in `backend/app/db/session.py` binds it, and four places moved onto it: the startup platform seed, the auth bootstrap (it creates the default tenant, users and licence rows with no tenant bound), the full-text-search function (DDL), and the test bootstrap. The dozen other `ensure_*_schema` helpers turned out to operate on a legacy SQLite file and never touch Postgres at all.

**The finding that matters is separate, and it invalidates an assumption the whole design rested on.** The tenant was bound once per request, at session level, with `set_config('app.tenant_id', …, false)`. But the setting lives on the *connection*, and a SQLAlchemy session releases its connection back to the pool on **every commit**, acquiring one again on the next statement. The `add` → `commit` → `refresh` shape used across the API therefore continues on a connection where the tenant was never set. While the application role bypassed RLS this was invisible; the moment policies applied, the read after the commit returned nothing and the endpoint answered 500 with `Could not refresh instance`.

So the binding is now applied on `after_begin` — once per transaction, transaction-locally, from `session.info["tenant_id"]` (`backend/app/db/tenant_session.py`). Transaction-local is the stronger choice in both directions: a connection handed back to the pool carries no tenant with it, and a session that never bound one cannot inherit another request's tenant from a recycled connection. Had this been switched on without noticing, every write endpoint would have failed at once — which is the argument for measuring under the role before switching it, not after.

**Result:** all eight cases in `backend/tests/api/test_tenant_isolation.py` pass with the application connected as `hostflow_app`, including `test_rls_enforcement_at_db_level` — PostgreSQL itself, not the application's `WHERE` clauses, now refuses the other tenant's rows.

**The cost of the switch, measured rather than guessed.** `scripts/testing/measure-restricted-role.sh` runs the full suite twice on the same tree — once with the application connected as the owner, once as `hostflow_app` — each from a database created from scratch, and diffs the two failure sets. Running it in both roles is the point: the owner run is the control, and it caught a change that would otherwise have been invisible (see the `session.info` note below). The owner control held at **369 on three consecutive runs**, then **366 on two more** once the identity work landed, so the deltas below are real and no fix bought its improvement by breaking the control:

| Measurement | Restricted-only failures | What was fixed between runs |
|---|---|---|
| First | **575** | — |
| Second | 424 | Fifteen test modules bound the tenant by hand with `set_config(…, false)` and no `session.info`, losing it at their first commit; they now call one helper, `test_support/tenant_context.bind_tenant` |
| Third | 159 | The harness defaults the tenant for sessions that bind none |
| Fourth | 108 | Eleven test modules that mint their own tenant now bind it in the helper that creates it |
| Fifth | 276 | *Nothing was fixed* — TI-4 closed the remaining 102 tables, so 102 more tables started enforcing. The rise is the measurement working |
| Sixth | **166** | The nine broken application paths, and the provisioning path that wrote platform reference rows from a tenant's session (`fr_canonical_fields` alone fell from 157 refusals to 15) |

Not one of the extra failures was a permissions problem — **no grant was missing.** All of them were `new row violates row-level security policy` on insert: writes issued with no tenant in scope, or with a tenant other than the one the row belongs to.

The application code was already correct on this axis — it sets `db.info["tenant_id"]` and binds transaction-locally.

**The bulk was closed by decision rather than by editing hundreds of tests.** Of the 888 places the suite opens a session, 767 never bind a tenant — they were written when the role bypassed RLS, so it did not matter. The test harness now applies the default tenant to any session that did not bind one. Two properties of that choice are worth stating, because both were deliberate:

- **It does not weaken what the suite proves about isolation.** That proof is made explicitly elsewhere: policy coverage (`test_rls_coverage_guard.py`), the application connecting as a restricted role, and cross-tenant refusal at the database level (`test_tenant_isolation.py`, which binds each tenant by hand).
- **The default touches the database setting only, not `session.info["tenant_id"]`.** Six places in `backend/app` read that key as the authoritative tenant — company scoping and tenant visibility among them — so defaulting it would change what the application under test believes about itself. An earlier version of the hook did set it, and the owner-role control run immediately showed a different failure pattern; that is why the measurement is run in both roles rather than only in the new one.

**What the default hides is covered by a guard instead.** `backend/tests/security/test_tenant_binding_call_sites.py` enumerates every function in `backend/app` that opens a session directly — 24 of them do so without binding — and requires each to be named in `unbound_session_sites.txt` with a class and a reason. A new unbound site fails at the point it is introduced. The reviewed classification:

| Class | Count | Content |
|---|---|---|
| `safe` | 12 | Authentication, which identifies a user before a tenant exists to bind (8 sites); jobs that read `tenants` to loop and bind each iteration; the generic `get_db` dependency, which its caller binds |
| `owner` | 2 | Startup bootstrap and auth seeding, now on the privileged connection |
| `broken` | 10 | Reads or writes a table that **does** carry a policy with no tenant bound. These do not work once the role is switched |

The `broken` set is the honest answer to "can the role be switched today": **no.** Public document scanning resolves `SELECT tenant_id FROM scan_sessions` before it binds, and `scan_sessions` has a policy, so every public scan session would answer 404. The lead bulk worker reads each lead on an unbound session and would report every one as "not found". Lead import writes `lead_import_jobs` unbound. Document upload registration reads `documents` unbound. The Stripe webhook job writes tenant rows unbound. All ten are named with the reason, and the switch is sequenced after they are fixed.

**What the last 108 are, and why the generic pass stopped there.** They divide into two shapes, both needing a per-test judgement rather than a rule:

- **A tenant is minted and rows are written for a different one.** `tenant_links` accounts for 35: the row belongs to the agency side, and a session bound to the client side cannot write it. The two permissive policies (`agency_tenant_id` or `client_tenant_id` matches) are right; the test binding is what has to be chosen.
- **The tenant is passed as an argument while the session is bound to another.** `backend/app/services/tenant_links.py::ensure_client_company_tenant_link` takes `agency_tenant_id` as a parameter, so a caller can name a tenant the session is not bound to; PostgreSQL then refuses the write, correctly. This is the general form of the remaining tail, and it applies to application code as much as to tests: **a write is permitted only where the tenant in the argument and the tenant on the session agree.**

A blanket attempt to bind the tenant inside every test helper that takes a `tenant_id` (53 helpers, 22 files) was measured on a subset and moved it from 37 to 33 — no real yield for a broad change in what those sessions believe — so it was reverted. The remaining 108 are named in the measurement output and belong to TI-4 alongside the app paths, because both must be true before the role can be switched.

**One decision TI-4 cannot avoid.** `users`, `user_memberships` and `tenants` have no policy today, which is the only reason authentication works on an unbound session. A tenant-scoped policy on `users` makes login-by-email impossible on the application connection. Closing the coverage gap therefore requires deciding what identity lookup runs as — a dedicated pre-auth connection, a policy that permits lookup by email, or identity tables that are deliberately not tenant-scoped. This is a security-canon decision, not a slice detail.

**One more shared-state defect surfaced.** `tenant2_data` never created the tenant it writes rows for; every insert has a `tenant_id` foreign key to `tenants`, so the fixture only ever worked because an earlier run had left tenant 2 behind. On a database that starts clean it failed with a foreign-key violation, and the vacancy case then answered 412 `OWN_COMPANY_REQUIRED` for the same reason. Both are fixed in the fixture. This is the same class as the 74 tests recorded in the register: the suite is coupled to rows that outlive the run.

---

## TI-4 — the coverage gap is closed (2026-08-29)

**Every tenant-scoped table now carries a policy.** The 102 that did not were closed in seven
migrations, batched by owning module rather than in one pass, so a failure reads as "the
communication batch broke something" instead of "something broke". The guard's baseline file is
now empty, which changes what it asserts: `test_no_tenant_table_loses_rls_coverage` used to mean
"the gap has not grown" and now means "there is no gap".

| Batch | Migration | Tables |
|---|---|---|
| Identity | `202608290002_rls_identity` | 2 |
| Acquisition | `202608290003_rls_acquisition` | 18 |
| Communication | `202608290004_rls_communication` | 31 |
| Recruitment & HR | `202608290005_rls_recruitment_hr` | 9 |
| Sales | `202608290006_rls_sales` | 8 |
| Documents | `202608290007_rls_documents` | 6 |
| Platform | `202608290008_rls_platform` | 15 plain + 13 platform-scope |

**Identity was decided, not deferred.** The choice (security canon owner, 2026-08-29) is to close
`users` and `user_memberships` like any other tenant table and to let authentication — and only
authentication — reach them over the owner connection, through one named factory,
`backend/app/auth/identity_session.py`. The alternatives were worse in different directions:
leaving identity exempt lets the whole application read every tenant's users, and an
`app.auth_lookup` escape hatch inside the policy puts a switch that disables isolation on the same
connection that serves requests. Nine call sites use the factory — the eight pre-authentication
endpoints and `ensure_user_can_access_tenant`, which answers *may this user act in this tenant*
and therefore has to run before the binding it decides.

The `users` policy is not the plain form. A user is visible to the tenants they belong to, not
only to the tenant that owns their row, so it carries an `EXISTS` over `user_memberships` — the
same shape the existing `candidates` policy uses for handed-off rows. Without it the agency ↔
client switcher would list a membership whose user has no name. `WITH CHECK` stays narrow, so
being visible in a tenant never becomes a licence to create accounts there.

**A stated contract line had to bend, and it is worth naming.** The TI-1 contract said `FORCE ROW
LEVEL SECURITY` would be applied to every policied table so ownership could never re-open the
bypass. `FORCE` applies policies to the owner too — which is exactly what the identity connection
and the platform seeder need to not happen. Rather than reintroduce a `BYPASSRLS` role, the rule
now has a named, guarded exception: 15 tables are not forced (2 identity, 13 platform reference),
every other policied table is, and `backend/tests/security/test_rls_force_exceptions.py` fails
both when the set grows and when a listed table no longer needs to be in it. The way to shrink the
platform half is to move platform seeding into migrations, where it runs as owner during DDL and
needs no exception at all; that is not this slice.

**The nine broken application paths are fixed.** They fell into three shapes, and the shape matters
more than the count, because the third one is a design finding rather than a bug:

| Shape | Paths | What changed |
|---|---|---|
| The tenant was already in scope and simply never bound | lead bulk worker, lead bulk queue, lead import job | bind it |
| The tenant was reachable but not passed | document upload registration | `tenant_id` became a required argument; the dev-only S3 mock endpoint now requires `X-Tenant-Id` rather than guessing |
| The tenant is what the lookup produces | public scanner (4 endpoints), Stripe webhook | a narrow owner-side resolution returns *a tenant id and nothing else*, then the caller binds and works under policy |

The third shape is the same problem authentication has, and it gets the same answer:
`backend/app/db/tenant_resolution.py` spells out each lookup by hand instead of accepting a table
name, because a generic "resolve the tenant of any row" helper is a general-purpose way around
isolation, one string away from any code path. For Stripe the binding was placed inside
`_find_tenant_for_stripe_event` rather than in the six handlers that call it, so a seventh handler
cannot forget.

**One genuine application defect surfaced that no test had named.** Tenant provisioning called
`ensure_platform_field_registry_catalog` inline — a tenant's session writing platform-owned rows
under the sentinel. It worked only because nothing stopped it. The presence check now runs on the
caller's session (sentinel rows are readable from any tenant, by design) and the seeding, on the
rare path where the catalog really is missing, runs on the owner connection that startup already
uses. A tenant that could mint a sentinel row could publish a field definition to every other
tenant, so this one was worth the detour.

The guard's `broken` class is now empty, and the assertion that used to protect the list from being
quietly emptied is inverted: an application path that cannot work under the restricted role is a
regression, not a known state of the world.

**What is left, and what it is not.** 166 tests fail only under the restricted role. Every one of
them is a test writing a row for a tenant other than the one its session is bound to — the shape
described above, now visible across the whole suite rather than in one corner of it. No application
path is among them, and no grant is missing. The concentrations are `tenant_links` (34, the
agency ↔ client row that belongs to one side while the test binds the other), `own_companies` (20)
and `candidates` (18). That tail is what stands between here and switching the role on; it is
suite work, and it is the last thing TI-4 owes.

---

## Internal ladder (proposed)

| Slice | Content | Named gate |
|---|---|---|
| **TI-1** ✅ | Decide and record the target: which tables are in scope (`tenant_id` present ⇒ in scope, minus a named allow-list with reasons), what the production role must look like (non-superuser, non-owner or `FORCE`), and whether §19's 100% is the target or is amended. Fix the four `test_tenant_isolation.py` cases so they test the intended property. | **Isolation Contract Gate** — contract recorded above; three of the four tests repaired, the fourth left red on purpose |
| **TI-2** ✅ | Coverage guard: a test/CI check that fails when a `tenant_id` table has no policy, plus the measured baseline committed as the allow-list. Makes the gap non-growing before it is closed. | — Delivered and verified in both directions |
| **TI-3** | Provision the role model: a documented, scripted production role that is not superuser and does not own the tables, or `FORCE ROW LEVEL SECURITY` where ownership cannot be separated. Isolation tests run under that role in CI. **Provisioning script, the policy-form migration and the connection split are delivered, and the isolation suite passes under the restricted role.** What remains is the cost of the switch across the *whole* suite (being measured) and the CI wiring, which needs a migrated database in CI (**OL-2**). | — |
| **TI-4** | Close the 102-table gap in batches with the guard staying green; retire the allow-list. Also: fix the **10 `broken` call sites** so the role can be switched, and decide what identity lookup runs as once `users` carries a policy. **Coverage is closed** — seven migrations, baseline empty, identity decided, `FORCE` exception named and guarded. What remains before the switch: the 10 application paths and the test tail. | **RLS Coverage Gate** |
| **TI-5** (conditional) | Fix the red module-registry boundary guard, or split it out if it proves unrelated. | — |

**Not this brief:** RBAC / role semantics, superadmin model, audit coverage, export rules, the `tenant_visibility` agency-linking model, and the [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md) erasure work (adjacent, separately owned).

---

## Relationship to the release

RR5 cannot be answered `PASS` while the canon's stated primary control is not in force. Two dispositions were legitimate:

1. **Fix before RC** — TI-1…TI-4 land, RR5 answered on evidence. ← **chosen 2026-08-28**
2. Accept for v1 with a named compensating control — application-level filtering plus an explicit customer-facing statement, an expiry, and amendment of §10 and §19 so the canon stops asserting something untrue. **Rejected**: the canon keeps its rule, and the runtime is brought up to it.

Consequences of the decision: RR5's evidence bar now demands isolation evidence produced **under the production-shaped role** plus a coverage guard; TI-1…TI-4 sit in the gate-prerequisite line of the roll-up (3–5 of the 4–7 prerequisite slices), which moved the planning RC band to 2026-10-01 … 2026-10-18.

What was **not** an option is the state this replaced: canon asserting 100% RLS coverage, measurement showing 55%, and the failing test treated as noise.

---

## History

| Date | Change |
|------|--------|
| 2026-08-29 | **TI-4 coverage delivered.** All 102 remaining tenant-scoped tables closed in seven owner-batched migrations; the guard's baseline is empty, so it now asserts *no gap* rather than *no growth*. Identity decided: `users` and `user_memberships` carry policies and authentication runs over one named owner connection. A stated contract line bent under evidence — `FORCE` cannot be universal, because it applies to the owner, and the owner is exactly what identity lookup and platform seeding need; 15 tables are named exceptions and a new guard fails if the set grows or goes stale. The nine broken application paths are fixed, and one undiscovered defect with them: tenant provisioning was writing platform-owned reference rows from a tenant's session. |
| 2026-08-29 | **Switch sequencing decided by the owner:** the application moves to the restricted role **after TI-4**, when the coverage gap is closed — a role in force over a schema where half the tables have no policy buys a false sense of protection. Test-suite bindings are defaulted in the harness rather than edited into 424 tests, with the blind spot that creates covered by a static guard over the 24 places `backend/app` opens a session directly. |
| 2026-08-29 | **TI-3 part two delivered: the isolation suite passes with the application connected as `hostflow_app`.** Two findings, both invisible while the role bypassed RLS. First, 126 of 130 policies read `app.tenant_id` with one argument, so an unbound statement raised instead of returning nothing; folded into the same migration. Second, and more consequential: the tenant was bound once per request at session level, but a session releases its connection to the pool on every commit, so the `add`/`commit`/`refresh` shape continued on an unbound connection — RLS could never have worked with that binding. Binding moved to `after_begin`, transaction-locally. Connection split added behind `PRIVILEGED_DATABASE_URL`, which resolves to the application URL when unset, so environments that do not separate roles are unaffected. One more leftover-state fixture defect fixed: `tenant2_data` never created its own tenant. |
| 2026-08-29 | **TI-3 part one delivered.** Migration `202608290001_rls_text_cmp` removed the uuid casts from all 83 affected policies, proven to turn a table-wide error into a correct denial under the restricted role. Two facts recorded that change TI-4: 15 tables hold platform-owned rows under the sentinel `PLATFORM_TENANT_SCOPE = ""` and need `OR tenant_id = ''` in `USING` (and its exclusion in `WITH CHECK`); and platform seeding runs at application startup, so the connection split has three consumers, not two. Suite regression: 369 vs the 370 baseline, fully accounted for, with a merge-order dependency on `fix/test-suite-reproducibility`. |
| 2026-08-29 | **TI-1 and TI-2 delivered** on `feat/tenant-isolation-ti1-ti2`. Contract recorded, coverage guard live with the 102-table gap frozen, three of the four isolation tests found to be test defects rather than isolation failures, and the restricted role proven to make PostgreSQL refuse cross-tenant rows. Two facts not known when the brief was written: all 228 `tenant_id` columns are `character varying` and 78 policies cast them to `uuid`, so under real enforcement they error rather than deny; and the test harness performs DDL, so running under the production-shaped role needs an owner/application connection split. **Estimate moves to the upper end (5–8 slices)** — TI-4 now has a measured size of 78 policy rewrites plus 102 tables. |
| 2026-08-28 | Brief created from the QB-1 baseline measurement (`255279fc`). Coverage and role facts measured on the dev cluster. Opened as **U-6** in the register and decided the same day: **close the gap before RC** (option 1), so the security canon keeps its rule and the runtime is raised to it. |
