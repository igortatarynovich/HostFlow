# Threat Model — Public Links

## Assets

- Публичные вакансии, формы intake, одноразовые формы, подписанные URL на ресурсы.

## Trust boundaries

- Интернет (анонимные пользователи), поисковики, кеши CDN.

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| PL-1 | Enumeration | угадывание token/id в URL |
| PL-2 | Long-lived secret in URL | утечка через Referer, логи прокси |
| PL-3 | Scope creep | один токен даёт доступ к лишним данным |
| PL-4 | Spam / abuse | массовая отправка форм, credential stuffing на recovery |
| PL-5 | Leftover ruleset as required-set SoT | Public apply checklist invents document types from `json_data` instead of persisted R5 `tenant_delta` |

## Митигации (baseline)

- Непредсказуемые токены достаточной энтропии; rate limit + CAPTCHA где нужно (см. также backlog в `HOSTFLOW_AUDIT_AND_PLAN.md` по public intake).
- Короткий TTL; revocation list; минимальный scope в JWT/query token.
- CSP и заголовки безопасности на публичных страницах.
- Не включать PII CLASS 3 в query string.
- RPM Consumer Cutover seals public apply `requiredTypes` from persisted `tenant_delta`. No new apply token, magic link, or public URL. Token enumeration / TTL remain PL-1 / PL-2.

## Тесты

- Истёкший / отозванный токен.
- Попытка расширить scope параметрами запроса.
- Повторное использование one-time токена → отказ.
- `backend/tests/platform/test_requirement_policy_consumer_cutover_gate.py` (apply checklist loads persisted overlay; no new public path).

## Связанные спеки

- `docs/specs/architecture/ADR-013-public-intake-strategy.md`
- Authenticated Forms Platform resolve / frozen publication identity: [`forms-platform.md`](./forms-platform.md) (not this surface)
