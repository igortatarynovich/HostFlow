# C1.2 — Workspace Actions

**Status:** ✅ Closed with C1 (2026-07-21)  
**Branch:** `feat/communication-c1-2-workspace-actions`  
**Base:** `integration/release-product-a-b` @ `dbeb36ed` (after PR #107)  
**Parents:** [C1 Inbox Workspace](c1-communication-inbox-workspace.md) · [C1.1 ThreadContext](c1-1-thread-context-composer.md)  
**PR:** https://github.com/igortatarynovich/HostFlow/pull/108  
**Close-out evidence:** [gate § C1](../gates/epic-c-complete-gate.md#c1-close-out-evidence-2026-07-21)

> Build the manager’s workplace around **Thread** mutations — without growing Composer  
> and without letting Workspace “sprawl” into field-level PATCH APIs.

## Architecture freeze

**C1 architecture is frozen.** No further architectural redesign until C1 close-out.  
Remaining work = implement Commands → projections → Workspace UX (C1.3) → close C1 → C2.

### Merge gates (every C1.2+ PR — blockers)

1. **No API bypasses Commands** — any Thread state change must go through a typed Command. New direct-mutation endpoints (field PATCH for ownership/unread/next_action/SLA/queues) = review blocker.  
2. **ThreadContext is the only Workspace read model** — new UX fields land in ThreadContext first; Workspace must not reassemble state from many endpoints.  
3. **Queue stays a projection** — no MoveThreadToQueue / queue write API, even as a “quick button”. Change Thread state → queues recompute.

### C1.2 close-out gates

1. **No mixed path** — Workspace HTTP must not mutate Thread outside Commands (contract test).  
2. **Command coverage = 100%** — every Workspace-visible Thread field maps to a named Command (`THREAD_FIELD_COMMAND_COVERAGE`).  
3. **Optimistic concurrency** — `work_version` on Thread; optional `expected_work_version` → typed `stale_work_version` (HTTP 409).

Legacy `PATCH /threads/{id}` and `POST /threads/{id}/read` are **removed**.

---

## Locked principle (entire C1)

> **Workspace changes Thread only through Commands.  
> Workspace never mutates projections directly.**

```text
Workspace
   ↓
Command
   ↓
Communication Platform
   ↓
Thread (+ related platform entities)
   ↓
Projections
   ↓
ThreadContext
   ↓
Workspace refresh
```

| Layer | Role |
|-------|------|
| **Thread** | Canonical work object |
| **Commands** | Sole way to change its state |
| **Projections** | Derived views (queues, counters, breached) |
| **ThreadContext** | Read model for Workspace / Composer |
| **Workspace** | Consumer of contracts only |

Aligned with outbound canon: Intent → Policy → Command → Sender.  
C2 (Automation / Campaigns / Templates) **must reuse the same Commands** — not invent parallel mutators.

---

## Workspace Commands (sole mutation API)

**Forbidden** (no field-level PATCH surface for Workspace):

- `PATCH /threads/{id}`
- `PATCH` ownership / unread / next_action / sla flags directly

**Required** — typed commands (names = contract; HTTP shape may be `POST …/commands/...`):

| Command | Intent |
|---------|--------|
| `AssignThread` | Set assignee (+ reason) |
| `ReassignThread` | Change assignee (+ reason) |
| `UnassignThread` | Clear assignee |
| `MarkThreadRead` | Thread-level read |
| `MarkThreadUnread` | Thread-level unread |
| `SetNextAction` | Create/replace active next action |
| `CompleteNextAction` | Complete active next action |
| `CancelNextAction` | Cancel active next action |
| `PauseSLA` | Pause SLA clock |
| `ResumeSLA` | Resume SLA clock |
| `CloseThread` | Terminal / archived |
| `ReopenThread` | Leave closed |
| `SetThreadPriority` | Priority |
| `SetThreadTags` | Tags / folder tags |
| `DeleteThread` / `RestoreThread` | Soft-delete lifecycle |
| `UpdateThreadWorkflow` | Ops mode / SLA policy meta |
| `SetThreadLinks` | Candidate / company / UOS links |

### Command response contract

Every successful Command **returns a fresh ThreadContext** — not bare `200 OK`.

```text
Command
  → mutate Thread / related entities
  → rebuild projections
  → return ThreadContext { context_version, generated_at, … }
```

Workspace must not need a second “reload state” GET for the happy path.  
Same contract for UI, later WebSocket apply, and mobile clients.

### Idempotency

Commands are **idempotent** where a no-op is well-defined:

| Command | Idempotent behaviour |
|---------|----------------------|
| `MarkThreadRead` | Already read → no state change, still return current ThreadContext |
| `MarkThreadUnread` | Already unread → no-op + current context |
| `AssignThread` to same user | No new assignment audit event; return current context |
| `CompleteNextAction` | Already completed → no-op |
| `CancelNextAction` | Already cancelled → no-op |
| `CloseThread` / `ReopenThread` | Already in target state → safe no-op |

Audits record **real transitions** only. No-ops do not invent history noise.

Also:

- optimistic concurrency → typed conflict on stale write (when a version/etag is supplied and mismatches);
- every mutating transition is audited (actor, time, before → after, reason where applicable).

---

## Thread invariants (must not break in follow-up PRs)

| Domain | Invariant |
|--------|-----------|
| **Ownership** | Exactly one current owner/assignee (or none). Assignment **history** is stored separately (audit / assignment log). |
| **Next Action** | At most one **active** action per Thread. Completed/cancelled actions are immutable. |
| **SLA** | Computed from events. Never edited manually as a boolean SoT. |
| **Queues** | Projection only. Never an object of write. |
| **Unread** | Thread-level state via commands — **not** a sum of unread Messages. |

Contract tests should lock these invariants as they land in code.

---

## Queue projections

**Queues have no mutation API.**

Impossible by design:

```text
MoveThreadToQueue("needs_reply")   ← forbidden
```

Correct chain:

```text
AssignThread (or other Command)
  → Thread state
  → Queue Projection
  → ThreadContext
  → Workspace
```

A queue is a **derivative**, not a controllable object.

| Queue | Projection of |
|-------|----------------|
| `assigned_to_me` | assignee = actor |
| `unassigned` | no assignee |
| `unread` / `new_inbound` | unread_count > 0 |
| `needs_reply` / `requires_reply` | inbound waiting on operator |
| `waiting_for_reply` | outbound awaiting counterpart |
| `sla_breached` | derived from SLA events |
| `closed` | terminal / archived |

---

## Ownership

Commands: `AssignThread` · `ReassignThread` · `UnassignThread`.

Beyond `assigned_to`:

**`AssignmentReason`** (required on assign/reassign):

- `manual`
- `automation`
- `queue_balancing`
- `escalation`
- `workload_balancing`

Audit: actor, time, from → to, reason.  
Optimistic concurrency on ownership writes.

---

## Read state

Commands: `MarkThreadRead` · `MarkThreadUnread`.

- Thread-level only (not bound to a specific Message)  
- unread counter = projection  
- idempotent  

---

## Next Action — platform entity (not a Thread field)

**`ThreadNextAction`** is a first-class Communication Platform entity:

| Field | Notes |
|-------|--------|
| `id` | Stable id |
| `thread_id` | Owning Thread |
| `action_type` | Typed action |
| `owner` | Responsible actor |
| `due_at` | Optional |
| `status` | active / completed / cancelled |
| `completed_at` / `completed_by` | When terminal |
| `source` | `manual` / `automation` |
| audit | History of changes |

Rules:

- **One active** next action per Thread (unless a later canon explicitly allows many).  
- ThreadContext `work_state.next_action` is a **projection** of the active entity.  
- Later consumers: Automation, SLA, AI, Dashboards — same entity, not a parallel field.

Commands: `SetNextAction` · `CompleteNextAction` · `CancelNextAction`.

---

## SLA — event model (derived breach)

Do **not** store `sla_breached = true` as SoT.

Store clock facts:

- `started_at`
- paused intervals
- `target_due_at`
- `resolved_at`

**`breached` is always computed** from events + clock.  
Commands: `PauseSLA` · `ResumeSLA` (plus start/resolve as side-effects of other commands where appropriate).  
No module business rules inside Communication — platform clock + rules only.

---

## Scope summary

| Area | Via |
|------|-----|
| Ownership | Assign / Reassign / Unassign + `AssignmentReason` |
| Read | MarkThreadRead / Unread |
| Next action | ThreadNextAction entity + Set / Complete / Cancel |
| SLA | Event clock + Pause / Resume; breached derived |
| Close | CloseThread / ReopenThread |
| Queues | Projection only — no move API |

Composer **unchanged** (C1.1). No `module == …` branches.

## Out of scope

- Composer capability / intent changes  
- Campaign / Automation product engines (C2) — but they **will** call these Commands later  
- Direct PATCH of Thread fields from UI  
- Any queue mutation endpoint  

## Definition of Done

- [x] Merge gates locked (Commands-only / ThreadContext-only read / queue projection)  
- [x] Ownership + read Commands: Assign / Reassign / Unassign / MarkRead / MarkUnread  
- [x] Successful Command response includes ThreadContext (`context_version`, `generated_at`)  
- [x] Idempotent no-ops; no spurious audit on no-op  
- [x] Real transitions audited (`CommunicationCommandAudit`)  
- [x] `AssignmentReason` on assign/reassign/unassign  
- [x] Contract test: no queue-mutation in Workspace Command routes  
- [x] ThreadNextAction entity + Set / Complete / Cancel (+ projection in ThreadContext)  
- [x] Pause/Resume SLA + Close/Reopen Commands  
- [x] SLA event clock; `breached` derived in ThreadContext.work_state.sla  
- [x] Legacy PATCH /read marked `deprecated=True`  
- [x] Workspace ControlPanel + mark-read use Commands + returned ThreadContext  
- [x] Hub bulk mark_read / archive / unarchive + Topbar dismiss → Commands  
- [x] Optimistic concurrency → `work_version` + `stale_work_version` (409)  
- [x] Hub tags/priority/delete + WorkflowCard + entity links + SLA incidents → Commands  
- [x] Deleted deprecated PATCH /read endpoints  
- [x] **Close-out:** no-mixed-path + Command coverage contract tests  
- [x] Composer unchanged  
- [x] No `module == …` branches  
- [ ] Contract test: modules use public Communication Workspace Command API via adapters (C2)

## After C1.2 → C1.3 Workspace Experience

Model of Thread + Commands stays frozen. Product UX assembles on top:

See [C1.3 Workspace Experience](c1-3-workspace-experience.md):

- unified Thread card  
- working queues  
- quick actions (Commands)  
- Composer (C1.1)  
- diagnostics strip  
- next action panel  
- SLA indicators  
- keyboard shortcuts  
- realtime updates (apply Command-returned / pushed ThreadContext)

**C1 closed 2026-07-21** (live smoke evidence in [Epic C Complete Gate](../gates/epic-c-complete-gate.md#c1-close-out-evidence-2026-07-21)).  
Next: **C2** (Templates, Automations & Campaigns on the **same Commands**) → gate PASS → Epic C complete.
