# Lead Intake Resolution Model & Activity Continuity (Guardrails)

**Status:** architecture / product spec — **guardrails before implementation**.  
**Purpose:** separate **intake triage** from **routing**, **recruitment workflow**, and **candidate operations** so the Lead screen becomes an **Intake Decision Workspace**, not a mini Candidate card.

**Related:** [**recruitment-operational-goals-and-order.md**](recruitment-operational-goals-and-order.md) (цели и порядок: Lead first → Candidate requirements → Handoff), [ingestion-contract-template.md](ingestion-contract-template.md) (mandatory lightweight contract per ingestion channel), [lead-intake-conversion-flow-audit.md](lead-intake-conversion-flow-audit.md) (implementation snapshot: stable vs gaps vs slices), [recruitment-domain-model.md](../architecture/recruitment-domain-model.md) (canonical story: Lead / Candidate / Application / conversion), [lead-to-candidate-operating-model.md](lead-to-candidate-operating-model.md) (entity boundaries), [activity-notification-operating-layer.md](../architecture/activity-notification-operating-layer.md), [phase-1-3-activity-layer-v1-migration-plan.md](../architecture/phase-1-3-activity-layer-v1-migration-plan.md), [application-creation-mvp.md](application-creation-mvp.md) (Applications MVP closed separately), [modules/leads.md](../modules/leads.md).

### Phase discipline: semantic foundation → operational consolidation

**Semantic foundation** (domain model, intake doctrine, duplicate semantics, Application intent, [ADR-013](../architecture/ADR-013-public-intake-strategy.md) governance, [ingestion contract](ingestion-contract-template.md) per channel, boundaries) is **largely complete**. The next phase is **operational consolidation**, not “more base entities by default”: align UX with doctrine, remove operational contradictions, enforce continuity, stabilise intake and routing, remove fake work. **Intake Resolution MVP** (§8) is the main delivery container for that phase.

**Hold the line:** do not skip ahead into Person, broad AI/intelligence, a giant cross-product Activities engine, or heavy lifecycle orchestration until the intake layer is **operationally stable** — semantics → governance → boundaries → continuity → intent separation → **then** automation at scale (§8.1).

**Success criterion (consolidation phase):** not “is there a CRUD screen / table for X?” but “does **real operational behaviour** (routing, vacancy, duplicate, Applications, continuity, ownership, automation side-effects) **match** doctrine?” — i.e. stabilizing and aligning, not exploratory feature stacking.

**Canonical operational architecture language:** shared vocabulary across PRs, ADRs, feature/architecture review, onboarding, and implementation slices — doctrine, phase framing, ingestion contracts, deferrals, success criteria above — so the same terms apply to UI, routing, automation, duplicate semantics, and ownership (failure mode: UI promises one thing, routing another, automation a third, trust collapses).

**Consolidation lens (examples):** ask **behaviour**, not checkbox coverage.

- **Vacancy:** not “is there a vacancy field?” but “does **vacancy behaviour** (confirm, routing, intent) match intake doctrine?”
- **Automation:** not “is there automation?” but “does it reinforce **operational truth** or generate **fake work**?”
- **Application:** not “does the table exist?” but “does it **separate recruitment intent from dossier** as the model requires?”

**Non-goals (for this document):** Rehire / new recruitment cycle spec (deferred); full UI build in one PR; changing Person model.

**Why this doc matters:** it is not “one more spec” — it is a guardrail against a **classic recruitment CRM failure mode**: turning **Lead** into a **bad Candidate** (early materialisation, fake tasks, lost context). The product pivot is from **“ATS with cards and statuses”** to an **operational recruitment workspace**.

### Canonical chain (target)

```text
Lead          → intake / qualification / routing *decisions*
    ↓
Candidate     → recruitment operational entity
    ↓
Application   → recruitment intent / cycle (see applications-operating-model)
    ↓
Workforce     → employment entity
```

**Strongest separations to preserve:** (1) **intake resolution** vs **candidate pipeline**; (2) **activity continuity** across convert — so the system does not **generate operational garbage** or make recruiters repeat the same work.

### Operational doctrine (decision checklist)

