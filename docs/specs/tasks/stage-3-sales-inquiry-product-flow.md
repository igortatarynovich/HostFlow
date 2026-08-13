# Stage 3 slice 3 — SalesInquiry product flow

**Status:** **IN PROGRESS** (code — `feat/stage-3-slice-3-sales-inquiry-product-flow`)  
**Branch (docs):** `docs/stage-3-slice-3-sales-inquiry-product-flow` ✅ merged #223  
**Branch (code):** `feat/stage-3-slice-3-sales-inquiry-product-flow`  
**Parents:** [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase B](../architecture/platform-completion-roadmap.md) · [Pipeline v1 seal](../architecture/sales-domain-pipeline-v1.md) · Stage 3 [slice 1](stage-3-sales-pipeline-product-wiring.md) · [slice 2](stage-3-sales-pipeline-convert-entrypoints.md) · [Meta Intake Completeness](meta-intake-completeness.md) · [ADR-022 Flow Spec](../workflows/adr022-phase2-sales-only-capability-flow.md) · [Intake Runtime Split](intake-runtime-split-v1.md)

> Product identity for Sales inbox/workspace = **SalesInquiry**.  
> Lead remains **transport / payload facade** only — not Sales product SoT.

---

## Why this slice

Domain convert is sealed (PR #98 / #99). Sales HTTP/UI still:

- lists/gets via `list_leads(lead_type=client)` + `lead_to_sales_inquiry`
- uses **Lead id** as `ApplicationOut.id`
- patches stage via Lead endpoints
- FE pages still call `getLead` / `listLeads` for inquiry work

Pipeline seal gap #3: demote Lead in Sales UI/API — SalesInquiry is product SoT  
([sales-domain-pipeline-v1.md](../architecture/sales-domain-pipeline-v1.md) §3).

Slice 1 explicitly deferred this: “Full Lead demotion across Sales UI/API (later Stage 3 slice).”

---

## Goal

Make **SalesInquiry** the product identity and read/write spine for the Sales inbox/workspace.  
Lead stays transport/compat (Meta payload, questionnaire invite storage, legacy HTTP).

---

## In scope (code PR — after this brief + Meta merge)

1. **List/get** resolve through `sales_inquiries` (join Lead for display fields until field migration).  
2. Expose **`sales_inquiry_id`** and **`transport_lead_id`** on `ApplicationOut`; product id prefers SI id (compat: accept Lead id on path during transition).  
3. Stage/status mutations are SI-owned (dual-write Lead stage as projection OK).  
4. Primary Sales FE (`SalesApplicationWorkspace`, inquiry rails) stop using `getLead`/`listLeads` for the core card — applications/SalesInquiry API only.  
5. Contract tests: Sales list/get keyed by SI; convert + Review still work via SI or Lead key; Recruitment API unchanged.  
6. Sales list never returns Candidate Application rows (R6-lite negative for Sales path).

---

## Out of scope (slice 4 / R6 / later)

| Deferred | Owner |
|----------|--------|
| Hard module separation (ADR-023 full DoD) | **Stage 3 slice 4** |
| Full R6 physically separate queues/APIs + Recruitment demotion | [intake-runtime-split-v1.md](intake-runtime-split-v1.md) R6 |
| Persist Meta answers / questionnaire on `sales_inquiries` columns | Meta deferred → later field migration |
| Delete `/leads/{id}/convert-client` or Leads CRM wholesale | Later |
| Forms `FormSubmissionEnvelope` for Meta | Phase C |
| Communication rewrite | Closed / frozen |

---

## Acceptance

- Operator Sales inbox/workspace identity = **SalesInquiry** (stable in UI/API).  
- Convert + Review + capability-spine still work.  
- Lead HTTP remains **compat**, not primary Sales SoT.  
- Meta form answers remain visible on the inquiry card (depends on Meta Intake Completeness).  
- Docs: this brief sealed; queue points at **feat** code PR next.

---

## Relation to Meta Intake Completeness

Meta (#222) keeps answers on **Lead.payload / normalized** and surfaces them on the Sales projection.  
Slice 3 **must not** move answers onto `sales_inquiries` in the same PR.  
Join Lead for display until a dedicated field-migration slice.

**Code order:** Meta merge → `feat/stage-3-slice-3-sales-inquiry-product-flow`.

---

## Relation to slice 4

| Slice | One-line |
|-------|----------|
| **3** | SalesInquiry product identity / Lead demotion on Sales path (transitional join OK) |
| **4** | Hard module separation — no dual Lead product entity; ADR-023 operational independence |

Do **not** mix slice 4 into slice 3.

---

## Likely code files (for the feat PR)

| Area | Paths |
|------|--------|
| API | `backend/app/modules/applications/router.py`, `mutations.py`, `mappers.py`, `schemas.py`, listing |
| Domain | `backend/app/modules/sales/services/*`, `capability_spine_read.py` |
| FE | `hostflow-frontend/src/api/applications.ts`, `pages/sales/*`, application-workspace, sales components still on `leadId` |
| Tests | `backend/tests/modules/sales/test_stage3_slice3_*.py` |

---

## DoD

- [x] Brief sealed with in/out + acceptance  
- [x] Queue + roadmap point at this brief  
- [x] Boundary vs slice 4 / R6 explicit  
- [x] Code feat PR — list/get/patch SI identity + `transport_lead_id`; FE Lead sections use transport id  
- [x] Spine / duplicates resolve by SI id (compat Lead id)  
- [x] Sales list pages `sales_inquiries` ⨝ Lead (ensure missing SI for Meta orphans)  
- [x] Contract tests: identity + HTTP list/get/spine/patch (`test_stage3_slice3_product_identity.py`); dedicated CI step in `backend-ci.yml`  
