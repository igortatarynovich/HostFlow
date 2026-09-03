# Threat Model — User Report Intake (ADR-040)

**Status:** outline (prerequisite for runtime; seal-time)  
**Date:** 2026-09-03  
**Normative:** [`ADR-040`](../../specs/architecture/ADR-040-user-report-intake.md) · ownership [`../../modules/user-report-intake/module_ownership_card.md`](../../modules/user-report-intake/module_ownership_card.md)  
**Related:** [`exports.md`](./exports.md) · [`document-uploads.md`](./document-uploads.md) · ADR-038 Collect diagnostics · [`security-events-governance.md`](../security-events-governance.md)

Runtime User Report Intake is a **security-perimeter** surface (free text, later attachments, cross-tenant platform inbox). **STOP** on Adapter/UI without this model, redaction policy, rate limits, and `emit_security_event_v1` taxonomy for create / cross-tenant read / export. This file is the seal-time outline; deepen it in the same PR that starts runtime.

## Assets

- User Report rows (`body`, optional `title`, `kind`, `status`, refs) — tenant-scoped when runtime exists  
- Optional opaque entity refs (navigation only)  
- Optional telemetry refs (`request_id`, `trace_id`, `sentry_event_id`, …) — correlation, not store  
- Later: attachments / screenshots (must be redacted before store/export)  
- Later: platform inbox (superadmin elevated) spanning tenants  
- Reporter identity (`reporter_user_id`, nullable on crash/email paths)

## Trust boundaries

- Authenticated tenant user → submit own report (later in-app)  
- Crash-path / pre-provider UI → minimal channel (mailto or isolated form); must not assume full app session  
- OL-7 email / procedure **before** runtime → **outside** this product SoT (not a report row writer by Architecture SoT alone)  
- Tenant operator → read/triage **own tenant** reports only  
- Superadmin + elevated reason → platform inbox (cross-tenant); must audit  
- Intake ↛ Observability store; Intake ↛ RB-10 incident SoT; Intake ↛ GitHub work SoT  
- Modules may pass observational entity context; must not read/write Intake tables as Activity substitute

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| UR-1 | Cross-tenant report leak | List/get by id without tenant bind; platform inbox without elevated gate |
| UR-2 | PII / secrets in free text | Body/title containing tokens, passwords, personal data in logs/export |
| UR-3 | Attachment malware / unredacted DOM | Screenshot/DOM dump with session tokens or CLASS 3 fields |
| UR-4 | Spam / DoS via submit | Unbounded create without rate limit |
| UR-5 | IDOR on reporter list | Tenant user reads another user’s or tenant’s reports |
| UR-6 | Elevated inbox without audit | Superadmin browse without `emit_security_event_v1` + reason |
| UR-7 | Correlation as mandatory gate | Rejecting reports without `request_id` / Sentry → bypass via email; false “invalid” |
| UR-8 | Lifecycle coupling abuse | Auto-close report from GitHub webhook without Intake policy / customer ack (INV-UR-01) |
| UR-9 | Surrogate SoT | Communications/Activity/Forms used as ticket store to bypass Intake RBAC |
| UR-10 | Entity authority creep | Treating opaque entity ref as proof of entity state / history |

## Митигации (baseline — required before runtime)

- Tenant RLS / session bind on all report CRUD; platform inbox only via elevated path + audit  
- Redact secrets/PII before export and before any attachment persistence; default deny unredacted DOM dump  
- Rate limits on submit; captcha or equivalent if anonymous crash path is ever opened  
- Correlation optional; validate report without telemetry refs  
- Taxonomy PR: create / triage / cross-tenant read / export / deny via `emit_security_event_v1` only  
- Guard: no module-local ticket API; no auto-status from external work refs without Intake policy  
- Entity refs opaque; no business-history queries owned by Intake  

## Тесты (when runtime starts)

- Cross-tenant get/list → deny  
- Submit without `request_id` → 201 / accepted  
- Elevated inbox without reason → deny + security event  
- Rate limit exceeded → 429  
- Guard scan: no `support_ticket` / download-log forks in business modules  

## Связанные спеки

- [`ADR-040`](../../specs/architecture/ADR-040-user-report-intake.md)  
- [`user-report-intake-contract-seal.md`](../../specs/tasks/user-report-intake-contract-seal.md)  
- [`security-review-checklist.md`](../security-review-checklist.md)  
- [`security-events-governance.md`](../security-events-governance.md)
