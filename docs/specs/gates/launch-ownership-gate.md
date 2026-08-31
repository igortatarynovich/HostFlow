# Launch Ownership Gate (OL-1)

**Status:** **PASS_WITH_CONSTRAINTS** (2026-08-31)
**Decision ID:** `OL1_LAUNCH_OWNERSHIP_PASS_WITH_CONSTRAINTS`
**Machine id:** `ol-contract`
**Type:** Named slice gate inside the Launch-ops track (not a product feature, not a release declaration)
**Parents:** [Operate & Launch](../tasks/operate-and-launch.md) (v1 blocker 6, OL-1) · [HostFlow v1 Release Goal](hostflow-v1-release-goal.md) blocker 6 · [Release Readiness Gate](release-readiness-gate.md) RR3 / RR4 / RR7 · [Runbook index](../../runbooks/README.md) · [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md) § Locked execution sequence
**Trusted base:** `integration/release-product-a-b`

> The first slice of the Launch-ops track. It writes **no procedure and no code** — it decides who is
> accountable, what the target is, which procedures must exist, and what counts as having executed
> one. OL-2…OL-7 write the procedures against these answers.
>
> This gate does **not** declare anything release-ready. Only the
> [Release Readiness Gate](release-readiness-gate.md) may do that.

---

## Formal decision

| Field | Value |
|-------|-------|
| **Outcome** | `PASS_WITH_CONSTRAINTS` |
| **Date** | 2026-08-31 |
| **Slice** | OL-1 Launch contract & ownership seal |
| **Unlocks** | **OL-2** Deploy, migrate & rollback (`ol-deploy`) — and, through it, the two remaining [TI-5](../tasks/tenant-isolation-enforcement.md) items |
| **Also unlocks** | **OL-6** Tenant lifecycle as product (`ol-tenant`), whose second condition was ADR-039 acceptance |

The outcome is `PASS_WITH_CONSTRAINTS` rather than `PASS` for one reason, stated in § Constraints:
all three release questions this slice had to assign are held by the same person, so RR7's escalation
step has no second party. The five requirements are met; the consequence of *how* requirement 2 is met
is the constraint.

---

## The five requirements, answered

### 1. Production target for v1

**One dedicated host running one compose stack.** Postgres, Redis, the backend, the ARQ worker and a
reverse proxy serving the built SPA, all on that host, from `docker-compose.yml` plus the profiles that
are today optional. The existing `hostflow.cc` instance is the shape being described, not a second
environment: it is where the procedures OL-2 writes will be rehearsed and then run.

Explicitly **not** v1: orchestration, multi-region, autoscaling, blue-green, IaC, a promotion pipeline
across environments. The brief permits a single host and this decision takes that permission.

**A consequence OL-2 and OL-5 inherit, recorded here so it is not discovered later.** With one host and
no staging environment, a rollback rehearsal and a restore drill cannot be performed on the production
host without risking the thing being protected. Both gates therefore require a **throwaway target
created for the drill and destroyed after it** — a second host for the duration, or a local stack with
the same compose file. "Executed on production" is not the evidence bar for OL-2's rollback step or
OL-5's restore drill; "executed on a target built by the same procedure" is. Choosing the cheap target
shape is legitimate; pretending it has no cost is not.

### 2. Owners of RR3, RR4, RR7

| Question | Scope | Named owner |
|---|---|---|
| **RR3** | Operability — deploy, roll back, monitor, recover from a written runbook | **igortatarynovich** |
| **RR4** | Tenant lifecycle — create, load, export, delete a tenant as product | **igortatarynovich** |
| **RR7** | Support & recovery — diagnose → escalate → mitigate → roll back → communicate | **igortatarynovich** |

Named, per the requirement: a person, not a role. The canon elsewhere assigns these layers to
*roles* — Engineering lead, Operational lead, Security owner
([ownership.md](../../governance/ownership.md)) — and those role names stay as the canonical layer
mapping. This table records who currently holds them, which is what the
[Release Readiness Gate](release-readiness-gate.md) needs in order to be answerable at all.

### 3. Required runbook set

Sealed as [`docs/runbooks/README.md`](../../runbooks/README.md) § Required set for v1: **RB-1…RB-10**,
each with the question it answers, its owner, the slice that writes it, and its status. **Ten required,
ten MISSING** as of this gate.

That number is the point of the index and is not a defect of this gate: OL-1 was required to make the
missing procedures *countable and owned*, not to write them. Changing the required set is a change to
blocker 6 scope and is made in [Operate & Launch](../tasks/operate-and-launch.md), not in the index.

