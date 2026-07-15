# HostFlow Release & Revenue Flow Audit

**Status:** **primary operational document** for development (L3 — living; update after each scenario walkthrough)  
**Date:** 2026-07-15  
**Purpose:** Prove HostFlow can be **bought, configured, and used for money** — not «close all modules».

**Development model:** think in **scenarios and steps**, not in PRs or modules. Every PR must advance at least one step below to the next status — or it goes to backlog.

**Gate question for every task / PR:**

> *Which scenario step becomes passable end-to-end (no curl, manual URL, JSON, or DB edits) that is not passable today?*

If the answer is vague or the work does not remove a Product A/B release blocker or move money closer — **lower backlog**.

**Related canon:** [`personas.md`](personas.md), [`tenant-types.md`](tenant-types.md), [`plans-matrix.md`](plans-matrix.md), [`SSOT.md`](../SSOT.md) §2.1 / §2.16–§2.18, [`ADR-021`](architecture/ADR-021-unified-intake-resolution-model.md), [`ADR-022`](architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md), [`ADR-020`](architecture/ADR-020-sales-to-engagement-commercial-model.md), [`entity-profile-definition-registry.md`](platform/entity-profile-definition-registry.md), [`process-engine.md`](platform/process-engine.md), [`document-hub/module-scope.md`](../document-hub/module-scope.md).

**Out of scope for this audit:** global Driver/Person outside tenant, portable identity — see product-discovery gate (§7).

---

## 0. Scenario Step Registry (operational index)

Use these IDs in **every PR title/body**. One PR may cover one step or a tight chain; it must name the step(s).

**Status per step:** `not_started` | `partial` | `passable` | `blocked`

### Flow 3 — Product B: B2B targeting (P0 revenue)

| Step ID | Flow → Product → Step | Status | Next PR target |
|---------|------------------------|--------|----------------|
| **F3-B-01** | Flow 3 → Product B → Meta Lead lands in Sales inbox | **partial** | — (backend mostly done) |
| **F3-B-02** | Flow 3 → Product B → Manager selects form + sends questionnaire | **partial** | **PR B-1** (next) |
| **F3-B-03** | Flow 3 → Product B → Status «ожидаем ответ» visible to manager | **not_started** | **PR B-1** |
| **F3-B-04** | Flow 3 → Product B → Client opens link + submits answers | **partial** | **PR B-2** |
| **F3-B-05** | Flow 3 → Product B → Answers visible in Sales Workspace | **not_started** | **PR B-2** |
| **F3-B-06** | Flow 3 → Product B → Attribution visible (form, version, source, new vs attach) | **not_started** | **PR B-2** |
| **F3-B-07** | Flow 3 → Product B → Manager decision (create client / clarify / reject) | **partial** | **PR B-2** |
| **F3-B-08** | Flow 3 → Product B → Quote → Service Order | **not_started** | after B-1/B-2 walkthrough |
| **F3-B-09** | Flow 3 → Product B → Campaign activation + lead delivery | **not_started** | Flow 4 |

**PR B-1 acceptance (send only):**

- Manager received Meta Lead → clicked «Отправить анкету»
- Can **select form**
- Can **send** invite
- Sees status **«ожидаем ответ»**
- No Application Workspace UX scope in this PR

**PR B-2 acceptance (receive + decide):**

- Client submitted → answers appear in Sales Workspace
- Visible: **source, form, version**, new inquiry vs attach
- Manager can **take action** (create client, request clarification, reject)
- Touches Application Workspace UX — isolated risk zone

**Forms rule after B-1/B-2:** Forms platform evolves **only** when a step above requires it. No standalone Form Definition editor PRs until a scenario step demands them.

### Flow 1 — Product A: Recruitment (P0 revenue)

