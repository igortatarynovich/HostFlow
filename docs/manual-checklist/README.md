# 🛠️ Manual Deployment Checklist

Обновлено для документооборота и метрик.

1. **Подготовить БД**
   - `docker compose exec backend alembic upgrade head`
   - для мульти-хедов: `docker compose exec backend alembic merge heads`

2. **Миграции и сиды**
   - Убедиться, что `ensure_documents_schema()` и `ensure_leads_schema()` прошли без ошибок в логе запуска.
   - Прогнать `docker compose exec backend python -m backend.app.db.seeds.dev_full_seed` (для демо-стендов).

3. **Линты и тесты**
   - `make lint`
   - `make test` (или точечные `pytest backend/tests/api/test_documents.py backend/tests/notifications/test_reminders.py`).

4. **Метрики и наблюдаемость**
   - Проверить, что `/metrics` отдаёт новые счётчики:
     - `hf_documents_overdue_total{tenant_id=...,doc_type=...}`
     - `hf_reminders_triggered_total{tenant_id=...,type=...,severity=...}`
   - Убедиться, что Grafana дашборды Supervisor/Admin/Platform обновлены под новые метрики.

5. **Smoke UI**
   - Проверить таблицу документов: фильтр “Заказан” показывает документы без файлов.
   - Убедиться, что напоминания отображаются и счётчики Readiness обновляются.

6. **Документация**
   - Синхронизировать `docs/specs/modules/documents.md` и `docs/specs/platform/observability.md` с актуальным состоянием.

Готово — можно выкатывать 🚀