### 4. What "executed" means

**A dated record naming the operator, the target, the build, and the observed result.** Each runbook
carries an **Execution log** table with those four columns; an empty log means the procedure has never
been executed, and an unexecuted procedure does not satisfy any gate's evidence bar.

Two clauses that make the definition bite rather than decorate:

- **The operator must not be the author** where the slice gate says so (OL-2 requires this explicitly).
  A procedure that only its writer can follow is not a procedure — it is notes.
- **The build must be identified** by tag or commit, not by "current". A record that cannot be tied to
  an artefact cannot be used as evidence that the artefact is deployable.

### 5. ADR-039 accepted

[ADR-039 Tenant Data Lifecycle](../architecture/ADR-039-tenant-data-lifecycle.md) moves
**Proposed → Accepted** on this gate, as its own Status line anticipated. OL-6 now has a contract to
implement against: five verbs owned by one platform capability, modules registering participants rather
than growing their own export and their own delete, and soft delete explicitly not counting as erasure.

Accepting it does **not** schedule OL-6 and does not create any endpoint. It removes the failure mode
where each module invents its own answer to a cross-module legal obligation.

---

## Constraints (named residuals)

| # | Residual | Impact | Owner | Expiry |
|---|---|---|---|---|
| **OL1-C1** | **One person owns RR3, RR4 and RR7.** RR7 asks for a path `diagnose → escalate → mitigate → roll back → communicate`. With a single holder, "escalate" has no destination, and an incident that begins with that person being unavailable has no path at all. | A customer-visible outage during the owner's absence has no defined response. This is a real v1 risk, not a documentation gap. | igortatarynovich | **OL-7** (`ol-support`) must either name a second party for escalation and customer communication, or record the single-person limit as an accepted release residual with the sentence the customer is told. |
| **OL1-C2** | **No staging environment**, by the target decision above. | OL-2's rollback step and OL-5's restore drill must build a throwaway target; neither may be evidenced on the production host. | igortatarynovich | OL-2 and OL-5 gates enforce it; no expiry, it is a property of the chosen target |

Both constraints are consequences of decisions taken deliberately, with their cost written down. Neither
is a reason to withhold the gate: OL-1's job was to make the accountability and the target explicit, and
an explicit single-person owner is strictly better than an unnamed role.

---

## What this gate does not do

- Does not write RB-1…RB-10 — OL-2…OL-7 own them, one slice per group.
- Does not choose a hosting vendor, an object-storage vendor, or SLO targets.
- Does not fix the migration blocker (`alembic upgrade heads` on a fresh database). That is **OL-2**,
  and it is the reason OL-2 is next.
- Does not declare RR3 / RR4 / RR7 answered. It makes them *answerable* by giving each a holder.
- Does not declare v1 release-ready, and no slice gate may.

---

## Evidence

| Requirement | Evidence |
|---|---|
| Production target defined | § 1 above; recorded in the queue's execution header and in [Operate & Launch](../tasks/operate-and-launch.md) |
| RR3 / RR4 / RR7 owners named | § 2 above; the owner cells in [Release Readiness Gate](release-readiness-gate.md) name the holder |
| Required runbook set enumerated with owner and status | [`docs/runbooks/README.md`](../../runbooks/README.md) — RB-1…RB-10, ten MISSING, each with owner and writing slice |
| "Executed" defined as a dated record | § 4 above; the Execution log contract in the runbook index § Rules |
| ADR-039 accepted | [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md) Status = Accepted (2026-08-31), this gate cited |

---

## History

- 2026-08-31: Gate recorded, `PASS_WITH_CONSTRAINTS`. Launch-ops opened by the same-day
  [queue amendment](../tasks/sales-to-comms-sequential-queue.md) § 8. Successor: **OL-2**, which owns
  the fresh-database migration blocker and therefore also gates the CI half of
  [TI-5](../tasks/tenant-isolation-enforcement.md).
- 2026-08-31 (later, note — the decision above is unchanged): the migration blocker referenced in
  § What this gate does not do and in the line above **was measured and does not exist** —
  `alembic upgrade heads` applies to a freshly created database in one command
  ([Operate & Launch § Correction](../tasks/operate-and-launch.md)). This does not alter the outcome,
  the five answers or either constraint; OL-2 remains the successor, with a corrected scope. One
  consequence for OL1-C1: OL-2's gate requires an operator who is not the author, so the
  **execution-witness** half of that residual is now an OL-2 entry condition, while the escalation half
  stays with OL-7 as recorded.
