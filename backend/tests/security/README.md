# Security regression suite

Интеграционные и узкие тесты для security perimeter.

- **Session / RLS guard:** `test_tenant_rls_session_guard.py`
- **Классификация elevated / support (unit):** `test_api_tenant_context_unit.py`
- **Superadmin cross-tenant bind (Postgres):** `test_superadmin_elevated_bind.py` (`postgres_integration`)
- **Tenant A/B matrix (API + Postgres):** `tests/api/test_tenant_isolation.py` (маркер `postgres_integration`; в CI — отдельный job + общий `tests/security`)

Полный A/B API по-прежнему в `tests/api/test_tenant_isolation.py`; маркер и CI см. `pytest.ini` и `.github/workflows/backend-ci.yml`.
