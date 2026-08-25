# Existing Runtime Reuse Review — Automation & Capability Control Plane

**Status:** Complete (architecture + code audit)  
**Date:** 2026-07-13  
**ADR:** [ADR-019](../architecture/ADR-019-automation-capability-entitlement-control-plane.md)  
**Prerequisite:** ADR-018 PR 2B-3 (Requirement Evaluation cutover)  
**Decision:** **Extend platform layer; do not fork per-module automation silos**

> **PR 3A-0 complete** when §8–§11 accepted. **3A-1** starts after sign-off.

---

## 1. Цель аудита

Перед проектированием **Reaction Orchestrator** (Automation & Capability Control Plane) определить, что в текущем runtime можно **reuse**, **extend**, **replace** или создать **new**, без дублирования domain evaluators и без новых локальных автоматизаций в Recruitment / HR / Sales / Finance / Fleet.

**Запрет:** Reaction Orchestrator не вычисляет requirement fulfillment, transfer readiness, billing milestones или qualification — это domain evaluators. Automation conditions **не** дублируют domain policy (ADR-019 §14.4).

---

## 2. Найденные подсистемы

### 2.1 Tenant automation rules (EXTEND — не SSOT control plane)

| Компонент | Путь | Responsibility | Verdict |
|-----------|------|----------------|---------|
| **AutomationRule** model | `backend/app/models/automation_rule.py` | Tenant rules: trigger, conditions_json, actions_json, priority | **Extend** → migrate into platform `AutomationRule` contract |
| **automation_rules service** | `backend/app/services/automation_rules.py` | Match conditions, fire rules, `create_reminder` action | **Extend** — thin runner over Action Registry |
| **API** | `backend/app/api/v1/automation_rules.py` | CRUD + plan gates | **Extend** |
| **UI** | `AutomationsHubPage`, `AutomationRulesPage`, `AutomationLogPage` | Hub + rule editor + log | **Extend** → Automation Center |
| **Triggers (today)** | `TRIGGERS` in service | `candidate.created`, `candidate.stage_changed`, `candidate.risk_band`, `document.expiring`, `lead.processed`, `lead.pipeline.stage_changed`, `lead.qualification` | **Extend** → canonical domain event catalog |
| **Actions (today)** | `execute_automation_rule` | Mostly `create_reminder` | **Replace** ad-hoc JSON → Action Registry |
| **Call sites** | `candidates/service.py`, `leads/_processing.py` | Direct `run_automation_rules(...)` after mutations | **Replace** → event publish + engine consume |

**Вывод:** Есть рабочий MVP tenant rules, но он **не** platform control plane: нет capability/entitlement checks, нет cross-module actions, нет execution modes, нет idempotency contract, вызовы встроены в module services.

---

### 2.2 Plan / subscription gates (REUSE)

| Компонент | Путь | Responsibility | Verdict |
|-----------|------|----------------|---------|
| **plan_feature_gates** | `backend/app/services/plan_feature_gates.py` | Team-tier, trial caps, automation_rules mutation/count limits | **Reuse** as Entitlement Service adapter |
| **billing_pack_addons** | `backend/app/services/billing_pack_addons.py` | Pack increments (`AUTOMATION_RULES_ENABLED_CAP`) | **Reuse** |
| **Tenant / TenantLicense** | `backend/app/models/tenant.py` | Plan, trial, license rows | **Reuse** |
| **Stripe price refs** | `backend/app/core/settings.py` | Automation rules pack SKUs | **Reuse** |

**Вывод:** Entitlement checks уже частично есть для automation rules count/mutation. Pricing **не** должен быть зашит в automation code — читать entitlement result (ADR-019).

---

### 2.3 Module enablement (EXTEND)

| Комponent | Путь | Responsibility | Verdict |
|-----------|------|----------------|---------|
| **Company.enabled_modules** | ADR-003 / `company_module_access.py` | Company ∩ tenant module keys | **Extend** → feeds Capability Registry |
| **Tenant settings.modules** | tenant snapshot | Legacy triad + module flags | **Extend** → module activation lifecycle |
| **Module catalog** | `module-catalog-and-routing-map.md` | Five product modules + platform capabilities | **Reuse** as capability namespace |

