# HostFlow v1 — Unowned Work Register

**Status:** **L2 OPERATING CANON** (register of work the plan does not own; **every row must carry a disposition**)
**Date:** 2026-08-28
**Owner:** Engineering lead + Operational lead (register upkeep); the owner named per row owns the item itself
**Parents:** [HostFlow v1 Release Goal](hostflow-v1-release-goal.md) · [Release Readiness Gate](release-readiness-gate.md) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md) · [Platform scope completeness audit](platform-scope-completeness-audit.md) · [Goal Completion Gate](goal-completion-gate.md)

> The plan can only be trusted if the work it **excludes** is written down as deliberately excluded.
> This register exists so the release decision is never surprised by a commitment nobody was tracking. It does **not** schedule anything and does **not** widen v1 scope.
> Inventory date 2026-08-28, from a full sweep of `docs/specs/gates/**`, `docs/specs/architecture/ADR-*`, `docs/specs/tasks/**`, `docs/security/**`, maturity and audit records.

---

## What counts as unowned

At inventory date the plan owns exactly this work:

| Track | Owns |
|-------|------|
| Product | [RPM-1 → RPM-2 → RPM-3](../tasks/requirement-policy-management.md) |
| Product (briefed, unscheduled) | [Mapping Authority](../tasks/mapping-authority.md) · [External Intake / Forms Publish](../tasks/external-intake-forms-publish.md) · [Hiring workflow E2E](../tasks/hiring-workflow-e2e.md) · [min HR handoff](../tasks/recruitment-hr-minimal-handoff.md) |
| Launch-ops (briefed, unscheduled) | [Operate & Launch](../tasks/operate-and-launch.md) OL-1…OL-7 |
| Background | [pytest baseline stabilisation](../tasks/stabilize-integration-pytest-baseline.md) |

Anything else in the canon that implies future work is **unowned** and must appear below with one of four dispositions.

| Disposition | Meaning | Consequence |
|-------------|---------|-------------|
| **D1 — owned by a v1 brief** | The item is inside a briefed blocker; it is unscheduled, not unowned | Nothing to add; the brief carries it |
| **D2 — declared residual** | Not v1, but the release decision must state it, with owner and (where relevant) expiry | Must appear in the [gate](release-readiness-gate.md) § Named residuals |
| **D3 — later (no action)** | Deliberately out of v1; no residual entry needed | Stays in the roadmap / ADR only |
| **D4 — needs a decision** | Nobody owns it and it is not clearly later | **Must be resolved before the gate opens** — this is the only disposition that blocks EC-1 |

---

## D4 — needs a decision (the only rows that block the gate)

**Empty. All six rows are decided as of 2026-08-28.** EC-6 of the [Release Readiness Gate](release-readiness-gate.md) is satisfied unless a new U-row is opened.

### Decided

| # | Item | Decision | Landed as |
|---|------|----------|-----------|
| **U-1** | RR6 known-failure list does not exist | **Measure once and freeze.** A scratch test database is authorised; the aggregate is replaced by an enumerated list with per-cluster owners. **Measured the same day: 371 failed / 3164 passed on a clean worktree at `255279fc`**, of which 8 are order-dependent; the earlier 397 / 54 readings were artifacts of the wrong working directory and a reused database | **D1** — [pytest baseline](../tasks/stabilize-integration-pytest-baseline.md) § QB-1 · list: [`qb1-known-failures.tsv`](../tasks/qb1-known-failures.tsv) |
| **U-2** | ADR-022 Intake Form Purpose is `Proposed` while its backend exists | **Accept the ADR** inside the first Forms Publish slice. v1 does not ship intake acceptance over an unaccepted contract | **D1** — [Forms Publish](../tasks/external-intake-forms-publish.md) FP-1 |
| **U-3** | Documents Foundation 🔄 with D3 / D5 / D6 / D7 / D9 `documents` slots unbound | **Residual.** Empty slots are acceptable for v1; the customer sentence is recorded | **D2** — Documents |
| **U-4** | Entity Shell inner capabilities remain module-local | **Residual.** Notes / Consent stay module-local for v1; no acceptance scenario depends on hosting them | **D2** — Product Architecture |
| **U-5** | FormTemplate SoT migration / `TenantLeadForm` bridge | **Residual.** Publish ships on the bridge; the migration is post-v1 | **D2** — Forms |
| **U-6** | **Database-level tenant isolation is not in force.** 226 tables carry `tenant_id`; 102 have no RLS policy at all; `FORCE ROW LEVEL SECURITY` is set on **zero** tables; the application role is superuser with `BYPASSRLS` and owns every table, so even policied tables are unprotected for it; nothing in the repository provisions a restricted role. Meanwhile [security-ssot.md](../../security/security-ssot.md) §10 asserts RLS «на всех tenant-scoped таблицах» and §19 sets coverage at 100% | **Close the gap before RC.** TI-1…TI-4 enter the plan as a gate prerequisite; RR5 will be answered on measured evidence rather than by amending the canon downwards | **D1** — [tenant isolation enforcement](../tasks/tenant-isolation-enforcement.md) TI-1…TI-4 |

