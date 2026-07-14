# ADR-019: Automation, Capability & Entitlement Control Plane

**Status:** Accepted (architectural direction)  
**Date:** 2026-07-13  
**Layer of change:** Domain | Life Cycle | Constitution  
**Start / Optimize / Scale:** Start (first vertical slice), then Optimize  
**Authors:** Platform architecture  
**Related:** [ADR-016](ADR-016-requirement-evidence-document-separation.md), [ADR-004](ADR-004-five-product-modules-and-billing-events.md), [ADR-012](ADR-012-activity-notification-operating-layer.md), [ADR-002](ADR-002-modular-recruitment-hr-boundary.md), [ADR-005](ADR-005-three-level-settings-hierarchy.md), [existing-runtime-reuse-review-automation-plane.md](../platform/existing-runtime-reuse-review-automation-plane.md)

> **Prerequisite:** ADR-018 PR 2B-3 (Requirement Evaluation cutover).  
> **Terminology (обязательно):** компонент, исторически называемый «Automation Engine», — это **Reaction Orchestrator** (оркестратор реакций). Он **не** управляет бизнес-логикой и **не** вычисляет domain truth. Он получает уже опубликованные факты и решает, какую зарегистрированную реакцию выполнить.

---

## 1. Какой бизнес-процесс изменяется?

Операционная платформа HostFlow: после выполнения требований, квалификации заявки, готовности к transfer, завершения услуги или billing milestone система должна **предсказуемо реагировать** — сменить этап воронки, открыть transfer, создать billing event, преобразовать заявку, назначить ответственного, отправить уведомление.

Сегодня реакции разбросаны: tenant `automation_rules` с узким набором triggers/actions, прямые вызовы `run_automation_rules()` из module services, plan gates без feature-level capabilities, disabled UI без объяснения причины.

**Цель:** один платформенный **Automation & Capability Control Plane** — единый центр управления автоматизациями, доступностью функций и коммерческими entitlements, без дублирования domain policy.

---

## 2. Какая Business Entity затрагивается?

| Entity | Класс | Owner Domain |
|--------|-------|--------------|
| DomainEvent (contract) | Infrastructure | Platform |
| AutomationRule | Business (platform config) | Platform |
| AutomationTemplate | Business (platform catalog) | Platform |
| AutomationExecution | Support (audit/runtime) | Platform |
| CapabilityDefinition | Infrastructure (registry) | Platform |
| TenantCapability / ModuleEntitlement | Support | Platform (Tenant billing) |
| CapabilityPreview | Support (projection) | Platform |
| ActionDefinition | Infrastructure (registry) | Platform |
| BillingEvent | Business | Finance (source modules emit) |

Domain entities (Candidate, Application, ServiceOrder, Employee) **не меняют ownership** — модули остаются владельцами бизнес-сущностей.

---

## 3. Существующая Entity или новая? Почему?

**Evolution check:**

- [x] Можно использовать **существующую** Business Entity (`AutomationRule` table — evolve)
- [x] Можно расширить **существующий** Life Cycle (stage transition, transfer, conversion)
- [x] Можно использовать **существующий** Workspace (Automations Hub → Automation Center)

**Ответ:** эволюция platform layer; новые operational сущности — Capability Registry, Action Registry, Domain Event contract, AutomationExecution.

**Почему текущая модель не подходит:** `automation_rules` — tenant-local CRUD без capability/entitlement layer, без cross-module actions, без execution modes, без единого event bus. Module services напрямую вызывают automation runner → нарушение границ модулей.

---

## 4. Life Cycle

**AutomationExecution lifecycle** (Reaction Orchestrator runtime):

```
detected → suggested | awaiting_approval | queued → running
  → succeeded | failed | cancelled | skipped | superseded
```

