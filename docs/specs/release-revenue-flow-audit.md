# HostFlow Release & Revenue Flow Audit

**Status:** **primary operational document** for development (L3 — living; update after each scenario walkthrough)  
**Date:** 2026-07-15  
**Purpose:** Prove HostFlow can be **bought, configured, and used for money** — not «close all modules».

**Development model (official):** three levels — **Foundation → Scenario Step → Revenue Flow**. Product progress = passable Scenario Steps + completed Revenue Flows. **Never** Foundation merges alone.

**Gate questions for every task / PR:**

1. **Scenario Step PR:** Which step becomes **passable** without workarounds? **What can the operator do today that they could not yesterday?**
2. **Foundation PR:** Which step(s) does this **unblock**? If none — backlog.
3. **Any PR:** Operator gain = «nothing» → Foundation only; **does not count as product progress**.

If vague or does not move Product A/B toward money — **lower backlog**.

**Related canon:** [`personas.md`](personas.md), [`tenant-types.md`](tenant-types.md), [`plans-matrix.md`](plans-matrix.md), [`SSOT.md`](../SSOT.md) §2.1 / §2.16–§2.18, [`ADR-021`](architecture/ADR-021-unified-intake-resolution-model.md), [`ADR-022`](architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md), [`ADR-020`](architecture/ADR-020-sales-to-engagement-commercial-model.md), [`entity-profile-definition-registry.md`](platform/entity-profile-definition-registry.md), [`process-engine.md`](platform/process-engine.md), [`document-hub/module-scope.md`](../document-hub/module-scope.md).

**Agent rules:** [`.cursor/rules/scenario-first-development.mdc`](../../.cursor/rules/scenario-first-development.mdc) — enforce scenario-first, reuse-first, no architecture for its own sake.

**Out of scope for this audit:** global Driver/Person outside tenant, portable identity — see product-discovery gate (§7).

---

## 0. Development model (official)

Three levels. Every piece of work must declare which level it serves.

### Level 1 — Foundation

Architecture, ADR, backend infrastructure, platform modules. **Does not sell by itself.** The client never sees it.

Examples: ADR-022, Submission Policy resolver, Match Resolver, Entity Profile gate, document metadata schema.

**Rule:** A Foundation PR is **never** product completion. It is **unblocking** one or more Scenario Steps. Progress is recorded only when a step becomes passable.

**Bad PR title (Foundation disguised as product):** «Added Form Definition Policy Resolver.»  
**Operator gain:** nothing → **Foundation only.**

### Level 2 — Scenario Step

One concrete user action an operator or client can perform and **demonstrate**. This is where product value appears.

Each step MUST answer:

> **What can the operator (or client) do today that they could not do yesterday?**

Example **F3-B-02:**

| | |
|---|---|
| **Yesterday** | Cannot send a questionnaire from the lead. |
| **Today** | Can select a form, send a link, see status «Waiting for response». |

That is a **good Scenario Step PR.**

Example **F3-B-04:**

| | |
|---|---|
| **Yesterday** | Response is lost or creates duplicate inquiry. |
| **Today** | Response appears on the existing application automatically. |

### Level 3 — Revenue Flow

A **complete money cycle** — passable end-to-end by a paying customer without workarounds.

**Flow 3 (Product B) — target cycle:**

```text
Meta Lead
    ↓
Manager sends questionnaire          (F3-B-02..03)
    ↓
Client responds                      (F3-B-04)
    ↓
Manager sees answers + decides       (F3-B-05..07)
    ↓
Creates client
    ↓
Sends Quote                          (F3-B-08)
    ↓
Receives payment
    ↓
Launches campaign                    (F3-B-09 / Flow 4)
    ↓
Receives new leads
    ↓
Issues next invoice
```

**Product progress metric:** count of **`passable` Scenario Steps** + count of **Revenue Flows walked without workarounds** on staging/production-like env.

Foundation merges **do not** increment this metric.

### Proven blocker rule (Foundation gate)

Before **any** Foundation PR, answer in this direction only:

```text
Revenue Flow target
      ↓
Step X is not passable (walkthrough proof)
      ↓
Root cause identified
      ↓
Can reuse existing code? → extend, do not create new
      ↓
Reuse impossible or worse → Foundation PR
      ↓
Scenario Step becomes passable
      ↓
Next Step
```

**Required statement (Foundation PR):**

> **Step `F3-B-04` cannot pass because** … **Therefore Foundation:** Match Resolver + Submission Policy.