**Rule (unchanged):** the Release Readiness Gate may not open while any U-row is undecided. Deciding a U-row means moving it to D2 (with owner, expiry, customer sentence) or into a named slice — not deleting it. A new U-row may be opened at any time by anyone who finds release-relevant work with no owner.

---

## D1 — owned by a v1 brief (unscheduled, not unowned)

| Item | Brief that owns it |
|------|--------------------|
| ~~Fresh-database `alembic upgrade heads` failure~~ — measured false 2026-08-31; replaced by **RC condition 4 lacks its "documented procedure" clause** (the migration half is proven, including by CI on every push) and **a freshly migrated instance starts with no admin user** | [Operate & Launch](../tasks/operate-and-launch.md) OL-2 · [§ Correction](../tasks/operate-and-launch.md) |
| All ten missing v1 runbooks (RB-1…RB-10) | [Operate & Launch](../tasks/operate-and-launch.md) OL-2…OL-7 · [runbook index](../../runbooks/README.md) |
| Production defaults: in-process queue, local-disk storage, scheduler inside the API process | [Operate & Launch](../tasks/operate-and-launch.md) OL-3 |
| Tenant export, subject erasure, retention policy; FAQ anonymisation claim without implementation | [Operate & Launch](../tasks/operate-and-launch.md) OL-6 · [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md) |
| No bulk import of a customer’s existing base | [Operate & Launch](../tasks/operate-and-launch.md) OL-6 |
| No on-call / severity / customer-communication path | [Operate & Launch](../tasks/operate-and-launch.md) OL-7 |
| Three mapping stores, three mapping editors, dual mapping vocabulary | [Mapping Authority](../tasks/mapping-authority.md) |
| Orphaned `commit_publish`; presentation-vs-Builder dual form definition | [External Intake / Forms Publish](../tasks/external-intake-forms-publish.md) |
| Three stage registries; ten eligibility answerers; arbitrary stage jumps | [Hiring workflow E2E](../tasks/hiring-workflow-e2e.md) |
| Delayed-workforce flag; conditional document reuse; PE HR inbound placeholder | [min HR handoff](../tasks/recruitment-hr-minimal-handoff.md) |
| Nine requirement-policy answerers | [RPM-1…RPM-3](../tasks/requirement-policy-management.md) |
| ~~Sales / Forms / Acquisition have runtime code and no ownership card~~ | **CLOSED** 2026-08-28 — MOC-1…MOC-3 delivered ([coverage record](module-ownership-coverage.md) §4) |
| ~~`backend/app/modules/leads` claimed by Recruitment, Integrations and the catalog simultaneously~~ | **CLOSED** 2026-08-28 — adjudicated per concern in the [Acquisition card](../../modules/acquisition/module_ownership_card.md) § Lead adjudication |
| Recruitment card’s «lead intake processing» is overbroad vs the ADR-021 transport demotion | [Acquisition card](../../modules/acquisition/module_ownership_card.md) — narrow when the Recruitment card is next revised (no slice; not v1-blocking) |
| **U-1 decided:** enumerate, freeze and own the known-failure list on a scratch test database | [pytest baseline](../tasks/stabilize-integration-pytest-baseline.md) § QB-1 — RR6 evidence |
| **U-2 decided:** accept [ADR-022](../architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md) (Intake Form Purpose) | [Forms Publish](../tasks/external-intake-forms-publish.md) FP-1 — was an explicit non-goal, now in scope |
| **U-6 decided:** close the tenant-isolation enforcement gap before RC — policy coverage, coverage guard, restricted production role | [Tenant isolation enforcement](../tasks/tenant-isolation-enforcement.md) TI-1…TI-4 — RR5 evidence |
| **Known-failure routing accepted 2026-08-28:** each blocker brief takes the failing tests on its own path as an entry condition (HH 100 · RPM/Documents 61 · HE 52 · MA 45 · FP 22); TEST-INFRA 42 and TI 5 are fix-before-RC | [`qb1-known-failures.tsv`](../tasks/qb1-known-failures.tsv) `proposed_owner` column |

