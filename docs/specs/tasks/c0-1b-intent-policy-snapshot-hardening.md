# C0.1b — Intent Policy & Snapshot Hardening

**Status:** Active (next after PR #100 merge)  
**Branch (proposed):** `fix/communication-c0-intent-policy-hardening`  
**Worktree:** `/tmp/hf-c0-1b-intent-policy`  
**Base:** `integration/release-product-a-b` @ `f8569fa9` (PR #100 merged)  
**Parents:** [C0.0 Canon](c0-0-communication-canon.md) · [Epic C0](epic-c0-communication-integrity.md) · [C0.1 platform outbound](c0-1-platform-outbound.md)

> C0.1 delivered the first working Canon path:  
> `Intent → Policy → Resolvers → Command → Sender`  
> This slice **hardens** that path. It is **not** another module writer.

## Mandatory scope

1. **typed `IntentPolicyResult`** — machine-readable allow/deny with codes/reasons  
2. **Unified registry of communication Intents** — single SoT beyond ad-hoc seed enum usage  
3. **Full immutable message snapshot** — intent, template/version, origin, resolved links, policy decision, actor/automation, correlation/source event  
4. **Explicit matrix `entity × intent × channel`** — capability denial with clear reasons  
5. **Migration map of all legacy writers** — inventory + target Intent path for each  
6. **Ban new bypass send-paths** — no new module SMTP/email composers; fail closed in review/tests  
7. **Contract test:** production callers go through `CommunicationSender` (or `execute_communication_intent` / `prepare_and_send_communication`)

## Out of scope

- New product writers (questionnaire already on Canon; do not add RODO/lead/candidate engines here beyond migration **map**)  
- Template admin UI, automation authoring UI, campaigns (C2)  
- Inbox UX (C1)  
- Full PublicActionLinkService product  
- Consent evidence engine product (snapshot field for policy decision is in scope; full RODO store is not)

## Acceptance

- [ ] `IntentPolicyResult` used by prepare/execute path  
- [ ] Intent registry is the only place new intents are added  
- [ ] Message + delivery persist the full immutable snapshot contract  
- [ ] Entity × intent × channel matrix documented and enforced in `CapabilityResolver`  
- [ ] Legacy writer migration map checked into docs  
- [ ] Tests forbid new bypass patterns; existing production callers asserted via `CommunicationSender` / execute path  
- [ ] No new module-specific send engine introduced  

## Post-#100 gate (done)

1. ✅ FF integration → `f8569fa9`  
2. ✅ SHA + clean tree  
3. ✅ `make repo-health` PASSED  
4. ✅ CI vs baseline: `docs-gates` failure pre-existing (also red on `2569b3ea`); other tip runs still settling  
5. ✅ Removed `/tmp/hf-c0-outbound-linkage`  
6. ✅ Created `/tmp/hf-c0-1b-intent-policy`  
