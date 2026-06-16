# HostFlow Platform Tree Map

Purpose: factual filesystem map of the HostFlow asset for transfer/opening package.
Scope date: 2026-05-21 (UTC).

## 1) Root Layout (`/opt/HostFlow`)

```text
HostFlow/
├── backend/                        # Python FastAPI backend (core platform logic)
├── hostflow-frontend/              # React/TypeScript frontend (SPA + public pages)
├── docs/                           # Product/architecture/spec/security/legal documentation
├── deploy/                         # Deployment images/config helpers (e.g., Caddy Dockerfile)
├── scripts/                        # Root operational scripts (seed/backfill/security helpers)
├── shared/                         # Cross-layer generated/canonical artifacts (route paths)
├── legal/                          # Public legal pages (privacy/terms/cookies/RODO)
├── e2e/                            # End-to-end test scenarios
├── backups/                        # DB dumps / backups (sensitive operational data)
├── exports/                        # Exported data artifacts (e.g., CSV)
├── archive/                        # Archived legacy artifacts
├── reports/                        # Static analysis reports (deptry/ruff/vulture)
├── app/                            # Root-level python package shim
├── opencv_contrib/                 # Vendored OpenCV contrib source tree
├── docker-compose.yml              # Main local runtime composition
├── docker-compose.caddy.yml        # Caddy-focused compose override
├── Caddyfile                       # Reverse proxy / static serving config
├── Makefile                        # Build/test/qa helper targets
├── package.json                    # Root JS tooling + scripts
├── playwright.config.ts            # Playwright config
├── requirements.txt                # Root python requirements
└── AGENTS.md                       # Engineering/agent operating rules
```

## 2) Backend Map (`/opt/HostFlow/backend`)

```text
backend/
├── app/
│   ├── main.py                     # App entrypoint, router wiring, middleware, static mounts
│   ├── api/
│   │   ├── v1/                     # Main private API surface (CRM/HR/admin/settings/etc.)
│   │   └── public/                 # Public intake/portal/notifications APIs
│   ├── auth/                       # Auth routers, JWT deps, membership/role checks
│   ├── core/                       # Settings, queue abstraction, storage, observability, security utils
│   ├── db/                         # Session/deps/base DB wiring
│   ├── models/                     # SQLAlchemy domain models (tenancy/recruitment/docs/hr/comms/billing)
│   ├── modules/                    # Domain modules (leads, documents, companies, vacancies, notifications)
│   ├── services/                   # Business services/workflows/automation/integrations logic
│   ├── schemas/                    # Pydantic schemas
│   ├── constants/                  # Canonical enums/constants/path keys
│   ├── security/                   # Security event/taxonomy/runtime-context modules
│   ├── observability/              # Metrics helpers
│   ├── document_types/             # Document-type definitions
│   ├── jobs/                       # Background job modules
│   └── uploads/                    # App-level local uploaded files
├── alembic/
│   └── versions/                   # DB migration history
├── tests/                          # Backend test suites (api/services/core/security/modules)
├── scripts/                        # Backend-specific scripts and SQL utilities
├── seed/                           # Seed helpers/data
├── public/                         # Backend-served static artifacts
├── uploads/                        # Runtime upload storage (tenant/user/document assets)
├── Dockerfile                      # Backend container image
├── requirements.txt                # Backend dependencies
└── .env.example                    # Backend environment template
```

### 2.1 Key Backend Domain Groups (by code organization)

- Recruitment: `api/v1/leads`, `api/v1/candidates`, `api/v1/vacancies`, `modules/leads/*`
- Companies/Access: `modules/companies/*`, `api/v1/companies*`, `api/v1/admin/companies_access.py`
- Documents: `modules/documents/*`, `api/v1/documents.py`, `api/v1/document_policies.py`, `api/v1/document_merge/*`
- Communications: `api/v1/communications/*`, related services in `services/communications_*`
- HR/Workforce: `api/v1/workforce/*`, `api/v1/hr_*`, `models/workforce_*`
- Automations/Tasks: `api/v1/automation_*`, `api/v1/reminders_v2.py`, `services/automation_*`, `services/reminder_*`
- Billing/Plans: `api/v1/settings/billing/*`, `models/tenant.py`, `models/stripe_webhook_event.py`
- Integrations: Meta/email/messenger/calendar modules under `api/v1/settings/*`, `api/v1/communications/*`, `services/*integration*`