Recruitment flow changes should be judged **systematically**, not by gut feel. For any Lead/intake UX or API change, ask:

| Question | If “yes”, rethink |
|----------|-------------------|
| Does this turn **Lead** into a **pseudo-Candidate**? | Violates entity boundary. |
| Does this **mix intake** with **recruitment** pipeline? | Wrong layer. |
| Does this **create fake operational work** (duplicate tasks/SLAs)? | Burns trust. |
| Does this push **lifecycle depth** before intake is resolved? | Too early. |

Together with the canonical chain above, this forms a **sequential operational doctrine** for recruitment: specs are not a pile of notes — they are **constraints** for product and engineering decisions.

### Specification style: what we allow *and* what we forbid

Sustainable products need **negative specification** as much as positive: **what the system must not conflate**. Most CRMs degrade from absent **semantic constraints**, not absent features.

### Semantic constraints backbone (HostFlow)

These inequalities are the **architectural backbone** — cite them when reviewing APIs, UI, and automation.

| Constraint | Meaning |
|------------|---------|
| **Lead ≠ Candidate** | Intake signal ≠ recruitment operational entity. |
| **Candidate ≠ Application** | Working recruitment record ≠ intent / cycle (see applications-operating-model). |
| **duplicate review ≠ merge** | Operator decision + audit + override; not merge / fuzzy identity studio. |
| **assignment ≠ stage** | Ownership / queue ≠ pipeline stage code. |
| **intake ≠ recruitment ops** | Triage / resolution layer ≠ candidate lifecycle depth. |
| **reject ≠ close** | Structured intake exit with taxonomy ≠ generic “closed” with no signal. |
| **vacancy hint ≠ routing confirmation** | Suggested / visible vacancy ≠ canonical routing until **confirmed**. |
| **activities ≠ fake tasks** | One encoded stream of real work; no duplicate busywork across entities. |
| **automation ≠ intelligence** | Rules and triggers ≠ ML/AI; order remains **semantics → automation → intelligence**. |

Full entity semantics: [lead-to-candidate-operating-model.md](lead-to-candidate-operating-model.md).

### Feature filter (product)

For any new Lead/intake feature, ask:

> **Does this speed up the intake decision, or does it only add another layer of UI/chrome?**

Use this as a **gate**: if it does not shorten time-to-decision, demote, collapse, or defer.

---

## 1. Problem statement

Today multiple concerns are mixed on the Lead experience and right rail:

- intake triage;
- routing;
- recruitment workflow;
- candidate-style operations.

**Symptoms:** too many blocks, too much operational state, unclear **next action** for recruiters, heavy Meta lead processing, and **CRM generating “fake work”** after convert (duplicate call tasks, duplicate reminders, duplicate SLAs).

**Principle:** **Lead intake ≠ mini Candidate card.**

---

## 2. Target mental model: Intake Decision Workspace

On a **Lead**, the product should answer **four questions** only:

### 2.1 What did the lead bring?

From Meta / form / WhatsApp / other:

- identity & contact; language; citizenship; experience; documents; category;
- route / campaign; **source**; expectations; availability; any structured intake fields.

*(Presentation can be compact; this is read-heavy triage.)*

### 2.2 Does it fit us?

Outcome (product-facing, not necessarily one DB column today):

- **fit** / **weak fit** / **reject** / **needs review**

### 2.3 What happens next?

Examples:

- call; reject; **convert to candidate**; send to **pool**; reroute; request documents.

### 2.4 Who owns the next step?

- auto; recruiter; supervisor; **unassigned**

Until these are clear, the UI should **not** push candidate pipeline depth, assignment theatre, or long operational widgets.

### 2.5 UX success criterion (what “good” means on Lead)

**Shift in quality bar:** the implicit goal is no longer *“show more data on the lead screen”*. It is *“help the recruiter reach an **intake decision** faster”* — fit / call / reject / route / owner — with **minimal cognitive load**.

**Typical ATS failure (to avoid):** the right rail is dominated by **operational chrome** that belongs after conversion: heavy **fit** widgets, **automation** config, **stage**, **assignment**, generic **actions**, **follow-up**, **routing** jargon, **candidate lifecycle** hints — while the user still has not answered the few questions that matter at intake.