| State | Meaning |
|-------|---------|
| `detected` | Event matched a rule; not yet surfaced to user |
| `suggested` | NBA / prompt shown (`execution_mode=suggested`) |
| `awaiting_approval` | In approval queue |
| `queued` | Scheduled for execution (retry/backoff) |
| `running` | Action in progress |
| `succeeded` | Action completed |
| `failed` | Action error (retry per policy) |
| `cancelled` | User or admin cancelled |
| `skipped` | Capability/entitlement/permission blocked |
| `superseded` | Stale — newer evaluation/event invalidated this execution |

**Особенно важен `superseded`:** старое предложение («перевести кандидата») становится неактуальным после нового evaluation result (например, документ истёк).

**AutomationRule lifecycle:**

```
draft → enabled → disabled → archived
```

**Capability (tenant view):**

```
locked (module/plan/role/config) → previewable → available → active
```

**Module activation lifecycle** (on purchase/connect):

```
purchased → entitled → activating → active → deactivated
```

**Запрещённые переходы:**

- Automation **не** переводит domain entity в состояние, запрещённое domain evaluator
- Cross-module action без registered public action — **запрещён**
- Invoice creation напрямую из Recruitment/Services — **запрещён** (ADR-004)

---

## 5. Owner Domain

| Entity | Owner Domain | Меняется ownership? |
|--------|--------------|---------------------|
| RequirementEvaluation, Transfer readiness | Platform evaluators (domain policy) | нет |
| AutomationRule, Template, Execution | Platform Reaction Orchestrator | **да** — platform SSOT |
| CapabilityDefinition, ActionDefinition | Platform registry | **да** — new |
| Tenant entitlements | Platform / Tenant billing | evolve |
| Candidate stage, HR employee, Invoice | Respective modules | нет — только через actions |

**Главный принцип:**

> **Domain policy определяет истину.**  
> **Automation policy определяет реакцию на эту истину.**

**Reaction Orchestrator** (не «второй policy engine») **не решает**, выполнено ли требование. Он получает опубликованный факт (`requirement fulfilled`, `transfer_ready`, `application qualified`, …) и выполняет зарегистрированный action — после проверки capability, entitlement, permission и актуальности evaluation result.

---

## 6. Domain Contract

| Domain | Изменение контракта |
|--------|---------------------|
| **Platform** | Event contract + outbox, Action Registry, Capability Registry, Reaction Orchestrator |
| **Recruitment** | Публикует `candidate.*`, `application.*` events; потребляет automation suggestions; **не** вызывает HR/Finance internals |
| **HR** | Регистрирует `hr.create_employee` action; публикует `employee.*` events |
| **Services / Finance** | Billing milestones → `invoiceable_event.created`; Finance — единственный создатель invoices (ADR-004) |
| **Document Hub** | Публикует `document.*` facts; не интерпретирует requirements |
| **Requirement Evaluation** (ADR-018) | Публикует `candidate.requirements_evaluated` с `can_transition`, blockers |

**Cross-module boundary:** модуль **не** вызывает internal service другого модуля. Только domain event publish или public action invoke.

---

## 7. Canonical State

| Concern | SSOT |
|---------|------|
| Requirement fulfillment | RequirementEvaluationService (ADR-018) |
| Transfer readiness | TransferPolicyResolver |
| Billing milestone | Contract/Billing Policy evaluator |
| Qualification | Qualification Policy evaluator |
| **What reaction to attempt** | **Reaction Orchestrator** |
| **What tenant can use** | **Capability Registry + Entitlement Service** |
| **What user can configure/run** | **Permission rules (RBAC)** |

**Риск параллельных истин:** per-module automation silos, frontend-only feature flags, plan checks в UI без registry — **запрещены** как SSOT.

---

## 8. Transitions

| Transition | Trigger | Side effects | Новый? |
|------------|---------|--------------|--------|
| Requirements evaluated | Document approved / policy re-run | Publish `candidate.requirements_evaluated` | evolve |
| Stage auto-transition | Event + automation template + capability | `candidate.change_stage` action | **да** |
| Transfer opened | `candidate.transfer_ready=true` | `candidate.open_transfer`; UI capability preview if HR locked | **да** |
| Transfer executed | Approval or automatic mode | `candidate.execute_transfer` → `hr.create_employee` | evolve |
| Application converted | `application.qualified=true` | `sales.convert_application` | **да** |
| Invoiceable event | Service/contract milestone | `finance.create_invoiceable_event` | **да** |
| Module activated | Purchase / admin enable | Entitlements + capabilities + templates + consumers | **да** |

