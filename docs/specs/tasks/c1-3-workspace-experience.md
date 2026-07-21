# C1.3 — Workspace Experience

**Status:** ✅ Closed with C1 (2026-07-21)  
**Branch:** `feat/communication-c1-3-workspace-experience`  
**Parents:** [C1.2 Workspace Actions](c1-2-workspace-actions.md) · [C1.1 ThreadContext](c1-1-thread-context-composer.md)  
**Close-out:** live Commands smoke + [gate evidence](../gates/epic-c-complete-gate.md#c1-close-out-evidence-2026-07-21)

> Final C1 product surface. Does **not** change the Thread / Command / projection model — only consumes it.

## Prerequisite

C1.2 DoD green: typed Commands return ThreadContext; queues/SLA/next-action invariants hold;
optimistic concurrency (`work_version`); no mixed PATCH path.

## Scope

| Surface | Notes |
|---------|--------|
| Unified Thread card | Timeline + work state from ThreadContext |
| Working queues | Projection filters only |
| Quick actions | Bind to Workspace Commands |
| Composer | Unchanged C1.1 contract |
| Diagnostics strip | Prefer `workspace.delivery_summary` from context |
| Next action panel | Active ThreadNextAction + Set/Complete/Cancel Commands |
| SLA indicators | Derived from `work_state.sla` |
| Keyboard shortcuts | UX only → same Commands (`e` read, `u` unread, `c` close) |
| Realtime updates | Apply ThreadContext (command response; push later) |
| Optimistic Commands | `expected_work_version` from ThreadContext on every Command |

## Implementation progress

- [x] Spec kickoff + branch  
- [x] `runCommand` + `expected_work_version` in Workspace hook / ControlPanel / Workflow / links  
- [x] Thread header consumes ThreadContext (status/unread/assignee/SLA chip)  
- [x] Next action panel (Set / Complete / Cancel Commands)  
- [x] Diagnostics strip prefers context delivery summary  
- [x] Keyboard shortcuts → Commands  
- [x] PauseSLA / ResumeSLA quick actions in SLA chip  
- [x] Soft realtime: poll ThreadContext and apply on `work_version` advance  
- [x] Drop legacy G-8 next-action badge from Thread WorkArea (panel is SoT)  
- [x] True push/WebSocket ThreadContext deferred (optional; poll covers C1.3 close)  

## Out of scope

- New mutation paths  
- Queue write APIs  
- Module-specific composer/command forks  
- C2 engines (templates / automations / campaigns)

## After C1.3

**C1 — contracts complete** (Foundation + Workspace model + Experience surface) → **C2** without rewriting Thread/Commands.

**Manager UX complete** is not claimed here. Follow-up: [Conversation Workspace v2](../frontend/conversation-workspace-v2.md) (pure FE overlay; [task](conversation-workspace-v2.md)).
