# HostFlow — Threat Models (per surface)

Каждый файл — **узкий threat model** для одной поверхности атаки. При изменении соответствующего кода обновляйте модель в том же PR или заводите тикет с дедлайном до merge в production.

| Модель | Охват |
|--------|--------|
| [candidate-portal.md](./candidate-portal.md) | Токены, magic links, загрузки кандидата, сессии |
| [document-uploads.md](./document-uploads.md) | Malware, MIME bypass, квоты, storage ACL |
| [public-links.md](./public-links.md) | Публичные intake, vacancy links, TTL, revocation |
| [webhooks.md](./webhooks.md) | Stripe, messaging, подпись, replay, SSRF |
| [handoff.md](./handoff.md) | Cross-tenant visibility, ACCESS CONTEXT, IDOR |
| [client-portal.md](./client-portal.md) | Фильтрация данных, company scope, комментарии |
| [automations.md](./automations.md) | Исходящие HTTP, права сервисных аккаунтов, side effects |
| [communication-campaign-orchestrator.md](./communication-campaign-orchestrator.md) | C2.3 Campaign Orchestrator: tenant scope, Intent-only egress, no provider/Thread, audience snapshot |
| [exports.md](./exports.md) | Insider, bulk CSV, скрытые поля, rate limits |
| [global-search.md](./global-search.md) | CRM global search + tenant link company directory retrieval audit |
| [client-account-manual-creation.md](./client-account-manual-creation.md) | Manual `ClientAccount` create: tenant/company bind, duplicates, idempotency, origin forgery |
| [acquisition-activity-timeline.md](./acquisition-activity-timeline.md) | Stage 3E Activity Timeline: append-only audit, RLS, tenant-scoped idempotency, no Ops FKs |
| [acquisition-flight-runtime.md](./acquisition-flight-runtime.md) | Stage 4 Flight Runtime: platform campaign/flight APIs, RBAC/company-scope, lifecycle commands, delivery-error activity |
| [acquisition-optimization-signals.md](./acquisition-optimization-signals.md) | Stage 5 PR-1: read-only optimization signals / `suggest_pause` (no auto-pause, no GET side effects) |
| [acquisition-stage-6-analytics.md](./acquisition-stage-6-analytics.md) | Stage 6 PR-1…PR-6: compare, cohorts, portfolio, Outcome commercial value, declared-value ROI |
| [acquisition-marketing-sources.md](./acquisition-marketing-sources.md) | C-3 Marketing Sources: read-only inventory GET, tenant isolation, no write/reprocess side effects |
| [acquisition-source-diagnostics.md](./acquisition-source-diagnostics.md) | Source Diagnostics PR1–PR9: read-only Lead + Activity casework, filters, duplicate, Mapping Health, drift alerts/summary, export, Replay via Leads process; SPA-only drift notify |
| [rbac-trust-roles.md](./rbac-trust-roles.md) | ADR-036 four trust roles: ceilings, matrix PATCH, `access_context`, legacy job-title/portal aliases, inventory lint |
| [forms-platform.md](./forms-platform.md) | Forms Platform C2+C3: frozen publication identity; Builder FormDefinition ↔ Draft only; no draft-as-publication; no Builder publish |

Родительский документ: [../security-ssot.md](../security-ssot.md).
