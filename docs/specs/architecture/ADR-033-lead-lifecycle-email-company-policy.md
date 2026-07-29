# ADR-033: Lead lifecycle email policy owned at Company (sparse Vacancy override)

## Status

Accepted (architecture). **Implementation phased (P0–P4)** — see [lead-lifecycle-email-policy.md](../workflows/lead-lifecycle-email-policy.md).

## Context

Lead RODO and operational lifecycle emails (`application_received`, rejection, `moving_forward`) were configured only via **tenant-global** JSON (`lead_rodo_v1`, `lead_communication_v1`) with Meta admin + Message Templates UI and hardcoded HostFlow body fallbacks. That prevents per-client copy, hides misconfiguration, and conflicts with [ADR-005](ADR-005-three-level-settings-hierarchy.md) (operational module settings belong at Company).

Delivery already must use Communication Pipeline ([ADR-031](ADR-031-compliance-outbound-requires-opaque-result.md), INV-17). This ADR does **not** change the send path — only **where policy and templates are chosen**.

## Decision

1. **Operational SoT** for lead lifecycle email policy is **Company Module Settings** (`module_key = recruitment`, block `lead_lifecycle_email_v1` in `settings_json`).
2. **Vacancy** may hold a **sparse** override in JSONB `vacancies.settings_json` → `lead_lifecycle_email_override_v1` (no new table).
3. **Tenant** JSON remains **preset + cutover/migration adapter** only; after cutover seed, live resolution prefers company (+ vacancy).
4. **Resolver** `resolve_lifecycle_email_policy` is the single read SoT for runtime and Control Center preview.
5. **Fail-closed:** enabled purpose without resolvable template → no send + **operator-visible** lead stamp (`pending_policy` / ops `failed` + `policy_*` reason codes). Silent HostFlow marketing fallback is forbidden when the purpose is enabled.
6. **Control Center** lives under **Настройки → Коммуникации** (`/app/settings/communications/lead-lifecycle-email`). Meta Integrations is deep-link only.
7. **RBAC:** write requires Communications settings admin class (`admin.users` + `communicationsAdmin`), not ordinary recruiter.
8. **Audit:** every policy PATCH (company or vacancy) emits an audit event with before/after summary.

### Resolution order

Vacancy sparse key → Company `lead_lifecycle_email_v1` → Tenant preset (missing keys) → fail-closed.

### `auto_on_first_action`

Normative triggers = RODO-gated actions only (Process, `request_info`, stage `contacted`, reserved lead contact APIs). See workflow spec §4.

## Consequences

1. New companies: ops off / RODO manual until configured (or preset applied).
2. Cutover: existing companies get a **snapshot** of current tenant preset — behavior must not mass-drop overnight.
3. Leads module consumes resolver; Communication owns templates/policy buckets ([ADR-028](ADR-028-configuration-ownership.md)).
4. Does not reopen Stage 3 / Meta product track; does not claim Epic C complete.

## References

- [lead-lifecycle-email-policy.md](../workflows/lead-lifecycle-email-policy.md)
- [ADR-005](ADR-005-three-level-settings-hierarchy.md) · [ADR-031](ADR-031-compliance-outbound-requires-opaque-result.md) · [ADR-028](ADR-028-configuration-ownership.md)
- [lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md) §8.0.1–8.0.2
- [module-catalog-and-routing-map.md](module-catalog-and-routing-map.md)
- [c0-0 Communication canon §14](../tasks/c0-0-communication-canon.md)

## History

- 2026-07-29: Accepted — Company-owned lifecycle email policy + sparse vacancy override; Control Center under Communications.
