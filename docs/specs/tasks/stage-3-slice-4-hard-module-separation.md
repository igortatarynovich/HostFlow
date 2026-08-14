# Stage 3 slice 4 — hard module separation

**Status:** **DONE** ([#238](https://github.com/igortatarynovich/HostFlow/pull/238) merged 2026-08-13)  
**Branch (docs):** `docs/stage-3-slice-4-hard-module-separation`  
**Branch (code):** `feat/stage-3-slice-4-hard-module-separation` (after this brief merges)  
**Parents:** [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase B](../architecture/platform-completion-roadmap.md) · [ADR-023](../architecture/ADR-023-recruitment-sales-module-separation.md) · [UI Constitution](../architecture/ui-constitution-v1.md) · [Intake Runtime Split](intake-runtime-split-v1.md) · Stage 3 [slice 3](stage-3-sales-inquiry-product-flow.md) ✅ [#224](https://github.com/igortatarynovich/HostFlow/pull/224)

> Lead is **not** a dual operational product entity.  
> Sales work object = **SalesInquiry**. Recruitment work object = **Application**.  
> `/app/leads` is not a product inbox.

---

## Why this slice

Slice 3 closed SalesInquiry identity on the Sales inbox/workspace. The mixed CRM leftover remains:

- `/app/leads` + `/app/leads/:id` still exist as a dual Lead work surface ([ui-constitution-v1.md](../architecture/ui-constitution-v1.md) §8)
- Entity deep-link catalog maps `lead` → `/app/leads/{id}` on the **recruitment** host (`shared/module_deploy_hosts.json`)
- Recruitment list is still Lead-backed (`list_recruitment_inbox_leads` + `lead_to_recruitment_application`) — allowed as **transport projection**, not as a second product inbox
- Reminders, Work Hub, onboarding, client-origin links still point at `/app/leads/:id`

ADR-023 level 3: operational UI must not use a shared `/leads` product contract for both businesses.

---

## Goal

Remove Lead as a **product** object that is both candidate and client. Operators open the owning module workspace. Lead HTTP stays transport / admin / compat.

This slice does **not** claim ADR-023 full eight-level DoD (settings, automations, analytics, production DNS cutover).

---

## In scope (code PR — after this brief)

1. **`/app/leads/:id` is a redirector**, not a work card:
   - client / SalesInquiry transport → `salesInquiryPath`
   - recruitment Application transport → `recruitmentApplicationPath`
2. **`/app/leads` is not a mixed product inbox.** Diagnostic query (`needs_routing` / `failed`) stays on the existing Meta/admin surface. Default list redirects to the owning module inbox (Sales inquiries or Recruitment applications — not a combined Lead kanban).
3. **Deep links** that still emit `/app/leads/{id}` (entity catalog, reminders, Work Hub, onboarding, client origin) resolve to the owning workspace.
4. **Contract tests:**
   - Recruitment `GET /api/v1/recruitment/applications` never returns a SalesInquiry / client-lead row (R6-lite recruitment; Sales side already in slice 3)
   - Opening a client transport Lead id lands on SalesInquiry workspace, not LeadDetailPage
   - Opening a recruitment transport Lead id lands on Recruitment Application workspace
5. `/api/v1/leads` remains mounted as **compat / admin / ingest** — not the operational Sales or Recruitment inbox.

---

## Out of scope

| Deferred | Owner |
|----------|--------|
| Module settings split / enable-disable | **Stage 5** (ADR-005 / ADR-035) |
| Production DNS/TLS subdomain cutover | Stage 6 follow-up (6A–6C runtime already done) |
| Full R6: RecruitmentApplication table as list SoT; physically separate intake queues | [intake-runtime-split-v1.md](intake-runtime-split-v1.md) R6 — **LOCKED** until Communication Context C1–C5 |
| Delete `/leads` HTTP or `POST /leads/{id}/convert-client` | Later |
| Persist Meta answers on `sales_inquiries` columns | Field-migration slice |
| Satellite `getLead(transportLeadId)` for notes / questionnaire / RODO | Allowed (slice 3) |
| Forms `FormSubmissionEnvelope` | Phase C |

Do **not** mix Stage 5 settings or R6 table-cutover into this PR.

---

## Relation to ADR-023 / R6

| Layer | This slice |
|-------|------------|
| ADR-023 §3.1 #3 — independent operational API contracts | Close the **mixed Lead UI**; modular APIs already exist (`/sales/inquiries`, `/recruitment/applications`) |
| ADR-023 §3.1 #5 — intake stops creating universal Lead as **product** entity | Lead may remain internal transport; operators must not work it as the product card |
| R6 physical queues / RecruitmentApplication SoT | **Not this slice** — still locked |

---

## Acceptance

- Operator cannot use `/app/leads` as a dual Recruitment+Sales inbox.
- `/app/leads/:id` never stays as the work target for a SalesInquiry or Recruitment Application.
- Recruitment API does not list SalesInquiry rows; Sales API does not list recruitment rows (slice 3 + this slice).
- Lead HTTP remains compat, not product SoT.
- Docs: this brief sealed; queue points at **feat** code PR next.

---

## Likely code files (for the feat PR)

| Area | Paths |
|------|--------|
| Redirect | `hostflow-frontend/src/pages/LeadDetailPage.tsx`, `LeadsPage.tsx`, `app/routes.tsx` |
| Deep links | `shared/module_deploy_hosts.json` → `entityDeepLinks.ts` / `entity_deep_links.py` |
| Callers | reminders, Work Hub, onboarding, `ClientLeadOriginPanel`, Meta admin “open lead” |
| Tests | `backend/tests/modules/sales/test_stage3_slice4_*.py` + FE route redirect tests |

---

## DoD

- [x] Brief sealed with in/out + acceptance
- [x] Queue + roadmap + AGENTS point at this brief
- [x] Boundary vs Stage 5 / R6 / production cutover explicit
- [x] Code feat PR — Lead routes redirect to owning workspace; mixed inbox gone
- [x] Contract tests: Recruitment ⊄ SalesInquiry; deep link / route redirect
