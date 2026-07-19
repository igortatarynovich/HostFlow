# Communication Context — C5 Send-path Migration

**Status:** **COMPLETE** (implementation)  
**Parent gate:** [`intake-communication-context-c1-c6-gate.md`](intake-communication-context-c1-c6-gate.md)  
**Prerequisite:** C4 Template Metadata Enforcement **COMPLETE** (`#74`)  
**Unlocks:** C6 Legacy unresolved handling · Queues/UI (R6) after C1–C5  

---

## Role

Migratory only — **no new architectural rules**.

```text
Thread Result Link → CommunicationContext → Module Policy
  → Template Metadata → Send
```

**Rule:** no transport may send unless it received permission from the full Communication Pipeline.

Sole outbound entry: `backend.app.communications.send_pipeline`  
(`authorize_outbound_communication` / `send_via_communication_pipeline`).

---

## Scope

All transports and initiators must use the same pipeline:

* Email · SMS · WhatsApp · Telegram · Internal notifications  
* Thread Actions · Automation workers · Scheduled jobs · Retry workers  
* Webhook callbacks that initiate communication  

No “simplified” send paths. Retries re-enter the same pipeline.

---

## Forbidden after C5

Direct from business modules:

* `send_email(...)` / `send_sms(...)` / `send_whatsapp(...)` (and tenant transport helpers)

without a validated `CommunicationContext` and approved template metadata.

Legacy Lead-scoped autosends without `thread_id` + purpose + template metadata are **fail-closed** (`communication_pipeline_required`).

---

## Acceptance

| Invariant | Result |
|-----------|--------|
| Send without Thread Result Link | deny |
| Send without resolved CommunicationContext | deny |
| Send without positive Policy | deny |
| Send without Template Metadata Gate | deny |
| Any transport | same pipeline |
| Any retry | same pipeline again |
| Legacy bypass | absent or redirected / fail-closed |
| Transport owns domain or template pick | forbidden |

Architectural seal: **INV-17** — sole outbound entry is the Communication Pipeline  
([`architecture-invariants.md`](../architecture/architecture-invariants.md)).

---

## History

- 2026-07-19: C5 implemented after C4 `#74`.
