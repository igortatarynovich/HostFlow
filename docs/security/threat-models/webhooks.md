# Threat Model — Webhooks (inbound)

## Assets

- Состояние биллинга, сообщения, статусы интеграций, внутренние очереди.

## Trust boundaries

- Внешние SaaS (Stripe, Meta, messaging providers) ↔ HostFlow API.

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| WH-1 | Forged webhook | поддельный запрос без подписи |
| WH-2 | Replay | повтор старого валидного payload |
| WH-3 | Secret leakage | секрет в репо, логах, ошибках |
| WH-4 | SSRF (outbound из обработчика) | callback к внутренним IP при follow-up HTTP |

## Митигации (baseline)

- HMAC / provider-specific signature verification; constant-time compare.
- Idempotency keys + дедупликация событий; clock skew tolerance.
- Ротация webhook secrets; раздельные secrets per env.
- Исходящие HTTP из обработчиков — только allowlist URL (см. `automations.md`).

## Тесты

- Невалидная подпись → 4xx, без изменения состояния.
- Повтор того же event id → идемпотентность.

## Кодовые точки (ориентир)

- Webhook handlers в `backend/app/api/**` — поддерживать единый middleware/utility для verify.
