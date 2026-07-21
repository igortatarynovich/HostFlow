# C2.1 — Template Platform

**Status:** Active (kickoff)  
**Epic:** [C2 Communication Capability Epic](epic-c2-communication-campaigns.md)  
**Branch (proposed):** `feat/communication-c2-1-template-platform`  
**Parents:** [C0.0 §5 CommunicationTemplate](c0-0-communication-canon.md) · [C1 closed](c1-communication-inbox-workspace.md) · [Epic C Complete Gate](../gates/epic-c-complete-gate.md)

> First C2 slice. **Templates only.** No Campaign, no Automation, no Scheduling product.

---

## Locked from C2 epic

> Templates participate in creating / shaping `CommunicationIntent` content.  
> They never mutate Thread and never call providers.

```text
Template Registry / Preview / Publish
  → used by Platform Pipeline when resolving an Intent
  → never a parallel send path
```

Merge gates (inherited): **Intent-only egress** · **no second pipeline** · **capability isolation** · **frozen Thread model**.

---

## In scope

| Capability | Notes |
|------------|--------|
| **Template Registry** | Tenant-owned catalog; Communication platform ownership |
| **Versioning** | Immutable published versions; draft edits do not mutate live sends |
| **Variables** | Declared variable schema; validated at preview and prepare-send |
| **Validation** | Channel + intent compatibility; required vars; no baked public URLs |
| **Preview** | Same render path as prepare-send (snapshot rules) |
| **Draft / Published** | Lifecycle status; only Published is selectable for live Intent resolution |
| **Channel compatibility** | email / messenger / … matrix per template |
| **Intent compatibility** | `link_intents` / purpose binding per Canon — templates reference intents, do not mint URLs |

---

## Out of scope (later slices)

- Automation Engine (C2.2)  
- Campaign Orchestrator (C2.3)  
- Scheduling product (C2.4)  
- Bulk audience selection UI  
- Module-specific template forks (forbidden by capability isolation)

---

## Anti-patterns (reject in review)

- Importing Recruitment / Sales / HR / Services / Finance into template code  
- Frontend-owned composition / channel policy  
- Preview that bypasses platform render/snapshot  
- Template → provider send shortcut  
- Hardcoded apply / public URLs in template bodies (use LinkIntent only)

---

## Definition of Done

- [ ] Registry + versioning + draft/published durable  
- [ ] Variables + validation + channel/intent compatibility enforced server-side  
- [ ] Preview uses prepare-send render path  
- [ ] Capability-isolation contract test covers `templates` / C2.1 packages  
- [ ] No Campaign / Automation code in this PR  
- [ ] Spec + Canon §5 remain aligned  

## After C2.1

**C2.2 Automation Engine** — `Event → Rules → Policy → CommunicationIntent`  
(still no provider / Thread knowledge).