---

## 3. What must not dominate the Lead panel (early)

Defer, collapse, or move to Candidate / settings — **not primary on Lead intake**:

- candidate-style **stage** & lifecycle chrome;
- heavy **fit explanation** blocks (criteria essays);
- **automation config** surfaces;
- long **operational widgets** that belong after conversion.

*(Exact UI moves are incremental; this list is the guardrail.)*

### 3.1 Lead workspace UI cleanup (concrete next pass)

1. **Reduce visual dominance** of operational blocks on Lead: stage & assignment, heavy fit panels, automation surfaces, candidate lifecycle hints — collapse, move to Candidate, or demote to secondary.  
2. **Promote Intake Resolution** as the **primary action area**: qualified path, **reject**, **pool**, **duplicate** flow, **request info/docs**, **confirm vacancy** — one coherent strip, not buried in chrome.  
3. **Vacancy confirmation is intake UX**, not a hidden routing mechanic: recruiter must see **suggested → selected → confirmed** as part of resolution (see §6).  
4. **Qualification summary** stays **compact**: experience, docs, citizenship, language, fit (one line or badge), route/source — not giant widgets.  
5. **Build continuity through Activities** (see §7): the same activity model later underpins SLA, timeline, inbox, workload, and automation — so Lead-side contact work is recorded **once** and carries over cleanly.

---

## 4. Lead intake resolution (separate from Candidate pipeline)

**Intake resolution** is *not* the same as Candidate pipeline stage.

### 4.1 Conceptual resolution states

Illustrative lifecycle for **intake** (names may map to existing `leads.status` + normalized payload over time):

| State | Meaning |
|-------|--------|
| `new` | Just arrived; not triaged. |
| `review_required` | Human decision needed (quality, policy, ambiguous fit). |
| `qualified` | Accepted for next operational step (may still be pre-candidate). |
| `rejected` | Closed at intake with reason taxonomy (§5). |
| `converted` | Successfully linked to recruitment entity (e.g. Candidate created/attached). |
| `duplicate_review` | Duplicate decision queue (already exists — keep distinct from reject). |
| `routed_to_pool` | Intent captured without a specific vacancy (pool / talent context). |

**Guardrail:** rejection at intake ≠ duplicate override ≠ candidate “lost” — align with [lead-to-candidate-operating-model.md](lead-to-candidate-operating-model.md) semantic boundaries.

### 4.2 Missing piece: explicit **Intake Resolution**

Today there is strong **process / routing / convert** machinery; the product gap is a **first-class intake resolution** path (especially **reject** with structured reasons) *before* Candidate work begins.

---

## 5. Reject reason taxonomy (intake)

Canonical **codes** (string enum in API / `normalized` / analytics — exact storage TBD in implementation phase):

| Code | Typical use |
|------|-------------|
| `insufficient_experience` | Below bar for role/route. |
| `missing_documents` | Cannot proceed without docs. |
| `unsupported_citizenship` | Policy / legal route. |
| `language_mismatch` | Language requirement not met. |
| `invalid_contact` | Bad phone/email; unreachable. |
| `no_response` | Outreach exhausted (if used at lead stage). |
| `salary_mismatch` | Expectations vs budget. |
| `unsuitable_route` | Geography / lane / client fit. |
| `duplicate_spam` | Abuse / duplicate noise (distinct from `duplicate_review`). |

**Why (operations):** campaign feedback, recruiter KPI, automation hooks, and **trust** (structured close, not “lead vanished”).

**Why (intelligence):** reject codes are **not** a bureaucratic field — they are the **foundation for later intelligence**: ad quality scoring, route quality, market/source fit, recruiter efficiency analytics, and policy automation. **Order matters:** nail **operational semantics** and consistent encoding first; then automation that consumes codes; only then ML/AI that needs clean labels.

---

## 6. Vacancy: UI context vs canonical routing

**Problem:** “Vacancy is visible to the human, but the routing system does not know it.”

**Rule:** **UI vacancy hint ≠ canonical routing mapping** until confirmed.