---

## D2 — declared residuals (not v1; must appear in the release record)

Grouped by class. Each row needs an owner in the closing record; expiry only where the item can grow.

### Gate residuals and constraints already recorded

| Item | Declared in | Owner | Can it grow? |
|------|-------------|-------|--------------|
| Epic C R2 — legacy SMTP allowlist non-empty (`rodo`, notifications, dispatch) | [epic-c-complete-gate.md](epic-c-complete-gate.md) | Communication + owning modules | **Yes** — allowlist must not grow; expiry needed |
| Epic C R3 — platform lazy-imports module adapters | [epic-c-complete-gate.md](epic-c-complete-gate.md) | Architecture / Communication | No |
| Epic C R4 — Campaign/Automation publish soft on Intent Registry membership | [epic-c-complete-gate.md](epic-c-complete-gate.md) | Communication | Yes — hardening before new Intent consumers |
| A2-F5 — two automation planes (ADR-019 vs `communication_*`) | [platform-governance-review-a2.md](platform-governance-review-a2.md) | Architecture + Communication | Yes |
| A2-F7 — Entity Workspace is not the platform SoT | [platform-governance-review-a2.md](platform-governance-review-a2.md) | Product Architecture | No |
| A2-F8 — Documents Foundation still consolidating | [platform-governance-review-a2.md](platform-governance-review-a2.md) | Documents | No |
| WCP G5 — migrate-on-touch inventory; Notes stub; Action Canon references | [workspace-capability-platform-complete.md](workspace-capability-platform-complete.md) | WCP G5 owner | Yes |
| Forms — `SalesInquiryQuestionnaireSection` + `leadId` glue | [platform-scope-completeness-audit.md](platform-scope-completeness-audit.md) | Forms | No |
| Acquisition — Lead stays transport; `/api/v1/leads` compat until R6 | [platform-scope-completeness-audit.md](platform-scope-completeness-audit.md) | Acquisition | No |
| REF-4 direct-access exceptions EXC-001…010 (+ EXC-005 documents intake) | [system_direct_access_exceptions_registry.md](system_direct_access_exceptions_registry.md) · [REF-4 scan](ref4_phase2_full_system_reference_adoption_scan_report.md) | per-row owner | **Yes** — registry must not grow |
| Acquisition Stage 3E deferred D1–D5 (Meta normalization, duplicate disposition, txn boundaries) | [acquisition-stage-3e-deferred.md](../tasks/acquisition-stage-3e-deferred.md) | per-row suggested home | No |
| Intake Communication Context C6 — legacy unresolved handling | [intake-domain-separation-communication-context-v1.md](../tasks/intake-domain-separation-communication-context-v1.md) | Intake / Communication | No |

### Decided residuals (2026-08-28, from D4)

Each carries the sentence a customer is told, because that is what the closing record copies.

