# Epic C2 — Communication Capability Epic

**Status:** Active (kickoff — after C1 close 2026-07-21)  
**Type:** Capability epic (not Communication v2)  
**Branch (proposed):** `feat/communication-c2-1-template-platform` (first slice)  
**Parents:** [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [C1 Inbox Workspace](c1-communication-inbox-workspace.md) · [C0.0 Communication Canon](c0-0-communication-canon.md) · [Epic C Complete Gate](../gates/epic-c-complete-gate.md)

**Filename note:** path kept as `epic-c2-communication-campaigns.md` for link stability; scope is the full C2 capability epic.

---

## Locked principle (entire C2)

> **C2 creates `CommunicationIntent`. C2 never mutates Thread directly.**

Foundation from C0–C1 is **frozen**. C2 must not reopen Thread, Commands, ThreadContext, or queue-projection architecture.

```text
Templates / Automations / Campaigns / Schedule / Bulk / Triggers
        ↓
  CommunicationIntent
        ↓
  existing Platform Pipeline
        ↓
  Commands / Thread / delivery / G13  (unchanged)
```

There are **no new send paths**, no private SMTP/Gmail/WhatsApp callers, and no Campaign/Automation → Thread shortcuts.

---

## Single responsibility

| C2 owns | C2 does **not** own |
|---------|---------------------|
| Emitting `CommunicationIntent` | Mutating Thread / Message / delivery SoT |
| Template Registry product | Provider transport |
| Automation rules → Intent | Workspace Commands redesign |
| Campaign orchestration → Intent | Queue projections / Inbox UX |
| Scheduling → Intent | Module business logic (Recruitment / Sales / …) |

Everything in C2 ends the same way:

```text
Automation | Campaign | Schedule | Bulk | Trigger
  → CommunicationIntent
  → existing Platform Pipeline
  → Commands / Thread
```

---

## Architecture freeze (from C1)

Do **not** change:

- Thread as work-object SoT  
- Workspace Commands as sole Thread mutation path  
- ThreadContext as Workspace read model  
- Queue membership as projection-only  
- Intent → Policy → Resolvers → Command → Sender pipeline  

C2 **adds capabilities that feed that pipeline**. It does not replace it.

---

## Merge gates (every C2 PR — blockers)

### 1. Intent-only egress

No C2 object may write Thread / Message / Outbox / delivery tables directly.  
Egress is **`CommunicationIntent` only** (then the existing platform pipeline).

### 2. No second pipeline

Forbidden: parallel senders, “campaign send”, “automation SMTP”, bulk loops that call providers or invent Thread writes.

### 3. Capability isolation *(new — mandatory)*

No C2 package/module may **import or depend on**:

- Recruitment  
- Sales  
- HR  
- Services  
- Finance  

**Allowed:** Platform contracts only (Communication Canon, Intent/Policy/Registry resolvers, DomainEvent ingress at the platform boundary, shared kernel types).

This gate stops module logic from leaking into Templates and Automation over time.  
Contract tests should fail the build if C2 code imports module packages.

### 4. Frozen Thread model

No Thread / Command / ThreadContext redesign in C2 PRs. Product gaps go to follow-ups **after** Epic C Complete Gate — not into C2 “while we’re here”.

---

## Slice sequence (locked)

```text
C2.1 Template Platform
  → C2.2 Automation Engine
  → C2.3 Campaign Orchestrator
  → C2.4 Scheduling
  → Epic C Complete Gate
```

Logical order: **what** to send → **when/why** → **to whom (bulk)** → **when (time)** → close Epic C  
without returning to Thread / Commands / ThreadContext architecture.

| Slice | Doc | First responsibility |
|-------|-----|----------------------|
| **C2.1** | [c2-1-template-platform.md](c2-1-template-platform.md) ✅ | Template Registry product (PR #110–#114) |
| **C2.2** | [c2-2-automation-engine.md](c2-2-automation-engine.md) ✅ | Event → Rules → Policy → Intent (PR #116–#120) |
| **C2.3** | [c2-3-campaign-orchestrator.md](c2-3-campaign-orchestrator.md) | Audience + plan → Intent — **implementation complete; merge blocked by shared CI debt** (PR #121–#126) |
| **C2.4** | *(blocked — after C2.3 merge)* | Schedule → Intent → same pipeline |
| **Gate** | [epic-c-complete-gate.md](../gates/epic-c-complete-gate.md) | Epic C — complete |

---

## C2.1 — Template Platform

**Templates only.** No Campaign, no Automation.  
**Domain-first:** no UI until the model/renderer/registry/API are stable — see [c2-1-template-platform.md](c2-1-template-platform.md).

Locked order:

```text
PR-1 Domain → PR-2 Renderer → PR-3 Registry → PR-4 API → PR-5 UI
```

C2.1 laws:

1. **Template = “how it looks” only** — never whom / when / whether / channel / Thread / Notification.  
2. **`template_version_id` is reproducible SoT** — Delivery/Snapshot/Command store version id, not “current template by name”.

Preview uses the **same render path** as prepare-send. Frontend is a thin client (PR-5 only).

---

## C2.2 — Automation Engine ✅

```text
Event → Rules → Policy → CommunicationIntent
```

Automation has **no own send path**.  
Automation does **not** know SMTP, Gmail, WhatsApp, or Thread.

It evaluates rules and emits Intent. Pipeline + Commands do the rest.

Slice: [c2-2-automation-engine.md](c2-2-automation-engine.md) (PR #116–#120).

---

## C2.3 — Campaigns ← **active**

Campaign is an **orchestrator**, not a sender.

Slice plan: [c2-3-campaign-orchestrator.md](c2-3-campaign-orchestrator.md).

| Campaign does | Campaign does **not** |
|---------------|------------------------|
| Select audience | Render templates |
| Plan send waves | Call providers |
| Create `CommunicationIntent` per recipient | Mutate Thread |

Per-recipient work still goes through Intent → platform pipeline (personal Thread / G13 as today).  
**Never** a shared “campaign thread”. Frontend must not loop N× Write buttons.

---

## C2.4 — Scheduling

Separate capability:

```text
Schedule → CommunicationIntent → ordinary pipeline
```

No special schedulers that talk to providers. Time fires Intent; pipeline unchanged.

---

## Product surfaces (later UX; same contracts)

1. Object lists → select → Write / schedule → template → preview → Intent  
2. Communication module: Templates · Automations · Campaigns · Schedules · Settings  

Settings / signatures / compliance UI may share **Настройки → Коммуникации** but stay separate ownership buckets ([C0.0 §13](c0-0-communication-canon.md)).

---

## Out of C2

- Thread / Commands / ThreadContext redesign (frozen)  
- Inbox Workspace product work (C1 closed)  
- C0 integrity writers (already done)  
- Module-owned send engines  
- Legal drafting of RODO notice text (legal review; architecture from C0.0)  
- Epic C Complete Gate checklist fill (after C2.1–C2.4)  

---

## Definition of Done (epic)

- [x] C2.1 Template Platform shipped under Intent-only + capability-isolation gates  
- [x] C2.2 Automation emits Intent only (no provider / Thread knowledge)  
- [ ] C2.3 Campaigns orchestrate Intent only (implementation complete; Closed only after PR #125+#126 merge)  
- [ ] C2.4 Scheduling emits Intent into the ordinary pipeline  
- [ ] Contract tests enforce capability isolation + no second pipeline  
- [ ] [Epic C Complete Gate](../gates/epic-c-complete-gate.md) ready for evidence pass  

**Active now:** **CI unblock** for C2.3 merge gate (`chore/ci-unblock-c2-3-stack`) — then merge PR #125+#126. Do **not** start C2.4. Slice doc: [c2-3-campaign-orchestrator.md](c2-3-campaign-orchestrator.md).
