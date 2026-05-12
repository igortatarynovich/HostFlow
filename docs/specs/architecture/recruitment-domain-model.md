# Recruitment domain model — Lead, Candidate, Application (operational semantics, no code)

**Purpose:** single **narrative** description of how **intake signal**, **recruitment dossier**, and **recruitment intent** relate — and **why** separating them avoids the failure mode where “everything collapses into one Candidate row.”

**Status:** canonical **operational semantics** (product + domain); implementation may lag in places — align code incrementally.

**Related:** [lead-intake-conversion-flow-audit.md](../workflows/lead-intake-conversion-flow-audit.md) (code/UI snapshot vs this model), [ADR-013-public-intake-strategy.md](ADR-013-public-intake-strategy.md) (Lead-first vs Candidate-first public intake — **Proposed**), [ingestion-contract-template.md](../workflows/ingestion-contract-template.md) (per-channel operational contract), [lead-to-candidate-operating-model.md](../workflows/lead-to-candidate-operating-model.md) (detailed operating model, events, §8 duplicate), [applications-operating-model.md](applications-operating-model.md) (Application entity), [application-creation-mvp.md](../workflows/application-creation-mvp.md) (first DB/API slice), [recruitment-application-lifecycle.md](../workflows/recruitment-application-lifecycle.md) (Application status enum / transitions / idempotency), [recruitment-application-lifecycle-sync-note.md](../workflows/recruitment-application-lifecycle-sync-note.md) (reconciliation: code ↔ canon, C1–C4 / C2b / I1), [lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md) (Canonical Intake Resolution Layer + **Intake Resolution MVP** §8), [person-identity-layer-and-roadmap.md](person-identity-layer-and-roadmap.md) (Person **after** this model stabilises).

---

## 1. Three different things

### 1.1 Lead

**Lead** is an **inbound signal**.

Examples: Meta form; Telegram; public form; import; ad response; WhatsApp; repeat delivery; referral; website.

A Lead does **not** mean we already have a full recruitment dossier.

**Lead answers:** *“Some interest / contact / application arrived. What is it?”*

### 1.2 Candidate

**Candidate** is the **recruitment dossier** for a person in this tenant’s recruitment context.

Working card: personal data; contact history; documents; pipeline stage; recruiter ownership; notes; reminders; checks; handoff toward HR; interaction history.

**Candidate answers:** *“Who is this person **as a recruitment dossier**?”*

### 1.3 Application

**Application** is **intent** — how this Candidate is tied to a **specific recruitment context** (vacancy, pool, cycle).

Typical cases: applied to a concrete vacancy; came from a campaign mapped to a vacancy; added to a recruitment pool; applied again to another vacancy; re-engaged later.

**Application answers:** *“**In which recruitment process** is this Candidate participating?”*

---

## 2. Why Lead ≠ Candidate

If every Lead immediately became a new Candidate, the system breaks quickly.

The same human can: Meta today, Telegram next week, another vacancy next month, another form later, become Employee, return a year later.

If every signal creates a **new** Candidate, you get: duplicate dossiers; duplicate docs; two recruiters on one person; split conversation history; broken analytics; wrong handoff; risk of a **second** Employee record.

**Lead = entry.**  
**Candidate = dossier.**  
They are not the same.

---

## 3. Why Candidate ≠ Application

**Candidate** = the person’s **dossier** in recruitment.

**Application** = a **specific participation** in a recruitment process.

One Candidate can have **many** Applications: Vacancy A, then B, pool, campaign again, client transfer, return.

If everything lives only in `candidate.vacancy_id`, the model flattens:

- one card ≈ one vacancy;
- repeat applications are lost;
- interest history is invisible;
- vacancy conversion metrics are wrong;
- “in database” vs “applied to **this** vacancy” blur;
- multiple cycles of the same person are hard to represent.

**Application** separates: *the human exists* vs *the human is in **this** process / application / vacancy context*.

