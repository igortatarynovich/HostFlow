-- Проверка типа тенанта Citronex
-- Замените 'citronex@hostflow.dev' на email пользователя или tenant_id на ID тенанта

-- 1. Найти tenant по email пользователя
SELECT 
    t.id,
    t.name,
    t.slug,
    t.type,
    u.email
FROM tenants t
JOIN users u ON u.tenant_id = t.id
WHERE u.email = 'citronex@hostflow.dev'
LIMIT 1;

-- 2. Найти tenant по slug
SELECT 
    id,
    name,
    slug,
    type
FROM tenants
WHERE slug = 'citronex'
LIMIT 1;

-- 3. Проверить TenantLink для этого tenant
SELECT 
    tl.id,
    tl.agency_tenant_id,
    tl.client_tenant_id,
    tl.client_company_id,
    tl.status,
    a.name as agency_name,
    c.name as client_company_name
FROM tenant_links tl
LEFT JOIN tenants a ON a.id = tl.agency_tenant_id
LEFT JOIN companies c ON c.id = tl.client_company_id
WHERE tl.client_tenant_id = (
    SELECT id FROM tenants WHERE slug = 'citronex' LIMIT 1
)
OR tl.client_tenant_id = (
    SELECT tenant_id FROM users WHERE email = 'citronex@hostflow.dev' LIMIT 1
);

-- 4. Полная информация о tenant и его связях
WITH citronex_tenant AS (
    SELECT id, name, slug, type 
    FROM tenants 
    WHERE slug = 'citronex' 
    OR id = (SELECT tenant_id FROM users WHERE email = 'citronex@hostflow.dev' LIMIT 1)
    LIMIT 1
)
SELECT 
    t.id as tenant_id,
    t.name as tenant_name,
    t.slug,
    t.type as tenant_type,
    CASE 
        WHEN t.type = 'company' THEN 'YES - Client tenant (company type)'
        WHEN EXISTS (
            SELECT 1 FROM tenant_links tl 
            WHERE tl.client_tenant_id = t.id AND tl.status = 'active'
        ) THEN 'YES - Client tenant (via TenantLink)'
        ELSE 'NO - Not a client tenant'
    END as is_client_tenant,
    COUNT(tl.id) as tenant_links_count
FROM citronex_tenant t
LEFT JOIN tenant_links tl ON (
    tl.client_tenant_id = t.id 
    OR tl.agency_tenant_id = t.id
) AND tl.status = 'active'
GROUP BY t.id, t.name, t.slug, t.type;
