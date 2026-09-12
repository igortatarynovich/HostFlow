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
| PL-6 | Source-local intake as decision authority | Treating `field_answers` / `lead.normalized` / Meta payload / `normalized.documents[]` as SoT for RSO/ESO deterministic decisions (citizenship, years_ce, …) |

## Митигации (baseline)

- Непредсказуемые токены достаточной энтропии; rate limit + CAPTCHA где нужно (см. также backlog в `HOSTFLOW_AUDIT_AND_PLAN.md` по public intake).
- Короткий TTL; revocation list; минимальный scope в JWT/query token.
- CSP и заголовки безопасности на публичных страницах.
- Не включать PII CLASS 3 в query string.
- RPM Consumer Cutover seals public apply `requiredTypes` from persisted `tenant_delta`. No new apply token, magic link, or public URL. Token enumeration / TTL remain PL-1 / PL-2.
- **Canonical Facts Occupancy:** public intake / Mapping write ADAPT facts into canonical storage (`personal_data.citizenship`, `extra.experience.years_ce`). Transport bags remain provenance only. Downstream deterministic consumers (RSO/ESO) read via `backend.app.field_registry.canonical_facts` — not `field_answers`, nationality/country twins, or `documents[]` as authority. Named gate: `test_canonical_facts_occupancy_gate.py` / [canonical-facts-completeness.md](../../specs/tasks/canonical-facts-completeness.md).

## Тесты

- Истёкший / отозванный токен.
- Попытка расширить scope параметрами запроса.
- Повторное использование one-time токена → отказ.
- `backend/tests/platform/test_requirement_policy_consumer_cutover_gate.py` (apply checklist loads persisted overlay; no new public path).
- `backend/tests/platform/test_canonical_facts_occupancy_gate.py` (source → Mapping → canonical occupancy → RSO/ESO; no source-bag decision authority).

## Связанные спеки

- `docs/specs/architecture/ADR-013-public-intake-strategy.md`
- `docs/specs/tasks/canonical-facts-completeness.md`
- Authenticated Forms Platform resolve / frozen publication identity: [`forms-platform.md`](./forms-platform.md) (not this surface)