---

## 4. End-to-end flow (conceptual)

### Step 1 — Lead enters

Source can be anything: Meta, Telegram, public form, import, manual, WhatsApp, referral, website.

System records: `source`; `external_id` if any; contact; raw payload; company / own-company context; possible vacancy context; consent / RODO where relevant; ingestion time.

**Lead is always created** — even without recruiter, without vacancy, weekends, etc.

### Step 2 — Idempotency

Ask: *new delivery or replay of the same lead?* (e.g. Meta redelivery.)

With `tenant_id + source + external_id`, replay must **not** create a second Lead and **not** create a second Candidate.

Outcome: new lead; or existing lead found; or idempotent replay with audit.

### Step 3 — Duplicate / identity check

Ask: *new person or existing dossier?*

Signals: phone, email, passport, tachograph, PESEL, residence card, Telegram chat id, external ids, other strong keys.

Outcomes may include: no duplicate; exact duplicate; possible duplicate; existing employee; active handoff; unclear identity.

### Step 4 — Decision: what to do with the Lead

Examples:

- **No duplicate** → may create a **new** Candidate (via conversion).
- **Exact duplicate** → do **not** create another Candidate; attach Lead to existing dossier / intake trail.
- **Possible duplicate** → **duplicate review**; human decides same person / new person / insufficient data.
- **Existing employee** → do **not** silently create a competing Candidate; reactivation / review / HR-aware path.
- **Unclear identity** → do **not** create Candidate; request data or keep in review.

---

## 5. Conversion boundary (critical)

**Candidate is not created by the webhook or the form alone.**

**Candidate is created only through a conversion decision:**

`Lead / intake signal → checks → decision → Candidate dossier`

Conversion should record (conceptually): initiator; source; lead id; duplicate outcome; company scope; vacancy context if any; assignment state; recruiter if any; **conversion contract version**.

So we can always answer: *why does this Candidate exist in the system?*

**Guardrail:** webhook ≠ Candidate; Meta form ≠ Candidate; Telegram message ≠ Candidate — **decision** creates the dossier.

---

## 6. When Application appears

Application is **not** always created.

Application exists only when there is a **recruitment intention** the system can state honestly.

### 6.1 Vacancy intent

Examples: lead tied to a vacancy; Meta campaign mapped to vacancy; public job post; recruiter selected vacancy; reroute to a concrete vacancy.

→ Application: **Candidate × Vacancy** (plus lead/source metadata).

### 6.2 Pool intent

Examples: not tied to one vacancy now, but organisation wants an explicit **pool** / talent intent.

→ Application: **Candidate × pool** (no `vacancy_id`, or dedicated representation — product choice).

---

## 7. When Application is **not** created

Do **not** create Application if:

- lead has no candidate yet;
- no vacancy and **no explicit pool intent**;
- lead in `duplicate_review` without resolution;
- identity unclear;
- pure webhook replay without new intent;
- intake draft with no recruitment decision.

Otherwise `recruitment_applications` becomes an intake junk drawer.

**Rule:** Application only if we can answer: *“In what recruitment context is this Candidate participating?”*

---

## 8–13. Worked examples (short)

| # | Scenario | Outcome |
|---|----------|---------|
| 8 | Meta lead with concrete vacancy | Lead → checks → Candidate → **Application** to that vacancy → pipeline. |
| 9 | Meta replay same `external_id` | Same Lead; no second Candidate; **no** second Application; idempotent audit. |
| 10 | Same person applies to **another** vacancy later | New Lead/event; duplicate finds Candidate; **new Application** to Vacancy B; one dossier, two intents. |
| 11 | Strong profile, **no** vacancy | Lead → Candidate possible; Application **only** with explicit **pool** intent; otherwise dossier without lying about “applied to vacancy”; follow-up to place. |
| 12 | Possible duplicate | Lead exists; **no** Candidate until decision; **no** Application; after attach/create → Application if vacancy/pool intent. |
| 13 | Person already **Employee** | No silent new Candidate; reactivation review / application event / notify HR / **manual** decision — HR ownership must not be bypassed. |

