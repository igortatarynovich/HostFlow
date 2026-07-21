# ADR-023: Module Surface Separation (Stage 1) and Full Module Independence Checklist

**Status:** Accepted  
**Date:** 2026-07-17  
**Amended:** 2026-07-17 (ownership correction: Employee → HR; Invoice/Payment → Finance)  
**Layer of change:** Domain | Product surface | Navigation | Settings | Roadmap gate  
**Authors:** Product + Platform architecture  
**Related:** [ui-constitution-v1.md](ui-constitution-v1.md), [ADR-004](ADR-004-five-product-modules-and-billing-events.md), [ADR-020](ADR-020-sales-to-engagement-commercial-model.md) (commercial / client→cash path), [ADR-002](ADR-002-modular-recruitment-hr-boundary.md), [module-catalog-and-routing-map.md](module-catalog-and-routing-map.md)

> **Principle:** Recruitment and Sales are independent product modules. They must not be treated as two variants of one CRM / Lead process.  
> **Naming:** What shipped in the first pass is **Module Surface Separation (Stage 1)** — not full Module Separation. Full independence requires eight levels (§3), including Deployment and URL Boundaries (§3.7).

---

## 1. Context

Historically HostFlow used **Lead** as an umbrella for candidate intake and client intake. Application workspaces and API facades already diverge, but the agency sidebar mixed domains, Settings used a single **CRM Setup** hub, and product language leaked “Lead = everything”.

Product goals (approved):

| | Recruitment | Sales / Commercial |
|--|-------------|--------------------|
| Goal | Candidate → qualification → documents → employment handoff | Inquiry → Client → Order → Invoice → Payment |
| Primary object | Candidate / Application | Inquiry / ClientAccount |
| After success | Handoff → **Employee (HR owns)** | Initiates billing → **Invoice/Payment (Finance owns)** |

**Same pattern:** Recruitment initiates Employee handoff but does not own Employee Workspace. Sales initiates Invoice but does not own invoice model, statuses, or financial rules.

---

## 2. Decision — Stage 1 (done / correcting)

### 2.1 What Stage 1 means

Stage 1 separates the **product surface**:

- separate nav sections (no mixed Pipeline / CRM / Leads bucket);
- separate operational routes and names;
- separate Recruitment Setup vs Sales Setup entry points;
- Communications, Documents, Forms, Activity remain **shared platform** (not copied);
- integrity test forbids Recruitment ∩ Sales rail overlap.

Stage 1 does **not** claim independent domain APIs, permissions, intake intents, or module-owned automations/analytics.

### 2.2 Domain ownership (canonical — even when nav is transitional)

| Object | Owner module | Notes |
|--------|--------------|-------|
| Recruitment Application | **Recruitment** | UI: Отклик |
| Candidate | **Recruitment** | |
| Vacancy / Search | **Recruitment** | |
| Inquiry | **Sales** | UI: Обращение |
| ClientAccount | **Sales** | |
| Contact (commercial) | **Sales** | |
| Opportunity / Deal | **Sales** | when introduced |
| Service Catalog | **Services** (or Commercial catalog facet) | not Recruitment |
| Service Order | **Services** | Sales may initiate; Services owns lifecycle |
| Employee | **HR / Workforce** | Recruitment may link after handoff only |
| Invoice | **Finance** | Sales may show in Client Workspace; Finance owns model/rules |
| Payment / Receivable | **Finance** | |

**Forbidden ownership leaks:**

- Recruitment must not own Employee Workspace.
- Sales must not define Invoice/Payment statuses, numbering, taxes, KSeF, or receivables rules.

### 2.3 Canonical agency navigation (Stage 1 corrected)

```text
Dashboard
Work
Communications
    Inbox                         ← platform horizontal
Recruitment
    Searches (Подборы)
    Applications (Отклики)
    Candidates
HR / Workforce
    Employees                     ← not under Recruitment
Sales
    Inquiries
    Clients
Services
    Orders
    Catalog (Services)
Finance
    Invoices                      ← not owned by Sales
Documents                         ← Document Hub (platform)
Automations                       ← platform engine
Integrations
Organization
Settings
Personal
```

