BEGIN;

-- 0) Расширенная карточка компании (основная таблица)
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    slug TEXT NOT NULL,
    legal_name TEXT NOT NULL,
    display_name TEXT,
    reg_no TEXT,
    tax_id TEXT,
    vat_eu TEXT,
    established_at DATE,
    registered_address JSONB NOT NULL DEFAULT '{}'::jsonb,
    operational_address JSONB,
    default_currency CHAR(3) NOT NULL DEFAULT 'PLN',
    payment_terms_days INT NOT NULL DEFAULT 30,
    billing_address JSONB,
    invoice_email TEXT,
    einvoice_peppol JSONB, -- {participant_id, scheme}
    fin_check_status TEXT NOT NULL DEFAULT 'pending', -- pending | pass | fail | manual_review
    aml_required BOOLEAN NOT NULL DEFAULT FALSE,
    iso9001 BOOLEAN NOT NULL DEFAULT FALSE,
    insurance_policy_no TEXT,
    doc_valid_until DATE,
    readiness_score NUMERIC(5,2) DEFAULT 0,
    client_portal_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    client_portal_url TEXT,
    portal_last_sync TIMESTAMPTZ,
    provider_ids UUID[] DEFAULT '{}',
    webhooks JSONB DEFAULT '[]'::jsonb,
    branding JSONB DEFAULT '{}'::jsonb,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_companies_slug UNIQUE (tenant_id, slug),
    CONSTRAINT chk_companies_payment_terms CHECK (payment_terms_days BETWEEN 1 AND 120),
    CONSTRAINT chk_companies_currency CHECK (char_length(default_currency) = 3),
    CONSTRAINT chk_companies_fin_status CHECK (fin_check_status IN ('pending','pass','fail','manual_review')),
    CONSTRAINT chk_companies_registered_addr CHECK (
        jsonb_typeof(registered_address) = 'object'
        AND registered_address ? 'country'
        AND registered_address ? 'city'
        AND registered_address ? 'street'
        AND registered_address ? 'zip'
    ),
    CONSTRAINT chk_companies_portal_url CHECK (client_portal_enabled = FALSE OR client_portal_url IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_tax_id ON companies(tenant_id, tax_id) WHERE tax_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_companies_active ON companies(tenant_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_companies_provider_ids ON companies USING GIN(provider_ids);

-- 1) Банковские реквизиты компании
CREATE TABLE IF NOT EXISTS company_bank_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    iban TEXT NOT NULL,
    swift_bic TEXT,
    bank_name TEXT,
    country CHAR(2),
    label TEXT,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at TIMESTAMPTZ,
    CONSTRAINT fk_cba_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT chk_cba_country CHECK (country IS NULL OR char_length(country) = 2),
    CONSTRAINT chk_cba_iban CHECK (char_length(iban) BETWEEN 15 AND 34)
);

CREATE INDEX IF NOT EXISTS idx_cba_company ON company_bank_accounts(company_id);
CREATE INDEX IF NOT EXISTS idx_cba_tenant ON company_bank_accounts(tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_cba_primary ON company_bank_accounts(company_id) WHERE is_primary = TRUE;

-- 2) Контактные лица компании
CREATE TABLE IF NOT EXISTS company_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    role TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    is_portal_user BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at TIMESTAMPTZ,
    CONSTRAINT fk_cc_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT chk_cc_role CHECK (role IN ('OWNER','ACC','HR','FM','OPS','LEGAL')),
    CONSTRAINT chk_cc_email CHECK (position('@' IN email) > 1)
);

