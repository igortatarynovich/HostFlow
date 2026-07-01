# Phase 2.1 — physical drop runbook (staging → prod)

**Owner:** ops + Phase 2.1 author on call.
**Scope:** opening `HOSTFLOW_PHASE_2_1_DROP_OK=1` and physically
dropping `candidate_tasks` + `communication_planner_events`.
**Pre-reqs:** Phase 2.1 backend (commits `23cfd3e`, `2a905eb`) and
docs (`e94ff5c`) deployed; FE shim live; migration head
`202607150005_dptt`. Architectural background lives in
`docs/specs/architecture/phase-2-1-planner-tasks-into-activities.md`
(this runbook is the executable subset).

This runbook is **gating**. Each step has explicit pass/fail
criteria. Do **not** advance to the next step on amber. Do **not**
batch staging + prod.

---

## Step 0 — environment baseline (each env, in order: staging → prod)

For staging and then for prod, capture the deploy timestamp `T0`
(the moment Phase 2.1 backend was promoted). All "no writes after"
checks reference `T0`.

```bash
# In the relevant env's bastion / kubectl exec / docker exec.
psql -At -c "SELECT version_num FROM alembic_version;"
# Must print: 202607150005_dptt
```

**Pass:** head is `202607150005_dptt`.
**Fail:** any other revision → stop, escalate to Phase 2.1 owner.

---

## Step 1 — staging canary smoke

Goal: real tenant traffic exercises the rewired stack. Pick a
canary tenant with non-trivial planner / reminder volume. Time-box
the canary to **at least 24h** before advancing.

Exercise these flows on the canary tenant — observe both UI and
backend logs. Each item is a hard checkbox.

| # | Flow | Verify |
|---|------|--------|
| 1.1 | `CommunicationsCalendarPage` open | legacy planner-source rows render via FE shim; no console errors; no 4xx/5xx in backend logs for `/api/v1/activities` |
| 1.2 | Create planner-style event (call / meeting / shift) from calendar | row lands in `activities` with `metadata.planner.kind` (or native `Activity.type`); appears in calendar within 5s |
| 1.3 | Drag-to-reschedule on planner-source row + reminder-source row | both update; `Activity.starts_at` (planner) and `Activity.due_at` (reminder) shift correctly; conflict detection still fires for overlap |
| 1.4 | Resize planner-source row | `Activity.ends_at` updates |
| 1.5 | Move candidate to terminal stage (`archived` / `withdrew` / `cancelled`) | pending activities for that candidate flip to `cancelled` (G-1); bell notifications auto-marked read (G-9) |
| 1.6 | Same for lead terminal transition | pending lead-related activities → `cancelled` |
| 1.7 | `accept_handoff` / `return_handoff` on a candidate | re-runs cancellation logic without errors |
| 1.8 | Open Work Hub for an admin/supervisor; trigger team load recompute | `compute_managers_weighted_day_load` returns expected weights; planner-source activities use `metadata.planner.kind`, native rows fall through `_ACTIVITY_TYPE_TO_PLANNER_KIND` |
| 1.9 | UOS auto-activity flow (vacancy stage transition that creates a follow-up via `ensure_vacancy_recruiting_follow_up_task`) | activity created on `activities`, not `communication_planner_events`; appears in `MyTasksPanel` / `TodayPlannerPanel` / `RemindersPage` |
| 1.10 | Approve time-off overlapping a planner activity + a reminder activity for the same assignee | both flip to `cancelled` with `payload._cancelled_reason='timeoff_approved'` |
| 1.11 | Bulk-update / bulk-complete / bulk-cancel via `/api/v1/activities/bulk*` | FE shim still maps legacy bulk-PATCH calls correctly (status enum, payload replace); no 5xx |

**Pass:** all 11 items green for 24h on staging.
**Fail:** any item amber → stop, capture repro, file as Phase 2.1
regression. Do not advance.

---

## Step 2 — staging zero-writes audit

Run on the staging DB. SQL is the canonical block from
`phase-2-1-planner-tasks-into-activities.md` §"Reproducible audit
query".

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

**Pass criteria — all three must hold:**

1. Legacy `last_write` for `candidate_tasks` and
   `communication_planner_events` is **strictly older than `T0`**
   (the staging Phase 2.1 deploy timestamp).
2. `phase_2_1_backfill_audit` has at least one row with
   `candidate_tasks_inserted == candidate_tasks_total` **and**
   `planner_events_inserted == planner_events_total`.
3. Row count of `activities WHERE legacy_source IS NOT NULL`
   equals `candidate_tasks_total + planner_events_total` from the
   most recent audit row.

**Fail:** any criterion amber → stop, investigate the writer
(check cron, BI, admin scripts). Do not advance.

Also re-confirm the FE-side sweep:

```bash
rg "/communications/planner/events" hostflow-frontend/src \
  | rg -v "src/api/communications.ts"
# Expected: zero matches.

rg "/api/v1/candidates/[^/]+/tasks" hostflow-frontend/src
# Expected: zero matches.
```

**Pass:** zero matches outside the FE shim.

---

## Step 3 — prod-snapshot rollback drill