| Item | Owner | Can it grow? | What the customer is told |
|------|-------|--------------|---------------------------|
| **U-3** Documents Foundation 🔄 — `documents` slots on D3 / D5–D7 / D9 unbound; no successor program after E8 | Documents | No — binding more consumers is a post-v1 program, and the empty set must not be re-labelled «done» | «Documents are attached to employees and candidates. Client, order and vacancy records do not carry their own document set in this release.» |
| **U-4** Entity Shell inner capabilities (Notes / Consent / rail) stay module-local | Product Architecture | No | Nothing customer-visible: the capabilities work, they are just implemented per module rather than on the shared host. |
| **U-5** Form definition ships on the `TenantLeadForm` bridge; `FormTemplate` SoT migration deferred | Forms | **Yes** — no new writer may be added to the bridge; the three live form definitions must not become four | Nothing customer-visible; internal storage model changes after v1 without affecting published forms. |

### Security residuals

| Item | Declared in | Owner |
|------|-------------|-------|
| Security roadmap Phase 3 / 4 — signed-URL telemetry, export sliding-window alerts deferred to Phase 7 | [runtime-roadmap.md](../../security/runtime-roadmap.md) | Security owner |
| Phase 5 — WORM audit / dual-authorisation superadmin backlog | [runtime-roadmap.md](../../security/runtime-roadmap.md) | Security owner |
| Phase 6 — RAG/vector GDPR delete; analytics drill-down retrieval | [runtime-roadmap.md](../../security/runtime-roadmap.md) | Security owner |
| Phase 7 — brute-force rules; **shared store for burst counters** (single-replica assumption today) | [runtime-roadmap.md](../../security/runtime-roadmap.md) | Security owner |
| RBAC — JOB_PROXY burn-down; portal `access_context` not persisted on JWT | [rbac-role-usage-inventory.md](../architecture/rbac-role-usage-inventory.md) · [rbac-trust-roles threat model](../../security/threat-models/rbac-trust-roles.md) | Security / RBAC |
| Global search Phase 6 — platform-only cross-tenant mode, rate limiting incomplete | [retrieval-audit-governance.md](../../security/retrieval-audit-governance.md) | Security owner |
| Public-surface rate limiting is **fail-open when Redis is unavailable** | `backend/app/core/rate_limit.py` (behaviour), consumed by [Operate & Launch](../tasks/operate-and-launch.md) OL-3/OL-4 | Security owner + Engineering lead |
| Interactive demo — shared public login forbidden until an isolation gate | [interactive-demo threat model](../../security/threat-models/interactive-demo.md) | Security owner |

### Quality debt

