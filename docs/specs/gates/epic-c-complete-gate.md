# Epic C Complete Gate

**Status:** **PASS_WITH_CONSTRAINTS** (2026-08-03)  
**Decision ID:** `EPIC_C_COMPLETE_PASS_WITH_CONSTRAINTS`  
**Type:** Mandatory merge / capability gate (not a product feature)  
**Parents:** [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Communication Platform Foundation](../architecture/communication-platform-foundation.md) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md)  
**Tip evidence:** `integration/release-product-a-b` includes **PR #219** (C2.3 Campaign Orchestrator land-on-tip)

> Final check that Communication is a **single platform capability**.  
> This gate is the only allowed transition from  
> **Communication Platform Foundation — complete** → **Epic C — complete**.

---

## Formal decision

| Field | Value |
|-------|-------|
| **Outcome** | `PASS_WITH_CONSTRAINTS` |
| **Date** | 2026-08-03 |
| **Epic C status** | **Epic C — complete** (under constraints below) |
| **Next Product Track** | **A2 Platform Governance Review** |
| **Not outcome** | Clean `PASS` (C2.4 frozen; legacy SMTP allowlist non-empty; Catalog Naming lag) · `STOP` (no second Campaign/Automation pipeline) |

**Rationale:** C0 foundation + C1 Inbox + C2.1–C2.3 Intent-only capabilities are on tip with enforcement (AST isolation, legacy allowlist freeze, inbound/diagnostics guards, Intent emitters). Communication operates as one platform for shipped slices. Remaining gaps are documented residuals with owners — not silent bypasses of the gate.

---

## Sequence (locked)

```text
C1 Inbox Workspace          ← CLOSED 2026-07-21 (evidence below)
  → C2 Capability epic (Intent-only; never mutate Thread)
       C2.1 Template Platform   ← ✅ closed (PR #110–#114)
       C2.2 Automation Engine   ← ✅ closed (PR #116–#120)
       C2.3 Campaign Orchestrator ← ✅ closed (PR #219)
       C2.4 Scheduling          ← FROZEN (accepted residual R1)
  → Epic C Complete Gate   ← PASS_WITH_CONSTRAINTS (this document)
  → A2 Platform Governance Review   ← next
  → Acquisition (Stage 3 + Meta)
  → Forms → Entity Workspace → Documents → Billing → AI
```

Do **not** skip this gate and mark Epic C complete after C2 alone.

---

## C1 close-out evidence (2026-07-21)

**Result:** C1 CLOSED — proceed to C2 **without Thread model changes**.

| Check | Evidence |
|-------|----------|
| Authenticated smoke of all 18 Workspace Commands on live Thread | `backend/scripts/smoke_c1_workspace_commands.py` → `SMOKE_PASS` |
| Thread | `197681a8-756a-4e3c-845b-1907cd88cbc8` (demo tenant; isolated smoke Thread) |
| Report | `backend/uploads/ops-reports/c1_workspace_commands_smoke_20260721T084034Z.json` |
| ThreadContext | Every Command + baseline/final `GET …/context` returned full four-block context (`identity` · `work_state` · `capabilities` · `workspace`) + `context_version` / `generated_at` |
| `work_version` | Monotonic +1 on applied transitions; unchanged on no-ops; final GET matches last Command (`wv=22` on closing run) |
| Optimistic concurrency | `expected_work_version` mismatch → HTTP **409** `stale_work_version` |
| Idempotency | Duplicate Assign / MarkRead/Unread / Complete/Cancel / Pause/Resume / Close/Reopen / Delete/Restore / SetPriority/Tags/Links → `applied=false`, **no** audit row, **no** version bump |
| Audit | `communication_command_audits` +1 only on real transitions; no-ops produce zero audit delta |
| Queue projections | `assigned_to_me` / `unassigned` / `new_inbound` / `requires_reply` / `closed` flip via Commands only (no MoveThreadToQueue) |
| Backend logs (smoke window) | Commands: **36×200 + 1×409**; **0** `500` / `IntegrityError` / `Traceback` / `no_intake_context` |
| Worker logs (smoke window) | **0** error signals |

Commands covered: AssignThread · ReassignThread · UnassignThread · MarkThreadRead · MarkThreadUnread · SetNextAction · CompleteNextAction · CancelNextAction · PauseSLA · ResumeSLA · CloseThread · ReopenThread · SetThreadPriority · SetThreadTags · DeleteThread · RestoreThread · UpdateThreadWorkflow · SetThreadLinks.

**Architecture freeze into C2:** Thread SoT + Commands-only mutations + ThreadContext read model + queue projections — unchanged.  
**C2 law:** create `CommunicationIntent` only; no second pipeline; **capability isolation** (no module imports). See [epic-c2](../tasks/epic-c2-communication-campaigns.md).

---

## Checklist

