# Application creation — MVP implementation contract

**Purpose:** Executable slice for the **first** Applications rollout: when rows are created, what is migrated, how duplicate decisions interact, and what must pass in tests. This is **workflow implementation**, not the canonical semantics (see [applications-operating-model.md](../architecture/applications-operating-model.md)).

**Related:** [Recruitment domain model](../architecture/recruitment-domain-model.md) (Lead / Candidate / Application narrative), [Lead → Candidate operating model](lead-to-candidate-operating-model.md) (§8 duplicate, conversion), [applications-operating-model.md](../architecture/applications-operating-model.md) (boundaries, non-goals), [Recruitment Application lifecycle](recruitment-application-lifecycle.md) (full status enum and transitions — **after** MVP creation rules), [Lifecycle reconciliation / sync note](recruitment-application-lifecycle-sync-note.md) (branch ↔ canon, contract alignment, **C1–C4 / C2b / I1**).

---

## Golden rule (iteration 1)

**Create an Application only when there is a `Candidate` *and* a concrete recruitment intent.**

Do **not** create Application:

- for a **Lead** that has **no** `candidate_id` yet;
- while the Lead is in **`duplicate_review`** (no decision yet).

This prevents the main failure mode: **Application must not become a second Lead.**

---

## 1. First migration — fields to add

Minimal table (names illustrative; adjust to HostFlow naming conventions):

| Column | Notes |
|--------|--------|
| `id` | UUID PK |
| `tenant_id` | Scope |
| `candidate_id` | FK → candidates, **required** |
| `lead_id` | FK → leads, **nullable** (set when intent originated from a known lead row) |
| `vacancy_id` | FK → vacancies, **nullable** (pool / no-match path) |
| `source` | String (mirror lead source / campaign attribution) |
| `recruiter_id` | FK → users, **nullable** |
| `applied_at` | Timestamp (default: intent recorded time) |
| `status` | Enum/string per [recruitment-application-lifecycle.md](recruitment-application-lifecycle.md) §3 — new rows default **`applied`**; legacy **`active`** is normalized to **`applied`** (API + migration). |
| `application_cycle` | Optional string or small int — **nullable** at MVP |
| `meta` | JSONB — small operator/system payload only |
| `created_at` / `updated_at` | Audit |

**Indexes (MVP):** `(tenant_id, candidate_id)`, `(tenant_id, lead_id)` where `lead_id` not null, optional `(tenant_id, vacancy_id)`.

No document blobs, no HR fields, no pipeline engine tables in this migration.

---

## 2. When Application is created (MVP rules)

| Situation | Application? |
|-----------|----------------|
| Lead exists, **no** `candidate_id` | **No** |
| Lead `status = duplicate_review` | **No** (wait for operator decision) |
| **`attach_existing`** duplicate decision | **Yes** — intent attaches to **existing** Candidate; create Application linking `candidate_id`, `lead_id`, resolved `vacancy_id` (from lead / candidate as per routing rules), `source`, `recruiter_id` as known |
| **`create_new`** or **`ignore`** → then **`POST /process`** creates **new** Candidate | **Yes** — create Application in the same successful conversion transaction (or immediately after candidate persist) with `lead_id` + intent fields |
| Normal Meta/CSV **process** → new or first-time Candidate | **Yes** — one Application for this conversion intent |
| **Exact duplicate** auto path (`duplicated` without review) | **Yes** — same as attach: existing Candidate + new intent from this lead → Application row (intake is not “another Lead”; it is another **intent**) |
| **No vacancy** (pool / talent context) | **Only with explicit intent** — e.g. `lead.funnel_id` set or `normalized["recruitment_pool_intent_v1"] is True`; then **Yes** with `vacancy_id` **null** (optional `meta`). Otherwise **No** (“bare” lead with no vacancy is not an application fact). |

**Legacy:** existing Candidates **without** Application rows remain valid until backfill; readers may fall back to `candidate.vacancy_id` (see §3).

---

## 3. `candidate.vacancy_id` during MVP

**Transition strategy:**

- Keep **writing** `candidate.vacancy_id` where the product already does (compatibility for lists, filters, legacy UI).
- Treat **`application.vacancy_id`** as the **intent** source of truth for “applied to which vacancy” when an Application row exists.
- **MVP:** on Application create, **set** `candidate.vacancy_id` from the resolved vacancy for that intent when vacancy is known (dual-write). Pool-only rows (explicit intent, no vacancy) do not force `candidate.vacancy_id`.
- **Later:** stop dual-write; UI reads Application; optional backfill script.

---

## 4. Duplicate decision → Application

Orthogonal layers (see [applications-operating-model.md §7](../architecture/applications-operating-model.md)):

