# ===== HostFlow Makefile =====

# ---- Load .env (export all non-comment KEY=VAL) ----
ifneq (,$(wildcard .env))
include .env
endif
ifneq (,$(wildcard backend/.env))
include backend/.env
endif
export ASYNC_DATABASE_URL SYNC_DATABASE_URL ALEMBIC_DATABASE_URL DATABASE_URL TENANT_ID

# ---- Paths / tools (canonical .venv at repo root; legacy .venv312 only if .venv missing) ----
# Old rule "use .venv312 when .venv has no alembic" picked a broken .venv312 over a fresh .venv.
VENV        := $(if $(wildcard .venv/bin/python),.venv,$(if $(wildcard .venv312/bin/python),.venv312,.venv))
PY          := $(VENV)/bin/python
UVICORN     := $(VENV)/bin/uvicorn
ALEMBIC     := $(VENV)/bin/alembic

# ---- Env (safe defaults; overridden by .env above) ----
export PYTHONPATH := backend
export ASYNC_DATABASE_URL ?= postgresql+asyncpg://hostflow:hostflow@db:5432/hostflow
export SYNC_DATABASE_URL  ?= postgresql://hostflow:hostflow@db:5432/hostflow
TENANT_ID   ?= 11111111-1111-1111-1111-111111111111

# ---- Default ----
.DEFAULT_GOAL := help

# ---- Help ----
.PHONY: help
help:
	@echo ""
	@echo "HostFlow commands:"
	@echo "  make up             - run API (uvicorn --reload)"
	@echo "  make install        - create .venv (or use existing), ensure pip, install backend/requirements.txt (PEP 668)"
	@echo "  make test           - pytest with project .venv (ARGS=...); DB host db→127.0.0.1 if DNS fails (see tests/conftest.py)"
	@echo "  make test-search    - shortcut: global search API tests only"
	@echo "  make upg            - alembic upgrade head"
	@echo "  make ensure-automation-schema - ensure automation_rules table exists (dev fallback)"
	@echo "  make mig msg=...    - alembic autogenerate revision"
	@echo "  make down           - alembic downgrade -1"
	@echo "  make seed-demo      - seed demo data (5 companies, 5 vacancies, 25 candidates)"
	@echo "  make env-print      - print effective DB URLs"
	@echo "  make curl-list      - GET /api/v1/candidates (needs TOKEN)"
	@echo "  make curl-create    - POST /api/v1/candidates (needs TOKEN)"
	@echo "  make get-token      - print JWT for admin@hostflow.dev / admin"
	@echo "  make check-meta-oauth-env - verify META_LEADS_* + FRONTEND_URL for Facebook Login (no DB)"
	@echo "  make check-spa-paths - fail on stray /app/... URL literals in backend/app"
	@echo "  make codegen-crm-app-paths - regenerate TS/Python from shared/crm_app_paths.json"
	@echo "  make check-codegen-crm-paths - fail if generated files drift from manifest"
	@echo "  make paths-qa - codegen + SPA literals + frontend route static checks (needs npm in hostflow-frontend)"
	@echo ""

# ---- Tests (need: make install, DB reachable) ----
.PHONY: test
test:
	@test -x "$(PY)" || (echo "Run 'make install' first (PEP 668: do not use system pip)." && exit 1)
	@"$(PY)" -m pytest -c backend/pytest.ini backend/$(if $(strip $(ARGS)),$(ARGS),tests/) -v

.PHONY: test-search
test-search:
	@$(MAKE) test ARGS=tests/api/test_global_search.py

# ---- Deps ----
.PHONY: install
install:
	@test -x "$(PY)" || python3 -m venv "$(VENV)"
	@"$(PY)" -m ensurepip --upgrade 2>/dev/null || true
	@"$(PY)" -m pip install --upgrade pip
	@if [ -f backend/requirements.txt ]; then \
		"$(PY)" -m pip install -r backend/requirements.txt; \
	elif [ -f requirements.txt ]; then \
		"$(PY)" -m pip install -r requirements.txt; \
	else \
		"$(PY)" -m pip install "fastapi>=0.110" "uvicorn[standard]" "sqlalchemy>=2.0" \
		               asyncpg psycopg2-binary greenlet "pydantic[email]" \
		               "passlib[bcrypt]" "python-jose[cryptography]" \
		               email-validator alembic faker; \
	fi

