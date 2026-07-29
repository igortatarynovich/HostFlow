# Detection & alerting runbooks (Phase 7)

**Owner (default):** security-champion  
**Related:** [`runtime-roadmap.md`](./runtime-roadmap.md) Phase 7 · [`security-ssot.md`](./security-ssot.md) §16 IR · telemetry in `hostflow.security.events`

Каждое правило в `backend/app/security/detection_rules.py` **обязано** ссылаться на этот файл (или более узкий runbook). Алерт без triage-процедуры запрещён.

Transport: canonical event `detection.alert.raised` + optional `SECURITY_ALERT_WEBHOOK_URL` / `settings.security_alert_webhook_url` (Slack-compatible JSON `text`).

---

## Rule `export_anomaly_v1`

| | |
|--|--|
| **Trigger** | `export.anomaly.detected` (Phase 4 per-request thresholds) |
| **Severity** | medium |
| **Triage** | 1) Open log by `correlation_id` / `trigger_event_id`. 2) Check `anomaly_codes` + `export_type` + actor. 3) Legitimate large org/analytics export → close as FP and note `export_type`. 4) Suspicious mass CLASS3 dump → revoke session, freeze user export capability if available, open IR §16. |
| **FP known** | Large org-structure snapshots; bulk CSV for ops reporting. |

---

## Rule `retrieval_denied_burst_v1`

| | |
|--|--|
| **Trigger** | ≥ **5** `search.retrieval.denied` for same `tenant_id`+`actor_id` in **10 min** (process-local counter v1) |
| **Severity** | medium |
| **Triage** | 1) Confirm actor membership / role. 2) Scripted scope probing → block IP / revoke tokens. 3) Misconfigured UI sending foreign `scope_tenant_id` → fix client, no IR. |
| **FP known** | Superadmin switching workspaces without elevated headers (should be rare after membership guard). |

---

## Rule `document_signed_url_denied_burst_v1`

| | |
|--|--|
| **Trigger** | ≥ **10** `document.signed_url.denied` for same tenant+actor in **10 min** |
| **Severity** | medium |
| **Triage** | 1) Expired link storms vs signature mismatch. 2) Token share / scan → rotate object keys, shorten TTL. 3) Follow IR if CLASS 3 exposure suspected. |
| **FP known** | Bulk UI refresh on expired intake links. |

---

## Adding a rule

1. Add `DetectionRule` in `detection_rules.py` with `owner`, thresholds, `runbook_path`.
2. Document triage in this file (or linked runbook).
3. Unit test for `should_raise_alert`.
4. No alert sink that bypasses `emit_security_event_v1` / `detection.alert.raised`.
