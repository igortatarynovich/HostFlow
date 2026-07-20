# C0.3 — Legacy delivery paths migration map

**Status:** Normative for C0.3  
**Parent:** [c0-3-delivery-diagnostics.md](c0-3-delivery-diagnostics.md)

Maps pre-C0.3 delivery / failure facts onto the diagnostics platform.  
Platforms do not depend on modules; modules consume public diagnostics contracts.

## Sources of truth (after C0.3)

| Fact | Canonical store | Operator API |
|------|-----------------|--------------|
| Message status | `communication_messages.delivery_status` | message DTO + diagnostics |
| Delivery status | `communication_deliveries.status` (canonical) | diagnostics |
| Attempt history | `communication_delivery_attempts` (immutable) | diagnostics timeline |
| Normalized reason | `reason_code` on attempt + delivery.meta.diagnostics | diagnostics |
| Raw provider payload | `attempt.raw_provider_payload` / delivery.meta.last_raw_callback | **not** in operator DTO |
| Unresolved receipts | `communication_delivery_callback_unresolved` | ops queue (later UI) |

## Legacy path → target

| Legacy | Status | Target |
|--------|--------|--------|
| `message.payload.dispatch.attempt_count` / `next_retry_at` | Compat mirror | Written by diagnostics retry scheduling; attempts table is SoT for history |
| `PATCH /messages/{id}/delivery-status` with `provider_payload` | Routed | `apply_delivery_callback` (unified path) |
| Direct `delivery.status = failed` + free-text `error_detail` in send path | Migrated | `record_delivery_attempt` + reason taxonomy |
| `lead.communication.failed` audit event | **Retired producer** | `communication.delivery.failed` with `reason_code` |
| Provider-specific status polling outside platform | **Forbidden** | Contract test + callback ingress only |
| `DELIVERY_STATUS_UNDELIVERED` / `unknown` | Alias | Normalize via `delivery_canon.normalize_canonical_status` |

## Callback ingress (required)

```text
provider webhook/payload
  → normalize_delivery_callback
  → resolve delivery (id / message / provider_message_id)
  → apply_delivery_state_transition (monotonic; no delivered downgrade)
  → record attempt (when applied) + persist raw callback
  → else unresolved callback queue
```

Public seam: `POST /communications/public/delivery-callback/{provider}`  
Authenticated operator read: `GET /communications/messages/{id}/delivery-diagnostics`  
Manual retry: `POST /communications/messages/{id}/delivery-retry` (audited).

## Module boundary

- Modules (Sales, Recruitment, Lead ops) must not interpret provider status strings.
- Modules may read diagnostics DTO / reason codes only.
- New providers adapt **into** `normalize_delivery_callback`, not into Inbox or Lead UI.
