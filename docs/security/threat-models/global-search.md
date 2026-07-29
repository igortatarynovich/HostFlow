# Threat Model — Global search & directory retrieval

## Assets

- Tenant-scoped CRM entities surfaced by `GET /api/v1/search` (candidates, companies, vacancies, leads, documents, invoices, orders, conversations, tasks).
- Cross-tenant company directory for agency linking (`GET /api/v1/tenants/{id}/links/search-companies`).

## Trust boundaries

- Authenticated CRM user ↔ search / directory API ↔ Postgres (RLS + membership) ↔ structured security log.

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| GS-1 | Cross-tenant retrieval | `scope_tenant_id` / path tenant without membership |
| GS-2 | Query leakage in logs | raw `q` / FTS SQL in security or debug logs |
| GS-3 | Over-broad result set | missing RBAC slice filters (leads/docs/tasks) |
| GS-4 | Directory enumeration | company search across tenants without role gate |

## Митигации (baseline)

- `get_db_with_tenant` + `ensure_user_can_access_tenant` on scope override.
- Role gate `GLOBAL_SEARCH_ROLES` / admin|owner for link company search.
- Audit: `search.retrieval.requested|completed|denied` via `emit_retrieval_security_event_v1` (no raw query in `extra`).
- CI: `scripts/security/check_retrieval_call_sites.py`.

## Тесты

- Short `q` → 422.
- Foreign `scope_tenant_id` without membership → 403 + `search.retrieval.denied`.
- Link search tenant mismatch → 403 + denied event.

## Связанные спеки

- [`retrieval-audit-governance.md`](../retrieval-audit-governance.md)
- [`runtime-roadmap.md`](../runtime-roadmap.md) Phase 6
