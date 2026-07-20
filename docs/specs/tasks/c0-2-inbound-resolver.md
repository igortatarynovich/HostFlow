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

## Acceptance

- [ ] Reply to a HostFlow-sent email joins the **same** thread and surfaces on the **same** entity  
- [ ] Unknown inbound never disappears — always message + thread + unresolved reason when unlinked  
- [ ] Duplicate provider message ID is idempotent  
- [ ] G13 written when entity is resolved  
- [ ] Contract tests for resolution chain + unresolved path + idempotency  

## Post-#101 gate (done)

1. ✅ FF integration → `7bc13d57`  
2. ✅ SHA + clean tree  
3. ✅ `make repo-health` PASSED  
4. ✅ CI vs baseline `f8569fa9`: same pre-existing red pattern (`docs-gates` / `backend-ci` / `frontend-static-qa` / `security-gates`); tip runs settling  
5. ✅ Removed `/tmp/hf-c0-1b-intent-policy`  
6. ✅ Created `/tmp/hf-c0-2-inbound-resolver`  
