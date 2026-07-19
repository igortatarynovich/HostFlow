# Communication Context — C1–C6 Gate

**Status:** **ACTIVE** · C1–C2 COMPLETE · **C3 NEXT** · unlocked by R5 (`#69`) / C1 (`#71`)  
**Parent epic:** [`intake-domain-separation-communication-context-v1.md`](intake-domain-separation-communication-context-v1.md)  
**Decision gate:** INV-16 · L0 · Flights provenance SoT · C1 opaque Thread link  
**Still LOCKED until C1–C5:** Queues / UI (R6) · Forms P3–P5  

---

## Prerequisite (R5 + C1)

Resolver may run only because:

1. Flights owns dispatch provenance (R5)  
2. Thread stores opaque result ref only (C1) — not destination ORM  
3. Confirmed ledger soft-ref is optional and never owned by communications  

Normative chain after C2:

```text
Thread → OpaqueResultRef → Communication Context
```

Then C3: `Communication Context → module-owned communication policy port`.

Forbidden SoT: Lead · `application_kind` · `lead_type` · FormPurpose · form title · URL · queue · frontend module · template text · legacy `entity_type` / `entity_id`.

---

## C2 resolver result (implemented)

See [`intake-communication-context-c2.md`](intake-communication-context-c2.md).

| Field | Required |
|-------|----------|
| `module_owner` · `result_type` · `result_id` | yes |
| `communication_domain` | yes (= module_owner in V1) |
| `resolution_status` · `result_link_id` · `thread_id` | yes |
| `provenance_ledger_id` | optional soft |
| `resolved_at` · `resolver_version` | yes |

**Not in C2:** `allowed_communication_purposes` — that is **C3**.

---

## Fail-closed send rules (epic; enforced progressively)

Block send when any of:

- Thread not linked to confirmed result object (C1/C2)  
- Multiple incompatible / active result references (C1/C2)  
- Provenance not confirmed when ledger present (C1/C2)  
- Module communication policy/adapter missing (C3)  
- Purpose not allowed by result owner (C3)  
- Template metadata ≠ `module_owner` + purpose (C4)  

No Lead / form / legacy-event fallback.

---

## Slices

| ID | Title | Status |
|----|-------|--------|
| **C1** | Thread Result Link Contract | ✅ COMPLETE — [`intake-communication-context-c1.md`](intake-communication-context-c1.md) / `#71` |
| **C2** | Communication Context Resolver | ✅ COMPLETE — [`intake-communication-context-c2.md`](intake-communication-context-c2.md) |
| **C3** | Module-owned Communication Policy Ports | **NEXT** |
| **C4** | Template Metadata Enforcement | AFTER C3 |
| **C5** | Send-path migration | AFTER C4 |
| **C6** | Legacy unresolved handling | AFTER C5 |

**Order is mandatory.** Do not unlock queues/UI before C1–C5.

---

## Acceptance (epic)

SalesInquiry + B2B questionnaire + **any** send path → always:

```text
sales + qualification_questionnaire_request
```

Recruitment acknowledgement is unreachable on that path (backend enforce, not UI hide).

---

## History

- 2026-07-19: Opened after R5 merge; C1–C6 freeze accepted.
- 2026-07-19: C1 Thread Result Link Contract COMPLETE (`#71`).
- 2026-07-19: C2 Communication Context Resolver COMPLETE.