### 6.1 Manual vacancy assignment in Lead intake (minimal)

In the Lead panel:

- show **current suggested** vacancy (from mapping / payload);
- allow **change / select** vacancy (simple control, not a 30-field modal);
- **Confirm vacancy** — commits canonical routing context for this lead.

After confirm:

- routing is **resolved** for this lead;
- **Process** / convert paths that depend on vacancy can proceed consistently.

**UX guardrail:** one line + dropdown + one primary button — not a wizard.

**Product rule:** **Confirm vacancy** is part of **intake resolution** in the UI — recruiters should never perceive it as a separate “routing subsystem” that contradicts what they see in the headline vacancy field.

---

## 7. Activity continuity (Lead → Candidate)

**Rule:** If contact work already happened **on the Lead** (call, WhatsApp, document request, notes, outcomes), **Convert → Candidate** must **not** spawn redundant Candidate-side work.

### 7.1 Anti-patterns (forbid)

After convert, Candidate must **not** automatically get:

- duplicate **first call** task;
- duplicate **intro** reminder;
- duplicate **contact SLA** / same intent as already closed on Lead.

Otherwise the CRM creates **fake work** and loses recruiter trust.

### 7.2 Target behaviour

**Convert Lead → Candidate** should carry forward (implementation detail in a later phase):

- contact / activity history relevant to recruitment;
- call outcomes;
- notes;
- **intake resolution** metadata (fit decision, reject avoided path, confirmed vacancy).

Then Candidate starts from a truthful state, e.g.:

- **contact established**, or
- **documents requested**, or
- **qualification started**,

—not always “call the candidate” from a blank slate.

**Alignment:** see Activity & Notification operating layer docs for how activities/notifications attach to entities; continuity rules may require explicit **handoff** semantics from `lead_id` to `candidate_id` without duplicating open items.

### 7.3 Activities as the continuity spine

Prefer recording intake-relevant work (calls, messages, doc requests, outcomes, notes) as **first-class activities** (or their canonical equivalent in the activity layer) on the **Lead** where appropriate, so that after convert the same stream can power:

- SLA and due dates;
- unified **timeline**;
- **inbox** / workload views;
- automation triggers;

—without spawning a **second parallel** task system on Candidate for the same human intent.

**Future architectural layer (do not jump ahead):** the end state is a **unified operational activity model** — not “just tasks” — spanning **calls, reminders, follow-ups, document requests, SLA, inbox-style events, recruiter workload**, with **continuity** across **Lead → Candidate → Application → (Workforce) → communications → timeline**. That layer removes duplicated actions between entities. **Correct sequence:** stabilise **intake resolution, vacancy confirmation, reject semantics, and continuity rules** (§8 table) *before* expanding the activity model as a cross-product rewrite. The Activity & Notification operating layer docs are the mechanical foundation; this file defines **when** to lean on them for intake without creating **fake** work.

---

## 8. Canonical Intake Resolution Layer — delivery priority

**Architectural program:** **Canonical Intake Resolution Layer** — граница между **intake world** и **recruitment / dossier operations**: vacancy + routing resolution, intake actions, qualification, reject semantics, continuity guards, ownership handoff readiness, demotion of candidate-style chrome на Lead. Это **не** «рефакторинг CRM ради UI», а **operational layer** (trust, adoption, analytics correctness, automation quality).

**Practical delivery track:** **Intake Resolution MVP** — шесть срезов ниже (в этом порядке). Не путать с «только Lead UI cleanup»: срез 6 — последний, после семантики и guards.

**Параллельно (архитектура):** публичный candidate intake — [ADR-013-public-intake-strategy.md](../architecture/ADR-013-public-intake-strategy.md) (**Accepted 2026-07-02**); contract [ingestion-contract-public-intake.md](ingestion-contract-public-intake.md). Telegram — отдельный contract при расширении.

Порядок срезов совпадает с [lead-intake-conversion-flow-audit.md](lead-intake-conversion-flow-audit.md) §4.

