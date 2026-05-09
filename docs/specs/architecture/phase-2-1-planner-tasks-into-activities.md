# Phase 2.1 — Planner / Candidate-Tasks into Activities

Status: **accepted / done (engineering)** as of 2026-05-09. Backfill,
service rewire, backend route removal, FE shim and docs are all
landed; the **physical drop** of the legacy tables is intentionally
held behind the `HOSTFLOW_PHASE_2_1_DROP_OK=1` soft-gate (see
"Drop revision" below). Next gate is canary on a real tenant +
verification that the legacy tables receive no new writes — only
then the gate is opened.

Linked artefacts:

* ADR-012 (`./ADR-012-activity-notification-operating-layer.md`).
* Phase 1.3 plan (`./phase-1-3-activity-layer-v1-migration-plan.md`).
* Alembic 202607150004 (backfill) and 202607150005 (drop).

This document captures the **operational notes** an operator needs to
read before driving Phase 2.1 to completion. The full design /
mapping / DDL CASE table is in the migration revisions themselves
(see their module docstrings) and the agent transcripts that
accepted the plan.

---

## Removal sequencing (binding)

Phase 2.1 removes two duplicate task surfaces (`candidate_tasks`,
`communication_planner_events`). The order is **fixed**:

1. **Backfill** (`202607150004_pti`) — applied. Legacy rows are
   projected into `activities` with `metadata.legacy_source` markers.
2. **Backend service rewire** (`p21-svc`) — applied. No service reads
   or writes the legacy tables; cancel / load / sweep paths route
   through `Activity` exclusively. Counter names (e.g.
   `planner_events_cancelled`) are kept verbatim through Phase 4 for
   log/metric compatibility — the bucketing rule is now
   `Activity.starts_at IS NULL` (deadline) vs `IS NOT NULL`
   (time-bound).
3. **Backend route removal** (`p21-be-rm`) — **DONE 2026-05-09**.
   `backend/app/api/v1/candidate_tasks.py` deleted; `app/main.py` no
   longer mounts the candidate-tasks router; `communications/routes/
   planner.py` keeps only working-hours / availability / time-off and
   no longer exposes `GET/POST/PATCH/DELETE /communications/planner/
   events*`. Schemas / DTOs (`CommunicationPlannerEventOut`,
   `CommunicationPlannerEventListResponse`,
   `CommunicationPlannerEventCreate/Patch`, `_planner_event_out`) are
   removed. Tests that hit the legacy URLs were either deleted as
   superseded or rewritten to use `/api/v1/activities`. The ORM
   `CommunicationPlannerEvent` is left in place behind
   `ensure_communications_schema.py` until the drop gate opens (step 7).
4. **Frontend shim** (`p21-fe-rm`) — **DONE 2026-05-09**. The four
   legacy callers (`getCommunicationPlannerEvent`,
   `listCommunicationPlannerEvents`, `createCommunicationPlannerEvent`,
   `patchCommunicationPlannerEvent`) live in
   `hostflow-frontend/src/api/communications.ts` with the **same
   call signatures and return types** but internally hit
   `/api/v1/activities` and remap fields planner-event ↔ activity
   (`kind ↔ type`, `start_at ↔ due_at`, `end_at ↔ due_at +
   duration_minutes`, `all_day ↔ payload._planner_all_day`,
   `linked_candidate_id` / `linked_company_id` ↔
   `entity_type` / `entity_id`, planner statuses
   `new`/`pending`/`sent`/`overdue` normalised to `planned` on read,
   `done` patch routes to `POST /activities/{id}/complete`).
   `CommunicationsCalendarPage`, `RemindersPage`, `MyTasksPanel` and
   `TodayPlannerPanel` continue to work unchanged. `rg
   "/communications/planner/events" hostflow-frontend/src` returns
   nothing live. **The shim is temporary** — Phase 3 deletes it and
   migrates the four UI consumers to native Activity types and helpers.
5. **Docs** (`p21-docs`) — **DONE 2026-05-09**. ADR-012 history /
   roadmap table updated; planner / reminders specs marked
   superseded; operations-loop §1 / §2.3 / §2.4 / §G-2 reflect the
   new state; canon §7 (mapping table) marks `candidate_tasks` and
   `communication_planner_events` as absorbed; this document moved
   to "accepted / done".
