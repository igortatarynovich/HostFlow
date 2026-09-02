# Lead lifecycle email policy (v1)

**Status:** NORMATIVE (L2 — workflow / operating canon)  
**Date:** 2026-07-29 · **Updated:** 2026-09-02 (recruiter Control Center IA)  
**Owner:** Communication capability (settings + templates); Leads module consumes resolver  
**Parents:** [ADR-033](../architecture/ADR-033-lead-lifecycle-email-company-policy.md) · [ADR-005](../architecture/ADR-005-three-level-settings-hierarchy.md) · [ADR-031](../architecture/ADR-031-compliance-outbound-requires-opaque-result.md) · [c0-0 Communication canon §14](../tasks/c0-0-communication-canon.md) · [§8.0.1–8.0.2 intake continuity](lead-intake-resolution-and-activity-continuity.md)

> Control Center + **own-company** policy for **lead lifecycle emails only**.  
> Delivery remains Communication Pipeline only (INV-17 / ADR-031). No second SMTP path.

---

## 1. Perimeter (v1)

| In scope | Out of scope |
|----------|--------------|
| RODO / art.14 (`gdpr_notice`) | Questionnaire invite |
| Application received (`submission_acknowledgement`) — **recruitment / candidate leads only** | B2B client inquiries (`lead_type=client` + `client_lead`) — never `application_received` |
| Intake rejection (`intake_rejection_notice`) | Document expiry reminders |
| Moving forward (`moving_forward_notice`) | Inbox composer / manual follow-up |
| | Per-Meta-ad or per-form copy |

---

## 2. Hierarchy (locked — own-company SoT)

```text
Vacancy sparse override (vacancies.settings_json.lead_lifecycle_email_override_v1)
  → Client company overlay (optional; company_module_settings.recruitment.lead_lifecycle_email_v1)
    → OwnCompany.extra.lead_lifecycle_email_v1  (SoT — operating firm / data controller)
      → Tenant preset (lead_rodo_v1 / lead_communication_v1) — missing keys / pre-cutover only
        → Fail-closed (no silent HostFlow marketing body)
```

- **Own company** = `Lead.own_company_id` → `own_companies` (firm that operates the workspace).
- **Client** = `Lead.company_id` → employer / B2B account in `companies` — **optional overlay** when that client must be named in notice copy or needs a different template (white-label / joint controller). Not required for send.
- **Tenant JSON** after cutover = preset + migration adapter, not live SoT.
- **Net-new own company** defaults: ops emails **off**; RODO `manual`.
- **Cutover:** every existing **own company** receives a **snapshot** of the then-current tenant preset. Pre-existing client-company `lead_lifecycle_email_v1` rows remain as overlays.

**Product rule:** default is **one firm RODO**. Per-client RODO is the exception, not the model.

---

## 3. Policy shape (`lead_lifecycle_email_v1`)

Same JSON on OwnCompany (`extra`) and as optional client overlay in `company_module_settings` (`module_key = recruitment`).

| Field | Meaning |
|-------|---------|
| `rodo_send_mode` | `manual` \| `auto_on_lead_created` \| `auto_on_first_action` |
| `rodo_template_ref` | Hub template id and/or C2.1 template version id |
| `ops_enabled` | Master switch for ops notices |
| `application_received` / `rejection` / `moving_forward` | `{ enabled: bool, template_ref?: str }` |
| `channels` | MVP `["email"]` |

### Client overlay

Non-empty `lead_lifecycle_email_v1` on the client company **overlays** the own-company policy (set fields win). Empty / missing client block → firm policy only.

### Vacancy override

JSONB column `vacancies.settings_json` key `lead_lifecycle_email_override_v1`: sparse map  
`purpose → { enabled?: bool, template_ref?: str }` (ops keys may use `application_received` / `rejection` / `moving_forward`). Missing purpose keys inherit own company (+ client overlay).

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
3. **Surface:** Intake Decision rail alert + lead queue badge/filter **email policy blocked**. Control Center lists misconfigured purposes. **Sales rail** must expose the same RODO unlock (Send / source-provided) — product slice C.

Recipient silence without operator signal = **spec FAIL**.

Undelivered / deferred delivery outcomes (DSN feedback) remain separate and still block conversion.

Missing `own_company_id` on the lead → `block_code = missing_own_company` (no send).

---

## 6. Resolver SoT

`resolve_lifecycle_email_policy(tenant_id, own_company_id, company_id?, vacancy_id?, purpose) → PolicyDecision`:

- `send: bool`
- `template_ref: str | null`
- `source_layer: vacancy | client | own_company | tenant_preset | none`
- `block_code: null | disabled | policy_template_missing | policy_misconfigured | missing_own_company | …`
- `send_mode` (RODO only)

Runtime callers: `lead_rodo`, `lead_communications` via `resolve_lifecycle_email_policy_for_lead` (reads `lead.own_company_id` + optional `lead.company_id`). Binders still use Pipeline; template metadata comes from the decision.

**Resolve-preview (mandatory):** `GET /api/v1/settings/communications/lead-lifecycle-email/resolve-preview` returns the same `PolicyDecision` the runtime uses (`own_company_id` required; `company_id` optional overlay).

---

## 7. Control Center IA

- Route: `/app/settings/communications/lead-lifecycle-email`
- **Operator IA:** recruiter scenario first — status (needs setup / active / manual) → RODO information-duty card (document + auto-send + message) → in-page **Save and use** composer → automatic-message events table. Do not send the operator through Hub catalog → bind → save policy as the happy path.
- **Diagnostics:** `resolve-preview`, layer, `template_ref`, `block_code`, client overlay, and vacancy sparse override stay behind **Advanced settings** / **Show technical details**. They remain available for admins; they are not the default screen.
- Own-company GET/PUT remain the SoT blob on `OwnCompany.extra`. Client-company GET/PUT remain overlay editing.
- Meta Integrations: **deep-link only** (not SoT UI).
- Misconfiguration is a recruiter status + **Create message** on the same page (`enabled && !template_ref` for auto RODO modes).

### RBAC

| Action | Permission |
|--------|------------|
| Write own-company / client / vacancy policy | `admin.users` + Communications admin feature (`communicationsAdmin`) — same class as other Communications settings; **not** ordinary recruiter |
| Read / resolve-preview | Managers with lead/settings view may read; write remains restricted |

### Audit

Every successful PATCH of own-company `lead_lifecycle_email_v1`, client overlay, or vacancy `lead_lifecycle_email_override_v1` emits an audit event: actor, timestamp, ids, before/after summary (mode, flags, template_ref).

---

## 8. Delivery

All sends go through `prepare_and_send_communication` with opaque module result (ADR-031). Purposes unchanged: `gdpr_notice`, `submission_acknowledgement`, `intake_rejection_notice`, `moving_forward_notice`.

---

## 9. Implementation slices

| Slice | Deliverable |
|-------|-------------|
| P0 | Spec + ADR-033 + linkages |
| P1 | Schema + resolver + resolve-preview + audit hooks |
| P2 | Wire send paths + lead stamps |
| P3 | Control Center UI + rail badge + RBAC |
| P4 | Cutover seed snapshot + Meta deep-link |
| **A** | **Own-company SoT resolver + own-company cutover** (this errata) |
| **B** | Control Center: own-company selector + client override IA |
| **C** | Sales inquiry rail: RODO status + Send / source-provided (**done** — `SalesInquiryRodoSection` on call notes / client lead detail) |

---

## 10. References

- [leads module](../modules/leads.md)
- [workflows index](index.md)
- [ADR-028 configuration ownership](../architecture/ADR-028-configuration-ownership.md)