**Вывод:** Нет единого Capability Registry и previewable locked capabilities. `enabled_modules` — близкий predecessor, но не описывает feature-level capabilities (`recruitment.to_hr_transfer`, `finance.invoice_generation`).

---

### 2.4 Domain evaluators — sources of truth (REUSE, never duplicate)

| Компонент | Путь | Publishes fact | Verdict |
|-----------|------|----------------|---------|
| **RequirementEvaluationService** | `backend/app/requirement_rules/evaluation/` | `can_transition`, blockers, per-requirement status | **Reuse** — emits `candidate.requirements_evaluated` |
| **TransferPolicyResolver** | `backend/app/services/transfer_policy_resolver.py` | Handoff readiness, destinations, blocking_reasons | **Reuse** — emits `candidate.transfer_ready` |
| **candidate_doc_pipeline_guard** | `backend/app/services/candidate_doc_pipeline_guard.py` | Stage gate enforcement (consumer) | **Keep** as action target, not automation owner |
| **Field requirements** | `field_registry/requirement_evaluator.py` | Intake field completeness | **Reuse** for qualification facts |
| **Workforce eligibility** | `workforce_eligibility_delivery_contract.py` | Eligibility context | **Reuse** |
| **Service order billing** | `service_order_invoice_billing.py` | Billing snapshot helper | **Partial** — not milestone evaluator yet |

**Вывод:** Domain truth уже разделена (ADR-018). Automation **подписывается** на результаты evaluation, не пересчитывает их.

---

### 2.5 Event / audit infrastructure (PARTIAL — NEW outbox + orchestrator)

| Компонент | Путь | Responsibility | Verdict |
|-----------|------|----------------|---------|
| **Domain event outbox** | — | Transactional publish with domain mutations | **New** (mandatory) |
| **Reaction Orchestrator** | — | Match rules, lifecycle, freshness gate | **New** |
| **ActivityLog** | `backend/app/models/audit.py` + `audit.py` service | `automation.rule_fired` audit rows | **Extend** → automation_executions audit |
| **Security events** | `emit_security_event_v1` | Security taxonomy | **Pattern reuse** — separate from domain events |
| **Direct service calls** | candidates → run_automation_rules | Implicit "events" | **Replace** |

**Вывод:** Нет канонического domain event contract и outbox. Post-commit hooks **недопустимы** для automation-critical paths. ActivityLog — audit trail, не event bus.

---

### 2.6 Notifications / tasks / suggestions (EXTEND)

| Компонент | Путь | Responsibility | Verdict |
|-----------|------|----------------|---------|
| **ADR-012** | Activity & Notification Operating Layer | Target unified Activity + Notification | **Reuse** as action targets |
| **reminder_tasks** | `backend/app/services/reminder_tasks.py` | Create reminders | **Reuse** via `notifications.send` / `activity.create` actions |
| **next_action publisher** | `backend/app/platform/next_action/` | NBA suggestions for leads | **Extend** → `suggested` execution mode |
| **uos_auto_activities** | `backend/app/services/uos_auto_activities.py` | Auto activity creation | **Absorb** into Action Registry |

**Вывод:** Execution modes `manual` / `suggested` могут опираться на NBA + Activity layer (ADR-012).

---

### 2.7 Billing / invoicing (ARCHITECTURE ONLY)

| Компонент | Путь | Responsibility | Verdict |
|-----------|------|----------------|---------|
| **ADR-004** | Billing Events rule | Modules emit events; Finance creates invoices | **Reuse** as billing action boundary |
| **BillingEvent model** | — | Normalized billable event | **New** |
| **Invoices API** | `backend/app/api/v1/invoices/` | Invoice CRUD | **Reuse** as Finance action target |
| **Direct invoice from Recruitment** | scattered helpers | Anti-pattern per ADR-004 | **Prohibit** |

---

### 2.8 Assignment / routing (EXTEND)

