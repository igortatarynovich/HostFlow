# Applications — operating model (canonical entity)

**Purpose:** Define **Application** as a first-class **operational intent** layer — semantics, boundaries, and migration path — **not** a CRUD appendix to Lead → Candidate. This document is the source of truth for *why* Applications exist and *what they must not become*.

**Related:** [Recruitment domain model](recruitment-domain-model.md) (full narrative: Lead vs Candidate vs Application, conversion boundary, examples), [Lead → Candidate operating model](../workflows/lead-to-candidate-operating-model.md) (current funnel; Candidate overload today), [Application creation MVP](../workflows/application-creation-mvp.md) (first migration, creation triggers, tests), [Recruitment Application lifecycle](../workflows/recruitment-application-lifecycle.md) (canonical statuses, transition matrix, idempotency — **spec before enum**), [Lifecycle reconciliation / sync note](../workflows/recruitment-application-lifecycle-sync-note.md) (branch diff, contract table, **C1–C4 / C2b / I1**), [person-identity-layer-and-roadmap.md](person-identity-layer-and-roadmap.md) (Person **after** Applications), duplicate / intake (§8 duplicate MVP in the workflow doc).

---

## 1. Why Application exists

**Main thesis:** One **Candidate** can have **many Applications**. That is **not** a duplicate problem.

- **Lead** = inbound *signal of interest* (intake).
- **Application** = *intent toward a specific vacancy / recruitment cycle* — “they applied *here*, *then*, *from this source*.”
- **Candidate** = recruitment *operational context* (ownership, qualification, tasks, document flow tied to **this** recruitment record — see migration for how this narrows over time).
- **WorkforceEmployee** = *employment* context (HR / post-handoff).

Applications are the layer that lets you answer: **“Which interest / which route / which cycle?”** without splitting identity or opening a second Candidate for every new vacancy interest.

---

## 2. What Application stores (minimum)

Conceptual minimum fields:

| Field | Role |
|--------|------|
| `candidate_id` | Which recruitment record this intent belongs to |
| `lead_id` | Optional link to originating intake (when converted from lead) |
| `vacancy_id` | What they applied toward |
| `source` | Campaign / channel / attribution |
| `recruiter_id` | Routing hint or assigned recruiter for **this** intent (not sole owner of entire Candidate forever — see “what not to store”) |
| `applied_at` | When this intent was recorded |
| `status` | Operational lifecycle of **this** intent (see §4) |
| `application_cycle` | Logical cycle id / label (rehire, second route, etc.) — keep lightweight at MVP |
| `notes` / `meta` | Small operator or system metadata — not a document store |

Exact schema, API shapes, and indexes are implementation details; this list is the **semantic contract**.

---

## 3. What Application must NOT store

Do **not** use Application as a dump for:

- **Documents** — document hub / candidate documents stay on the document model and Candidate (or future Person pointers), not per-application file systems in v1.
- **Employment** — payroll, contracts, ZUS, leaves → **WorkforceEmployee** / HR modules.
- **Whole-recruiter ownership of the human** — Candidate-level and assignment rules apply; Application may carry *this intent’s* recruiter, not “the only owner of the person.”
- **HR state** — readiness for HR, handoff outcome, client decision → Handoff / HR boundaries.
- **Identity** — names, canonical phones, dedupe keys → remain on Candidate (today) and later **Person** if introduced.
- **Global pipeline** — one giant “application state machine” that replaces Candidate stage; Application status is **intent** lifecycle, not the entire recruitment OS.

---

## 4. Application status (single canon)

**Do not maintain a second status vocabulary here.** All enum values, transition rules, repeat-apply, pool→vacancy, idempotency, and non-goals for Application lifecycle live in [Recruitment Application lifecycle](../workflows/recruitment-application-lifecycle.md) (§§3–11). The [lifecycle sync / reconciliation note](../workflows/recruitment-application-lifecycle-sync-note.md) tracks **code alignment**, branch diffs, and **open conflicts** (e.g. C2b, C3, I1).