| Priority | Slice (Intake Resolution MVP) | Rationale |
|----------|-------------------------------|-----------|
| **1** | **Manual vacancy confirmation** | Устраняет главную operational contradiction: vacancy в UI vs routing «не знает» — ломается доверие. Suggest → select → **Confirm vacancy** (§6) + согласованный routing resolution. |
| **2** | **Intake resolution actions** | Явный operational набор: convert, reject, pool, request docs, duplicate review, assign / confirm ownership — **не** только «Process» и воронка как у кандидата. |
| **3** | **Reject reasons + intake taxonomy** | Foundation для source/campaign/recruiter KPI и automation; CRM `lost` недостаточно. §5 коды — опора аналитики. |
| **4** | **Qualification summary** | Один компактный блок (опыт, документы, язык, fit, route, source) **без** гигантских виджетов — поддержка решения по intake, не дублирование candidate card. |
| **5** | **Activity continuity guards** | Enforcement: нет дублирующего first-call/SLA после convert; перенос контекста (§7). Doctrine без слоя проверки ≠ «проблема решена». |
| **6** | **Lead workspace cleanup** | Demote stage/fit/automation/playbook до вторичного; **intake decision first** в layout и mental model. | **Done (2026-07-02)** — recruitment detail + inbox workspace; CRM chrome under More. |

**Порядок намеренный:** сначала семантика, действия, таксономия, qualification data, continuity guards — **затем** чистка UI. Рисовать «красивый Lead» до стабилизации смыслов почти всегда даёт **operationally inconsistent** интерфейс.

*Parallel track (optional):* persist **reject / resolution** codes в API + audit events **раньше** полного UI среза 3, чтобы данные не терялись (совместимо с 1–2).

**Defer until Intake Resolution MVP is stable:** Activities operational spine; Rehire; richer Applications lifecycle UI; Person; intelligence — **сначала закончить этот слой**, иначе fake work и шумная automation.

**Meta:** lock this spec; align `leads.status` / `normalized` only as needed per slice; ship incrementally (no big-bang UI).

### 8.0.3 Recruitment Lead Intake Decision Surface

Named cut: **Recruitment Lead Intake Decision Surface**. Four atomic deliverables (this order): answers projection → call outcome → authoritative intake state → conversion mapping + activity continuity.

**Operator funnel:** `new → in_progress → terminal decision`. Terminal outcomes: converted | rejected | pool | duplicate_review. “No answer” is a **call outcome**, not a lead stage.

**Authority:** `intake_resolution_v1` is the only recruitment-intake lifecycle SoT. UI / KPI / `GET /leads?intake_lifecycle=` consume one projection:

`new | in_progress | converted | rejected | pool | duplicate_review`

CRM `Lead.stage` is a **compatibility projection** only (`new` → `contacted` on first substantive action; `converted` / `lost` on terminals). Do not use it as a second independent truth for recruitment filters.

**Queue filters:** `new | in_progress | needs_decision | pool | completed` (legacy `intake_lane` aliases still accepted). These partition the projection: `needs_decision` is duplicate review only (not “any called lead”).

**First substantive action** (not opening the card) stamps `in_progress`: saved call result, operator note, operator RODO send / source-provided, request_info.

**Call activity:** `POST /leads/{id}/call-result` records `call → outcome → note → actor → timestamp → next_contact_at`. History in `call_results_v1`. Convert carries history + original `field_answers` onto the candidate (`lead_continuity_v1` / `intake_answers_v1`).

**Conversion mapping:** if an answer has an executable mapping to a Candidate destination (field-registry qualified code or `mapping_applied_v1.executable_rules`), the value is written at convert. Unmapped answers remain as the original questionnaire. No conversion-specific extra whitelist.

**Out of this cut:** pipeline builder, SLA engine, scoring, AI, candidate documents, candidate stages, task sequences, comms automations.

### 8.0 Slice 2 — implementation signed off (operational consolidation, 2026-05)

**Scope:** intake resolution **actions** + **reject taxonomy** + **manual Process gating** (stable block codes), aligned across **all operator entrypoints** — not only the primary Process button.

**Backend (enforcement)**