---

## 9. History

- [x] AutomationExecution — append-only audit (success/failure, idempotency key, actor, override)
- [x] Manual override — logged with reason, actor, prior automation state
- [x] Capability changes — tenant entitlement history
- [ ] Migration: existing `automation_rules` rows → platform AutomationRule schema (Phase 1)

---

## 10. Workspace

| Элемент | Тип | Domain Workspace | Новый? |
|---------|-----|------------------|--------|
| **Automation Center** | View + Command | Platform settings | evolve from AutomationsHub |
| Active / Recommended / Locked automations | View | Automation Center | **да** |
| Execution history / Failed runs / Approval queue | View | Automation Center | **да** |
| Capability map | View | Automation Center | **да** |
| In-context automation hints | View | Entity Workspace (candidate, application, …) | **да** |
| **CapabilityPreview** DTO | View | **Platform** — all module workspaces consume same read model | **да** |

**Workspace хранит state?** нет — только projections из Reaction Orchestrator + Capability Registry.

**CapabilityPreview** — platform surface, не Recruitment-only banner.

**In-context example:**

> «После одобрения legal stay HostFlow автоматически откроет transfer в HR.»  
> «HR-модуль не подключён. Кандидат уже готов к transfer.»

---

## 11. Start / Optimize / Scale

**Класс:** Start — первый вертикальный срез на Recruitment transfer path; затем Optimize.

**Обоснование:** Не строить универсальный конструктор. Доказать пять опор (evaluator → event → automation → capability → entitlement) на одном сценарии.

---

## 12. Почему существующая модель не подходит?

Tenant `automation_rules` решает локальные задачи (reminders, lead routing) но не образует control plane: нет separation domain vs automation rules, нет capability registry, нет previewable upsell, нет cross-module action registry, нет execution modes. Plan gates (`plan_feature_gates.py`) знают про лимиты automation rules, но не про feature capabilities (`recruitment.to_hr_transfer`). Прямые вызовы automation из `candidates/service.py` создают скрытые coupling между модулями.

---

## 13. Альтернативы

| Альтернатива | Плюсы | Минусы | Отклонена |
|--------------|-------|--------|-----------|
| A. Per-module automation (Recruitment rules, HR rules, …) | Быстрый local MVP | Множество SSOT; cross-module хаос | **да** |
| B. Extend `automation_rules` as-is | Минимальный diff | Не масштабируется на capabilities/billing/transfer | **да** |
| C. External workflow engine (Temporal/n8n only) | Mature orchestration | Не решает entitlement/capability/upsell; vendor lock-in | **да** (как sole solution) |
| D. **Platform Automation & Capability Engine** (этот ADR) | Единый control plane; module independence | Требует event bus + registries | **выбрано** |

---

## 14. Решение

### 14.1 Reaction Orchestrator (не policy engine)

Рабочее название platform layer:

**HostFlow Automation & Capability Control Plane**

Ключевой runtime-компонент — **Reaction Orchestrator** (в коде/доках допустим alias `AutomationEngine`, но роль всегда «оркестратор реакций», не «движок бизнес-логики»).

Пять опор:

1. **Domain evaluators** определяют факты  
2. **Event contracts + transactional outbox** публикуют изменения атомарно с domain state  
3. **Reaction Orchestrator** решает, какую реакцию запустить  
4. **Capability Registry** определяет, что функция **существует** в платформе  
5. **Entitlement Service** определяет, что tenant **имеет право** ею пользоваться  

**Capability ≠ Entitlement:**

