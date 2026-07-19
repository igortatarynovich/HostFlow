# Communication Context — C1–C6 Gate

**Status:** **ACTIVE** · C1–C3 COMPLETE · **C4 NEXT** · unlocked by R5 (`#69`) / C1 (`#71`) / C2 (`#72`)  
**Parent epic:** [`intake-domain-separation-communication-context-v1.md`](intake-domain-separation-communication-context-v1.md)  
**Decision gate:** INV-16 · L0 · Flights provenance · C1 opaque Thread link · C2 context  
**Still LOCKED until C1–C5:** Queues / UI (R6) · Forms P3–P5  

---

## Normative chain

```text
Forms → Flights → destination contract → module adapter → module-owned result
  → Thread Result Link → CommunicationContext
  → policy contract → module policy adapter → allow/deny
```

---

## Slices

| ID | Title | Status |
|----|-------|--------|
| **C1** | Thread Result Link Contract | ✅ COMPLETE — [`intake-communication-context-c1.md`](intake-communication-context-c1.md) / `#71` |
| **C2** | Communication Context Resolver | ✅ COMPLETE — [`intake-communication-context-c2.md`](intake-communication-context-c2.md) / `#72` |
| **C3** | Module-owned Communication Policy Ports | ✅ COMPLETE — [`intake-communication-context-c3.md`](intake-communication-context-c3.md) |
| **C4** | Template Metadata Enforcement | **NEXT** |
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
- 2026-07-19: C1 COMPLETE (`#71`); C2 COMPLETE (`#72`); C3 COMPLETE.
