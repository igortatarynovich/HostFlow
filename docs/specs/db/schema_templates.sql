

BEGIN;

-- 1. Таблица шаблонов документов
CREATE TABLE IF NOT EXISTS document_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT 'v1',
    category TEXT NOT NULL, -- contract | invoice | act | certificate | other
    file_id UUID, -- связанный оригинальный файл шаблона (DOCX, PDF)
    engine TEXT NOT NULL DEFAULT 'jinja2', -- jinja2 | markdown | html
    language VARCHAR(5) DEFAULT 'pl',
    placeholders JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_template_code_version UNIQUE (tenant_id, code, version),
    CONSTRAINT fk_template_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_template_file FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE INDEX IF NOT EXISTS idx_templates_tenant ON document_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_templates_category ON document_templates(category);
CREATE INDEX IF NOT EXISTS idx_templates_active ON document_templates(is_active);

-- 2. Таблица историй рендеров (использований шаблонов)
CREATE TABLE IF NOT EXISTS document_template_renders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    template_id UUID NOT NULL,
    related_model TEXT, -- например 'invoice' или 'contract'
    related_id UUID,
    render_time TIMESTAMPTZ DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'success', -- success | failed
    output_file_id UUID,
    variables JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_by UUID,
    CONSTRAINT fk_render_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_render_template FOREIGN KEY (template_id) REFERENCES document_templates(id) ON DELETE CASCADE,
    CONSTRAINT fk_render_output FOREIGN KEY (output_file_id) REFERENCES files(id)
);

CREATE INDEX IF NOT EXISTS idx_renders_template ON document_template_renders(template_id);
CREATE INDEX IF NOT EXISTS idx_renders_tenant ON document_template_renders(tenant_id);
CREATE INDEX IF NOT EXISTS idx_renders_status ON document_template_renders(status);

-- 3. Представление — активные шаблоны с последним рендером
CREATE OR REPLACE VIEW v_active_templates_with_last_render AS
SELECT t.id AS template_id,
       t.name,
       t.code,
       t.version,
       t.category,
       t.language,
       t.is_active,
       r.render_time AS last_render_at,
       r.status AS last_status
FROM document_templates t
LEFT JOIN LATERAL (
    SELECT render_time, status
    FROM document_template_renders r
    WHERE r.template_id = t.id
    ORDER BY r.render_time DESC
    LIMIT 1
) r ON TRUE
WHERE t.is_active = TRUE;

-- 4. Политики RLS
ALTER TABLE document_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_template_renders ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS rls_templates_tenant ON document_templates USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY IF NOT EXISTS rls_renders_tenant ON document_template_renders USING (tenant_id = current_setting('app.tenant_id')::uuid);

COMMIT;