# Acquisition UI Cutover

**Status:** **ACTIVE — Product Track next** (blocks Stage 5 PR-2)  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) · [acquisition/module-scope.md](../../acquisition/module-scope.md)  
**Depends on:** Stage **4 runtime** DONE (#136 / #148–#151)  
**Parents:** [Stage 4 — Flight Runtime](acquisition-stage-4-flight-runtime.md) · [Stage 5 — Optimization](acquisition-stage-5-optimization.md) (paused)  
**Branch (planned):** `feat/acquisition-ui-cutover`  
**Trusted tip at open:** `integration/release-product-a-b` @ `0d87d377` (docs PR-2 boundaries)

> Stage 4 **runtime** is DONE. Stage 4 **product/UI cutover** is **NOT DONE**.  
> Production still looks “old” because navigation and legacy Подборы surfaces were never retired.  
> Technical entities (Campaign/Flight, IntakeSourceProfile, Meta OAuth, Forms builder, mapping_rules) exist but are **split across screens** — there is no single operator onboarding path.

---

## Diagnosis (locked 2026-07-23)

### What is already true in code

| Surface | Path | Role |
|---------|------|------|
| Marketing list / create / detail / connect source | `/app/marketing`, `/app/marketing/new`, `/app/marketing/:campaignId`, `/app/marketing/:campaignId/sources/new` | Canonical Campaign / Flight operator SPA |
| Sales workplace | `/app/sales` | Client / service sales — **not** Growth owner |
| Integrations (tenant access) | `/app/settings/integrations`, `…/meta` | Meta OAuth / Business / Pages / webhook health |
| Form Builder (Forms platform) | `/app/settings/lead-forms`, `…/:formId`, `…/:formId/builder` | Forms SoT (ADR-007); **not** embedded in Marketing setup |
| Legacy Подборы | `/app/recruitment/searches`, `…/new`, inbox | Still registered and nav-visible |
| Legacy launch-from-search | `…/searches/:id/acquisition/*` | Still uses **searchAcquisition** activity API — **not** platform Campaign/Flight |

Nav fact: Marketing is top-level after **C-1** (#157). Sales bucket no longer owns Marketing.

**Campaign create vs Connect Source (UI split):**  
`/app/marketing/new` creates Campaign only (`own_company_id` + Primary Target + optional `CampaignTarget(role=context)`). Sources bind later via `/app/marketing/:campaignId/sources/new` to the current Flight. Detail shows empty state / bindings list; CTA is gated so UI does not offer a second **primary** of the same endpoint type (multi-primary sources = later runtime PR). Not Form Builder and not full Source onboarding / mapping.

**Campaign Detail Source cards (PR2):** bindings render as business cards — Lead Form (Meta) / анкета HostFlow — with page/form labels, binding & publication status, last submission when available from activity/SoT compose. Technical IDs only under «Подробнее». Terminology: Source ≠ Connection ≠ Endpoint.

### What was missed when Stage 4 was closed

Runtime delivered: Campaign/Flight API, commands, monitor, activity, Marketing ops card, deploy/smoke.

**Not** delivered as product cutover:

1. Unified operator path for **external sources** (connect → inventory → test lead → mapping → destination → Flight)  
2. Source readiness / Mapping Health visible in Marketing  
3. Forms inside Marketing flow (`/app/marketing/forms…`) + create-form-in-setup  
4. Retire / freeze Подборы as an advertising launch surface (**only after** the new path is complete)  
5. Full production navigation acceptance  

### Data / dual-model note (do not overclaim)

There is **no completed cutover** that retired Search as the ad-launch object. Platform Campaign/Flight coexist with:

- Recruitment Searches UI  
- Legacy search-scoped acquisition activities (`search_acquisition_service` / `createAcquisitionActivity`)

Any “подбор → Campaign” mapping must be **audited and reconciled** in this epic — not assumed already done for all rows. Unresolved rows go to a migration reconciliation queue.

**Do not** mechanically equate Подбор = Flight:

| Object | Role after cutover |
|--------|--------------------|
| **Campaign** | Growth initiative / promotion goal |
| **Flight** | Concrete launch wave |
| **Vacancy / hiring need** | Destination / Recruitment process (Operations) |
| **Recruitment inbox** | Processing arrived candidates |
| **Sales** | Client leads, offers, service sales |

---

## Corrected status line

```text
Stage 4 runtime          = DONE
Stage 4 product/UI cutover = NOT DONE  ← this epic
Stage 5 PR-1             = DONE (read-only signals)
Stage 5 PR-2             = PAUSED until this cutover closes
```

---

## Target IA (after cutover)

### Marketing zones during C-3…C-7 (onboarding cutover)

| Zone | Owns |
|------|------|
| **Campaigns** | Campaigns, Flights, statuses, results, optimization signals |
| **Forms** | HostFlow Form Builder: create/edit/preview/publish, public URL, versions, destination, Campaign/Flight usage |
| **Sources** | External intake sources: Connection summary, Mapping workspace entry, Mapping Health, destination, Flight usage, last lead / last error (onboarding signals only — **not** a full ops console) |
| **Activity** | Campaign/Flight activity timeline |

Field mapping during cutover lives **under Sources** (per-source setup). It is not a fifth top-level nav item yet.

### Marketing zones after C-7 + Source Diagnostics epic

| Zone | Owns |
|------|------|
| **Campaigns** | unchanged |
| **Forms** | unchanged |
| **Sources** | Source inventory, readiness, mapping entry, health — **configuration**, not casework |
| **Activity** | unchanged |
| **Diagnostics** | **Separate** day-2 ops tool (not a tab inside Sources): per-submission timeline, raw/normalized payload, routing/duplicate decisions, mapping version, warnings, replay, export — provider-agnostic (Meta, later TikTok / LinkedIn / Google Ads / API / webhooks / CSV / …) |

**Why Diagnostics is top-level:** scales across providers without nesting ops under each Source type; avoids another large UI move later. Marketing becomes a full **acquisition management** module (setup + run + explain), not only Campaign/Flight screens — aligned with long-term HostFlow architecture (ADR-024 Growth surface), without inventing a `marketing.*` host module.

### Cross-section ownership

| Section | Owns |
|---------|------|
| **Marketing** | Campaigns, Forms, Sources, Activity; later **Diagnostics** |
| **Sales** | Client leads, offers, service sales |
| **Recruitment** | Candidates, vacancies/pipeline, inbox — **no** ad-launch “Подборы” object (after **C-7**) |
| **Settings → Integrations** | Tenant-level **access only**: OAuth, Meta Business, available Pages, ad accounts, webhook health, permissions, reconnect/disconnect |

**Settings answers “can we talk to the provider?”**  
**Marketing answers “how do we run ads, place inbound fields, and (later) diagnose intake?”**

---

## Locked product principles (Source onboarding and mapping)

This stream is a **mandatory** Product Track slice — **not** buried inside Form Builder.

### Two product lifecycles (do not mix)

Product Track for acquisition Sources splits into **two independent lifecycles**. Cutover owns only the first; Diagnostics owns the second.

| Lifecycle | User question | Flow | Goal |
|-----------|---------------|------|------|
| **1. Onboarding** (one-time setup) | «How do I connect a new source so it starts delivering leads?» | Connect → Source → Test Lead → Field Discovery → Mapping → Destination → Campaign / Flight → First Processed Lead | Bring the source to **Mapping Health = Ready** |
| **2. Operations** (daily work) | «Why did **this** lead process this way, and how do I fix it?» | Lead arrived → Processed → Problem? → Diagnostics → Replay / Fix → Continue | Explain a **specific** lead without re-running source setup |

These are different jobs, different mental models, and therefore **different UIs** — do not collapse them into one “Sources settings” screen.

C-3…C-5 implement **onboarding** surfaces only (inventory, sample discovery, mapping decisions, health summary).  
**Source Diagnostics** (post–C-7) implements **operations** — see [After cutover](#after-cutover--source-diagnostics-separate-product-epic).

### Three independent levels

| Level | Meaning | Home |
|-------|---------|------|
| **Connection** | Authorization and provider access (OAuth, Business, Pages, ad accounts, webhook, permissions) | Settings → Integrations |
| **Source** | Concrete Page / provider form / webhook endpoint used in operations | Marketing → Sources |
| **Mapping** | Where each field of **that** source goes in HostFlow | Marketing → Sources → … → Field mapping |

They must not be presented as one undifferentiated “Meta settings” screen.

### Value placement hierarchy

| Layer | What belongs here |
|-------|-------------------|
| **Person** | Stable person data used across processes: name, phone, email, language, city/address when global |
| **Candidate** | Stable recruitment profile: licence categories, experience, work permit, qualifications, preferences |
| **Application / Sales inquiry** | Response-scoped answers: chosen vacancy/service, schedule, start date, salary expectations, campaign-specific Q&A; for B2B — company, need, headcount, budget, timeline |
| **Raw submission** | Always retains the provider payload without loss (proof of what was sent) |

**Rule:** do **not** turn every Meta question into a Candidate column. Most ad questions stay as submission / application answers (or form response snapshot). Candidate receives only durable person/profile attributes needed in many processes.

For each provider field the operator may choose only:

1. **Standard field** (e.g. phone, email, name, language)  
2. **Domain field** (e.g. vacancy, driving licence, experience)  
3. **Custom field** (managed custom field on the owning entity)  
4. **Keep as form answer** (submission/application answers, no new system field)  
5. **Ignore** — only explicitly, with a warning  

### Mapping Health (per Source)

Every Source must surface health so Meta form drift is visible and data is not silently dropped:

| Status | Meaning |
|--------|---------|
| **Ready** | All known provider fields decided; required targets satisfied |
| **Needs review** | New provider fields appeared (or sample changed) since last confirmed mapping |
| **Broken** | Mapping cannot run (missing required decisions, invalid targets, or ingest failures) |

Example surface:

```text
Source: Meta / Kierowca CE
Mapping: ✓ 18 mapped · ⚠ 2 new fields · ✗ 0 required missing
Status: Needs review
```

### Reuse (no new mapping engine)

Product UI must reuse existing mechanisms where possible:

- `IntakeSourceProfile.mapping_rules`  
- Existing Meta admin field-mapping UI / APIs  
- Existing mapping preview / test-ingest paths  

C-3…C-5 deliver **operator surface + readiness + discovery + health** in Marketing — not a parallel mapping runtime.

### Acceptance path (cutover readiness criterion)

A non-developer operator must complete:

```text
Connect Meta
  → Select Page / Lead Form
  → Receive Test Lead
  → Configure Mapping (with Routing preview)
  → Choose Destination (Vacancy / Service / Sales)
  → Launch Flight
  → Receive First Processed Lead
```

Test-lead modes (product intent for **C-4**):

| Mode | Role |
|------|------|
| **A — Official Meta test lead** | Primary: instruction or available Meta test workflow → capture raw payload → propose mapping → dry-run normalize/route; **no** production funnel entity unless explicitly opted in |
| **B — Capture next real lead as sample** | Next submission processes normally **and** seeds mapping sample (PII masked in UI where feasible) |
| **C — Paste saved payload** | Admin diagnostics only — not the default path |

Routing preview after mapping must show concrete outcome (entity type, vacancy/service, company, Campaign/Flight, Person vs Candidate vs answers vs ignored, duplicate phone/email behavior, assignee/queue) — not a bare “saved”.

---

## PR sequence (locked 2026-07-23)

| PR | Scope | Status |
|----|--------|--------|
| **C-1** | Nav: Marketing top-level section; remove from Sales bucket; Activity under Marketing | **DONE** — #157 |
| **C-2** | Stop legacy ad-launch from Подборы (`searchAcquisition`); reconcile to Campaign/Flight; block new dual-write debt | **DONE** — #158 (merge exception: scoped C-2 + qa-static green; full backend-ci baseline → Engineering [#159](https://github.com/igortatarynovich/HostFlow/issues/159)) |
| **C-3** | **Sources foundation** — unified Sources list; connection status; Meta Page/Form inventory; webhook health; last submission; links to current provider bindings; Mapping Health summary (**Ready / Needs review / Broken**). No new mapping engine | **DONE** — #160 |
| **C-4** | **Test submission & field discovery** — Meta test lead and/or capture-next; raw payload inspector; detected fields + sample values; masking; replay normalization **without** creating production entities by default | After C-3 |
| **C-5** | **Mapping workspace** — provider field → standard / domain / custom / answer / ignore; validation; versioning; unmapped-field alerts; routing preview; Mapping Health updates | After C-4 |
| **C-6** | **Form Builder cutover** — Forms under Marketing (`/app/marketing/forms`…); create/edit/preview/publish; create-form-in-setup; integrate with Campaign Setup | After C-5 |
| **C-7** | **Recruitment Searches decommission + navigation acceptance** — retire Подборы ad-launch UI (redirect/read-only); unresolved → reconciliation queue; production nav + smoke; close Stage 4 product cutover gate | After C-6 |

**Ordering rationale**

1. **C-2 first** — stop growing dual-path launch debt.  
2. **C-3 → C-5** — Source onboarding and mapping before Form Builder embedding, so operators can discover real provider fields and place them.  
3. **C-6** — HostFlow Forms join the same Marketing IA once Sources/mapping work.  
4. **C-7 last** — do **not** remove Подборы UI until the full cycle works:

```text
Connect → Source → Test Lead → Mapping → Form → Campaign → Flight → Lead
```

Early decommission would leave a scenario gap for users who still use legacy surfaces to understand inbound field structure.

### C-2 locked scope

1. Forbid creating new launches via `searchAcquisition` (POST activities/channels + `duplicate` action).  
2. Inventory all legacy launch call sites (frontend + backend) — enforced by scan tests.  
3. Unambiguous Подбор/vacancy → Marketing setup prefilled (`Campaign → Flight` with `target_type=vacancy`).  
4. Ambiguous / historical activities → `reconciliation` state on acquisition snapshot (`linked` \| `unresolved`).  
5. Подборы acquisition UI stays temporarily as **read-only / legacy** (view + sync + pause/resume/archive of existing rows only).  
6. Where a Campaign is already linked by vacancy target — surface link/redirect to that Campaign.  
7. Do **not** delete legacy JSON/activity data until reconciliation complete.  
8. Do **not** touch Form Builder, Sources IA, or Mapping workspace in C-2.  
9. Do **not** decommission Подборы list/nav in C-2 — that is **C-7** only.

**C-2 acceptance:** after merge, no user action may create a new acquisition launch outside Campaign/Flight.

### C-2 call-site inventory (enforced by scan tests)

| Surface | Path | C-2 behavior |
|---------|------|----------------|
| API create | `POST …/vacancies/{id}/acquisition/activities\|channels` | **410** `legacy_launch_disabled` + `marketing_setup_path` |
| API duplicate | `POST …/activities/{id}/actions` `action=duplicate` | **410** same |
| FE helper | `createAcquisitionActivity` / `createAcquisitionChannel` | throws client-side; no HTTP |
| Launch page | `…/searches/:id/acquisition/new` | redirect → `/app/marketing/new?target_type=vacancy&…` |
| Acquisition layout CTA | Подборы acquisition header | «Создать в Marketing» + legacy banner + Campaign link when `reconciliation.status=linked` |
| Search workspace pulse | «Запустить рекламу» | Marketing setup href (not legacy create) |
| Snapshot | `GET …/acquisition` | `legacy_mode`, `reconciliation`, `marketing_setup_path` |
| Form Builder / Sources / Mapping | Settings lead-forms + Meta admin | **out of scope** until C-3…C-6 |

Scan tests: `backend/tests/api/test_acquisition_c2_legacy_launch_disabled.py`, `hostflow-frontend/src/app/__tests__/acquisitionC2LegacyLaunchScan.test.ts`.

### C-3…C-5 sketch (Sources foundation → Mapping)

**C-3 Sources list columns (minimum):** status (Connected / Attention / Disconnected), provider, account/portfolio, page, provider form, last lead at, last error, Mapping Health, destination, active Flights count.

**C-3 waiting / missing Campaign-Flight visibility (this PR only — no runtime change):**

| Signal | Operator sees |
|--------|----------------|
| `waiting_submissions` | Count of saved submissions in technical wait (`needs_routing`) for this Source |
| Last submission time | Already on list (`last_submission_at`) |
| `last_problematic_ad_id` | Most recent waiting Meta Ad ID |
| Concrete reason | **Campaign/Flight для этого Ad ID не настроены** (`routing_issue_code=missing_campaign_flight`) — not an abstract “Awaiting Routing” UI status |
| CTA | **Настроить Campaign/Flight** → Marketing setup deep-link |

**C-3 limitation (explicit):** this PR displays the **current** routing / `needs_routing` state. Full waiting-submission semantics for Meta under the Ad ID → Campaign/Flight model land in a **separate runtime PR** (contract below). Do **not** mix runtime ingest changes into C-3.

### Locked contract — Meta Ad ID → Campaign/Flight (before runtime PR)

Short decision in this Acquisition SoT. No new ADR unless a real L0/L1 gap appears. Runtime implements this contract in **one** follow-up PR after C-3 merges.

**Inventory (2026-07-23) — locked:**

- `meta_ads_map` stays **Ad ID → Vacancy only** (do not overload with Flight).
- Flight attribution needs a **separate** binding table (do not extend `CampaignRunForm` / `CampaignRunIntakeSource`).
- Unique key must be composite `(tenant_id, provider, provider_ad_id)` — **never** global `PK = ad_id` (meta_ads_map anti-pattern).

#### 1. Fact of receipt (Submission)

For Meta, the existing **`Lead`** with raw/`normalized` payload **is** the Submission. Do **not** add a Meta Submission table in the runtime PR if Lead already allows:

- store payload;
- store `ad_id`;
- tell whether Candidate/Application already exists;
- reprocess idempotently (`tenant+source+external_id`, Application `(tenant, candidate_id, lead_id)`).

Ingest always persists Lead. Routing may stop without creating Candidate/Application.

#### 2. Advertising route key

**Canonical rule:** for a Meta submission with `ad_id`, Campaign/Flight is resolved by **Ad ID**.

Resolution order:

1. Exact **active** binding Ad ID → Flight;
2. If none — do **not** route (no Candidate/Application); reason `missing_campaign_flight`;
3. Form ID, Page ID, IntakeSourceProfile **must not** pick a different Flight;
4. **`profile_default` is forbidden** for such a submission.

Form / Source remain for Meta connection, field mapping, intake type, diagnostics, and Source UI — **not** for ad attribution.

#### 3. Binding schema — `FlightAdBinding` (minimal)

Table (name illustrative; acquisition schema): e.g. `acq_flight_ad_bindings`.

| Column | Notes |
|--------|--------|
| `id` | UUID PK |
| `tenant_id` | RLS / isolation |
| `provider` | e.g. `meta` |
| `provider_ad_id` | string (Meta ad id as text) |
| `campaign_id` | FK → campaign; must own `flight_id` |
| `flight_id` | FK → campaign run (Flight) |
| `is_active` | bool |
| `created_at` / `updated_at` | timestamps |

**Constraints**

- Unique **active** route: `(tenant_id, provider, provider_ad_id)` where `is_active` (partial unique index preferred).
- Flight must belong to Campaign and same tenant.
- Deactivate/delete binding must **not** delete Leads.
- Do **not** reuse `meta_ads_map.ad_id` as lone PK.

`meta_ads_map` remains Vacancy SoT for the same Ad ID (second table, different concern).

#### 4. Write points (binding)

| Point | When |
|-------|------|
| Marketing setup / Flight ops API | Operator links Meta Ad ID to a Flight (create / update / activate) |
| Deactivate / reassign API | Operator turns off or moves Ad → another Flight |
| **Not** | Meta webhook ingest (read-only consumer of binding) |
| **Not** | `meta_ads_map` CRUD (Vacancy only; no dual-write of Flight) |

First runtime PR: backend binding CRUD (or attach on existing Flight endpoints) + resolver/reprocess. Marketing UI CTA may deep-link setup; full Ad-picker UX can follow if needed.

#### 5. Auto-reprocess trigger

After **successful commit** of: create active binding, activate (`is_active` false→true), or change `flight_id` on an active binding for `(tenant, provider, ad_id)`:

1. Select Leads where `tenant_id` match, `source`/`provider` = binding provider, `ad_id` exact match;
2. No `candidate_id` (and no Application for this lead);
3. Stopped for **`missing_campaign_flight`** only (`lead.error` and/or `acquisition_routing_v1.unresolved_reason`);
4. Re-run existing idempotent process path (`process_normalized_lead` / equivalent) per lead.

No “Process waiting” button. Do **not** reprocess other `needs_routing` causes.

#### 6. Vacancy after Flight (priority)

Once Flight is resolved from Ad binding:

1. **CampaignTarget** on that Campaign: primary target with `target_type=vacancy` → `target_id` as vacancy;
2. Else **`meta_ads_map`** for the same Ad ID → Vacancy;
3. Else leave Lead without Candidate; vacancy unresolved reason (distinct from `missing_campaign_flight`).

Do not invent a third Vacancy SoT.

#### 7. Runtime PR scope (single PR after C-3)

1. Migration + model `FlightAdBinding`  
2. Resolver Ad ID → Flight; Meta+`ad_id` path ignores Form/Profile Flight and forbids `profile_default`  
3. Persist Lead + `missing_campaign_flight` when no active binding  
4. Binding write API + auto-reprocess trigger (filter above)  
5. Vacancy priority §6  
6. Activity: `SubmissionReceived`, `RoutingFailed` (`missing_campaign_flight`), `RoutingCompleted`, `CandidateCreated`, `ApplicationCreated` if in catalog  
7. Tests: no Candidate without binding; Form/Profile cannot override; reprocess idempotent; only `missing_campaign_flight` rows reprocessed  

**C-4 field discovery table:** provider field · sample (masked) · proposed HostFlow target · action (confirm / select).

**C-5 mapping + routing preview:** confirm decisions; show Person / Candidate / answers / ignored; duplicate policy; assignee/queue; dry-run without silent drop of unknown fields (inbox / Needs review).

### C-6 sketch (Forms)

- Operator create/edit/publish from Marketing without Settings as the only path  
- Marketing Setup: select-existing **and** create-new-form-in-flow  
- Forms SoT remains ADR-007; cutover is **navigation and workflow**, not a second Forms runtime  

### C-7 sketch (decommission + PASS)

- Подборы ad-launch UI retired or strictly read-only with redirects  
- Reconciliation inventory documented  
- Production nav smoke of full Marketing IA  
- Stage 4 product cutover gate closed → Stage 5 PR-2 may resume  

**C-7 PASS = Acquisition Product Track cutover complete.**  
After that, work is **product evolution**, not migration onto the Campaign/Flight + Sources model:

| After C-7 | Nature |
|-----------|--------|
| **Source Diagnostics** | First ops epic (top-level Marketing Diagnostics) |
| Stage 5 Optimization PR-2+ | Improve running Flights |
| Stage 6 Analytics / automation / AI assistants / campaign recommendations | Exploitation & growth features |

Do **not** reopen cutover scope for those — they assume the onboarding path and Marketing IA above already work.

---

## OUT

- Auto-pause / Stage 5 PR-2 explainability (resume only after cutover PASS)  
- Renaming Vacancy/Inbox into Campaign  
- New Marketing product module / `marketing.*` host (ADR-024 anti-scope)  
- Changing Flight Runtime command matrix  
- New mapping engine parallel to `IntakeSourceProfile.mapping_rules`  
- Decommissioning Подборы before C-6 complete  
- **Source Diagnostics** (operations after onboarding) — see below; **not** C-3…C-5 scope  

---

## After cutover — Source Diagnostics (separate Product Epic)

**Not part of this cutover.** Opens only after **C-7 PASS**.

| | Onboarding (this cutover) | Operations (Source Diagnostics epic) |
|--|---------------------------|--------------------------------------|
| **Lifecycle** | One-time setup to **Ready** | Daily casework on arrived leads |
| **Goal** | First successful Connect → Flight → Lead | Explain and repair live intake for a specific submission |
| **Marketing home** | **Sources** (Connection · Mapping · Health) | **Diagnostics** — **sibling** of Sources, not a Sources tab |
| **Provider scope** | Meta-first; HostFlow form / webhook as listed sources | Provider-agnostic console (Meta + future channels) |

Cutover (C-3…C-5) may show only **summary** signals on a Source (last lead at, last error, Mapping Health). Full ops console waits for this epic.

Minimum epic intent (lock later in its own task doc):

- recent submissions  
- processing timeline  
- raw payload  
- normalized payload  
- routing decision  
- duplicate decision  
- mapping version used  
- warnings / Mapping Health drift alerts  
- replay submission  
- export payload  

---

## Acceptance (cutover PASS)

- [x] Marketing is a top-level sidebar section (not under Sales) — **C-1**  
- [x] No new acquisition launch outside Campaign/Flight — **C-2**  
- [ ] Marketing → Sources shows inventory + connection + Mapping Health — **C-3**  
- [ ] Operator can obtain a test/sample submission and see detected fields — **C-4**  
- [ ] Per-source mapping workspace + routing preview; unknown fields force review (not silent loss) — **C-5**  
- [ ] Operator can create/edit/publish a form from Marketing; Setup supports select-existing **and** create-new — **C-6**  
- [ ] New ad launch cannot start from Подборы; legacy URLs redirect or read-only — **C-7**  
- [ ] Reconciliation inventory: migrated / unresolved counts documented — **C-7**  
- [ ] Sales / Recruitment / Marketing IA match the tables above — **C-7**  
- [ ] End-to-end acceptance path (Connect → … → First processed lead) executable without a developer — **C-7**  
- [ ] Deploy smoke of full production nav — **C-7**  

---

## History

- 2026-07-24: **PR2 presentation** — Campaign Detail Source cards show Lead Form / анкета HostFlow human fields; technical IDs behind «Подробнее».
- 2026-07-24: **UI split** — Create Campaign (`/marketing/new`) vs Connect Source (`/marketing/:campaignId/sources/new`); Detail empty state + primary-slot CTA gate; no ADR-024 rewrite.
- 2026-07-23: Opened after owner diagnosis — Stage 4 runtime DONE but product/UI cutover incomplete; Stage 5 PR-2 paused.
- 2026-07-23: **C-1 DONE** (#157) — Marketing top-level nav; Activity under Marketing; Sales = sales+clients only.
- 2026-07-23: Product Track next = **C-2** legacy launch stop + Campaign/Flight reconciliation (Forms C-3 deferred).
- 2026-07-23: **C-2 DONE** (#158) — legacy launch create/duplicate → 410 `legacy_launch_disabled` + `marketing_setup_path`; snapshot `legacy_mode` + `reconciliation` linked/unresolved; production smoke PASS. Merged under unstable-integration exception (scoped C-2 tests + qa-static green; full backend-ci baseline → [#159](https://github.com/igortatarynovich/HostFlow/issues/159)). Product Track next = **C-3 Sources foundation**.
- 2026-07-23: Locked **Source onboarding and mapping** as mandatory stream — PR order **C-3 Sources → C-4 Test lead/discovery → C-5 Mapping workspace → C-6 Form Builder → C-7 Searches decommission**; Settings vs Marketing split; Connection/Source/Mapping levels; Person→Candidate→Application/Inquiry→Raw hierarchy; Mapping Health; reuse existing mapping_rules/test-ingest; Подборы UI stays until C-7.
- 2026-07-23: Noted post-cutover epic **Source Diagnostics** (ops: submissions timeline, raw/normalized, routing/duplicate, mapping version, replay/export) — explicit OUT of C-3…C-5; open only after C-7.
- 2026-07-23: Locked **two lifecycles** (Onboarding vs Operations) and Marketing IA evolution: during C-3…C-7 Sources holds Connection/Mapping/Health; after C-7 **Diagnostics** is a top-level Marketing tool (not a Sources tab), provider-agnostic.
- 2026-07-23: Locked closure: **C-7 PASS ends Acquisition UI cutover / migration**; further Acquisition work is product evolution (Diagnostics, Stage 5+, analytics, automation, AI) — not another model move.
- 2026-07-23: **C-3 Sources** — inventory + Mapping Health + **waiting visibility** over current `needs_routing` (read-only). Limitation: full Meta waiting semantics under Ad ID → Flight = separate runtime PR. Locked SoT contract: Lead = Meta Submission; route by Ad ID; no Form/Profile Flight override; forbid `profile_default`; dedicated Ad→Flight binding (check `meta_ads_map` first); auto-reprocess only `missing_campaign_flight` rows.
- 2026-07-23: Inventory closed — keep `meta_ads_map` as Vacancy only; add `FlightAdBinding` with composite unique `(tenant_id, provider, provider_ad_id)`; vacancy after Flight = CampaignTarget(vacancy) then meta_ads_map; write points + auto-reprocess trigger formalized in cutover SoT (runtime code still gated on C-3 merge).
- 2026-07-23: **C-3 DONE** (#160). Runtime PR started: `feat/acq-meta-ad-flight-binding` — `FlightAdBinding` + Meta Ad resolver forbids `profile_default`; auto-reprocess on binding commit.
- 2026-07-23: Runtime PR #161 harden — binding commit first, then batched auto-reprocess (page size 200, commit per batch) in a separate tenant session; reprocess errors never roll back binding; resume-safe on re-trigger.
- 2026-07-24: #161 — SQL-filter waiting (`Lead.error` / `normalized.acquisition_routing_v1.unresolved_reason`); no oversampling starvation; Ad binding API Meta-only (`provider=meta` ↔ `Lead.source`).