- **Duplicate resolution** decides **whether** the Lead attaches to **which** Candidate (or override for new Candidate).
- **Application** records **recruitment intent** once that attachment + intent exists.

**Mapping:**

| Decision | Effect on Application |
|----------|------------------------|
| **attach_existing** | After link + intake trail: **create** Application for `(existing candidate_id, this lead_id, …)` if not already created for this `(candidate_id, lead_id)` (idempotent; skip if no vacancy and no explicit pool intent). |
| **create_new** | No Application until **Process** succeeds → **new** Candidate → **new** Application. |
| **ignore** | Same as create_new path: Application only after **Process** creates/links recruitment success. |

**Tests must assert:** no Application row whose `lead_id` is still in `duplicate_review` without a resolved candidate path.

---

## 5. APIs (MVP minimum)

Implementation can start **internal** (service-layer only) before public REST is exhaustive.

**Minimum useful surface:**

1. **Create Application** — internal helper used by lead→candidate pipeline (not necessarily public in v1).
2. **`GET /candidates/{id}/applications`** — list intents for a candidate (recruiter UI, timeline later).
3. **`GET /leads/{id}/applications`** or **`GET /applications?lead_id=`** — optional if easier for debugging; else infer via candidate.

**Defer:** PATCH-heavy lifecycle, employer portal, analytics exports, bulk endpoints — add when product needs them.

---

## 6. Tests that must pass (acceptance)

1. **Lead without candidate** → no Application in DB for that lead id.
2. **Lead in `duplicate_review`** → no Application for that `lead_id`.
3. **`attach_existing`** → exactly one new Application (or idempotent replay) tied to **existing** `candidate_id` + `lead_id`; duplicate intake trail on Candidate may coexist; Application still created for intent analytics.
4. **`create_new` + successful `process`** → new `candidate_id` + Application with that `lead_id`.
5. **`ignore` + successful `process`** → same as (4) with override semantics unchanged.
6. **Normal process** (no duplicate trap) → Candidate + Application.
7. **Pool / no vacancy** → no Application unless explicit intent (`funnel_id` or `recruitment_pool_intent_v1`); then one Application with `vacancy_id` null, status **`applied`** per [recruitment-application-lifecycle.md](recruitment-application-lifecycle.md) §3.
8. **Legacy candidate** (no Application row) → existing flows still work; optional backfill test marked `@pytest.mark.skip` until backfill exists.

---

## 7. Document hierarchy (reminder)

1. [lead-to-candidate-operating-model.md](lead-to-candidate-operating-model.md) — intake, conversion, duplicate, assignment.
2. [applications-operating-model.md](../architecture/applications-operating-model.md) — intent layer semantics.
3. **This file** — first migration + creation rules + APIs/tests contract.
4. [person-identity-layer-and-roadmap.md](../architecture/person-identity-layer-and-roadmap.md) — identity later.

**Later:** `docs/specs/modules/applications.md` when DB, permissions, full API, UI, and migrations are specified as a module.

---

## 8. Staging smoke — close Applications MVP (UI + backend)

Run on staging after backend migration and frontend deploy. **If all items pass, treat Applications MVP as closed** (no new feature work until product priorities change).

**Data / API**

1. Normal Meta lead → **Process** → new Candidate → exactly one `recruitment_applications` row for that lead; **GET** `/api/v1/candidates/{id}/applications` returns it.
2. **Exact duplicate** auto path → existing Candidate → new Application + intake; visible on that candidate’s applications list.
3. **`duplicate_review` → `attach_existing`** → Application on **existing** candidate; list shows source / lead / vacancy as expected.
4. **`duplicate_review` → `create_new` → Process** → **new** candidate → Application on new candidate.
5. **Pool / no vacancy** → Application row with **`vacancy_id` null**; UI shows pool / empty vacancy copy (not an error).
6. **Legacy** candidate (created before Applications) with **no** rows → GET returns `[]`; candidate card **Applications / interests** shows empty state, no error.
7. From the card, **Lead** and **Vacancy** links open the correct drill-down pages.
8. **Masked** or **new (unsaved)** candidate card → **no** Applications section (privacy / no id).

**Note:** `refreshTrigger` on the card is unnecessary for MVP; list loads on open. Add refresh only if an in-card action can create an Application without navigating away.

---

## 9. Next architectural slice (out of scope for this MVP)

Priority after Applications MVP sign-off: **[lead-intake-resolution-and-activity-continuity.md](lead-intake-resolution-and-activity-continuity.md)** — Lead as **Intake Decision Workspace**, intake resolution + reject taxonomy, **manual vacancy confirm** vs routing canonical, and **activity continuity** on convert (no duplicate “first call” work).

**Rehire / new recruitment cycle** — still **spec/guardrails first**, **after** intake clarity; not immediate code.
