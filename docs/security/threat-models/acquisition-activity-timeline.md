# Threat Model — Acquisition Activity Timeline (Stage 3E)

## Assets

- Append-only audit history of Acquisition inbound flow (`acquisition_activity_events`)
- Typed event payloads (may include opaque Lead/Candidate ids, routing codes — not full PII dumps by design)
- Tenant isolation for read/query of Timeline rows
- Idempotency keys (`source_event_id`) used by projectors / retries

## Trust boundaries

- Domain operation / outbox consumer → `append_activity_event` (same DB transaction preferred)
- Operator / future Read API → `list_activity_events` (tenant-scoped; RBAC in PR-3)
- Automation Engine **must not** treat Timeline as a message queue (ADR-024 §10)

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| AAT-1 | Cross-tenant read/write | Query/append without tenant filter or RLS bypass |
| AAT-2 | Audit tampering | UPDATE/DELETE of history rows; payload rewrite |
| AAT-3 | Idempotency collision across tenants | Unique key without `tenant_id` |
| AAT-4 | Ownership leak via FK | Typed FK from Timeline to Lead/Candidate/Sales/Recruitment tables |
| AAT-5 | Free-text / untyped dump of PII | Unvalidated payload accepting arbitrary JSON |
| AAT-6 | Confused deputy via Automation | Automation consuming Timeline table as event bus |

## Митигации (Stage 3E PR-1)

- Table has `tenant_id NOT NULL`; app queries always filter by `tenant_id`; PostgreSQL **RLS** policy `tenant_isolation`
- **Append-only:** no repository update/delete; PG trigger blocks any `UPDATE`/`DELETE`
- Unique partial index `(tenant_id, source_event_id)` WHERE `source_event_id IS NOT NULL`; duplicate append returns existing row
- FK only to Acquisition-owned `acq_campaigns` / `acq_campaign_runs`; Lead/Candidate ids only in typed payload refs
- Closed Event Catalog + per-type payload allowlists / required fields
- Public surface limited to `append_activity_event` + `list_activity_events` (no HTTP in PR-1)

## Тесты

- Contract suite `backend/tests/api/test_stage_3e_activity_foundation.py`: tenant isolation, idempotency, immutable UPDATE/DELETE, payload/version validation, migration roundtrip

## Связанные спеки

- [`docs/specs/architecture/ADR-024-acquisition-campaigns-intake-routing.md`](../../specs/architecture/ADR-024-acquisition-campaigns-intake-routing.md) §10 · §14.1  
- [`docs/specs/tasks/acquisition-stage-3e-activity-timeline.md`](../../specs/tasks/acquisition-stage-3e-activity-timeline.md)  
- [`docs/security/security-ssot.md`](../security-ssot.md) (RLS / tenant context)
