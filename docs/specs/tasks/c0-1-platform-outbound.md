# C0.1 — Platform outbound capability (normative)

**Status:** First Canon implementation in PR #100 (outbound path)  
**Parents:** [C0.0 Communication Canon](c0-0-communication-canon.md) · [Epic C0](epic-c0-communication-integrity.md) · [GAP audit](c0-1-outbound-linkage-gap-audit.md)

> Intent is primary. `send_communication` executes durable writes.  
> PR #100 aligns seams to the canon without shipping C2/Inbox/consent/campaign product.

## Capability (mandatory)

From any supported HostFlow entity the operator can start communication without manually creating or re-binding a thread after send.

Product labels map to **intents** (examples):

- Request Questionnaire → `request_questionnaire`  
- Request Documents → `request_documents`  
- Invite to Interview → `invite_to_interview`  
- … plus manual Write → `manual_outbound` until specialized intents exist  

## Unified path

```text
CommunicationIntent → CommunicationCommand → prepare_and_send_communication → send_communication
```

Resolvers (seams, thin impls in #100):

- `resolve_communication_capabilities` / `CapabilityResolver`  
- `TemplateResolver` (seed registry behind the interface)  
- `LinkResolver` (questionnaire impl; full PublicActionLinkService later)  

Questionnaire invite is the **first intent caller** — compose via resolvers, send via `CommunicationSender`.

## Threading rule

One person ≠ one thread. G13 stores multiple entity links; **origin** is the entity from which the user pressed Write / the intent was raised.

## DoD contract scenarios (C0.1)

| # | Scenario |
|---|----------|
| 1 | Send from `candidate` |
| 2 | Send from `application` |
| 3 | Send from `sales_inquiry` |
| 4 | Send from `client_account` |
| 5 | Send from `lead` (compatibility facade) |
| 6 | Re-send from same origin reuses the correct thread |
| 7 | Every created thread has G13 link to origin |
| 8 | Cannot complete send with known origin without G13 link |
| 9 | Questionnaire uses Intent + TemplateResolver + LinkResolver + CommunicationSender |

## Out of C0.1 / PR #100

- Full Compose UI on every entity card  
- Signature / template / automation **admin** product (C2)  
- Consent evidence engine product  
- Full PublicActionLinkService  
- Campaign / bulk engine (C2)  
- Inbound resolver (C0.2)  
- Delivery diagnostics UX (C0.3)  
- Inbox redesign (C1)  
