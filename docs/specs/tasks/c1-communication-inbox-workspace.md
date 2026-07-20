# C1 — Communication Inbox Workspace

**Status:** Active (kickoff)  
**Branch:** `feat/communication-c1-inbox-workspace`  
**Worktree:** `/tmp/hf-c1-inbox-workspace`  
**Base:** `integration/release-product-a-b` @ `95f2a525` (after PR #104)  
**Parents:** [Communication Platform Foundation](../architecture/communication-platform-foundation.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Epic C0](epic-c0-communication-integrity.md) · [C0.3](c0-3-delivery-diagnostics.md)

> Communication becomes the manager’s primary workplace — not a message journal.  
> Infrastructure (Foundation) is complete; C1 is **product UX** on top of it.

## Main object

**`CommunicationThread`** — conversations, not individual messages, drive the workspace.

## Architectural rule (locked)

> **Thread is the work object. Message is an event inside the Thread.**

Consequences (do not invert):

| Concern | Belongs to |
|---------|------------|
| List rows | Thread |
| Unread | Thread |
| Ownership / assignee | Thread |
| SLA | Thread |
| Next action | Thread |
| Working queues / filters | Thread |
| Entity links (G13) | Thread |
| Timeline | Chronology of events *on* the Thread (not a first-class list entity) |

Composer and allowed intents/channels come from the Communication Platform — UI does not invent them.

### ThreadContext (Workspace read model — not a SoT)

```text
Thread → ThreadContext (read model) → Composer
```

**`ThreadContext` is not a second Communication aggregate.**  
It is a **read model / workspace contract** assembled from Thread, G13, participants, queue projection, capabilities, diagnostics, and draft. It aggregates for UI; it does not own assignee, unread, capabilities, or delivery truth.

Four blocks: `identity` · `work_state` · `capabilities` · `workspace`  
Details + DoD: [C1.1 ThreadContext & Composer](c1-1-thread-context-composer.md).

Composer is dumb: show what ThreadContext allows. Backend re-validates intent+channel on send.

**Interactive openers only** (Recruitment / Services / manual Workspace AI draft) → ThreadContext → Composer.  
**Not** Campaign / Automation / bulk — those emit `CommunicationIntent` via their own adapters.

### C1 end-state architecture

| Layer | Role |
|-------|------|
| **Thread** | Canonical work object (SoT for work state) |
| **ThreadContext** | Workspace read model (Composer input; no persistence) |
| **Composer** | Universal UI driven by ThreadContext + user input |
| **Communication Platform** | Authority for capabilities, intents, and policy |

Maturity: Communication **Workspace** stage — see [platform-capability-maturity.md](../architecture/platform-capability-maturity.md).

## Goal

Managers see what needs action without reading server logs or provider internals:

- who needs a reply;
- what requires action;
- what is waiting on the client;
- what was handled automatically;
- what needs escalation.

## Working queues (minimum)

| Queue | Intent |
|-------|--------|
| Requires reply | Inbound waiting on operator |
| New inbound | Fresh unresolved attention |
| Delivery errors | Failed / undeliverable diagnostics |
| Unresolved | Inbound (and later callback) unresolved queue |
| Assigned to me | Owner/assignee = current user |
| Unassigned | No owner |
| Waiting for reply | Outbound sent; awaiting counterpart |
| Closed | Terminal / archived threads |

## Thread card (assembled facts)

- Chronological message timeline  
- Linked entities via G13  
- Participants  
- Owner / assignee  
- Unread state  
- Last inbound / last outbound  
- Delivery diagnostics (C0.3 contract — no provider internals)  
- Composer (driven only by ThreadContext)  
- **Allowed actions** already resolved inside ThreadContext (intents + channels + policy restrictions)

## Key principle

**UI does not decide what may be sent.**  
The workspace receives a finished **ThreadContext** read model for display. Backend policy remains authority on every send (stale context → typed denial). Modules open the workspace through adapters; they do not assemble composer policy themselves.

## Scope (in)

- Thread-centric Inbox Workspace UI + supporting read APIs  
- Queue filters listed above  
- Thread card composition over Foundation contracts  
- Composer bound to allowed intents/channels  

## Scope (out)

- Campaign engine  
- Automation engine  
- Full template editor  
- New consent engine  
- Stage 3 Sales product flow  
- Modular Recruitment / Sales business logic inside Communication  

## After C1

```text
C2 → Epic C Complete Gate → Governance → Stage 3 / Meta → …
```

**C2 — Templates, Automations & Campaigns**, then mandatory  
[Epic C Complete Gate](../gates/epic-c-complete-gate.md).  
**Epic C — complete** only after that gate. Not Stage 3 next.

## Acceptance (draft)

- [x] Primary navigation lands on thread queues, not a flat message list  
- [x] Working queues backed by platform `GET /threads?queue=` (not FE-only heuristics)  
- [x] Thread card shows delivery diagnostics summary (C0.3)  
- [x] `GET /threads/{id}/context` assembles ThreadContext read model (four blocks; not a SoT)  
- [x] `GET /threads/{id}/capabilities` is a compat slice of `capabilities`  
- [x] Composer consumes ThreadContext only; backend re-applies policy on outbound  
- [ ] Modules deep-link / filter workspace via adapters — no parallel inbox engines  
- See also [C1.1 DoD](c1-1-thread-context-composer.md) 
