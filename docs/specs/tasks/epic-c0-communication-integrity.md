# Epic C0 — Communication Integrity

**Status:** C0.0–C0.3 ✅ — **Communication Platform Foundation complete** (not Epic C complete)  
**Parents:** [Foundation](../architecture/communication-platform-foundation.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [C0.0 Communication Canon](c0-0-communication-canon.md)

> Platform integrity slices C0.0–C0.3 are done (**Foundation complete**).  
> Next: **[C1](c1-communication-inbox-workspace.md)** → C2 → **[Epic C Complete Gate](../gates/epic-c-complete-gate.md)** → Governance.  
> **Epic C — complete** only after the gate. This epic is **not** Stage 3 Sales.

## Why before Stage 3 slice 3

Continuing Sales product flow on unbound / mis-linked threads (or module-specific email engines) makes every later Sales↔Communication surface more expensive. Canon + integrity first, then Sales module completion, then Inbox UX, then C2 product surfaces.

## Observed GAPs (facts)

1. **Unbound outbound threads** — send from inquiry / application / client / candidate / order already knows origin; G13 `communication_thread_entity_link` must be written in the same business operation. Address fallback must not be the primary outbound mechanism.
2. **Inbound resolver too weak** — unlinked became common; resolver must prefer reply headers → provider IDs → exact contact → active inquiry/application → client/candidate → only then unresolved.
3. **`lead.communication.failed`** — likely wrong event model after Thread-primary; delivery state belongs on Message/Delivery with human-readable history text.
4. **Parallel writers / hardcoded public URLs** — questionnaire, lead ops, RODO, candidate notifications still diverge from one command (see C0.0 anti-patterns).
5. **Meta Intake Completeness** — separate sprint (not inside C0); see [meta-intake-completeness.md](meta-intake-completeness.md).

---

## Slice C0.0 — Communication Canon & Contracts

**Task:** [c0-0-communication-canon.md](c0-0-communication-canon.md)  
**Type:** normative docs + **contract seams in PR #100** (no new product features)

### Delivers

- **Communication Intent** as the primary business layer  
- Scope / ownership of the Communication platform  
- `CommunicationCommand`, TemplateResolver, LinkResolver, CapabilityResolver  
- Action policy, thread resolution, message snapshot contracts  
- Consent/RODO, automation, settings ownership (contracts)  
- Idempotency + transaction boundaries  
- Migration path + anti-patterns  

### Acceptance

Canon linked from queue + this epic; Intent-first documented; C2 scope expanded; PR #100 implements seams without shipping C2/Inbox/consent engines.

---

## Slice C0.1 — Universal outbound foundation ✅

**Branch:** `fix/communication-c0-outbound-linkage`  
**PR:** [#100](https://github.com/igortatarynovich/HostFlow/pull/100) — **merged** (`f8569fa9`)  
**Normative capability note:** [c0-1-platform-outbound.md](c0-1-platform-outbound.md)  
**Canon:** [c0-0-communication-canon.md](c0-0-communication-canon.md)  

**Result:** first working Canon path `Intent → Policy → Resolvers → Command → Sender` + G13.

### Main contract

> **Cannot** create an outbound message from a HostFlow entity without a durable `thread ↔ origin entity` link.  
> Unknown **delivery** result is allowed.  
> Unbound thread when origin is known is **not** allowed.

### GAP audit (required before writing code)

**Done:** [c0-1-outbound-linkage-gap-audit.md](c0-1-outbound-linkage-gap-audit.md) @ `2569b3ea`.

### Locked in PR #100 (contract alignment — do not expand into product)

- `CommunicationIntent` + IntentPolicy seed  
- `CommunicationCommand` + `prepare_and_send_communication` + `CommunicationSender`  
- `CapabilityResolver` / `TemplateResolver` / `LinkResolver` (thin impls)  
- Platform `send_communication` executor (thread + G13 + message + delivery)  
- Questionnaire as **first intent caller** through resolvers + sender port  
- Thread API/UI `entity_links` with temporary legacy fallback  

```text
request_questionnaire → TemplateResolver + LinkResolver → CommunicationCommand
  → prepare_and_send → send_communication → G13 + snapshot + outbox
```

### Not in C0.1 / #100

- Bulk/campaign engine, template admin product, automation authoring UI → [Epic C2](epic-c2-communication-campaigns.md)  
- Full PublicActionLinkService, consent evidence engine  
- Inbound resolver (C0.2), delivery diagnostics UX (C0.3), Inbox (C1)

---

## Slice C0.1b — Intent Policy & Snapshot Hardening ✅

**Task:** [c0-1b-intent-policy-snapshot-hardening.md](c0-1b-intent-policy-snapshot-hardening.md)  
**PR:** [#101](https://github.com/igortatarynovich/HostFlow/pull/101) — **merged** (`7bc13d57`)

Mandatory delivered: typed `IntentPolicyResult`, unified Intent registry, full immutable snapshot, entity × intent × channel matrix, legacy writer migration map, ban bypass send-paths, contract test that production callers use `CommunicationSender`.

---

## Slice C0.2 — Inbound resolver and threading ✅

**Task:** [c0-2-inbound-resolver.md](c0-2-inbound-resolver.md)  
**PR:** [#102](https://github.com/igortatarynovich/HostFlow/pull/102) — **merged** (`00ea61e9`)

### Main contract

Every inbound message is deterministically linked to a thread/entity **or** enters an explicit unresolved queue. No lost inbound.

---

## Slice C0.3 — Delivery diagnostics and history ✅

**Task:** [c0-3-delivery-diagnostics.md](c0-3-delivery-diagnostics.md)  
**Legacy map:** [c0-3-legacy-delivery-migration-map.md](c0-3-legacy-delivery-migration-map.md)  
**PR:** [#104](https://github.com/igortatarynovich/HostFlow/pull/104) — **merged** (`95f2a525`)

### Main contract

For every send and delivery attempt the operator knows what happened, where it failed, whether retry is allowed, and what to show — without server logs.

### Foundation lock

After C0.3: [Communication Platform Foundation — complete](../architecture/communication-platform-foundation.md).

### Next

**[C1 Communication Inbox Workspace](c1-communication-inbox-workspace.md)** — not Stage 3.

---

## Out of scope (all C0 slices)

- Inbox UX redesign (Epic C1)  
- Templates / automations / campaigns **product** (Epic C2) — contracts only in C0.0  
- Signature policy product UI (may land with C2 / settings)  
- Meta Intake Completeness (separate epic)  
- Stage 3 Sales slice 3+ product flow  
- Historical repair of ambiguous unbound threads beyond fail-closed gates (may follow C0.1 gate)  