| Step ID | Flow → Product → Step | Status |
|---------|------------------------|--------|
| **F1-A-01** | Flow 1 → Product A → Signal lands in recruitment inbox | **partial** |
| **F1-A-02** | Flow 1 → Product A → Review + assign candidate | **partial** |
| **F1-A-03** | Flow 1 → Product A → Questionnaire + documents complete | **partial** |
| **F1-A-04** | Flow 1 → Product A → Pipeline decision | **partial** |
| **F1-A-05** | Flow 1 → Product A → Handoff ready | **partial** |

**Next after Product B B-1/B-2:** walk Flow 1 on staging → update statuses → pick first `not_started` / `partial` step.

### Platform foundations (only when a step above fails)

| Block | Trigger | Do not start until |
|-------|---------|-------------------|
| **Document Platform** | F1-A-03 or handoff fails on real docs | Flow 1/3 walkthrough shows doc blocker |
| **Process Platform** | Decision/clarification/SLA fails in real use | Working scenarios show automation gap |

---

## 0.1 PR template (mandatory header)

Every PR body starts with:

```markdown
## Scenario

- **Step(s):** F3-B-02, F3-B-03  (from release-revenue-flow-audit.md §0)
- **Flow:** Flow 3 → Product B
- **Before:** Manager cannot …
- **After:** Manager can … end-to-end without curl / manual URL / JSON / DB

## Not in this PR

- (explicit steps deferred)
```

If **Scenario** section is missing or step IDs do not exist in §0 — PR is out of process.

---

## 1. Sellable products (release scope)

Only two products block first revenue. HR, Fleet, and full ecosystem modules **must not** block them.

| Product | Buyer | Core value | Primary money event |
|---------|-------|------------|---------------------|
| **A — Recruitment CRM** | Agency (`business_type=agency`) or employer (`employer`) | Leads → candidates → pipeline → documents → handoff/hire | **HostFlow SaaS subscription** (Solo/Team/Business) |
| **B — Services / Targeting** | Agency or services company | B2B inquiry → client → quote → order → campaign → leads → report | **HostFlow SaaS** + **agency bills client** (Quote → SO → invoice — Contour B) |

---

## 2. Release Flow Matrix

**Status legend:** `working` | `partial` | `blocked` | `not_implemented`  
**Assessment basis:** code + tests + canon as of 2026-07-15 (not demo assumptions).

### 2.1 Flow 1 — Agency receives a candidate

| Block | What we check | Status | Evidence / notes |
|-------|---------------|--------|------------------|
| Purchase | Plan visible; trial; upgrade path | **partial** | [`plans-matrix.md`](plans-matrix.md); Stripe gaps — [`SSOT.md`](../SSOT.md) §2.1 Stripe |
| Onboarding | Tenant + own company + modules | **working** | [`tenant-types.md`](tenant-types.md); onboarding wizard |
| Intake | Meta / form / manual → correct inbox | **partial** | Meta + public intake wired (Entity Profile P3–P8); **ADR-021 Proposed**; `/app/leads` still competes with recruitment inbox per ADR-021 §1.2 |
| Work | Manager daily: review, decide, assign | **partial** | Lead detail, candidate card, pipeline; unified Application review contract **not** shipped (Phase 1B) |
| Result | Candidate on vacancy; documents; handoff | **partial** | Conversion + pipeline **working**; handoff T2 **working** per [`handoff-contract.md`](architecture/handoff-contract.md); document blockers per §4 |
| Money | SaaS subscription | **blocked** | Stripe checkout/webhooks incomplete — SSOT §2.1 |
| Errors | Duplicates, incomplete data | **partial** | Duplicate MVP per [`person-identity-layer-and-roadmap.md`](architecture/person-identity-layer-and-roadmap.md); idempotency on intake improving (P5C/P7) |
| Renewal | Why pay next month | **partial** | Plan limits enforced partially (`billing_restrictions`, quotas); full write-gate + portal **not** done |

