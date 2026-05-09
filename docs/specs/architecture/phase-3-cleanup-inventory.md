# Phase 3 cleanup inventory (no code yet)

**Status:** prep only — locked targets list. Phase 3 code is gated
on the physical drop landing on prod (see
`docs/specs/runbooks/phase-2-1-drop-runbook.md` Step 5). This
document is the canonical "what to delete / revert / rename" list
the next engineer (or follow-up PR series) walks through, in
order. **Do not start Phase 3 work until the gate has opened on
prod and post-drop staging+prod canary is clean for ≥24h.**

Each section calls out:
* exact files
* the symbols / branches / fields to remove
* tests to add or rewrite
* acceptance signal

The order below is the safe order — earlier items remove forward
callers, later items remove the now-orphan backend pieces.

---

## p3-fe-shim-rip — delete the FE planner-event shim

**File:** `hostflow-frontend/src/api/communications.ts`

**Remove:**
* `getCommunicationPlannerEvent`
* `listCommunicationPlannerEvents`
* `createCommunicationPlannerEvent`
* `patchCommunicationPlannerEvent`
* All `*PlannerEvent`-named helpers introduced for field remapping
  (kind ↔ type, start_at/end_at ↔ due_at, etc.).

**Type cleanup:** drop the `CommunicationPlannerEvent*` type
exports in the same file (they are shim-only contracts and have
no consumer once the page-side migration in `p3-fe-pages-native`
lands).

**Acceptance:**

```bash
rg "(get|list|create|patch)CommunicationPlannerEvent" hostflow-frontend/src
# Zero matches.
rg "/communications/planner/events" hostflow-frontend/src
# Zero matches (already enforced by Phase 2.1 verify).
```

**Pre-condition:** all consuming pages migrated to native Activity
types — see next item. Land `p3-fe-pages-native` first; this PR
is the cleanup that follows.

---

## p3-fe-pages-native — migrate UI pages to native `Activity`

**Pages to migrate** (call counts as of Phase 2.1 close):

| File | Shim calls | Notes |
|------|------------|-------|
| `hostflow-frontend/src/pages/CommunicationsCalendarPage.tsx` | 21 | heaviest user; calendar drag-resize / conflict detection touches the field remap |
| `hostflow-frontend/src/pages/RemindersPage.tsx` | 9 | mixed planner + reminder rows |
| `hostflow-frontend/src/pages/CommunicationsPlannerPage.tsx` | 6 | the legacy "planner" landing page; rename pass also lives here (`p3-frontend-rename`) |
| `hostflow-frontend/src/modules/workHub/MyTasksPanel.tsx` | 3 | |
| `hostflow-frontend/src/modules/workHub/TodayPlannerPanel.tsx` | 3 | |

**Migration:** swap each shim call for the canonical
`listActivities` / `getActivity` / `createActivity` /
`patchActivity` from the activities API surface; replace
`CommunicationPlannerEvent*` types with the canonical `Activity` /
`ActivityType` / `ActivityStatus`. Field remap moves from the FE
shim into each page's mapper if the page genuinely needs the
planner kind taxonomy (`metadata.planner.kind`).

**Tests to update:**
* component tests for each of the 5 pages (replace mocked planner
  responses with mocked `Activity` rows);
* any e2e / playwright spec that touches the calendar UI.

**Acceptance:**
* `tsc` passes with no `CommunicationPlannerEvent*` references in
  the React tree.
* visual smoke: each page renders a mix of planner-source and
  reminder-source rows correctly (the dev seed data carries both,
  filtered by `metadata.legacy_source`).

---

## p3-be-reminder-update-revert — rip transitional fields

**File:** `backend/app/api/v1/reminders_v2.py`

**Class:** `ReminderUpdateRequest` (around line 230). Remove the
transitional fields (lines ~252-256):

```text
status:       Optional[str]              = None    # remove
type:         Optional[str]              = None    # remove
entity_type:  Optional[str]              = None    # remove
entity_id:    Optional[str]              = None    # remove
payload:      Optional[Dict[str, Any]]   = None    # remove
```