| Item | Declared in | Owner | Note |
|------|-------------|-------|------|
| Coverage ratchet gap — backend baseline ~35% vs 60% target; frontend ~5% vs 40% | [HOSTFLOW_AUDIT_AND_PLAN.md](../../HOSTFLOW_AUDIT_AND_PLAN.md) | Engineering lead | Non-blocking suite; feeds RR6 |
| ~~Backend suite is not reproducibly measurable~~ **Resolved 2026-08-29** on `fix/test-suite-reproducibility`: working-directory dependence, stale alembic head pins and monthly-quota accumulation are fixed, and `scripts/testing/measure-known-failures.sh` gives an identical 370-id set on two consecutive runs | [pytest baseline](../tasks/stabilize-integration-pytest-baseline.md) § TEST-INFRA progress | Engineering lead | RR6 now has a reproducible number. The remaining coupling is the row below |
| 108 tests write a row for one tenant while their session is bound to another, so they pass while the application bypasses RLS and fail the moment it does not. The general form is not a test bug: **a write is permitted only where the tenant in the argument and the tenant on the session agree** — `ensure_client_company_tenant_link` takes the agency tenant as a parameter and is refused when the caller is bound elsewhere | [tenant isolation](../tasks/tenant-isolation-enforcement.md) § the last 108 | Engineering lead | Owned by **TI-4**; blocks switching the application to the restricted role together with the 10 unbound application paths |
| Tests depend on, and mutate, rows that outlive the run: on a reused database 54 tests fail only when it is fresh (HR dashboard, workforce, handoff, ZUS) and 20 only when it is warm (Meta credentials, communication accounts, funnel and document-type fallback resolvers) | [pytest baseline](../tasks/stabilize-integration-pytest-baseline.md) § TEST-INFRA progress | Engineering lead | Does not block RR6 while the fresh-database protocol is mandatory, and the tolerated-set expiry already bounds it. Blocks any move to per-test transactional isolation |
| **Tolerated for v1 (decided 2026-08-28):** 44 known failures outside all six v1 blockers — Fleet, calendar, invoices, analytics, org units, company module settings | [`qb1-known-failures.tsv`](../tasks/qb1-known-failures.tsv) (`proposed_owner = UNROUTED`) | Engineering lead | **Expiry 2027-01-31** (one quarter after the planning RC band). The set may not grow: a new failure on these surfaces is a normal defect, not an addition to the tolerated list. Customer sentence: «Fleet, calendar, invoicing and analytics surfaces ship as-is in v1; defects there are tracked but were not part of release acceptance» |
| ~~126 of 130 RLS policies could raise instead of denying: 83 cast `(tenant_id)::uuid` although all 228 `tenant_id` columns are `character varying`, and 126 read `app.tenant_id` without tolerating an unset parameter~~ **Fixed 2026-08-29** by migration `202608290001_rls_text_cmp`, which refuses to finish while any policy can still raise | [tenant isolation](../tasks/tenant-isolation-enforcement.md) § TI-3 progress | Security canon owner | Proven to turn a table-wide `invalid input syntax for type uuid`, and an `unrecognized configuration parameter` 500, into correct denials |
| ~~10 application paths open a database session and never bind a tenant~~ **Fixed 2026-08-29** — nine were real (the tenth was a miscount) and each now binds: three had the tenant in scope, one takes it as a required argument, and five resolve it through a narrow owner-side lookup that returns a tenant id and nothing else. A further defect surfaced on the way — tenant provisioning was writing platform-owned reference rows from a tenant's session — and is fixed with them | [tenant isolation](../tasks/tenant-isolation-enforcement.md) § the nine broken paths | Engineering lead | Closed. The guard's `broken` class is empty and the assertion is inverted: a path that cannot work under the restricted role is now a regression |
| ~~Identity tables have no RLS policy, and authentication depends on that~~ **Decided and closed 2026-08-29** — `users` and `user_memberships` carry policies; authentication reaches them over one named owner connection (`backend/app/auth/identity_session.py`), which is why those two are among the 15 tables deliberately not forced | [tenant isolation](../tasks/tenant-isolation-enforcement.md) § TI-4 | Security canon owner | Closed. The clause that also claimed `tenants` "is not tenant-scoped" was wrong and is superseded by the row below |
| ~~`candidate_handoffs` and `candidate_handoff_snapshots` had row-level security switched off entirely, and `tenant_links` carried read-only policies that made every write default-deny~~ **Fixed 2026-08-30** by `202608290009_rls_handoff_dual_leg` | [tenant isolation](../tasks/tenant-isolation-enforcement.md) § TI-5 | Security canon owner | Closed. These three are scoped through `agency_tenant_id` / `client_tenant_id`, and the coverage guard keyed on the literal name `tenant_id` — so two tables holding cross-tenant candidate data and personal snapshots were readable by any tenant for the whole duration of TI-1…TI-4, and were reported as covered. The guard now matches any column ending in `tenant_id` and additionally requires a policy that can admit a write |
| `tenants` has no RLS policy, and closing it is blocked on the superadmin platform surface: all of `/api/v1/platform` runs on an unbound session and reads and writes every tenant by design, as do tenant creation, global slug uniqueness, and the two public resolvers that map a share token or a host to a tenant | [tenant isolation](../tasks/tenant-isolation-enforcement.md) § TI-5 | Security canon owner + Engineering lead | **Owned by TI-5, and it moves the role switch.** The 2026-08-29 decision to switch after TI-4 does not hold: under the restricted role the platform surface is denied on every tenant it administers. Named in `backend/tests/security/rls_uncovered_tables.txt` with the reason |
| ~~The tenant was bound once per request at session level, but a session releases its connection to the pool on every commit — so RLS could not have worked at all: the `add`/`commit`/`refresh` shape continued on an unbound connection~~ **Fixed 2026-08-29**: bound on `after_begin`, transaction-locally | [tenant isolation](../tasks/tenant-isolation-enforcement.md) § TI-3 part two | Engineering lead | Found only by connecting the restricted role. Had the role been switched without measuring first, every write endpoint would have failed at once |
| Platform reference data lives in tenant tables under the sentinel `PLATFORM_TENANT_SCOPE = ""` (15 `ep_*` / `fr_*` / `pe_*` tables, 143 rows), and it is written by `run_seed` at **application startup** | [tenant isolation](../tasks/tenant-isolation-enforcement.md) § TI-1 contract | Architecture canon owner | Two consequences owned by TI-3 / TI-4: those policies need `OR tenant_id = ''` in `USING` and its exclusion in `WITH CHECK`, and platform seeding must not run on the tenant-restricted connection. Moving reference seeding from runtime into migrations would be the correct end state and needs an ADR |
| ~~Test bootstrap performs DDL (`CREATE TABLE IF NOT EXISTS candidate_permits` in `conftest.py`), so the suite cannot run under a role without `CREATE` on `public`~~ **Fixed 2026-08-29**: bootstrap and platform seeding run on an owner connection (`PRIVILEGED_DATABASE_URL`), request serving on the restricted one | [tenant isolation](../tasks/tenant-isolation-enforcement.md) § TI-3 part two | Engineering lead | The URL resolves to the application's own when unset, so environments that do not separate roles are unaffected |
| Architecture guard `test_p2_no_new_direct_legacy_module_flag_reads` is red — a live boundary violation against `module_registry.resolver` | [`qb1-known-failures.tsv`](../tasks/qb1-known-failures.tsv) | Engineering lead | Concrete instance of the Rule 7 enforcement gap named in [module-ownership-coverage.md](module-ownership-coverage.md) |
| ~~`test_alembic_has_single_head` and `test_forms_sprint6_alembic_single_head` pin obsolete literal revision ids~~ **Fixed 2026-08-29**: they now assert one head plus reachability in `alembic history` | [pytest baseline](../tasks/stabilize-integration-pytest-baseline.md) § TEST-INFRA progress | Engineering lead | |
| Hardcoded screening / required-field maps in the frontend | [CL1 inventory](../tasks/entity-field-composition-cl1-inventory.tsv) | RPM / Field Composition | Cutover in RPM-3 where it overlaps policy |
| Telegram messenger hardcoded strings (i18n) | [telegram execution plan](../workflows/candidate-intake-via-telegram-execution-plan.md) | Communications | |
| Select / listbox accessibility deferred to implementation review | [SELECT_V1_DRAFT.md](../frontend/SELECT_V1_DRAFT.md) | Frontend owner | |
| Dependabot: 19 open vulnerability alerts on the default branch (8 high) | GitHub security tab (reported on push) | Security owner | Not in `docs/`; must be triaged before the gate |
| No enforcement that a domain has an ownership card, or that the certification matrix matches the runtime module list (Rule 7 → the coverage dimension of the Module Independence Program is documentation only) | [module ownership coverage](module-ownership-coverage.md) §5 | Architecture canon owner | Launch-ops candidate; prevents future drift, does not make v1 launchable |
| Empty packages `backend/app/modules/finance` and `.../services` imply ownership their documented modules run elsewhere | [module ownership coverage](module-ownership-coverage.md) §3 | Architecture canon owner | Either the runtime moves in or the packages go |