# ---- Run server ----
.PHONY: up
up:
	@echo "[make up] PYTHONPATH=$(PYTHONPATH)"
	@echo "[make up] ASYNC_DATABASE_URL=$(ASYNC_DATABASE_URL)"
	@echo "[make up] SYNC_DATABASE_URL=$(SYNC_DATABASE_URL)"
	$(UVICORN) --app-dir backend app.main:app --reload --reload-dir backend/app

# ---- Alembic ----
.PHONY: mig
mig:
	@test -n "$(msg)" || (echo "Usage: make mig msg=\"your message\"" && exit 1)
	$(ALEMBIC) revision --autogenerate -m "$(msg)"

.PHONY: upg
upg:
	@echo "[make upg] Using venv: $(VENV), DB: $$(echo $(SYNC_DATABASE_URL) | sed 's/:[^:@]*@/:***@/')"
	$(ALEMBIC) -c alembic.ini upgrade head

.PHONY: down
down:
	$(ALEMBIC) downgrade -1

.PHONY: ensure-automation-schema
ensure-automation-schema:
	$(PY) -c "from backend.app.services.ensure_automation_rules_schema import ensure_automation_rules_schema; ensure_automation_rules_schema(); print('automation_rules schema ensured')"

# ---- Seed demo data ----
# Скрипт читает SYNC_DATABASE_URL из окружения
.PHONY: seed
seed: upg
	@echo "[seed] Using DB: $(SYNC_DATABASE_URL)"
	$(PY) backend/app/db/seeds/dev_full_seed.py

.PHONY: seed-demo
seed-demo: upg
	@echo "[seed-demo] Using DB: $(SYNC_DATABASE_URL)"
	$(PY) backend/scripts/seed_demo.py

# ---- Static checks (no venv deps) ----
.PHONY: check-meta-oauth-env
check-meta-oauth-env:
	@python3 scripts/check_meta_oauth_env.py

.PHONY: check-spa-paths
check-spa-paths:
	python3 backend/scripts/check_spa_path_literals.py

.PHONY: codegen-crm-app-paths
codegen-crm-app-paths:
	python3 scripts/codegen/generate_crm_app_paths.py

.PHONY: check-codegen-crm-paths
check-codegen-crm-paths:
	python3 scripts/codegen/generate_crm_app_paths.py --check

.PHONY: paths-qa
paths-qa:
	npm run paths:qa

# ---- Utils ----
.PHONY: env-print
env-print:
	@echo "PYTHONPATH=$(PYTHONPATH)"
	@echo "ASYNC_DATABASE_URL=$(ASYNC_DATABASE_URL)"
	@echo "SYNC_DATABASE_URL=$(SYNC_DATABASE_URL)"
	@echo "TENANT_ID=$(TENANT_ID)"

# ---- Curl helpers (require TOKEN env var) ----
# Получить токен: make get-token
.PHONY: curl-list
curl-list:
	@test -n "$(TOKEN)" || (echo "Set TOKEN env var first"; exit 1)
	curl -s -H "X-Tenant-Id: $(TENANT_ID)" \
	     -H "Authorization: Bearer $(TOKEN)" \
	     http://127.0.0.1:8000/api/v1/candidates | jq .

.PHONY: curl-create
curl-create:
	@test -n "$(TOKEN)" || (echo "Set TOKEN env var first"; exit 1)
	curl -s -X POST http://127.0.0.1:8000/api/v1/candidates \
	  -H "Content-Type: application/json" \
	  -H "X-Tenant-Id: $(TENANT_ID)" \
	  -H "Authorization: Bearer $(TOKEN)" \
	  -d '{ \
	    "first_name": "Ivan", \
	    "last_name": "Ivanov", \
	    "phone": "+48123123123", \
	    "languages": ["pl","ru"], \
	    "stage": "Новый", \
	    "email": "ivan@example.com", \
	    "note": "seed via make", \
	    "manager": "Olha", \
	    "short_id": "C-001" \
	  }' | jq .

# Быстрый вывод access_token для админа
.PHONY: get-token
get-token:
	@curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
	  -H "Content-Type: application/json" \
	  -d '{"email":"admin@hostflow.dev","password":"admin"}' \
	  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])'