| # | Check | Status | Evidence (one line) |
|---|--------|--------|---------------------|
| 1 | One SoT for Communication | **PASS** | Canon + `backend/app/communications/` + Intent Registry + Thread/Commands; campaigns = `communication_campaign_*` |
| 2 | No legacy senders and no legacy inbound paths | **PASS_WITH_CONSTRAINTS** | Inbound unified + allowlist frozen (`test_legacy_bypass_allowlist_does_not_grow`); SMTP allowlist still non-empty (R2) |
| 3 | All modules use only the public Communication Contract via adapters | **PASS_WITH_CONSTRAINTS** | C3 adapters + Pipeline / INV-17; residual SMTP services (R2) |
| 4 | No platform → module dependencies (C2 capability isolation) | **PASS_WITH_CONSTRAINTS** | C2.1–C2.3 AST isolation tests ✅; gate/manual_reply lazy adapter imports (R3) |
| 5 | All messages (outbound / inbound) pass through the unified pipeline | **PASS_WITH_CONSTRAINTS** | Intent emitters + `ingest_inbound_message`; allowlisted bypasses remain (R2) |
| 6 | Callbacks, retries, diagnostics, and Inbox share one data model | **PASS** | C0.3 + C1 + C2.3 Intent fan-out; no competing scheduler SoT (C2.4 frozen) |
| 7 | Templates, Automations, and Campaigns use Intent Registry — not private rule engines | **PASS_WITH_CONSTRAINTS** | Templates/execute on Registry; publish-time key membership soft (R4) |
| 8 | Documentation (ADR, Canon, Catalog) matches implementation | **PASS_WITH_CONSTRAINTS** | Canon/C2/queue aligned in this PR; Catalog Notifications vs Communication naming → A2 (R5) |

### Evidence index

| Mechanism | Path |
|-----------|------|
| Intent Registry SoT + enum drift | `backend/app/communications/intent_registry.py`; `backend/tests/communications/test_c0_1b_intent_policy_hardening.py` |
| Legacy SMTP / Message ctor allowlist | `test_legacy_bypass_allowlist_does_not_grow` |
| Inbound no legacy bypass | `test_ingest_routes_have_no_legacy_thread_bypass` (`test_c0_2_inbound_resolver.py`) |
| Delivery mutation / provider poll bans | `backend/tests/communications/test_c0_3_delivery_diagnostics.py` |
| C2.1–C2.3 capability isolation AST | `backend/tests/communications/test_c2_1_*`, `test_c2_2_*`, `test_c2_3_*` |
| Policy adapter ports | `backend/tests/communications/test_policy_ports_c3.py` |
| C1 Commands smoke | `backend/scripts/smoke_c1_workspace_commands.py` |
| C2.3 land | GitHub PR **#219** |
| Legacy writers map | [c0-1b-legacy-writers-migration-map.md](../tasks/c0-1b-legacy-writers-migration-map.md) |
| Threat model (C2.3) | [communication-campaign-orchestrator.md](../../security/threat-models/communication-campaign-orchestrator.md) |

---

## Accepted residuals / constraints

| ID | Residual | Severity | Owner | Disposition |
|----|----------|----------|-------|-------------|
| **R1** | **C2.4 Scheduling FROZEN** — no Schedule→Intent product | Accepted | Communication Product | Do not start until explicit unfreeze; does not block Epic C complete |
| **R2** | Legacy SMTP allowlist writers (`rodo`, `candidate_notifications`, `draft_reminders`, `contact_attempts`, inbox `dispatch`, telegram link; ops digest) | Medium | Communication + owning modules | Shrink via allowlist / INV-17 follow-ups; map must not grow |
| **R3** | Platform lazy-imports of module adapters (`policy_gate`, `manual_thread_reply`) | Low | Architecture / Communication | Optional invert to registration; review in A2 |
| **R4** | Campaign/Automation publish without Intent Registry membership check; test key `campaign_outreach` not in registry | Medium | Communication | Hardening PR; bind keys to registry at publish |
| **R5** | Catalog / passport still centers **Notifications** vs runtime **Communication** | High (docs apply) | Architecture Canon | A2 Governance / Catalog apply (RFC if renaming L0 capability) |

---

## Status transition

| Before gate | After this decision |
|-------------|---------------------|
| Communication Platform Foundation — complete | **unchanged** (historically true) |
| Epic C open | **Epic C — complete** (`PASS_WITH_CONSTRAINTS`) |

Epic C complete means Foundation + C1 + C2.1–C2.3 + this gate.  
**C2.4** remains frozen and is **not** required to reopen Epic C.

---

## Relation to A2 Governance

**Epic C Complete Gate** = Communication capability closed as one platform.  
**A2 Platform Governance Review** = cross-platform check that the boundary rule  
(platforms independent; modules only via public contracts/adapters) was not violated  
during platform growth — not a re-test of “are integrations wired”.

Governance does not replace this gate. **R3** and **R5** are explicitly handed to A2.

**Suggested A2 branch:** `docs/platform-governance-review-post-epic-c`

---

## Branch

`docs/epic-c-complete-gate` (checklist + evidence links; no drive-by refactors)

## DoD

- [x] Checklist filled with evidence (paths / PRs / contract tests)  
- [x] Residual gaps listed with owners or accepted waivers  
- [x] Status docs updated: Foundation stays complete; **Epic C — complete** set only here  
- [x] Sequential queue + roadmap point at A2 next  
- [x] C1 close-out smoke + log evidence recorded (above)  