Client Workspace may **surface** invoices/payments as related context; Finance remains SoT.

Recruitment may show handoff result + link to Employee; HR remains SoT.

### 2.4 Settings (Stage 1 vs target)

| Area | Stage 1 | Target ownership |
|------|---------|------------------|
| Recruitment Setup | pipeline, gates, handoff, candidate profiles, candidate doc requirements | Recruitment |
| Sales Setup | inquiry forms, commercial templates | Sales (+ later opportunity stages) |
| Finance Setup | *(not yet a first-class chrome tab)* | numbering, taxes, payment terms, KSeF, receivables |
| Services Setup | *(via company module settings)* | catalog, SLA, fulfilment |

**Do not** park invoice/tax/KSeF under Sales Setup.

### 2.5 Shared platform (allowed reuse)

Identity, Companies, Entity Workspace framework, Communications, Documents, Forms, Tasks/Queues, Notifications, Automations **engine**, Integrations, Search, Audit/Activity, Settings **framework**, Analytics **framework**, AI.

Shared **engines**; module-owned **definitions** (pipelines, metrics, templates, gates).

---

## 3. Full Module Separation — eight levels

| # | Level | Stage 1 / 2A | Full separation requires |
|---|-------|--------------|---------------------------|
| 1 | Product surface | Partially done | Stable nav/routes/names; no Leads/Pipeline umbrella |
| 2 | Domain ownership | Documented + SSOT | Code + specs enforce owner per entity (§2.2) |
| 3 | API contracts | Facades started | No operational `/leads` for both; modular product APIs |
| 4 | Permissions & module gates | **Stage 2B DONE** (HTTP gates) | Fine-grained `recruitment.*` action strings beyond read/write matrix (incremental) |
| 5 | Intake routing | Still Lead-centric | Intent before object: `candidate_application` → Recruitment; `sales_inquiry` → Sales — design SoT: [`intake-canonical-input-matrix.md`](intake-canonical-input-matrix.md) (**ACCEPTED / FROZEN**); runtime: [`intake-runtime-split-v1.md`](../tasks/intake-runtime-split-v1.md) |
| 6 | Workspaces & comms context | Workspaces exist | Distinct workspaces; Thread links entities, does not decide module |
| 7 | Settings / automations / analytics | Split tabs only | Module-owned process & metric definitions on shared engines |
| 8 | **Deployment and URL Boundaries** | **6A+6B+6C DONE**; production cutover open | Production DNS/TLS/proxy cutover closes full Stage 6 (§3.7) |

### 3.1 Definition of Done — full Module Separation

1. Employee finally lives under HR (nav + workspace + permissions).
2. Invoice and Payment belong to Finance (API, settings, rules) — Sales only initiates/views.
3. Recruitment and Sales have independent operational API contracts.
4. Separate permissions and HTTP module gates exist and are enforced.
5. Intake stops creating universal Lead as the product entity (Lead may remain internal transport).
6. Settings, Automations, Search, Analytics respect module ownership.
7. Shared code remains infrastructure only — not shared business meaning.
8. Each of the five business modules is reachable on its own subdomain; the apex host is the shell / platform entry (§3.7).

### 3.2 Delivery order (mandatory)

