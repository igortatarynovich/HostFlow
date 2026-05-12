# scripts/security

Скрипты для **enforcement** security-процесса (вызываются из `.github/workflows/security-gates.yml` и локально).

| Файл | Назначение |
|------|------------|
| `threat_model_gate.py` | Если diff затрагивает чувствительные пути кода — требует изменения под `docs/security/`. |
| `npm_audit_gate.mjs` | Падает при high/critical в чувствительных frontend-пакетах (axios, react-router, …). |
| `check_no_raw_emit_security_event.py` | Запрещает raw `emit_security_event(` вне allowlist; см. `docs/security/security-events-governance.md`. |
| `emit_security_event_allowlist.txt` | Burn-down allowlist для legacy shim / временной миграции. |

Локально:

```bash
python3 scripts/security/check_no_raw_emit_security_event.py
python3 scripts/security/threat_model_gate.py   # нужны BASE_SHA и HEAD_SHA
node scripts/security/npm_audit_gate.mjs        # из корня репо, после npm ci в hostflow-frontend
```
