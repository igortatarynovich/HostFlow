# ✅ Definition of Done — Documents Module

> Чек-лист принимает изменения в модуле Documents перед релизом UI/Backend.

---

## 1. Функциональные проверки

- [ ] `POST /api/v1/documents` валидирует поля `doc_type`, `kind`, `requested_from`, `process_type`; для `other` требует `custom_name`.
- [ ] `workflow.steps[*]` соответствуют контракту (`documents_workflow_contract.md`).
- [ ] Напоминания создаются при наличии `workflow.steps[*].due_at` и снимаются при `done=true`.
- [ ] `PATCH /api/v1/documents` при сдвиге `due_at` пересоздаёт напоминания без дубликатов.
- [ ] `compute_auto_status` соответствует таблице в контракте.
- [ ] `owner_summary` корректно считает просрочки и «температуру» документа.
- [ ] i18n фолбэк: при отсутствии `pl` ключа используется `en`.

---

## 2. Notifications & Reminders

- [ ] In-app уведомления создаются для новых/просроченных документов.
- [ ] SLA-эскалации задокументированы в `reminders_matrix.md` и покрыты тестами.
- [ ] Webhook по документам содержит `idempotency_key` и подпись.

---

## 3. UI / UX

- [ ] Форма документов отображает обязательные поля, работу с шаблонами и шагами workflow.
- [ ] Панель напоминаний показывает T−24 / T−4 / T+0 события.
- [ ] Локализация (en/ru/pl) проверена вручную для ключевых экранов.
- [ ] Роли: рекрутер/супервизор/клиент видят только допустимые действия (см. `rbac_matrix.md`).

---

## 4. Тесты

- [ ] Pytest: интеграционные тесты на CRUD, workflow, напоминания, i18n фолбэк.
- [ ] Frontend: тесты компонентов (workflow timeline, reminder panel).
- [ ] Smoke-тест импорта документов (CSV/ шаблоны) проходит.

---

## 5. Документация и миграции

- [ ] Обновлены спецификации: `documents.md`, `documents_workflow_contract.md`, `reminders_matrix.md`, `doc_types_catalog.md`.
- [ ] Alembic миграции и сиды синхронизированы (`make mig`, `make seed`).
- [ ] Changelog/релиз-ноты зафиксированы.

---

## 6. Approval

- [ ] UX-ревью (супервизор/рекрутер сценарии).
- [ ] Security review (RBAC, RLS).
- [ ] Подпись продукта: ответственное лицо подтверждает соответствие чек-листу.
