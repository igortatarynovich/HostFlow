# Epic C2 — Communication Campaigns & Bulk Messaging

**Status:** Queued (after Epic C0 integrity)  
**Parents:** [Sequential queue](sales-to-comms-sequential-queue.md) · [Epic C0](epic-c0-communication-integrity.md) · platform `SendCommunication`

> Bulk / campaign messaging is a **separate mode on top of** the same outbound platform.  
> Do **not** implement inside C0.1.

## Model

`CommunicationCampaign` holds audience, channel, template, sender, schedule, limits, status, stats, and selection provenance.

Per recipient the campaign creates separate:

- delivery  
- message  
- thread / G13 links  
- idempotency key  

Recipient replies land in their **personal** thread — never a shared campaign thread.

## UI entry points (later)

1. From object lists (candidates, inquiries, prospects, clients, employees): select → Write → channel → template → preview → send/schedule  
2. Communication module: Dialogs · Campaigns · Templates · Settings  

## Rule

Frontend must not loop “Write” buttons for N recipients. Campaigns orchestrate platform `SendCommunication` (or a bulk variant) server-side.
