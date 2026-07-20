# C1.2 — Workspace Actions

**Status:** Active (kickoff)  
**Branch:** `feat/communication-c1-2-workspace-actions`  
**Worktree:** `/tmp/hf-c1-2-workspace-actions`  
**Base:** `integration/release-product-a-b` @ `dbeb36ed` (after PR #107)  
**Parents:** [C1 Inbox Workspace](c1-communication-inbox-workspace.md) · [C1.1 ThreadContext](c1-1-thread-context-composer.md)  
**PR:** https://github.com/igortatarynovich/HostFlow/pull/108

> Build the manager’s workplace around **Thread** mutations — without growing Composer  
> and without letting Workspace “sprawl” into field-level PATCH APIs.

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

Each command:

- is audited (actor, time, before → after, reason where applicable);
- supports optimistic concurrency → typed conflict on stale write;
- returns (or triggers) a refreshed ThreadContext with new `context_version` / `generated_at`.

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

- [ ] All Workspace actions are typed Commands from the table above  
- [ ] No `PATCH /threads/{id}` (or field-level PATCH) used by Workspace UI  
- [ ] No `MoveThreadToQueue` (or equivalent) API exists  
- [ ] Every command is audited  
- [ ] Stale write → typed conflict  
- [ ] Queue membership is projection-only (not a second SoT)  
- [ ] Next Action persisted as platform entity; ThreadContext projects active one  
- [ ] SLA breach is derived; no stored `sla_breached` SoT flag  
- [ ] `AssignmentReason` recorded on assign/reassign  
- [ ] After command, ThreadContext has fresh `context_version` / `generated_at`  
- [ ] Composer unchanged  
- [ ] No `module == …` branches  
- [ ] Contract test: modules use public Communication Workspace Command API via adapters  
- [ ] Contract test: no queue-mutation routes; no generic Thread PATCH for Workspace fields  

## After C1.2

Full Workspace UX + C1 close-out → **C2** (same Commands) → [Epic C Complete Gate](../gates/epic-c-complete-gate.md).
