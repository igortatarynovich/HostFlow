# Intake Domain Separation & Communication Context V1

**Status:** **ACTIVE** · C1–C4 COMPLETE · **C5 NEXT** (R5 COMPLETE `#69`)  
**Prerequisite:** Canonical Input Matrix **ACCEPTED / FROZEN** · Runtime Split R1–R5 COMPLETE · INV-16 · R3.5  
**Acceptance scenario (must close epic):** A Sales Inquiry that received a B2B questionnaire may send **only Sales-owned** communications. Recruitment acknowledgement is unavailable regardless of form, Thread UI, locale, or send path.  
**Parents:** [`intake-canonical-input-matrix.md`](../architecture/intake-canonical-input-matrix.md) · [`intake-runtime-split-v1.md`](intake-runtime-split-v1.md) · [`intake-r5-provenance-gate.md`](intake-r5-provenance-gate.md) · [`ADR-023`](../architecture/ADR-023-recruitment-sales-module-separation.md) · [`../architecture/decision-priority-rule.md`](../architecture/decision-priority-rule.md)  
**Gate:** [`intake-communication-context-c1-c6-gate.md`](intake-communication-context-c1-c6-gate.md)  
**Still LOCKED:** Forms P3–P5 · Queues/UI until **C1–C5** complete  

---

## Current status

| Stage | Status |
|-------|--------|
| R1 fail-closed routing | ✅ COMPLETE |
| R2 destination registry | ✅ COMPLETE |
| R3 intermediate split | ✅ COMPLETE |
| R3.5 Flights-owned boundary | ✅ COMPLETE (`#66`) |
| R4 independent result objects | ✅ COMPLETE |
| R5 provenance / exactly-once | ✅ COMPLETE (`#69`) |
| **Communication Context Resolver** | **NEXT** (C1–C6) |
| Queues/UI | **LOCKED** |
| Forms P3–P5 | **LOCKED** |

### What R5 guarantees (foundation for this epic)

- Flights owns dispatch provenance.  
- `OpaqueResultRef` does not expose destination-module internals.  
- Replay after `confirmed` does not reach the adapter.  
- Reprocess does not create a second Application or SalesInquiry.  
- Missing / ambiguous → fail-closed.  
- No Recruitment fallback.  
- Exactly-once is **not** a shared cross-module DB transaction.

Canonical intake boundary (unchanged):

```text
Forms → Flights → Contract → Adapter → Module-owned Result
```

---

## Problem (observed)

Different surfaces independently “guess” Candidate vs Sales:

| Surface | Observed behavior |
|---------|-------------------|
| Queue | Treats row as B2B / Sales |
| Questionnaire | Client / B2B questionnaire |
| Email / automation | “recruitment team will review your application” |

Root cause is **not** a wrong template string. There is no single communication context derived from **confirmed Flights provenance**.

---

## Target rule

Resolver must rely **only** on confirmed R5 result:

```text
Thread → confirmed Flights dispatch provenance → OpaqueResultRef → module communication contract
```

**Not** on: Lead · `application_kind` · `lead_type` · FormPurpose · form title · URL · queue · frontend module · template text.

| `route_intent` | Destination | Result object | Communication domain |
|----------------|-------------|---------------|----------------------|
| `candidate_application` | Recruitment | Application | `recruitment` |
| `sales_inquiry` | Sales | SalesInquiry | `sales` |

Form, Thread, and email automation **must not** independently infer type.

---

## Recommended resolver result contract

Minimum fields:

| Field | Meaning |
|-------|---------|
| `module_owner` | `recruitment` \| `sales` |
| `result_type` | opaque type string (`application` \| `sales_inquiry`) |
| `result_id` | opaque id for shared communication layer |
| `communication_domain` | same owner domain for policies/templates |
| `allowed_communication_purposes` | purposes published by module policy port |
| `provenance_ref` | Flights ledger / dispatch id |
| `resolution_status` | `resolved` \| `unresolved` \| `ambiguous` \| … |

`result_id` remains **opaque** to the shared communication layer — no destination ORM graph.

---

## Fail-closed (send blocked when)

- Thread is not linked to a **confirmed** result object  
- Multiple incompatible result references  
- Provenance is not confirmed  
- Module communication adapter / policy port missing  
- Purpose not allowed by the result owner  
- Template metadata does not match `module_owner` + purpose  

**No fallback** via Lead, form, or legacy event type.

---

## Implementation slices (C1–C6)

| # | Slice | Status |
|---|-------|--------|
| **C1** | Thread Result Link Contract — Thread ↔ opaque result ref (not foreign ORM) | ✅ COMPLETE — [`intake-communication-context-c1.md`](intake-communication-context-c1.md) |
| **C2** | Communication Context Resolver — unique owner + result type | ✅ COMPLETE — [`intake-communication-context-c2.md`](intake-communication-context-c2.md) |
| **C3** | Module-owned Communication Policy Ports — Recruitment/Sales publish purposes | ✅ COMPLETE — [`intake-communication-context-c3.md`](intake-communication-context-c3.md) |
| **C4** | Template Metadata Enforcement — backend rejects cross-domain templates | ✅ COMPLETE — [`intake-communication-context-c4.md`](intake-communication-context-c4.md) |
| **C5** | Send-path migration — email/SMS/WhatsApp/automations/Thread actions via resolver | **NEXT** |
| **C6** | Legacy unresolved handling — no send; resolution state | AFTER C5 |
| — | Queues/UI (Runtime Split R6) | **LOCKED** until C1–C5 |

---

## Main acceptance test

**SalesInquiry + B2B questionnaire + any send path** must always resolve as:

```text
sales + qualification_questionnaire_request
```

and must have **no technical access** to Recruitment acknowledgement.

---

## Mandatory tests (epic DoD)

- [ ] B2B submission does not create Application  
- [ ] Candidate submission does not create SalesInquiry  
- [ ] SalesInquiry cannot receive recruitment acknowledgement  
- [ ] Application cannot receive B2B questionnaire  
- [ ] Sales thread cannot invoke Recruitment template  
- [ ] Missing routing / unconfirmed provenance blocks send  
- [ ] Ambiguous entity links block send  
- [ ] Changing URL / frontend module does not change domain  
- [ ] Changing `application_kind` does not change domain  
- [ ] Reprocess does not create second object / second acknowledgement  
- [ ] Legacy unresolved never auto-lands in Recruitment  

---

## Relation to Runtime Split V1

| Runtime Split | Communication Context |
|---------------|----------------------|
| R1–R2 fail-closed + registry | Foundation |
| R3 / R3.5 / R4 | Isolation + result objects |
| R5 Flights provenance | ✅ required SoT for C1–C6 |
| R6 queues/APIs | AFTER C1–C5 |

---

## History

- 2026-07-19: Opened after Sales Inquiry received Recruitment acknowledgement while B2B questionnaire was active.  
- 2026-07-19: R5 COMPLETE `#69`; opened C1–C6 gate; queues/UI remain LOCKED until C1–C5.
