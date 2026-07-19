# Communication Context — C2 Resolver

**Status:** **COMPLETE** (implementation)  
**Parent gate:** [`intake-communication-context-c1-c6-gate.md`](intake-communication-context-c1-c6-gate.md)  
**Prerequisite:** C1 Thread Result Link **COMPLETE** (`#71`)  
**Unlocks:** C3 Module-owned Communication Policy Ports  

---

## Scope (only resolution)

```text
Thread Result Link → validated CommunicationContext
```

C2 **does not**: choose templates · send messages · import Recruitment/Sales ORM · read Lead · use `application_kind` / FormPurpose / `entity_type` · auto-fix legacy links · create result links · decide `communication_purpose` (C3).

---

## Immutable context

| Field | Notes |
|-------|--------|
| `thread_id` | |
| `module_owner` | |
| `result_type` | opaque |
| `result_id` | opaque |
| `communication_domain` | V1 == `module_owner` |
| `resolution_status` | `resolved` |
| `result_link_id` | |
| `provenance_ledger_id` | optional soft Flights ref |
| `resolved_at` | |
| `resolver_version` | `communication.context_resolver.v1` |

---

## Compatibility registry

| module_owner | result_type | communication_domain |
|--------------|-------------|----------------------|
| `recruitment` | `application` | `recruitment` |
| `sales` | `sales_inquiry` | `sales` |

Deterministic · no duplicate keys · no cross-owned mapping · fail-closed unknown owner/type · **no default domain**.

---

## Fail-closed

Missing link · multiple active links · incomplete opaque · unconfirmed ledger · unknown owner · unknown/incompatible `(owner, type)` · damaged/archived link · legacy entity kwargs.

None of these become Recruitment.

---

## History

- 2026-07-19: C2 implemented after C1 `#71` freeze.
