# Intake Routing Foundation

**Status:** ACTIVE (foundation spec — PR-1)  
**Owner:** Product + Platform  
**Date:** 2026-06-05

**Supersedes direction (not deletes runtime yet):** [`intake-routes.md`](intake-routes.md) (Phase 0 Meta bridge)

**Related:**

- [`../architecture/intake-canonical-input-matrix.md`](../architecture/intake-canonical-input-matrix.md) — **Canonical Input Matrix ACCEPTED / FROZEN**; epic [`../tasks/intake-canonical-input-matrix.md`](../tasks/intake-canonical-input-matrix.md) **COMPLETE**; runtime [`../tasks/intake-runtime-split-v1.md`](../tasks/intake-runtime-split-v1.md) **READY**
- [`../architecture/ADR-007-forms-platform-capability.md`](../architecture/ADR-007-forms-platform-capability.md) — Forms as input layer; bindings attach forms to intake configs
- [`../platform/entity-profile-definition-registry.md`](../platform/entity-profile-definition-registry.md) — Entity Profile (field composition); Intake Source Config references profile, does not define semantics
- [`../workflows/lead-conversion-contract.md`](../workflows/lead-conversion-contract.md) — Lead → Candidate boundary; outcome rules must align
- [`lead-types.md`](../lead-types.md) — `Lead.lead_type` legacy; route intent replaces ad-hoc type branching
- [`../workflows/lead-intake-resolution-and-activity-continuity.md`](../workflows/lead-intake-resolution-and-activity-continuity.md) — operator triage after ingest
- [`../../SSOT.md`](../../SSOT.md) — SSOT updates when PR-2+ land

---

## 1. Goal

Establish a **provider-agnostic, reference-first** intake routing layer for HostFlow.

**Principle (foundation-first):**

> Canonical registries and rules first. Runtime ingest consumes them.

**Canonical chain:**

```
External signal
  → Provider Binding (adapter key)
  → Intake Source Profile (reference router)
  → Lead (universal intake entity)
  → Outcome Rules (when to create derivatives)
  → Candidate | Client | Service Order | Opportunity | nothing
```

**Not canonical:**

- Meta-specific tables as the source of truth for routing
- `business_type` as the primary ingest branch
- `lead_target_type` / `lead_type` as CRM business entities

---

## 2. Scope boundaries

### In scope

- Tenant-scoped **Intake Source Profile** registry
- **Provider bindings** (Meta form, website slug, public intake form, WhatsApp flow, …)
- **Route intent** reference vocabulary
- **Outcome rules** reference (ingest + lifecycle moments)
- **IntakeRouter** resolution service (single entry for all ingest paths)
- Migration from Phase 0 `meta_form_routes`
- Admin UI: **Settings → Intake Sources**

### Out of scope (this foundation)

- Full Forms platform (`FormTemplate` / `Submission` — ADR-007 long path)
- Opportunity / Deal CRM module (only hooks and outcome placeholders)
- Event bus / matching engine
- Replacing `Lead` as intake entity
- Per-field mapping (stays in provider adapters: Meta field mapping, Forms field mapping)

### Relationship to Forms (ADR-007) and Entity Profile

| Layer | Role |
|-------|------|
| **Field Registry** | Canonical field semantics (`qualified_code`) |
| **Entity Profile Definition** | Which fields belong to a business object type — see [`entity-profile-definition-registry.md`](../platform/entity-profile-definition-registry.md) |
| **Forms / Intake Source** | Presentation surface; asks a **subset** of Entity Profile fields |
| **Intake Routing** | Decides operating context + intent + pipeline |
| **Outcome Rules** | Decides derivative entities after Lead exists |

A public form submission handler calls `IntakeRouter.resolve(...)`, resolves **Entity Profile**, normalizes via Mapping, runs **Decision Layer**, creates **Lead**, then applies outcome rules.

**Terminology note:** `intake_source_profiles` (this spec) configures **routing** — not Entity Profile field composition. Prefer **Intake Source Config** in new docs to avoid collision with Entity Profile Definition Registry.

---

## 3. Canonical entities

### 3.1. Intake Source Profile

Tenant-scoped **reference record**. Answers: *what is this entry point and how do we work with it?*