- `POST /api/v1/leads/{id}/intake-decision` — **qualify**, **reject** (required `reason_code`), **pool**, **request_info** (+ note), **duplicate_review**; persistence in `normalized.intake_resolution_v1`; **reject** and **duplicate_review** paths do **not** create Candidate/Application until doctrine allows conversion.
- `POST /api/v1/leads/{id}/process` — `manual_process_block_code` before pipeline → **422** with `detail: { code }` (stable machine codes).
- **Same block layer** applied before pipeline on: bulk **auto-process** / **NBA process-new** (`service/_bulk.py`), **Meta retry** (`service/_retry.py`), **CSV reimport** for an existing row eligible for re-run (`services/imports/leads.py`); CSV passes **`target_lead_id`** to avoid attaching the pipeline to the wrong `Lead` row. **Webhook / first-row Meta ingest** are not bluntly short-circuited at file ingress (normalization / updates); a stricter **conversion-only** gate inside `process_normalized_lead` remains a separate product decision if needed.
- Reprocess path preserves operational decisions via **`_merge_lead_normalized_fallback`** (e.g. `intake_resolution_v1`, pool intent).

**Frontend (UX + gating)**

- **`LeadIntakeResolutionPanel`** — vacancy select + **Confirm vacancy**; intake block with all five actions above; copy positions these as **intake decisions**, not candidate pipeline stages.
- **`manualProcessBlockHint`** / **`manualProcessBlockedUserMessage`** — single client semantics; **Lead detail header Process**, **Leads list / inbox Process**, and **LeadQualificationSuggestionPanel** Process CTA all use the same hint (no secondary bypass).

**Automated tests**

- Backend: `backend/tests/api/test_lead_intake_decision.py` (including bulk worker + CSV reimport gate).
- Frontend: `hostflow-frontend/src/utils/__tests__/intakeResolution.test.ts`, `hostflow-frontend/src/components/leads/__tests__/LeadQualificationSuggestionPanel.intake.test.tsx`.

**Automated smoke** (backend): `backend/tests/api/test_lead_intake_decision.py` covers the core intake × Process matrix (reject, request_info, duplicate_review, pool, qualify + confirm, bulk worker gate, CSV reimport gate).

**Manual staging smoke** (run once per staging deploy for intake / lead regression):

1. **Reject** — no Candidate/Application; Process remains blocked (UI + 422 with stable code).
2. **Request info** — Process blocked; **note** persisted on `intake_resolution_v1` / visible in API+UI.
3. **Pool** — Process **without** committed vacancy creates **Candidate** + **pool Application** when intake doctrine satisfied.
4. **Duplicate review** — Process blocked until duplicate path resolved.
5. **Qualify + confirmed vacancy** — Process creates **Candidate** + **Application** (happy path).
6. **CSV reimport** of an intake-rejected `needs_routing` row — `error_report` row shows stable **block code**; no new Candidate from that import pass.
7. **Bulk / NBA / retry** — do not bypass the same blocks as manual Process (spot-check one blocked lead in queue).

**Slice 2 closure:** implementation + docs aligned; **no additional intake layer** required before moving on.

**Slice 3 closure:** qualification summary is **read/decision support only** (gated UI, no empty block, shared `leadQualificationPreview` utility, narrow tests). See `docs/specs/workflows/slice-3-qualification-summary-data-audit.md`.

**Next program slice:** **Slice 4 — Activity continuity guards** (Lead → Candidate handoff): no fake first-contact work, no reminder spam after lead-side contact, carry context — **spec skeleton:** `docs/specs/workflows/slice-4-activity-continuity-guards.md`.

**Explicitly not Slice 2:** full Lead workspace mega-cleanup (table slice **6**); cross-product **Activities** spine; lifecycle / AI expansion.

### 8.0.1 Lead-stage RODO (art. 14) — intake contract (signed off, 2026-05)

**Boundary:** RODO / GDPR art. 14 notice is satisfied **on the Lead** before gated intake actions. After conversion, candidate-level compliance may apply separately; lead audit is copied read-only into `Candidate.extra['rodo_lead_audit']` — not re-sent by default.