**Historical note:** Early MVP drafts used a coarse **`active`** label. That is **superseded**: canonical first state is **`applied`**; legacy **`active`** normalizes to **`applied`** (see lifecycle §3 legacy note and §12).

**Reporting shorthand (non-storage):** “Operationally open intent” may be described as statuses in **`applied` | `in_review` | `shortlisted` | `reopened`** (when the row is in play again) — exact reporting definitions belong in analytics specs, not as a duplicate enum on this page.

**Refinements** (SLA substeps, interview steps) stay on **Candidate** / tasks / automations — not duplicated as Application sub-states unless the lifecycle doc is explicitly extended.

---

## 5. Explicit non-goals (do not build yet)

To avoid **premature architecture explosion**, do **not** start with:

- multi-pipeline engine per application;
- application-level workflow designer;
- AI matching or ranking at application layer;
- cross-tenant identity or shared application graphs;
- merge logic between applications (duplicate resolution stays on **Lead / Candidate** boundaries — see §7);
- application scoring or automated quality tiers;
- Application Kanban as a primary product surface.

MVP is a **thin operational intent record** + clear links to Candidate, Lead, Vacancy — not a second CRM inside the CRM.

---

## 6. Migration strategy

### Current state (today)

**Candidate** effectively holds:

- identity anchor (temporary, until Person is justified);
- recruitment lifecycle (stage, tasks, documents flow);
- vacancy relation (`vacancy_id`, interest context).

That overload is **acceptable for early MVP** but blocks clean multi-interest analytics and rehire storytelling.

### Future state (target)

- **Candidate** → recruitment **context** for a person-in-the-system (one row per recruitment subject in tenant scope).
- **Application** → **concrete recruitment intent** (this vacancy, this cycle, this source, this applied_at).

### MVP transition (gradual, non-catastrophic)

Designed to avoid a big-bang refactor:

1. **One active Application per Candidate** is acceptable initially — still teaches the model and APIs.
2. **Legacy `vacancy_id` on Candidate** may remain for a transition period; UI and reports may read Candidate until backfill is complete.
3. **Application is created at conversion / process** when a Lead becomes (or attaches to) a Candidate — first-class creation moment.
4. **UI may still show** some fields from Candidate while Application is the source of truth for “applied where / when.”

Later: multiple active Applications, rehire as new Application + cycle, analytics keyed by `application_id` where relevant.

---

## 7. Link to duplicate flow and intake

Duplicate work is a **precursor** to Applications, not a detour.

Today, events such as **`candidate.duplicate_lead_intake`** and structured intake on **`Candidate.origin.lead_duplicate_intakes_v1`** already express: *another inbound interest attached to the same recruitment subject*.

That is conceptually aligned with **multi-interest** — the same human (Candidate) receives another lead / route signal. **Applications** formalize that pattern as a normal case (“second interest”) instead of overloading “duplicate” semantics.

**Important:** Duplicate resolution answers *whether this Lead attaches to this Candidate*. Application answers *this attached interest is an intent toward vacancy X / cycle Y*. They are orthogonal layers.

---

## 8. Why Applications come before Person

**Applications solve an operational problem before an identity problem.**

- Multi-vacancy interest, cleaner pipeline history, rehire as a new cycle, and better analytics do **not** require a global Person registry.
- **Person** is justified when identity sharing, cross-company reuse, or strict “who” vs “every cycle” separation at identity level becomes a product requirement (see [person-identity-layer-and-roadmap.md](person-identity-layer-and-roadmap.md)).

Order: stabilize **duplicate / intake** → introduce **Applications** → **Rehire** / ownership → **Person** only when signals demand it.

---

## Summary table

| Entity | Question it answers |
|--------|---------------------|
| **Lead** | What came in? (intake) |
| **Application** | What did they apply **for**, **when**, **from where**? (intent) |
| **Candidate** | How do we **work** them in recruitment? (operational context) |
| **WorkforceEmployee** | How are they **employed**? (HR) |

**Application** is the **operational intent layer** — not “another table,” but the boundary that keeps Candidate from being the only place where “interest in vacancy” lives.