### ADRs accepted without runtime

| ADR | State | Owner | v1 relevance |
|-----|-------|-------|--------------|
| [ADR-012](../architecture/ADR-012-activity-notification-operating-layer.md) Activity & Notification layer | Phases 1–4 not started; parallel task tables remain | Platform | Declared residual |
| [ADR-019](../architecture/ADR-019-automation-capability-entitlement-control-plane.md) Reaction Orchestrator | Target architecture; scattered `automation_rules` | Architecture + Platform | Already declared later in the Release Goal |
| [ADR-037](../architecture/ADR-037-lifecycle-identity-canon.md) Lifecycle Identity | Canon sealed; LI-1 ✅ merged; **LI-2…LI-4 queued** | Product Architecture | Declared residual; HE-2 consumes LI-1 only |
| [ADR-038](../architecture/ADR-038-shell-observability-diagnostics.md) Shell Observability / Collect diagnostics | Accepted; runtime not started | Platform / Shell | Declared residual — overlaps OL-4 signal work |
| [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) Unified Resource List Shell | Target model; lists still diverge (ListWorkspace unscheduled) | Platform UI | Declared residual |
| [ADR-016](../architecture/ADR-016-requirement-evidence-document-separation.md) Requirement / Evidence / Document | Accepted; P0 phased; dual evidence model persists | Platform | Consumed by RPM / HE-1 decision |
| [ADR-005](../architecture/ADR-005-three-level-settings-hierarchy.md) three-level settings | Company Module Settings layer missing (tied to Stage 5) | Architecture | Declared residual |
| [ADR-003](../architecture/ADR-003-tenant-company-module-data-boundaries.md) · [ADR-004](../architecture/ADR-004-five-product-modules-and-billing-events.md) · [ADR-006](../architecture/ADR-006-marketplace-and-integration-platform.md) · [ADR-008](../architecture/ADR-008-job-publishing-and-distribution.md) · [ADR-033](../architecture/ADR-033-lead-lifecycle-email-company-policy.md) · [ADR-034](../architecture/ADR-034-self-service-public-funnels.md) | Accepted with phased or partial adoption | Architecture / owning modules | Declared residual (none release-blocking) |
| [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md) Tenant Data Lifecycle | **Proposed** — accepted by OL-1 | Platform + Security | D1 (owned by Operate & Launch) |

