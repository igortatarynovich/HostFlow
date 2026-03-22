

# Additional Services (Дополнительные услуги)
<a id="services-domain"></a>

## Цель
Дать возможность продавать и исполнять дополнительные услуги, связанные с трудоустройством кандидатов и обслуживанием клиентов: медосмотр, психотест, Code 95/ADR, оформление виз/ŚK/разрешений, переводы, проживание, трансфер, обучение и т.д.

## SSOT и терминология
Канонический пайплайн заказов (`ServiceOrder.status`), модель **Party** (клиент = `companies`), связь счётов с заказами (`invoices.service_order_id`), метрики каталога и deep-link параметры UI описаны в [`docs/SSOT.md`](../../SSOT.md) (раздел *Party model + client workspace + services deep links*). Этот модульный spec дополняет SSOT деталями домена услуг; при расхождении приоритет у SSOT и кода (`backend/app/models/additional_service.py`).

## Основные сущности
- **Service** — элемент каталога услуг/товаров, который можно заказать и затем переиспользовать в фактуре.
- **ServiceOrder** — заказ на услугу (привязан к кандидату, вакансии или компании).
- **ServiceItem** — конкретная позиция в заказе (одна услуга).
- **ServiceSchedule** — запись или бронь на выполнение услуги (если требуется).
- **ServiceAttachment** — файлы и результаты, прикреплённые к услуге.

## Связи
- `ServiceOrder` связан **ровно с одним** владельцем: `candidate_id`, `vacancy_id` или `company_id` (CHECK `ck_service_orders_owner`). Для клиентского workspace заказы по Party — это заказы с `company_id` (см. SSOT).
- `ServiceItem.service_id → Service`.
- `ServiceItem` может иметь поле `required_documents` (список типов документов, которые должны быть одобрены до исполнения).
- Услуга может порождать новый документ (`result_document_type`), например результат медосмотра.
- Каталог `Service` выступает source of truth для billable items в `service order` и как reusable selector в invoicing flow.
- **Invoice** (см. модуль счетов): опциональная связь `invoices.service_order_id → service_orders.id` — счёт может быть привязан к заказу услуг для сквозной аналитики и UI.

## Структура таблиц

```sql
-- services (фактическая ORM-модель; без kind/sku/tax_mode на уровне каталога — см. Release contract ниже)
id UUID PK,
tenant_id UUID NOT NULL,
code TEXT NOT NULL,
name TEXT NOT NULL,
description TEXT,
category TEXT,
unit ENUM('piece','person','hour','package') NOT NULL,
base_price NUMERIC(12,2) DEFAULT 0,
estimated_cost NUMERIC(12,2) DEFAULT 0,
cost_currency CHAR(3) DEFAULT 'PLN',
currency CHAR(3) DEFAULT 'PLN',
vat_rate NUMERIC(4,2) DEFAULT 23.00,
requires_schedule BOOLEAN DEFAULT false,
requires_candidate BOOLEAN DEFAULT false,
requires_documents JSONB,
result_document_type TEXT,
sla_hours INT,
is_active BOOLEAN DEFAULT true,
meta JSONB,
created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ,
UNIQUE (tenant_id, code)

-- service_orders — канонический пайплайн заказа (единый с ATS revenue orders)
id UUID PK,
tenant_id UUID NOT NULL,
candidate_id UUID NULL,
vacancy_id UUID NULL,
company_id UUID NULL,
status ENUM(
  'draft',
  'confirmed',
  'in_progress',
  'completed',
  'cancelled',
  'on_hold'
) NOT NULL DEFAULT 'draft',
total_amount NUMERIC(12,2) DEFAULT 0,
currency CHAR(3) DEFAULT 'PLN',
vat_total NUMERIC(12,2) DEFAULT 0,
requested_by UUID NOT NULL,
assigned_to UUID NULL,
start_date DATE NULL,
end_date DATE NULL,
notes TEXT,
audit JSONB,
created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ,
CHECK ( (candidate_id IS NOT NULL)::int + (vacancy_id IS NOT NULL)::int + (company_id IS NOT NULL)::int = 1 )

-- Legacy: в старых клиентах/доках могли встречаться quoted / approved / scheduled / delivered / refunded.
-- API нормализует их в канонические значения (см. backend additional_services service layer).

-- service_items
id UUID PK,
tenant_id UUID NOT NULL,
order_id UUID NOT NULL REFERENCES service_orders(id) ON DELETE CASCADE,
service_id UUID NOT NULL REFERENCES services(id),
qty NUMERIC(10,2) DEFAULT 1,
unit_price NUMERIC(12,2),
estimated_cost NUMERIC(12,2),
actual_cost NUMERIC(12,2),
cost_currency CHAR(3),
cost_source TEXT,
cost_status TEXT DEFAULT 'missing',
vat_rate NUMERIC(4,2),
amount NUMERIC(12,2),
status ENUM('pending','scheduled','in_progress','delivered','cancelled') DEFAULT 'pending',
required_documents JSONB,
result_document_type TEXT NULL,
meta JSONB

-- service_schedule
id UUID PK,
tenant_id UUID NOT NULL,
item_id UUID NOT NULL REFERENCES service_items(id) ON DELETE CASCADE,
provider TEXT,
slot_start TIMESTAMPTZ,
slot_end TIMESTAMPTZ,
location TEXT,
status ENUM('reserved','confirmed','completed','no_show','cancelled') DEFAULT 'reserved',
meta JSONB

-- service_attachments
id UUID PK,
tenant_id UUID NOT NULL,
item_id UUID NOT NULL REFERENCES service_items(id) ON DELETE CASCADE,
file_id UUID NOT NULL,
label TEXT,
created_at TIMESTAMPTZ
```