6. **Canary** — pending. Smoke test the rewired services on a real
   tenant; verify zero new writes to `candidate_tasks` /
   `communication_planner_events` (audit query in §"Acceptance"
   below).
7. **Drop legacy tables** — pending. Only after every step above is
   green. See "Drop revision (202607150005_dptt)" below.

Skipping any step risks either silently dropping rows the rewire
hasn't yet caught (4 → 7 reverses the safety) or breaking the
frontend mid-canary (3 → 4 ditto).

---

## Drop revision (`202607150005_dptt`) — important nuance

The drop revision is **soft-gated** behind the env flag
`HOSTFLOW_PHASE_2_1_DROP_OK=1`. Behaviour:

* `alembic upgrade head` (no flag) → revision is **recorded** in
  `alembic_version` but `upgrade()` is a logged no-op. The legacy
  tables (`candidate_tasks`, `communication_planner_events`) are
  intentionally left in place.
* `HOSTFLOW_PHASE_2_1_DROP_OK=1 alembic upgrade head` → the same
  logical revision physically drops the tables.

This means:

* **Revision 202607150005_dptt may be `applied` logically while the
  physical drop has not happened.** Do not interpret a green
  `alembic current` / `alembic upgrade head` as proof that the
  legacy tables are gone.
* **Physical drop requires a re-run** with the gate open:

  ```bash
  alembic downgrade 202607150004_pti
  HOSTFLOW_PHASE_2_1_DROP_OK=1 alembic upgrade head
  ```

  The `downgrade` step doesn't touch `activities` — the backfill
  revision (`202607150004_pti`) already keeps its rows on
  downgrade unless its own downgrade is invoked. Only the drop
  revision flips state on re-upgrade.
* Until that explicit re-run, **the legacy tables intentionally
  remain on every environment** (dev, staging, prod). New writes to
  the legacy tables would be a regression — the rewire ensures no
  service reaches them, and the route removal (step 3) removes the
  remaining external write surface.

Audit:

* The backfill revision writes to `phase_2_1_backfill_audit` on every
  invocation (one row per `upgrade()`). The downgrade adds a second
  row with deletion counts. Operators can verify the canonical row
  count matches the audit before opening the drop gate:

  ```sql
  SELECT kind, payload, created_at FROM phase_2_1_backfill_audit
   ORDER BY id;
  ```

* Before opening the gate, also confirm the legacy tables are
  receiving **zero new writes** since route removal landed
  (2026-05-09). Quick smoke:

  ```sql
  SELECT MAX(updated_at) AS last_legacy_write,
         COUNT(*)        AS legacy_row_count
    FROM candidate_tasks;

  SELECT MAX(updated_at) AS last_legacy_write,
         COUNT(*)        AS legacy_row_count
    FROM communication_planner_events;
  ```

  `last_legacy_write` should be **strictly older** than the route
  removal deploy timestamp on every environment. Any row newer than
  that means a service or job still reaches the legacy table and the
  gate must stay closed until that source is identified.

---

## Next gate after `p21-docs`

Phase 2.1 engineering is complete; the remaining work is operational.
This section is the **canonical pre-drop checklist** — every item
must be green on every environment before opening
`HOSTFLOW_PHASE_2_1_DROP_OK=1`.

### 1. Canary smoke on a staging tenant

Exercise the rewired stack with realistic volume. The list is
deliberately broad — Phase 2.1 touched read paths, write paths,
cancel paths and load-weight paths, so each one needs a live
sanity check:

* **Planner UI** — open `CommunicationsCalendarPage`, observe
  legacy planner-source rows render via the FE shim; create a new
  planner-style event (call / meeting / shift), verify it lands as
  an `Activity` with the expected `metadata.planner.kind` (or
  `Activity.type` for native creates) and shows up in the calendar
  immediately.
* **Calendar flows** — drag-to-reschedule on both planner-source
  and reminder-source rows (G-7 unification); resize on
  planner-source rows; conflict detection still fires.
* **Lifecycle cancellations** — move a candidate to a terminal
  stage, then to `archived` / `withdrew` / `cancelled`; verify
  pending activities for that candidate flip to `cancelled` (G-1)
  and bell notifications for that candidate are auto-marked read
  (G-9). Same drill for lead terminal transition. Re-run after
  manual `accept_handoff` / `return_handoff`.
