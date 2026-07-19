# Communication Context — C1–C6 Gate

**Status:** **ACTIVE** · C1–C4 COMPLETE · **C5 NEXT** · unlocked by R5 / C1–C3  
**Parent epic:** [`intake-domain-separation-communication-context-v1.md`](intake-domain-separation-communication-context-v1.md)  
**Still LOCKED until C1–C5:** Queues / UI (R6) · Forms P3–P5  

---

## Normative chain

```text
Thread → Result Link → CommunicationContext → Module Policy
  → Template Metadata (C4) → Send (C5)
```

---

## Slices

| ID | Title | Status |
|----|-------|--------|
| **C1** | Thread Result Link Contract | ✅ COMPLETE — `#71` |
| **C2** | Communication Context Resolver | ✅ COMPLETE — `#72` |
| **C3** | Module-owned Communication Policy Ports | ✅ COMPLETE — `#73` |
| **C4** | Template Metadata Enforcement | ✅ COMPLETE — [`intake-communication-context-c4.md`](intake-communication-context-c4.md) |
| **C5** | Send-path migration | **NEXT** |
| **C6** | Legacy unresolved handling | AFTER C5 |

**Order is mandatory.** Do not unlock queues/UI before C1–C5.

---

## Acceptance (epic)

SalesInquiry + B2B questionnaire + **any** send path → always:

```text
sales + qualification_questionnaire_request
```

Recruitment acknowledgement is unreachable (backend enforce).

---

## History

- 2026-07-19: C1–C3 COMPLETE (`#71`–`#73`); C4 Template Metadata Enforcement COMPLETE.