## Правила и поведение
- Услуга может требовать документы, кандидата или запись (schedule).
- **Заказ (`ServiceOrder`)**: операционные переходы используют канонические статусы. Типичный поток: `draft` → `confirmed` → `in_progress` → `completed`; `on_hold` и `cancelled` — внешние/прерывающие состояния. Статус заказа отделён от статуса **позиции** (`ServiceItem`): позиция по-прежнему может быть `delivered` при завершении исполнения строки.
- Переход в **`confirmed`** (ранее в документах могло называться «approved») должен фиксировать согласованные цены и ставки НДС на уровне позиций.
- Цены и `vat_rate` хранятся на `ServiceItem` (отдельного JSON snapshot позиции в текущей схеме нет — актуальные поля см. ORM); изменения каталога не должны переписывать уже созданные строки заказа.
- Для profitability analytics позиция хранит cost basis: `estimated_cost`, `actual_cost`, `cost_currency`, `cost_source`, `cost_status`.
- Нельзя перевести **позицию** в `scheduled`, если не закрыты все `required_documents` (правило на уровне item/schedule).
- Если `ServiceItem.result_document_type` заполнен, при `deliver` создаётся или обновляется соответствующий документ кандидата.
- При `meta.blocking=true` услуга блокирует этап кандидата до завершения (например, ADR-тренинг до рейса) — критерий «завершено» для позиции: статус позиции `delivered`, не обязательно `completed` у всего заказа.
- `cancelled` на заказе требует явной фиксации причины в `audit` там, где это реализовано в API.
- Для счетов и отчётности: явный выбор налогового режима (`tax_mode` и т.п.) остаётся целевым требованием invoicing/analytics (см. Release contract); на уровне `Service`/`ServiceOrder` в текущей ORM доминирует `vat_rate` на позициях.

## Расчёт суммы
`order.total_amount = SUM(item.amount)`  
`vat_total = SUM(item.amount * vat_rate / 100)`  
Валюта заказа — по первой позиции либо заданная при создании.

## Роли и доступ
| Роль | Права |
|------|--------|
| OWNER / ADMIN | Управление каталогом, подтверждение, возвраты |
| RECRUITER | Создание заказов и расписаний, загрузка файлов |
| VIEWER | Только просмотр |
| can_override_requirements | Может обойти проверки документов (с обязательной причиной и аудитом) |

