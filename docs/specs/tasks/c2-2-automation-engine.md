# C2.2 — Automation Engine

**Status:** Active (kickoff — Intent-only; no send path)  
**Epic:** [C2 Communication Capability Epic](epic-c2-communication-campaigns.md)  
**Branch (proposed):** `feat/communication-c2-2-automation-domain` (PR-1)  
**Parents:** [C2.1 Template Platform ✅](c2-1-template-platform.md) · [C0.0 Canon](c0-0-communication-canon.md) · [Epic C Complete Gate](../gates/epic-c-complete-gate.md)

> Second C2 slice. **Automation only.** No Campaign product, no Scheduling product, no Thread redesign.  
> Automation creates / shapes `CommunicationIntent`. It never mutates Thread and never calls providers.

---

## Locked from C2 epic

```text
Event → Rules → Policy → CommunicationIntent
```

Merge gates (inherited): **Intent-only egress** · **no second pipeline** · **capability isolation** · **frozen Thread model**.

Automation has **no own send path**.  
Automation does **not** know SMTP, Gmail, WhatsApp, or Thread.  
It evaluates rules and emits Intent. Pipeline + Commands + Template Platform do the rest.

---

## Two principles (C2.2 law)

### 1. Automation never sends

Automation answers only:

> **“Should we create an Intent now, with which Intent key / template / recipients inputs?”**

Automation does **not**:

| Forbidden concern | Owner |
|-------------------|--------|
| Render body | Template Platform (C2.1) |
| Call provider / SMTP | CommunicationSender |
| Open / mutate Thread | Workspace Commands |
| Bulk audience waves | Campaign (C2.3) |
| Clock / cron product | Scheduling (C2.4) |

### 2. Rules are declarative and replayable

Same event + same rule snapshot + same policy inputs → same Intent decision (or structured skip).  
Store rule version / definition id on emitted Intent metadata where applicable so diagnostics can explain “why this fired”.

---

## Implementation order (locked)

```text
PR-1 Automation Domain (Event / Rule / Decision records)
  → PR-2 Rule Evaluator (pure where possible)
  → PR-3 Intent Emitter (creates CommunicationIntent only)
  → PR-4 Automation API
  → PR-5 Thin operator UI
```

No UI before domain + evaluator + emitter contracts are stable.

---

### PR-1 — Domain

ORM uses `CommunicationAutomation*` tables (`communication_automation_*`) so we do **not** collide with legacy tenant reminder `automation_rules`. Spec aliases live in the communications package only.

| Spec name | ORM / table |
|-----------|-------------|
| `AutomationRule` | `CommunicationAutomationRule` / `communication_automation_rules` |
| `AutomationRuleVersion` | `CommunicationAutomationRuleVersion` / `…_rule_versions` |
| `AutomationTrigger` | `CommunicationAutomationTrigger` / `…_triggers` |
| `AutomationDecision` | `CommunicationAutomationDecision` / `…_decisions` |

Lifecycle: draft=`version_number=0` editable; publish creates a new immutable published version and keeps the draft. Package: `backend/app/communications/automation/`.

Out of PR-1: rich UI, Campaign, Scheduling product, rule evaluator, Intent emitter.

### PR-2 — Rule Evaluator

Pure evaluation package: `communications/automation/evaluator/`.

| Op | Role |
|----|------|
| `evaluate` | Fire/skip decision + diagnostics |
| `dry_run` | Alias of evaluate (no side effects) |
| `diagnostics` | Structured findings only |

- Input: `EventPayload` + `RuleVersionPayload` + optional `PolicyContext`  
- Output: `EvaluationResult` (`fire` \| `skip`, reason codes, mapped template variables)  
- Forbidden in pure core: SQL · ORM · Sender · Thread · Campaign · `execute_intent`  
- ORM adapter stays outside: `communications/automation/payload.py`

### PR-3 — Intent Emitter

Only path from Automation → platform:

```text
EvaluationResult(fire) → IntentExecutionRequest → execute_communication_intent
```

Package: `communications/automation/emitter.py`

| Op | Role |
|----|------|
| `build_intent_request` | Pure-ish builder (no I/O) |
| `emit_from_evaluation` | Persist decision + optional render/execute |

- Skip outcomes never create Intent (decision may still be recorded)  
- Sets `automation_identity` + `source_event_id` + rule version meta  
- Goes through Intent Policy via existing `execute_communication_intent` / `render_communication_intent`  
- Forbidden: Thread models · Workspace Commands · provider/sender shortcut

### PR-4 — API

CRUD draft rules, publish, enable/disable, dry-run evaluate, decision history.

### PR-5 — UI

Thin client: list / editor / dry-run / history. No client-owned send loop.

---

## Out of scope (later slices)

- Campaign Orchestrator (C2.3)  
- Scheduling product (C2.4)  
- Module-specific automation engines (forbidden by capability isolation)  
- Thread / Commands redesign  

---

## Anti-patterns (reject in review)

- Automation → provider shortcut  
- Automation mutating Thread / writing Messages directly  
- Importing Recruitment / Sales / HR / Services / Finance into automation packages  
- Frontend looping N× Write instead of Intent emission  
- Embedding template HTML/business routing inside rule scripts  

---

## Definition of Done (C2.2)

- [x] PR-1 domain + immutable published rule versions — `feat/communication-c2-2-automation-domain`  
- [x] PR-2 evaluator with structured diagnostics — `feat/communication-c2-2-automation-evaluator`  
- [x] PR-3 Intent-only emitter (contract tests: no Sender / Thread writes) — `feat/communication-c2-2-automation-emitter`  
- [ ] PR-4 API + PR-5 thin UI  
- [ ] Capability-isolation contract tests on C2.2 packages  
- [ ] No Campaign / Scheduling product code in C2.2  

## After C2.2

**C2.3 Campaign Orchestrator** — audience + plan → Intent (still no render/send/Thread).