**Forbidden direction:** «Foundation X will be useful someday» without naming a **currently blocked** step ID.

PRs that fail this filter — **reject / backlog**.

### Foundation Debt

Foundation creates **debt**: no operator gain until paid down by Scenario Step PR(s).

| Rule | Value |
|------|-------|
| Paydown deadline | **1–2 PRs** after Foundation merge (next PR must be Scenario Step unless walkthrough proves new blocker) |
| Max consecutive Foundation PRs | **2** — third in a row = process violation; stop and ship Scenario Step |
| Debt register | §0.3 below — updated on every Foundation merge |

**Example chain (current):**

| PR | Level | Pays down | Next required |
|----|-------|-----------|---------------|
| **#22** ADR-022 backend | Foundation | — | **B-1** (mandatory next) |
| **B-1** | Scenario Step | #22 (partial — F3-B-02/03) | B-2 |
| **B-2** | Scenario Step | #22 (full — F3-B-04..07) | next blocked step |

Three Foundation PRs after #22 without B-1/B-2 = **infrastructure drift** — escalate.

---

## 0.1 Scenario Step Registry

Use step IDs in **every PR**. **Operator gain** is the most important column — if empty, the work is Foundation.

**Step status:** `not_started` | `partial` | `passable` | `blocked`  
**Foundation column:** dependency + `unblocked` (ready to implement step) or `pending`

### Flow 3 — Product B: B2B targeting (P0)

| Step | User action | Foundation dependency | Operator gain (yesterday → today) | Status |
|------|-------------|----------------------|-----------------------------------|--------|
| **F3-B-01** | Meta Lead in Sales inbox | Intake routing, Entity Profile | **Was:** lead lost or wrong inbox → **Now:** lead in Sales (partial — walkthrough needed) | **partial** |
| **F3-B-02** | Send questionnaire | ADR-022 backend (**unblocked**) | **Was:** cannot send questionnaire → **Now:** select form + send link to client | **partial** |
| **F3-B-03** | Waiting for response | Submission + invite transport (**unblocked**) | **Was:** no visibility → **Now:** status «Waiting for response» on lead | **not_started** |
| **F3-B-04** | Client submits answers | Match resolver + attach (**unblocked**) | **Was:** response lost / duplicate inquiry → **Now:** answers land on correct application | **partial** |
| **F3-B-05** | See answers in Sales | Application Workspace UX (**pending**) | **Was:** answers in JSON/DB only → **Now:** filled questionnaire visible in Sales | **not_started** |
| **F3-B-06** | See attribution | Submission snapshot (**unblocked**) | **Was:** unknown source/form → **Now:** form, version, source, new vs attach visible | **not_started** |
| **F3-B-07** | Take decision | ClientAccount + workspace actions | **Was:** no clear next action → **Now:** create client / clarify / reject | **partial** |
| **F3-B-08** | Quote → Service Order | Quote Foundation (**pending**) | **Was:** commercial path manual → **Now:** quote sent from inquiry | **not_started** |
| **F3-B-09** | Campaign + delivery | SO + campaign linkage | **Was:** no delivery loop → **Now:** campaign runs, leads attributed | **not_started** |

**Next Scenario Step PRs (not Foundation):**

| PR | Steps | Operator gain summary |
|----|-------|----------------------|
| **B-1** | F3-B-02, F3-B-03 | Manager can send questionnaire and see waiting status |
| **B-2** | F3-B-04..F3-B-07 | Manager sees answers, attribution, and can decide |

**Current Foundation PR (in review):** ADR-022 backend — unblocks F3-B-04 data path; **does not** pass any step until B-1/B-2.

**Forms rule:** no standalone Forms PRs unless a row above is blocked.

### §0.3 Foundation Debt register

Living ledger. Update on every Foundation merge.

| PR / change | Blocked step(s) | Proven cause | Foundation delivered | Unblocks | Paydown by PR | Debt status |
|-------------|-----------------|--------------|----------------------|----------|---------------|-------------|
| **#22** ADR-022 backend | F3-B-04, F3-B-06 | Response attaches to wrong/missing application without policy+match+submission snapshot | `intake_platform`, Submission Policy, Match Resolver | F3-B-04, F3-B-06 data path | **B-1** (next), **B-2** (max) | **open** |

**Debt status:** `open` | `partial` | **paid** (all listed steps passable)

---

### §0.4 Product B walkthrough gaps (G-B-*)

