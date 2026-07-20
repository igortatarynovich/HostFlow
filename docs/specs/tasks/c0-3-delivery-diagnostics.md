# C0.3 — Delivery Diagnostics

**Status:** ✅ Merged (PR #104 @ `95f2a525`)  
**Branch:** `fix/communication-c0-delivery-diagnostics`  
**Base:** `integration/release-product-a-b`  
**Parents:** [Epic C0](epic-c0-communication-integrity.md) · [Foundation](../architecture/communication-platform-foundation.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [C0.2](c0-2-inbound-resolver.md)

> For every send and delivery attempt the operator must know what happened, where it failed, whether retry is allowed, and what to show in UI — without server logs.

## Main contract

Message status, Delivery status, and Attempt status are separate layers.  
Provider status is never the operator-facing fact — only normalized canonical status + reason code.

## Scope (in)

1. Canonical state model (message / delivery / attempt)  
2. Immutable `CommunicationDeliveryAttempt` rows  
3. Error taxonomy + reason codes  
4. Retry policy driven by normalized reason (not error text)  
5. Unified provider callback path (normalize → resolve → transition → audit)  
6. Operator diagnostics API / timeline (no Inbox redesign)  
7. Retire or remap `lead.communication.failed`  
8. Legacy delivery migration map + contract tests banning direct provider status checks outside platform

## Scope (out)

- Inbox UX redesign (C1)  
- Stage 3 Sales product flow  
- Full multi-provider receipt adapters beyond the platform path seams  

## Canonical chains

**Progress:** `queued → accepted → sent → delivered`  

**Terminal negative:** `failed` | `rejected` | `bounced` | `expired` | `cancelled` | `undeliverable`

## Acceptance

- [x] No bare `failed` without reason code (`delivery_errors` + attempt writer)  
- [x] Attempt history immutable (retry = new attempt)  
- [x] Callbacks idempotent; out-of-order cannot downgrade `delivered`  
- [x] Retry only via policy; exhaustion → explicit terminal  
- [x] Operator diagnostics without server logs (`GET …/delivery-diagnostics`)  
- [x] `lead.communication.failed` producer retired → `communication.delivery.failed`  
- [x] Contract test: no provider-specific status checks outside diagnostics platform  
- [x] Legacy migration map: [c0-3-legacy-delivery-migration-map.md](c0-3-legacy-delivery-migration-map.md)  
- [x] Merge gates: state-machine allowlist · provider independence · immutable timeline · retry keeps Message/Delivery  

## Key modules

| Piece | Path |
|-------|------|
| Canon statuses | `backend/app/communications/delivery_canon.py` |
| Error taxonomy | `backend/app/communications/delivery_errors.py` |
| Retry policy | `backend/app/communications/delivery_retry.py` |
| Platform path | `backend/app/communications/delivery_diagnostics.py` |
| Attempt model | `backend/app/models/communication_delivery_attempt.py` |
| Unresolved callbacks | `backend/app/models/communication_delivery_callback_unresolved.py` |
| Migration | `backend/alembic/versions/202607200003_comm_delivery_diagnostics_c0_3.py` |
| API | `backend/app/api/v1/communications/routes/delivery_diagnostics.py` |
| Tests | `backend/tests/communications/test_c0_3_delivery_diagnostics.py` |

## Next after merge

**[C1 Communication Inbox Workspace](c1-communication-inbox-workspace.md)** — not Stage 3.  
Foundation status: [Communication Platform Foundation — complete](../architecture/communication-platform-foundation.md).