The companion comment block (lines ~248-251) referencing the FE
shim wholesale-payload replace also goes.

**File:** `backend/app/services/reminder_tasks.py`

**Function:** `update_reminder` — rip the branches that consume
those fields. Specifically:
* the `status` branch with the closed-enum validation comment
  (around line 599);
* the wholesale `payload` replace branch explicitly marked
  temporary (around line 642);
* `type` / `entity_type` / `entity_id` straight passthroughs.

**Acceptance:**
* `ReminderUpdateRequest` has only the canonical Activity-update
  surface (title, description, due_at, priority, assignee_id,
  starts_at, ends_at, etc. — confirm against the canonical
  `Activity` PATCH body in `activity-notification-operating-layer.md`).
* `pytest backend/tests/api/test_reminders*` green.
* `update_reminder` no longer reads `update.payload` /
  `update.status` / `update.type` / `update.entity_type` /
  `update.entity_id`.

**Pre-condition:** FE shim is gone (`p3-fe-shim-rip`). The shim is
the only producer of these fields.

---

## p3-orm-rip-planner — delete `CommunicationPlannerEvent` ORM

**File:** `backend/app/models/communication.py` (around line 186 —
`class CommunicationPlannerEvent(Base, TimestampMixin)`).

**Remove:** the entire class definition + any `__all__` export.

**Side-effect cleanup:**
* `backend/app/models/__init__.py` — remove the class re-export
  (search `CommunicationPlannerEvent`).
* `backend/tests/test_owner_fk_set_null.py:132` — the only
  remaining `db.add(CommunicationPlannerEvent(...))` site. Either
  rewrite the test to use `Activity` (preferred — it tests
  FK SET NULL on `owner_id`, which `Activity` also has) or delete
  it if the FK SET NULL path is already covered by the
  `Activity`-side test.

**Acceptance:**
```bash
rg "CommunicationPlannerEvent" backend
# Zero matches outside Alembic migration history (which we keep).
```

---

## p3-orm-rip-candidate-task — delete `CandidateTask` ORM

**File:** `backend/app/models/candidate_children.py` (around line
50 — `class CandidateTask(Base)`).

**Remove:** the class definition + any `__all__` export. Also
strip the table-creation branch in
`backend/app/modules/candidate_children/ensure_schema.py` (lines
75-96 — the `CREATE TABLE IF NOT EXISTS candidate_tasks` block
plus its two `CREATE INDEX IF NOT EXISTS` lines).

**Acceptance:**
```bash
rg "\bCandidateTask\b|candidate_tasks" backend/app
# Zero matches.
```

(Alembic migration history files keep the references — they are
historical and immutable.)

---

## p3-ensure-schema-cleanup — strip planner branch from comms ensure

**File:** `backend/app/services/ensure_communications_schema.py`

**Remove the planner-table bootstrap branches:**
* `CommunicationPlannerEvent` import (line 29);
* `CommunicationPlannerEvent.__table__` reference (line 52);
* the `CREATE TABLE communication_planner_events ...` block + its
  four `CREATE INDEX IF NOT EXISTS ix_comm_planner_*` lines
  (lines 226-256).

The remainder of the file (templates, threads, messages, etc.)
stays.

**Acceptance:** `ensure_communications_schema()` runs cleanly
against a fresh DB without the planner branch; no `CREATE
TABLE communication_planner_events` SQL emitted.

---

## p3-aliases-cleanup — drop transitional aliases / synonyms

**Targets** (split in two: code now, and a deferred Phase 4 piece).

### Now (after p3-orm-rip-* lands):

* `backend/app/services/team_assignee_auto.py:_activity_planner_kind`
  — once all backfilled `metadata.planner.kind` rows have aged
  out (visibility window depends on tenant retention; coordinate
  with ops). Until then, keep the lookup. The aging-out criterion
  is captured in `phase-2-1-planner-tasks-into-activities.md`
  §"Phase 3 cleanup" item 6.