| Stage | Name | Goal | Must not do yet |
|-------|------|------|-----------------|
| **1** | Module Surface Separation | Nav / routes / settings labels | Claim full independence |
| **2A** | Domain Ownership + API Boundaries | Owner per entity; modular operational API | Permissions redesign |
| **2B** | Permissions + Module Gates | `recruitment.*` / `sales.*` / … + HTTP gates | Cash Loop |
| **3** | Universal Acquisition and Intake Routing | [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) slices **3A→3E**; V1 = Campaign+Goal Type+Primary KPI+Flight(1)→…→attribution; **Template** after V1 | Marketing 6th product; Template/multi-Flight in 3A; Goal flat enum; Goal=`route_intent`; Campaign owns Candidate/Inquiry |
| **4** | Workspace boundaries | Cross-workspace deep-link policy | — |
| **5** | Module-owned Settings / Automations / Analytics | Definitions owned by modules | — |
| **6A** | Module Host Runtime | Hostname routing, module-aware nav, cross-module redirect, module landing, unified SPA serve | Call Stage 6 “done”; treat `#hf_auth=` as production contract |
| **6B** | Shared cookie session | `Domain=.hostflow.cc` Secure + HttpOnly + SameSite; **delete `#hf_auth=` inside 6B** | Leave hash handoff alive after cookies ship |
| **6C** | Canonical deep-link resolver | Entity → owning host for UI, email, Inbox, Notifications | Hostname swap of current path |
| **Cash Loop** | Finance cash path | Only after 2A+2B; deployable on `finance.*` | Building Finance inside Sales |

**Why 2A before 2B:** permissions must attach to stable API ownership. Gates on unstable surfaces recreate the Lead umbrella under new names.

**After 6A:** 6B (shared cookie + delete `#hf_auth=`) → 2B gates → 6C deep-link wiring → production subdomain cutover. DNS/TLS may be prepared earlier.

### 3.3 Stage 2A — Domain Ownership and API Boundaries

**Task title:** *Module Separation Stage 2A: закрепить domain ownership и создать модульные API surfaces для Sales, HR, Services и Finance без изменения текущей бизнес-логики.*

| Object | Owner | Target API surface |
|--------|-------|-------------------|
| Candidate | Recruitment | `/api/v1/recruitment/candidates/*` |
| Recruitment Application | Recruitment | `/api/v1/recruitment/applications/*` |
| Employee | HR | `/api/v1/hr/employees/*` |
| Inquiry | Sales | `/api/v1/sales/inquiries/*` |
| Client Account | Sales | `/api/v1/sales/clients/*` |
| Service (catalog) | Services | `/api/v1/services/catalog/*` |
| Service Order | Services | `/api/v1/services/orders/*` |
| Invoice | Finance | `/api/v1/finance/invoices/*` |
| Payment | Finance | `/api/v1/finance/payments/*` (+ nested under invoices) |

**Key rule:** the owner module defines create/update, statuses, transitions, validation. Other modules get links, projections, or **allowed commands** only (e.g. Sales may request invoice creation; Sales must not set Invoice → `paid`).

**Allowed transitional pattern:**

- keep legacy tables/models;
- modular API becomes the **operational** surface;
- legacy paths stay mounted as deprecated/compat;
- no second entity tables “for modularity”;
- no folder moves pretending to be boundaries — contract first, then physical reorg.

### 3.4 Stage 2B — Permissions and Module Gates (after 2A) — DONE

Unified backend gate: `backend/app/auth/module_gate.py` + path ownership `backend/app/modules/http_module_ownership.py`.

**Check order (hostname is never authorization):**

1. owning module for the endpoint (path registry / explicit `require_module_gate(module)`);
2. tenant module entitlement (`tenant.settings.modules` snapshot — SSOT for product toggles);
3. company module enablement (when `company_id` / `X-Company-Id` present);
4. user ↔ company access (when company context present);
5. user module access (role matrix / user overrides);
6. action permission (`read` vs `write` from HTTP method / matrix editable);
7. object scope — remains on entity ACL helpers (candidates/employees/…); gate does not replace object ownership.

**Modules gated:** `recruitment`, `hr`, `sales`, `services`, `fleet`, `finance` — product + legacy mounts share the same dependency.

**Not security:** FE nav hide; request `Host` header / module subdomain.

**Runtime:** Bearer and cookie auth resolve the same `UserCtx` → same gate result.

### 3.5 Definition of Done — Stage 2 (2A + 2B)

