# C2.3 — Campaign Orchestrator

**Status:** **DONE** (landed on tip via Engineering PR; stacked #121–#126 superseded)  
**Epic:** [C2 Communication Capability Epic](epic-c2-communication-campaigns.md)  
**C2.4 frozen.** Legacy full-repo pytest = base-known debt, not a C2.3 regression.

**Parents:** [C2.2 Automation Engine ✅](c2-2-automation-engine.md) · [C2.1 Template Platform ✅](c2-1-template-platform.md) · [Epic C Complete Gate](../gates/epic-c-complete-gate.md)

> Third C2 slice. **Campaigns only.** No Scheduling product, no Thread redesign.  
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

---

## Two audience concepts (law)

| Concept | Role | Mutability |
|---------|------|------------|
| **Audience definition** | Rule for *who may be selected* (on `CampaignVersion`) | Editable on draft; frozen into published version |
| **Audience snapshot** | Concrete recipient list *for one Run* | Immutable after run creation |

Replaying / inspecting an old run must show the snapshot from that moment — never re-query a live changing definition.

---

## Domain entities

ORM uses `CommunicationCampaign*` / tables `communication_campaign_*` (distinct from Acquisition `acq_campaigns`).

| Spec | Role |
|------|------|
| `Campaign` | Stable identity / lifecycle head |
| `CampaignVersion` | Draft or published immutable body + plan |
| `CampaignAudienceDefinition` | Selection rule on a version |
| `CampaignRecipient` | Snapshot member belonging to a Run |
| `CampaignRun` | One execution against a specific `campaign_version_id` |
| `CampaignRunItem` | Per-recipient outcome in a run (status + reason) |

### Invariants

- Draft version is editable; **published version is immutable**  
- Every run references a concrete **`campaign_version_id`**  
- Audience for a run is the **snapshot**, not a live re-resolve of the definition  
- Same tenant + **`idempotency_key`** → at most one Run  
- Each recipient/item has its own status and skip/failure reason  
- One failed/skipped item does **not** stop the run  
- No imports of Recruitment / Sales / HR / Services / Finance  
- No knowledge of provider, Thread, Sender, or Workspace Commands  

---

## Definition of Done (C2.3)

- [x] PR-1 domain + immutable campaign/wave versions  
- [x] PR-2 planner produces Intent inputs only  
- [x] PR-3 fan-out uses platform Intent path (no provider / Thread writes)  
- [x] PR-4 run orchestration  
- [x] PR-5 API + PR-6 thin UI  
- [x] Landed on tip (Engineering land PR)  
- [x] No Scheduling product code in C2.3  

## After C2.3

**Epic C Complete Gate:** [PASS_WITH_CONSTRAINTS](../gates/epic-c-complete-gate.md) (2026-08-03).  
**Next Product Track:** A2 Platform Governance Review.  
**C2.4 Scheduling** remains frozen.