**Persona:** P-1 administrator, P-3 recruiter (agency `Tenant.type=agency`).  
**Starting point:** Meta lead, public form (`/intake/...`), or manual lead.  
**Steps:** signal → (Application projection) → recruitment inbox → review → Candidate → vacancy pipeline → documents → handoff / hire.  
**Final value:** Hired candidate or client-ready handoff; measurable conversion.  
**Money event:** Monthly SaaS (Contour A).  
**Release priority:** **P0** (Product A).  
**Top blockers:** ADR-021 Accepted + Phase 1A/1B; Intake Platform coherence (§5.1); Document requirements in pipeline; Stripe (Contour A).

---

### 2.2 Flow 2 — Employer hires directly

| Block | Status | Notes |
|-------|--------|-------|
| Purchase / Onboarding | **partial** / **working** | `business_type=employer` → `Tenant.type=company`; modules: candidates+vacancies, no leads/services/client_portal — [`tenant-types.md`](tenant-types.md) |
| Intake | **partial** | Same intake stack; employer may use vacancies + forms without agency client handoff |
| Work | **partial** | Company scope + roles (`client_processor` N/A); recruiter roles in own tenant |
| Result | **partial** | `ready_for_hr` → WorkforceEmployee via handoff; idempotent per ADR-002 / handoff-contract |
| Money | **blocked** | Same Stripe gap |
| Errors | **partial** | Duplicate + company scope |
| Renewal | **partial** | Same as Flow 1 |

**Difference from Flow 1:** No agency client handoff; single-company ownership.  
**Release priority:** **P1** (subset of Product A; same intake/doc/process blockers).  
**Owner:** Recruitment + platform intake.

---

### 2.3 Flow 3 — B2B client buys targeting

| Block | Status | Notes |
|-------|--------|-------|
| Purchase | **partial** | Services module in ADR-004; SaaS plan must include `services` / leads |
| Onboarding | **working** | `business_type=services` or agency with services module |
| Intake | **partial** | B2B Meta / form → `route_intent=sales_inquiry`; tests: `test_sales_targeted_advertising_intake.py`, `test_intake_forms_settings_p8.py`; questionnaire invite: `lead_questionnaire_invite.py` |
| Work | **partial** | Sales inquiry UI; Entity Profile `service_sales.targeted_advertising`; presentation editor WIP (`LeadFormsSettingsPage`, `IntakeFormPresentationEditor`) |
| Result | **partial** | **ClientAccount** Stage 1A implemented ([`stage-1a-client-account-implementation-contract.md`](tasks/stage-1a-client-account-implementation-contract.md)); **Quote / SO / activation — not_implemented** (no `quotes` in backend) |
| Money | **not_implemented** | Contour B: Quote → SO → Billing Event → Invoice; design on branch `design/stage-1b-quote-foundation` |
| Errors | **partial** | Intake routing tests exist; commercial path untested end-to-end |
| Renewal | **partial** | Recurring service fee model undefined in runtime |

**Persona:** P-1 administrator (agency/services).  
**Starting point:** Meta B2B lead or B2B intake form.  
**Steps:** signal → Sales inbox → questionnaire → ClientAccount → Quote → Service Order → payment → campaign onboarding.  
**Final value:** Running campaign delivering leads with reporting.  
**Money events:** SaaS (A) + agency→client commercial (B).  
**Release priority:** **P0** (Product B).  
**Top blockers:** Quote Foundation runtime; **F3-B-02..B-07** questionnaire send/receive/decide UX; campaign↔SO linkage (Flow 4).

**Scenario steps (detail):** see §0 — `F3-B-01`..`F3-B-09`.

---

### 2.4 Flow 4 — Client receives leads from running ads

| Block | Status | Notes |
|-------|--------|-------|
| Intake routing | **partial** | `route_intent` distinguishes sales vs recruitment; tests for targeted advertising intake |
| Campaign linkage | **blocked** / **partial** | Need E2E proof: campaign → SO → Meta lead attribution → correct owner company |
| Work | **partial** | Lead lands in correct module inbox |
| Result | **partial** | CPL / reporting — analytics depends on attribution chain |
| Money | **not_implemented** | Ad spend vs agency fee separation (Contour D) — not in runtime |

