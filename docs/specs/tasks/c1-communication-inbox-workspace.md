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
- Composer  
- **Allowed actions** from Intent Policy (intents + channels)

## Key principle

**UI does not decide what may be sent.**  
The workspace receives allowed intents and channels from the Communication Platform (policy / capability resolvers). Modules only open or filter the workspace through adapters and entity links.

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

- [ ] Primary navigation lands on thread queues, not a flat message list  
- [ ] Each queue is backed by platform facts (not ad-hoc FE heuristics where contracts exist)  
- [ ] Thread card shows G13 links, diagnostics summary, and policy-allowed actions  
- [ ] Composer cannot offer intents/channels the platform did not authorize  
- [ ] Modules deep-link / filter workspace via adapters — no parallel inbox engines  