**Table (target):** `intake_source_profiles`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | PK |
| `tenant_id` | UUID | RLS scope |
| `code` | string(64) | Stable slug, unique per tenant (`meta-b2b-carriers`) |
| `name` | string(255) | Operator-facing label |
| `provider` | enum | Primary provider family (see §4.1) |
| `channel` | enum | Acquisition channel (see §4.2) |
| `own_company_id` | UUID FK | Operating Company Profile (Topbar scope) |
| `route_intent` | enum | Intent of inbound contact (see §4.3) |
| `pipeline_preset` | string(64)? | Funnel preset key (`service_sales`, `lead_pipeline`, …) |
| `default_assignee_id` | UUID? FK users | Optional ingest assignee hint |
| `default_language` | string(8)? | ISO 639-1 hint for comms (`pl`, `en`, `ru`) |
| `is_active` | bool | Soft disable |
| `notes` | text? | Internal |
| `created_at`, `updated_at` | timestamptz | Audit |

**Example:**

```yaml
code: meta-b2b-carriers
name: Meta — «Найдём вам водителей»
provider: meta
channel: paid
own_company_id: <Work Host Services>
route_intent: sales_inquiry
pipeline_preset: service_sales
default_language: pl
is_active: true
```

**Invariants:**

- One profile may have **many** provider bindings
- Profile is **not** deleted when a binding is removed; bindings are adapters
- `own_company_id` must belong to `tenant_id` and not be archived

---

### 3.2. Intake Source Binding

**Adapter** from an external provider key to an Intake Source Profile.

**Table (target):** `intake_source_bindings`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | PK |
| `tenant_id` | UUID | RLS scope |
| `intake_source_profile_id` | UUID FK | Canonical router |
| `provider` | enum | Must match or refine profile provider |
| `external_key` | string(255) | Canonical key (see §3.3) |
| `external_key_secondary` | string(64)? | e.g. Meta `page_id` |
| `label` | string(255)? | Operator hint |
| `is_active` | bool | |
| `priority` | int | Higher wins on duplicate keys (default 0) |
| `created_at`, `updated_at` | timestamptz | |

**Unique constraint:** `(tenant_id, provider, external_key, external_key_secondary)`

**Examples:**

| provider | external_key | external_key_secondary | profile.code |
|----------|--------------|------------------------|--------------|
| `meta` | `form_id:123456789` | `page_id:987654` or `""` | `meta-b2b-carriers` |
| `meta` | `form_id:111222333` | `""` | `meta-driver-application` |
| `website` | `slug:find-drivers` | — | `web-b2b-carriers` |
| `public_intake` | `form_id:<uuid>` | — | `public-driver-form` |
| `whatsapp` | `flow_id:abc` | — | `wa-sales` |
| `telegram` | `bot_intake:driver` | — | `tg-driver-application` |
| `import` | `batch:csv-drivers` | — | `import-candidates` |
| `api` | `webhook:<secret_hash>` | — | `api-generic-inbound` |

---

### 3.3. External key format

Canonical string, provider-namespaced:

```
<form_id>:<value>
<slug>:<value>
<flow_id>:<value>
...
```

Meta ingest normalizes to `form_id:{id}`; public intake to `form_id:{tenant_lead_form.id}` or `slug:{public_slug}`.

**Resolution normalizes** provider payload → `(provider, external_key, external_key_secondary)` before lookup.

---

### 3.4. Lead (universal intake entity)

**Lead remains the only mandatory intake entity.**

On every successful ingest:

1. Create or update **Lead** (idempotent by `tenant_id + source + external_id`)
2. Stamp resolution metadata on `Lead.normalized` (denormalized cache):

```json
{
  "intake_routing_v1": {
    "profile_id": "uuid",
    "profile_code": "meta-b2b-carriers",
    "route_intent": "sales_inquiry",
    "provider": "meta",
    "binding_id": "uuid",
    "resolution": "exact_binding | tenant_default | fallback",
    "routing_status": "resolved | fallback | unknown"
  }
}
```

3. Optionally set `Lead.own_company_id`, `Lead.source`, funnel from profile

**Deprecated as primary router (keep as denormalized hints only during migration):**

- `Lead.lead_target_type` (Phase 0) → map to `route_intent` on read
- `Lead.lead_type` → derived from outcome / route_intent for UI compat

