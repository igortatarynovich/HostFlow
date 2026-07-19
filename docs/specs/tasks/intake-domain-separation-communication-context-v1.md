# Intake Domain Separation & Communication Context V1

**Status:** **READY FOR IMPLEMENTATION**  
**Prerequisite:** Canonical Input Matrix **ACCEPTED / FROZEN** · Runtime Split R1+R2 merged (`41e83eae` / #63)  
**Acceptance scenario (must close epic):** A Sales Inquiry that received a B2B questionnaire may send **only Sales-owned** communications. Recruitment acknowledgement is unavailable regardless of form, Thread UI, locale, or send path.  
**Parents:** [`intake-canonical-input-matrix.md`](../architecture/intake-canonical-input-matrix.md) · [`intake-runtime-split-v1.md`](intake-runtime-split-v1.md) · [`ADR-023`](../architecture/ADR-023-recruitment-sales-module-separation.md)  
**Still LOCKED:** Forms P3–P5 · physical queues/UI until Runtime Split R4–R5 done  

---

## Problem (observed)

Different surfaces independently “guess” Candidate vs Sales:

| Surface | Observed behavior |
|---------|-------------------|
| Queue | Treats row as B2B / Sales |
| Questionnaire | Client / B2B questionnaire |
| Email / automation | “recruitment team will review your application” |

Root cause is **not** a wrong template string. There is no single communication context derived from the routing decision.

---

## Target rule

After the primary routing decision, inbound type is fixed once and never recomputed:

```text
route_intent → destination → result object → communication context
```

| `route_intent` | Destination | Result object | Communication domain |
|----------------|-------------|---------------|----------------------|
| `candidate_application` | Recruitment | Application | `recruitment` |
| `sales_inquiry` | Sales | SalesInquiry | `sales` |

Form, Thread, and email automation **must not** independently infer type.

**Forbidden SoT:** `application_kind` · `lead_type` · `lead_target_type` · form title · FormPurpose · URL · template text · vacancy presence · frontend module query · open queue.

**Fail closed:** if domain object cannot be resolved uniquely → do not send; do not run automation; enqueue Intake Resolution with exact reason. Never default to candidate flow.

---

## Epic stages

| # | Stage | Status |
|---|-------|--------|
| 1 | Runtime determination audit (concrete call sites) | **ACTIVE** |
| 2 | Fail-closed routing | ✅ R1 (`#63`) |
| 3 | Recruitment/Sales destination handlers | ✅ R3 (`#64`) — **superseded as dispatch owner by R3.5** |
| 3.5 | Flights-owned dispatch boundary (L0) | ✅ COMPLETE (`#66`) |
| INV-16 | Decision Priority Rule | ✅ COMPLETE (`#67`) |
| 4 | Independent result objects | ✅ R4 (`#65`) behind module ports |
| 5 | Thread business-context resolution | AFTER R5 |
| — | **R5 provenance / exactly-once** | **NEXT** — [`intake-r5-provenance-gate.md`](intake-r5-provenance-gate.md) |
| 6 | Module-owned communication policies + template metadata | AFTER stage 5 |
| 7 | Separate APIs and queues | Runtime Split R6 · **LOCKED** until after R5 + Communication Context |
| 8 | Legacy resolution queue | AFTER stage 7 |

**Order rule:** do not split queues/UI (7) before R5 provenance + Communication Context Resolver (stages 5–6). Visual separation on mixed backend is not isolation. R5 must not use a cross-module shared DB transaction ([`intake-r5-provenance-gate.md`](intake-r5-provenance-gate.md)).

---

## Communication Context Resolver (stage 5–6)

```text
Thread → linked destination object → module_owner → allowed communication purposes
```

Template selection:

```text
destination module + communication_purpose + locale
```

Example for the bug:

```text
sales + qualification_questionnaire_request + pl
```

Candidate templates must be **backend-rejected** for SalesInquiry threads.

Separate acknowledgement handlers (shared transport only):

- Recruitment acknowledgement  
- Sales acknowledgement  

No shared “application received” handler that branches on Candidate vs Client text.

---

## Mandatory tests (epic DoD)

- [ ] B2B submission does not create Application  
- [ ] Candidate submission does not create SalesInquiry  
- [ ] SalesInquiry cannot receive recruitment acknowledgement  
- [ ] Application cannot receive B2B questionnaire  
- [ ] Sales thread cannot invoke Recruitment template  
- [ ] Missing routing context blocks send  
- [ ] Ambiguous entity links block send  
- [ ] Changing URL / frontend module does not change domain  
- [ ] Changing `application_kind` does not change domain  
- [ ] Reprocess does not create second object / second acknowledgement  
- [ ] Legacy unresolved never auto-lands in Recruitment  

---

## Relation to Runtime Split V1

Runtime Split R1–R6 remains the backend isolation spine. This epic adds **communication + Thread context** on top and tracks Stage 1 audit + acceptance scenario for the email bug.

| Runtime Split | Communication Context |
|---------------|----------------------|
| R1 fail-closed | Stage 2 |
| R2 registry | Stage 2 |
| R3 handlers (intermediate) | Stage 3 |
| R3.5 Flights dispatch | Stage 3 boundary |
| R4 result objects | Stage 4 |
| R5 Flights provenance / exactly-once | **required before** stages 5–6 |
| R6 queues/APIs | Stage 7 |

---

## History

- 2026-07-19: Opened after Sales Inquiry received Recruitment acknowledgement while B2B questionnaire was active; R1/R2 already merged.
