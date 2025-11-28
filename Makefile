# ===== HostFlow Makefile =====

# ---- Load .env (export all non-comment KEY=VAL) ----
ifneq (,$(wildcard .env))
include .env
endif
export ASYNC_DATABASE_URL SYNC_DATABASE_URL ALEMBIC_DATABASE_URL DATABASE_URL TENANT_ID

# ---- Paths / tools ----
VENV        ?= .venv312
PY          := $(VENV)/bin/python
PIP         := $(VENV)/bin/pip
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
	@echo "  make install        - create venv and install deps"
	@echo "  make upg            - alembic upgrade head"
	@echo "  make mig msg=...    - alembic autogenerate revision"
	@echo "  make down           - alembic downgrade -1"
	@echo "  make seed-demo      - seed demo data (5 companies, 5 vacancies, 25 candidates)"
	@echo "  make env-print      - print effective DB URLs"
	@echo "  make curl-list      - GET /api/v1/candidates (needs TOKEN)"
	@echo "  make curl-create    - POST /api/v1/candidates (needs TOKEN)"
	@echo "  make get-token      - print JWT for admin@hostflow.dev / admin"
	@echo ""

# ---- Deps ----
.PHONY: install
install:
	@test -x "$(PY)" || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	@if [ -f requirements.txt ]; then \
		$(PIP) install -r requirements.txt; \
	else \
		$(PIP) install "fastapi>=0.110" "uvicorn[standard]" "sqlalchemy>=2.0" \
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
	$(ALEMBIC) upgrade heads

.PHONY: down
down:
	$(ALEMBIC) downgrade -1

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
