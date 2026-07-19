# Canonical Intake Input Matrix

**Status:** **ACCEPTED / FROZEN**  
**Date:** 2026-07-19  
**Epic:** [`../tasks/intake-canonical-input-matrix.md`](../tasks/intake-canonical-input-matrix.md) · **COMPLETE**  
**Next:** [`../tasks/intake-runtime-split-v1.md`](../tasks/intake-runtime-split-v1.md) · **READY FOR IMPLEMENTATION**  
**Prerequisite:** Forms Builder MVP **COMPLETE** (`4cb2a148` / #61) · Acquisition Epic P Stage 3A–3D **COMPLETE**  
**Normative parents:** [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) · [`ADR-023`](ADR-023-recruitment-sales-module-separation.md) · [`intake-routing-foundation.md`](../modules/intake-routing-foundation.md) · [`ADR-007`](ADR-007-forms-platform-capability.md)

---

## Purpose

Freeze the **canonical input resolution chain** so one Forms Platform can accept submissions while **Intake Routing** unambiguously chooses the destination business process.

```text
Source profile → Provider → Published form binding → route_intent → intake_handoff → Destination module
```

**This document is accepted design SoT.** Runtime isolation is delivered by [`intake-runtime-split-v1.md`](../tasks/intake-runtime-split-v1.md) (R1–R6). Do not reopen this matrix for handler/queue work — implement against it.

---

## Vocabulary (anti-collision)

| Term | Meaning | Not a synonym for |
|------|---------|-------------------|
| **Intake Source Profile** | Routing config (`IntakeSourceProfile`) | Entity Profile (field composition) |
| **Provider** | `IntakeProvider` (meta, website, public_intake, …) | Channel / Goal Type |
| **Published form binding** | Publication / TenantLeadForm / Flight↔Form / Flight↔Profile | FormPurpose |
| **`route_intent`** | What to create in Intake | FormPurpose, Goal Type, Outcome, `application_kind` |
| **Forms `intake_handoff`** | Shared Intake payload from Forms (`presentation_values_v1`, answer contracts) | Recruitment→HR candidate handoff |
| **Destination module** | Recruitment \| Sales \| … | Universal Lead as product entity |
| **Flight / `CampaignRun`** | Campaign wave | A third entity name for “campaign” |
| **`application_kind`** | Public UI/state (`candidate` \| `client`) derived from intent | SoT for routing |

**Hard orthogonality (ADR-022 / ADR-024):**

- Goal Type ≠ `route_intent` ≠ Outcome  
- FormPurpose ≠ `route_intent`  
- Routing once per Lead; continuation submissions inherit context  

**Not routing SoT:** FormPurpose · Goal Type · Outcome · `application_kind` · `lead_type` · `lead_target_type`.

---

## Resolve order (normative)

1. **Source profile** — `IntakeSourceProfile.code` (+ optional `pipeline_preset`)  
2. **Provider** — `IntakeProvider` (+ Binding `external_key`)  
3. **Published form binding** — Endpoint specialization: HostFlow publication / Flight↔Form / Profile-linked form  
4. **Route intent** — `RouteIntent` SoT for “what to create”  
5. **Intake handoff** — Forms → Shared Intake contract (no domain mapping in Forms)  
6. **Destination module** — owns the resulting business object  

Forms Platform **accepts** the submission and emits `intake_handoff`.  
Intake Routing **decides** the destination **once** and hands off to **exactly one** destination — no Recruitment↔Sales fallback.  
Recruitment / Sales **do not** own the Public Form; they do not read publication directly; they do not analyze `application_kind`.

---

## Canonical matrix (V1 must-have rows)

| Source profile (example) | Provider | Published form binding | Route intent | Intake handoff | Destination module | Result object (ops) |
|--------------------------|----------|------------------------|--------------|----------------|--------------------|---------------------|
| Public vacancy / driver application profile | `public_intake` / `website` / `meta` | Flight↔Form or Profile-linked `TenantLeadForm` publication | `candidate_application` | `forms.normalized_answers.v1` → Shared Intake | **Recruitment** | Application / Candidate path |
| B2B / sales inquiry profile | `website` / `meta` / `public_intake` | same Endpoint pattern | `sales_inquiry` | same handoff **shape** | **Sales** | Sales Inquiry |

Aligned with `shared/campaign_registries.json` `promotion_targets`:

- `vacancy` / `search` → `target_module: recruitment` · `allowed_route_intents: [candidate_application]`  
- `service` / `client_account` → `target_module: sales` · `allowed_route_intents: [sales_inquiry]`  

### Documented later (not V1 runtime gate)

| Route intent | Destination (design) |
|--------------|----------------------|
| `service_request` | Sales / Services (TBD) |
| `partner_inquiry` | Future partner module |
| `unknown` | Disposition-only / triage queue (Stage 3C pattern) |

---

## Minimal split (product outcome)

| Route intent | Intake stream | Must not land in |
|--------------|---------------|------------------|
| `candidate_application` | **Recruitment intake** | Sales inquiry queue |
| `sales_inquiry` | **Sales intake** | Candidate / recruitment application queue |

**Key result:** one Forms Platform → many destination processes via Intake Routing — without Recruitment or Sales depending on Public Form.

---

## Known debt (tracked in Runtime Split — do not reopen matrix)

| Debt | Target (Runtime Split) |
|------|------------------------|
| Fail-closed missing intent | R1 — no `candidate_application` default |
| Destination registry | R2 — closed intent → destination → handler |
| `sales_inquiry` still recruitment-owned in legacy paths | R3 — Sales-owned handler; no cross-package imports |
| Lead as universal product entity | R4 — Application / SalesInquiry as result objects |
| Non-idempotent / non-transactional dispatch | R5 |
| Mixed queues / shared `type=` APIs | R6 |

---

## Out of scope for this document

- Implementing IntakeRouter branches (see Runtime Split)  
- Renaming handlers / migrations  
- Stage 3E Timeline  
- Publish UI (Forms P3)  
- Changing Field Catalog or Builder MVP  

---

## History

- 2026-07-19: Opened READY after Forms Builder MVP (`4cb2a148` / #61); design gate before Flights / Intake Routing runtime.
- 2026-07-19: **ACCEPTED / FROZEN**; matrix epic COMPLETE; Intake Runtime Split V1 opened; Flights / Intake Routing runtime UNLOCKED; Forms P3–P5 remain LOCKED.
