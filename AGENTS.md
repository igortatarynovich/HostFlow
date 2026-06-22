# HostFlow Repository Guidelines  
_Живой инженерный канон и стандарты разработки проекта HostFlow_

Этот документ определяет структуру, стандарты и правила разработки проекта HostFlow. Он служит источником истины для всех модулей (backend, frontend, инфраструктура, AI-агенты) и регулярно обновляется по мере развития системы.

## Project Structure & Module Organization
The FastAPI backend lives in `backend/app` with API routes under `backend/app/api/v1`, SQLAlchemy models in `backend/app/models`, and service helpers in `backend/app/services`. Database migrations are tracked via Alembic: the Alembic configuration file `alembic.ini` is located in the project root, and migration scripts are stored in `backend/alembic/versions`. Reusable scripts for seeding and utilities are in `backend/app/db/seeds`. Automated tests target live endpoints and reside in `backend/tests`. The React client is in `hostflow-frontend/src`, organised by feature modules (for example `src/modules/candidates` and `src/modules/vacancies`). Shared documentation and architecture notes belong in `docs/`, and incremental tooling lives under `scripts/` and the top-level `Makefile`.

### Alembic Layout & Safety Checklist
- **Single source of truth:** запускайте Alembic только из `/opt/HostFlow` (repo root) — здесь лежит `alembic.ini` и сюда смотрит `script_location`.
- **Versions folder:** все ревизии должны находиться в `/opt/HostFlow/backend/alembic/versions`. Не копируйте миграции в `/opt/backend` или другие каталоги: они не подцепятся.
- **В контейнере:** backend-сервис монтирует `./backend` в `/app`, поэтому изменения в `backend/alembic/versions` автоматически видны внутри контейнера по тому же пути. Проверка: `docker compose exec backend ls backend/alembic/versions`.
- **Запуск миграций:** используйте `docker compose exec backend alembic upgrade heads` (или конкретный revision) — так гарантируется, что применяется актуальный код контейнера.
- **Повторный прогон:** если ревизия упала, удалите только её запись из `alembic_version` и повторите `alembic upgrade <rev>`. Перенос файлов между директориями запрещён.

## Build, Test, and Development Commands
### Makefile Commands

- `make up` — Запускает backend (Uvicorn с автоперезапуском) и необходимые сервисы.
- `make down` — Останавливает все сервисы и контейнеры.
- `make mig` — Применяет все доступные миграции базы данных.
- `make mig-rev` — Создаёт новую ревизию Alembic (указать msg через `MSG="описание"`).
- `make seed` — Заполняет базу начальными данными (сиды из `backend/app/db/seeds`).
- `make test` — Запускает все тесты (pytest).
- `make lint` — Запускает линтеры и автоформатирование.

Для клиента: установите зависимости в `hostflow-frontend` и используйте `npm run dev` для локальной разработки, `npm run build` для сборки, и `npm run preview` для проверки production-версии.

## Coding Style & Naming Conventions
Python code uses 4-space indentation, type hints, and snake_case for modules, packages, and variables. Enforce formatting and linting with `ruff --fix` (Python), type checking via `mypy`, and import ordering via `isort --profile=black`; all эти инструменты запускаются автоматически через pre-commit hooks. Для фронтенда используется `eslint` (см. `hostflow-frontend/eslint.config.js`). React и TypeScript исходники используют функциональные компоненты, PascalCase для компонентов и camelCase для хуков и вспомогательных функций. Tailwind utility classes должны оставаться в `*.tsx` файлах для колокации стилей.

## Testing Guidelines
Pytest is configured in `backend/pytest.ini` with asyncio support; tests expect an API at `http://localhost:8000` and bearer tokens supplied via `VIEWER_TOKEN`/`MANAGER_TOKEN`. Name new test modules `test_<feature>.py`, mirror the API surface, and assert both status codes and payload shapes. Add integration tests whenever you expose a new route, and keep seed data scripts up to date so fixtures succeed locally and in CI.

`backend/tests/api/test_public_intake.py` и связанные интеграционные тесты нужно гонять только в окружении с доступной Postgres — в песочницах без реальной базы они падают еще на попытке коннекта.

## Commit & Pull Request Guidelines
Commit messages follow a short `scope: summary` convention (for example `API: mount stages under /api/v1` or `labs(docs-module): ruleset v1.1`). Group related changes into coherent commits, and reference tickets in the body when relevant. Pull requests should outline the change, list validation steps (such as `pytest` or `npm run build`), attach screenshots for UI updates, and link any blocking migrations or feature flags. Tag reviewers from the affected domain (backend, frontend, or tooling) to keep feedback focused.

### Pull Request Checklist
- [ ] Обновлены соответствующие файлы в `docs/specs/**` при изменении логики или моделей
- [ ] Добавлены/обновлены тесты
- [ ] Проведён `make lint` и `make test`
- [ ] Проверены миграции Alembic и сиды
- [ ] Обновлены связанные спеки и README при необходимости

---

## Multi-tenancy & RLS

- Каждая запись в базе данных содержит поле `tenant_id`.
- Включён Row-Level Security (RLS) на уровне базы данных.
- Приложение устанавливает текущий tenant через `current_setting('app.tenant_id')` в сессии PostgreSQL.
- Все запросы и операции должны учитывать tenant isolation.

## Notes for AI Agents (Codex/ChatGPT)

