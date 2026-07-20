# C0.1 — Platform outbound capability (normative)

**Status:** Vertical slice in progress (PR #100) — **not** completed Communication foundation  
**Parents:** [C0.0 Communication Canon](c0-0-communication-canon.md) · [Epic C0](epic-c0-communication-integrity.md) · [GAP audit](c0-1-outbound-linkage-gap-audit.md)

> C0.0 defines the full contracts. This slice ships the first durable outbound path under those contracts.  
> Aligning questionnaire → policy → template → link → full snapshot is a **follow-up** after C0.0 docs, not an expansion of unrelated scope in PR #100.

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

The platform resolves: channels, address/number, existing thread, **origin entity**, related entities, sender, signature, templates (full resolver per C0.0 — capability API may land in align slice).

## Unified command

Canon name: `prepare_and_send_communication(command)` — see [C0.0 §3](c0-0-communication-canon.md).

PR #100 vertical approximation:

```text
SendCommunication(origin, recipients, channel, content, context)
```

It must (vertical DoD):

1. Resolve or create thread (by **work context / origin**, not email alone)  
2. Create G13 link to **origin**  
3. Optionally add G13 links to related entities  
4. Create `CommunicationMessage`  
5. Enqueue delivery / outbox record  
6. Return `thread_id` + `message_id` (+ delivery id)  
7. Be idempotent and atomic  

Sales / Recruitment / HR / Services must not own separate email writers. They call the platform command.

Questionnaire invite email is the **first caller** of this contour — not a special-case engine forever. Link minting / template registry / consent steps align in the follow-up slice.

## Threading rule

One person ≠ one thread. The same contact may be candidate, company contact, and client on another order. G13 stores multiple entity links; **origin** is always the entity from which the user pressed Write.

## Campaigns / templates product / automations product

**Epic C2** — [epic-c2-communication-campaigns.md](epic-c2-communication-campaigns.md) (templates + automations + campaigns). Out of C0.1.

## Locked in PR #100 (do not expand)

- `send_communication`  
- G13 writer + outbound gate  
- Questionnaire as first caller  
- `entity_links` API/UI (+ legacy fallback)  

## DoD contract scenarios (C0.1 vertical)

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
- Template catalog / automation authoring / campaign engine (C2)  
- `PublicActionLinkService` product completion (contract in C0.0; wire in align slice)  
- Inbound resolver (C0.2)  
- Delivery diagnostics UX (C0.3)  
- Inbox redesign (C1)  