Stage 2 is closed only when:

1. each key entity has one canonical owner;
2. operational UI does not use `/leads` or other shared legacy operational endpoints;
3. Invoice via Finance API; Client Account via Sales API; Employee via HR API; Service Order via Services API;
4. each module has a backend gate;
5. user without module gets 403/404 per policy;
6. nav/frontend routes derive from the same module capabilities;
7. integrity tests cover cross-module imports and route ownership;
8. tests cover denied access when license off / permission missing.

### 3.6 Cash Loop gate

**Cash Loop must not start before Stage 2A + 2B** (Finance API ownership + permissions/module gates).

Otherwise Finance will be rebuilt as an internal facet of Sales and the next architectural boundary will be violated immediately.

Cash Loop UI/API, when built, lives under the **Finance** deployment boundary (`finance.hostflow.cc` / Finance product API) — not under Sales.

### 3.7 Deployment and URL Boundaries (level 8)

Independent business modules are deployed and addressed as **separate URL authorities**. Path prefixes alone (`/app/sales`, `/app/recruitment`) are not the end state.

#### Canonical hosts (production)

| Host | Role |
|------|------|
| `hostflow.cc` | **Platform shell** — entry, auth handoff, tenant/company switcher, cross-module launcher, shared platform surfaces (Communications hub entry, Settings framework entry, Marketplace) |
| `recruitment.hostflow.cc` | **Recruitment** — Applications, Candidates, Vacancies/Searches, recruitment settings/analytics |
| `hr.hostflow.cc` | **HR / Workforce** — Employees, HR processes, employee docs, absences, termination, HR analytics |
| `sales.hostflow.cc` | **Sales / Commercial** — Inquiries, ClientAccounts, Contacts, Opportunities/Deals, commercial follow-up; Services catalog/orders UI when licensed may be entered from here but **does not become a sixth deployable business host** |
| `fleet.hostflow.cc` | **Fleet** — vehicles, assignments, operational fleet docs/events |
| `finance.hostflow.cc` | **Finance** — Invoices, Payments, receivables, taxes/KSeF, finance settings/analytics |

**Exactly five independent business-module hosts** + one shell:

```text
hostflow.cc                 → Platform shell
├── recruitment.hostflow.cc → Recruitment
├── hr.hostflow.cc          → HR / Workforce
├── sales.hostflow.cc       → Sales / Commercial
├── fleet.hostflow.cc       → Fleet
└── finance.hostflow.cc     → Finance
```

#### Relationship to ADR-004 license keys

ADR-004 licenses: `recruitment` \| `hr` \| `fleet` \| `services` \| `finance`.

Deployment hosts map as:

| Deploy host | Primary license key(s) | Notes |
|-------------|------------------------|-------|
| `recruitment.*` | `recruitment` (+ triad) | |
| `hr.*` | `hr` | |
| `sales.*` | commercial Sales surface; `services` when catalog/orders enabled | **No** `services.hostflow.cc` — Services is not a sixth business subdomain |
| `fleet.*` | `fleet` | |
| `finance.*` | `finance` | |

Shared platform capabilities (Communications, Documents, Forms, Automations engine, Identity) stay on the shell and/or embed via contracts — they are **not** given their own business-module subdomain.

#### Rules

1. A module host must not serve another module’s primary workspace as its home (e.g. `recruitment.*` must not be the home of Sales Inquiry or Employee).
2. Cross-module navigation uses **explicit handoff URLs** (shell launcher or deep link to the owning host), not silent in-app route swaps that hide ownership.
3. Cookies / auth: **Stage 6B** shared parent-domain session (`Domain=.hostflow.cc`, Secure, HttpOnly access/refresh, SameSite=Lax, double-submit CSRF). `#hf_auth=` hash handoff is removed.
4. API may remain on a shared API host (`api.hostflow.cc` or shell-relative `/api/v1`) with **module path prefixes**; URL boundary for humans is the module SPA host. Splitting API hosts per module is optional later and not required for Stage 6 DoD.
5. Staging/dev mirrors the same shape (`recruitment.<env>.…`, etc.) or path-based emulation only as a temporary local shortcut — production canon is subdomains.

