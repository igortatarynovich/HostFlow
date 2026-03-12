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
   - Frontend static QA gate:
     - `npm --prefix hostflow-frontend run qa:static`
     - Включает `routes:check` (консистентность `NAV_ITEMS`/`APP_ROUTES`), `activation:check` (целостность activation route-map + allowlist), `comm:gates:check` (обязательный communications feature-gating), `module:permissions:check` (module-permission mapping integrity), `permissions:check`, `i18n:check`, production `build`.

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
   - Для release-gate сценариев `A/B/C` обновить run-log в `docs/crm-production-readiness-ssot.md` (раздел `10.1`) по шаблону `docs/manual-checklist/f7-scenario-protocol.md`.
   - Для каждого прогона `F7` сохранять отдельный run-record по шаблону `docs/manual-checklist/f7-run-record-template.md` и указывать ссылку на него в колонке `Evidence` раздела `10.1`.
   - Для создания run-record файла использовать CLI: `npm run f7:run-record:new -- --scenario <a|b|c> --env <staging|production> --tenant <slug> --owner "<name/role>"`.
   - Для полного авто-обновления `F7` использовать: `npm run f7:run-record:apply -- --scenario <a|b|c> --env <staging|production> --tenant <slug> --owner "<name/role>" --result <PASS|FAIL|BLOCKED|IN_PROGRESS>`.
   - Для мгновенной вставки в SSOT использовать `--print-ssot-row` (CLI выводит готовую строку таблицы `10.1`).
   - Для автодобавления записи в `10.1` использовать `--append-ssot` (CLI вставит строку и защитит от дубля по `date/scenario/env/tenant`).
   - Для синхронизации статуса в execution board использовать `--sync-board-status` (обновляет статус сценария в разделе `10` на основе `--result`).
   - `--append-ssot` по умолчанию запускает валидацию `f7:run-log:check` сразу после вставки строки; отключение доступно флагом `--no-validate`.
   - Перед финальным обновлением `10.1` запускать: `npm run f7:run-log:check`.

Готово — можно выкатывать 🚀