| Компонент | Путь | Responsibility | Verdict |
|-----------|------|----------------|---------|
| **Lead qualification rules** | `leads/service/_helpers.py` | AutomationRule `lead.qualification` routing | **Migrate** to platform templates |
| **Manager assignment** | `manager-assignment.md` + services | Round-robin / queue | **Reuse** via `assignment.assign_owner` action |
| **Smart operations bundle** | `plan_feature_gates.py` | Weighted routing on Team+ | **Entitlement-gated** |

---

### 2.9 Cross-module transfer (REUSE boundaries)

| Компонент | Путь | Responsibility | Verdict |
|-----------|------|----------------|---------|
| **ADR-002** | Recruitment ↔ HR boundary | Handoff contract | **Reuse** |
| **TenantLink** | `tenant_links` service | Handoff destinations | **Reuse** |
| **transition_bridge** | `requirement_rules/transition_bridge.py` | PE gate payload | **Reuse** pattern for action input |
| **Direct HR employee create from Recruitment** | — | Forbidden | **Prohibit** — only `hr.create_employee` public action |

---

## 3. Карта: Extend / Replace / New

| Asset | Verdict | ADR-019 action |
|-------|---------|----------------|
| `automation_rules` table + service | **Extend** | Evolve schema; runner → Automation Engine |
| `plan_feature_gates` | **Reuse** | Entitlement Service adapter |
| `Company.enabled_modules` | **Extend** | Module activation → capabilities |
| `RequirementEvaluationService` | **Reuse** | Event source only |
| `TransferPolicyResolver` | **Reuse** | Event source only |
| Direct `run_automation_rules()` in modules | **Replace** | Outbox publish |
| Per-module stage transition automation | **Replace** | Platform templates |
| Transactional outbox + Event Contract Registry | **New** | PR 3A-1 |
| Reaction Orchestrator + execution lifecycle | **New** | PR 3A-4 |
| Capability Registry + CapabilityPreview DTO | **New** | PR 3A-2, 3A-6 |
| Action Registry | **New** | PR 3A-3 |
| Automation templates | **New** | Canonical presets |
| BillingEvent | **New** | Per ADR-004 |
| `AutomationsHubPage` | **Extend** | Automation Center |

---

## 4. Четыре слоя правил (не смешивать)

| Layer | Owner today | ADR-019 owner |
|-------|-------------|---------------|
| **Domain rules** | Requirement Policy, Transfer Policy, … | Same — unchanged |
| **Automation rules** | `automation_rules` (partial) | Platform Reaction Orchestrator |
| **Capability rules** | `enabled_modules` + plan gates (partial) | Capability Registry + Entitlement Service |
| **Permission rules** | RBAC (`rbac_matrix.md`) | RBAC + automation admin scopes |

---

## 5. PR plan (согласовано с ADR-019)

| PR | Content |
|----|---------|
| **3A-0** | Code-level audit (§8–§11) — **complete** |
| **3A-1** | Event Contract Registry + transactional outbox + publisher worker |
| **3A-2** | Capability Registry + entitlement adapter + availability reason model |
| **3A-3** | Action Registry + public actions |
| **3A-4** | Execution model: lifecycle, idempotency, freshness gate, `superseded` |
| **3A-5** | Suggested automation via NBA |
| **3A-6** | CapabilityPreview platform read model (Candidate Workspace first consumer) |
| **3A-7** | Automation Center read model |

**Не начинать с publisher.** 3A-0 обязателен — иначе риск второго механизма рядом с `automation_rules`, NBA, stage services, feature gates.

---

## 6. Рекомендуемый первый вертикальный срез

После ADR-018 2B-3 и **3A-0**:

1. Outbox: `candidate.requirements_evaluated` (from RequirementEvaluationService)
2. Outbox: `candidate.transfer_ready` (from TransferPolicyResolver)
3. Capability: `recruitment.automatic_stage_transition`, `recruitment.to_hr_transfer`
4. Template: suggest stage transition when payload `can_transition=true`
5. Template: open transfer on `transfer_ready` fact event
6. Freshness gate before `candidate.open_transfer`
7. If HR not entitled → **CapabilityPreview** DTO (not disabled button)
8. If HR entitled → `candidate.open_transfer` via Action Registry (suggested/approval first)

