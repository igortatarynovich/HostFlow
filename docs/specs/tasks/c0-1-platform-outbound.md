# C0.1 — Platform outbound capability (normative)

**Status:** In progress (PR #100)  
**Parents:** [Epic C0](epic-c0-communication-integrity.md) · [GAP audit](c0-1-outbound-linkage-gap-audit.md)

## Capability (mandatory)

From any supported HostFlow entity the operator can start communication without manually creating or re-binding a thread after send.

Product labels (examples):

- Написать кандидату  
- Написать отклику  
- Написать обращению  
- Написать потенциальному клиенту  
- Написать клиенту  
- Написать заказчику  
- Написать сотруднику  

The platform resolves: channels, address/number, existing thread, **origin entity**, related entities, sender, signature, templates.

## Unified command

All product modules use one platform operation:

```text
SendCommunication(origin, recipients, channel, content, context)
```

It must:

1. Resolve or create thread (by **work context / origin**, not email alone)  
2. Create G13 link to **origin**  
3. Optionally add G13 links to related entities  
4. Create `CommunicationMessage`  
5. Enqueue delivery / outbox record  
6. Return `thread_id` + `message_id` (+ delivery id)  
7. Be idempotent and atomic  

Sales / Recruitment / HR / Services must not own separate email writers. They call `SendCommunication`.

Questionnaire invite email is the **first caller** of this contour — not a special-case engine.

## Threading rule

One person ≠ one thread. The same contact may be candidate, company contact, and client on another order. G13 stores multiple entity links; **origin** is always the entity from which the user pressed Write.

## Campaigns

Bulk send is **Epic C2** — see [epic-c2-communication-campaigns.md](epic-c2-communication-campaigns.md). Out of C0.1.

## DoD contract scenarios (C0.1)

| # | Scenario |
|---|----------|
| 1 | Send from `candidate` |
| 2 | Send from `application` (CandidateApplication / recruitment application) |
| 3 | Send from `sales_inquiry` |
| 4 | Send from `client_account` |
| 5 | Send from `lead` (compatibility facade) |
| 6 | Re-send from same origin reuses the correct thread |
| 7 | Every created thread has G13 link to origin |
| 8 | Cannot complete send with known origin without G13 link |

## Out of C0.1

- Full Compose UI on every entity card  
- Signature policy product UI  
- Campaign / bulk engine (C2)  
- Inbound resolver (C0.2)  
- Delivery diagnostics UX (C0.3)  
- Inbox redesign (C1)  
