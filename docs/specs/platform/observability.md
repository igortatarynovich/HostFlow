# 📈 Observability & Audit

> Единая политика мониторинга и аудита экосистемы HostFlow.

**Ownership (L1):** [`ADR-038`](../architecture/ADR-038-shell-observability-diagnostics.md) · Catalog Passports **Observability** (Infrastructure) and **Shell Diagnostics** (Platform).

**Правило:** Shell умеет **получить и предоставить** диагностические данные. Shell **не** генерирует и не хранит все логи. Каждый сервис/модуль пишет свои структурированные логи и spans; Platform собирает, коррелирует и хранит; Shell — единая операторская точка доступа.

Этот файл — L2 operating canon (метрики, retention, checklist). Ownership и границы — ADR-038 + Catalog. Не путать с **Activity** (операционная история продукта, ADR-012) и с **domain diagnostics** (Delivery / Source / Marketing).

---

## 0. Emit vs access

| Слой | Делает | Не делает |
|------|--------|-----------|
| **Service / module** | Emit structured logs and spans | Log store, «скачать лог», Collect diagnostics |
| **Observability** | Collect, correlate (`trace_id` / `request_id`), store, search Logs/Traces/Errors, redact secrets/PII, retention | Operator UI |
| **Shell Diagnostics** | Diagnostics UI; Collect diagnostics; download diagnostic bundle | Telemetry SoT |
| **Platform RBAC** (ADR-036) | Кто может Collect / читать traces | Redaction engine |
| **Security canon** | PII / CLASS policy for telemetry and exports | Хранение логов |

**Collect diagnostics** собирает bundle за операцию (`trace_id` / `request_id`) или ограниченный период: metadata, frontend logs, backend logs, errors, traces. Перед выдачей Observability обязан удалить secrets, tokens и чувствительные данные.

Runtime Collect diagnostics **не** начат в ADR-038. Пока действуют существующие emit-пути (Sentry, JSON logs, Prometheus) без операторского bundle UI.

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

- **Бизнес-события** (`lead.*`, `document.*`, `notification.*`) — формат JSON, уровень INFO. Emit — владеющий модуль; хранение/поиск — Observability.
- **Ошибки i18n** — фиксируются при отсутствии ключа (уровень WARNING). Содержат `key`, `locale`, `tenant_id`.
- **Корреляция:** `trace_id`, `request_id`, `tenant_id`, при наличии `company_id`, `module`, `entity`. Propagation — Platform.
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
  - (runtime, later) Collect diagnostics / download diagnostic bundle.

Audit log — продуктный след действий, не замена traces. Security telemetry — [`../../security/security-events-governance.md`](../../security/security-events-governance.md).

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
- **Diagnostics** (Shell Diagnostics, ADR-038 — runtime later):
  - Correlation context: Trace ID, Request ID, tenant, company, module, entity.
  - Open trace, related logs, Collect diagnostics.

Product KPI dashboards ≠ telemetry search. Domain diagnostics (delivery/source/marketing) remain with their owners and may deep-link here.

---

## 5. Хранение и Retention

- Логи: 30 дней онлайн (ELK), архив 180 дней.
- Метрики: 14 дней high-resolution, 6 месяцев aggregated.
- Audit log: 365 дней (tenant-scoped, может выгружаться администратором).
- Diagnostic bundle: ephemeral; retention of *issued* bundles is a later Observability Manifest knob — default must not become a second log store.

---

## 6. Checklist

- [ ] Новые события добавлены в метрики/логи.
- [ ] i18n ошибки мониторятся в Grafana (панель `i18n-missing-keys`).
- [ ] Для новых модулей настроены alert правила.
- [ ] Модуль **не** добавляет свой download-log / trace store (ADR-038).
- [ ] Документация обновлена (данный файл + Passport при смене границы).