| Concept | Question | Example |
|---------|----------|---------|
| **Capability** | Функция существует в платформе? | `recruitment.to_hr_transfer` зарегистрирована |
| **Entitlement** | Tenant купил / подключил? | HR module active on Pro plan |

### 14.2 Четыре вида правил (не смешивать)

| Layer | Определяет | Examples | Owner |
|-------|------------|----------|-------|
| **1. Domain rules** | Истину | docs fulfilled, contract complete, transfer ready, billing milestone | Requirement Policy, Transfer Policy, Billing Policy, … |
| **2. Automation rules** | Реакцию | change stage, open transfer, create task, draft invoice event, convert application | Platform Reaction Orchestrator |
| **3. Capability rules** | Что доступно tenant | HR module, Finance, cross-module automation, advanced workflow | Capability Registry |
| **4. Permission rules** | Кто может | enable automation, manual run, cancel, override, edit, view audit | RBAC |

### 14.3 Domain Event Contract — факты, не команды

Modules publish **facts** through platform event contract + **transactional outbox** (same DB transaction as domain state change).

**Правило: событие ≠ команда.** Событие описывает то, что **уже произошло** или **уже вычислено**. Решение «что делать» — только в Reaction Orchestrator → Action Registry.

| Kind | Example | Role |
|------|---------|------|
| **Fact event** | `candidate.transfer_ready` | Readiness computed; payload includes evaluation refs |
| **Fact event** | `candidate.requirements_evaluated` | Evaluation DTO summary |
| **Action** | `candidate.open_transfer` | Registered public command |
| **Action** | `candidate.execute_transfer` | Registered public command |
| **Forbidden** | `candidate.should_be_transferred` | Mixes fact and decision — **запрещено** |

Canonical fact events (initial):

```
candidate.created
candidate.stage_changed
candidate.requirements_evaluated
candidate.transfer_ready
candidate.transferred
application.qualified
application.converted
service_order.completed
contract.milestone_reached
employee.onboarding_completed
invoiceable_event.created
module.activated
module.deactivated
document.expiring
lead.processed
lead.qualification
```

Existing triggers in `automation_rules.TRIGGERS` — **subset**; migrate to canonical names.

**Event payload (minimum):** `event_id`, entity type/id, `owner_company_id`, tenant_id, fact DTO, `occurred_at`, `correlation_id`, evaluation lineage (see §14.4).

**Transactional outbox (обязательно):**

Domain mutation and event record **must** commit in one transaction. Async publisher reads outbox and delivers to Reaction Orchestrator.

```
BEGIN;
  UPDATE candidate …;
  INSERT domain_event_outbox (event_type, payload, …);
COMMIT;
→ outbox worker → Reaction Orchestrator
```

**Запрещено:** publish event после commit обычным post-hook без outbox — при сбое получится изменённый domain state без automation event.

### 14.4 Automation conditions — только реакционные фильтры

**Reaction Orchestrator не имеет произвольных domain conditions.**

В `AutomationRule.conditions` допустимы **только**:

| Source | Examples |
|--------|----------|
| Published **event payload** fields | `can_transition=true`, `transfer_ready=true` |
| Stored **evaluation result** refs | `evaluation_result_id`, `policy_version` match |
| **Capability** result | `recruitment.to_hr_transfer` available |
| **Entitlement** result | HR module entitled |
| **Permission** result | user may execute action |
| **Technical params** | scheduled date, assignee id, execution mode override |

**Запрещено заново проверять в automation conditions:**

- комплектность документов  
- readiness к transfer  
- qualification заявки  
- выполнение контракта  
- billing milestone  

Иначе Reaction Orchestrator превратится во **второй policy engine**. Domain re-evaluation — только через повторный publish fact event от domain evaluator.

### 14.5 Stale evaluation protection (freshness gate)

Каждая `AutomationExecution` и каждый critical action **must** reference:

| Field | Purpose |
|-------|---------|
| `source_entity_type` / `source_entity_id` | Candidate, application, … |
| `evaluation_type` | e.g. `requirement_evaluation`, `transfer_readiness` |
| `evaluation_result_id` or `evaluation_version` | Pin to specific result |
| `entity_revision` | Optimistic lock / row version of source entity |
| `source_event_id` | Event that triggered this execution |

**Before critical action** (`candidate.change_stage`, `candidate.open_transfer`, `candidate.execute_transfer`, …) Reaction Orchestrator **must** verify evaluation result is still current:

1. Re-read latest evaluation for same `evaluation_type` + entity  
2. Compare `evaluation_result_id` / fingerprint / `entity_revision`  
3. If stale → mark execution `superseded`; do **not** run action  

**Failure scenario prevented:**

1. Candidate was transfer-ready → execution queued  
2. Document expires before run  
3. Without freshness gate → transfer opens incorrectly  

### 14.6 AutomationRule model

| Field | Purpose |
|-------|---------|
| `trigger` | Canonical domain event |
| `conditions` | Reaction filters only (§14.4) — **not** domain re-evaluation |
| `action` | Registered action code |
| `target` | Entity reference / parameters |
| `required_capability` | Capability code gate |
| `execution_mode` | `manual` \| `suggested` \| `approval_required` \| `automatic` |
| `retry_policy` | Backoff / max attempts |
| `idempotency_key_template` | Dedup |
| `ownership` | Module + tenant scope |
| `audit` | Required metadata |
| `version` | Template/rule version |

**Example:**

> When `candidate.requirements_evaluated` and payload `can_transition=true`, run `candidate.change_stage` (mode: `suggested` → later `automatic`).

### 14.7 Action Registry

Public actions only. Examples:

| Action code | Owner module | Required capability |
|-------------|--------------|---------------------|
| `candidate.change_stage` | recruitment | `recruitment.pipeline` |
| `candidate.open_transfer` | recruitment | `recruitment.to_hr_transfer` |
| `candidate.execute_transfer` | recruitment | `recruitment.to_hr_transfer` |
| `hr.create_employee` | hr | `hr.employee_onboarding` |
| `sales.convert_application` | recruitment/leads | `sales.application_conversion` |
| `finance.create_invoiceable_event` | finance | `finance.invoice_generation` |
| `notifications.send` | platform | `automation.conditional_actions` |
| `assignment.assign_owner` | platform | `automation.cross_module` |
| `activity.create` | platform (ADR-012) | — |

Each action defines: input contract, required capability, permission, idempotency key, rollback semantics, audit metadata.

**Prohibited:**

- Automation directly updates `candidate.stage` in DB  
- Recruitment directly creates HR employee  
- Sales directly creates invoice  
- Frontend orchestrates cross-module sequence  

### 14.8 Capability Registry

Canonical capability codes (initial):

```
recruitment.pipeline
recruitment.automatic_stage_transition
recruitment.to_hr_transfer
hr.employee_onboarding
sales.application_conversion
finance.invoice_generation
services.billing_milestones
automation.cross_module
automation.scheduled_rules
automation.conditional_actions
```

**UI reads Capability Registry + tenant entitlements** — not hardcoded menu logic.

### 14.9 Module activation lifecycle

On module purchase/connect:

1. Create module entitlement  
2. Activate capabilities  
3. Enable related automation templates  
4. Register allowed actions  
5. Open transfer targets  
6. Register event consumers  
7. Expose UI surfaces  
7. Apply module-specific policies  

Module adds **capability package**, not just menu item.

### 14.10 CapabilityPreview — платформенный read model

**CapabilityPreview — не Recruitment-only баннер.** Единый platform read model, используемый во всех модулях (Recruitment, HR, Fleet, Services, Finance).

