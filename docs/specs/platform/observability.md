# 📈 Observability & Audit

> Единая политика мониторинга и аудита экосистемы HostFlow.

---

## 1. Метрики (Prometheus)

| Metric | Type | Labels | Описание |
|--------|------|--------|----------|
| `hf_documents_workflow_duration_seconds` | histogram | `tenant_id`, `doc_type`, `step_code` | Время прохождения шага документа |
| `hf_documents_overdue_total` | gauge | `tenant_id`, `doc_type` | Количество просроченных шагов/документов (обновляется на create/patch документа и в джобах напоминаний) |
| `hf_leads_conversion_rate` | gauge | `tenant_id`, `source` | Конверсия лидов по этапам |
| `hf_notifications_unread_total` | gauge | `tenant_id`, `role` | Непрочитанные уведомления |
| `hf_reminders_triggered_total` | counter | `tenant_id`, `type`, `severity` | Количество сработавших напоминаний (инкрементируется при доставке in-app/email/webhook) |
| `hf_api_request_duration_seconds` | histogram | `tenant_id`, `route`, `status_code` | Латентность API |

- Метрики собираются через Prometheus client (`prometheus-client`) + кастомные события в сервисах. Экспорт через `/metrics` (см. раздел Integration).

---

## 2. Логи

- **Бизнес-события** (`lead.*`, `document.*`, `notification.*`) — формат JSON, уровень INFO.
- **Ошибки i18n** — фиксируются при отсутствии ключа (уровень WARNING). Содержат `key`, `locale`, `tenant_id`.
- **Audit log** — отдельная таблица `audit_log` (tenant scoped):
  - `id`, `tenant_id`, `actor_id`, `actor_role`
  - `entity_type`, `entity_id`
  - `action` (`create`, `update`, `delete`, `status_change`, `reminder_cancel`, `role_assign`)
  - `payload_before`, `payload_after`
  - `created_at`
- Запись в audit обязательна для:
  - Изменения ролей/доступов.
  - Ручной маршрутизации лидов.
  - Изменения `due_at` и статусов документов/шагов.
  - Настроек напоминаний, webhook секретов, локализации.

---

## 3. Алёрты

| Алёрт | Условие | Действие |
|-------|---------|----------|
| `alerts_documents_overdue_spike` | `hf_documents_overdue_total` > 10 (per tenant) | Уведомление админу тенанта + Slack канал поддержки |
| `alerts_leads_webhook_failures` | 3 ошибки подряд при доставке webhook | Авто-деактивация webhook, письмо админу |
| `alerts_notifications_queue_lag` | Напоминания T+0 не доставлены за 5 мин | PagerDuty для on-call |
| `alerts_db_migration_failed` | `alembic` exit code != 0 | Блокировать деплой, уведомить DevOps |

---

## 4. Дашборды

- **Operations Dashboard** (Supervisor):
  - Конверсия лидов по стадиям.
  - Просроченные документы (heatmap).
  - SLA напоминаний.
- **Admin Dashboard** (Tenant Admin):
  - Статистика импортов CSV.
  - Ошибки webhooks/интеграций.
  - Локализация (количество ключей без перевода).
- **Platform Dashboard** (Superadmin):
  - Количество активных тенантов.
  - Использование лицензий.
  - Ошибки миграций и seed.

---

## 5. Хранение и Retention

- Логи: 30 дней онлайн (ELK), архив 180 дней.
- Метрики: 14 дней high-resolution, 6 месяцев aggregated.
- Audit log: 365 дней (tenant-scoped, может выгружаться администратором).

---

## 6. Checklist

- [ ] Новые события добавлены в метрики/логи.
- [ ] i18n ошибки мониторятся в Grafana (панель `i18n-missing-keys`).
- [ ] Для новых модулей настроены alert правила.
- [ ] Документация обновлена (данный файл).