**Slice done when:** full contour proven (evaluation → outbox → orchestrator → entitlement → action/preview → audit).

**Не строить:** drag-and-drop builder, billing automation, scheduled rules, multi-action chains.

---

## 8. PR 3A-0 — `run_automation_rules()` call site classification

**Found:** 5 direct `run_automation_rules()` call sites + 1 indirect risk-band runner + 1 parallel qualification runner (same `AutomationRule` table).  
**Note:** trigger `document.expiring` registered in `TRIGGERS` but **has zero call sites** in backend (dead until wired).

### CS-01 — `candidate.created`

| Field | Value |
|-------|-------|
| **caller** | `create_candidate_full()` — `backend/app/api/v1/candidates/service.py:788` |
| **transaction boundary** | **Post-commit.** Domain `db.commit()` at :779, `db.refresh`, `sync_candidate_links` — then automation in **new** implicit TX |
| **mutation** | Candidate row inserted; optional `events.emit_event(candidate.created)` already committed |
| **trigger** | `candidate.created` |
| **sync/async** | Synchronous `await` in request handler |
| **error consequences** | `try/except` → `db.rollback()` — **candidate persists, automation silently lost** |
| **side effects** | `ActivityLog` `automation.rule_fired`; `reminder_tasks.create_reminder` per matched rule; trial cap increment |
| **target replacement** | Outbox row in **same TX as candidate insert** (move before :779 commit); consumer → Reaction Orchestrator |
| **migration priority** | **P1** — high volume; also duplicates `emit_event` + `uos_auto_activities` (see §9) |

### CS-02 — `candidate.stage_changed`

| Field | Value |
|-------|-------|
| **caller** | `update_candidate_full()` stage branch — `candidates/service.py:1539` |
| **transaction boundary** | **Post-commit** of stage PATCH; separate try/TX for automation |
| **mutation** | `candidate.stage` updated; `sync_candidate_links`; pipeline doc gate already enforced earlier in same request |
| **trigger** | `candidate.stage_changed` |
| **sync/async** | Synchronous `await` in request handler |
| **error consequences** | Rollback of automation TX only — **stage change persists** |
| **side effects** | Same as CS-01; followed by Telegram notify + `uos_auto_activities.ensure_candidate_stage_follow_up_task` |
| **target replacement** | Outbox on stage mutation TX; event payload: `stage_from`, `stage_to`, entity revision |
| **migration priority** | **P0** — overlaps future `candidate.requirements_evaluated` slice; **must not dual-fire** with new engine |

### CS-03 — `lead.processed` (services / client intake)

| Field | Value |
|-------|-------|
| **caller** | `_complete_sales_intake_lead()` — `leads/service/_processing.py:201` |
| **transaction boundary** | **Post-commit** — lead status `processed` committed at :186 |
| **mutation** | Lead → `status=processed`, company outcome; `_emit_lead_event` already in prior TX |
| **trigger** | `lead.processed` |
| **sync/async** | Synchronous in ingest request |
| **error consequences** | Rollback automation TX — lead stays processed |
| **side effects** | Reminders + ActivityLog; `_pick_lead_assignee_id` runs **before** rules (separate orchestration) |
| **target replacement** | Outbox in lead-processed TX; consolidate assignee + automation via orchestrator templates |
| **migration priority** | **P2** |

### CS-04 — `lead.processed` (agency / meta convert)

| Field | Value |
|-------|-------|
| **caller** | `process_normalized_lead()` agency path — `_processing.py:1430` |
| **transaction boundary** | **Post-commit** — explicit comment :1390 «Commit lead status update before automation» |
| **mutation** | Lead processed + candidate created; `apply_lead_terminal_cleanup` committed separately |
| **trigger** | `lead.processed` |
| **sync/async** | Synchronous in ingest request |
| **error consequences** | Rollback automation TX — lead+candidate persist; `_emit_lead_event` runs **after** at :1453 |
| **side effects** | Reminders + ActivityLog; duplicate notification path via `_emit_lead_event` |
| **target replacement** | Single outbox event after convert TX; merge with CS-03 template later |
| **migration priority** | **P2** |