| Field | Purpose |
|-------|---------|
| `capability_code` | Какая функция (`recruitment.to_hr_transfer`, …) |
| `availability` | `available` \| `locked` \| `blocked` \| `forbidden` |
| `reason_code` | Почему недоступна (`module_missing`, `plan_tier`, `role`, `config`, `domain_conditions`) |
| `title` | Пользовательское название |
| `value_statement` | Что даст функция пользователю |
| `current_context` | Что уже подготовлено в текущем кейсе (данные, evaluation summary) |
| `unlock_requirement` | Модуль, тариф или конфигурация для разблокировки |
| `cta` | `connect_module` \| `request_demo` \| `configure` \| `upgrade_plan` |
| `target_action` | Какой action станет доступен после unlock |

**Availability reasons (не смешивать):**

| `reason_code` | User-facing pattern |
|---------------|---------------------|
| `role` | «Недоступно по роли» |
| `config` | «Настройте …» |
| `plan_tier` | «Доступно на тарифе Pro» |
| `module_missing` | «Подключите HR-модуль» + preview + CTA |
| `domain_conditions` | «Пока недоступно: …» (from evaluator — **not** automation) |

Example:

> «Кандидат готов к передаче в HR. Подключите HR-модуль, чтобы автоматически создать карточку сотрудника, перенести документы и запустить onboarding.»

UI **reads** `CapabilityPreview` DTO — не hardcodes upsell copy per module.

### 14.11 Automation Templates

Canonical templates (tenant enables/configures, does not rewrite domain policy):

| Template | Trigger | Action | Default mode |
|----------|---------|--------|--------------|
| Auto stage after requirements | `candidate.requirements_evaluated` | `candidate.change_stage` | `suggested` |
| Open transfer when ready | `candidate.transfer_ready` | `candidate.open_transfer` | `automatic` |
| HR case after transfer | `candidate.transferred` | `hr.create_employee` | `approval_required` |
| Invoiceable after service | `service_order.completed` | `finance.create_invoiceable_event` | `approval_required` |
| Convert qualified application | `application.qualified` | `sales.convert_application` | `manual` |
| Round-robin assign | `lead.processed` | `assignment.assign_owner` | `automatic` |
| Document expiry follow-up | `document.expiring` | `activity.create` + `notifications.send` | `automatic` |

Tenant may: enable/disable, tune parameters, assign executor, change notifications, switch execution mode.

### 14.12 Execution modes

| Mode | Behavior |
|------|----------|
| `manual` | Show action; user initiates |
| `suggested` | NBA / prompt: «All conditions met. Proceed?» |
| `approval_required` | Queue in Automation Center approval |
| `automatic` | Execute when conditions + capability + permission pass |

Rollout path: `suggested` → `approval_required` → `automatic`.

### 14.13 Commercial model (reads entitlement, not hardcoded)

| Tier | Capabilities (examples) |
|------|-------------------------|
| Base | manual transitions, suggested automations, basic notifications |
| Pro | automatic stage transitions, approval workflows, transfer automations |
| Advanced | cross-module automation, billing triggers, custom templates |
| Enterprise | custom policies, custom event actions, advanced audit, external integrations |

Pricing lives in Entitlement Service / Stripe — **not** in automation rule code.

### 14.14 Platform storage (target)

Platform-level tables/services:

- `automation_registry` / `automation_rules`  
- `automation_executions`  
- `automation_templates`  
- `capability_registry`  
- `tenant_entitlements` / `module_capabilities`  
- `domain_event_outbox`  
- `event_contracts`  
- `action_registry`  

Modules supply: events, actions, templates, capability declarations, policy result contracts.

### 14.16 Migration coexistence (legacy + new runtime)

During trigger-by-trigger cutover:

| Rule | Requirement |
|------|-------------|
| Feature flag per trigger | `platform.automation.outbox.{event_type}` |
| No dual execution | Flag ON → legacy `run_automation_rules(trigger)` **disabled** at call site |
| Shadow mode | `platform.automation.shadow.{event_type}` — compare decisions, **zero side effects** |
| Rollback | Flag OFF → legacy path only |
| Cutover order | New events first (`candidate.requirements_evaluated`) → CS-02 `stage_changed` (P0) → lead triggers → risk band |

