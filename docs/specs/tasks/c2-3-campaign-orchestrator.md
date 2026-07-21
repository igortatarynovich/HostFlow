# C2.3 — Campaign Orchestrator

**Status:** **Landing on tip** (Engineering Track) — code from PR #121–#126 replayed onto `integration/release-product-a-b` after Stage 6.  
**Epic:** [C2 Communication Capability Epic](epic-c2-communication-campaigns.md)  
**Land branch:** `feat/communication-c2-3-land-on-tip` (supersedes stacked #121–#126)  
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
PR-1 Campaign Domain
  → PR-2 Audience / wave planner (no send)
  → PR-3 Intent fan-out (uses C2.2 emitter patterns / execute_intent)
  → PR-4 Campaign run orchestration
  → PR-5 Campaign API
  → PR-6 Thin operator UI
```

---

## Definition of Done (C2.3)

- [x] PR-1 domain + immutable campaign/wave versions  
- [x] PR-2 planner produces Intent inputs only  
- [x] PR-3 fan-out uses platform Intent path (no provider / Thread writes)  
- [x] PR-4 run orchestration  
- [x] PR-5 API + PR-6 thin UI  
- [ ] Landed on tip (this Engineering PR)  
- [ ] Capability-isolation contract tests green on tip  
- [x] No Scheduling product code in C2.3  

## After C2.3

**Epic C Complete Gate** — then A2 Governance.  
**C2.4 Scheduling** remains frozen.