<a id="services-api"></a>
## API (черновик)
- `GET /services` — каталог; опционально `?include_metrics=true` — агрегаты по заказам (число заказов, выручка по завершённым) на уровне услуги.
- `POST /services` — добавить услугу (админ).
- `GET /service-orders` — список заказов; фильтр `?company_id=` для заказов клиента (Party).
- `POST /service-orders` — создать заказ (ровно одно из `candidate_id` / `vacancy_id` / `company_id`).
- `POST /service-orders/{id}/items` — добавить позиции.
- `POST /service-items/{id}/schedule` — назначить время.
- `POST /service-items/{id}/deliver` — завершить позицию (с созданием документа при необходимости).
- `GET /candidates/{id}/service-orders` — заказы кандидата.

Префикс в продукте: `/api/v1/…`. Параметры UI для workspace «Услуги»: `tab`, `order_id`, `company_id` (см. SSOT).

### Пример контракта
```json
POST /service-orders
{
  "candidate_id": "…",
  "currency": "PLN",
  "tax_mode": "standard_vat",
  "items": [
    {"service_code":"medical","qty":1},
    {"service_code":"psychotest","qty":1}
  ],
  "notes":"Пакет стартовых услуг"
}
```

### Пример завершения услуги
```json
POST /service-items/{id}/deliver
{
  "result_document": {
    "document_type": "medical",
    "issue_date": "2025-10-15",
    "expiry_date": "2026-10-15",
    "status": "approved",
    "file_id": "…"
  }
}
```

## Каталог услуг (seed)
| Код | Категория | Результирующий документ | Блокирующая | Требует запись |
|------|------------|--------------------------|--------------|----------------|
| medical | medical | medical | ❌ | ✅ |
| psychotest | medical | psychotest | ❌ | ✅ |
| code95_training | training | qualification_code95 | ❌ | ✅ |
| adr_training | training | adr_certificate | ✅ | ✅ |
| visa_support | legal | visa_or_title | ❌ | ❌ |
| attestation_support | legal | attestation | ❌ | ❌ |
| work_permit_support | legal | work_permit | ❌ | ❌ |
| translation | legal | — | ❌ | ❌ |
| airport_transfer | logistics | — | ❌ | ❌ |
| accommodation | logistics | — | ❌ | ❌ |

## Тест-кейсы
- Позиция/расписание: нельзя перевести в `scheduled`, если не готовы `required_documents` (где реализовано).
- При `deliver` для `medical` создаётся документ `medical` у кандидата.
- `adr_training` блокирует переход «Выехал в рейс», пока позиция не `delivered`.
- Владелец заказа: ровно один из candidate / vacancy / company; заказы с `company_id` доступны из карточки клиента.
- Кандидат обязателен, если `requires_candidate=true`.
- Проверка расчёта суммы и НДС.
- Проверка RLS и изоляции данных tenant.
- Канонические статусы заказа: отсутствие устаревших значений (`approved`, `delivered` на уровне заказа) в сохранённых данных после обновления.

## Реализация (2025-03)

- **Бэкенд**: добавлены ORM-модели `Service`, `ServiceOrder`, `ServiceItem`, `ServiceSchedule`, `ServiceAttachment`, миграция `202512150001_additional_services_module.py`, сервис-слой `backend/app/services/additional_services.py`, схемы `backend/app/schemas/additional_services.py` и маршруты `backend/app/api/v1/services.py`.
- **API**: доступны эндпоинты `/api/v1/services`, `/api/v1/service-orders`, `/api/v1/service-orders/{id}`, `/api/v1/service-items/{id}/schedule`, `/api/v1/service-items/{id}/deliver`, `/api/v1/service-items/{id}/attachments`, `/api/v1/service-orders/{id}/summary`, `/api/v1/candidates/{id}/service-orders`.
- **Права**: вводятся разрешения `services.view`, `services.orders.manage`, `services.catalog.manage`, `services.overrideRequirements`. Они подключены к ролям через `usePermissions`.
- **Сиды**: `backend/app/db/seeds/dev_full_seed.py` заполняет каталог 10 услугами и создаёт 3 демонстрационных заказа с расписаниями и вложениями.
- **Тесты**: `backend/tests/test_additional_services.py` покрывает базовый сценарий каталога, создания заказа, назначения расписания и завершения услуги (с проверкой документов).
- **Фронтенд**: добавлена страница `/services` (`ServicesPage.tsx`) с табами «Заказы» и «Каталог», поддержкой создания услуг/заказов, обновлением статусов и работой с расписанием/доставкой. Навигация обновлена (`Layout.tsx`). Хуки `useAdditionalServices` и API-клиент `api/additionalServices.ts` обеспечивают загрузку данных. В карточке кандидата отображается раздел «Дополнительные услуги» с заказами.

