# Communication Context — C1 Thread Result Link Contract

**Status:** **COMPLETE** (implementation)  
**Parent gate:** [`intake-communication-context-c1-c6-gate.md`](intake-communication-context-c1-c6-gate.md)  
**Unlocks:** C2 Communication Context Resolver  

---

## Contract

```text
Thread → communication_thread_result_links → OpaqueResultRef (+ optional Flights ledger_id)
```

| Column | Role |
|--------|------|
| `module_owner` | `recruitment` \| `sales` |
| `result_type` | opaque type string |
| `result_id` | opaque id (shared layer must not join destination ORM) |
| `ledger_id` | soft `acq_flight_dispatch_ledger.id` provenance |
| `status` | `confirmed` \| `unresolved` |

**Not SoT:** Lead · `application_kind` · FormPurpose · URL · `entity_type`/`entity_id` · `linked_candidate_id`.

---

## API / helpers

- `backend.app.communications.result_link.attach_thread_result_link`
- `attach_thread_result_from_confirmed_ledger` (requires Flights `status=confirmed`)
- `require_confirmed_thread_result_link` (fail-closed for C2+)
- `POST /communications/threads` optional: `result_module_owner` / `result_type` / `result_id` / `provenance_ledger_id`
- `POST /communications/threads/{id}/result-link`

Fail-closed: missing link · incompatible second link · unconfirmed ledger · incomplete opaque triple.

---

## History

- 2026-07-19: C1 implemented after R5 / C1–C6 gate freeze.
