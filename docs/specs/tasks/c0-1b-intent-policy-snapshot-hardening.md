# C0.1b — Intent Policy & Snapshot Hardening

**Status:** In progress  
**Branch:** `fix/communication-c0-intent-policy-hardening`  
**Worktree:** `/tmp/hf-c0-1b-intent-policy`  
**Base:** `integration/release-product-a-b` @ `f8569fa9` (PR #100 merged)  
**Parents:** [C0.0 Canon](c0-0-communication-canon.md) · [Epic C0](epic-c0-communication-integrity.md) · [Legacy migration map](c0-1b-legacy-writers-migration-map.md)

> Hardens the Canon path so registry, policy, and snapshot cannot drift.  
> **Not** another module writer.

## Implementation order (locked)

1. **Unified Intent Registry** — `intent_registry.py` (SoT)  
2. **Typed `IntentPolicyResult`** — `intent_policy.py` / `evaluate_intent_policy`  
3. **Matrix entity × intent × channel** — derived from registry; deny unknown  
4. **Full immutable snapshot** — `snapshot.py` → message/delivery payload  
5. **Legacy writers migration map** — [c0-1b-legacy-writers-migration-map.md](c0-1b-legacy-writers-migration-map.md)  
6. **Bypass ban** — allowlist contract test (allowlist shrinks only)

## Merge criteria

- [x] New intent cannot be added without registry entry (enum ↔ registry test)  
- [x] Forbidden entity/intent/channel blocked before message create  
- [x] Snapshot reconstructs send without live templates/settings  
- [x] Questionnaire production caller uses `prepare_and_send` / Sender path  
- [x] All legacy writers listed with removal plan  
- [x] New legacy exceptions forbidden by allowlist test  

## Out of scope

- Migrating legacy writers in this PR (map only)  
- Template admin / automations / campaigns (C2)  
- Inbox UX (C1)  
- Full PublicActionLinkService / consent evidence store  

## After merge

Proceed to **C0.2 inbound resolver** on a stable outbound model.
