# C0.2 — Inbound resolver & threading

**Status:** Active (next after PR #101 / C0.1b)  
**Branch:** `fix/communication-c0-inbound-resolver`  
**Worktree:** `/tmp/hf-c0-2-inbound-resolver`  
**Base:** `integration/release-product-a-b` @ `7bc13d57`  
**Parents:** [Epic C0](epic-c0-communication-integrity.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [C0.1b](c0-1b-intent-policy-snapshot-hardening.md)

> Outbound Canon is stable (Intent → Policy → Snapshot).  
> This slice makes inbound correspondence equally deterministic.

## Main contract

> Every inbound message is either **deterministically linked** to a thread/entity,  
> or lands in an **explicit unresolved queue**.  
> Lost / silently dropped inbound messages are forbidden.

## Scope (in)

1. **Inbound provider normalization** — provider payloads → common inbound DTO  
2. **Reply / thread resolution** — prefer `In-Reply-To` / `References` → provider thread ids → …  
3. **Entity resolution** — exact contact → active inquiry/application → client/candidate  
4. **Create inbound `CommunicationMessage`** on the resolved (or unresolved) thread  
5. **G13 links** — durable `thread ↔ entity` when entity is known  
6. **Unresolved queue** — explicit queue + reason when resolution fails  
7. **Idempotency** by provider message ID (no duplicate inbound rows)  
8. **Audit / correlation** — resolution reason codes + correlation to outbound when reply  

### Resolution preference (normative)

1. `In-Reply-To` / `References` → existing thread  
2. Provider conversation / message identifiers  
3. Exact email/phone among linked persons  
4. Active inquiry or application for that contact  
5. Client / candidate  
6. Only then: unlinked thread + **unresolved** queue  

Resolution reasons (audit):  
`reply_headers` | `provider_thread` | `known_participant` | `entity_contact` | `manual` | `unresolved`

## Scope (out)

- Inbox UX redesign (Epic C1)  
- Delivery diagnostics product UX (C0.3)  
- Template/automation/campaign product (C2)  
- Migrating remaining outbound legacy writers (map from C0.1b; separate slices)

## Acceptance / merge gate

- [x] Reply to a HostFlow-sent email joins the **same** thread and surfaces on the **same** entity  
- [x] Unknown inbound never disappears — always message + thread + unresolved reason when unlinked  
- [x] Duplicate provider message ID is idempotent (`tenant` + `channel` + `channel_account` + provider message id)  
- [x] Ambiguous `entity_contact` → unresolved (`ambiguous_entity_contact`), never arbitrary pick  
- [x] Unresolved row in same transactional boundary as message (caller commit)  
- [x] Manual resolution retains audit (who / when / entity / thread)  
- [x] Message persisted before optional downstream side effects (auto-assign / UOS)  
- [x] `/ingest/email` and `/ingest/{channel}` have no legacy thread-heuristic bypass  
- [x] Reply Message-ID normalize: brackets, case, duplicate headers  
- [x] G13 link idempotent  
- [x] Corrupt / forced unresolved payload kept with reason code  

### Implementation map

| Piece | Location |
|-------|----------|
| Normalized DTO | `backend/app/communications/inbound_dto.py` |
| Provider normalize | `backend/app/communications/inbound_normalize.py` |
| Resolution chain | `backend/app/communications/inbound_resolve.py` |
| Ingest + G13 / unresolved | `backend/app/communications/inbound_ingest.py` |
| Unresolved queue model | `backend/app/models/communication_inbound_unresolved.py` |
| Migration | `backend/alembic/versions/202607200002_comm_inbound_unresolved_c0_2.py` |
| Outbound Message-ID stamp | `backend/app/communications/send_communication.py` |
| API wire | `backend/app/api/v1/communications/routes/ingest.py` |
| Contract tests | `backend/tests/communications/test_c0_2_inbound_resolver.py` |

## Post-#101 gate (done)

1. ✅ FF integration → `7bc13d57`  
2. ✅ SHA + clean tree  
3. ✅ `make repo-health` PASSED  
4. ✅ CI vs baseline `f8569fa9`: same pre-existing red pattern (`docs-gates` / `backend-ci` / `frontend-static-qa` / `security-gates`); tip runs settling  
5. ✅ Removed `/tmp/hf-c0-1b-intent-policy`  
6. ✅ Created `/tmp/hf-c0-2-inbound-resolver`  
