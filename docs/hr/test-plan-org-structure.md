# Тест-план: оргструктура и права

Цель: зафиксировать минимальный набор проверок для регрессии HR-подмодуля оргструктуры (API + роли). Автотесты: `backend/tests/api/test_admin_org_units.py`.

## Роли и доступ

| Сценарий | Ожидание |
|----------|----------|
| `GET /admin/org-units/tree` под **supervisor** | 200 |
| Тот же запрос под **viewer** | 403 |
| `GET /admin/users`, `GET /admin/users/{id}`, `PATCH .../org-units` под **supervisor** | 200 (в рамках тенанта) |
| CRUD оргюнитов, members, import/export под **viewer** | 403 |

## Функциональные потоки

1. **Дерево и CRUD:** создание корня и дочернего узла, PATCH имени/`sort_order`, DELETE листа (после снятия детей).
2. **Участники:** POST member, GET list, DELETE member.
3. **Инвайт:** `POST /admin/users/invite` с `org_unit_id`; в ответе тот же `org_unit_id`.
4. **Назначение оргюнитов пользователю:** `PATCH /admin/users/{id}/org-units` с списком id; повтор с `[]` очищает членство.
5. **Экспорт/импорт:** `GET /admin/org-units/export` возвращает `version` и массив `units`; `POST /admin/org-units/import` с `version: 1` и уникальными `code` создаёт иерархию; повторный импорт с теми же `code` обновляет записи (`updated > 0`).
6. **Аудит:** после `POST` создания юнита в `user_audit_log` есть запись `org_unit.created` (см. `test_org_unit_create_writes_user_audit_log`).

## Контракт импорта (v1)

- У каждой строки обязателен уникальный **`code`** (внутри файла).
- **`parent_code`** опционален; должен указывать на другую строку того же файла **или** на уже существующий в тенанте `code`.
- Циклы в файле → 422.

## Связка HR Employee ↔ User (P1)

| Сценарий | Ожидание |
|----------|----------|
| `PATCH /workforce/employees/{id}` с `linked_user_id` | 200; в ответе `linked_user_org_units` совпадают с членством пользователя в оргструктуре |
| Второй сотрудник с тем же `linked_user_id` в тенанте | 409 |
| `GET /workforce/employees/link-user-options` под HR workspace | 200, список активных пользователей тенанта |

Автотест: `backend/tests/api/test_workforce_employee_linked_user.py`.

## Workforce + рекрутёр (контракт API)

| Сценарий | Ожидание |
|----------|----------|
| `GET /workforce/employees` под **recruiter** | не 404; **200** и список |
| `POST /workforce/employees/from-candidate/{id}` при кандидате с `manager` = рекрутёр | **200** |
| `viewer` на `GET /workforce/employees` | **403** |

Автотест: `backend/tests/api/test_workforce_recruiter_contract.py`.

Черновик критериев **1 / 3 / 5** (auto-bundle после handoff): `backend/tests/api/test_workforce_hr_readiness_v0.py`.

## CI

Прогон: `pytest backend/tests/api/test_admin_org_units.py` после `alembic upgrade head` на чистой схеме. Расхождение версии миграций и БД — вне области этого плана; конвейер должен поднимать БД из миграций или использовать фикстированный stamp.

Дополнительно:

- `pytest backend/tests/api/test_workforce_employee_linked_user.py` (нужна миграция `202604302490_workforce_linked_user`).
- `pytest backend/tests/api/test_workforce_recruiter_contract.py` — регрессия роутера `workforce` и RBAC рекрутёра.
- Сид `conftest._init_data` поднимает лимиты мест в `tenant_licenses` для дефолтного тенанта тестов, чтобы при общей БД не ломались инвайты и `PATCH /admin/users/{id}/role` (см. `tests/conftest.py`).
- Таймаут старта ASGI в фикстуре `client`: по умолчанию **60 с** (`LifespanManager`), переопределение через `HOSTFLOW_TEST_LIFESPAN_STARTUP_S` / `HOSTFLOW_TEST_LIFESPAN_SHUTDOWN_S`.
