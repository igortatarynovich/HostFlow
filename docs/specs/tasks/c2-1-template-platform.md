# C2.1 — Template Platform

**Status:** Active (kickoff — domain-first; no UI yet)  
**Epic:** [C2 Communication Capability Epic](epic-c2-communication-campaigns.md)  
**Branch (proposed):** `feat/communication-c2-1-template-domain` (PR-1)  
**Parents:** [C0.0 §5 CommunicationTemplate](c0-0-communication-canon.md) · [C1 closed](c1-communication-inbox-workspace.md) · [Epic C Complete Gate](../gates/epic-c-complete-gate.md)

> First C2 slice. **Templates only.** No Campaign, no Automation, no Scheduling product.  
> **Do not start with a template editor UI.** Model and renderer first; UI last.

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

## Two principles (C2.1 law)

### 1. Template never contains business logic

Template answers only:

> **“How does the message look?”**

Template does **not** answer:

| Forbidden concern | Owner |
|-------------------|--------|
| Whom to send | Intent + recipient resolvers |
| When to send | Automation / Campaign / Schedule |
| Whether send is allowed | Policy / consent / capability |
| Which channel to use | Intent + capability / channel policy |
| Which Thread to change | Platform thread resolution + Commands |
| Whether to create a Notification | Notification / other platforms |

All of those decisions already belong to the **existing pipeline**.  
A Template is presentation, not a workflow engine.

### 2. TemplateVersion is fully reproducible

Years later, any `DeliveryAttempt` (and message snapshot) must show the message **exactly as sent**.

Therefore:

- Delivery / Message snapshot store and resolve by **`template_version_id`**  
- Never by “current published template” or bare template name alone  
- `CommunicationCommand` (and durable snapshot) hold **`template_version_id`**, not only a template key/name  

Publish creates an immutable version; later edits cannot rewrite history.

---

## Implementation order (locked — no UI until PR-5)

```text
PR-1 Template Domain
  → PR-2 Rendering Engine
  → PR-3 Registry (SoT)
  → PR-4 Template API
  → PR-5 UI (thin client)
```

Largest failure mode of similar systems: pretty editor first, model fitted later.  
**C2.1 forbids that sequence.**

---

### PR-1 — Template Domain

**Only domain entities.** No UI. No HTTP product API required beyond what migrations/tests need.

Entities:

| Entity | Role |
|--------|------|
| `Template` | Stable identity / key / lifecycle head |
| `TemplateVersion` | Immutable published (or draft working) body + schema |
| `TemplateVariable` | Declared typed variables for a version |
| `TemplateChannelBinding` | Which channels this version may use |
| `TemplateIntentBinding` | Which CommunicationIntents may select this template |

Invariants:

- Template body is **immutable after publish**  
- **Draft** is always editable  
- **Publish** creates a **new** `TemplateVersion` (does not mutate the previous published row)  
- `CommunicationCommand` / snapshot store **`template_version_id`**, not template name as the composition SoT  

Out of PR-1: renderer product surface, registry matrices UX, public CRUD API, UI.

---

### PR-2 — Rendering Engine

**Server-side renderer only.** No Campaign.

Capabilities:

- Strict variable validation  
- Typed variables  
- `preview`  
- `render`  
- Missing-variable diagnostics  
- Channel validation (against `TemplateChannelBinding`)  

Preview and prepare-send **must share** this engine (same snapshot rules).  
No provider calls. No Thread writes.

---

### PR-3 — Registry

**Single SoT** for “which templates are allowed where”:

| Axis | Mapping |
|------|---------|
| Intent → allowed Templates | Intent compatibility |
| Channel → allowed Templates | Channel compatibility |
| Capability → allowed Templates | Feature / capability matrix |

No second allow-list in modules or frontend.  
Registry is the only place that answers “may this Intent use this Template on this channel under this capability?”.

---

### PR-4 — Template API

Only after the model is stable:

- CRUD draft  
- publish  
- archive  
- preview  
- versions  
- diff  

Public HTTP API for operators/tools. Still **no** Campaign / Automation product endpoints.

---

### PR-5 — UI

Thin client over the API only:

- list  
- editor  
- preview  
- publish  
- history  

UI must not invent composition, channel policy, or versioning rules.

---

## In scope (epic slice total)

| Capability | Lands mainly in |
|------------|-----------------|
| Domain entities + publish immutability | PR-1 |
| Typed vars + render/preview/diagnostics | PR-2 |
| Intent / channel / capability SoT registry | PR-3 |
| CRUD / publish / archive / versions / diff API | PR-4 |
| Operator UI (thin) | PR-5 |

---

## Out of scope (later slices)

- Automation Engine (C2.2)  
- Campaign Orchestrator (C2.3)  
- Scheduling product (C2.4)  
- Bulk audience selection UI  
- Module-specific template forks (forbidden by capability isolation)  
- Template editor **before** PR-1…PR-4  

---

## Anti-patterns (reject in review)

- Starting C2.1 with a rich UI editor  
- Business logic / routing / consent / channel choice inside template bodies or template services  
- Snapshot or Command keyed only by template name without `template_version_id`  
- Importing Recruitment / Sales / HR / Services / Finance into template packages  
- Frontend-owned composition / channel policy  
- Preview that bypasses the PR-2 renderer  
- Template → provider send shortcut  
- Hardcoded apply / public URLs in bodies (LinkIntent only)  
- Mutating a published `TemplateVersion` in place  

---

## Definition of Done (C2.1)

- [ ] PR-1 domain entities + publish immutability invariants  
- [ ] PR-2 shared server renderer (preview ≡ prepare-send path)  
- [ ] PR-3 registry is sole SoT for Intent/Channel/Capability → Template  
- [ ] PR-4 Template API (draft/publish/archive/preview/versions/diff)  
- [ ] PR-5 thin UI only after API  
- [ ] Commands/snapshots persist `template_version_id` for reproducibility  
- [ ] Capability-isolation contract tests on C2.1 packages  
- [ ] No Campaign / Automation product code  
- [ ] Canon §5 / snapshot section aligned with version_id  

## After C2.1

**C2.2 Automation Engine** — `Event → Rules → Policy → CommunicationIntent`  
(still no provider / Thread knowledge; still uses Template Platform for “how it looks”).