## 3) Frontend Map (`/opt/HostFlow/hostflow-frontend`)

```text
hostflow-frontend/
├── src/
│   ├── main.tsx                    # SPA bootstrap, providers, observability init
│   ├── App.tsx / AppShell.tsx      # Main shell
│   ├── app/                        # Route config, nav model, generated CRM paths
│   ├── pages/                      # App pages (dashboard/candidates/leads/hr/admin/public/etc.)
│   ├── api/                        # HTTP client and domain API adapters
│   ├── components/                 # Reusable UI components
│   ├── hooks/                      # Feature hooks
│   ├── modules/                    # Domain-focused frontend modules
│   ├── nav/                        # Navigation policy/mappings
│   ├── store/                      # Auth + app contexts
│   ├── contexts/                   # Additional React contexts
│   ├── i18n/                       # Localization layer
│   ├── utils/                      # Utility functions
│   ├── styles/                     # CSS layers
│   └── data/                       # Frontend static data lists
├── public/                         # Static assets, legal pages, sitemap, landing assets
├── scripts/                        # Frontend QA/codegen/static checks
├── dist/                           # Built frontend output
├── package.json                    # Frontend dependencies/scripts
├── vite.config.ts                  # Vite config
├── vitest.config.ts                # Unit test config
└── tailwind.config.cjs             # Tailwind config
```

## 4) Documentation Map (`/opt/HostFlow/docs`)

```text
docs/
├── SSOT.md                         # Operational backlog + source-of-truth process rules
├── HOSTFLOW_AUDIT_AND_PLAN.md      # Architecture/state audit document
├── pipe.md / pipedesign.md         # Product and UX blueprint docs
├── adr/                            # Architecture decision records
├── specs/                          # Technical specs (api/db/frontend/integrations/workflows)
├── security/                       # Security and threat-model docs
├── legal/                          # Legal/business docs
├── hr/ / recruitment/ / fleet/     # Domain-specific documentation
└── FRONTEND_DEPLOY.md              # Frontend deployment instructions
```

## 5) Runtime and Deployment Assets

- `docker-compose.yml`: local platform runtime (db, redis, backend, caddy, optional arq-worker, optional minio).
- `deploy/caddy.Dockerfile` + `Caddyfile`: reverse proxy and static distribution.
- `backend/.env.example`, `hostflow-frontend/.env.example`: environment templates.

## 6) Data/Operational Artifacts

- `backups/`: database dumps (contains sensitive business data).
- `backend/uploads/`: tenant document/media storage (sensitive operational files).
- `exports/`: extracted CSV/data exports.

## 7) Tests and Quality Gates

- Backend tests: `backend/tests/`
- E2E tests: root `e2e/`
- Frontend unit tests: under `hostflow-frontend/src/**/__tests__` + `vitest`
- Static QA scripts: `hostflow-frontend/scripts/` and root/backend `scripts/security/*`

## 8) Exclusions / Non-core in Asset Review

These directories exist but are generally not counted as core IP logic:
- `.git/`, `.venv*`, `node_modules/`, `.pytest_cache/`, `.ruff_cache/`, build outputs (`dist/`)
- `opencv_contrib/` (third-party source, not HostFlow proprietary core)

## 9) Minimal Asset Transfer Narrative (template)

Use this as a concise opening description of what is being transferred:

1. Multi-tenant recruitment + operations platform with backend (`backend/app`) and frontend (`hostflow-frontend/src`).
2. Domain IP in workflows for leads, candidates, vacancies, communications, documents, handoff, and HR/workforce.
3. Data model and migrations in `backend/app/models` and `backend/alembic/versions`.
4. Operational/architecture documentation in `docs/` with SSOT and ADR/spec structure.
5. Deployment/runtime stack via Docker Compose + Caddy + Postgres + Redis (+ optional ARQ/MinIO).
