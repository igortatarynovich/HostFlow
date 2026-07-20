# C0.1 GAP Audit — Guaranteed Outbound Linkage

**Status:** Audit complete (no product code yet)  
**Tip:** `2569b3ea` · branch `fix/communication-c0-outbound-linkage` · worktree `/tmp/hf-c0-outbound-linkage`  
**Parents:** [Epic C0](epic-c0-communication-integrity.md) · [Sequential queue](sales-to-comms-sequential-queue.md)

## Contract

> Cannot create an outbound message from a HostFlow entity without a durable `thread ↔ origin entity` link (G13).  
> Unknown **delivery** result is allowed.  
> Unbound thread when origin is known is **not** allowed.

---

## Executive summary

- **G13 is schema-only.** Table `communication_thread_entity_links` exists + one-time backfill in Alembic `202607160001`; **no ORM model**, **no runtime writer**, zero `backend/app` references.
- **C1 Thread Result Link ≠ G13.** C5 dispatch fail-closes on opaque SalesInquiry result links — domain policy, not entity-history linkage.
- **Primary outbound create path allows unbound threads.** Locked by test `test_outbound_thread_message_allowed_without_mandatory_link`.
- **Questionnaire invite email** binds C1 + legacy columns, journals `CommunicationDelivery` on **lead**, SMTP sends — but **no G13** and **no `CommunicationMessage`**, so inquiry history cannot show the send immediately.
- **UI reads legacy** `entity_type` / `entity_id` / `linked_*` — never G13.

---

## Findings (7 questions)

| # | Question | Severity | Evidence |
|---|----------|----------|----------|
| 1 | Outbound send entrypoints | **GAP** | Multiple HTTP/service paths; most bypass G13; several bypass C5 (see table). |
| 2 | Thread create/resolve on send | **PARTIAL** | Questionnaire binder creates/resolves email thread + C1. Inbox: create thread → message → dispatch with no origin required. Many emails never touch a thread. |
| 3 | G13 writes | **GAP** | Only migration backfill: `backend/alembic/versions/202607160001_comm_thread_entity_links.py`. No runtime INSERT. |
| 4 | Callers passing entity context | **PARTIAL** | Legacy columns + C1 opaque result for pipeline. **No caller writes G13.** Delivery journal uses `entity_type=lead` separately. |
| 5 | UI legacy vs G13 | **GAP** | Work area / link forms / unlinked heuristic / candidate history / list filters use legacy columns only. |
| 6 | Transactional boundaries | **GAP** | No G13 in any txn. Message create commits alone. Dispatch: provider call then commit. Questionnaire: delivery flush → SMTP → router commit; no `CommunicationMessage`. |
| 7 | Send idempotency | **PARTIAL** | C1 attach idempotent; G13 unique key exists in schema but unused; questionnaire delivery `idempotency_key` unused on send path. |

---

## Send entrypoints (origin + G13)

| Entrypoint | Symbol | Origin known? | Writes G13? | Notes |
|------------|--------|---------------|-------------|-------|
| Create thread message | `POST …/threads/{id}/messages` · `messages.py` | Optional | **No** | Unbound outbound allowed (test locked) |
| Dispatch message | `POST …/messages/{id}/dispatch` · `dispatch.py` | Via C1 for C5 | **No** | Provider before commit |
| Worker dispatch | `dispatch_queued_messages` / email worker | Same C5 | **No** | |
| Create / patch thread | `threads.py` | Optional legacy / C1 | **No** | UI “entity link” uses PATCH |
| Questionnaire invite email | `POST /leads/{id}/questionnaire-invite/email/send` → `send_questionnaire_invite_email` | SI + C1 + legacy | **No** | No `CommunicationMessage` |
| Lead operational emails | `maybe_send_lead_communication` | Caller thread + purpose | **No** | Often skipped |
| Lead RODO / contact attempt / candidate notifications | various | Entity-scoped stamps | **No** | Bypass threads / C5 |
| Tenant SMTP / settings test / digests | transport / ops | N/A | **No** | Out of C0.1 CRM origin scope |

---

## Distinguish existing “links”

| Mechanism | Role vs C0.1 |
|-----------|--------------|
| **G13** `communication_thread_entity_links` | **SoT** for thread ↔ origin — **not implemented at runtime** |
| **C1** `communication_thread_result_links` | Opaque result for C5 policy — done, not G13 |
| Legacy thread columns | Still written/read; must move history attachment to G13 |
| `CommunicationDelivery` | Side journal by entity; not thread history |

---

## Recommended C0.1 implementation order (thin)

1. ORM + ensure/upsert helper for G13 (unique key = re-send safe).
2. Single write site from entity-origin binders **before** provider handoff — start with Sales questionnaire binder (`ensure_sales_questionnaire_pipeline_binding`): G13 for `sales_inquiry` + transport `lead` in same flush as thread/C1.
3. Gate entity-origin outbound message create/dispatch when origin is known: require ≥1 G13 link (or create from request origin in same txn). Pure address-only inbox may remain temporarily; fail-closed when origin is already known.
4. Persist `CommunicationMessage` on questionnaire send on the bound thread in the same commit as delivery + G13 (acceptance: inquiry history immediate). SMTP failure → delivery unknown/failed (allowed).
5. Minimal read path: expose `entity_links[]` / filter by G13; point inquiry history UI at that.
6. Idempotency: G13 unique + C1 attach; set delivery `idempotency_key` for questionnaire re-send if still journaling.

---

## Out of scope (do not touch in C0.1)

- Inbound resolver / unlinked queue (**C0.2**)
- `lead.communication.failed` / delivery diagnostics UX (**C0.3**)
- Inbox UX (C1), signature policy UI, Meta Intake Completeness
- Stage 3 Sales slice 3+
- Bulk historical repair of ambiguous unbound threads
- Non-correspondence system mail (settings test, digests) unless it claims CRM entity history

---

## Post-merge gate (done)

| Step | Result |
|------|--------|
| Merge PR #99 | ✅ `2569b3ea` |
| FF `integration/release-product-a-b` | ✅ clean @ `2569b3ea` |
| `make repo-health` | ✅ PASSED |
| CI vs baseline | Same pre-existing reds: `docs-governance`, `qa-static`, `tests` (+ intermittent `pip-audit`); not C0 blockers |
| Remove `/tmp/hf-convert-entrypoints` | ✅ |
| Only integration + C0.1 worktrees | ✅ `/opt/HostFlow` + `/tmp/hf-c0-outbound-linkage` |
