# Threat Model — Candidate Portal

## Assets

- PII кандидата (CLASS 2), документы (часто CLASS 3).
- Upload tokens, session tokens, magic links из email.

## Trust boundaries

- Браузер кандидата (недоверенный), email (пересылки), история браузера, скриншоты.

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| CP-1 | Token leakage | Долгоживущие ссылки в email, referrer, логах |
| CP-2 | Session fixation / theft | XSS на поддомене, расширения браузера |
| CP-3 | Upload abuse | Заливка malware, zip bomb, DoS по квоте |
| CP-4 | IDOR | Смена `candidate_id` / document id в API |
| CP-5 | Scope creep | Кандидат получает поля других сущностей в JSON |

## Митигации (baseline)

- Публичные / полупубличные ссылки: **короткий TTL**, **revocable**, **one-purpose** (отдельный scope claim), опционально пароль/SMS для CLASS 3.
- **Upload token ≠ auth token**; отдельный endpoint и ограниченный scope.
- Квоты на размер и число файлов; malware scan для production.
- Строгая сериализация ответов API candidate: allowlist полей по классу данных.
- Rate limiting на login / link redemption.

## Тесты

- Негативные IDOR по `candidate_id`, `document_id`, `application_id`.
- Истёкший и отозванный токен → отказ.
- Невалидный upload → 4xx без side effects.

## Связанные спеки

- `docs/specs/journeys/candidate-portal.md`
- `docs/specs/db/schema_candidate_portal.sql` (если актуален)