**Release priority:** **P0** (completes Product B).  
**Depends on:** Flow 3 SO + campaign model; Intake routing (§5.1).

---

### 2.5 Flow 5 — HR creates employee manually

| Block | Status | Notes |
|-------|--------|-------|
| All blocks | **partial** / **working** | [`ADR-001`](../hr/ADR-001-workforce-employee-vs-app-user.md): WorkforceEmployee without Candidate; no intake decision required |
| Money | **n/a** | Not a first-release product unless HR sold separately |

**Release priority:** **P3** — candidate for future HR product; **not a blocker** for Products A/B.

---

### 2.6 Flow 6 — HostFlow subscription (Contour A)

| Block | Status | Notes |
|-------|--------|-------|
| Plan / trial / seats | **partial** | [`plans-matrix.md`](plans-matrix.md) + enforcement services exist; gaps in SSOT §2.1 |
| Stripe checkout | **partial** | Some checkout paths; full §2.18 spec **open** |
| Webhooks | **partial** | `StripeWebhookEventLog`; not all SKU/subscription items |
| Write enforcement | **partial** | `billing_restrictions` — leads + comms; not all write APIs |
| Customer portal | **not_implemented** | SSOT §2.17 |
| Grace / past_due | **partial** | Spec: 3d grace; implementation incomplete |

**Release priority:** **P0** for monetizing Product A; **P1** for Product B (agency already needs SaaS).  
**Owner:** Billing / platform.

---

### 2.7 Flow 7 — Recruitment fee (agency → client)

| Variant | Status | Notes |
|---------|--------|-------|
| Fixed / success / per-candidate / retainer | **not_implemented** | No canonical runtime in ADR-020 scope; Finance can invoice manually **partial** |

**Release priority:** **P2** — define which variants are **in** or **out** of v1 before building.

---

### 2.8 Flow 8 — Targeting fee (Contour B + D)

| Block | Status | Notes |
|-------|--------|-------|
| Quote → SO → Billing Event | **not_implemented** | Design-first on `design/stage-1b-quote-foundation` |
| Ad spend vs management fee | **not_implemented** | Must not mix in one line item — product rule |

**Release priority:** **P0** for Product B revenue (agency side).

---

## 3. Money Flow Matrix

| ID | Contour | Who pays | To whom | For what | Trigger object | Invoice creator | After payment | Non-payment |
|----|---------|----------|---------|----------|----------------|-----------------|---------------|-------------|
| **A** | HostFlow SaaS | Tenant admin | HostFlow | Plan + seats + modules + usage | `TenantLicense` / Stripe Subscription | Stripe → Finance mirror | Full write access | `billing_restrictions`, trial end, past_due grace (spec 3d) |
| **B** | Agency → client service | Client (B2B) | Agency tenant | Targeting / recruiting service | Quote → Service Order → Billing Event | Finance module (tenant) | SO activation / delivery | SO blocked / dunning (TBD) |
| **C** | Recruitment fee | Client | Agency | Placement / retainer | TBD contract object | Finance | Handoff complete | TBD |
| **D** | Ad spend | Client | Meta (external) | Ads | Campaign / budget line | **Not** HostFlow invoice | Campaign runs | Pause campaign |
| **E** | Add-ons / packs | Tenant | HostFlow | Over-cap usage | Pack SKU | Stripe Checkout | Limit raised | 402 on operation |

**First-release minimum:** Contour **A** (sell CRM) + Contour **B** skeleton (Quote→SO→invoice) for targeting agencies.

---

## 4. Three platform foundations (why flows stall)

These are **not** three independent bugs — they block **all** full user flows.

### 4.1 Intake Platform