#### Stage 6 split (do not call Stage 6 “done” after 6A alone)

| Sub-stage | Name | Status |
|-----------|------|--------|
| **6A** | Module Host Runtime | **DONE** — hostname → module, module-aware nav, cross-module redirect, module landing, single SPA dist on all hosts |
| **6B** | Shared cookie session on `.hostflow.cc` | **DONE** — `hf_access` / `hf_refresh` / `hf_csrf`; login / refresh / logout; CORS allowlist; CSRF; `#hf_auth=` removed from runtime |
| **6C** | Canonical entity deep-link resolver | **DONE** — `buildEntityDeepLink` / `resolve_entity_deep_link` for Inbox, Notifications, Search, Activity, Tasks, email; matrix + integrity tests |

**Full Stage 6** closes only when: shared cookie session works across shell + five module hosts (**6B done**); deep links resolve by entity ownership (**6C**); backend module gates (Stage **2B**) deny unauthorized module access (nav filter alone is UX, not a gate).

#### Stage 6A Definition of Done (Module Host Runtime) — met

- Hostname routing for shell + five business hosts.
- Module-aware navigation filter + launcher links from shell.
- Cross-module / shell→module path redirect to owning host (preserve query; strip auth fragment).
- Module landing paths per host.
- Unified production SPA serve (Caddy/nginx same dist).
- **Single host registry:** `shared/module_deploy_hosts.json` (SPA, backend, redirect allowlist, deep-link catalog, proxy host list).
- Strict `next` allowlist: only registry hosts; reject external, protocol-relative, exotic ports, nested evil absolute URLs in query.
- Integrity tests for route↔host uniqueness and open-redirect guard.

**Not Stage 6A / not security:** nav hide ≠ module gate. Shell must not accumulate business `/app/...` workspaces — business paths on `hostflow.cc` redirect to the owning module host.

**Runtime pointers:** `shared/module_deploy_hosts.json` → `platform/deployHosts.ts` + `backend/app/constants/module_deploy_hosts.py`. Local: `VITE_MODULE_HOST` / `?hf_module=`.

#### Stage 6B Definition of Done (shared cookie session) — met

- Session cookies on parent domain `.hostflow.cc` (host-only on localhost): `hf_access` (HttpOnly), `hf_refresh` (HttpOnly), `hf_csrf` (readable).
- Login / refresh / logout endpoints maintain and clear the shared session.
- Auth deps + whoami accept access cookie (Bearer remains for API clients / e2e).
- CORS origins include shell + five module hosts; credentials enabled.
- Double-submit CSRF for mutating requests when CSRF cookie is present.
- Cross-host login uses `?next=` only — **no** `#hf_auth=` token handoff.
- Regression tests cover cookies, cookie whoami, refresh, logout revoke, CSRF, Bearer-without-cookies.

#### Follow-up order (after 6B + 2B + 6C)

