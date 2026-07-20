# C1.2 — Workspace Actions

**Status:** Active (kickoff)  
**Branch:** `feat/communication-c1-2-workspace-actions`  
**Worktree:** `/tmp/hf-c1-2-workspace-actions`  
**Base:** `integration/release-product-a-b` @ `dbeb36ed` (after PR #107)  
**Parents:** [C1 Inbox Workspace](c1-communication-inbox-workspace.md) · [C1.1 ThreadContext](c1-1-thread-context-composer.md)  
**PR:** https://github.com/igortatarynovich/HostFlow/pull/108

> Build the manager’s workplace around **Thread** mutations — without growing Composer  
> and without letting Workspace “sprawl” into field-level PATCH APIs.

## Architecture freeze

**C1 architecture is frozen.** No further architectural redesign until C1 close-out.  
Remaining work = implement Commands → projections → Workspace UX (C1.3) → close C1 → C2.

### Merge gates (every C1.2+ PR — blockers)

1. **No API bypasses Commands** — any Thread state change must go through a typed Command. New direct-mutation endpoints (field PATCH for ownership/unread/next_action/SLA/queues) = review blocker.  
2. **ThreadContext is the only Workspace read model** — new UX fields land in ThreadContext first; Workspace must not reassemble state from many endpoints.  
3. **Queue stays a projection** — no MoveThreadToQueue / queue write API, even as a “quick button”. Change Thread state → queues recompute.

### C1.2 close-out gate — no mixed path

While C1.2 PRs are open, legacy mutation APIs may still exist.  
**Before declaring C1.2 complete / merging the close-out:** the codebase must have **zero** remaining Thread mutations outside Commands (grep + contract test). Dual API is temporary only.

### Implementation priority (remaining)

1. ThreadNextAction entity + Set / Complete / Cancel ← **in progress**  
2. SLA event clock (start/pause/resume/resolve; breached derived)  
3. CloseThread / ReopenThread (+ invariants vs Next Action / SLA)  
4. Deprecate legacy PATCH → migrate internal callers → delete in one PR  
5. Frontend: Commands only; apply returned ThreadContext (no extra refresh)

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
- [ ] Pause/Resume SLA + Close/Reopen Commands  
- [ ] Optimistic concurrency → typed conflict  
- [ ] SLA event clock; breached derived  
- [ ] Workspace UI uses Commands only (no field PATCH)  
- [ ] Legacy PATCH deprecated → internals on Commands → delete  
- [ ] **Close-out:** no-mixed-path contract test (zero Thread mutations outside Commands)  
- [ ] Composer unchanged  
- [ ] No `module == …` branches  
- [ ] Contract test: modules use public Communication Workspace Command API via adapters 

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

Then **close C1** → **C2** (Templates, Automations & Campaigns on the **same Commands**) → [Epic C Complete Gate](../gates/epic-c-complete-gate.md).