### CS-05 — `lead.pipeline.stage_changed`

| Field | Value |
|-------|-------|
| **caller** | `run_lead_stage_change_automations()` — `pipeline_hooks.py:176`; invoked from `leads/router.py:711`, `:1113` |
| **transaction boundary** | **Post-commit** — docstring :140 «after stage update transaction has been committed» |
| **mutation** | Lead pipeline stage updated (committed by caller) |
| **trigger** | `lead.pipeline.stage_changed` |
| **sync/async** | Synchronous; caller also runs `events.emit_event(lead.pipeline.stage_changed)` separately (:116) |
| **error consequences** | Rollback automation TX — stage persists |
| **side effects** | Reminders + ActivityLog; parallel `emit_event` notification |
| **target replacement** | One outbox fact event; orchestrator replaces both `run_automation_rules` and duplicate emit |
| **migration priority** | **P2** |

### CS-06 — `candidate.risk_band` (indirect, not `run_rules`)

| Field | Value |
|-------|-------|
| **caller** | `risk_intel_v1` hourly job → `run_candidate_risk_band_rules()` — `automation_rules.py:267` |
| **transaction boundary** | Background batch; own DB session per tenant batch |
| **mutation** | None (reads shadow risk rows) |
| **trigger** | `candidate.risk_band` |
| **sync/async** | **Async job** (scheduled) |
| **error consequences** | Per-row skip; dedupe via `was_rule_fired_for_candidate_since` (24h window) |
| **side effects** | Reminders for high/critical bands |
| **target replacement** | Domain event `candidate.risk_band_detected` from risk job → orchestrator; migrate **after** slice 1 |
| **migration priority** | **P3** |

### CS-07 — `lead.qualification` (parallel runner, same table)

| Field | Value |
|-------|-------|
| **caller** | `pick_vacancy_via_qualification_rules()` — `lead_qualification_rules.py`; called from `_helpers.py:505` during ingest |
| **transaction boundary** | **Inside** ingest TX (pre-commit) — **different from CS-03/04/05** |
| **mutation** | Sets vacancy/recruiter routing on lead **before** convert |
| **trigger** | `lead.qualification` (AutomationRule rows; **not** via `run_rules` — explicitly excluded at :366) |
| **sync/async** | Synchronous in ingest |
| **error consequences** | Part of ingest failure surface |
| **side effects** | Vacancy assignment, optional recruiter stamp, audit `lead.qualification_rule_matched` |
| **target replacement** | Platform automation template + fact event at ingest; **deprecate separate runner** |
| **migration priority** | **P1** — duplicate condition matcher `_matches_conditions` |

### Call site summary

| ID | Trigger | TX timing | Silent fail risk | Priority |
|----|---------|-----------|------------------|----------|
| CS-01 | `candidate.created` | post-commit | yes | P1 |
| CS-02 | `candidate.stage_changed` | post-commit | yes | **P0** |
| CS-03 | `lead.processed` | post-commit | yes | P2 |
| CS-04 | `lead.processed` | post-commit | yes | P2 |
| CS-05 | `lead.pipeline.stage_changed` | post-commit | yes | P2 |
| CS-06 | `candidate.risk_band` | job | partial dedupe | P3 |
| CS-07 | `lead.qualification` | **in-TX** | ingest fails | P1 |

---

## 9. Hidden automation paths (local orchestration audit)

Paths that **execute automation-like behavior** without going through Reaction Orchestrator:

### 9.1 Stage changes (domain gate — keep as evaluator, not automation)

| Path | File | Verdict |
|------|------|---------|
| `enforce_pipeline_doc_forward_block` | `candidate_doc_pipeline_guard.py` | **Keep** — domain gate; emits no automation |
| `_validate_stage_transition` | `candidates/service.py` | **Keep** — lifecycle guard |
| `candidate_risk_stage_gate` | `candidate_risk_stage_gate.py` | **Keep** — risk policy |
| Bulk stage update | `bulk_update_stage()` | **Keep** — manual command; future outbox on change |

