


BEGIN;

-- ENUM-подобные проверки через CHECK
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    company_id UUID,
    candidate_id UUID,
    contract_id UUID,
    order_id UUID,
    service_order_id UUID,
    invoice_number VARCHAR(64) NOT NULL UNIQUE,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'PLN',
    subtotal NUMERIC(14,2) NOT NULL DEFAULT 0,
    vat_total NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    paid_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'draft', -- draft|issued|sent|paid|overdue|cancelled
    payment_date DATE,
    pdf_file_id UUID,
    billing_details JSONB,
    created_by UUID,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_invoice_status CHECK (status IN ('draft','issued','sent','paid','overdue','cancelled')),
    CONSTRAINT chk_invoice_amounts CHECK (subtotal >= 0 AND vat_total >= 0 AND total_amount = subtotal + vat_total AND paid_amount >= 0),
    CONSTRAINT fk_inv_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_inv_company FOREIGN KEY (company_id) REFERENCES companies(id),
    CONSTRAINT fk_inv_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id),
    CONSTRAINT fk_inv_contract FOREIGN KEY (contract_id) REFERENCES contracts(id),
    CONSTRAINT fk_inv_order FOREIGN KEY (order_id) REFERENCES company_orders(id),
    CONSTRAINT fk_inv_service_order FOREIGN KEY (service_order_id) REFERENCES service_orders(id),
    CONSTRAINT fk_inv_pdf FOREIGN KEY (pdf_file_id) REFERENCES files(id)
);

