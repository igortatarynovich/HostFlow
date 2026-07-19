# Communication Context — C1–C6 Gate

**Status:** **ACTIVE** · C1 COMPLETE · **C2 NEXT** · unlocked by R5 (`#69` / `ed781d70`)  
**Parent epic:** [`intake-domain-separation-communication-context-v1.md`](intake-domain-separation-communication-context-v1.md)  
**Decision gate:** INV-16 · L0 · Flights provenance SoT  
**Still LOCKED until C1–C5:** Queues / UI (R6) · Forms P3–P5  

---

## Prerequisite (R5)

Communication Context may start only because R5 guarantees:

1. Flights owns dispatch provenance  
2. Opaque result refs only (`module_owner` · `result_type` · `result_id`)  
3. Confirmed ⇒ no second adapter invoke  
4. Fail-closed missing/ambiguous; no Recruitment fallback  
5. Exactly-once without cross-module shared transaction  

Resolver chain (normative):

```text
Thread → confirmed Flights dispatch provenance → OpaqueResultRef → module communication contract
```

Forbidden SoT for resolution: Lead · `application_kind` · `lead_type` · FormPurpose · form title · URL · queue · frontend module · template text · legacy event type.

---

## Resolver result contract (minimum)

| Field | Required |
|-------|----------|
| `module_owner` | yes |
| `result_type` | yes |
| `result_id` | yes (opaque to shared layer) |
| `communication_domain` | yes |
| `allowed_communication_purposes` | yes |
| `provenance_ref` | yes |
| `resolution_status` | yes |

---

## Fail-closed send rules

Block send when any of:

- Thread not linked to confirmed result object  
- Multiple incompatible result references  
- Provenance not confirmed  
- Module communication policy/adapter missing  
- Purpose not allowed by result owner  
- Template metadata ≠ `module_owner` + purpose  

No Lead / form / legacy-event fallback.

---

## Slices

| ID | Title | DoD (slice) |
|----|-------|-------------|
| **C1** | Thread Result Link Contract | ✅ COMPLETE — [`intake-communication-context-c1.md`](intake-communication-context-c1.md) |
| **C2** | Communication Context Resolver | **NEXT** |
| **C3** | Module-owned Communication Policy Ports | Recruitment and Sales independently publish allowed purposes |
| **C4** | Template Metadata Enforcement | Backend rejects cross-domain template usage |
| **C5** | Send-path migration | Email, SMS, WhatsApp, automations, Thread actions all call resolver |
| **C6** | Legacy unresolved handling | Unconfirmed / legacy threads do not send; enter resolution state |

**Order is mandatory.** Do not start C5 send-path migration before C1–C4. Do not unlock queues/UI before C1–C5.

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
- 2026-07-19: C1 Thread Result Link Contract COMPLETE.