---

## 4. Reference enums

### 4.1. `provider`

| Value | Description |
|-------|-------------|
| `meta` | Meta / Facebook Lead Ads |
| `tiktok` | TikTok lead ads |
| `website` | Hosted / embedded site forms |
| `public_intake` | HostFlow `tenant_lead_forms` / `/public/intake` |
| `whatsapp` | WhatsApp flows |
| `telegram` | Telegram bot intake |
| `referral` | Referral program links |
| `import` | CSV / bulk import |
| `api` | Generic inbound webhook / REST |
| `manual` | Operator-created lead |
| `unknown` | Unclassified |

Stored as `String` in DB (not Postgres ENUM) for forward compatibility.

### 4.2. `channel`

| Value | Description |
|-------|-------------|
| `paid` | Paid ads |
| `organic` | Organic web / social |
| `referral` | Partner / employee referral |
| `direct` | Direct / offline |
| `internal` | Internal tool / import |
| `unknown` | |

### 4.3. `route_intent`

**Not a CRM entity.** Vocabulary for routing and outcome rules.

| Value | Meaning | Typical pipeline |
|-------|---------|------------------|
| `candidate_application` | Person seeking employment | Recruitment / Lead → Candidate |
| `sales_inquiry` | Company interested in service | Service Sales |
| `service_request` | Concrete service order intent | Service Sales → Service Order |
| `partner_inquiry` | Partnership / integration | Partner pipeline (future) |
| `unknown` | Could not classify | Review queue |

**Phase 0 mapping (`lead_target_type` → `route_intent`):**

| Phase 0 | Foundation |
|---------|------------|
| `candidate` | `candidate_application` |
| `client_lead` | `sales_inquiry` |
| `service_order_lead` | `service_request` |
| `partner_lead` | `partner_inquiry` |

### 4.4. `routing_status`

Stored on resolution result / Lead normalized block:

| Value | Meaning |
|-------|---------|
| `resolved` | Exact or tenant-default binding matched |
| `fallback` | Used tenant fallback profile (logged) |
| `unknown` | No profile; minimal safe path |

---

## 5. Route resolution

### 5.1. Service: `IntakeRouter`

**Module (target):** `backend/app/services/intake_router.py`

```python
async def resolve(
    db,
    *,
    tenant_id: str,
    provider: str,
    external_key: str,
    external_key_secondary: str | None = None,
    own_company_hint: str | None = None,
) -> IntakeRoutingResult:
    ...
```

**`IntakeRoutingResult` fields:**

- `profile: IntakeSourceProfile | None`
- `binding: IntakeSourceBinding | None`
- `route_intent: str`
- `own_company_id: str | None`
- `pipeline_preset: str | None`
- `default_assignee_id: str | None`
- `default_language: str | None`
- `routing_status: str`
- `resolution: str` — `exact_binding` | `tenant_default` | `fallback` | `unknown`

### 5.2. Resolution order

1. **Exact binding** — `(tenant_id, provider, external_key, secondary)` active binding → profile
2. **Secondary-relaxed** — same with `external_key_secondary=""` if Meta page-less match
3. **Tenant default profile** — `tenant.settings.intake_routing_v1.default_profile_id` (optional)
4. **Fallback policy** (§5.3) — log warning `intake_routing_fallback`
5. **Unknown** — `route_intent=unknown`, `routing_status=unknown`, Lead still created

**Never:** infer profile from first OwnCompany by `created_at`.

### 5.3. Fallback policy

When no binding matches:

| Condition | Fallback `route_intent` | Notes |
|-----------|-------------------------|-------|
| `provider=meta` and no `form_id` | `unknown` | Needs routing queue |
| Legacy: active OwnCompany `business_type=services` | `sales_inquiry` | Transitional until profiles seeded |
| Legacy: agency/employer | `candidate_application` | Transitional |
| Operator policy: strict mode (future) | reject ingest → `needs_routing` | Tenant flag |

Fallback is **explicitly logged** with structured fields: `tenant_id`, `provider`, `external_key`, `reason`.

### 5.4. Pipeline resolver

**Input:** `route_intent`, `own_company.business_type`, `industry`, `pipeline_preset` on profile

**Output:** `funnel_id` or preset key for Lead stage initialization