**Question answered:** How data enters HostFlow and becomes an owned operational case.

| Capability | Canon | Implementation | Gap |
|------------|-------|----------------|-----|
| Sources | ADR-007, ADR-013, ADR-021 | Meta, public intake, forms settings, import | Telegram/WhatsApp/API contracts incomplete |
| Entity Profile + Presentation | entity-profile-definition-registry **P8 complete** | Intake Source CRUD, presentation write API, public render P7 | Questionnaire UI polish; B2B/B2C/candidate **three profiles** need one operator story |
| Submit → outcome | Decision Layer + Outcome Executor P5B | `route_intent`, executor targets | **ADR-021 not Accepted**; Application/Submission contract not in API |
| Inbox ownership | ADR-021 §6 | Recruitment + Sales facades partial | `/app/leads` legacy; dual inbox risk |
| Auto-policy | ADR-021 §10 | Partial | Granular policies not product-complete |

**Scope rule:** ADR-021 applies to **inbound signals needing review/decision** only — **not** HR manual create, Fleet create, direct entity CRUD.

**Blocks:** Flow 1, 2, 3, 4.

---

### 4.2 Document Platform

**Question answered:** What the system knows about proof and files — not «upload a file».

| Concept | Canon | Implementation | Gap |
|---------|-------|----------------|-----|
| Document instance | ADR-009 | Document model + links | Hub evolution ongoing |
| Requirement / Evidence | ADR-016 | requirement-evidence-model-p0 | Recruitment readiness + handoff fulfillments **partial** |
| Type / metadata / validity | document-type-model-standard | Partial catalog | Operator clarity in UI |
| Cross-module transfer | handoff-contract §B.4 | Links, not copy — **working** for HR handoff | Fleet / portal sharing rules incomplete |
| Sharing / ownership | ADR-009, domain map | `owner_company_id` | Portable / consent model **deferred** (§7) |

**Blocks:** Flow 1 (blockers on candidate), Flow 2, handoff quality.

---

### 4.3 Process Platform

**Question answered:** How work moves — stages, guards, handoff, automation.

| Capability | Canon | Implementation | Gap |
|------------|-------|----------------|-----|
| Stages / transitions | process-engine **P0–P6 complete** | Recruitment profile, funnel mapping, handoff evaluator | HR/Fleet/Services profiles thin |
| Handoff | handoff-contract, ADR-002 | CandidateHandoff → Workforce **working** | Client portal handoff UX partial |
| Automations | ADR-019 | Rules engine **partial** | Entitlement gates vs product expectations |
| SLA / reminders | ADR-012 | Activity layer **working** | Not unified with intake review SLA |
| Returns / clarifications | ADR-021 §5.2 Phase 2 | **not_implemented** | `reviewed_data` / new Submission |

**Blocks:** Flow 1 handoff polish, Flow 3 activation readiness (post-SO).

---

## 5. Release Blockers (explicit list)

Items that **objectively** prevent selling Products A or B. Review weekly: still blocking?

| # | Blocker | Blocks | Status | Owner |
|---|---------|--------|--------|-------|
| R1 | ADR-021 → Accepted | Unified intake contract | **open** | Architecture |
| R2 | Phase 1A — inbox ownership, `/app/leads` nav freeze | Flow 1/2/3 inbox trust | **open** | Product + frontend |
| R3 | Phase 1B — unified review (Sales + Recruitment only) | Manager daily work | **open** | Product + frontend |
| R4 | Intake questionnaires — B2B/B2C/candidate operator story | Flow 3, Flow 1 forms | **partial** | Forms platform |
| R5 | Document requirements in recruitment pipeline | Flow 1 result quality | **partial** | Document Hub |
| R6 | Quote Foundation design → Approved | Flow 3/8 design gate | **open** (branch `design/stage-1b-quote-foundation`) | Sales/Services |
| R7 | Quote + Service Order runtime | Product B | **not_implemented** | Sales/Services backend |
| R8 | Campaign ↔ SO ↔ lead attribution | Product B delivery | **partial** | Services + integrations |
| R9 | Stripe subscription E2E (§2.18) | Product A money | **open** | Billing |
| R10 | Trial + write enforcement all APIs | SaaS trust | **partial** | Billing |
| R11 | CI / integration gates (Stage 1A, paths:qa, P8 tests green) | Ship confidence | **verify** | Engineering |