### Обновления (2026-03)

- **Канонические статусы заказа**: `draft`, `confirmed`, `in_progress`, `completed`, `cancelled`, `on_hold` (`ServiceOrderStatus`); нормализация legacy значений на входе API.
- **Поля заказа**: `start_date`, `end_date`; счёт — `invoices.service_order_id`.
- **Клиент / Party**: заказы с `company_id`; список компаний с опциональными метриками по заказам (`include_service_metrics`); фильтр заказов по `company_id`.
- **Каталог**: `GET /services?include_metrics=true` для столбцов заказов/выручки в UI.
- **Фронтенд**: колонки метрик в каталоге; deep links `tab`, `order_id`, `company_id`; в карточке компании — вкладки workspace (в т.ч. заказы услуг и счета). Подробности — в `docs/SSOT.md`.

## Release contract additions (`2026-03-13`)

- Каталог должен поддерживать как услуги, так и товары (`kind=service/product`), чтобы tenant мог выставлять счета не только за worklog, но и за продаваемые позиции. *(В текущей ORM `Service` поле `kind` ещё не введено — до появления в схеме биллинг опирается на каталог услуг и позиции заказа; см. SSOT.)*
- Для каждой позиции в каталоге обязательны reusable billing defaults: `currency`, `tax_mode`, `vat_rate`, `unit`, `base_price`, `sku/code`, `is_active`.
- `ServiceOrder` должен позволять выбирать эти позиции из каталога и сохранять snapshot на уровне `ServiceItem`.
- Дальнейший invoicing flow обязан уметь переиспользовать `ServiceItem` как основу invoice line items без ручного повторного ввода.

## Analytics contract (`2026-03-13`)

- `Services` workspace обязан поддерживать не только операционное исполнение, но и управленческую аналитику для service-led tenants.
- Минимальный analytics baseline:
  - revenue / paid / outstanding
  - gross profit / margin
  - top services/products
  - top clients
  - trends by period
  - slices by manager, client, item, currency, tax mode, status
- Важное правило: любая сводная метрика должна иметь drill-down в underlying `service_orders`, `service_items`, `invoices`, `payments`.
- Если tenant продает услуги, отсутствие profitability analytics считается product gap, даже если создание заказов и счетов уже работает.

### Canonical analytics dimensions

- `period`
- `client/company`
- `company_classification`
- `service/product`
- `category`
- `manager/owner`
- `lead_source`
- `status/stage`
- `currency`
- `tax_mode`

### Canonical analytics views

- `Overview` — KPI cards, overdue alerts, low-margin alerts, missing cost basis alerts
- `Trends` — day/week/month time-series for leads, orders, invoices, paid, profit
- `Clients` — ranked client profitability/revenue table
- `Items` — ranked service/product profitability/revenue table
- `Pivot` — slice/pivot workspace on top of the same source metrics

### Data quality rules

- Profitability without explicit cost basis must be marked as `estimated` or `missing`, not silently treated as exact.
- Multi-currency analytics requires source snapshots on `service_items` and `invoices` plus a clear reporting-currency policy.
- Export is allowed as secondary action, but core trend/slice analysis must remain usable inside the product.

### Cost basis contract

- `Service` catalog may provide default `estimated_cost`, but it is only a seed for order creation.
- Canonical profitability source is `ServiceItem` snapshot, not mutable catalog data.
- `cost_status` must distinguish at least `missing`, `estimated`, `confirmed`.
- Aggregate profit/margin in order, invoice and analytics views must expose cost coverage when some items are not `confirmed`.