Goal: prove the migration round-trip is data-preserving on a
**copy of prod**. Required because the dev rollback drill only
exercised the soft-gate path (legacy source tables empty) — see
`phase-2-1-planner-tasks-into-activities.md` §"Dev — caveat".

Use whatever the prod-snapshot mechanism is (logical replica /
restored backup / PITR clone). Do **not** run on live prod.

```bash
# Snapshot before
psql -At -c "
SELECT 'activities='   || COUNT(*) FROM activities
UNION ALL SELECT 'activities_legacy=' || COUNT(*)
  FROM activities WHERE metadata::jsonb ->> 'legacy_source' IS NOT NULL
UNION ALL SELECT 'candidate_tasks='   || COUNT(*) FROM candidate_tasks
UNION ALL SELECT 'planner_events='    || COUNT(*) FROM communication_planner_events
UNION ALL SELECT 'audit_rows='        || COUNT(*) FROM phase_2_1_backfill_audit;
"

alembic downgrade 202607150003_cvla   # downgrade past 004_pti
psql -At -c "<same query>"            # snapshot mid

alembic upgrade head                  # back to 005_dptt (still gated on the snapshot)
psql -At -c "<same query>"            # snapshot after
```

**Pass criteria:**

1. After `alembic downgrade 202607150003_cvla`:
   - `activities_legacy` drops to 0 (legacy_source rows removed).
   - `candidate_tasks` and `planner_events` row counts unchanged.
   - `audit_rows` drops to 0 (audit table removed by 004's downgrade).
2. After `alembic upgrade head`:
   - `activities_legacy` returns to the **exact** pre-downgrade
     count (re-backfilled from still-populated legacy tables).
   - `candidate_tasks` and `planner_events` unchanged.
   - `audit_rows` ≥ 1; the new row's `*_inserted` equals
     `*_total` and matches `activities_legacy`.

**Fail:** any drift → stop. Phase 2.1 backfill is not
round-trip-clean against prod data; investigate before continuing.

---

## Step 4 — staging physical drop (gate-open dry run)

Open the gate on staging only. Verify the upgrade actually drops
and the schema settles.

```bash
HOSTFLOW_PHASE_2_1_DROP_OK=1 alembic downgrade 202607150004_pti
HOSTFLOW_PHASE_2_1_DROP_OK=1 alembic upgrade head
```

The double-step is mandatory — `alembic upgrade head` alone is a
logged no-op once `202607150005_dptt` is already recorded.

```bash
psql -At -c "
SELECT relname FROM pg_class
 WHERE relname IN ('candidate_tasks','communication_planner_events')
   AND relnamespace = 'public'::regnamespace;
"
```

**Pass:** zero rows returned. Tables are physically gone on
staging.

Re-run staging canary smoke (Step 1) for at least **24h more**
post-drop. If any 1.x item regresses on staging-without-the-tables,
the issue is a hidden reader and prod must wait. Filter backend
logs for `relation .* does not exist` against the dropped names —
zero hits expected.

---

## Step 5 — prod physical drop

Only after Steps 1-4 are green on every environment **and**
post-drop staging is clean for ≥24h.

```bash
HOSTFLOW_PHASE_2_1_DROP_OK=1 alembic downgrade 202607150004_pti
HOSTFLOW_PHASE_2_1_DROP_OK=1 alembic upgrade head
```

Verify:

```bash
psql -At -c "
SELECT relname FROM pg_class
 WHERE relname IN ('candidate_tasks','communication_planner_events')
   AND relnamespace = 'public'::regnamespace;
"
# Expected: zero rows.
```

Then re-run the audit query from Step 2 once more on prod for the
record:

* legacy table queries should now error
  (`relation "candidate_tasks" does not exist`) — that is the
  expected post-drop state.
* `activities_legacy` count is unchanged from pre-drop.
* `phase_2_1_backfill_audit` is intact (it's a separate table).

Tag the prod deploy timestamp `T_drop`. From this point Phase 3
cleanup (`p3-*`) is unblocked.

---

## Rollback procedure (if any step fails)

Phase 2.1 is forward-only by design — once the physical drop has
landed on prod, rollback means **restoring from backup**. Before
that point:

* Failure during Step 4 (staging drop) → `alembic downgrade
  202607150004_pti` (no flag needed; recreates empty tables) +
  redeploy previous backend image. Resume from Step 1 once the
  cause is fixed.
* Failure during Steps 1-3 → no DDL has run; just back the
  triggering deploy out and resume.
* Failure during Step 5 (prod drop) → restore prod from the most
  recent backup taken **before** the gate was opened. The backfill
  rows in `activities` (carrying `metadata.legacy_source`) are
  lossless against prod data, so worst case prod re-runs the
  backfill on the restored snapshot.

---

## Open-the-gate criteria (summary)

`HOSTFLOW_PHASE_2_1_DROP_OK=1` may be set on prod **only** when:

- [ ] Step 0 baseline green on prod (head = `202607150005_dptt`).
- [ ] Step 1 canary smoke green on staging for ≥24h.
- [ ] Step 2 zero-writes audit green on staging **and** prod.
- [ ] Step 3 rollback drill green on prod-snapshot.
- [ ] Step 4 physical drop green on staging + post-drop canary
      green on staging for ≥24h.
- [ ] On-call ack from Phase 2.1 owner.

Recorded in this branch's PR description.
