# ADR-033: Lead lifecycle email policy owned at Own Company (sparse client / Vacancy override)

## Status

Accepted (architecture). **Implementation phased (P0–P4 + own-company SoT errata)** — see [lead-lifecycle-email-policy.md](../workflows/lead-lifecycle-email-policy.md).

## Context

Lead RODO and operational lifecycle emails (`application_received`, rejection, `moving_forward`) were configured only via **tenant-global** JSON (`lead_rodo_v1`, `lead_communication_v1`) with Meta admin + Message Templates UI and hardcoded HostFlow body fallbacks. That prevents firm-level compliance copy, hides misconfiguration, and conflicts with [ADR-005](ADR-005-three-level-settings-hierarchy.md) (operational module settings belong at Company / operating entity).

Delivery already must use Communication Pipeline ([ADR-031](ADR-031-compliance-outbound-requires-opaque-result.md), INV-17). This ADR does **not** change the send path — only **where policy and templates are chosen**.

**Product clarification (2026-07-31):** the GDPR art.14 notice identifies the **data controller** — normally the tenant’s **operating firm** (`OwnCompany`), not each prospect or employer client. Per-client RODO text is an optional white-label / joint-controller exception, not the default.

## Decision

1. **Operational SoT** for lead lifecycle email policy is the **operating firm** — `OwnCompany.extra.lead_lifecycle_email_v1` (same JSON shape as before).
2. **Client company** (`Lead.company_id` → `company_module_settings` / recruitment) may hold an **optional sparse or full overlay** (`lead_lifecycle_email_v1`) when that employer must appear in copy or use a different template.
3. **Vacancy** may hold a **sparse** override in JSONB `vacancies.settings_json` → `lead_lifecycle_email_override_v1` (no new table).
4. **Tenant** JSON remains **preset + cutover/migration adapter** only; after own-company cutover, live resolution prefers own company (+ optional client + vacancy).
5. **Resolver** `resolve_lifecycle_email_policy` is the single read SoT for runtime and Control Center preview.
6. **Fail-closed:** enabled purpose without resolvable template → no send + **operator-visible** lead stamp (`pending_policy` / ops `failed` + `policy_*` reason codes). Silent HostFlow marketing fallback is forbidden when the purpose is enabled.
7. **Control Center** lives under **Настройки → Коммуникации** (`/app/settings/communications/lead-lifecycle-email`). Meta Integrations is deep-link only. **Slice B** aligns the UI selector to Own Company (firm) with optional client override; until then APIs may still expose client-company rows as the override layer.
8. **RBAC:** write requires Communications settings admin class (`admin.users` + `communicationsAdmin`), not ordinary recruiter.
9. **Audit:** every policy PATCH (own company, client overlay, or vacancy) emits an audit event with before/after summary.

### Resolution order

```text
Vacancy sparse override
  → Client company overlay (optional; Lead.company_id)
    → OwnCompany.extra.lead_lifecycle_email_v1  (SoT)
      → Tenant preset (missing keys / pre-cutover)
        → Fail-closed
```

### `auto_on_first_action`

Normative triggers = RODO-gated actions only (Process, `request_info`, stage `contacted`, reserved lead contact APIs including `communication_call`). See workflow spec §4.

## Consequences

1. New own companies: ops off; **RODO evaluation is always on**. The engine decides whether outbound delivery is required. Missing firm template uses the HostFlow default body + `/legal/rodo.html`. Delivery uses tenant SMTP when configured, otherwise `info@hostflow.cc`. Tenants cannot disable fulfillment. HostFlow is not the named controller.
2. Leads **without** `company_id` (typical early B2B / sales inquiry) still resolve firm RODO via `own_company_id`.
3. Cutover: seed **own companies** from tenant preset; existing client-company `lead_lifecycle_email_v1` blocks remain valid as **overlays** (preserve prior per-client snapshots).
4. Leads module consumes resolver; Communication owns templates/policy buckets ([ADR-028](ADR-028-configuration-ownership.md)).
5. Does not reopen Stage 3 / Meta product track; does not claim Epic C complete.

## References

- [lead-lifecycle-email-policy.md](../workflows/lead-lifecycle-email-policy.md)
- [ADR-005](ADR-005-three-level-settings-hierarchy.md) · [ADR-031](ADR-031-compliance-outbound-requires-opaque-result.md) · [ADR-028](ADR-028-configuration-ownership.md)
- [lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md) §8.0.1–8.0.2
- [module-catalog-and-routing-map.md](module-catalog-and-routing-map.md)
- [c0-0 Communication canon §14](../tasks/c0-0-communication-canon.md)

## History

- 2026-07-29: Accepted — Company-owned lifecycle email policy + sparse vacancy override; Control Center under Communications.
- 2026-07-31: **Errata / product lock** — SoT = **OwnCompany** (firm); client company + vacancy = optional override; sales leads without `company_id` use firm policy. Resolver + own-company cutover = implementation slice A; Control Center IA + sales RODO rail = later slices.
- 2026-09-02: **Errata / legal floor** — `gdpr_notice` is a platform obligation for every tenant: `auto_on_lead_created` from `info@hostflow.cc`; missing firm template uses the HostFlow default body + `/legal/rodo.html`; stored `manual` / vacancy disable cannot skip the notice. Ops purposes unchanged (fail-closed).
- 2026-09-02: **Errata / compliance-by-design** — every lead gets a **mandatory obligation evaluation** (art. 13 vs art. 14, already provided, exemption, deadline). The tenant may configure controller identity, clause, sender, and copy, but cannot disable fulfillment. HostFlow mailbox is default **delivery infrastructure**, not the controller. Missing config uses the platform default rather than doing nothing. Custom sender falls back to the platform mailbox. Idempotent; audit records controller, notice version, and delivery channel.