**Delivery (ADR-031):** compliance **gates and audit** stay on Lead (`normalized.rodo`). When outbound email is required, **send** must use Communication Pipeline with opaque result (`sales_inquiry` \| `application`) via module binders — not business-module SMTP. Permanent path: [ADR-031](../architecture/ADR-031-compliance-outbound-requires-opaque-result.md) · [task](../tasks/compliance-outbound-pipeline-early-result.md). Legacy `lead_rodo` SMTP is migration debt (C0.1b allowlist) until removed.

**Company policy (ADR-033, target SoT):** operational RODO/ops email policy resolves via [lead-lifecycle-email-policy.md](lead-lifecycle-email-policy.md) — Vacancy override → Company `lead_lifecycle_email_v1` → tenant preset. Control Center: **Настройки → Коммуникации → Lead lifecycle email**. Tenant JSON below remains preset/cutover adapter.

**Tenant policy** (`Tenant.settings.lead_rodo_v1`, exposed on `GET/PATCH /api/v1/settings/leads/settings` — **preset / migration**):

| `lead_rodo_send_mode` | Behaviour |
|-------------------------|-----------|
| `manual` (default) | Recruiter sends from intake rail / API; no outbound on ingest. |
| `auto_on_lead_created` | After **new** lead row + custom-field sync: auto-send for eligible ingest sources when email channel exists (MVP: Meta, generic webhook, `csv_import`, import, Telegram*, public form). |
| `auto_on_first_action` | Outbound attempt immediately before first gated action (process, request_info, stage `contacted`, `communication_call`). |

**Policy SoT (ADR-033):** firm **OwnCompany** `lead_lifecycle_email_v1`; optional client + vacancy override — [lead-lifecycle-email-policy.md](lead-lifecycle-email-policy.md).

Also: `lead_rodo_channels` (default `["email"]`), optional `lead_rodo_template_id` (active `rodo_clause` version override).

**Persistence** (`Lead.normalized.rodo`):

| `status` / signal | Meaning |
|-------------------|---------|
| `sent` | Outbound art. 14 email sent (`sent_at`, `channel`, `recipient`, optional `auto_trigger`, `ingest_source`). |
| `source_provided` | Notice already covered at source (e.g. `normalized.rodo_notice_at_source` or public intake consents) — **no duplicate outbound**. |
| `pending_channel` | Auto/manual send could not run — no usable channel (MVP: email). |
| `failed` | Send error; manual retry allowed. |
| *(none / unsatisfied)* | UI: `manual_required`; gates apply. |

**Idempotency:** webhook replay for the same `tenant_id + source + external_id` does not send a second notice (`lead_rodo_sent_from_normalized`). Pipeline merges preserve `normalized.rodo` when other keys are rewritten (`normalized_merging_lead_rodo` in `update_lead`).

**Gates** (422 `LEAD_RODO_REQUIRED` unless satisfied): `POST .../process`, intake-decision **request_info**, CRM stage → **contacted**; bulk/retry/CSV reimport use the same `manual_process_block_code` / `ensure_lead_rodo_allows_action` layer as manual Process.

**API (operator):**

- `POST /api/v1/leads/{id}/compliance/rodo/send` — manual / retry (always available when auto is on).
- `POST /api/v1/leads/{id}/compliance/rodo/source-provided` — mark covered at source.
- `POST /api/v1/leads/bulk/compliance/rodo/retry` — bulk re-send after Pipeline cutover (default `rodo.status=failed`; `dry_run` supported). CLI: `backend/scripts/retry_lead_rodo.py`.

**UI:** Meta Leads settings — mode select; **Intake Decision rail** — status copy for `sent` / `failed` / `pending_channel` / manual hint; Send RODO + “covered at source” buttons retained for retry. **Sales inquiry rail / client lead call-result** — same Send / source-provided unlock (ADR-033 slice C) before `call-result` / stage `contacted`.

**Tests:** `backend/tests/api/test_lead_rodo_gate.py`, `backend/tests/api/test_lead_rodo_auto.py`.

**Out of scope (operational communication — see §8.0.2):** application-received / moving-forward / rejected templates, tracking links, non-RODO operational email — do not extend this gate.

