# Epic C0 — Communication Integrity

**Status:** Queued (starts only after Stage 3 slice 2 / PR #99 is merged)  
**Parents:** [Sequential queue](sales-to-comms-sequential-queue.md) · G13 thread entity links · Thread-primary Communication

> Platform-critical GAP: HostFlow loses the link between the originating entity and the actual correspondence.  
> This epic is **not** Inbox UX and **not** Stage 3 Sales slice 3. Thin integrity slices only.

## Why before Stage 3 slice 3

Continuing Sales product flow on unbound / mis-linked threads makes every later Sales↔Communication surface more expensive. Integrity first, then Sales module completion, then Inbox UX.

## Observed GAPs (facts)

1. **Unbound outbound threads** — send from inquiry / application / client / candidate / order already knows origin; G13 `communication_thread_entity_link` must be written in the same business operation. Address fallback must not be the primary outbound mechanism.
2. **Inbound resolver too weak** — unlinked became common; resolver must prefer reply headers → provider IDs → exact contact → active inquiry/application → client/candidate → only then unresolved.
3. **`lead.communication.failed`** — likely wrong event model after Thread-primary; delivery state belongs on Message/Delivery with human-readable history text.
4. **Meta Intake Completeness** — separate sprint (not inside C0); see [meta-intake-completeness.md](meta-intake-completeness.md).

---

## Slice C0.1 — Guaranteed outbound linkage

**Branch (proposed):** `fix/communication-c0-outbound-linkage`  
**Worktree (proposed):** `/tmp/hf-c0-outbound-linkage`  
**Base:** `integration/release-product-a-b` tip **after** PR #99 merge

### Post-merge gate (before any C0.1 worktree)

1. Fast-forward `integration/release-product-a-b`
2. Verify new SHA and clean tree
3. `make repo-health`
4. Compare CI to known baseline (pre-existing reds are not C0 blockers)
5. Remove `/tmp/hf-convert-entrypoints`
6. Confirm only the integration worktree remains
7. Create a **new** worktree + branch exclusively for C0.1

### Main contract

> **Cannot** create an outbound message from a HostFlow entity without a durable `thread ↔ origin entity` link.  
> Unknown **delivery** result is allowed.  
> Unbound thread when origin is known is **not** allowed.

### GAP audit (required before writing code)

Short, evidence-based inventory — no product code until this lands in the slice notes:

| # | Question |
|---|----------|
| 1 | All outbound send entrypoints (HTTP, services, workflows, questionnaire invite, etc.) |
| 2 | Where thread is created or resolved |
| 3 | Where `communication_thread_entity_links` are written |
| 4 | Which callers pass entity context (`entity_type` / `entity_id` / origin) |
| 5 | Where UI reads legacy `entity_type` / `entity_id` instead of G13 links |
| 6 | Transactional boundaries between message, thread, link, and outbox |
| 7 | Existing send idempotency (re-send must not duplicate links) |

### Scope (implementation, after audit)

- Every send action requires origin context: `tenant_id`, `entity_type`, `entity_id`, `actor`, `recipient`.
- Thread is created or resolved **before** provider handoff.
- Entity link written in the **same** business operation; re-send does not duplicate links.
- Send from SalesInquiry links thread at least to: SalesInquiry + transport Lead/Submission for traceability.
- After convert: add ClientAccount link **without** removing Inquiry link.
- UI reads G13 entity links, not only legacy `entity_type` / `entity_id` columns.

### Acceptance

Email sent from an inquiry card appears in that inquiry’s history **immediately**, before provider reply/webhook.

---

## Slice C0.2 — Inbound resolver and threading

**Branch (proposed):** `fix/communication-c0-inbound-resolver`

### Scope

Unified resolution chain:

1. `In-Reply-To` / `References` → existing thread  
2. Provider conversation / message identifiers  
3. Exact email/phone among linked persons  
4. Active inquiry or application for that contact  
5. Client / candidate  
6. Only then create unlinked thread + unresolved queue  

Resolution reasons (audit): `reply_headers` | `provider_thread` | `known_participant` | `entity_contact` | `manual` | `unresolved`.

### Acceptance

A reply to an email sent from HostFlow lands in the **same** thread and surfaces on the **same** entity.

---

## Slice C0.3 — Delivery diagnostics and history

**Branch (proposed):** `fix/communication-c0-delivery-diagnostics`

### Scope

- Find producer of `lead.communication.failed`; retire or remap after Thread-primary.
- Delivery state on Message/Delivery: created / succeeded / failed.
- No internal event names in operator UI.
- History shows: who sent, when, from, to, delivered/failed, safe failure reason.
- Correlation IDs between outbound message and provider webhook.

### Acceptance

Any send failure is explainable from **one** record without server logs.

---

## Out of scope (all C0 slices)

- Inbox UX redesign (Epic C1)  
- Signature policy product UI (later Communication stage)  
- Meta Intake Completeness (parallel-near sprint, separate epic)  
- Stage 3 Sales slice 3+ product flow  
- Historical repair of ambiguous unbound threads beyond fail-closed gates (may follow C0.1 gate)
