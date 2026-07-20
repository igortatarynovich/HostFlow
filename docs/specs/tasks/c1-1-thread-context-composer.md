# C1.1 — ThreadContext & Capability-driven Composer

**Status:** Complete (ship with PR #107)  
**Parents:** [C1 Inbox Workspace](c1-communication-inbox-workspace.md) · Communication Platform Foundation

## Role of ThreadContext

**ThreadContext is not a second Communication aggregate and not a SoT.**

It is a **read model / workspace contract** assembled from canonical sources:

| Source | Contributes |
|--------|-------------|
| Thread | identity projection, ownership, unread, SLA fields |
| G13 links | linked entities / origin |
| Messages | participants, draft recipient hints |
| Queue projection | `active_queues` membership |
| CapabilityResolver + Intent Policy | allowed intents/channels, policy denials |
| Delivery diagnostics | lightweight `delivery_summary` |
| `thread_meta.composer_draft` | draft projection |

Rule: **aggregates and returns Workspace data; never owns it.**  
No ThreadContext table, no dual-write of assignee/unread/capabilities/delivery.

## Contract (four blocks)

```text
identity        → thread projection, linked_entities, participants, origin
work_state      → queues, ownership, unread, SLA, next_action (nullable)
capabilities    → allowed intents/channels, defaults, policy_denials
workspace       → draft, delivery_summary, timeline_cursor, ui_hints
meta            → context_version, generated_at (freshness / diagnostics; not locking)
```

`ui_hints` = neutral presentation metadata only (no module business logic).  
`generated_at` / `context_version` = snapshot freshness for stale UI diagnosis and future live updates — not optimistic locking.

**Scale rule:** ThreadContext scales with Thread, not Message history (bounded message scan for participants only; timeline is a separate request).

API: `GET /communications/threads/{id}/context`  
Compat: `GET …/capabilities` (slice of `capabilities` block).

## Composer

Accepts only:

* ThreadContext
* user input
* selected intent/channel from the allowed set

On send, Composer does **not** assert policy. Backend re-checks:

```text
intent + thread origin/source data + actor + channel
```

Frontend capabilities = display. Backend policy = authority (stale context → typed denial).

## In scope for interactive Workspace

```text
Recruitment UI → ThreadContext → Composer
Services UI    → ThreadContext → Composer
Manual AI draft in Workspace → ThreadContext → Composer
```

## Out of scope (do not force through ThreadContext)

```text
Automation → CommunicationIntent (platform adapter)
Campaign   → Campaign recipient context → CommunicationIntent
Bulk / server processes → CommunicationCommand / Intent path
```

Interactive read models must not become mandatory dependencies of server-side engines.

## Definition of Done

- [x] One endpoint returns ThreadContext (four-block read model)
- [x] Composer does not load links / capabilities / diagnostics itself
- [x] Intent and channel taken only from context allow-lists in UI
- [x] Backend re-applies policy on outbound create (`composer_policy`)
- [x] Stale / denied combinations return typed denial (`composer_policy_denied` + `reason_code`)
- [x] No `module == …` Composer branches
- [x] ThreadContext has no persistence of its own
- [x] Contract test forbids Composer calling legacy capability/diagnostics APIs
- [x] Read-only contract: building context does not mutate drafts/unread/ownership/queues
- [x] Completeness contract: Composer gets intents/channels/policy/links from one context
- [x] `context_version` + `generated_at` on every snapshot

## After C1.1 → C1.2 Workspace Actions

Ownership, assign/reassign, unread/read, next action, SLA, queue transitions — around **Thread**, without growing Composer responsibility.