### 8.0.2 Lead operational communication (MVP PR1 — signed off, 2026-05)

**Boundary:** Candidate-facing **operational** status email on the Lead lifecycle. **Not** RODO / art. 14 — separate settings, persistence, audit, and UI block.

**Delivery (ADR-031 / C5):** hooks remain on Lead lifecycle; send requires Pipeline inputs (thread + purpose + template metadata) from destination binders. Fail-closed `communication_pipeline_required` without binder is intentional until [compliance-outbound-pipeline-early-result](../tasks/compliance-outbound-pipeline-early-result.md) PR-4 lands.

**Tenant policy** (`Tenant.settings.lead_communication_v1`, exposed on `GET/PATCH /api/v1/settings/leads/settings`):

| Flag | Behaviour |
|------|-----------|
| `lead_communication_enabled` | Master switch; when off, no operational sends. |
| `send_application_received` | After **new** **recruitment** lead ingest (post contact check) when email exists. **Not** for B2B / `client` + `client_lead` inquiries. |
| `send_rejection_notice` | After intake decision **reject**. |
| `send_moving_forward_notice` | After successful Lead → Candidate conversion (production path: `create_candidate_full` in `process_normalized_lead`). |

**Persistence** (`Lead.normalized.lead_communication_v1`): per event type (`application_received`, `lead_rejected`, `moving_forward`) — `sent` | `failed` | `pending_channel` (no email), with timestamps. Pipeline merges preserve `lead_communication_v1` alongside `rodo` (`normalized_merging_lead_persisted_blocks`).

**Idempotency:** one send per event type per lead; webhook replay does not resend.

**Audit:** `lead.communication.application_received_sent` | `rejection_sent` | `moving_forward_sent` | `failed`.

**Hooks:** ingest (`maybe_send_application_received_on_ingest`), intake reject (`maybe_send_lead_rejected_notice`), conversion (`maybe_send_moving_forward_notice`).

**UI:** Meta Leads settings — toggles next to RODO; **Intake Decision rail** — read-only “Operational emails” status (no retry in PR1).

**Tests:** `backend/tests/api/test_lead_communications.py`.

**Out of scope (later PRs):** in-app, Telegram, status portal, manual retry UI, HR branch work.

**Manual staging smoke** (add to deploy checklist):

8. Meta lead + email + `auto_on_lead_created` → RODO sent, rail `sent`, Process allowed after vacancy confirm.
9. Lead without email → `pending_channel`, Process / request_info / contacted blocked; manual send or source-provided unblocks.
10. Meta webhook replay → single send, no duplicate audit spam.
11. Public form / ingest with `rodo_notice_at_source` → `source_provided`, no duplicate send.
12. Failed send → rail `failed`, retry via manual send clears gate.

### 8.1 Product evolution order (doctrine)

**Semantics → automation → intelligence/AI.**

1. **Operational semantics** — intake resolution states, reject codes, vacancy confirm, continuity rules (truth in the domain model).  
2. **Automation** — rules that consume those signals (routing, notifications, assignments).  
3. **Intelligence** — scoring, recommendations, ad quality, forecasting — only when encoded outcomes are **reliable**.

Skipping (1) and jumping to (3) produces **noisy automation**, **broken scoring**, **hollow suggestions**, and **recruiter distrust**. **Recruitment AI without clean operational semantics** is not “smart CRM” — it is **fake work at scale**. The enterprise path is a **deterministic operational layer first**, then intelligence that consumes it.

---

## 9. Document hierarchy (reminder)

1. [recruitment-domain-model.md](../architecture/recruitment-domain-model.md) — **full narrative** Lead → Candidate → Application (no code).  
2. [lead-to-candidate-operating-model.md](lead-to-candidate-operating-model.md) — canonical entities, events, duplicate §8.  
3. **This file** — intake workspace, resolution, vacancy confirm, **lead-stage RODO (§8.0.1)**, activity continuity guardrails.  
4. Activity layer ADRs / migration plan — mechanical model for activities & notifications.  
5. [application-creation-mvp.md](application-creation-mvp.md) — Application MVP DDL/API/tests.
