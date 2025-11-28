**Invoicing Module — Summary**

1. **Purpose**  
Управление счетами, платежами и возвратами для клиентов (компаний) и физических лиц.  
Интегрируется с модулями `Contracts_Orders`, `Additional_Services`, `Providers` и `Reporting`.

2. **Core Entities**  
- `invoices`: основная таблица, хранит статусы, суммы, даты, ссылки на компании и заказы.  
- `invoice_items`: позиции счёта (описание, количество, ставка НДС, итог).  
- `payments`: входящие платежи (метод, сумма, статус).  
- `refunds`: возвраты, связанные с платежами.

3. **Statuses**  
- `draft`, `issued`, `sent`, `paid`, `overdue`, `cancelled`  
- Переход в `issued` создаёт номер счёта (`invoice_numbering.snip`).  
- Переход в `paid` — при полной оплате, обновляется `payment_date`.

4. **Rules**  
- Расчёт итогов (`subtotal`, `vat_total`, `total_amount`) выполняется триггерами.  
- При изменении позиций или платежей вызывается пересчёт (`fn_invoice_recalc_totals`, `fn_invoice_recalc_paid`).  
- `overdue` автоматически выставляется, если `due_date < now()` и сумма не погашена.  
- Номер счёта уникален в рамках `(tenant_id, year)`.

5. **Integration**  
- `Payments` и `Refunds` напрямую влияют на статус счета.  
- `Reporting_Documents` получает агрегированные данные для отчётов.  
- `Client Portal` отображает счета и позволяет скачивать PDF.  
- Поддержка внешних провайдеров оплат через модуль `Providers`.

6. **API**  
- `GET /invoices` — список счетов.  
- `POST /invoices` — создание черновика.  
- `PATCH /invoices/{id}/status` — изменение статуса.  
- `POST /payments` — регистрация платежа.  
- `POST /refunds` — создание возврата.

7. **Security**  
- Политика RLS по `tenant_id`.  
- Только пользователи с ролями `OWNER` и `FINANCE` имеют доступ к операциям выставления и изменения счетов.  
- Все изменения логируются в `audit_log`.

8. **Planned Extensions**  
- Автоматическая интеграция с внешними бухгалтерскими системами (Optima, Comarch, Xero).  
- Шаблоны инвойсов и кастомные PDF-рендеры.  
- Массовая отправка счетов и напоминания об оплате через `scheduler`.
