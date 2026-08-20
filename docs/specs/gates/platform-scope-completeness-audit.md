# Platform Scope Completeness Audit

**Status:** **COMPLETE** (docs — this record) · **STOP** on Entity Workspace D vs original goal  
**Date:** 2026-08-20  
**Trusted base:** `integration/release-product-a-b` @ `1c0dac88` (E2 brief [#271](https://github.com/igortatarynovich/HostFlow/pull/271); E2 feat not landed)  
**Parents:** [Goal Completion Gate](goal-completion-gate.md) · [D1](../tasks/entity-workspace-d1-contract-seal.md)…[D9](../tasks/entity-workspace-d9-services-order-cutover.md) · [Epic C Complete Gate](epic-c-complete-gate.md) · [A2](platform-governance-review-a2.md) · [Forms C6](../tasks/forms-platform-c6-optimization.md) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md)  
**Corrective Product Track:** [Entity Platform Completion](../tasks/entity-platform-completion.md)

> This is **not** a development sprint.  
> It applies the [Goal Completion Gate](goal-completion-gate.md) to already-closed platform blocks.  
> Question: *what residual capability should this block have given the system, and can the next layer work without local workarounds?*  
> Not: *did the approved brief ship?*

---

## Method

Each row uses G1–G5. Three failure classes — do not collapse them:

| Class | Meaning | Typical close-out |
|-------|---------|-------------------|
| **Goal substitution** | Original problem replaced by a weaker brief; later slices tested against the substitute | Formal COMPLETE, wrong goal |
| **Documented residual** | Original goal still incomplete; leftovers named; next layer allowed only outside them | `PASS_WITH_CONSTRAINTS` |
| **Honest deferral** | Never claimed; named later slice | Locked / out of slice |

D is **goal substitution**. Epic C / A2 are **documented residual**. R6 / Forms P3–P5 / C2.4 are **honest deferral**.

---

## Results (summary)

| Block | Brief-complete? | Goal-complete? | Class | Next layer without new primitive? |
|-------|-----------------|----------------|-------|-----------------------------------|
| **Platform Extraction / PX chrome** | Chrome path reserved; D1 treats PX ≠ Universal | **No** for “any new list/workspace/analytics screen from kit including inner blocks” | Honest deferral **plus** later substitution at D | No — Application Workspace still module `ContextRail` composition |
| **Entity Workspace D1–D9** | Yes (named D gates) | **No** vs Entity Shell + contributions | **Goal substitution** | **No** — Notes/Consent/rail blocks still module-owned |
| **Forms C1–C6** | Yes — Foundation ✅ serve→execute | **Partial** vs “any module, no own form runtime” | Documented residual + honest deferral | Not yet — `TenantLeadForm` bridge; `SalesInquiryQuestionnaireSection` still `leadId` glue; P3–P5 locked |
| **Communication / Epic C** | `PASS_WITH_CONSTRAINTS` | **Partial** | Documented residual | New Intent paths yes; legacy SMTP allowlist (R2) and Catalog naming (A2-F1) remain |
| **Acquisition / Stage 3–4** | Slice 4 UI separation ✅ | **Partial** vs physical Application SoT | Honest deferral (R6) | UI inboxes separated; Lead remains transport; `/api/v1/leads` compat |
| **RBAC / ADR-036** | Canon accepted; enum remapped | **Partial** | Honest deferral (matrix keys / presets) | New job-title **role** forbidden; leftover matrix/UI aliases remain |
| **Analytics** | Acquisition Stage 6 ✅ | **No** as **platform** analytics | Honest deferral / never claimed as platform kit | New HR/Fleet/Recruitment dashboard can still invent KPI/chart families |
| **Actions / States / Relationships** | Vocabulary / EntityModel fragments | **No** runtime path when needed | Honest deferral | No cross-module action registry (ADR-019 still names the hole) |

**Disposition:** do **not** start Documents E2 feat, Billing, or AI while Entity D is goal-incomplete. Other rows do **not** each need an emergency epic; they need G5 leftovers honored and this gate on their next close-out.

---

## 1. Platform Extraction / PX chrome

| Gate | Answer |
|------|--------|
| **G1** | Stop Stage 3 from inventing a fifth card shell. Product pages reuse kit chrome (header / tabs / summary / action bar / rail / content). |
| **G2** | Forbidden: a fifth Entity/Application card shell beside kit `EntityWorkspace`. |
| **G3** | A **new list** can reuse DataTable/ListWorkspace **if authors choose the kit**. A **new entity screen with inner capabilities** cannot — PX explicitly is **not** Universal Entity Workspace ([D1](../tasks/entity-workspace-d1-contract-seal.md)). |
| **G4** | Kit chrome path exists (`components/ui/EntityWorkspace` / Shell adapter). Proof is chrome reuse, not full screen assembly. |
| **G5** | Candidate/HR/Vacancy/Recruitment workspaces stay module-owned by D1 rule. Application Workspace still composes `ContextRail` + module `contextSlots`. |

**Outcome:** not D-class substitution. PX did what it claimed (chrome). The error is using PX-complete as if Entity Platform were complete.

---

## 2. Entity Workspace D1–D9 — STOP vs original goal

| Gate | Answer |
|------|--------|
| **G1 Original** | Entity Shell = one envelope for the object **plus all common information and functions**. Default and paid modules add blocks through **one** composition/contribution contract. No module invents its own rail, comments, consent, actions, widgets, or navigation. The same entity looks and behaves the same regardless of which modules are on. |
| **G1 Substituted (D1–D2)** | Shell = page geometry. D2 = platform **surfaces** (`overview` / `timeline` / `communication` / `forms` / `documents` / `context-rail`). Inner functions stay module-owned. D3–D9 = named consumer cutovers onto that catalog. |
| **G2 After D (actual)** | Forbidden: fifth shell; new D2 slot kinds without amending D2; enabling `documents` before Phase E. **Not** forbidden: `SalesInquiryCallNotesSection`, `SalesInquiryRodoSection`, `CandidateRodoSection`, Recruitment-local comments/RODO, stuffing into `overview`/`summary`. |
| **G3** | Recruitment Application **cannot** be assembled without local rail-blocks / notes / consent. Sales Inquiry “cutover” still supplies module renderers into CompositionHost. |
| **G4** | D3–D9 proof is `EntityWorkspaceCompositionHost` + slot allowlists + `data-entity-workspace-slot`. That proves **surface binding**, not common capabilities. Shell `comments` nav maps to `[]` and never enables ([`projectEntityWorkspaceView.ts`](../../../hostflow-frontend/src/platform/entity-workspace/projectEntityWorkspaceView.ts)). |
| **G5** | Documents reserved until E — honest. Catalog Passport later — honest. **Inner capabilities “out of D”** was not honest relative to G1; it was the substitution. |

**Outcome:** **STOP** for any further platform expansion that would multiply entity screens or rails. Brief-complete. Goal-incomplete.

Self-consistency trap: D4–D9 were checked against D2, not against G1. Locally the chain is correct. Relative to the original Entity Platform it is the wrong system.

---

## 3. Forms C1–C6

| Gate | Answer |
|------|--------|
| **G1** | One Forms platform: any module consumes HostFlow Form via public contract; no second form runtime/builder. |
| **G2** | Forbidden: module Form Builder; production submit that skips resolve→serve→execute (C6). |
| **G3** | A module can bind D2 `forms` via `listFormsPlatformHandlers()` (D3–D9 slots). A Sales inquiry still uses `SalesInquiryQuestionnaireSection` with **`leadId`** — Lead-backed questionnaire glue, not the public Form runtime as the only UI. |
| **G4** | Shared Intake public submit is the Foundation proof (C6). Not proof that every in-app questionnaire is platform-only. |
| **G5** | `TenantLeadForm` publication bridge until FormTemplate SoT — named. P3 Publish UI / P4 Themes / P5 Analytics — locked. ADR-022 not accepted — named. |

**Outcome:** **PASS_WITH_CONSTRAINTS**. Foundation ✅ is true for the **intake write path**. It is not true that “any module uses Forms without own glue.” Next Forms product work must not treat C6 as inner-capability complete.

---

## 4. Communication (Epic C)

| Gate | Answer |
|------|--------|
| **G1** | One communication platform; modules do not create their own send/thread/SMTP flows (INV-17). |
| **G2** | Forbidden: second outbound pipeline; new `send_email_for_tenant` outside the frozen allowlist. |
| **G3** | New product outbound must go Intent → pipeline. Module-local SMTP for **new** paths is gated. |
| **G4** | C1 Inbox + C2.1–C2.3 Intent emitters on tip; AST isolation. |
| **G5** | C2.4 Scheduling frozen (R1). Legacy SMTP allowlist **non-empty** (R2). Catalog has no Communication passport (A2-F1 RFC). Dual automation planes (A2-F5). |

**Outcome:** **PASS_WITH_CONSTRAINTS** — already recorded at [Epic C Complete Gate](epic-c-complete-gate.md) and [A2](platform-governance-review-a2.md). Not goal substitution: residuals were named instead of claiming clean PASS. Do not treat Epic C as “modules cannot still hit allowlisted SMTP.”

---

## 5. Acquisition / intake vs Application

| Gate | Answer |
|------|--------|
| **G1** | Intake/Lead/Application separation: operators work Application Workspace; Lead is not the product inbox; routing is platform, not module-local. |
| **G2** | Forbidden: mixed `/app/leads` inbox as Sales+Recruitment work target (slice 4). |
| **G3** | UI redirects to Sales Inquiry / Recruitment Application. Physical RecruitmentApplication table SoT (**R6**) is still locked. Modules still ride Lead transport. |
| **G4** | Slice 4 (#238): `/app/leads/:id` redirects. Facade APIs exist. |
| **G5** | R6 table-cutover — honest deferral. `/api/v1/leads` remains compat/admin/ingest. Stage 5 settings residual. |

**Outcome:** **PASS_WITH_CONSTRAINTS** / honest deferral. Not D-class. Do not claim “no module-local routing” while R6 is open; claim “no mixed operator inbox.”

---

## 6. RBAC / Governance (ADR-036)

| Gate | Answer |
|------|--------|
| **G1** | Modules do not invent job-title security roles; four trust roles + permissions/presets. |
| **G2** | Forbidden: fifth canonical JWT role without RFC; `Role.recruiter` as security. |
| **G3** | New module should use trust role + preset + permission. Matrix column keys (`recruiter`, `hr_officer`, …) still exist for compatibility. |
| **G4** | Enum remapped (Alembic `202608100001`); `make rbac-role-lint` in CI. |
| **G5** | Inventory still lists JOB_PROXY / UI leftover classes ([`rbac-role-usage-inventory.md`](../architecture/rbac-role-usage-inventory.md)). Portal vs viewer discipline is canon, not fully burned down. |

**Outcome:** **PASS_WITH_CONSTRAINTS**. Canon holds. Runtime leftovers are named migration, not a substituted goal.

---

## 7. Analytics

| Gate | Answer |
|------|--------|
| **G1** (if claimed as platform) | New dashboards reuse one KPI/chart family; modules do not mint parallel metric SoTs. |
| **G1 (what shipped)** | Acquisition Stage 6 **Decide** rung on Flight/Campaign KPI — [acquisition-stage-6-analytics.md](../tasks/acquisition-stage-6-analytics.md). Hard ban on new metrics ledgers **inside that epic**. |
| **G2** | Forbidden inside Stage 6: Timeline-as-dashboard, Forms/BI owning Acquisition KPI. |
| **G3** | An HR or Fleet dashboard is **not** forced onto an Acquisition KPI contract. No platform analytics kit close-out exists. |
| **G4** | Stage 6 PRs #213–#217 + ROI compose — Acquisition-only. |
| **G5** | Platform analytics / shared chart family — never claimed. Treat as **not started**, not COMPLETE. |

**Outcome:** Acquisition analytics **PASS** against **its** goal. Platform analytics **not claimed**. Risk: next dashboard copies Stage 6 patterns locally. Apply this gate when a “platform analytics” slice is proposed — do not infer it from Stage 6.

---

## 8. Actions / States / Relationships

| Gate | Answer |
|------|--------|
| **G1** | Shared language + runtime when a second module needs actions/states/relationships — not docs-only cells. |
| **G2** | Forbidden (P-03): a module-local action/status graph that duplicates a platform registry once that registry exists. |
| **G3** | No cross-module action registry. [ADR-019](../architecture/ADR-019-automation-capability-entitlement-control-plane.md) still records the hole. EntityModel sections omit comments; Shell `comments` never enables. |
| **G4** | None for a shared action runtime. |
| **G5** | Vocabulary / Catalog cells may exist as canon without runtime (Events gap class). Honest **if** nobody marked them COMPLETE as runtime. |

**Outcome:** **not started** as runtime platform. Do not read “canon exists” as “next consumer can subscribe.”

---

## What this audit does **not** authorize

- Patching `ApplicationRodoSection` / `ApplicationCommentsSection` as the fix  
- Entity Workspace D10 (eighth consumer on the weak D2 model)  
- Reopening Forms P3–P5, R6, C2.4, or Catalog Notifications RFC as this slice  
- Treating every residual as D-class substitution  
- Starting Documents E2 feat, Billing, or AI before Entity Platform goal is restored  

---

## Disposition (locked)

1. Introduce [Goal Completion Gate](goal-completion-gate.md) for every future phase close.  
2. Product Track → [Entity Platform Completion](../tasks/entity-platform-completion.md) (restore Entity Shell + common capabilities + module contributions).  
3. Documents E2 feat stays locked (brief [#271](https://github.com/igortatarynovich/HostFlow/pull/271) unchanged).  
4. Forms / Communication / Acquisition / RBAC residuals stay on their named owners — they do not jump the queue unless they are the original Entity Shell problem (they are not).

---

## History

- 2026-08-20: Triggered by D1–D9 passing brief gates while failing the original Entity Shell goal. Same-day Shared UI Capabilities (Notes+Consent, no registry) draft **superseded** — still accepted the weak D model.