CREATE INDEX IF NOT EXISTS idx_invoices_tenant ON invoices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invoices_company ON invoices(company_id);
CREATE INDEX IF NOT EXISTS idx_invoices_candidate ON invoices(candidate_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_due ON invoices(due_date) WHERE status IN ('issued','sent','overdue');

CREATE TABLE IF NOT EXISTS invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL,
    line_no INT NOT NULL DEFAULT 1,
    description TEXT NOT NULL,
    qty NUMERIC(12,2) NOT NULL DEFAULT 1,
    unit_price NUMERIC(14,2) NOT NULL DEFAULT 0,
    vat_rate NUMERIC(5,2) NOT NULL DEFAULT 23.00,
    net_total NUMERIC(14,2) GENERATED ALWAYS AS (qty * unit_price) STORED,
    vat_amount NUMERIC(14,2) GENERATED ALWAYS AS (ROUND((qty * unit_price) * (vat_rate/100.0), 2)) STORED,
    gross_total NUMERIC(14,2) GENERATED ALWAYS AS (ROUND((qty * unit_price) * (1 + vat_rate/100.0), 2)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_item_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    CONSTRAINT chk_qty CHECK (qty > 0),
    CONSTRAINT chk_price CHECK (unit_price >= 0)
);

CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_items(invoice_id);

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    invoice_id UUID NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    payment_date DATE NOT NULL,
    method VARCHAR(24) NOT NULL, -- bank_transfer|card|cash|online|other
    provider VARCHAR(32),
    provider_reference VARCHAR(128),
    reference_number VARCHAR(128),
    status VARCHAR(16) NOT NULL DEFAULT 'confirmed', -- pending|confirmed|failed
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_payment_status CHECK (status IN ('pending','confirmed','failed')),
    CONSTRAINT chk_payment_amount CHECK (amount > 0),
    CONSTRAINT fk_pay_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_pay_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_tenant ON payments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    payment_id UUID NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    reason TEXT,
    refund_date DATE NOT NULL DEFAULT (CURRENT_DATE),
    status VARCHAR(16) NOT NULL DEFAULT 'initiated', -- initiated|completed|cancelled
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_refund_status CHECK (status IN ('initiated','completed','cancelled')),
    CONSTRAINT chk_refund_amount CHECK (amount > 0),
    CONSTRAINT fk_ref_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_ref_payment FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_refunds_payment ON refunds(payment_id);
CREATE INDEX IF NOT EXISTS idx_refunds_tenant ON refunds(tenant_id);

-- Авто-подсчёт сумм инвойса из позиций
CREATE OR REPLACE FUNCTION fn_invoice_recalc_totals(p_invoice_id UUID)
RETURNS VOID AS $$
BEGIN
  UPDATE invoices i SET
    subtotal = COALESCE((SELECT ROUND(SUM(net_total),2) FROM invoice_items WHERE invoice_id = p_invoice_id), 0),
    vat_total = COALESCE((SELECT ROUND(SUM(vat_amount),2) FROM invoice_items WHERE invoice_id = p_invoice_id), 0),
    total_amount = COALESCE((SELECT ROUND(SUM(gross_total),2) FROM invoice_items WHERE invoice_id = p_invoice_id), 0),
    updated_at = now()
  WHERE i.id = p_invoice_id;
END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_invoice_recalc_paid(p_invoice_id UUID)
RETURNS VOID AS $$
DECLARE v_paid NUMERIC(14,2);
BEGIN
  SELECT COALESCE(SUM(amount),0) INTO v_paid FROM payments WHERE invoice_id = p_invoice_id AND status = 'confirmed';
  SELECT v_paid - COALESCE(SUM(r.amount) FILTER (WHERE r.status = 'completed'),0)
    INTO v_paid
  FROM payments p
  LEFT JOIN refunds r ON r.payment_id = p.id
  WHERE p.invoice_id = p_invoice_id AND p.status = 'confirmed';

  UPDATE invoices i SET paid_amount = GREATEST(0,v_paid), updated_at = now()
  WHERE i.id = p_invoice_id;

  UPDATE invoices i SET status = CASE
      WHEN i.status <> 'cancelled' AND i.paid_amount >= i.total_amount AND i.total_amount > 0 THEN 'paid'
      WHEN i.status IN ('issued','sent') AND i.due_date < CURRENT_DATE AND i.paid_amount < i.total_amount THEN 'overdue'
      ELSE i.status
    END,
    payment_date = CASE WHEN i.paid_amount >= i.total_amount AND i.total_amount > 0 THEN CURRENT_DATE ELSE i.payment_date END
  WHERE i.id = p_invoice_id;
END; $$ LANGUAGE plpgsql;

-- Триггеры на позиции счёта
DROP TRIGGER IF EXISTS trg_items_recalc_insert ON invoice_items;
CREATE TRIGGER trg_items_recalc_insert
AFTER INSERT ON invoice_items
FOR EACH ROW EXECUTE FUNCTION fn_invoice_recalc_totals(NEW.invoice_id);

DROP TRIGGER IF EXISTS trg_items_recalc_update ON invoice_items;
CREATE TRIGGER trg_items_recalc_update
AFTER UPDATE ON invoice_items
FOR EACH ROW EXECUTE FUNCTION fn_invoice_recalc_totals(NEW.invoice_id);

DROP TRIGGER IF EXISTS trg_items_recalc_delete ON invoice_items;
CREATE TRIGGER trg_items_recalc_delete
AFTER DELETE ON invoice_items
FOR EACH ROW EXECUTE FUNCTION fn_invoice_recalc_totals(OLD.invoice_id);

-- Триггеры на платежи/возвраты
DROP TRIGGER IF EXISTS trg_payments_recalc_insert ON payments;
CREATE TRIGGER trg_payments_recalc_insert
AFTER INSERT ON payments
FOR EACH ROW EXECUTE FUNCTION fn_invoice_recalc_paid(NEW.invoice_id);

DROP TRIGGER IF EXISTS trg_payments_recalc_update ON payments;
CREATE TRIGGER trg_payments_recalc_update
AFTER UPDATE ON payments
FOR EACH ROW EXECUTE FUNCTION fn_invoice_recalc_paid(NEW.invoice_id);

DROP TRIGGER IF EXISTS trg_payments_recalc_delete ON payments;
CREATE TRIGGER trg_payments_recalc_delete
AFTER DELETE ON payments
FOR EACH ROW EXECUTE FUNCTION fn_invoice_recalc_paid(OLD.invoice_id);

DROP TRIGGER IF EXISTS trg_refunds_recalc_all ON refunds;
CREATE TRIGGER trg_refunds_recalc_all
AFTER INSERT OR UPDATE OR DELETE ON refunds
FOR EACH ROW EXECUTE FUNCTION fn_invoice_recalc_paid(COALESCE(NEW.payment_id, OLD.payment_id)::uuid);

-- Авто-перевод в overdue при апдейте инвойса
CREATE OR REPLACE FUNCTION fn_invoice_status_overdue()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status IN ('issued','sent') AND NEW.due_date < CURRENT_DATE AND NEW.paid_amount < NEW.total_amount THEN
    NEW.status := 'overdue';
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_invoice_overdue ON invoices;
CREATE TRIGGER trg_invoice_overdue
BEFORE INSERT OR UPDATE ON invoices
FOR EACH ROW EXECUTE FUNCTION fn_invoice_status_overdue();

-- Представления
CREATE OR REPLACE VIEW v_invoices_outstanding AS
SELECT i.*, (i.total_amount - i.paid_amount) AS outstanding
FROM invoices i
WHERE i.status IN ('issued','sent','overdue') AND (i.total_amount - i.paid_amount) > 0;

CREATE OR REPLACE VIEW v_invoices_overdue AS
SELECT * FROM invoices
WHERE status = 'overdue' AND due_date < CURRENT_DATE;

CREATE OR REPLACE VIEW v_payments_summary_by_company AS
SELECT i.tenant_id, i.company_id, COUNT(DISTINCT i.id) AS invoices_count,
       ROUND(SUM(i.total_amount),2) AS invoiced,
       ROUND(SUM(i.paid_amount),2) AS paid,
       ROUND(SUM(GREATEST(i.total_amount - i.paid_amount,0)),2) AS outstanding
FROM invoices i
GROUP BY i.tenant_id, i.company_id;

-- RLS
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE refunds ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS rls_invoices_tenant ON invoices USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY IF NOT EXISTS rls_invoice_items_parent ON invoice_items USING (
  EXISTS (SELECT 1 FROM invoices i WHERE i.id = invoice_items.invoice_id AND i.tenant_id = current_setting('app.tenant_id')::uuid)
);
CREATE POLICY IF NOT EXISTS rls_payments_tenant ON payments USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY IF NOT EXISTS rls_refunds_tenant ON refunds USING (tenant_id = current_setting('app.tenant_id')::uuid);

COMMIT;