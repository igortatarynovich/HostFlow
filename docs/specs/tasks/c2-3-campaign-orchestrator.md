# C2.3 — Campaign Orchestrator

**Status:** Active (PR-3 Intent emission — no Campaign UI yet)  
**Epic:** [C2 Communication Capability Epic](epic-c2-communication-campaigns.md)  
**Branch:** `feat/communication-c2-3-campaign-intent-emitter` (PR-3)  


**Parents:** [C2.2 Automation Engine ✅](c2-2-automation-engine.md) · [C2.1 Template Platform ✅](c2-1-template-platform.md) · [Epic C Complete Gate](../gates/epic-c-complete-gate.md)

> Third C2 slice. **Campaigns only.** No Scheduling product, no Thread redesign, **no Campaign UI in PR-1…PR-4.**  
> Campaign selects audience and creates `CommunicationIntent` per allowed run item. It never renders, sends, or mutates Thread.

---

## Locked from C2 epic

```text
Audience + plan → CommunicationIntent (per recipient) → ordinary pipeline
```

Merge gates (inherited): **Intent-only egress** · **no second pipeline** · **capability isolation** · **frozen Thread model**.

| Campaign does | Campaign does **not** |
|---------------|------------------------|
| Select audience | Render templates |
| Plan / orchestrate runs | Call providers |
| Create `CommunicationIntent` per recipient | Mutate Thread / Message / Delivery |

**Never** a shared “campaign thread”. Frontend must not loop N× Write buttons.  
**UI is last** — same failure mode as overloaded Threads UX; do not start Campaign screens before domain + resolver + emission + API are stable.

---

## Two audience concepts (law)

| Concept | Role | Mutability |
|---------|------|------------|
| **Audience definition** | Rule for *who may be selected* (on `CampaignVersion`) | Editable on draft; frozen into published version |
| **Audience snapshot** | Concrete recipient list *for one Run* | Immutable after run creation |

Replaying / inspecting an old run must show the snapshot from that moment — never re-query a live changing definition.

---

## Domain entities (PR-1)

ORM uses `CommunicationCampaign*` / tables `communication_campaign_*`. Spec aliases live in the communications package.

| Spec | Role |
|------|------|
| `Campaign` | Stable identity / lifecycle head |
| `CampaignVersion` | Draft or published immutable body + plan |
| `CampaignAudienceDefinition` | Selection rule on a version |
| `CampaignRecipient` | Snapshot member belonging to a Run |
| `CampaignRun` | One execution against a specific `campaign_version_id` |
| `CampaignRunItem` | Per-recipient outcome in a run (status + reason) |
| `CampaignStatus` | Head lifecycle constants |
| `CampaignRunStatus` / item statuses | Run + item lifecycle constants |

### Invariants

- Draft version is editable; **published version is immutable**  
- Every run references a concrete **`campaign_version_id`**  
- Audience for a run is the **snapshot**, not a live re-resolve of the definition  
- Same tenant + **`idempotency_key`** → at most one Run  
- Each recipient/item has its own status and skip/failure reason  
- One failed/skipped item does **not** stop the run  
- No imports of Recruitment / Sales / HR / Services / Finance  
- No knowledge of provider, Thread, Sender, or Workspace Commands  

Campaign does **not** send and does **not** create Thread / Message / Delivery in this package.

---

## Implementation order (locked)

```text
PR-1 Domain
  → PR-2 Audience resolver (definition → snapshot; no send)
  → PR-3 Intent emission (per allowed RunItem → CommunicationIntent)
  → PR-4 Run orchestration (drive items; isolate failures)
  → PR-5 API
  → PR-6 Thin UI (last — not before API)
```

### PR-2 Audience resolver (locked)

Pure package `communications/campaign/audience/`:

| `definition_type` | Input | Output |
|-------------------|-------|--------|
| `static_list` | `definition.recipients` | Snapshot candidates |
| `filter` | `definition.filter` + caller `ResolveContext.entities` | Filtered snapshot candidates |

- No SQL / ORM / module imports inside `audience/`
- Entity pool is injected by the caller (platform boundary) — Campaign still does not import Recruitment/Sales/…
- `create_run_from_audience` freezes resolve output into Run recipients (never re-queries later)
- Out of PR-2: Intent emission, run orchestration loop, HTTP API, UI

### PR-3 Intent emission (locked)

`communications/campaign/emitter.py`:

```text
allowed RunItem → IntentExecutionRequest → execute_communication_intent
```

- Per-item emission; one failure → `failed`/`skipped` on that item only  
- Idempotent: already `emitted` items are not re-fired  
- `automation_identity = comm_campaign:{campaign_id}:{version_id}`  
- No provider / Sender / Workspace Commands / Thread ORM imports  
- Out of PR-3: run orchestration product loop, HTTP API, UI


---

## Anti-patterns (reject in review)

- Campaign UI / rich editor before PR-5+  
- Re-resolving live audience when displaying a past Run  
- Run without `campaign_version_id`  
- Shared campaign Thread  
- Provider / Sender / Commands imports in campaign packages  
- Module-specific campaign forks  

---

## Definition of Done (C2.3)

- [x] PR-1 domain + publish immutability + run idempotency + snapshot vs definition  
- [x] PR-2 audience resolver produces snapshot only (`static_list` / `filter` + caller entity pool)  
- [x] PR-3 Intent emission via platform path (no provider / Thread writes)  

- [ ] PR-4 run orchestration (item-level failure isolation)  
- [ ] PR-5 API  
- [ ] PR-6 thin UI only after API  
- [ ] Capability-isolation contract tests  
- [ ] No Scheduling product code in C2.3  

## After C2.3

**C2.4 Scheduling** — Schedule → Intent → ordinary pipeline.
