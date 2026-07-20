# C1.2 — Workspace Actions

**Status:** Active (kickoff)  
**Branch:** `feat/communication-c1-2-workspace-actions`  
**Worktree:** `/tmp/hf-c1-2-workspace-actions`  
**Base:** `integration/release-product-a-b` @ `dbeb36ed` (after PR #107)  
**Parents:** [C1 Inbox Workspace](c1-communication-inbox-workspace.md) · [C1.1 ThreadContext](c1-1-thread-context-composer.md)

> Build the manager’s workplace around **Thread** mutations — without growing Composer.

## Main contract

```text
Workspace action
  → typed platform command
  → Thread state changes (SoT)
  → queue projections / counters / ThreadContext refresh
```

UI changes **canonical Thread state**. Queue membership is **recomputed**, never stored as a second SoT.  
Composer stays unchanged (still driven only by ThreadContext).

## Scope

### Ownership

- assign / reassign / unassign  
- optimistic concurrency (stale write → typed conflict)  
- audit: actor, time, from → to  

### Read state

- mark read / unread at **Thread** level  
- unread counter as projection  
- idempotent  
- not bound to a specific Message  

### Next action

- type, `due_at`, owner  
- completed / cancelled  
- audit history  
- **one active** next action per Thread (unless a later canon explicitly allows many)  

### SLA

- SLA clock on Thread  
- pause / resume rules  
- breach reason  
- **derived** status (not a manual flag)  
- no module business logic inside Communication  

### Queue transitions

Queues are projections of Thread state, not hand-managed lists:

| Queue | Projection of |
|-------|----------------|
| `assigned_to_me` | assignee = actor |
| `unassigned` | no assignee |
| `unread` / `new_inbound` | unread_count > 0 |
| `needs_reply` / `requires_reply` | inbound waiting on operator |
| `waiting_for_reply` | outbound awaiting counterpart |
| `sla_breached` | derived SLA breach |
| `closed` | terminal / archived |

UI must not “move Thread into a queue”. It mutates ownership / read / SLA / next-action; membership follows.

## Out of scope

- Composer capability / intent changes (C1.1 locked)  
- Campaign / Automation engines (C2)  
- Module-specific `if module == …` branches  
- Direct PATCH of arbitrary Thread fields from UI  

## Definition of Done

- [ ] All actions go through typed commands  
- [ ] No direct PATCH of individual Thread fields from UI  
- [ ] Every change is audited  
- [ ] Stale write returns typed conflict  
- [ ] Queue membership is not a second SoT  
- [ ] After action, ThreadContext returns a fresh `context_version` / `generated_at`  
- [ ] Composer unchanged  
- [ ] No `module == …` branches  
- [ ] Contract test: modules use public Communication Workspace API via adapters  

## After C1.2

Assemble full Workspace UX + C1 close-out, then **C2** (templates / automations / campaigns) → [Epic C Complete Gate](../gates/epic-c-complete-gate.md).
