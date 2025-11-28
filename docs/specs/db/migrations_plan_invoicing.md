

# Invoicing Module — Database Migration Plan

## Цель
Определить структуру и последовательность миграций базы данных для модуля **Invoicing**, включая зависимые сущности: `invoices`, `invoice_items`, `payments`, `refunds`, и связи с компаниями, кандидатами и заказами.

---

## 1. Таблица `invoices`
**Описание:** хранит информацию о выставленных счетах.

```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    company_id UUID,
    candidate_id UUID,
    order_id UUID,
    number VARCHAR(50) NOT NULL UNIQUE,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'PLN',
    total_amount NUMERIC(12,2) NOT NULL,
    paid_amount NUMERIC(12,2) DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'draft', -- draft | issued | paid | cancelled
    notes TEXT,
    created_by UUID,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    CONSTRAINT fk_invoice_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_invoice_company FOREIGN KEY (company_id) REFERENCES companies(id),
    CONSTRAINT fk_invoice_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id),
    CONSTRAINT fk_invoice_order FOREIGN KEY (order_id) REFERENCES orders(id)
);
```

---

## 2. Таблица `invoice_items`
**Описание:** позиции внутри счёта (услуги, товары, доп. услуги).

```sql
CREATE TABLE invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL,
    description TEXT NOT NULL,
    quantity NUMERIC(10,2) NOT NULL DEFAULT 1,
    unit_price NUMERIC(12,2) NOT NULL,
    total NUMERIC(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    vat_rate NUMERIC(5,2) DEFAULT 23.00,
    created_at TIMESTAMP DEFAULT now(),
    CONSTRAINT fk_invoice_items_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);
```

---

## 3. Таблица `payments`
**Описание:** фиксирует поступления средств по счетам.

```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    invoice_id UUID NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    payment_date DATE NOT NULL,
    payment_method VARCHAR(20) NOT NULL, -- transfer | card | cash | online
    reference VARCHAR(100),
    status VARCHAR(20) DEFAULT 'confirmed', -- pending | confirmed | failed
    created_at TIMESTAMP DEFAULT now(),
    CONSTRAINT fk_payment_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_payment_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);
```

---

## 4. Таблица `refunds`
**Описание:** возвраты средств по оплачиваемым счетам.

```sql
CREATE TABLE refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    payment_id UUID NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    reason TEXT,
    refund_date DATE DEFAULT now(),
    status VARCHAR(20) DEFAULT 'initiated', -- initiated | completed | cancelled
    created_at TIMESTAMP DEFAULT now(),
    CONSTRAINT fk_refund_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_refund_payment FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
);
```

---

## 5. Индексы и оптимизация
```sql
CREATE INDEX idx_invoices_tenant ON invoices(tenant_id);
CREATE INDEX idx_invoices_company ON invoices(company_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_payments_invoice ON payments(invoice_id);
CREATE INDEX idx_refunds_payment ON refunds(payment_id);
```

---

## 6. Триггеры и вычисляемые поля
- **Триггер:** при создании `payment` обновляется `paid_amount` в `invoices`.
- **Триггер:** при полном совпадении `paid_amount = total_amount` → `status = 'paid'`.
- **Триггер:** при `refund.completed` → уменьшается `paid_amount`.

---

## 7. Последовательность миграций
1. `20251016_01_create_invoices_table.sql`  
2. `20251016_02_create_invoice_items_table.sql`  
3. `20251016_03_create_payments_table.sql`  
4. `20251016_04_create_refunds_table.sql`  
5. `20251016_05_add_triggers_and_indexes.sql`

---

## 8. Безопасность и RLS
```sql
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_invoices ON invoices USING (tenant_id = current_setting('app.tenant_id')::uuid);
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_payments ON payments USING (tenant_id = current_setting('app.tenant_id')::uuid);
ALTER TABLE refunds ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_refunds ON refunds USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

---

## 9. Связанные таблицы и модули
- `companies` (получатели счетов)  
- `candidates` (физлица, покупатели услуг)  
- `orders` (источник инвойсов)  
- `documents` (привязка актов и контрактов)  
- `audit_log` (отслеживание изменений)