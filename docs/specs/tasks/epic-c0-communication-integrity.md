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

**Done:** [c0-1-outbound-linkage-gap-audit.md](c0-1-outbound-linkage-gap-audit.md) @ `2569b3ea`.

| # | Question | Result |
|---|----------|--------|
| 1 | All outbound send entrypoints | **GAP** — none write G13 |
| 2 | Where thread is created or resolved | **PARTIAL** |
| 3 | Where `communication_thread_entity_links` are written | **GAP** — migration only |
| 4 | Which callers pass entity context | **PARTIAL** — legacy/C1 only |
| 5 | Where UI reads legacy vs G13 | **GAP** — legacy only |
| 6 | Transactional boundaries | **GAP** — no G13 in txn |
| 7 | Send idempotency | **PARTIAL** — C1 yes; G13 unused |

### Scope (implementation, after audit)

**Normative capability:** [c0-1-platform-outbound.md](c0-1-platform-outbound.md)

- Platform operation `SendCommunication(origin, recipients, channel, content, context)` — single outbound contour for all modules.
- Mandatory **origin**; G13 link to origin (+ optional related entities) in the same atomic unit as `CommunicationMessage` + delivery/outbox.
- Thread resolved by **work context / origin**, not recipient address alone; one person may have multiple threads.
- Product modules do **not** own separate email writers; questionnaire invite is the first caller.
- UI reads G13 entity links, with temporary legacy fallback.
- After convert: ClientAccount G13 link may be added without removing Inquiry link (later callers).

**Not in C0.1:** bulk/campaign engine → [Epic C2](epic-c2-communication-campaigns.md).

### Acceptance / DoD

- Email / message started from a supported entity appears on that entity’s history immediately (before provider reply).
- Contract scenarios: send from `candidate`, `application`, `sales_inquiry`, `client_account`, `lead`; re-send reuses origin thread; every new thread has G13 origin; cannot send with known origin without G13.

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