| route_intent | own_company.business_type | Preset |
|--------------|---------------------------|--------|
| `candidate_application` | agency | `lead_pipeline` / industry override |
| `candidate_application` | employer | employer hiring preset |
| `sales_inquiry` | services / agency | `service_sales` |
| `service_request` | services | `service_sales` |
| `unknown` | any | `lead_pipeline` + status `needs_routing` |

Single function; no scattered `business_type == "services"` in ingest.

---

## 6. Outcome rules

**Separate reference/rules layer.** Defines **when** to create derivative entities.

### 6.1. Moments

| Moment | Trigger |
|--------|---------|
| `on_ingest` | Lead row persisted, processing pipeline |
| `on_qualified` | Lead stage → `qualified` (or intake decision qualify) |
| `on_won` | Lead stage → `converted` / terminal win |
| `on_reject` | Lead rejected / lost |

### 6.2. Rules (reference table — target `intake_outcome_rules` or JSON policy v1)

| Moment | route_intent | Action | Forbidden |
|--------|--------------|--------|-----------|
| `on_ingest` | * | **Always** ensure Lead exists | — |
| `on_ingest` | `candidate_application` | **May** auto-create Candidate if processing mode = automatic + outcome allows | Skip if duplicate / fit gate |
| `on_ingest` | `sales_inquiry` | Lead only; **no** Candidate | Candidate creation |
| `on_ingest` | `service_request` | Lead only; optional Service Order draft (future) | Candidate creation |
| `on_ingest` | `partner_inquiry` | Lead only | Candidate creation |
| `on_ingest` | `unknown` | Lead + `needs_routing` or review queue | Auto Candidate |
| `on_qualified` | `sales_inquiry` | May create Service Order draft | — |
| `on_qualified` | `service_request` | May create Service Order | — |
| `on_won` | `sales_inquiry` | Create or link **Client** (Organization) | — |
| `on_won` | `service_request` | Finalize Service Order | — |
| `on_won` | `candidate_application` | Candidate already exists; handoff / employment flows | — |

**Critical invariant:**

> **Candidate is created only by an outcome rule for `candidate_application`, never by `business_type` alone.**

Aligns with [`lead-conversion-contract.md`](../workflows/lead-conversion-contract.md): webhook/form creates Lead; conversion use-case creates Candidate.

### 6.3. Phase 0 → Foundation outcome mapping

Current `_processing.py` branch on `is_sales_intake_target(lead_target_type)` becomes:

```python
routing = await IntakeRouter.resolve(...)
if OutcomeRules.allows(db, moment="on_ingest", action="create_candidate", route_intent=routing.route_intent):
    ... create_candidate_full ...
```

---

## 7. Provider consumers (adapters)

Each ingest path **only** adapts payload → `(provider, external_key)` then calls `IntakeRouter`.

| Consumer | Provider | External key source |
|----------|----------|-------------------|
| Meta webhook | `meta` | `form_id`, optional `page_id` |
| Generic inbound webhook | `api` | configured secret / path |
| Public intake submit | `public_intake` | `lead_form_id` or `slug` |
| CSV import | `import` | `batch:{import_job_id}` or profile-bound |
| Telegram intake | `telegram` | bot flow id |
| Manual lead create | `manual` | operator-selected profile |

**Meta field mapping** (`meta_lead_form_mappings`) remains Meta-adapter concern — not routing canon.

---

## 8. Migration from Phase 0 (`meta_form_routes`)

**Phase 0 artifacts (shipped 2026-06-05):**

- Table `meta_form_routes`
- Column `leads.lead_target_type`
- `backend/app/modules/leads/intake_route.py`
- Meta LeadHub UI block «Intake route»

**Migration script (PR-4):**

For each `meta_form_routes` row:

1. Create or upsert `intake_source_profiles`:
   - `code` = `meta-form-{form_id}` (or operator-defined merge)
   - Map `lead_target_type` → `route_intent` (§4.3)
   - Copy `own_company_id`, `pipeline_preset`, `default_assignee_id`, `is_active`
   - `provider=meta`, `channel=paid` (default; operator may edit)

2. Create `intake_source_bindings`:
   - `provider=meta`
   - `external_key=form_id:{form_id}`
   - `external_key_secondary=page_id:{page_id}` or empty

