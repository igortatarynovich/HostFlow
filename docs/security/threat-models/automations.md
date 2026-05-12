# Threat Model — Automations

## Assets

- Фоновые задачи, исходящие HTTP, права сервисного пользователя, данные кандидатов при триггерах.

## Trust boundaries

- Правила автоматизации (конфиг tenant admin) ↔ исполнение в worker/API.

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| AU-1 | SSRF | URL из пользовательского поля в HTTP node |
| AU-2 | Secret exfiltration | логирование тел запросов с токенами |
| AU-3 | Privilege escalation | автоматизация вызывает internal endpoint без impersonation bounds |
| AU-4 | Cross-tenant | job без tenant context в сессии БД |

## Митигации (baseline)

- Allowlist исходящих хостов/схем; запрет RFC1918/metadata IP для user-controlled URL.
- Jobs всегда с явным `tenant_id` в контексте и RLS.
- Ограничить набор вызываемых действий closed allowlist (не произвольный код).
- Не логировать секреты; redaction в structured logs.

## Тесты

- Попытка SSRF на `169.254.169.254` и внутренние hostname → блок.
- Job с неверным tenant → fail closed.

## Связанные спеки

- `docs/specs/modules/scheduler.md` (если автоматизации завязаны на планировщик)
