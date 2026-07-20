# Epic C2 — Templates, Automations & Campaigns

**Status:** Queued (after Epic C0 integrity; after C1 per sequential queue)  
**Parents:** [Sequential queue](sales-to-comms-sequential-queue.md) · [Epic C0](epic-c0-communication-integrity.md) · [C0.0 Communication Canon](c0-0-communication-canon.md) · platform `prepare_and_send_communication` / `SendCommunication`

> Product surfaces for **templates**, **automation rules**, and **campaigns** — all on top of the same Communication platform command.  
> Do **not** implement inside C0.1. Do **not** invent a second send engine.

**Filename note:** path kept as `epic-c2-communication-campaigns.md` for link stability; scope is broader than campaigns alone.

---

## Scope

| Area | Product outcome |
|------|-----------------|
| **Templates** | Tenant catalog with versioning, purpose, variables, `link_intents`, locales, status — per [C0.0 §4](c0-0-communication-canon.md) |
| **Automations** | Authoring/enablement of `CommunicationAutomationRule` bound to pipelines / domain events — per [C0.0 §12](c0-0-communication-canon.md) |
| **Campaigns** | Bulk / scheduled audience sends with per-recipient message + thread + G13 |

Settings / signatures / compliance policy UI may share **Настройки → Коммуникации** but remain separate ownership buckets ([C0.0 §13](c0-0-communication-canon.md)).

---

## Templates

- CRUD + activate/archive for `CommunicationTemplate`  
- No baked public URLs — only link intents  
- Preview uses the same render path as prepare-send (snapshot rules)  
- Frontend must not own template composition logic beyond editor UX  

---

## Automations

- Rules: trigger, stage bounds, conditions, delay, channel strategy, template key, recipient role, link intents, dedupe, quiet hours, consent flag  
- Chain only: `DomainEvent → Automation evaluation → CommunicationCommand`  
- No sync provider send from stage handlers  

---

## Campaigns / bulk

`CommunicationCampaign` holds audience, channel, template, sender, schedule, limits, status, stats, and selection provenance.

Per recipient the campaign creates separate:

- delivery  
- message  
- thread / G13 links  
- idempotency key  

Recipient replies land in their **personal** thread — never a shared campaign thread.

### UI entry points (later)

1. From object lists (candidates, inquiries, prospects, clients, employees): select → Write → channel → template → preview → send/schedule  
2. Communication module: Dialogs · Campaigns · Templates · Automations · Settings  

### Rule

Frontend must not loop “Write” buttons for N recipients. Campaigns orchestrate platform `prepare_and_send_communication` (or a bulk variant) server-side.

---

## Out of C2

- C0 integrity writers/gates (already C0.0–C0.3)  
- Inbox UX (C1)  
- Legal drafting of RODO notice text (legal review; architecture from C0.0)  
