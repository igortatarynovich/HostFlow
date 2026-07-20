# C1.3 — Workspace Experience

**Status:** Planned (after C1.2)  
**Parents:** [C1.2 Workspace Actions](c1-2-workspace-actions.md) · [C1.1 ThreadContext](c1-1-thread-context-composer.md)

> Final C1 product surface. Does **not** change the Thread / Command / projection model — only consumes it.

## Prerequisite

C1.2 DoD green: typed Commands return ThreadContext; queues/SLA/next-action invariants hold.

## Scope

| Surface | Notes |
|---------|--------|
| Unified Thread card | Timeline + work state from ThreadContext |
| Working queues | Projection filters only |
| Quick actions | Bind to Workspace Commands |
| Composer | Unchanged C1.1 contract |
| Diagnostics strip | C0.3 projection in context |
| Next action panel | Active ThreadNextAction projection |
| SLA indicators | Derived from SLA events |
| Keyboard shortcuts | UX only → same Commands |
| Realtime updates | Apply ThreadContext (command response or push) |

## Out of scope

- New mutation paths  
- Queue write APIs  
- Module-specific composer/command forks  
- C2 engines (templates / automations / campaigns)

## After C1.3

**C1 — complete** (Foundation + Workspace model + Experience) → **C2** without rewriting Thread/Commands.