### 9.2 Task / activity creation (migrate → actions)

| Path | File | Side effect | Verdict |
|------|------|-------------|---------|
| `uos_auto_activities.ensure_candidate_created_call_task` | after CS-01 | Auto call task | **Migrate** → `activity.create` action |
| `uos_auto_activities.ensure_candidate_stage_follow_up_task` | after CS-02 | Follow-up task | **Migrate** → template |
| `automation_rules.execute_automation_rule` | `create_reminder` | Reminder row | **Migrate** → `activity.create` |
| `schedule_document_expiry_reminders` | `reminders.py` | Expiry reminders | **Migrate** — event `document.expiring` (currently dead trigger) |

### 9.3 Owner assignment (migrate → actions)

| Path | File | Verdict |
|------|------|---------|
| `_pick_lead_assignee_id` | `leads/service/_helpers.py` | **Migrate** → `assignment.assign_owner` |
| `lead_distribution.pick_assignee_user_id_for_ingest` | `lead_distribution.py` | **Reuse** behind action + entitlement |
| `team_assignee_auto` | `team_assignee_auto.py` | **Reuse** — smart ops bundle gated |
| `lead_qualification_rules.set_recruiter_id` | qualification actions JSON | **Migrate** with CS-07 |

### 9.4 Notifications (keep emit layer; decouple from automation)

| Path | File | Verdict |
|------|------|---------|
| `events.emit_event` | candidate.created, lead.pipeline.stage_changed | **Keep** — Activity/Notification layer (ADR-012) |
| `_emit_lead_event` | leads processing | **Keep** — separate from automation |
| `candidate_tg_notifications` | stage changed telegram | **Keep** — channel adapter |
| `next_action` publisher | `platform/next_action/` | **Extend** — `suggested` mode |

### 9.5 Cross-module entity creation

| Path | File | Verdict |
|------|------|---------|
| Lead → candidate convert | `process_normalized_lead` | **Keep** domain command; emit outbox after |
| Handoffs API | `api/v1/handoffs.py` | **Keep**; future `candidate.execute_transfer` action |
| HR employee create from recruitment | — | **Must** go through Action Registry only |

### 9.6 Background jobs / scheduler

| Path | File | Verdict |
|------|------|---------|
| `risk_intel_v1` hourly | CS-06 | Migrate P3 |
| `arq_worker` / queue | `core/arq_worker.py` | Outbox dispatcher candidate |
| Document expiry engine | `document_expiry_engine.py` | Fact publisher candidate |

### 9.7 Frontend feature gates (must read CapabilityPreview later)

| Path | Pattern | Verdict |
|------|---------|---------|
| `PlanLimitModalContext` | API error → upsell modal | **Replace** with CapabilityPreview DTO for automation features |
| `usePlanLimitModal` | Used in AutomationsHub, Funnels, Comms | **Extend** — not SSOT for capability availability |
| Hardcoded disabled buttons | various | **Audit during 3A-6** — must show `reason_code` |

### 9.8 Webhooks / external integrations

| Path | File | Verdict |
|------|------|---------|
| `core/webhooks.py` | Outbound webhooks | **Out of slice 1** — no webhook builder |
| Communications webhooks | `communications/routes/webhooks.py` | Inbound — unrelated |
| Deluge | **Not found** in backend | N/A |

---

## 10. Migration coexistence strategy

Legacy `automation_rules` and new Reaction Orchestrator **coexist during migration**. Rules:

| Rule | Requirement |
|------|-------------|
| **Feature flag per trigger** | `platform.automation.outbox.{trigger}` — e.g. `candidate.requirements_evaluated` enabled per tenant/env |
| **No dual execution** | When flag ON for trigger T: legacy `run_automation_rules(T)` **must not run** (guard at call site or removed branch) |
| **Shadow mode** | Optional `platform.automation.shadow.{trigger}` — orchestrator **logs decision only**, zero side effects; compares with legacy intent |
| **Rollback** | Flag OFF → legacy consumer only; outbox events for T may be **drained but not consumed** or left for replay |
| **Trigger-by-trigger cutover** | Order: `candidate.requirements_evaluated` (new) → `candidate.stage_changed` (CS-02 P0) → lead triggers → risk band |
| **Idempotency** | Both paths must share idempotency key space during shadow to detect double-fire |

**CS-02 critical:** stage_changed legacy **must be disabled** before enabling automatic stage transition template — highest double-fire risk.

---

## 11. Existing entity ownership

| Entity | Current state | Decision | Notes |
|--------|---------------|----------|-------|
| **`automation_rules` table** | Tenant CRUD; free-form `conditions_json` with dot-path domain matching | **Retain table, evolve contract** | Add validation: conditions **only** §14.4 sources. **Do not** store document/transfer/qualification checks. New rules via templates; old rows **frozen** per trigger at cutover |
| **Trigger codes (`TRIGGERS`)** | 7 codes in `automation_rules.py` | **Migrate** | Map to Event Contract Registry; legacy aliases during coexistence |
| **Action codes (`create_reminder`)** | JSON in `actions_json` | **Migrate** → Action Registry | Ad-hoc JSON **deprecated** for new rules |
| **Execution history** | `ActivityLog` actions `automation.*`; API `automation_log.py` | **Extend** | New `automation_executions` table SSOT; AutomationLogPage reads union during migration → cut to executions only |
| **UI AutomationsHub** | Policy links + rules editor | **Extend** → Automation Center | Retain routes; add Active/Recommended/Locked/history sections (3A-7) |
| **AutomationRulesPage** | Tenant rule CRUD | **Retain limited** | Slice 1: templates toggle only; **no arbitrary condition builder** |
| **AutomationLogPage** | ActivityLog query | **Extend** | Add execution lifecycle + correlation ids |
| **`lead_qualification_rules.py`** | Parallel runner on `AutomationRule` | **Deprecate runner** | Migrate to platform template; delete separate `_matches_conditions` path after CS-07 cutover |
| **`run_automation_rules()` service** | Legacy executor | **Deprecate per trigger** | Empty stub returns 0 when flag ON; remove call sites trigger-by-trigger |

**Hard rule:** do **not** extend `conditions_json` schema to accept domain policy fields. If a condition needs document completeness — that belongs in evaluator → fact event payload.

---

## 12. 3A-0 definition of done

- [x] Architecture inventory (§2–§4)
- [x] Call site classification with TX boundary + side effects (§8)
- [x] Hidden automation paths audit (§9)
- [x] Coexistence strategy (§10)
- [x] Entity ownership decisions (§11)
- [x] PR plan aligned with ADR-019

**3A-0: COMPLETE.** Proceed to **3A-1**.

---

## 13. 3A-1 scope preview (for handoff)

Minimal scope — **no cross-module actions**:

1. Canonical **event envelope** (`event_id`, `correlation_id`, `causation_id`, `occurred_at`, payload)  
2. **Event Contract Registry** (schema per event type)  
3. **Transactional outbox table** (`domain_event_outbox`)  
4. **Publisher API** for domain services (insert-only, same TX)  
5. **Outbox dispatcher** (worker)  
6. **Idempotent consumer skeleton** (Reaction Orchestrator stub — log only)  
7. **Retry + dead-letter** states on outbox rows  
8. **Audit correlation** via `event_id` / `correlation_id` / `causation_id`  
9. **First publisher:** `candidate.requirements_evaluated` from RequirementEvaluationService only  
10. **No real cross-module actions** in 3A-1  

---

## References

- ADR-018: Requirement Policy & Evaluation Model
- ADR-004: Billing Events
- ADR-012: Activity & Notification Operating Layer
- ADR-002: Recruitment ↔ HR boundary
- PR 2B reuse audit: [`requirement-evidence-model-p0.md`](requirement-evidence-model-p0.md)