* Any planner-status normalisation helpers in remaining call
  sites (search: `planner_status`, `_normalize_planner_status` —
  may already be empty post Phase 2.1; verify via `rg`).
* `metadata.planner.linked_candidate_id` lookup in
  `backend/app/services/candidate_lifecycle.py` (line ~324) — same
  aging-out criterion as `kind`.
* Russian + English docstrings in
  `backend/app/services/assignee_load_taxonomy.py` referencing
  `metadata.planner.kind` — update to drop the legacy clause once
  the runtime lookup is gone.

### Phase 4 territory (do not touch in Phase 3):

* `Reminder = Activity` ORM alias (in
  `backend/app/models/reminder.py`).
* `ReminderEvent = ActivityEvent` alias (in
  `backend/app/models/reminder_event.py`).
* `UserNotification = Notification` alias (in
  `backend/app/models/user_notification.py`).
* The `reminders` and `user_notifications` compat views with
  `INSTEAD OF` reject triggers in alembic
  `202607150003_compat_views_legacy_aliases.py`.

These four are Phase 4 deletion targets — they protect every
remaining `from backend.app.models.reminder import Reminder` call
site in the codebase. Ripping them is a separate audit (find every
`Reminder` / `ReminderEvent` / `UserNotification` consumer and
rename), and out of scope for Phase 3.

---

## p3-frontend-rename — final UI semantics under `Activity`

**Goal:** zero "planner event" wording in the React tree.

**Hot zones** (broad sweep, expect ≥30 hits each):

```bash
rg -i "planner.event|plannerEvent|planner_event" hostflow-frontend/src
rg "PlannerEvent" hostflow-frontend/src
rg "plannerKind|planner_kind" hostflow-frontend/src
```

**Specific places to look:**

* component names (`CommunicationsPlannerPage` → likely
  `CommunicationsCalendarPage` or merged into `RemindersPage`);
* React-Query / Zustand store keys (`["plannerEvents", ...]` →
  `["activities", ...]`);
* i18n keys in `hostflow-frontend/src/i18n/{en,pl,ru}.json`
  (search `planner.event`, `planner_event`, `plannerEvent`);
* telemetry events (`track("planner.event.created")` → match
  pattern with the activity taxonomy).

**Acceptance:**
* `rg -i "planner.event" hostflow-frontend/src` returns zero
  matches outside the changelog / spec / archived docs.
* i18n triple (en/pl/ru) stays in sync — language parity check
  via `python3 -c "import json; …"` over the three files.

---

## Test checklist for the whole Phase 3 series

When each PR in the series lands, run:

| Suite | Coverage |
|-------|----------|
| `pytest backend/tests/api/test_activity_*` | core Activity HTTP surface |
| `pytest backend/tests/api/test_reminders_*` | legacy alias surface (still alive in Phase 3 — Phase 4 territory) |
| `pytest backend/tests/test_timeoff_cleanup.py backend/tests/test_lead_lifecycle.py backend/tests/test_team_assignee_auto.py backend/tests/test_candidate_children.py::test_tasks_crud` | the recovery suite from Phase 2.1 — must still pass |
| `pytest backend/tests/migrations/test_phase_2_1_round_trip.py` | round-trip migration; only meaningful pre-`p3-be-reminder-update-revert` |
| `npm run test` (or `vitest run`) in `hostflow-frontend/` | component tests for the five migrated pages |
| `tsc --noEmit` in `hostflow-frontend/` | type purity after `p3-fe-pages-native` |
| `rg "CommunicationPlannerEvent\|CandidateTask\|/communications/planner/events\|/api/v1/candidates/[^/]+/tasks" .` (excluding alembic history + this doc) | zero hits; the canonical Phase-3-done signal |

When that final `rg` is clean across the repo (minus alembic
history + this inventory), Phase 3 is closed and Phase 4 (alias
removal) becomes the next gate.
