

# Billing & Invoicing (Выставление счетов)

## Цель
Создать модуль, обеспечивающий выставление счетов и управление платежами между агентствами, транспортными компаниями и кандидатами (физлицами). Модуль интегрируется с контрактами, заказами и дополнительными услугами.

## Основные сущности

### 1. Invoice (Счёт)
| Поле | Описание |
|------|-----------|
| `id` | UUID |
| `tenant_id` | Арендатор |
| `company_id` | Компания-плательщик (nullable) |
| `candidate_id` | Кандидат (nullable, для физлиц) |
| `contract_id` | Контракт, по которому выставлен счёт |
| `order_id` | Заказ (company_order) |
| `service_order_id` | Заказ на дополнительные услуги |
| `invoice_number` | Уникальный номер счёта |
| `issue_date` | Дата выставления |
| `due_date` | Срок оплаты |
| `currency` | Валюта |
| `subtotal` | Сумма без НДС |
| `vat_total` | Сумма НДС |
| `total_amount` | Общая сумма |
| `status` | `draft`, `issued`, `sent`, `paid`, `overdue`, `cancelled` |
| `payment_date` | Дата оплаты |
| `pdf_file_id` | ID PDF-файла счёта |
| `billing_details` | JSON со снапшотом реквизитов клиента |
| `items` | JSON со списком позиций |
| `created_by` | Пользователь, создавший счёт |
| `notes` | Комментарии |
| `created_at`, `updated_at` | Таймстемпы |

### 2. Payment (Платёж)
| Поле | Описание |
|------|-----------|
| `id` | UUID |
| `invoice_id` | ID счёта |
| `amount` | Сумма |
| `currency` | Валюта |
| `payment_date` | Дата оплаты |
| `method` | `bank_transfer`, `card`, `cash`, `other` |
| `reference_number` | Номер транзакции |
| `status` | `pending`, `confirmed`, `failed` |
| `created_at`, `updated_at` | Таймстемпы |

## Логика и бизнес-правила
- Счета могут выставляться как компаниям, так и кандидатам (физическим лицам).
- Каждый счёт связан с конкретным контекстом: контракт, заказ или услуга.
- Номер счёта формируется по шаблону: `INV/{TENANT}/{YYYY}/{SEQ}`.
- При создании счёта сохраняются реквизиты плательщика в `billing_details`.
- Line items могут собираться из reusable catalog entries (`service/product`) с сохранением invoice-time snapshot описания, цены, валюты и налогового режима.
- У счёта должен быть явный tax handling contract: `standard_vat`, `reverse_charge`, `vat_exempt` или локальный эквивалент; одного `vat_rate` недостаточно для бизнес-смысла.
- После статуса `paid` изменение данных запрещено.
- Статус `overdue` устанавливается автоматически по `due_date`.
- После `ServiceOrder.delivered` система может автоматически создавать счёт.
- Счета на физлиц отображаются в профиле кандидата.
- Система должна уметь отправить счёт получателю напрямую из HostFlow и сохранить delivery/audit trail (`sent_at`, `sent_to`, `channel`, `delivery_status`, `last_error`).

## API (черновик)
- `POST /invoices` — создать счёт.
- `GET /invoices` — список счетов.
- `GET /invoices/{id}` — детали счёта.
- `PATCH /invoices/{id}` — обновить статус.
- `POST /invoices/{id}/send` — отправить клиенту по email.
- `POST /invoices/{id}/cancel` — отменить.
- `POST /invoices/{id}/payments` — добавить оплату.
- `GET /invoices/{id}/pdf` — скачать PDF.

## Пример структуры `items`
```json
[
  {
    "description": "Подбор водителя категории CE",
    "qty": 1,
    "unit_price": 2500,
    "vat_rate": 23,
    "total": 3075
  },
  {
    "description": "Медицинская комиссия",
    "qty": 1,
    "unit_price": 200,
    "vat_rate": 23,
    "total": 246
  }
]
```

## Пример JSON счёта
```json
{
  "invoice_number": "INV/WORKHOST/2025/0045",
  "company_id": "a123-b456",
  "contract_id": "c987",
  "issue_date": "2025-10-15",
  "due_date": "2025-10-30",
  "currency": "PLN",
  "subtotal": 2700,
  "vat_total": 621,
  "total_amount": 3321,
  "status": "issued",
  "items": [
    {"description": "Подбор водителя категории CE", "qty": 1, "unit_price": 2500, "vat_rate": 23, "total": 3075},
    {"description": "Медкомиссия", "qty": 1, "unit_price": 200, "vat_rate": 23, "total": 246}
  ]
}
```

## Взаимосвязи
| Модуль | Взаимодействие |
|--------|----------------|
| **Companies** | Реквизиты, контракты, история оплат |
| **Contracts & Orders** | Счета за выполненные заказы |
| **Additional Services** | Автоматическое создание счёта после `delivered` |
| **Candidate Portal** | Просмотр и оплата счетов физлицами |
| **Document Templates** | Генерация PDF инвойса |

## Автоматизация
- Проверка сроков оплаты и изменение статуса на `overdue`.
- Генерация PDF при переходе в `issued`.
- Отправка уведомлений клиенту и агентству.
- Автоматическое создание счёта при выполнении заказа или услуги.
- Расчёт задолженности и аналитика по контрагентам.

## Operational contract additions (`2026-03-13`)

- `/app/invoices`, client card и `service order -> invoice` должны использовать один и тот же line-item contract.
- При создании invoice из service order пользователь не должен заново вручную вводить товар/услугу, валюту и налоговый режим, если они уже выбраны в заказе.
- Отправка счета из системы считается first-class action: `issue/send`, повторная отправка, статус доставки и история попыток должны быть доступны в invoice workspace.

## Отчёты и аналитика
- Общая выручка по компаниям.
- Задолженности по срокам.
- Статистика по типам услуг.
- Доля оплаченных и просроченных счетов.
- Счета по кандидатам (физлицам).

## Тест-кейсы
- Создание счёта компании.
- Создание счёта физлицу за услугу.
- Оплата счёта и смена статуса.
- Автоматическое создание PDF и отправка email.
- Проверка RLS: компания видит только свои счета.
- Просрочка счёта → статус `overdue`.
