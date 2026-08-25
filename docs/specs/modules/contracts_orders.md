

# Contracts & Orders (Контракты и заказы)

## Цель
Организовать управление контрактами между агентством и транспортными компаниями, а также заказами в рамках контрактов, которые определяют потребности в водителях и других услугах.

## Основные сущности

### 1. Контракт (`contracts`)
Определяет условия сотрудничества между агентством и клиентом.

| Поле | Описание |
|------|-----------|
| `id` | UUID |
| `tenant_id` | Идентификатор арендатора |
| `company_id` | Клиент (транспортная компания) |
| `title` | Название контракта |
| `description` | Описание условий |
| `start_date`, `end_date` | Срок действия |
| `currency` | Валюта расчётов |
| `rate_per_driver` | Стоимость одного водителя |
| `drivers_required` | Количество водителей по контракту |
| `billing_type` | `per_driver`, `per_service`, `package` |
| `status` | `draft`, `active`, `suspended`, `closed` |
| `file_id` | ID прикреплённого PDF-файла |
| `meta` | Дополнительные параметры |
| `created_at`, `updated_at` | Таймстемпы |

### 2. Заказ (`company_orders`)
Описывает конкретный запрос компании в рамках контракта.

| Поле | Описание |
|------|-----------|
| `id` | UUID |
| `tenant_id` | Tenant |
| `company_id` | Клиент |
| `contract_id` | Ссылка на контракт |
| `title` | Название заказа |
| `drivers_needed` | Количество требуемых водителей |
| `description` | Детали заказа |
| `status` | `open`, `in_progress`, `completed`, `cancelled` |
| `assigned_recruiter` | Ответственный менеджер |
| `progress` | JSON с данными по выполнению |
| `created_at`, `updated_at` | Таймстемпы |

## Связи
- `contract` ↔ `company` — один ко многим.
- `company_order` ↔ `contract` — один ко многим.
- `company_order` ↔ `vacancies` — один ко многим.
- `vacancy` ↔ `candidates` — один ко многим.

> **Canon update (ADR-032, 2026-07-28):** fulfillment SoT is **Sales** `sales_orders` → `sales_order_lines` → Vacancy (`order_line_id`, 1 line = 1 vacancy). Legacy JSON `companies.extra.company_orders` is **not** billing SoT. Invoice comes from **Billable Items**, not from vacancy filled alone. See [`ADR-032`](../architecture/ADR-032-client-order-vacancy-flight-chain.md) and [`sales_orders.md`](sales_orders.md).

## Логика и бизнес-правила
- Контракт определяет тариф и условия оплаты для заказов.
- Заказ может быть создан только для активного контракта.
- Закрытие контракта автоматически завершает все открытые заказы.
- При выполнении заказа (`drivers_needed` достигнут `drivers_hired`) → `status = completed`.

> **Superseded for billing (ADR-032):** do not treat headcount-complete as the sole invoice trigger. Use Order Line `billing_trigger` → Billable Item → Invoice.
- `progress` хранит сводные данные: `{requested, in_process, hired, rejected}`.
- Взаимодействие с модулем **Invoicing** — генерация счета после закрытия заказа.

## API (черновик)
- `POST /contracts` — создать контракт.
- `GET /contracts` — список контрактов.
- `GET /contracts/{id}` — детали контракта.
- `PATCH /contracts/{id}` — обновить контракт.
- `POST /company-orders` — создать заказ.
- `GET /company-orders` — список заказов.
- `PATCH /company-orders/{id}` — обновить статус.
- `GET /company-orders/{id}/progress` — прогресс выполнения.

## Пример API
```json
POST /company-orders
{
  "company_id": "f1a2b3...",
  "contract_id": "c9d8e7...",
  "title": "Заказ на 10 водителей для линии PL-DE",
  "drivers_needed": 10,
  "assigned_recruiter": "r7f8g9..."
}
```

## Прогресс выполнения
Пример хранимого поля `progress`:
```json
{
  "requested": 10,
  "in_process": 7,
  "hired": 5,
  "rejected": 2
}
```

## Интеграции
- **Invoicing:** после `status=completed` создаётся счёт.
- **Client Portal:** заказ и его прогресс отображаются клиенту.
- **Candidate Portal:** кандидат видит, на какой заказ он назначен.

## Статусы и автоматизация
| Статус | Описание | Автоматический переход |
|---------|-----------|------------------------|
| `open` | Заказ создан, подбор не начат | — |
| `in_progress` | Идёт подбор кандидатов | После назначения кандидатов |
| `completed` | Заказ выполнен | Все водители наняты |
| `cancelled` | Заказ отменён | Вручную или при закрытии контракта |

## Отчёты и аналитика
- Количество активных контрактов.
- Общие заказы и их прогресс.
- Выполнение по компаниям (% закрытых позиций).
- Среднее время выполнения заказа.
- Доход по контрактам.

## Тест-кейсы
- Создание контракта и заказа.
- Попытка создания заказа для неактивного контракта → ошибка.
- Обновление `progress` при изменении статусов кандидатов.
- Генерация счёта после завершения заказа.
- Проверка видимости (RLS): агентство видит только свои контракты и заказы.