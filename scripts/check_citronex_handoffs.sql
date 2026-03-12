-- Проверка handoff для тенанта Citronex (client_tenant_id = '517319d0-b53e-493d-9ac8-40f23091a35d').
-- Полные данные у клиента только у кандидатов с accepted handoff В ТЕНАНТ (client_tenant_id не NULL).
-- Запуск: docker compose exec db psql -U hostflow -d hostflow -f - < scripts/check_citronex_handoffs.sql
-- или: docker compose exec db psql -U hostflow -d hostflow -c "$(cat scripts/check_citronex_handoffs.sql)"

\echo '=== Accepted handoffs WITH client_tenant_id = Citronex (полные данные у клиента) ==='
SELECT id, candidate_id, client_tenant_id, client_company_id, status, reviewed_at
FROM candidate_handoffs
WHERE client_tenant_id = '517319d0-b53e-493d-9ac8-40f23091a35d'
  AND status = 'accepted'
ORDER BY reviewed_at DESC NULLS LAST;

\echo ''
\echo '=== Все accepted handoffs (client_tenant_id или client_company_id) для справки ==='
SELECT id, candidate_id, client_tenant_id, client_company_id, status, reviewed_at
FROM candidate_handoffs
WHERE status = 'accepted'
ORDER BY reviewed_at DESC NULLS LAST;
