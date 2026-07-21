# Epic C Complete Gate

**Status:** Queued (after C2; before Platform Governance Review)  
**Type:** Mandatory merge / capability gate (not a product feature)  
**Parents:** [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Communication Platform Foundation](../architecture/communication-platform-foundation.md) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md)

> Final check that Communication is a **single platform capability**.  
> Passing this gate is the only allowed transition from  
> **Communication Platform Foundation — complete** → **Epic C — complete**.

---

## Sequence (locked)

```text
C1 Inbox Workspace          ← CLOSED 2026-07-21 (evidence below)
  → C2 Capability epic (Intent-only; never mutate Thread)
       C2.1 Template Platform   ← ✅ closed
       C2.2 Automation Engine   ← ✅ closed
       C2.3 Campaign Orchestrator ← active

       C2.3 Campaign Orchestrator
       C2.4 Scheduling
  → Epic C Complete Gate   ← this document
  → A2 Platform Governance Review
  → Acquisition (Stage 3 + Meta)
  → Forms → Entity Workspace → Documents → Billing → AI
```

Do **not** skip this gate and mark Epic C complete after C2 alone.

---

## C1 close-out evidence (2026-07-21)

**Result:** C1 CLOSED — proceed to C2 **without Thread model changes**.

| Check | Evidence |
|-------|----------|
| Authenticated smoke of all 18 Workspace Commands on live Thread | `backend/scripts/smoke_c1_workspace_commands.py` → `SMOKE_PASS` |
| Thread | `197681a8-756a-4e3c-845b-1907cd88cbc8` (demo tenant; isolated smoke Thread) |
| Report | `backend/uploads/ops-reports/c1_workspace_commands_smoke_20260721T084034Z.json` |
| ThreadContext | Every Command + baseline/final `GET …/context` returned full four-block context (`identity` · `work_state` · `capabilities` · `workspace`) + `context_version` / `generated_at` |
| `work_version` | Monotonic +1 on applied transitions; unchanged on no-ops; final GET matches last Command (`wv=22` on closing run) |
| Optimistic concurrency | `expected_work_version` mismatch → HTTP **409** `stale_work_version` |
| Idempotency | Duplicate Assign / MarkRead/Unread / Complete/Cancel / Pause/Resume / Close/Reopen / Delete/Restore / SetPriority/Tags/Links → `applied=false`, **no** audit row, **no** version bump |
| Audit | `communication_command_audits` +1 only on real transitions; no-ops produce zero audit delta |
| Queue projections | `assigned_to_me` / `unassigned` / `new_inbound` / `requires_reply` / `closed` flip via Commands only (no MoveThreadToQueue) |
| Backend logs (smoke window) | Commands: **36×200 + 1×409**; **0** `500` / `IntegrityError` / `Traceback` / `no_intake_context` |
| Worker logs (smoke window) | **0** error signals |

Commands covered: AssignThread · ReassignThread · UnassignThread · MarkThreadRead · MarkThreadUnread · SetNextAction · CompleteNextAction · CancelNextAction · PauseSLA · ResumeSLA · CloseThread · ReopenThread · SetThreadPriority · SetThreadTags · DeleteThread · RestoreThread · UpdateThreadWorkflow · SetThreadLinks.

**Architecture freeze into C2:** Thread SoT + Commands-only mutations + ThreadContext read model + queue projections — unchanged.  
**C2 law:** create `CommunicationIntent` only; no second pipeline; **capability isolation** (no module imports). See [epic-c2](../tasks/epic-c2-communication-campaigns.md).

**Not yet Epic C complete** — C2.1–C2.4 + this gate checklist still required.

---

## Checklist

| # | Check | Status |
|---|--------|--------|
| 1 | One SoT for Communication | Pending (post-C2) |
| 2 | No legacy senders and no legacy inbound paths | Pending (post-C2) |
| 3 | All modules use only the public Communication Contract via adapters | Pending (post-C2) |
| 4 | No platform → module dependencies (C2 capability isolation) | Pending (enforce from C2.1) |
| 5 | All messages (outbound / inbound) pass through the unified pipeline | Pending (post-C2) |
| 6 | Callbacks, retries, diagnostics, and Inbox share one data model | C1 Inbox ✅; campaigns pending C2 |
| 7 | Templates, Automations, and Campaigns use Intent Registry — not private rule engines | Pending C2 |
| 8 | Documentation (ADR, Canon, Catalog) matches implementation | Pending (post-C2) |

---

## Status transition (only after PASS)

| Before gate | After gate PASS |
|-------------|-----------------|
| Communication Platform Foundation — complete | **Epic C — complete** |

Foundation remains historically true (C0.0–C0.3 closed earlier).  
C1 Inbox Workspace — complete (2026-07-21).  
Epic C complete means Foundation + C1 + C2 + this gate.

---

## Relation to A2 Governance

**Epic C Complete Gate** = Communication capability closed as one platform.  
**A2 Platform Governance Review** = cross-platform check that the boundary rule  
(platforms independent; modules only via public contracts/adapters) was not violated  
during platform growth — not a re-test of “are integrations wired”.

Governance does not replace this gate.

---

## Suggested branch

`docs/epic-c-complete-gate` (checklist + evidence links; no drive-by refactors unless trivial)

## DoD

- [ ] Checklist filled with evidence (paths / PRs / contract tests)  
- [ ] Residual gaps listed with owners or accepted waivers  
- [ ] Status docs updated: Foundation stays complete; **Epic C — complete** set only here  
- [ ] Sequential queue + roadmap point at A2 next  
- [x] C1 close-out smoke + log evidence recorded (above)  
