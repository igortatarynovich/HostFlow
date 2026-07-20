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
| [exports.md](./exports.md) | Insider, bulk CSV, скрытые поля, rate limits |
| [client-account-manual-creation.md](./client-account-manual-creation.md) | Manual `ClientAccount` create: tenant/company bind, duplicates, idempotency, origin forgery |

Родительский документ: [../security-ssot.md](../security-ssot.md).
