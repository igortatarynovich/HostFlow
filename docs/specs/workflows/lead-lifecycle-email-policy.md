# Lead lifecycle email policy (v1)

**Status:** NORMATIVE (L2 — workflow / operating canon)  
**Date:** 2026-07-29  
**Owner:** Communication capability (settings + templates); Leads module consumes resolver  
**Parents:** [ADR-033](../architecture/ADR-033-lead-lifecycle-email-company-policy.md) · [ADR-005](../architecture/ADR-005-three-level-settings-hierarchy.md) · [ADR-031](../architecture/ADR-031-compliance-outbound-requires-opaque-result.md) · [c0-0 Communication canon §14](../tasks/c0-0-communication-canon.md) · [§8.0.1–8.0.2 intake continuity](lead-intake-resolution-and-activity-continuity.md)

> Control Center + company/vacancy policy for **lead lifecycle emails only**.  
> Delivery remains Communication Pipeline only (INV-17 / ADR-031). No second SMTP path.

---

## 1. Perimeter (v1)

| In scope | Out of scope |
|----------|--------------|
| RODO / art.14 (`gdpr_notice`) | Questionnaire invite |
| Application received (`submission_acknowledgement`) | Document expiry reminders |
| Intake rejection (`intake_rejection_notice`) | Inbox composer / manual follow-up |
| Moving forward (`moving_forward_notice`) | Per-Meta-ad or per-form copy |

---

## 2. Hierarchy (locked 1A / 2A)

```text
Vacancy sparse override (vacancies.settings_json.lead_lifecycle_email_override_v1)
  → Company Module Settings (recruitment.settings_json.lead_lifecycle_email_v1)
    → Tenant preset (lead_rodo_v1 / lead_communication_v1) — missing keys only
      → Fail-closed (no silent HostFlow marketing body)
```

- **Client** = `Lead.company_id` (Company).
- **Tenant JSON** after cutover = preset + migration adapter, not live SoT.
- **Net-new company** defaults: ops emails **off**; RODO `manual`.
- **Cutover:** every existing company receives a **snapshot** of the then-current tenant preset (not “all off”).

---

## 3. Company settings shape (`lead_lifecycle_email_v1`)

Stored under `company_module_settings` where `module_key = recruitment` (Sales path may mirror later under `sales`).

Runtime JSON (flat keys; nested plan notation maps 1:1):

| Field | Meaning |
|-------|---------|
| `rodo_send_mode` | `manual` \| `auto_on_lead_created` \| `auto_on_first_action` |
| `rodo_template_ref` | Hub template id and/or C2.1 template version id |
| `ops_enabled` | Master switch for ops notices |
| `application_received` / `rejection` / `moving_forward` | `{ enabled: bool, template_ref?: str }` |
| `channels` | MVP `["email"]` |

### Vacancy override

JSONB column `vacancies.settings_json` key `lead_lifecycle_email_override_v1`: sparse map  
`purpose → { enabled?: bool, template_ref?: str }` (ops keys may use `application_received` / `rejection` / `moving_forward`). Missing purpose keys inherit company.

---

## 4. `auto_on_first_action` trigger set (normative)

“First action” = first call into a **RODO-gated lead action** while notice is unsatisfied:

| Trigger | Boundary |
|---------|----------|
| Manual Process | `POST /api/v1/leads/{id}/process` |
| Intake `request_info` | intake-decision |
| CRM stage → `contacted` | lead stage patch |
| Reserved lead-scoped contact APIs (when wired) | `communication_call` / `communication_email` / `communication_whatsapp` / `request_documents` |

**Not** first-action: arbitrary other stage changes, first inbound email reply, inbox composer send.

---

## 5. Fail-closed + operator signal (never silent)

If purpose is **enabled** (or RODO mode requires outbound) but template is missing / unresolvable / channel unavailable:

1. **Do not send.**
2. **Stamp the lead:**
   - RODO: `normalized.rodo.status = pending_policy` with `failure_reason_code` ∈ `{policy_template_missing, policy_misconfigured}` + `failure_reason`; gate stays unsatisfied (`LEAD_RODO_REQUIRED`).
   - Ops: `normalized.lead_communication_v1.<event>.status = failed` with the same codes.
3. **Surface:** Intake Decision rail alert + lead queue badge/filter **email policy blocked**. Control Center lists misconfigured company purposes.

Recipient silence without operator signal = **spec FAIL**.

Undelivered / deferred delivery outcomes (DSN feedback) remain separate and still block conversion.

---

## 6. Resolver SoT

`resolve_lifecycle_email_policy(tenant_id, company_id, vacancy_id, purpose) → PolicyDecision`:

- `send: bool`
- `template_ref: str | null`
- `source_layer: vacancy | company | tenant_preset | none`
- `block_code: null | disabled | policy_template_missing | policy_misconfigured | …`
- `send_mode` (RODO only)

Runtime callers: `lead_rodo`, `lead_communications`. Binders still use Pipeline; template metadata comes from the decision.

**Resolve-preview (mandatory):** `GET /api/v1/settings/communications/lead-lifecycle-email/resolve-preview` returns the same `PolicyDecision` the runtime uses.

---

## 7. Control Center IA

- Route: `/app/settings/communications/lead-lifecycle-email`
- Company selector → four purpose cards → **Effective policy** panel (resolve-preview) → Vacancy overrides → links to SMTP + templates.
- Meta Integrations: **deep-link only** (not SoT UI).
- Misconfiguration strip: `enabled && !template_ref`.

### RBAC

| Action | Permission |
|--------|------------|
| Write company/vacancy policy | `admin.users` + Communications admin feature (`communicationsAdmin`) — same class as other Communications settings; **not** ordinary recruiter |
| Read / resolve-preview | Managers with lead/settings view may read; write remains restricted |

### Audit

Every successful PATCH of company `lead_lifecycle_email_v1` or vacancy `lead_lifecycle_email_override_v1` emits an audit event: actor, timestamp, company/vacancy id, before/after summary (mode, flags, template_ref).

---

## 8. Delivery

All sends go through `prepare_and_send_communication` with opaque module result (ADR-031). Purposes unchanged: `gdpr_notice`, `submission_acknowledgement`, `intake_rejection_notice`, `moving_forward_notice`.

---

## 9. Implementation slices

| Slice | Deliverable |
|-------|-------------|
| P0 | This spec + ADR-033 + linkages |
| P1 | Schema + resolver + resolve-preview + audit hooks |
| P2 | Wire send paths + lead stamps |
| P3 | Control Center UI + rail badge + RBAC |
| P4 | Cutover seed snapshot + Meta deep-link |

---

## 10. References

- [leads module](../modules/leads.md)
- [workflows index](index.md)
- [ADR-028 configuration ownership](../architecture/ADR-028-configuration-ownership.md)