See audit §10: [`existing-runtime-reuse-review-automation-plane.md`](../platform/existing-runtime-reuse-review-automation-plane.md).

### 14.17 Existing entity ownership

| Entity | Decision |
|--------|----------|
| `automation_rules` table | **Retain, evolve contract** — validate conditions §14.4 only; no domain matching in JSON |
| Trigger/action codes | **Migrate** to Event/Action Registry; legacy aliases during coexistence |
| `ActivityLog` automation.* | **Extend** → `automation_executions` SSOT; AutomationLogPage union during migration |
| AutomationsHub / RulesPage | **Extend** → Automation Center; no arbitrary builder in slice 1 |
| `lead_qualification_rules.py` | **Deprecate runner** → platform template |

See audit §11.

### 14.18 Reuse of existing runtime

See audit: [`existing-runtime-reuse-review-automation-plane.md`](../platform/existing-runtime-reuse-review-automation-plane.md).

| Asset | Verdict |
|-------|---------|
| `automation_rules` + UI hub | Extend |
| `plan_feature_gates` | Reuse as entitlement adapter |
| `RequirementEvaluationService` | Reuse as event source |
| `TransferPolicyResolver` | Reuse as event source |
| Direct `run_automation_rules()` in modules | Replace with event publish |
| Domain event bus | New |
| Capability / Action Registry | New |

---

## Implementation Contract — Vertical Slice 1

**Goal:** доказать **полный контур**, не просто появление события:

```
Evaluation result
  → transactional outbox event
  → Reaction Orchestrator decision
  → capability + entitlement check
  → suggested or automatic action
  → audit trail
  → CapabilityPreview при locked capability
```

**Scenario:** Requirement Evaluation → transfer-ready → stage suggestion → HR transfer (or contextual upsell if HR inactive).

### PR plan (обязательный порядок)

| PR | Content | Status |
|----|---------|--------|
| **3A-0** | Code audit §8–§11: call sites, hidden paths, coexistence, ownership | **done** |
| **3A-1** | Event envelope + Contract Registry + outbox + publisher API + dispatcher + consumer skeleton + retry/DLQ; publisher: `candidate.requirements_evaluated` only; **no cross-module actions** | **next** |
| **3A-2** | Capability Registry + entitlement adapter + `availability` / `reason_code` model | |
| **3A-3** | Action Registry + public actions (`candidate.change_stage`, `candidate.open_transfer`) | |
| **3A-4** | Execution lifecycle, idempotency, freshness gate, `superseded` | |
| **3A-5** | Suggested automation via NBA (`execution_mode=suggested`) | |
| **3A-6** | CapabilityPreview platform read model in Candidate Workspace | |
| **3A-7** | Automation Center read model (Active / Recommended / Locked / history) | |

Audit: [`existing-runtime-reuse-review-automation-plane.md`](../platform/existing-runtime-reuse-review-automation-plane.md).

### 3A-1 minimal scope (explicit)

1. Canonical event envelope (`event_id`, `correlation_id`, `causation_id`, `occurred_at`, payload)  
2. Event Contract Registry  
3. Transactional outbox table  
4. Publisher API (insert in same TX as domain mutation)  
5. Outbox dispatcher worker  
6. Idempotent consumer skeleton (log-only orchestrator stub)  
7. Retry and dead-letter states  
8. Audit correlation via event/correlation/causation ids  
9. **Single publisher:** RequirementEvaluationService → `candidate.requirements_evaluated`  
10. **No** cross-module actions  

**STOP:** merge blocked if domain mutation commits without outbox row in same transaction.

### Scope IN (full slice — 3A-1 through 3A-7)

- `candidate.requirements_evaluated` + `candidate.transfer_ready` via outbox  
- Templates: stage transition (`can_transition=true`, suggested); open transfer  
- Freshness gate before critical actions  
- CapabilityPreview when `recruitment.to_hr_transfer` locked (module/plan)  
- Execution audit + superseded handling  

### Scope OUT (until slice proven)