1. Production cutover — DNS, wildcard TLS, proxy reload, smoke tests, legacy URL redirects.
2. **Stage 3** ([`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)), slices in order:
   - **3A** ✅ **DONE** — Campaign + Goal Type + Primary KPI + Target + reserved CampaignRun (Flight; V1 = one); Template canon only (implement later)  
   - **3B** ✅ **DONE** — Form + Intake Source binding (uses, not owns)
   - **3C** ✅ **DONE** — universal submission routing
   - **3D** outcome attribution + basic analytics ← next
   - **3E** timeline + automation events

V1 = vertical chain through 3A–3E (minimal; single Flight); Audience/Assets/full Budget/multi-Flight later. Not a Marketing product module.

**Do not** cut production traffic to all subdomains until 6B is live (done) and `next` validation is verified in the target environment.

#### Stage 6C Definition of Done (entity deep links) — met

- Shared surfaces resolve entity → owning host via registry (`shared/module_deploy_hosts.json` → FE `entityDeepLinks.ts` / BE `entity_deep_links.py`).
- Wired: Inbox context links, Notifications, Global Search, Activity/Tasks, email digests; `spa_*` entity helpers delegate to the resolver.
- No shell business fallback for unknown/deleted entity types; query allowlist only.
- **Service Order → Sales host**; Services is not a sixth licensed/product module (HTTP gates use `sales` entitlement).
- Matrix + integrity tests: entity type → host/path; catalog hosts ⊆ five product modules.
- Permission/module gate (Stage 2B) still applies after navigation — hostname is routing only.

---

## 4. Target API surface (Stage 2A)

| Module | Product API (operational) | Legacy compat (deprecated for ops UI) |
|--------|---------------------------|----------------------------------------|
| Recruitment | `/api/v1/recruitment/applications`, `/recruitment/candidates` | `/api/v1/candidates` |
| Sales | `/api/v1/sales/inquiries`, `/sales/clients` | `/api/v1/client-accounts` |
| Services | `/api/v1/services/catalog`, `/services/orders` | `/api/v1/services`, `/service-orders` |
| Finance | `/api/v1/finance/invoices`, `/finance/payments` | `/api/v1/invoices` |
| HR | `/api/v1/hr/employees` (+ HR inbox under `/hr/*`) | `/api/v1/workforce/*` |

`/api/v1/leads` = admin/ingest/transport only — not an operational product contract for both businesses.

Internal table reuse is temporarily allowed. A shared **external** contract is not. Code SSOT for ownership: `backend/app/modules/domain_ownership.py`.

---

## 5. Consequences

- Stage 1 rail: Recruitment / HR / Sales / Services / Finance are separate sections.
- Stage 2A adds modular API surfaces without business-logic rewrite.
- Stage 2B (permissions) follows only after 2A.
- Stage **6A** connects Module Host Runtime; **6B** shared cookie session (hash handoff removed); **2B** HTTP module gates enforce entitlements without trusting hostname.
- Stage **6C** entity deep-link wiring is **DONE**; production cutover remains open for full Stage 6.
- After cutover: **Stage 3A→3E** Universal Acquisition ([`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)) — **3A+3B+3C DONE**; continue **3D→3E** vertical V1 chain (single Flight); not full Campaign Manager / multi-Flight in one shot.
- Docs name Stage 1 **Module Surface Separation**; full Module Separation requires the eight-level checklist (§3).
- Cash Loop is gated on Stage 2A+2B (§3.6) and ships under Finance URL boundary.

---

## 6. Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Call Stage 1 “full Module Separation” | Premature; ownership/API/permissions incomplete |
| Keep Employees under Recruitment | Violates ADR-002 / HR ownership after handoff |
| Keep Invoices under Sales as owner | Violates ADR-004 Finance boundary |
| Start Cash Loop inside Sales | Recreates Finance-as-Sales-facet |

---

## 7. Cross-references

- [ui-constitution-v1.md](ui-constitution-v1.md)
- [module-catalog-and-routing-map.md](module-catalog-and-routing-map.md)
- [`docs/recruitment/module-scope.md`](../../recruitment/module-scope.md)
- Sales product surface: this ADR + [ADR-020](ADR-020-sales-to-engagement-commercial-model.md) (no separate `docs/sales/module-scope.md`; cash path lives in Services + Finance scopes below)
- [`docs/services/module-scope.md`](../../services/module-scope.md)
- [`docs/finance/module-scope.md`](../../finance/module-scope.md)
- [`docs/hr/module-scope.md`](../../hr/module-scope.md)
- [`docs/acquisition/module-scope.md`](../../acquisition/module-scope.md)
- [ADR-002](ADR-002-modular-recruitment-hr-boundary.md)
- [ADR-024](ADR-024-acquisition-campaigns-intake-routing.md)
