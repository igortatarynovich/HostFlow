# Threat Model — Client Portal

## Assets

- Кандидаты и документы в scope компании клиента; коммуникации; статусы процессов.

## Trust boundaries

- Пользователь `client_manager` ↔ данные агентства ↔ другие компании того же тенанта (если применимо).

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| CL-1 | company_id bypass | подмена параметров запроса |
| CL-2 | Read internal notes | слишком широкий serializer |
| CL-3 | Export / bulk | скачивание базы через «отчёты» |
| CL-4 | Vertical privilege | client_manager → функции recruiter через URL |

## Митигации (baseline)

- Всегда фильтровать по `company_id` / связке из membership, не по телу запроса.
- Отдельные DTO для client API без internal полей.
- Запрет массового экспорта по умолчанию; audit на исключения.

## Тесты

- Два `client_manager` разных компаний — взаимная изоляция.
- Попытка доступа к кандидату без связи компании → 403/404.

## Связанные спеки

- `docs/specs/journeys/client-portal.md`
- `docs/specs/architecture/rbac_matrix.md` (панель Client Portal)
