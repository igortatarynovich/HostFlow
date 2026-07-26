# ADR-031: Compliance outbound requires opaque module result (no Lead SMTP)

**Status:** Accepted  
**Date:** 2026-07-26  
**Layer of change:** Domain creation timing · Communication Pipeline · Compliance delivery  
**Authors:** Product + Platform architecture  
**Checklist:** [`architecture-review-checklist.md`](architecture-review-checklist.md) (L0 ×10 + INV-17) — completed below  
**Does not amend L0 constitution** — references P-01…P-05 / INV-09…17 / Catalog only  
**Related:** [INV-17](architecture-invariants.md) · [§8.0.1 Lead-stage RODO](../workflows/lead-intake-resolution-and-activity-continuity.md) · [applications-operating-model.md](applications-operating-model.md) · [application-creation-mvp.md](../workflows/application-creation-mvp.md) · [C5](../tasks/intake-communication-context-c5.md) · [C0.1b migration map](../tasks/c0-1b-legacy-writers-migration-map.md) · [task: compliance-outbound-pipeline](../tasks/compliance-outbound-pipeline-early-result.md) · Sales questionnaire binder (pattern)

---

## 1. Context

HostFlow has two correct, currently conflicting constraints:

| Constraint | Source | Meaning |
|------------|--------|---------|
| Art.14 / RODO gates on **Lead** before Process / request_info / contacted | §8.0.1 | Legal processing of applications requires notice satisfaction **before** gated intake actions |
| Every product outbound goes through **Communication Pipeline** | INV-17 / C5 | Thread Result Link → Context → Policy → Template → transport. Business modules must not call SMTP |

C2 opaque results are only **`sales_inquiry`** (Sales) and **`application`** (Recruitment). **`lead` is not a result type.**

Today:

- Sales can create **SalesInquiry** early (`ensure_sales_inquiry_for_transport_lead`) — questionnaire binder already uses Pipeline.
- Recruitment **Application** creation MVP forbids Application without **Candidate**, and Candidate is usually created at **Process** — so Meta/webhook leads cannot authorize Pipeline send for art.14 **before** Process.
- `lead_rodo.py` / `rodo.py` still bypass via `send_email_for_tenant` (legacy allowlist).
- Lead operational emails (`lead_communications.py`) are C5 **fail-closed** (`communication_pipeline_required`) and do not send.

Temporary escapes (Lead as result type, SMTP re-enable, “compliance exception” RFC that weakens INV-17) are **rejected**.

---

## 2. Decision (permanent)

### 2.1 Sole delivery path

All product emails that affect legal or candidate/client-facing status — including **art.14 RODO**, **application_received**, **rejection**, **moving_forward**, and future notice templates — MUST go through Communication Pipeline with Intent:

| Message | Intent (target) | Opaque result |
|---------|-----------------|---------------|
| Art.14 RODO | `gdpr_notice` | Sales → `sales_inquiry`; Recruitment → `application` |
| Application received / rejection / moving forward | `follow_up` (or dedicated workflow intents when catalogued) | Same destination result |
| Questionnaire | existing Sales purpose | `sales_inquiry` (already) |

Tenant SMTP remains a **platform transport adapter** only (`prepare_send` / Sender) — never a business-module caller for these paths.

### 2.2 Compliance SoT stays on Lead

§8.0.1 **gates and audit** (`Lead.normalized.rodo`, `LEAD_RODO_REQUIRED`, source-provided) remain the **compliance SoT**.

This ADR changes **delivery ownership**, not gate ownership:

```text
Lead.normalized.rodo     = compliance fact (sent | source_provided | …)
Communication Pipeline   = how "sent" is achieved when outbound email is required
```

Conversion still copies `rodo_lead_audit` to Candidate; default is **no re-send**.

### 2.3 Opaque result must exist before outbound

**Rule:** No `gdpr_notice` / Lead ops outbound until a **confirmed Thread Result Link** can be attached to the destination opaque result.

| Destination | Early result owner | Early ensure API (pattern) |
|-------------|--------------------|----------------------------|
| Sales | SalesInquiry | Existing `ensure_sales_inquiry_for_transport_lead` + Pipeline binder |
| Recruitment | Application (+ Candidate shell) | New Recruitment-owned ensure (see §2.4) |

### 2.4 Recruitment: early Candidate shell + Application (amends creation timing)

**Amends** [applications-operating-model.md](applications-operating-model.md) §6.3 and [application-creation-mvp.md](../workflows/application-creation-mvp.md) golden rule as follows.

**When** (all must hold):

1. Transport Lead exists with concrete recruitment intent: `vacancy_id` **or** explicit pool intent (`funnel_id` / `recruitment_pool_intent_v1`).
2. Destination routing is Recruitment (`candidate_application` / Flights-confirmed recruitment result path — not Sales).
3. Outbound compliance or operational email is **required now** (tenant RODO auto mode, manual send, or ops-email toggle that would fire), **or** public-intake path already materializes Application (existing R4 handler).

**Then** Recruitment MAY create, idempotently, in one transaction:

1. **Candidate shell** — minimal identity/contact for this recruitment subject; **not** Process; **not** full pipeline depth; must not make Lead UI a Candidate card.
2. **Application** — opaque result (`result_type=application`) linked to `lead_id` + `candidate_id`, status `applied` (lifecycle canon).
3. Stamp `Lead.normalized.intake_result_link_v1` (same shape as R4 transport link).

**Process** remains an **intake decision** (vacancy confirm, accept/reject, duplicate resolution). It must **not** be the first moment an Application can exist when §2.4 conditions already held.

**Still forbidden:**

- Application for Lead with **no** Candidate shell.
- Application while Lead is in unresolved `duplicate_review` without attach/create decision.
- Treating Lead as C2 `result_type`.
- Creating Candidate shell for Sales-bound leads.
- Dual destination links (SalesInquiry ⊕ Application) on one transport Lead.

Public intake R4 (`ensure_application_result_for_transport_lead`) already follows Candidate+Application; Meta/webhook/CSV auto paths must **converge** on the same Recruitment-owned ensure, not invent a second shape.

### 2.5 Module binders (pattern = Sales questionnaire)

Each module owns a binder that:

1. Resolves/ensures opaque result for the transport Lead.
2. Ensures email Thread + **confirmed** `communication_thread_result_links`.
3. Writes G13 entity links as required.
4. Returns `communication_purpose` + `CommunicationTemplateMetadata` (+ locale).
5. Does **not** call SMTP.

Callers (`lead_rodo`, ops hooks, manual API) call binder → `authorize_outbound_communication` → `prepare_and_send_communication` (or Intent execute). Fail-closed if binder cannot ensure result.

### 2.6 Explicit non-goals (permanent rejections)

| Rejected | Why |
|----------|-----|
| Temporary “compliance SMTP” exception | Violates INV-17 |
| Registering `lead` as C2 result type | Lead ≠ module result; INV-17 / domain registry |
| Growing `send_email_for_tenant` allowlist | C0.1b contract |
| Sync SMTP inside ingest without outbox/command | C0.0 |
| Candidate auto-RODO re-send after lead-satisfied conversion | Duplicate notice |
| Using Sales questionnaire binder for Recruitment Applications | Cross-module ownership |

---

## 3. Architecture Review Checklist (ADR gate)

| # | Answer |
|---|--------|
| 1 Owner | Recruitment owns Application + Candidate shell ensure; Sales owns SalesInquiry ensure; Communication Platform owns Pipeline/Sender; Lead module owns compliance **gates**/audit keys |
| 2 Existing capability? | Pipeline + SI early ensure + questionnaire binder exist; Recruitment early Application for Meta path missing; RODO/ops still legacy |
| 3 Adapter | Destination result ensure (module) → Pipeline binder → CommunicationSender / prepare_send (platform transport) |
| 4 Boundary | No Sales↔Recruitment imports; Lead remains transport + compliance SoT, not result type |
| 5 Settings | No new SMTP config; reuse `lead_rodo_v1` / `lead_communication_v1` as **policy** only |
| 6 SoT | Compliance fact on Lead; delivery via Pipeline messages/deliveries; Application/SI are opaque results |
| 7 Events | Prefer DomainEvent → command/outbox for auto sends (no domain commit that already talked to SMTP); audit events retained |
| 8 Requires | Confirmed Result Link; template metadata; Intent `gdpr_notice` / ops intents; Flights/routing destination when applicable |
| 9 License | No new license |
| 10 Contract | Additive binders + creation-timing amendment; remove legacy bypasses in same migration PRs (breaking for silent SMTP callers — intentional) |

**Invariants:** INV-17 preserved and enforced. INV-09…12 (intake spine) respected — destination ownership unchanged. No L0 constitution edit.

---

## 4. Consequences

### Positive

- Legal outbound and product outbound share one path.
- Meta/webhook recruitment can satisfy art.14 **before** Process without SMTP bypass.
- Allowlist shrinks toward empty for RODO/ops.

### Trade-offs

- Some Meta leads gain an early Candidate shell + Application before operator Process — must be UX-disciplined (Lead rail stays intake; Candidate not “opened” as full ops).
- Application creation docs must stay aligned with this ADR (single creation timing story).

### Follow-up (implementation)

Normative slices: [`compliance-outbound-pipeline-early-result.md`](../tasks/compliance-outbound-pipeline-early-result.md).

---

## 5. Doc amendments required in the same merge train

| Doc | Change |
|-----|--------|
| `applications-operating-model.md` §6.3 | Creation also allowed under ADR-031 §2.4 (not only at Process) |
| `application-creation-mvp.md` | Golden rule: Candidate shell + intent → Application; Process is not sole create moment |
| `lead-intake-resolution…` §8.0.1–8.0.2 | Delivery via Pipeline + binders; gates unchanged |
| `c0-1b-legacy-writers-migration-map.md` | Point RODO/ops rows at this ADR; shrink on merge |
| `intent_registry` (code) | Ensure `gdpr_notice` allows `application` for Recruitment |

---

## History

- 2026-07-26: **Accepted** — permanent path; temporary SMTP/Lead-result escapes rejected.
- 2026-07-26: Proposed.
