# Recruitment Application — lifecycle semantics

**Purpose:** Canonical **meaning** of Application status, allowed transitions, and idempotency — **intent / cycle** layer only.

**Single canon (reconciliation):** §§1–11 below are the **normative semantics** for recruitment intent. The [Applications operating model](../architecture/applications-operating-model.md) explains **why** Application exists and what it must not absorb; its §4 does **not** introduce a competing status vocabulary. [Application creation — MVP](application-creation-mvp.md) covers **when rows are created** and acceptance tests. **[Implementation contract + branch diff + conflict register](recruitment-application-lifecycle-sync-note.md)** tracks code alignment, parallel-branch `git diff`, and **open** items (do not resolve silently there).

**Related:** [Applications — operating model](../architecture/applications-operating-model.md) (entity boundaries; **no second enum**), [Application creation — MVP](application-creation-mvp.md) (when rows are created), [Recruitment domain model](../architecture/recruitment-domain-model.md) (Lead / Candidate / Application — Candidate stage **different** concern, см. также ADR-002), [Slice 4 — Activity continuity guards](slice-4-activity-continuity-guards.md) (Lead→Candidate handoff: suppress duplicate **first-contact** UOS / reminders using lead signals — **does not** define Application status; see that doc §1.1).

**Audience:** Product + backend; no workflow-engine product design here.

---

## 1. What Application lifecycle is

**Application lifecycle** describes the **state of one recruitment intent** toward a **target** (concrete vacancy **or** explicit pool / no-vacancy intent) within a **logical cycle**.

It answers:

- Is this intent **live**, **being evaluated**, **successful**, **closed negatively**, or **historical**?
- Was the intent **explicitly withdrawn** by the candidate or operator?
- Is this row **closed** and kept only for audit / analytics?

It does **not** answer:

- Which **Candidate pipeline stage** the person is in (screening, interview, offer — that stays on Candidate / tasks / automations).
- Whether the **person** is employed, on leave, or terminated (**Employee** / HR lifecycle).
- Whether a **Lead** is duplicate, pending review, or converted (**Lead** lifecycle).

---

## 2. How it differs from Candidate pipeline

| Dimension | Application lifecycle | Candidate pipeline |
|-----------|------------------------|-------------------|
| **Scope** | One **intent** (this apply, this vacancy or pool, this cycle) | One **recruitment record** for the person in tenant scope |
| **Cardinality** | Many Applications per Candidate over time | One primary stage progression per Candidate (per configured pipeline) |
| **Rejection** | **Rejected Application** = this **route** is closed | **Rejected Candidate** (stage) = overall process outcome for that recruitment context — **not** the same event |
| **Hire signal** | **Hired** on Application = this intent **resulted in hire** for this route | Hire may trigger stage updates, handoff, workforce — **downstream** of Application semantics |
| **Pool vs vacancy** | Pool intent: `vacancy_id` null with explicit pool semantics | Candidate may still have `vacancy_id` on dossier for legacy/UI; see operating model |

**Rule:** Never infer Candidate stage **solely** from Application status, or the reverse. Integrations may **correlate** (e.g. hired Application → stage update) via **explicit** product rules, not by collapsing the two models.

---

## 3. Canonical enum

All values describe **this Application row** only.

| Value | Meaning |
|--------|--------|
| **applied** | Intent is **recorded**; not yet in active recruiter evaluation (or system has not moved it forward). |
| **in_review** | Recruiter / process is **actively evaluating** this intent against the target. |
| **shortlisted** | Intent passed initial evaluation and is **in a positive shortlist** for this target (still revocable). |
| **rejected** | This intent is **closed negatively** for this target — not necessarily “never hire this person.” |
| **withdrawn** | Candidate or operator **withdrew** this intent (distinct from rejection). |
| **hired** | This intent **successfully completed** in hire for this route (see §8 for handoff; not equal to full Employee lifecycle). |
| **archived** | Intent is **closed and historical** — no operational work expected on this row. |
| **reopened** | A **previously closed** intent (see transition rules) was **explicitly brought back** into play **on the same row** — rare; see §5 vs new cycle. |

**Legacy alias:** Historical rows or clients may still send **`active`**. In this codebase, **`active` is normalized to `applied`** at read time and via DB migration (see §12). Do **not** introduce new writes of `active`.

---

## 4. Transition matrix

**Allowed transitions** (rows = from, columns = to). `—` = not allowed by default; overrides require explicit policy + audit.

Legend: ✓ = allowed; **(c)** = conditional (guards in §5–§9).

**Same-status (“no-op”) transitions:** The matrix describes **changes** of state. Implementations **should** treat `status → same status` as a valid no-op (idempotent PATCH retries). The edge set below lists **distinct** `from → to` pairs only.