* **Assignee load** — open Work Hub for an admin/supervisor;
  trigger team load recompute (assign several activities to one
  recruiter); verify `compute_managers_weighted_day_load` returns
  the expected weights using `_activity_planner_kind` (legacy rows
  preserve `metadata.planner.kind`, native rows fall through
  `_ACTIVITY_TYPE_TO_PLANNER_KIND`).
* **Follow-up creation** — drive a UOS auto-activity flow (e.g.
  vacancy-stage transition that creates a follow-up via
  `ensure_vacancy_recruiting_follow_up_task`); verify the activity
  is created on `activities`, not `communication_planner_events`,
  and appears in `MyTasksPanel` / `TodayPlannerPanel` /
  `RemindersPage`.
* **Time-off cleanup** — approve a time-off request that overlaps
  with an existing planner-style activity and a reminder-style
  activity for the same assignee; verify both flip to `cancelled`
  with `payload._cancelled_reason='timeoff_approved'`.
* **Bulk activity operations** — bulk-update / bulk-complete /
  bulk-cancel via `/api/v1/activities/bulk*` (whichever bulk
  endpoints the tenant uses); verify the FE shim still maps legacy
  bulk-PATCH calls correctly (status enum, payload replace).

### 2. Zero new writes in legacy tables

Run the audit query (see "Audit" earlier in this document) on
every environment. `last_legacy_write` must be **strictly older**
than the route-removal deploy timestamp (2026-05-09 + canary
window). Any newer row means a writer still reaches the legacy
table — investigate before opening the gate.

### 3. Pre-drop "is anyone still reading legacy tables" sweep

Route removal kills HTTP-level writers, but the physical drop also
breaks any non-HTTP code path. Confirm none of the following exist
on production / staging / dev:

* **Cron / job / background worker** writing or reading
  `candidate_tasks` / `communication_planner_events`. Check:
  Celery / RQ task definitions, `apscheduler` jobs,
  `services/communications_scheduler.py` tick handlers, any
  cron entries on the host. `rg
  "communication_planner_events|candidate_tasks" backend/` is the
  fast filter.
* **BI / export / report SQL** that reads the planner / tasks
  tables directly. Check the analytics warehouse / dbt project /
  Looker / Metabase / any tenant-facing export module
  (`services/exports/*`, `services/analytics/*`). Direct reads
  against the live OLTP planner table after drop will fail; reads
  against a snapshot copy still need re-pointing to `activities`
  with the `metadata.legacy_source='communication_planner_events'`
  filter.
* **Ad-hoc admin scripts** — anything in `scripts/`, `tools/`,
  ops runbooks (`docs/runbooks/`, internal wiki) that references
  the legacy tables by name. Replace with `/api/v1/activities`
  before drop.
* **Frontend polling via legacy typed adapters** — confirm `rg
  "/communications/planner/events" hostflow-frontend/src` returns
  zero hits **outside** the FE shim itself (i.e., no UI page is
  bypassing `getCommunicationPlannerEvent` /
  `listCommunicationPlannerEvents` /
  `createCommunicationPlannerEvent` /
  `patchCommunicationPlannerEvent` and hitting the URL string
  directly). This was clean as of `p21-fe-rm` close; re-confirm
  before drop because a Phase 3 prep PR could re-introduce it.

### 4. Rollback drill

Before opening the gate, prove that the migration round-trip is
still clean on a snapshot of prod:

```bash
alembic downgrade 202607150004_pti
alembic upgrade head
```

Verify consistency counts after each step using the
`phase_2_1_backfill_audit` query and the row-count audit (see
"Audit" earlier). The drop revision is idempotent (table-existence
guards), but the rollback drill confirms the gate-open path is
boring before it touches prod.

### 5. Open the gate and physically drop

Only after 1-4 are green on every environment:

```bash
HOSTFLOW_PHASE_2_1_DROP_OK=1 alembic downgrade 202607150004_pti
HOSTFLOW_PHASE_2_1_DROP_OK=1 alembic upgrade head
```

