# Lead lifecycle email policy (v1)

**Status:** NORMATIVE (L2 — workflow / operating canon)  
**Date:** 2026-07-29 · **Updated:** 2026-09-04 (restricted RODO compliance-state transitions)  
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
        → Platform floor for `gdpr_notice` (mandatory evaluation; default body + HostFlow mailbox if tenant sender is absent)
```

- **Own company** = `Lead.own_company_id` → `own_companies` (firm that operates the workspace).
- **Client** = `Lead.company_id` → employer / B2B account in `companies` — **optional overlay** when that client must be named in notice copy or needs a different template (white-label / joint controller). Not required for send.
- **Tenant JSON** after cutover = preset + migration adapter, not live SoT.
- **Net-new own company** defaults: ops emails **off**; RODO **platform-mandatory evaluation** (fulfillment when the engine requires delivery). Tenants cannot disable the obligation; missing template/sender uses the HostFlow default.
- **Cutover:** every existing **own company** receives a **snapshot** of the then-current tenant preset. Pre-existing client-company `lead_lifecycle_email_v1` rows remain as overlays.

**Product rule:** default is **one firm RODO**. Per-client RODO is the exception, not the model.

---

## 3. Policy shape (`lead_lifecycle_email_v1`)

Same JSON on OwnCompany (`extra`) and as optional client overlay in `company_module_settings` (`module_key = recruitment`).

| Field | Meaning |
|-------|---------|
| `rodo_send_mode` | Platform floor: stored `manual` / `auto_on_first_action` are coerced. The tenant cannot disable evaluation or fulfillment. The engine decides whether outbound delivery is required. |
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

## 4. Obligation engine (mandatory)

After a new lead is recorded, HostFlow **evaluates** the information obligation. The tenant cannot disable this step. Evaluation is not “send art.14 on every `lead_created`”.

**Product invariant:** Tenant may configure how the RODO information obligation is fulfilled, but cannot disable its fulfillment. HostFlow provides a platform default whenever tenant-specific configuration is absent.

**Technical invariant:** No lead may silently bypass compliance evaluation. An unresolved or failed compliance obligation must remain explicitly actionable until resolved. The engine has no state “could not determine → did nothing”.

Canonical `compliance_state` values on `Lead.normalized.rodo`:

| State | Meaning | Gate |
|-------|---------|------|
| `compliant` | Obligation already fulfilled; assessment proof exists (notice at source / already notified) | Closed |
| `delivery_required` | Outbound fulfillment required | Open — auto-send |
| `delivered` | Send completed; delivery evidence recorded | Closed |
| `exempt` | Lawful exception **with** reason code | Closed |
| `review_required` | Engine cannot safely classify (unknown source, exemption without reason) | Open — operator review |
| `delivery_failed` | Obligation exists; tenant SMTP then platform SMTP exhausted, or no channel | Open — retry / alert |

Two evidence objects (never mixed):

- **`assessment`** — why art.13 / art.14 / exempt / already provided / review: source, collection path, reason_code, notice_at_source, controller, evaluated_at.
- **`delivery_evidence`** — what was sent or attempted: controller, recipient, timestamp, notice version/hash, template, sender, channel, `attempts[]`, delivery status.

Delivery path: tenant SMTP → on failure platform SMTP (`info@hostflow.cc`) → on failure `delivery_failed` with both attempts (webhook notify is **not** GDPR proof). Idempotency: the same obligation is not sent twice because of webhook replay.

**Transitions (no universal mark-resolved):**

| From | To | Required proof |
|------|----|----------------|
| unset / `delivery_required` / `review_required` | `delivered` | Successful SMTP `delivery_evidence` |
| `delivery_failed` | `delivered` | Successful SMTP send only |
| `review_required` | `compliant` | Assessment proof: notice at source **or** operator attestation (`actor_id`) |
| `review_required` | `exempt` | Valid exemption reason code |
| `delivery_failed` | `compliant` / `exempt` | Same proofs as above (operator attestation or lawful code) |
| `delivered` | `delivery_failed` | Bounce / DSN feedback |
| any closed state | another closed state | **Forbidden** (no mark resolved) |

`delivery_failed` is not rewritten back to `delivery_required` on re-evaluation. Covered-at-source is an explicit operator (or ingest-captured notice) path with `assessment` evidence — not a silent close.

---

## 5. Retry before gated action

If the information obligation is still unsatisfied when a RODO-gated action runs (ingest had no email, send failed, etc.), the platform re-evaluates and retries fulfillment before blocking. Triggers:

| Trigger | Boundary |
|---------|----------|
| Manual Process | `POST /api/v1/leads/{id}/process` |
| Intake `request_info` | intake-decision |
| CRM stage → `contacted` | lead stage patch |
| Reserved lead-scoped contact APIs (when wired) | `communication_call` / `communication_email` / `communication_whatsapp` / `request_documents` |

This is a **retry of fulfillment**, not an opt-out of ingest evaluation. Stored `auto_on_first_action` is coerced; the engine still decides whether delivery is required.

---

## 6. Fail-closed + operator signal (never silent)

**Exception — `gdpr_notice`:** this purpose is a **platform compliance policy**. Resolve always returns `send=true` when the obligation engine requires delivery. Missing tenant/own-company template uses the HostFlow platform body and public clause (`/legal/rodo.html`). **Controller identity is the operating firm (OwnCompany)**, not HostFlow. Delivery uses tenant SMTP when configured; if the custom sender is missing or fails, HostFlow falls back to the platform mailbox (`info@hostflow.cc`). Vacancy `enabled: false` and stored `manual` / `auto_on_first_action` cannot skip evaluation. Duplicate outbound is skipped when the engine records `source_provided`, already-notified, or a lawful exemption.

If an **ops** purpose is **enabled** but template is missing / unresolvable / channel unavailable:

1. **Do not send.**
2. **Stamp the lead:**
   - Ops: `normalized.lead_communication_v1.<event>.status = failed` with `failure_reason_code` ∈ `{policy_template_missing, policy_misconfigured}` + `failure_reason`.
3. **Surface:** Intake Decision rail alert + lead queue badge/filter **email policy blocked**. Control Center lists misconfigured purposes.

Recipient silence without operator signal = **spec FAIL** (ops purposes).

Undelivered / deferred delivery outcomes (DSN feedback) remain separate and still block conversion.

Missing `own_company_id` on the lead → ops purposes `block_code = missing_own_company` (no send). **RODO evaluation still runs**; fulfillment uses the platform default notice and mailbox, naming the firm when it can be resolved.

---

## 7. Resolver SoT

`resolve_lifecycle_email_policy(tenant_id, own_company_id, company_id?, vacancy_id?, purpose) → PolicyDecision`:

- `send: bool`
- `template_ref: str | null`
- `source_layer: vacancy | client | own_company | tenant_preset | platform | none`
- `block_code: null | disabled | policy_template_missing | policy_misconfigured | missing_own_company | …`
- `send_mode` (RODO only)

Runtime callers: `lead_rodo`, `lead_communications` via `resolve_lifecycle_email_policy_for_lead` (reads `lead.own_company_id` + optional `lead.company_id`). Binders still use Pipeline; template metadata comes from the decision.

**Resolve-preview (mandatory):** `GET /api/v1/settings/communications/lead-lifecycle-email/resolve-preview` returns the same `PolicyDecision` the runtime uses (`own_company_id` required; `company_id` optional overlay).

---

## 8. Control Center IA

- Route: `/app/settings/communications/lead-lifecycle-email`
- **Operator IA:** recruiter scenario first — status (Active — managed by HostFlow) → RODO information-duty card (document + locked obligation + optional message / sender) → in-page **Save and use** composer → automatic-message events table. The information obligation cannot be turned off.
- **Diagnostics:** `resolve-preview`, layer, `template_ref`, `block_code`, client overlay, and vacancy sparse override stay behind **Advanced settings** / **Show technical details**. They remain available for admins; they are not the default screen.
- Own-company GET/PUT remain the SoT blob on `OwnCompany.extra`. Client-company GET/PUT remain overlay editing.
- Meta Integrations: **deep-link only** (not SoT UI).
- Misconfiguration of **ops** purposes is a recruiter status + **Create message** on the same page. RODO uses the platform body when no firm message is selected.

### RBAC

| Action | Permission |
|--------|------------|
| Write own-company / client / vacancy policy | `admin.users` + Communications admin feature (`communicationsAdmin`) — same class as other Communications settings; **not** ordinary recruiter |
| Read / resolve-preview | Managers with lead/settings view may read; write remains restricted |

### Audit

Every successful PATCH of own-company `lead_lifecycle_email_v1`, client overlay, or vacancy `lead_lifecycle_email_override_v1` emits an audit event: actor, timestamp, ids, before/after summary (mode, flags, template_ref).

---

## 9. Delivery

All sends go through `prepare_and_send_communication` with opaque module result (ADR-031). Purposes unchanged: `gdpr_notice`, `submission_acknowledgement`, `intake_rejection_notice`, `moving_forward_notice`.

**`gdpr_notice` sender:** tenant SMTP when configured; otherwise the platform mailbox `info@hostflow.cc`. If the custom sender is broken or removed, delivery falls back to the platform mailbox. Using HostFlow infrastructure does not make HostFlow the controller. Ops lifecycle emails still use tenant SMTP only.

---

## 10. Implementation slices

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

## 11. References

- [leads module](../modules/leads.md)
- [workflows index](index.md)
- [ADR-028 configuration ownership](../architecture/ADR-028-configuration-ownership.md)