| From \\ To | applied | in_review | shortlisted | rejected | withdrawn | hired | archived | reopened |
|------------|---------|-----------|-------------|----------|-----------|-------|----------|----------|
| **applied** | — | ✓ | ✓ **(c)** | ✓ | ✓ | ✓ **(c)** | ✓ **(c)** | — |
| **in_review** | — | — | ✓ | ✓ | ✓ | ✓ **(c)** | ✓ **(c)** | — |
| **shortlisted** | — | ✓ **(c)** | — | ✓ | ✓ | ✓ **(c)** | ✓ **(c)** | — |
| **rejected** | — | — | — | — | — | — | ✓ | ✓ **(c)** |
| **withdrawn** | — | — | — | — | — | — | ✓ | ✓ **(c)** |
| **hired** | — | — | — | — | — | — | ✓ | ✓ **(c)** |
| **archived** | — | — | — | — | — | — | — | ✓ **(c)** |
| **reopened** | ✓ **(c)** | ✓ | ✓ **(c)** | ✓ | ✓ | ✓ **(c)** | ✓ **(c)** | — |

**Guards (normative intent):**

- **applied → hired** / **in_review → hired** / **shortlisted → hired:** only when hire decision is **bound to this Application’s target** (correct vacancy or approved pool-to-hire path).
- **rejected / withdrawn / archived → reopened:** only via **explicit** operator or system rule (HR return, correction, legal reopen) — not automatic on new inbound signal.
- **reopened → applied:** use when the row is live again but must **reset** to “recorded” semantics before review.
- **Terminal hygiene:** **rejected** and **withdrawn** should typically move to **archived** after a cooling period or immediately — product choice; matrix allows direct **archived** from open states.

**Withdrawn vs rejected:** Both are terminal for the **current evaluation**; relaunch of interest should default to **§5 (new cycle)** unless **reopened** is explicitly allowed.

---

## 5. Repeat apply rules

**Default:** A **new** Application row = **new `application_cycle`** (or new cycle identifier), even if `candidate_id`, `vacancy_id`, and `source` repeat.

**Same row update** is **not** the default for “they applied again” — it obscures history and breaks audit.

**Exceptions (same row, no new cycle):**

- **Idempotent replay** of the **same** external event (webhook retry) — see §10.
- **Explicit correction** (wrong status keyed by operator) — audit trail required.

**New cycle** should carry:

- New **`applied_at`** (or explicit business timestamp from source).
- Stable **`lead_id`** / **`source`** / **`external_id`** per §10 for deduplication — not reuse of an old row as “update.”

---

## 6. Pool → vacancy rules

**Pool Application** = intent with **no** `vacancy_id` (explicit pool / talent intent — see [application-creation-mvp](application-creation-mvp.md)).

**Binding** when a concrete vacancy is chosen:

- **Preferred:** Keep **one row** and set `vacancy_id` **if** the cycle is unchanged and the business meaning is “same intent, now anchored.”
- **Alternative:** Create a **new** Application if pool intent and vacancy intent are considered **separate** episodes (stricter audit). Product must pick one default; HostFlow default recommendation: **same row + audit field** for pool→vacancy **within the same cycle** if there was no rejection/withdrawal in between.

**Not allowed:** Silent pool→vacancy change **without** recording that the target changed (meta or event), even if staying on one row.

**Status:** Typically **applied** or **in_review** during binding; moving to **shortlisted** only after target is stable if the pipeline requires it.

---

## 7. Vacancy switch rules

**Vacancy switch** = candidate was evaluated for vacancy **A** and should be evaluated for vacancy **B** instead (or in parallel).

- **Default:** **New Application** row for **B** (possibly new cycle). **Do not** overwrite `vacancy_id` on the row that already progressed through **in_review / shortlisted** for **A**, unless a dedicated **“reroute intent”** transition exists with full audit.
- **Parallel intents:** Two Applications may be **open** at once for different vacancies if the product allows; each has its own lifecycle.
- **Closing the old intent:** Moving **A** to **rejected** or **withdrawn** with reason “rerouted” is preferred over leaving two contradictory **shortlisted** rows without policy.

---

## 8. HR handoff / return rules

**Handoff:** When recruitment commits to hire on this Application, transition to **hired** on **this** row; **Employee** / HR records are **downstream** (not defined here).

**Return from HR** (candidate sent back to recruitment **for the same route**):

- **Preferred:** **New Application** + **new cycle** (clean intent story).
- **Same row:** Only via **reopened** (or **archived → reopened**) with explicit reason — e.g. failed start, contract voided before day one, governed by tenant policy.

**Important:** **Hired** on Application ≠ “employee active forever.” Termination / rehire is **Employee** + **new Application** territory, not a silent rollback of **hired** to **in_review**.

---

## 9. Existing employee reactivation

When a **former or current employee** enters recruitment again:

- **New recruitment intent** → **new Application** (and **new cycle**), linked to the appropriate **Candidate** record (same or new Candidate per tenant identity rules — **outside** this doc).
- **Do not** revive arbitrary **archived** Applications from a past employment era without **reopened** + audit and policy.

---

## 10. Idempotency rules

Idempotency prevents duplicate rows from **retries** and **multi-channel** ingestion while preserving **§5** (true second apply = new cycle).

**Composite keys (conceptual — implementation may use partial unique indexes + nullable columns):**

