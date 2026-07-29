# scripts/security

Скрипты для **enforcement** security-процесса (вызываются из `.github/workflows/security-gates.yml` и локально).

| Файл | Назначение |
|------|------------|
| `threat_model_gate.py` | Если diff затрагивает чувствительные пути кода — требует изменения под `docs/security/`. |
| `npm_audit_gate.mjs` | Падает при high/critical в чувствительных frontend-пакетах (axios, react-router, …). |
| `check_no_raw_emit_security_event.py` | Запрещает raw `emit_security_event(` вне allowlist; см. `docs/security/security-events-governance.md`. |
| `emit_security_event_allowlist.txt` | Burn-down allowlist для legacy shim / временной миграции. |
| `check_tenant_bind_auth.py` | Fail-closed: `get_db_with_tenant` / meta-leads dep требуют `get_current_user`; `get_db_with_tenant_public` только по allowlist; route с `X-Tenant-Id` без auth — только по header allowlist. |
| `tenant_bind_public_allowlist.txt` | Разрешённые call sites для anonymous signed-webhook tenant bind. |
| `tenant_header_public_allowlist.txt` | Route handlers, которым разрешён `X-Tenant-Id` без CRM JWT (public/webhooks). |
| `check_arq_worker_tenant.py` | ARQ jobs: tenant-scoped → `tenant_enforced_session` + `parse_required_job_tenant_id`; platform → `security_job_context`. |
| `check_retrieval_call_sites.py` | Phase 6: global search + tenant link company search must emit retrieval events. |

Локально:

```bash
python3 scripts/security/check_no_raw_emit_security_event.py
python3 scripts/security/check_tenant_bind_auth.py
python3 scripts/security/check_arq_worker_tenant.py
python3 scripts/security/check_retrieval_call_sites.py
python3 scripts/security/threat_model_gate.py   # нужны BASE_SHA и HEAD_SHA
node scripts/security/npm_audit_gate.mjs        # из корня репо, после npm ci в hostflow-frontend
```