**Not release blockers (defer):** HR manual product, Fleet, Driver identity, global Person, Client portal polish (unless sold in v1 plan), full automation designer.

---

## 6. Recommended work order

**Scenario-first — not module-first.** Order follows §0 step IDs.

```text
NOW (architecture closing):
  - Merge ADR-022 backend foundation (enables F3-B-04 data path; not a scenario step by itself)
  - ADR-022 → Accepted

NEXT (Product B — nearest money):
  PR B-1 → F3-B-02, F3-B-03  (send questionnaire + awaiting status)
  PR B-2 → F3-B-04..F3-B-07  (answers in Sales + attribution + decision)
  Re-walk F3-B-01..B-07 on staging; update §0 statuses

THEN (Product A):
  Walk Flow 1 → pick F1-A-* step → one PR per passable increment

ONLY WHEN WALKTHROUGH FAILS:
  Document Platform (F1-A-03 blockers)
  Process Platform (automation gaps from real use)

COMMERCIAL (after F3-B-07 passable):
  Quote Foundation → F3-B-08 → F3-B-09 / Flow 4

MONETIZATION:
  Stripe E2E Contour A (Flow 6) — parallel if blocking Product A sale
```

**Do not:** standalone Forms/ADR editor PRs, Process Platform design, Document Platform refactors — unless a §0 step is blocked.

**Shortest path to money:**

1. **Product B** — F3-B-02..B-07 passable (questionnaire → decision) → then Quote/SO  
2. **Product A** — F1-A-01..F5 passable + Contour A Stripe  

---

## 7. Driver / portable identity — discovery gate

**Do not** add to Domain Map or implementation backlog until product doc answers:

| Topic | Decision needed |
|-------|-----------------|
| Profile creator | Driver / tenant / import / platform |
| Owner | Driver / platform / company |
| `tenant_id` | Nullable / platform tenant / separate realm |
| Documents | Personal / company-owned / shared links |
| Recruitment | One vs many Applications |
| Employers | One / many / historical |
| Candidate vs Employee vs Driver | Projection vs aggregates |
| Access | Consent, expiry, revocation |
| Portability | Cross-company / cross-tenant |
| Portal auth | Magic link / account / external user |
| Monetization | Who pays for profile storage |

**User scenarios to walk first (10):** self-create profile; apply to vacancy; share docs without recruitment; company manual create; candidate→employee; job change; revoke access; see employer process status; multi-company; tenant churn.

---

## 8. How to use this document

1. **Before starting work:** find step ID in §0; confirm PR advances it to `passable`.  
2. **Opening a PR:** use §0.1 template; link step IDs in title or body.  
3. **After each walkthrough:** update step status in §0 and flow block in §2.  
4. **Weekly:** review §5 — demote blockers that no longer block A/B.  
5. **Forms / Intake / ADR work:** only when a named step requires it.  
6. **Do not** expand ADR-021 scope based on §7.

**This document is the primary operational backlog filter.** Technical specs and ADRs implement steps listed here — they do not drive priority by themselves.

**Inbound:** referenced from [`SSOT.md`](../SSOT.md) §2 (release audit).

---

## 9. Changelog

| Date | Change |
|------|--------|
| 2026-07-15 | Scenario Step Registry §0; PR template §0.1; Product B split PR B-1/B-2; scenario-first work order |
| 2026-07-15 | Initial audit — Products A/B, 8 flows, money matrix, 3 platforms, release blockers |