| Key | Use |
|-----|-----|
| **`tenant_id` + `candidate_id` + `vacancy_id` + `application_cycle`** | **Vacancy-bound** intent: at most **one** open “active” row per cycle per target, unless product explicitly allows parallel duplicates. |
| **`tenant_id` + `candidate_id` + `vacancy_id` IS NULL + pool discriminator + `application_cycle`** | **Pool** intent: require a **stable pool discriminator** in schema or `meta` (e.g. funnel / campaign) so “pool” is not a single undifferentiated bucket if multiple pool intents exist. |
| **`lead_id`** (when not null) | **One** Application per `(tenant, lead_id)` for the canonical conversion path — retries **upsert** the same row (MVP alignment). |
| **`source` + `external_id`** (when present) | Ingestion idempotency: same external application event → same row; **different** external id → **new** row or new cycle per §5. |

**Rules:**

- **Same** `lead_id` + replay → **no second row**.
- **New** lead, **same person**, **same vacancy** → usually **new** `lead_id` → **new** Application (possibly same Candidate after duplicate resolution) — **not** idempotent with previous Application unless product defines merge.
- **Repeat apply** with **new** external id → **new cycle** (new row).

**MVP implementation subset (today):** `ensure_recruitment_application_for_lead_intent` implements idempotent upsert for **`(tenant_id, candidate_id, lead_id)`** when `lead_id` is set, and for **`(tenant_id, candidate_id, vacancy_id, source)`** when `lead_id` is null and a resolved vacancy exists — see [sync note §2](recruitment-application-lifecycle-sync-note.md). **`external_id`** on the row and full **pool discriminator** uniqueness are **not** required for the first slice; they remain **open** until a second-apply / portal contract lands (sync note **C2b**).

---

## 11. Non-goals

The following are **explicitly out of scope** for this lifecycle spec and the **first** implementation slice that follows it:

- **No workflow engine** — no generic state machine product, BPMN, or per-tenant DAG for Application.
- **No orchestration layer** — no central saga coordinator; only **transition helpers** and explicit API/service calls.
- **No reports migration** — analytics may keep using existing fields until a dedicated reporting phase.
- **No removal of `candidate.vacancy_id`** — legacy dossier field remains per [application-creation-mvp §3](application-creation-mvp.md); Application remains truth for intent when a row exists.

---

## 12. Implementation contract (aligned tree)

Normative semantics remain §§1–11. The table below is the **contract alignment** for the HostFlow backend in this repository — update it when code moves.

| Topic | Spec | Code | Tests |
|--------|------|------|--------|
| Enum §3 + `active`→`applied` | §3, §3 legacy note | `backend/app/services/recruitment_application_lifecycle.py` | `backend/tests/services/test_recruitment_application_lifecycle.py`; Alembic `202605120001_recruitment_application_status_applied.py` |
| Transition matrix §4 (distinct edges) | §4 | `_ALLOWED_TRANSITIONS`, `validate_application_status_transition`, `apply_application_status_transition`, **`set_recruitment_application_status`** (ORM writes) | `test_recruitment_application_lifecycle.py` (incl. forbidden edge parametrize) |
| **(c)** guards (hire binding, reopen policy) | §4 guards | **Not** in helper — future status PATCH / domain services | — |
| Create + list | creation MVP | `recruitment_application_service.py`; GET router uses `normalize_application_status` | `backend/tests/api/test_recruitment_applications_mvp.py` |
| Idempotency `lead_id` | §10 | `ensure_recruitment_application_for_lead_intent` | MVP tests |
| Idempotency no-lead | §10 subset | same helper, `(tenant, candidate, vacancy_id, source)` branch | MVP tests |
| Pool → vacancy + audit | §6 | `meta["pool_to_vacancy_audit_v1"]` | `test_pool_to_vacancy_updates_row_and_audit_meta` |
| Vacancy switch §7 | §7 default new row | **No** dedicated policy API yet | sync note **I1** |
| No automatic Candidate.stage from Application.status | §2 | No coupling in `ensure_*`; `test_ensure_does_not_change_candidate_stage` | MVP suite (**C4**) |
| `hired` does not materialize Employee alone | §8 | No implicit Employee create on status | **C3** — add when PATCH exists |

---

## Next implementation step (after spec + sync)

1. ~~Enum + migration from `active`~~ — done in aligned tree.
2. ~~Transition helper (matrix edges)~~ — done; **`set_recruitment_application_status`** enforces writes on create (`ensure_*`); wire **future** PATCH / other mutators through the same helper.
3. **Still open:** **C2b** second-apply without new Lead; **C3** regression test for `hired`; **I1** vacancy-switch policy; **(c)** guards in service layer.
4. **UI:** display raw status with normalization only; no new workflow surfaces required by this doc.

---

## Document history

- **v1:** Initial lifecycle semantics and matrix (spec-first; code follows).
- **v2:** Reconciliation pass — single canon statement, §4 no-op clarification, §10 MVP subset, §12 implementation contract, next-step refresh.
- **v2.1:** Code contract — `set_recruitment_application_status` documented in §12 as the enforced write path for services.