---

## 14. Assignment (separate axis)

**Assignment** answers: *who should work this lead/candidate **right now**?*

Illustrative states: unassigned; assigned; claimed.

**Do not conflate** assignment with: pipeline **stage**; **vacancy**; **Application** row; long-term **ownership**; **HR handoff**.

Example: Lead unassigned; Candidate assigned; Application tied to vacancy; HR owns dossier after handoff — **different dimensions**.

---

## 15. Vacancy

**Vacancy** is **company demand**, not Lead and not Candidate.

**Application** links **Candidate** to **Vacancy** (or pool).

Only `candidate.vacancy_id` → at most one “current” vacancy visible; history and repeat intents collapse.

With **Application** → multiple applications, sources, times, statuses, cycles — and honest analytics per vacancy.

---

## 16. Why Application now

Separating modules and meanings:

**Without Application:** Candidate becomes person + application + vacancy + pipeline in one blob; `vacancy_id` is a magic field; duplicates of intent; pool vs vacancy blurred; handoff story weak; vacancy analytics break.

**With Application:** Candidate = dossier; Application = intent; Vacancy = demand; Lead = signal; Employee = employment — **separation**.

---

## 17. Canonical formula (one screen)

1. **Lead** records **entry**.  
2. **Duplicate resolution** decides new vs existing person.  
3. **Conversion** creates **Candidate** dossier.  
4. **Application** records **why** this Candidate is in a recruitment **context** (vacancy or pool).  
5. **Assignment** = who works it **now**.  
6. **Handoff** = operational **owner** transition (e.g. to client / HR).  
7. **HR** materialises **Employee** when employment applies.

---

## 18. Current implementation alignment (transitional)

At this stage it is **expected** that:

- Candidate creation is **centralised** (e.g. through the main conversion path / wrapper — see codebase).
- High-volume leads go through the **conversion** pipeline, not ad-hoc Candidate inserts.
- **Application** is a **separate** table/row from Candidate.
- Application is created only when **vacancy intent** or **pool intent** exists (MVP: see [application-creation-mvp.md](../workflows/application-creation-mvp.md)).
- `duplicate_review` does **not** create Application until resolved.
- Bare lead without candidate/intent does **not** create Application.
- **`candidate.vacancy_id` may remain dual-write** for legacy UI until Application reads are primary.

**Do not** rip out `candidate.vacancy_id` prematurely — grow confidence in the Application layer first.

---

## Design strengths (why this model scales)

1. **Conversion boundary** — no “channel creates Candidate” by accident.  
2. **Application only with intent** — table stays honest, not intake garbage.  
3. **Pool vs vacancy intent** — “good for market” ≠ “applied to this requisition.”  
4. **Duplicate attach + Application** — attach is **new intent / new source / possible new Application**, not “nothing happened.”  
5. **Assignment as its own axis** — avoids one “status” field doing everything.  
6. **Employee collision** — silent second dossier is forbidden; HR-aware paths.  
7. **Person deferred** — Applications + duplicate + intent relieve most pressure that products wrongly solve with a premature global identity layer.

This is the **recruitment domain separation** that can later scale to agencies, employers, multi-country, rehire, pools, client portals, workforce — **without** melting semantics back into one Candidate table.

---

## Relation to “doctrine” docs

Semantic **inequalities** and intake UX guardrails: [lead-intake-resolution-and-activity-continuity.md](../workflows/lead-intake-resolution-and-activity-continuity.md).  
Formal funnel, events, duplicate §8: [lead-to-candidate-operating-model.md](../workflows/lead-to-candidate-operating-model.md).  
Application MVP DDL/triggers/tests: [application-creation-mvp.md](../workflows/application-creation-mvp.md).