CREATE INDEX IF NOT EXISTS idx_cc_company ON company_contacts(company_id);
CREATE INDEX IF NOT EXISTS idx_cc_tenant ON company_contacts(tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_cc_primary ON company_contacts(company_id) WHERE is_primary = TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_cc_email ON company_contacts(tenant_id, company_id, lower(email));

-- 3) Операционная и комплаенс информация
CREATE TABLE IF NOT EXISTS company_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    fleet_tractors INT DEFAULT 0,
    fleet_intl_perc NUMERIC(5,2),
    fleet_local_perc NUMERIC(5,2),
    trailers JSONB DEFAULT '{}'::jsonb,        -- {mega:int, standard:int, frigo:int, container:int}
    lanes JSONB DEFAULT '{}'::jsonb,           -- {origins:[], destinations:[]}
    cargo_types TEXT[] DEFAULT '{}',
    languages TEXT[] DEFAULT '{}',
    preferred_nationalities TEXT[] DEFAULT '{}',
    has_adr_operations BOOLEAN NOT NULL DEFAULT FALSE,
    work_modes TEXT[] DEFAULT '{}',            -- e.g. {UOP,B2B,LEASE}
    fin_check_status TEXT NOT NULL DEFAULT 'pending', -- синхронизируется с финмодулем
    aml_required BOOLEAN NOT NULL DEFAULT FALSE,
    iso9001 BOOLEAN NOT NULL DEFAULT FALSE,
    insurance_policy_no TEXT,
    doc_valid_until DATE,
    provider_ids UUID[] DEFAULT '{}',
    webhooks JSONB DEFAULT '[]'::jsonb,
    branding JSONB DEFAULT '{}'::jsonb,
    last_compliance_check_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_co_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT uq_co_company UNIQUE (company_id),
    CONSTRAINT chk_co_fleet_intl CHECK (fleet_intl_perc IS NULL OR (fleet_intl_perc BETWEEN 0 AND 100)),
    CONSTRAINT chk_co_fleet_local CHECK (fleet_local_perc IS NULL OR (fleet_local_perc BETWEEN 0 AND 100)),
    CONSTRAINT chk_co_fleet_total CHECK (
        COALESCE(fleet_intl_perc, 0) + COALESCE(fleet_local_perc, 0) <= 100
    ),
    CONSTRAINT chk_co_fin_status CHECK (fin_check_status IN ('pending','pass','fail','manual_review'))
);

CREATE INDEX IF NOT EXISTS idx_co_company ON company_operations(company_id);
CREATE INDEX IF NOT EXISTS idx_co_tenant ON company_operations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_co_cargo_types ON company_operations USING GIN(cargo_types);

-- 4) Представление готовности профиля (для API /companies/{id}/readiness)
CREATE OR REPLACE VIEW v_company_profile_readiness AS
SELECT
    c.id AS company_id,
    c.tenant_id,
    (c.legal_name IS NOT NULL AND c.tax_id IS NOT NULL) AS has_legal,
    EXISTS (
        SELECT 1 FROM company_contacts cc
        WHERE cc.company_id = c.id AND cc.is_primary = TRUE AND cc.archived_at IS NULL
    ) AS has_primary_contact,
    EXISTS (
        SELECT 1 FROM company_bank_accounts ba
        WHERE ba.company_id = c.id AND ba.is_primary = TRUE AND ba.archived_at IS NULL
    ) AS has_primary_bank,
    COALESCE(co.fin_check_status, 'pending') AS fin_check_status,
    (c.invoice_email IS NOT NULL AND c.payment_terms_days BETWEEN 1 AND 120) AS billing_ready,
    (co.doc_valid_until IS NULL OR co.doc_valid_until >= now()::date) AS compliance_valid,
    c.client_portal_enabled,
    c.readiness_score,
    CASE
        WHEN NOT (c.legal_name IS NOT NULL AND c.tax_id IS NOT NULL) THEN 'legal_missing'
        WHEN NOT EXISTS (
            SELECT 1 FROM company_contacts cc WHERE cc.company_id = c.id AND cc.is_primary = TRUE AND cc.archived_at IS NULL
        ) THEN 'contact_missing'
        WHEN NOT EXISTS (
            SELECT 1 FROM company_bank_accounts ba WHERE ba.company_id = c.id AND ba.is_primary = TRUE AND ba.archived_at IS NULL
        ) THEN 'bank_missing'
        WHEN NOT (c.invoice_email IS NOT NULL AND c.payment_terms_days BETWEEN 1 AND 120) THEN 'billing_invalid'
        WHEN NOT (co.doc_valid_until IS NULL OR co.doc_valid_until >= now()::date) THEN 'compliance_expired'
        ELSE 'ready'
    END AS readiness_state
FROM companies c
LEFT JOIN company_operations co ON co.company_id = c.id;

-- 5) Триггеры на обновление updated_at
CREATE OR REPLACE FUNCTION trg_companies_touch_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS t_companies_touch_updated ON companies;
CREATE TRIGGER t_companies_touch_updated
BEFORE UPDATE ON companies
FOR EACH ROW
EXECUTE FUNCTION trg_companies_touch_updated();

CREATE OR REPLACE FUNCTION trg_co_touch_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS t_co_touch_updated ON company_operations;
CREATE TRIGGER t_co_touch_updated
BEFORE UPDATE ON company_operations
FOR EACH ROW
EXECUTE FUNCTION trg_co_touch_updated();

-- 6) Политики RLS
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_bank_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_operations ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS rls_companies_tenant
ON companies
USING (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY IF NOT EXISTS rls_cba_tenant
ON company_bank_accounts
USING (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY IF NOT EXISTS rls_cc_tenant
ON company_contacts
USING (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY IF NOT EXISTS rls_co_tenant
ON company_operations
USING (tenant_id = current_setting('app.tenant_id')::uuid);

COMMIT;