### Maturity gaps

| Capability | State | Disposition |
|------------|-------|-------------|
| Entity Workspace Foundation 🔄 | brief-complete, not Complete | D2 (see also U-4) |
| Documents Foundation 🔄 | E7 / E8 done; consumer slots unbound | D2 — decided residual (was U-3) |
| Acquisition Automation 🔄 | Stage 5 / R6 residual | D2 |
| Forms Workspace / Automation ⏳ | P4 / P5 locked | D3 (P3 path is a v1 blocker brief) |
| Billing platform ⏳ | all stages | D3 (operator-assisted commerce is the v1 answer) |
| Platform analytics kit | never started | D2 |
| Cross-module Action / State / Relationship runtime | canon only | D2 |

---

## D3 — later, no action

C2.4 Communication Scheduling (frozen) · CL8 (forbidden by name) · Forms P4 Themes / P5 Analytics · Entity Workspace D10 · OCR product · Document packages Hub · Document approvals / e-sign · Phase F Billing · Phase G AI · Marketplace / tenant extensions / widget lifecycle · Billing / Fleet / Housing / Payroll domains · Entity Catalog Passport · Architecture RFC for Catalog Notifications ↔ Communication naming (A2-F1) · Acquisition R6 table cutover · Stage 5 settings / enable-disable · ListWorkspace as a program.

“Later” means deferred on purpose. Appearing in this list is **not** permission to start the item, and not a reason to treat it as the next Product.

---

## How this register is used

| Moment | Use |
|--------|-----|
| Before the [Release Readiness Gate](release-readiness-gate.md) opens | Every **U-row** must be decided (moved to D2 or into a slice). Entry condition EC-6 is not met otherwise. **Status 2026-08-28: D4 is empty** |
| In the closing record | Every **D2** row that touches the release perimeter is copied into § Named residuals with owner, expiry and the sentence a customer is told |
| When a new leftover is created | The slice that creates it adds a row here in the same PR. A leftover that exists only inside a gate record is invisible to the release decision |
| When a queue amendment schedules a blocker | The corresponding **D1** rows move with it; nothing is re-litigated |

This register is **not** a backlog to burn down. Most rows are supposed to stay open — the point is that they stay open **knowingly**.

