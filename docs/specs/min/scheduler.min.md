**Scheduler Module — Summary**

1. **Purpose**
   - Централизованный механизм планирования задач, напоминаний и автоматических действий.
   - Используется для документооборота, обучения, инвойсинга, согласований и напоминаний пользователям.

2. **Core Concepts**
   - `tasks`: единицы планирования с типом (`reminder`, `check`, `sync`, `cleanup`).
   - `events`: события, привязанные к объектам (document, candidate, invoice).
   - `triggers`: условия запуска — по дате, cron, webhook или статусу.
   - `jobs`: выполняемые действия (уведомления, webhooks, пересчёты).

3. **Rules**
   - Все задачи имеют `tenant_id` и подлежат RLS.
   - Повторяющиеся задачи поддерживаются через cron-формат (`RRULE`).
   - Ошибки выполнения логируются в `scheduler_logs`.
   - Истёкшие задачи автоматически архивируются через nightly job.
   - Системные задачи помечаются `is_system = true` и не редактируются вручную.

4. **Integration**
   - Модули: `Documents` (expiry alerts), `Training` (обучение), `Invoicing` (оплата), `Approvals` (согласования).
   - `Notifications` — через общий сервис уведомлений (email/web/WhatsApp).
   - `Webhooks` — для интеграции с CRM, ERP, внешними API.
   - Поддерживает обратную связь (`task.completed` event) для отчётности.

5. **API**
   - `POST /scheduler/task` — создание задачи.
   - `PATCH /scheduler/task/{id}` — обновление статуса.
   - `GET /scheduler/tasks?type=reminder` — выборка по фильтрам.

6. **Security**
   - Политики RLS по `tenant_id`.
   - Ограничение прав: `OWNER`, `MANAGER`, `SYSTEM`.
   - Логирование всех событий в `audit_log`.

7. **Planned Extensions**
   - Поддержка очередей (Redis/Kafka) для масштабирования.
   - UI-календарь в админке и порталах.
   - История выполнения задач и SLA-отчёты.
