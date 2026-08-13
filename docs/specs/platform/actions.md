# Actions — contract inventory (confirmed slice)

**Hierarchy:** L2 — Action contract + confirmed-slice rows; **not** the runtime Action Registry  
**Decision record:** [`ADR-047`](../architecture/ADR-047-actions.md)  
**Parent model:** [`ADR-038`](../architecture/ADR-038-platform-standardization-model.md) · [`platform-standardization-model.md`](platform-standardization-model.md) (area `actions`)  
**Implementation path:** [`ADR-019`](../architecture/ADR-019-automation-capability-entitlement-control-plane.md) §14.7 / **3A-3**  
**Related:** [`ADR-012`](../architecture/ADR-012-activity-notification-operating-layer.md) · [`ADR-009`](../architecture/ADR-009-document-hub-platform-layer.md) · [`ADR-036`](../architecture/ADR-036-four-trust-roles-rbac.md) · [`relationships.md`](relationships.md)  
**Owner:** Platform Automations (registry target) + action-owning modules  
**Slice:** Documents · Activity/Notifications · Process/handoff · platform notification send

---

## 1. Row contract

| Field | Meaning |
|-------|---------|
| `action_code` | Dotted `qualified_code` |
| `subject_kind` | Primary subject |
| `effect_summary` | Successful effect |
| `owner` | Semantics owner |
| `required_capability` | Entitlement gate |
| `permission` | Authz surface |
| `idempotency` | Key strategy (descriptive) |
| `rollback` | Compensation notes |
| `writers` | Invokers |
| `status` | `confirmed` \| `fragment` |
| `sot_refs` | Paths |
| `notes` | Aliases / deferrals |

---

## 2. Rules summary (from ADR-047)

1. Action ≠ Permission ≠ Capability ≠ Event ≠ Intent ≠ RelationshipKind.
2. Automation invokes **Actions** only (target); never raw stage/DB writes across modules.
3. Confirmed slice only; CRM 3A-3 codes stay **fragment** until registry ships.
4. C2.2 `intent_key` is **not** an `action_code`.
5. Docs-only — no `platform/actions/` package in this PR.

---

## 3. Confirmed slice (`status=confirmed`)

| action_code | subject_kind | effect_summary | owner | required_capability | permission | idempotency | rollback | writers | sot_refs | notes |
|-------------|--------------|----------------|-------|---------------------|------------|-------------|----------|---------|----------|-------|
| `document.upload` | `document` | Presign / register file bytes for a document instance | Document Hub | Documents / Hub exposure (Catalog) | Documents write / upload routes | upload session / object key | abort unused upload | Hub API · entitled modules | ADR-009, documents router / hub services | — |
| `document.review` | `document` | Approve or reject review decision | Document Hub | Documents review capability (module) | Reviewer roles / documents review perm | review decision id | reverse via new review / policy | Reviewers · Hub | ADR-009, document review flows | Effect is review dimension (ADR-039), not a status bag |
| `document.mutate` | `document` | Non-destructive metadata / non-file mutate | Document Hub | Documents | Documents mutate / write | request / etag if any | compensate with prior metadata | Hub API | ADR-014 access model, document locks | Distinct from destructive |
| `document.destructive_mutate` | `document` | Replace/delete under process locks | Document Hub | Documents | Destructive mutate + lock checks | destructive op id | often `none` / tombstone | Hub API · privileged roles | `document_visibility_and_locks.py`, ADR-014 | PE locks may block |
| `activity.create` | `activity` | Create Activity work item (optional related entity) | Platform Activity (ADR-012) | — (platform) | Activity create / module producer perms | producer idempotency key (target) | cancel/close activity | Modules · Automations (target) | ADR-012, `activity` model | Target absorb path for reminder-like side effects |
| `notifications.send` | `notification` | Dispatch a notification | Platform Notifications | `automation.conditional_actions` (when automated) | Notifications send / role | notification id / dedupe key | suppress / mark failed | Notifications · Automations | ADR-019 §14.7 example | — |
| `process.transition` | process subject (entity + pipeline) | Evaluate/apply a PE-allowed transition | Process Engine consumers | `process_engine` evaluate / module install | Role-scoped transition perms | transition attempt id | PE compensation / reject | Module services via PE | PE manifests, process-engine.md | Gate **rules** configure readiness; they are not this Action |
| `handoff.submit` | `candidate` (handoff edge) | Open/submit handoff to destination | Recruitment / PE bridge | `recruitment.to_hr_transfer` (when entitlement applies) | `recruitment.handoff.submit` (module manifest) | handoff id | cancel handoff per policy | Recruitment writers · orchestrator (later) | handoff-contract, module_registry manifests | RelationshipKind `candidate_handoff_to_destination` is the edge; this is the op |
| `handoff.accept` | HR / destination case | Accept inbound handoff | HR | HR module / onboarding entitlement | `hr.handoff.accept` | handoff accept id | reject / return per policy | HR writers | handoff-contract, module manifests | — |

---

## 4. Fragment / out_of_slice (do not invent as confirmed)

| Evidence / ADR-019 example | Why fragment |
|----------------------------|--------------|
| `candidate.change_stage`, `candidate.open_transfer`, `candidate.execute_transfer` | ADR-019 **3A-3** public CRM actions — not confirmed in this Docs/PE slice |
| `hr.create_employee`, `sales.convert_application`, `finance.create_invoiceable_event` | Cross-module CRM/finance — 3A-3+ |
| `assignment.assign_owner` | Listed in ADR-019; needs ownership card before confirmed |
| `automation_rules` `create_reminder` / `actions_json` | Legacy side-effect string → migrate toward `activity.create` / registry |
| C2.2 `intent_key` values (`request_documents`, `invite_to_interview`, …) | **Intent ≠ Action**; Communications egress |
| PE rule codes (`ready_for_handoff_gate`, `handoff_internal_hr`, …) | ProcessRule / config, not Action vocabulary |
| `uos_auto_activities` direct creates | Absorb into Action Registry / `activity.create` |

---

## 5. Forbidden mixes (quick check)

| If you are about to… | Use instead |
|----------------------|-------------|
| Check only a permission string for “can automate X” | Capability + Action + Permission chain |
| Fire C2.2 intent and call it an Action | Intent (Comms) ± later map to Action |
| Let automation UPDATE `candidate.stage` in SQL | `candidate.change_stage` via Action Registry (3A-3) |
| Add a RelationshipKind for “do review” | `document.review` Action |
| Treat handoff **status** as an Action | State dimension + `handoff.submit` / `handoff.accept` |

---

## 6. History

- 2026-08-13: Initial L2 Actions inventory under ADR-047; area `actions` → exists; 3A-3 runtime and CRM public actions deferred as fragment.
