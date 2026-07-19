# Intake Communication Context — Stage 1 Runtime Determination Audit

**Status:** **ACTIVE** (call-site inventory · docs + R3 remediation started)  
**Epic:** [`../tasks/intake-domain-separation-communication-context-v1.md`](../tasks/intake-domain-separation-communication-context-v1.md)  
**Date:** 2026-07-19  

This is a **concrete call-site list**, not a narrative-only design note. Each row is an independent Candidate/Sales determination path that must stop guessing.

---

## Closed by Runtime Split R1–R3

| Call site | Was | Now |
|-----------|-----|-----|
| `forms_platform/handlers.py` default `or "candidate_application"` | Missing intent → Recruitment | **R1** fail-closed `forms_routing_unresolved` |
| `forms_platform/publication_bridge.py` publication resolve default | Same | **R1** `routing_status=unresolved` |
| `handlers.py` `sales_inquiry` → `recruitment.client_lead_draft` | Sales owned by Recruitment metadata | **R2** → `sales.inquiry_draft` / `module_owner=sales` |
| Destination dispatch | No callable handlers | **R3** `intake_platform/handler_dispatch.py` → `modules/sales` / `modules/recruitment` |
| Public lead-draft submit branch on `application_kind` | SoT for client vs candidate path | **R3** pinned `route_intent` → `dispatch_public_intake_submit` |

---

## Still open (must close in later stages)

### A. Destination / object creation still Lead-centric (R4)

| File | Lines / symbol | Independent determination |
|------|----------------|---------------------------|
| `entity_profile/public_intake_draft_session.py` | `submit_public_intake_lead_draft`, Decision Layer gates | Shared draft session for both destinations; Lead flags |
| `modules/leads/service/_processing.py` | Meta ingest `lead_type_for_route_intent` | Creates Lead; mixes funnel helpers |
| `modules/applications/mappers.py` | `lead_to_sales_inquiry` | SalesInquiry is a Lead projection |
| `modules/applications/listing.py` | Lead type filters | Queue split via Lead flags (R6) |

### B. Communication / acknowledgement without destination object (stages 5–6)

| File | Lines / symbol | Independent determination |
|------|----------------|---------------------------|
| `services/communication_deliveries/questionnaire_email.py` | `lead_type == "client"` gate (~144) | Questionnaire allowed by **Lead.lead_type**, not SalesInquiry / destination |
| `services/notification_templates.py` | `candidate.intake_submitted` catalog | Candidate-only event catalog; no Sales acknowledgement twin |
| `api/public/intake.py` | `event_type="candidate.intake_submitted"` (~4586) | Legacy candidate session emit |
| `api/v1/settings/communications.py` | Static “Acknowledge received” (~356) | Not keyed by destination module / purpose |
| Thread actions / automations (FE + API) | Various | May send without resolving Thread → destination object |

### C. Public / admin UI still derives kind from non-SoT signals (stages 5–7)

| File | Lines / symbol | Independent determination |
|------|----------------|---------------------------|
| `api/public/intake.py` | `_resolve_intake_application_kind`, `_lead_form_implies_client_application` (~115–150) | Infers client from FormPurpose / `service_sales.*` entity profile |
| `services/intake_form_admin_context.py` | `or "candidate_application"` defaults | Admin context defaults intent |
| `services/intake_mapping_admin_service.py` | `or "candidate_application"` | Mapping admin default |
| `entity_profile/legacy_bridge.py` | `module_owner: "recruitment"` (~137) | Legacy EP bridge always recruitment |
| Frontend module query / open queue | Product UI | Must not select template/domain (stage 6–7) |

### D. Fallback / legacy routing helpers (stage 8)

| File | Lines / symbol | Independent determination |
|------|----------------|---------------------------|
| `services/intake_router.py` | `_fallback_route_intent` (~114–119) | `business_type` → candidate/sales/unknown |
| Acquisition Stage 3C unresolved | disposition path | Correct fail-closed pattern — keep; do not default to Recruitment |

---

## Required end state per category

1. **Creation (A):** only destination handlers create result objects; Lead is transport at most.  
2. **Communications (B):** every send resolves Thread → Application \| SalesInquiry → module → purpose; incompatible templates rejected.  
3. **Labels (C):** `application_kind` / FormPurpose become derived display only.  
4. **Legacy (D):** unresolved → Intake Resolution queue; never auto-Recruitment.

---

## Acceptance scenario mapping

Bug: Sales Inquiry + B2B questionnaire + Recruitment acknowledgement email.

| Layer | Must resolve to |
|-------|-----------------|
| Routing | `sales_inquiry` |
| Destination | `sales` |
| Result | SalesInquiry (R4) |
| Communication | `sales` + purpose (e.g. `qualification_questionnaire_request` / Sales acknowledgement) |
| Forbidden | Any path that loads Recruitment acknowledgement because form/thread/locale/`application_kind` looked “candidate-like” |

---

## History

- 2026-07-19: Initial inventory after observed Recruitment acknowledgement on Sales Inquiry; R1/R2 closed; R3 handlers opened.