---

## History

- 2026-08-30: **A closed row reopens as two, and the role switch moves.** The coverage guard delivered in TI-2 recognised tenant scope by the literal column name `tenant_id`, so it never saw `candidate_handoffs`, `candidate_handoff_snapshots` or `tenant_links` — the first two with row-level security switched off entirely, holding cross-tenant candidate presentations and personal snapshot payloads. They are fixed the same day, and the guard is widened in both dimensions it was thin on: any column ending in `tenant_id`, and a policy that can actually admit a write. One row stays open with an owner: `tenants` cannot be closed until the superadmin `/api/v1/platform` surface has a named elevated connection, which makes **TI-5** — not TI-4 — the precondition for switching the application role. D4 stays empty because both rows have owners.
- 2026-08-29: TI-3 part two delivered — the isolation suite passes under the restricted role. Two rows close (unsafe policy forms, test-bootstrap DDL) and one opens and closes in the same day: the tenant binding did not survive a commit, because a session returns its connection to the pool there, so RLS could not have worked at all under the previous design. D4 stays empty.
- 2026-08-29: TI-3 part one delivered — the unsafe-policy row closes, and one row opens for the platform-scope sentinel convention (15 tables written at application startup), which constrains both the remaining policy work and the connection split. D4 stays empty.
- 2026-08-29: TI-1 / TI-2 delivered. Two rows open from what real enforcement exposed — 78 policies that would error instead of denying, and a test bootstrap that needs DDL — both owned inside the isolation brief, so D4 stays empty. The isolation failures themselves shrank: three of the four were test defects.
- 2026-08-29: Two quality-debt rows close — the suite is now reproducible (identical 370-id set on two consecutive runs of `scripts/testing/measure-known-failures.sh`) and the stale alembic head pins are fixed. One row opens in their place: 74 tests are coupled to rows that outlive the run (54 fail only on a fresh database, 20 only on a warm one), which the fresh-database protocol contains but does not remove. D4 stays empty.
- 2026-08-28: Introduced. Full sweep of gate records, ADRs, maturity matrix, audits, security roadmap and task briefs produced 74 items; five (U-1…U-5) turned out to be release-relevant with no owner, and the rest were dispositioned D1 / D2 / D3. Created because the plan documented what would be built and never documented what would deliberately not be.
- 2026-08-28: **D4 emptied.** All five U-rows decided by the owner: U-1 → measure once on an authorised scratch test database and freeze the list (QB-1); U-2 → accept ADR-022 inside FP-1; U-3 / U-4 / U-5 → declared residuals with owners and customer sentences. EC-6 satisfied. Two briefs gain scope (pytest baseline, Forms Publish); nothing scheduled.
- 2026-08-28: **U-6 opened and decided the same day.** The QB-1 baseline measurement found database-level tenant isolation inert — 226 tables carry `tenant_id`, 102 have no policy, `FORCE ROW LEVEL SECURITY` is set nowhere, the application role is superuser with `BYPASSRLS`, and no restricted role is provisioned anywhere in the repository — while [security-ssot.md](../../security/security-ssot.md) §10 / §19 assert full coverage. Decision: close the gap before RC ([TI-1…TI-4](../tasks/tenant-isolation-enforcement.md)), so D4 is empty again. Three further quality-debt rows opened from the same measurement (non-reproducible suite, red architecture guard, stale alembic head pins), and the 44 off-blocker failures became a tolerated set with expiry 2027-01-31. 83 items.
- 2026-08-28: MOC-1…MOC-3 delivered — the two ownership-coverage rows close, and one new non-blocking row opens (Recruitment card wording). 79 items, 5 undecided (U-1…U-5, unchanged).
- 2026-08-28: +4 rows from the canon-hygiene pass — ownership-card coverage for Sales / Forms / Acquisition and the `leads` triple claim (D1, owned by [module ownership coverage](module-ownership-coverage.md)); the Rule 7 enforcement gap and the two empty module packages (D2). No new U-row: the coverage gaps are decided by that record, not deferred. 78 items.
