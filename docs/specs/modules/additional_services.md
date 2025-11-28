

# Additional Services (Дополнительные услуги)
<a id="services-domain"></a>

## Цель
Дать возможность продавать и исполнять дополнительные услуги, связанные с трудоустройством кандидатов и обслуживанием клиентов: медосмотр, психотест, Code 95/ADR, оформление виз/ŚK/разрешений, переводы, проживание, трансфер, обучение и т.д.

## Основные сущности
- **Service** — элемент каталога услуг, который можно заказать.
- **ServiceOrder** — заказ на услугу (привязан к кандидату, вакансии или компании).
- **ServiceItem** — конкретная позиция в заказе (одна услуга).
- **ServiceSchedule** — запись или бронь на выполнение услуги (если требуется).
- **ServiceAttachment** — файлы и результаты, прикреплённые к услуге.

## Связи
- `ServiceOrder` связан с одним из: `candidate_id`, `vacancy_id`, `company_id`.
- `ServiceItem.service_id → Service`.
- `ServiceItem` может иметь поле `required_documents` (список типов документов, которые должны быть одобрены до исполнения).
- Услуга может порождать новый документ (`result_document_type`), например результат медосмотра.

## Структура таблиц

```sql
-- services
id UUID PK,
tenant_id UUID NOT NULL,
code TEXT UNIQUE,
name TEXT NOT NULL,
description TEXT,
category TEXT,
unit ENUM('piece','person','hour','package') NOT NULL,
base_price NUMERIC(12,2) DEFAULT 0,
currency CHAR(3) DEFAULT 'PLN',
vat_rate NUMERIC(4,2) DEFAULT 23.00,
requires_schedule BOOLEAN DEFAULT false,
requires_candidate BOOLEAN DEFAULT false,
requires_documents JSONB,
sla_hours INT,
is_active BOOLEAN DEFAULT true,
meta JSONB,
created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ

-- service_orders
id UUID PK,
tenant_id UUID NOT NULL,
candidate_id UUID NULL,
vacancy_id UUID NULL,
company_id UUID NULL,
status ENUM('draft','quoted','approved','scheduled','in_progress','delivered','cancelled','refunded') DEFAULT 'draft',
total_amount NUMERIC(12,2) DEFAULT 0,
currency CHAR(3) DEFAULT 'PLN',
vat_total NUMERIC(12,2) DEFAULT 0,
requested_by UUID NOT NULL,
assigned_to UUID NULL,
notes TEXT,
audit JSONB,
created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ,
CHECK ( (candidate_id IS NOT NULL)::int + (vacancy_id IS NOT NULL)::int + (company_id IS NOT NULL)::int = 1 )

-- service_items
id UUID PK,
tenant_id UUID NOT NULL,
order_id UUID NOT NULL REFERENCES service_orders(id) ON DELETE CASCADE,
service_id UUID NOT NULL REFERENCES services(id),
qty NUMERIC(10,2) DEFAULT 1,
unit_price NUMERIC(12,2),
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
- Переход `draft → approved` фиксирует цену и ставку НДС.
- Нельзя перевести в `scheduled`, если не закрыты все `required_documents`.
- Если `ServiceItem.result_document_type` заполнен, при `deliver` создаётся или обновляется соответствующий документ кандидата.
- При `meta.blocking=true` услуга блокирует этап кандидата до завершения (например, ADR-тренинг до рейса).
- `cancelled` и `refunded` требуют указания причины (логируется в `audit`).

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
- `GET /services` — получить каталог услуг.
- `POST /services` — добавить услугу (админ).
- `POST /service-orders` — создать заказ.
- `POST /service-orders/{id}/items` — добавить позиции.
- `POST /service-items/{id}/schedule` — назначить время.
- `POST /service-items/{id}/deliver` — завершить (с созданием документа).
- `GET /candidates/{id}/service-orders` — получить заказы кандидата.

### Пример контракта
```json
POST /service-orders
{
  "candidate_id": "…",
  "currency": "PLN",
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
- Заказ не переводится в `scheduled`, если не готовы `required_documents`.
- При `deliver` для `medical` создаётся документ `medical` у кандидата.
- `adr_training` блокирует переход «Выехал в рейс», пока не `delivered`.
- Кандидат обязателен, если `requires_candidate=true`.
- Проверка расчёта суммы и НДС.
- Проверка RLS и изоляции данных tenant.

## Реализация (2025-03)

- **Бэкенд**: добавлены ORM-модели `Service`, `ServiceOrder`, `ServiceItem`, `ServiceSchedule`, `ServiceAttachment`, миграция `202512150001_additional_services_module.py`, сервис-слой `backend/app/services/additional_services.py`, схемы `backend/app/schemas/additional_services.py` и маршруты `backend/app/api/v1/services.py`.
- **API**: доступны эндпоинты `/api/v1/services`, `/api/v1/service-orders`, `/api/v1/service-orders/{id}`, `/api/v1/service-items/{id}/schedule`, `/api/v1/service-items/{id}/deliver`, `/api/v1/service-items/{id}/attachments`, `/api/v1/service-orders/{id}/summary`, `/api/v1/candidates/{id}/service-orders`.
- **Права**: вводятся разрешения `services.view`, `services.orders.manage`, `services.catalog.manage`, `services.overrideRequirements`. Они подключены к ролям через `usePermissions`.
- **Сиды**: `backend/app/db/seeds/dev_full_seed.py` заполняет каталог 10 услугами и создаёт 3 демонстрационных заказа с расписаниями и вложениями.
- **Тесты**: `backend/tests/test_additional_services.py` покрывает базовый сценарий каталога, создания заказа, назначения расписания и завершения услуги (с проверкой документов).
- **Фронтенд**: добавлена страница `/services` (`ServicesPage.tsx`) с табами «Заказы» и «Каталог», поддержкой создания услуг/заказов, обновлением статусов и работой с расписанием/доставкой. Навигация обновлена (`Layout.tsx`). Хуки `useAdditionalServices` и API-клиент `api/additionalServices.ts` обеспечивают загрузку данных. В карточке кандидата отображается раздел «Дополнительные услуги» с заказами.