The re-run sequence is mandatory — `alembic upgrade head` alone is
a logged no-op once the revision is already recorded (see "Drop
revision" earlier). After the physical drop, the legacy tables are
gone; `ensure_communications_schema.py` will re-create
`communication_planner_events` on dev SQLite the next time it
runs, which is fine for dev (no writers reach it) and is
explicitly removed in Phase 3 cleanup.

### 6. Phase 3 cleanup (only after the physical drop)

1. Delete the FE shim in
   `hostflow-frontend/src/api/communications.ts` (the four
   `*PlannerEvent*` functions and the `_planner*` helpers).
2. Migrate `CommunicationsCalendarPage`, `RemindersPage`,
   `MyTasksPanel`, `TodayPlannerPanel` to native Activity types
   and helpers.
3. Remove the transitional fields (`status`, `type`,
   `entity_type`, `entity_id`, `payload`) from
   `ReminderUpdateRequest` and the matching branches in
   `services/reminder_tasks.update_reminder`. Specifically remove
   the **wholesale `payload` replace** branch — Phase 3 must not
   leave it behind as a long-term update mode for Activity. If
   any consumer still legitimately needs to replace `payload` or
   re-anchor `entity_type` / `entity_id`, introduce dedicated
   endpoints (`PUT /activities/{id}/payload`, `POST
   /activities/{id}/relink`) rather than reattach those fields to
   PATCH.
4. Delete the ORM `models/communication.py::CommunicationPlannerEvent`
   and `models/candidate_children.py::CandidateTask`.
5. Delete `app/services/ensure_communications_schema.py` legacy
   branch (the planner-table bootstrap).
6. Drop legacy aliases / synonyms (e.g. `Reminder = Activity` ORM
   alias once Phase 4 lands; planner-status normalisation in any
   remaining call site; `metadata.planner.kind` lookup in
   `team_assignee_auto._activity_planner_kind` once all backfilled
   rows have aged out).
7. Frontend rename pass — final UI semantics under Activity (no
   "planner event" wording in component names, store keys,
   i18n keys, or telemetry events).

---

## Operational-gate evidence — dev (2026-05-09)

Recorded after the recovery commit (`23cfd3e`) + startup-fix commit
(`2a905eb`) that re-applied the Phase 2.1 backend work lost to a
`git reset` and resolved the `sqlalchemy.exc.InvalidRequestError`
double-registration of the `activities` table that the recovery had
exposed. Captured against the local docker-compose dev DB; the same
queries / commands are what staging and prod should run before
opening `HOSTFLOW_PHASE_2_1_DROP_OK=1`.

### Dev — section 2 (zero-writes audit)

```text
              tbl              |  rows   |          last_write
-------------------------------+---------+-------------------------------
 activities                    |    5865 | 2026-05-09 19:29:13.887323+00
 activity_events               |    2451 | 2026-05-09 19:29:13.880096+00
 candidate_tasks (LEGACY)      |       0 | (no rows, no writes)
 communication_planner_events  |       0 | (no rows, no writes)
 notifications                 | 3546699 | 2026-05-09 19:28:59.227338+00
```

`phase_2_1_backfill_audit` row (single):

```json
{ "candidate_tasks_total": 0, "planner_events_total": 50,
  "candidate_tasks_inserted": 0, "planner_events_inserted": 50,
  "missing_due_on": 0, "unparseable_due_on": 0,
  "unresolved_related_entities": 41 }
```

Compat-view runtime guard is in place: `INSTEAD OF
{INSERT,UPDATE,DELETE}` triggers `reject_writes_reminders` and
`reject_writes_user_notifications` are present on `reminders` /
`user_notifications` (verified via `information_schema.triggers`).
Code-level audit (`rg "(db|session)\.add\(\s*(CommunicationPlannerEvent|CandidateTask)\b"`)
returns zero hits in `backend/app/`; the only matches are the ORM
class declarations themselves and one `tests/test_owner_fk_set_null.py`
fixture (test code, not a runtime writer — folded into Phase 3
cleanup `p3-orm-rip-*`).

### Dev — section 4 (rollback drill, soft-gate path)

Run inside the backend container:

```bash
docker compose exec -T backend alembic downgrade 202607150004_pti
docker compose exec -T backend alembic upgrade head
```

Snapshots match across all three checkpoints:

```text
                       BEFORE       AFTER DOWNGRADE   AFTER UPGRADE
head=                  005_dptt     004_pti           005_dptt
activities_total=      5865         5865              5865
activities_legacy=     50           50                50
candidate_tasks_rows=  0            0                 0
planner_events_rows=   0            0                 0
audit_rows=            1            1                 1
```

The re-upgrade emits the soft-gate warning as designed:

> `WARNI [phase_2_1] DROP revision is gated; tables left in place
> (candidate_tasks_present=yes, planner_events_present=yes). Set
> HOSTFLOW_PHASE_2_1_DROP_OK=1 to actually drop them after canary
> completes.`

This validates the soft-gate end-to-end: `alembic upgrade head` is
non-destructive on every environment that has not opted into the
gate, and the version-num round-trip preserves data and audit rows.

### Dev — caveat for the prod-style 004 drill

Downgrading **past** `202607150004_pti` (the backfill) is destructive
on dev because `candidate_tasks` and `communication_planner_events`
are empty here (post-backfill state) — `downgrade()` deletes the
50 rows in `activities` carrying `metadata.legacy_source`, and a
re-`upgrade` re-runs the backfill against now-empty source tables,
inserting nothing. Net loss: 50 activities. The full
`alembic downgrade 202607150003_cvla && alembic upgrade head`
round-trip with row-count consistency belongs on a **prod-snapshot**
environment where the legacy source tables still hold data and the
re-upgrade can re-populate the activities rows. That drill is the
gating evidence for `p21-rollback-drill` and is intentionally
excluded from the dev-env recipe above.

### Reproducible audit query (any environment)

```sql
SELECT 'activities' AS tbl, COUNT(*) AS rows, MAX(updated_at) AS last_write
  FROM activities
UNION ALL SELECT 'activity_events', COUNT(*), MAX(created_at) FROM activity_events
UNION ALL SELECT 'notifications',   COUNT(*), MAX(created_at) FROM notifications
UNION ALL SELECT 'candidate_tasks (LEGACY)',
                 COUNT(*), MAX(updated_at) FROM candidate_tasks
UNION ALL SELECT 'communication_planner_events (LEGACY)',
                 COUNT(*), MAX(updated_at) FROM communication_planner_events
ORDER BY tbl;

SELECT metadata::jsonb ->> 'legacy_source' AS legacy_source, COUNT(*) AS rows
  FROM activities
 WHERE metadata::jsonb ->> 'legacy_source' IS NOT NULL
 GROUP BY 1 ORDER BY 1;

SELECT * FROM phase_2_1_backfill_audit ORDER BY created_at DESC LIMIT 5;
```

Acceptance for the audit on staging / prod: legacy `last_write` is
strictly older than the Phase 2.1 route-removal deploy timestamp
(2026-05-09); `phase_2_1_backfill_audit` has at least one row with
`candidate_tasks_inserted == candidate_tasks_total` and
`planner_events_inserted == planner_events_total`; row count of
`activities WHERE legacy_source IS NOT NULL` equals
`candidate_tasks_total + planner_events_total` from that audit row.

---

## What "service rewire" means concretely (`p21-svc`)

Files touched:

* `app/services/timeoff_cleanup.py` — both reminder-style and
  planner-style cancellation now query `Activity`. The split is on
  `Activity.starts_at IS NULL` (deadline) vs `IS NOT NULL`
  (time-bound). Counters keep their old names.
* `app/services/lead_lifecycle.py` — `_cancel_lead_planner_events`
  reads `Activity` with `starts_at IS NOT NULL`,
  `related_entity_type='lead'`. `sweep_converted_lead_operational_noise`
  reads its planner subquery from `Activity` too.
  `_cancel_lead_reminders` is scoped to `starts_at IS NULL` so it
  doesn't double-process time-bound rows.
* `app/services/candidate_lifecycle.py` — same pattern. The
  candidate-link predicate also covers
  `metadata.planner.linked_candidate_id` for backfilled rows where
  the original `linked_candidate_id` differed from the entity FK.
* `app/services/team_assignee_auto.py` —
  `compute_managers_weighted_day_load` reads `Activity` directly.
  The "planner kind" used for load weighting is resolved by the new
  helper `_activity_planner_kind`: `metadata.planner.kind` wins for
  backfilled rows (preserves `shift`), otherwise `Activity.type` is
  mapped via `_ACTIVITY_TYPE_TO_PLANNER_KIND`.
* `app/services/assignee_load_taxonomy.py` — docstrings updated.
  Constants (`PLANNER_KIND_BASE_WEIGHT`,
  `PLANNER_STATUS_LOAD_MULT`, etc.) stay — they are valid weights
  for the canonical activity load model.
* `app/services/communications_scheduler.py` — no DB read; just
  reads `stats.get("planner_events_cancelled", ...)` and adds it to
  the tick summary. Counter is still produced by
  `lead_lifecycle.sweep_converted_lead_operational_noise`.

Files **deliberately not** touched:

* `app/services/ensure_communications_schema.py` — bootstraps the
  legacy table on dev SQLite. Required while the table physically
  exists. Removed together with the table after the drop gate opens.

---

## Transitional backend addition — `ReminderUpdateRequest` (Phase 2.1 only)

To keep the FE shim functional without touching UI pages, a small
**transitional** extension was made to the canonical Activity update
contract on the backend. This change is acceptable as a Phase 2.1
crutch, but Phase 3 **must** revert it to native Activity semantics.

What changed:

* `backend/app/api/v1/reminders_v2.py::ReminderUpdateRequest` gained
  five optional fields:
  * `status` — accepts the closed Activity enum values plus the
    legacy planner statuses `new`/`pending`/`sent`/`overdue` so the
    shim can pass them through verbatim. The service layer validates
    the set and rejects anything else with `HTTP 400`.
  * `type` — mirror of legacy planner `kind`.
  * `entity_type` / `entity_id` — re-link the activity to a different
    domain entity (planner allowed re-anchoring via
    `linked_candidate_id` / `linked_company_id`).
  * `payload` — replaces the row's payload blob **wholesale**, mirroring
    legacy planner PATCH semantics (planner-event PATCH replaced
    `payload`; Activity PATCH historically merged it). This is the
    most invasive part of the transitional contract; see "Why this is
    transitional" below.
* `backend/app/services/reminder_tasks.update_reminder` consumes those
  fields when present and ignores them when absent. Validation lives
  next to the field assignment so the existing PATCH contract for
  callers that do **not** use the shim is unchanged.

Why this is transitional and what Phase 3 must do:

* The shim only exists because the legacy planner PATCH was a
  blob-replace operation and we did not want to rewrite the four UI
  pages that still call `patchCommunicationPlannerEvent`. Phase 3
  deletes the shim, so these fields are then **dead surface**.
* `payload` wholesale-replace is **not** the long-term update model
  for Activity. The canonical update model is **domain-specific
  PATCH** of named fields (e.g. `description`, `priority`,
  `assignee_id`, `due_at`, `duration_minutes`, …). Allowing
  `payload` replace anywhere except this shim risks letters lost in
  the blob (e.g. `_working_hours_shift` diagnostics, source-marker
  metadata, automation-rule fingerprints) — those *do* belong in
  `payload` but must be preserved on PATCH.
* Phase 3 cleanup checklist:
  1. Delete the four shim functions in
     `hostflow-frontend/src/api/communications.ts`.
  2. Migrate `CommunicationsCalendarPage`, `RemindersPage`,
     `MyTasksPanel`, `TodayPlannerPanel` to call native
     `listActivities` / `createActivity` / `patchActivity` /
     `completeActivity` (already exposed) with native Activity
     types — no remap helpers.
  3. Remove `status`, `type`, `entity_type`, `entity_id`, `payload`
     from `ReminderUpdateRequest` and from `update_reminder`.
  4. If any caller still legitimately needs to re-anchor an
     activity to a different entity or replace the payload blob,
     introduce **dedicated** endpoints (`POST
     /activities/{id}/relink`, `PUT /activities/{id}/payload`)
     rather than re-introducing them as side fields on the generic
     PATCH.

The change is intentionally narrow (one schema, one service
function, validated set of statuses) so reverting it in Phase 3 is
a small, mechanical patch.

---

## Acceptance for `p21-svc`

* `rg "CommunicationPlannerEvent" backend/app/services/` returns only
  docstrings/comments and `ensure_communications_schema.py`. No
  imports / queries / writes anywhere else.
* `pytest tests/test_timeoff_cleanup.py tests/test_lead_lifecycle.py
  tests/test_team_assignee_auto.py` is green.
* `pytest tests/migrations/test_phase_2_1_round_trip.py` is green
  (idempotent backfill + downgrade still works on SQLite).

These were verified on 2026-05-09.

---

## Pre-existing issue (not part of Phase 2.1)

* `tests/api/test_uos_candidate_stage_auto_activities.py::
  test_uos_candidate_stage_follow_up_on_patch` returns 409 because of
  a fixture / data-setup race that pre-dates this work. Tracked
  separately as `rodo-409-followup`. **Do not** mix with Phase 2.1
  diagnostics.
