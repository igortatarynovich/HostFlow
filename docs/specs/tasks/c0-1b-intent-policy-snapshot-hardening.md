# C0.1b — Intent Policy & Snapshot Hardening

**Status:** Queued (after PR #100 merge)  
**Parents:** [C0.0 Canon](c0-0-communication-canon.md) · [Epic C0](epic-c0-communication-integrity.md) · [C0.1 platform outbound](c0-1-platform-outbound.md)

> Next slice after #100 is **not** another module writer.  
> It hardens Intent policy, snapshots, and the migration map for remaining senders.

## Scope

- Unified Intent registry (durable / typed beyond seed enum)  
- Typed policy results (allow/deny with machine-readable codes)  
- Full message/delivery snapshot contract (intent, template, links, consent decision, automation id)  
- Canonical entity × channel × intent matrix  
- Migration map for remaining writers (`lead_communications`, `lead_rodo`, `candidate_notifications`, inbox dispatch)

## Out of scope

- Template admin UI, automation authoring UI, campaigns (C2)  
- Inbox UX (C1)  
- Full PublicActionLinkService product  
- Consent evidence engine product (contracts + minimal gate only if needed)

## Depends on

PR #100 merged: Intent-first outbound path + gate contract tests green.
