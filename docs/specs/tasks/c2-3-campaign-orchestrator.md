# C2.3 — Campaign Orchestrator

**Status:** Active (kickoff — Intent-only; no send path)  
**Epic:** [C2 Communication Capability Epic](epic-c2-communication-campaigns.md)  
**Branch (proposed):** `feat/communication-c2-3-campaign-domain` (PR-1)  
**Parents:** [C2.2 Automation Engine ✅](c2-2-automation-engine.md) · [C2.1 Template Platform ✅](c2-1-template-platform.md) · [Epic C Complete Gate](../gates/epic-c-complete-gate.md)

> Third C2 slice. **Campaigns only.** No Automation product changes, no Scheduling product, no Thread redesign.  
> Campaign selects audience and plans waves; it creates `CommunicationIntent` per recipient. It never renders, sends, or mutates Thread.

---

## Locked from C2 epic

```text
Audience + plan → CommunicationIntent (per recipient) → ordinary pipeline
```

Merge gates (inherited): **Intent-only egress** · **no second pipeline** · **capability isolation** · **frozen Thread model**.

| Campaign does | Campaign does **not** |
|---------------|------------------------|
| Select audience | Render templates |
| Plan send waves | Call providers |
| Create `CommunicationIntent` per recipient | Mutate Thread |

**Never** a shared “campaign thread”. Frontend must not loop N× Write buttons.

---

## Implementation order (locked)

```text
PR-1 Campaign Domain
  → PR-2 Audience / wave planner (no send)
  → PR-3 Intent fan-out (uses C2.2 emitter patterns / execute_intent)
  → PR-4 Campaign API
  → PR-5 Thin operator UI
```

---

## Definition of Done (C2.3)

- [ ] PR-1 domain + immutable campaign/wave versions  
- [ ] PR-2 planner produces Intent inputs only  
- [ ] PR-3 fan-out uses platform Intent path (no provider / Thread writes)  
- [ ] PR-4 API + PR-5 thin UI  
- [ ] Capability-isolation contract tests  
- [ ] No Scheduling product code in C2.3  

## After C2.3

**C2.4 Scheduling** — Schedule → Intent → ordinary pipeline.