3. Dual-read period: `IntakeRouter` checks bindings first, falls back to `meta_form_routes` if no binding (one release)

4. Deprecate `meta_form_routes` table (mark deprecated in spec; drop in PR-N+2 after dual-read removed)

**Operational note:** WHI B2B ad — configure Phase 0 route **or** seed profile `meta-b2b-carriers` after PR-2.

---

## 9. API (target)

### Admin — Intake Sources

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/settings/intake/sources` | List profiles |
| POST | `/api/v1/settings/intake/sources` | Create profile |
| GET | `/api/v1/settings/intake/sources/{id}` | Detail + bindings |
| PATCH | `/api/v1/settings/intake/sources/{id}` | Update profile |
| GET | `/api/v1/settings/intake/bindings` | List bindings (filter provider) |
| POST | `/api/v1/settings/intake/bindings` | Create binding |
| PATCH | `/api/v1/settings/intake/bindings/{id}` | Update |
| POST | `/api/v1/settings/intake/resolve` | Test resolve (dry-run) |

### Meta consumer (thin wrapper)

| Method | Path | Description |
|--------|------|-------------|
| GET/PUT | `/api/v1/settings/leads/meta/forms/{form_id}/route` | **Deprecated** → writes binding + ensures profile |

---

## 10. UI (target — PR-6)

**Settings → Intake Sources**

- Profile list (code, name, route_intent, own company, active)
- Profile editor: all §3.1 fields
- Bindings tab per profile
- **Test route** — paste sample provider payload → shows resolved profile + outcome preview
- **Meta tab** — convenience editor for `provider=meta` bindings (same data as Intake Sources)

Meta LeadHub «Intake route» block becomes a **consumer view** of binding + profile (no separate canon).

---

## 11. PR plan

| PR | Deliverable | DoD |
|----|-------------|-----|
| **PR-1** | This spec | Reviewed; linked from SSOT; Phase 0 doc marked bridge |
| **PR-2** | Schema: `intake_source_profiles`, `intake_source_bindings`; reference enums in code; seed migration optional | Migration applies; RLS; CRUD repo |
| **PR-3** | `IntakeRouter.resolve()` + unit tests | All resolution order cases; fallback logging |
| **PR-4** | Meta ingest → IntakeRouter; migrate `meta_form_routes` data; dual-read | Meta B2B form resolves via binding; no new Candidates for `sales_inquiry` |
| **PR-5** | Outcome rules module; remove `business_type == services` ingest branch | Candidate only via `candidate_application` + rule |
| **PR-6** | Settings → Intake Sources UI; Meta tab as binding editor | Operator can configure WHI without SQL |

**Branch:** `feature/intake-routing-foundation`

---

## 12. Definition of Done (foundation complete)

- [ ] Every ingest path (Meta, public intake, CSV, generic webhook) calls **one** `IntakeRouter`
- [ ] No ingest path creates Candidate based on `tenant.business_type` alone
- [ ] Operator can configure WHI B2B ad via **Intake Source Profile + binding** without code deploy
- [ ] `meta_form_routes` dual-read removed; table deprecated
- [ ] Lead.normalized contains `intake_routing_v1` with `profile_code` and `route_intent`
- [ ] Fallback emits structured log / audit event
- [ ] Docs: SSOT, lead-conversion-contract cross-link updated
- [ ] Analytics can group by `profile_code` and `route_intent`

---

## 13. WHI operational path (until PR-4)

1. **Now:** Phase 0 Meta route — profile Services + `client_lead` / map to `sales_inquiry` after migration
2. **After PR-2:** Seed profile `meta-b2b-carriers` + binding for Meta `form_id`
3. **After PR-5:** Qualify → Client; won → Service Order via outcome rules

---

## 14. Open questions (defer to PR-2 review)

1. **Tenant default profile** — one per tenant or per `own_company_id`?
2. **Strict fallback mode** — block ingest vs `unknown` Lead?
3. **Outcome rules storage** — table vs `tenant.settings.intake_outcome_rules_v1` JSON for v1?
4. **Opportunity entity** — stub in outcome rules or defer to Commercial module?

---

## History

- 2026-06-05: PR-1 foundation spec. Phase 0 `meta_form_routes` documented as bridge.