- Visual drag-and-drop builder  
- Arbitrary user-defined domain conditions  
- Multi-action chains  
- Scheduled automation  
- Full template marketplace  
- Billing automation  
- Universal rollback  
- External webhook builder  
- Full approval queue UI (stub OK in 3A-4)  
- Cross-module actions before 3A-3  
- Module purchase flow (manual entitlement flag OK)  

### Slice flow

```
BEGIN TX;
  RequirementEvaluationService.evaluate()
  INSERT outbox: candidate.requirements_evaluated { can_transition, evaluation_result_id, entity_revision }
COMMIT;
→ outbox worker
→ Reaction Orchestrator: match template, conditions on payload only
→ capability + entitlement check
→ freshness gate
→ if entitled: execution=suggested → NBA «Перевести кандидата?»
→ TransferPolicyResolver → outbox: candidate.transfer_ready
→ if recruitment.to_hr_transfer entitled:
     action candidate.open_transfer
   else:
     CapabilityPreview { reason_code: module_missing, current_context: … }
→ audit AutomationExecution
```

### Slice definition of done

- [ ] No domain conditions inside automation rules (only §14.4 sources)  
- [ ] Events are facts; actions via Action Registry only  
- [ ] Outbox: domain state + event atomic  
- [ ] Stale evaluation → `superseded`, action blocked  
- [ ] CapabilityPreview DTO reused (not hardcoded Recruitment banner)  
- [ ] Full audit trail for one candidate path (Yurchuk or equivalent)  

---

## Последствия

### Для кода / данных

- Evolve `automation_rules` schema toward ADR-019 contract  
- Introduce **transactional outbox**; replace direct `run_automation_rules()` incrementally  
- New platform packages: `platform/automation/`, `platform/capabilities/`, `platform/actions/`, `platform/events/`  
- Reaction Orchestrator with lifecycle + freshness gate + `superseded`  
- CapabilityPreview as shared platform DTO  

### Для Domain Contracts

- Handoff contract: transfer actions via Action Registry, not direct service calls  
- ADR-004: billing automations emit BillingEvent only  
- ADR-018: evaluation DTO becomes event payload fact  

### Для Entity Specs

- Update recruitment module-scope with automation consumption pattern  
- Add platform automation spec after Slice 1  

### Human Language (UI)

| Модель | UI |
|--------|-----|
| AutomationTemplate | «Автоматизация» |
| Execution mode `suggested` | «Рекомендуется» |
| CapabilityPreview | Platform read model — «Доступно после подключения …» |
| Automation Center | «Центр автоматизаций» |

---

## Compliance checklist

- [x] Первый принцип: моделируем работу, не экран  
- [x] Identity отделена от State (domain fact vs automation reaction)  
- [x] Reaction Orchestrator ≠ policy engine (§14.4 prohibitions)  
- [x] Events are facts; actions are commands (§14.3)  
- [x] Transactional outbox mandatory for domain events  
- [x] Freshness gate + `superseded` lifecycle  
- [x] CapabilityPreview — platform read model  
- [x] Business time: `occurred_at`, execution timestamps  
- [x] Layer of change: Platform + cross-module contracts  
- [ ] Entity Spec / Domain Contract обновлены (после Slice 1)  

---

## Ссылки

- Constitution: [`ui-constitution-v1.md`](ui-constitution-v1.md)  
- ADR-018: Requirement Policy & Evaluation  
- ADR-004: Billing Events  
- ADR-012: Activity & Notification Operating Layer  
- ADR-002: Recruitment ↔ HR boundary  
- Reuse audit: [`existing-runtime-reuse-review-automation-plane.md`](../platform/existing-runtime-reuse-review-automation-plane.md)  
- PR 2B audit: [`requirement-evidence-model-p0.md`](../platform/requirement-evidence-model-p0.md)  
- Module catalog: [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)  
- Existing automation service: `backend/app/services/automation_rules.py`  
- Plan gates: `backend/app/services/plan_feature_gates.py`  
