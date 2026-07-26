# C0.1b — Legacy writers migration map

**Status:** NORMATIVE inventory (allowlist must shrink, never grow)  
**Parent:** [C0.1b Intent Policy & Snapshot Hardening](c0-1b-intent-policy-snapshot-hardening.md)

> Every outbound path outside `CommunicationSender` / `execute_communication_intent` /
> `prepare_and_send_communication` is legacy until migrated.  
> New bypasses are forbidden by contract test.

## Canon path (required for new work)

```text
Intent → IntentPolicyResult → Resolvers → CommunicationCommand → CommunicationSender
```

## Platform (allowed — not legacy)

| Caller | Role | Notes |
|--------|------|--------|
| `communications/prepare_send.py` | Platform transport adapter | May call `send_email_for_tenant` |
| `communications/send_communication.py` | Durable message/delivery/G13 writer | Sole SoT writer for Canon outbound |
| `communications/execute_intent.py` | Intent render + prepare | Business entry |
| `services/communication_deliveries/questionnaire_email.py` | First Canon caller | Uses `prepare_and_send_communication` |

## Legacy writers (temporary bypass allowlist)

| Current caller | Intent (target) | Origin (typical) | Channel | Template | Links | Compliance | Migration slice | Bypass |
|----------------|-----------------|------------------|---------|----------|-------|------------|-----------------|--------|
| `services/lead_communications.py` | `follow_up` | `sales_inquiry` / `application` (not Lead-as-result) | email | lead templates | Result Link | lead_rodo adjacent | [ADR-031](../architecture/ADR-031-compliance-outbound-requires-opaque-result.md) / [compliance-outbound task](compliance-outbound-pipeline-early-result.md) **PR-4/PR-5** | **migrated** — Pipeline only; unbound → C5 `communication_pipeline_required`; removed from SMTP allowlist |
| `services/lead_rodo.py` | `gdpr_notice` | `sales_inquiry` / `application` | email | RODO notice | `privacy_notice` | RODO | ADR-031 PR-1/PR-3/PR-5 | **migrated** — Pipeline only; unbound fail-closed; removed from SMTP allowlist |
| `services/rodo.py` | `gdpr_notice` | candidate / `application` | email | RODO | `privacy_notice` | RODO | ADR-031 / candidate path | **allowed** until migrated |
| `services/candidate_notifications.py` | `follow_up` / stage intents | `candidate` / `application` | email/telegram | notification keys | none | workflow | C0.1c | **allowed** |
| `services/draft_reminders.py` | `document_expiry_reminder` | varies | email | reminder keys | none | workflow | C0.1c | **allowed** |
| `services/contact_attempts.py` | `follow_up` | lead/contact | email | contact attempt | none | workflow | C0.1c | **allowed** |
| `services/risk_intel_digest_email.py` | *(ops digest — not product Intent)* | tenant ops | email | digest | none | internal | keep ops or map later | **allowed** (ops) |
| `api/.../dispatch.py` | inbox reply / outbound | thread origin | email/… | none/manual | none | workflow | C0.2/C1 | **allowed** |
| `api/.../telegram_intake/candidate_link.py` | `follow_up` | candidate | email | link mail | none | workflow | C0.1c | **allowed** |
| `api/.../routes/messages.py` | inbox compose | thread | * | manual | none | workflow | align to Sender in C1 | **allowed** (inbox API) |
| `api/.../routes/ingest.py` + `_helpers/ingest.py` | inbound → message rows | inbound | * | n/a | n/a | n/a | C0.2 (inbound) | **allowed** (inbound writer) |

## Rules

1. **No new rows** in the legacy table without an explicit queue amendment.  
2. Contract test `test_legacy_bypass_allowlist_does_not_grow` fails if a new `send_email_for_tenant` / direct `CommunicationMessage(` / `CommunicationDelivery(` appears outside the allowlist.  
3. When a writer migrates to `CommunicationSender`, remove it from the allowlist in the same PR.  
4. Product features must not add module-specific SMTP composers.

## Removal plan (order)

1. `lead_communications` / `lead_rodo` → `gdpr_notice` + `follow_up` via Sender  
2. `candidate_notifications` → stage Intents via Sender  
3. Reminders / contact attempts → `document_expiry_reminder` / `follow_up`  
4. Inbox dispatch / messages create → Sender (with C1 UX)  
5. Keep ingest writers until C0.2 owns inbound snapshot shape  