Walkthrough-specific gaps discovered during §20-style staging verification. Each gap → **one PR** → full walkthrough re-run. Do **not** paper over with frontend API suppression.

| Gap | Step(s) | Summary | Status |
|-----|---------|---------|--------|
| G-B-01 | F3-B-01 | Channel id meta vs `intake_routing_v1` | **closed** |
| G-B-02 | F3-B-01 | Channel inbox filter | **closed** |
| G-B-03 | F3-B-05 / A12 | Structured answers UI on inquiry work page | **closed** (#24) |
| G-B-04 | F3-B-06 / A13 | Submission attribution panel | **closed** (#25) |
| **G-B-05** | Form editor / provisioning | **Targeted-advertising Entity Profile registry on services tenants** | **open** |

#### G-B-05 — targeted-advertising Entity Profile available for every services tenant

**Symptom (staging, 2026-07-15):** Manager opens form editor from inquiry attribution link and clicks **Load platform preset**. Console shows:

```text
GET …/settings/intake-forms/entity-profiles/service_sales.targeted_advertising/fields → 404
GET …/settings/intake-forms/entity-profiles/service_sales.targeted_advertising/presentation-preset → 404
```

**Not a G-B-04 regression:** form title and attribution work via `listLeadForms` fallback; answers panel tolerates missing registry via submission snapshot. **Form constructor** (`IntakeFormPresentationEditor`) requires registry-backed catalog + preset.

**Observed state on affected tenant:**

| Artifact | Present? |
|----------|------------|
| `TenantLeadForm` (e.g. B1 Acceptance Form) | yes |
| Submission snapshot (`submissions_v1`, answers) | yes |
| `EpEntityProfile` `service_sales.targeted_advertising` for tenant | **no** → `resolution_source: not_found` |
| Presentation preset in registry | **no** |
| Field catalog API | **404** |

**Root cause (investigation):**

1. **Deployment drift — auto-seed not on Product B integration line.** Full provisioning lives on branch `feat/targeted-advertising-auto-seed` (commit `30edbcc2`), **not merged** into `feat/adr022-intake-policy-phase1-backend`. Integration line only has partial `ensure_tenant_targeted_advertising_intake_form` (creates `TenantLeadForm` + `IntakeSourceProfile` bindings) — it does **not** register Entity Profile + presentation into `EpEntityProfile` / `EpIntakePresentation` for the tenant.

2. **Partial lazy seed on questionnaire list.** `list_questionnaire_forms_for_targeted_advertising` calls `ensure_tenant_targeted_advertising_intake_form` but that path never invokes `EntityProfileRegistry.register_profile*`.

3. **Legacy / manually created forms.** Tenants with constructor-created forms (e.g. inactive B1 Acceptance Form) have form rows without registry rows — expected until recovery runs.

**Implementation path (reuse — do not invent new mechanism):**

| Asset | Location |
|-------|----------|
| `provision_targeted_advertising_capability` | `backend/app/entity_profile/provision_targeted_advertising.py` on `feat/targeted-advertising-auto-seed` |
| `recover_targeted_advertising_capability` | same module (lazy ensure / repair) |
| Repair CLI | `backend/scripts/repair_targeted_advertising_capability.py` — `python …/repair_targeted_advertising_capability.py <tenant_id>` |
| Tenant-create hook | `provision_targeted_advertising_on_tenant_create` in same module |
| Tests | `backend/tests/entity_profile/test_targeted_advertising_auto_seed.py` on auto-seed branch |

**PR scope:** merge or cherry-pick auto-seed onto integration line; run repair on staging tenant; verify — **not** a frontend suppression PR.

**Acceptance**

1. New **services** tenant (onboarding) receives automatically: Entity Profile `service_sales.targeted_advertising`, presentation preset, field catalog, canonical targeted-advertising form (create-only).
2. Existing tenant restored by **`repair_targeted_advertising_capability.py <tenant_id>`** without duplicating user-owned forms.
3. `GET …/entity-profiles/service_sales.targeted_advertising/fields` → **200**.
4. `GET …/entity-profiles/service_sales.targeted_advertising/presentation-preset` → **200**.
5. **Load platform preset** in form editor UI succeeds (fields populated, success toast).
6. Re-run provisioning/repair is **idempotent**: no duplicate slug forms, no overwrite of tenant-customized form title/presentation.
7. After repair + page refresh: **no** 404 on the two endpoints above (browser extension noise excluded — verify incognito).

**Walkthrough verify:** open inquiry → attribution form link → form editor → Load platform preset → save optional smoke.

---

| Step | User action | Foundation dependency | Operator gain (yesterday → today) | Status |
|------|-------------|----------------------|-----------------------------------|--------|
| **F1-A-01** | Signal in recruitment inbox | Intake + ADR-021 | Lead/candidate in correct inbox | **partial** |
| **F1-A-02** | Review + assign | Application review UX | Manager can assign and move forward | **partial** |
| **F1-A-03** | Questionnaire + documents | Document requirements | Candidate completes proof; manager sees readiness | **partial** |
| **F1-A-04** | Pipeline decision | Process engine | Hire / reject / next stage | **partial** |
| **F1-A-05** | Handoff | Handoff contract | HR receives employee package | **partial** |

**Start Flow 1 walkthrough after F3-B-02..07 passable.**

### Platform blocks (Foundation — only when a step fails walkthrough)

| Block | Unblocks steps | Start only when |
|-------|----------------|-----------------|
| Document Platform | F1-A-03, handoff quality | Walkthrough fails on real documents |
| Process Platform | F1-A-04, clarifications, SLA | Walkthrough fails on transitions/automation |

---

## 0.2 PR template (mandatory)

Classify every PR as **Foundation** or **Scenario Step**. Scenario Step PRs must fill **Operator gain**.

```markdown
## PR level

- [ ] **Scenario Step** — makes step(s) passable: F3-B-02
- [ ] **Foundation** — unblocks step(s): F3-B-04 (no operator gain in this PR)

## Operator gain (required for Scenario Step PRs)

**Yesterday:** Manager cannot send questionnaire from lead detail.
**Today:** Manager can select form, send link, see «Waiting for response».

## Scenario

- **Step(s):** F3-B-02, F3-B-03
- **Revenue Flow:** Flow 3 → Product B
- **Demonstration:** (how to show in staging in ≤5 min)

## Not in this PR

- (explicit steps deferred)

## Foundation note (required for Foundation PRs)

- **Blocked step(s):** F3-B-04 — cannot pass because …
- **Proven cause:** (from walkthrough, not speculation)
- **Reuse attempted:** (what existing code was considered)
- **Foundation delivers:** Match Resolver + …
- **Unblocks:** F3-B-04, F3-B-06
- **Foundation Debt:** paydown due in next **1–2 PRs** (name them: B-1, B-2)
- **Operator gain in this PR:** none
```

PRs without **Operator gain** (Scenario Step) or **Blocked step + Proven cause + Unblocks + Paydown** (Foundation) — **out of process**.

**Anti-patterns (auto-reject):**

- Foundation PR: «will be useful later» without blocked step ID
- Foundation PR: no paydown plan
- **3+ consecutive Foundation PRs** without Scenario Step paydown

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

1. **Classify work:** Foundation (unblocks) vs Scenario Step (passable) vs Revenue Flow (full cycle).  
2. **Before starting:** pick step ID in §0.1; write Operator gain (yesterday → today).  
3. **Opening a PR:** use §0.2 template; Foundation PRs must list **Unblocks**; Scenario Step PRs must list **Operator gain**.  
4. **Measuring progress:** count `passable` steps + completed Revenue Flow walkthroughs — **not** Foundation merges.  
5. **After walkthrough:** update Operator gain column and status in §0.1.  
6. **Weekly:** review §5 blockers.  
7. **Forms / ADR / platform:** only when a step row is blocked.

**Hard rule:** No Foundation PR counts as product shipment. Product moves only when an operator can do something new without workarounds.

**Inbound:** [`SSOT.md`](../SSOT.md) §2.

---

## 9. Changelog

| Date | Change |
|------|--------|
| 2026-07-15 | **G-B-05** opened — staging Entity Profile registry drift; auto-seed on `feat/targeted-advertising-auto-seed` not merged to integration line (§0.4) |
| 2026-07-15 | Proven blocker rule + Foundation Debt register (§0.3); paydown within 1–2 PRs; max 2 consecutive Foundation |
| 2026-07-15 | Agent rule `.cursor/rules/scenario-first-development.mdc` — proven blocker only, no "just in case" |
| 2026-07-15 | Three-level model (Foundation / Scenario Step / Revenue Flow); Operator gain column; Foundation ≠ product progress rule |
| 2026-07-15 | Scenario Step Registry §0; PR template §0.1; Product B split PR B-1/B-2; scenario-first work order |
| 2026-07-15 | Initial audit — Products A/B, 8 flows, money matrix, 3 platforms, release blockers |