1. Перед выполнением изменений всегда формируйте план и список файлов для редактирования и ожидайте подтверждения.
2. Не выполняйте shell-команды, коммиты или push без явного разрешения.
3. При изменении схемы базы данных необходимо:
   - Создать миграцию через Alembic (см. Makefile).
   - Обновить сиды в `backend/app/db/seeds`, чтобы тестовые/локальные данные были актуальны.

## Linting & Typing Tools

- Python: `ruff` (линтинг+форматирование), `mypy` (type checking), `pre-commit` (hooks).
- JS/TS: `eslint` (с конфигом в `hostflow-frontend/eslint.config.js`).


- Основные связи: `candidate↔client`, `candidate↔documents`, `client↔vacancies`.
- Источник истины по статусу, документам и связям — карточка кандидата.
- Все напоминания и контроль сроков по документам реализуются через связанные объекты документов.


## Living Spec Integration
HostFlow использует живую спецификацию в `docs/specs/`. Перед изменением логики, структуры моделей или API необходимо:
1. Проверить и при необходимости обновить соответствующие файлы (`core.md`, `modules/*.md`).
2. Согласовать изменения с ответственными разработчиками или агентом Codex.
3. После обновления спецификации — сгенерировать/обновить код и тесты.
4. Поддерживать согласованность кода и документации на всех этапах.

## Cursor Cloud specific instructions

Дев-окружение в облаке использует **локальный PostgreSQL** (а не docker-compose). Постгрес ставится один раз и сохраняется в snapshot; update-скрипт только переустанавливает зависимости (Python venv `.venv312` + npm в `hostflow-frontend`).

### Services
- **PostgreSQL 16** (local cluster): role/db `hostflow`/`hostflow` on `localhost:5432`. Start if not running: `sudo pg_ctlcluster 16 main start` (или `sudo service postgresql start`). Дев-БД уже мигрирована до head и лежит в snapshot.
- **Backend (FastAPI/uvicorn)** on `:8000`: `make up` (reads repo-root `.env`, runs `uvicorn --reload`). Admin seeded on startup: `admin@hostflow.dev` / `Admin@025`. API requires header `X-Tenant-Id: 11111111-1111-1111-1111-111111111111` + `Authorization: Bearer <token>` (получить через `POST /api/v1/auth/login`).
- **Frontend (Vite/React)** on `:5173`: `cd hostflow-frontend && npm run dev`. API base auto-resolves to `http://localhost:8000/api/v1` on localhost.
- Lint: `.venv312/bin/ruff check backend` (Python), `npm run lint` in `hostflow-frontend` (eslint). Tests: from `backend/` run `PYTHONPATH=/workspace:/workspace/backend /workspace/.venv312/bin/pytest -q` (in-process ASGI against local Postgres).

### Required env (`/workspace/.env`, gitignored — recreate if missing)
`make up`/alembic read these. The Makefile's built-in defaults point at docker host `db:5432`, so the localhost `.env` below is **required** for non-docker dev:
```
DATABASE_URL=postgresql+asyncpg://hostflow:hostflow@localhost:5432/hostflow
ASYNC_DATABASE_URL=postgresql+asyncpg://hostflow:hostflow@localhost:5432/hostflow
SYNC_DATABASE_URL=postgresql+psycopg://hostflow:hostflow@localhost:5432/hostflow
ALEMBIC_DATABASE_URL=postgresql+psycopg://hostflow:hostflow@localhost:5432/hostflow
JWT_SECRET=hostflow-dev-secret
TENANT_ID=11111111-1111-1111-1111-111111111111
```

### Dependency pin (critical)
`requirements.txt` pins are too loose. Newer FastAPI (≥0.116) adds `_IncludedRouter` route objects that `prometheus-fastapi-instrumentator` 8.x cannot introspect (`'_IncludedRouter' object has no attribute 'path'`), which makes **every request return 500**. Keep `fastapi==0.115.6` + `prometheus-fastapi-instrumentator==7.0.0` (with `starlette 0.41.x`). Run `scripts/cursor-cloud-update.sh` on agent startup; do not blindly `pip install -U fastapi`.

### Migration caveats (non-obvious)
`alembic upgrade heads` does **not** apply cleanly on a fresh DB (pre-existing bugs). The snapshot DB is already at head. If you ever rebuild the DB from scratch, this sequence works (run from repo root with `.env` loaded, `PYTHONPATH=backend`):
1. Pre-create `alembic_version` with `version_num VARCHAR(255)` (default 32 chars is too short for some revision ids).
2. Apply parallel branch tips in dependency order so "create table" runs before sibling "alter table" migrations: `202512010310_meta_leads_pipeline` (creates `leads`), then `202512150001_unify_documents_module` (creates `document_templates`), `202512150001_documents_module_restructure`, `202512010300_ruleset_versioning_foundation`, `202512010300_expand_reminder_entity_id`, `202512210001_documents_type_dedup`, then `alembic upgrade 202605050001`.
3. Skip the broken double-`CREATE TYPE` migration `202605200001`: manually `CREATE TYPE document_scan_status_enum ...` + a stub `document_scan_sessions` table, then `alembic stamp 202605200001` (the next migration drops them), then `alembic upgrade heads`.
4. Post-migration fixups the bootstrap seed needs: `ALTER TYPE role ADD VALUE IF NOT EXISTS 'superadmin';` and `ALTER TABLE users ALTER COLUMN preferences SET DEFAULT '{}'::jsonb;` (the seed creates the admin with role `superadmin` and omits `preferences`, which is NOT NULL without a default).

Many `pytest` failures stem from pre-existing bugs and schema/seed gaps (≈60 tests pass); CI's `alembic upgrade head` also fails on a fresh DB for the reasons above.
