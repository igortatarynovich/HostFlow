# Communication Context — C1–C6 Gate

**Status:** **PARKED** · C1–C5 **COMPLETE** ([#71](https://github.com/igortatarynovich/HostFlow/pull/71)–[#75](https://github.com/igortatarynovich/HostFlow/pull/75), 2026-07-19) · **C6 not started, unowned, not scheduled** — [unowned work register](../gates/v1-unowned-work-register.md)  
**Parent epic:** [`intake-domain-separation-communication-context-v1.md`](intake-domain-separation-communication-context-v1.md)  
**Still LOCKED:** Forms P4 / P5 (P3 Publish is v1 blocker 3 — [brief](external-intake-forms-publish.md)). Queues / UI are gated by product **R6**, not by this chain  

C1–C5 complete already unlocked Queues/UI (R6) from the Communication Context chain perspective; R6 remains locked on its own table-cutover grounds.

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
| **C4** | Template Metadata Enforcement | ✅ COMPLETE — `#74` |
| **C5** | Send-path migration | ✅ COMPLETE — [`intake-communication-context-c5.md`](intake-communication-context-c5.md) · **INV-17** |
| **C6** | Legacy unresolved handling | **NEXT** |

**Order is mandatory.** Do not unlock queues/UI before C1–C5 (now complete).

---

## Acceptance (epic)

SalesInquiry + B2B questionnaire + **any** send path → always:

```text
sales + qualification_questionnaire_request
```

Recruitment acknowledgement is unreachable (backend enforce).

---

## History

- 2026-07-19: C1–C3 COMPLETE (`#71`–`#73`); C4 Template Metadata Enforcement COMPLETE (`#74`).
- 2026-07-19: C5 Send-path migration COMPLETE; INV-17 adopted; C6 NEXT.
