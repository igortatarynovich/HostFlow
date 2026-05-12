# Recruitment Application lifecycle — reconciliation & contract alignment

**Purpose:** One place to **reconcile** the semantics canon ([recruitment-application-lifecycle.md](recruitment-application-lifecycle.md)) with **this repository’s code**, record **parallel-branch** diffs when they exist, and list **conflicts and gaps** that must not be resolved silently.

**Outcome of reconciliation (spec + tree):** There is **one** Application lifecycle canon for statuses and transitions: **lifecycle doc §§3–4**. The older coarse vocabulary **`active`** is **not** a second canon — it is a **legacy alias → `applied`** (see lifecycle §3 legacy note and §12). The [Applications operating model](../architecture/applications-operating-model.md) §4 **defers** to lifecycle §3 and does not duplicate enum meanings.

**Related:** [applications-operating-model.md](../architecture/applications-operating-model.md), [application-creation-mvp.md](application-creation-mvp.md), [lead-conversion-contract.md](lead-conversion-contract.md), [candidate-creation-entrypoints-audit.md](candidate-creation-entrypoints-audit.md), [lead-to-candidate-operating-model.md](lead-to-candidate-operating-model.md), [slice-4-activity-continuity-guards.md](slice-4-activity-continuity-guards.md), [workflows/index.md](index.md).

---

## 1. Parallel branch check

If work split across branches (e.g. `origin/feature/application-lifecycle` vs `HEAD`), compare before merge:

```bash
git fetch origin
git diff origin/<lifecycle-branch>...HEAD -- \
  backend/app/models/recruitment_application.py \
  backend/app/services/recruitment_application_service.py \
  backend/app/services/recruitment_application_lifecycle.py \
  backend/tests/api/test_recruitment_applications_mvp.py \
  backend/tests/services/test_recruitment_application_lifecycle.py \
  docs/specs/workflows/recruitment-application-lifecycle.md \
  docs/specs/workflows/recruitment-application-lifecycle-sync-note.md
```

**This clone:** remotes may not name a separate “lifecycle-only” branch — when absent, treat **lifecycle §12 + this file §2** as the alignment record for `HEAD`.

---

## 2. Contract alignment table (canon ↔ code ↔ tests)

| Topic | Canon (lifecycle doc) | Implementation (this tree) | Tests / notes |
|--------|------------------------|------------------------------|----------------|
| **Status enum** | §3 | `CANONICAL_APPLICATION_STATUSES`; new rows `applied`; `normalize_application_status` | `test_recruitment_application_lifecycle.py`; migration `202605120001_recruitment_application_status_applied.py` |
| **`active` alias** | §3 legacy | Maps → `applied` (read + migration) | `test_normalize_active_to_applied` |
| **Transition matrix** | §4 distinct edges | `_ALLOWED_TRANSITIONS` + `validate_application_status_transition` | Transition tests in `test_recruitment_application_lifecycle.py` |
| **ORM status writes** | §4 + legacy normalize | **`set_recruitment_application_status(row, new_status)`** — sole supported assign path from services | Same + `ensure_*` create path uses setter |
| **No-op `X→X`** | lifecycle §4 note | `validate_*` early-return; `set_recruitment_application_status` when `cur_n == new_n` | `test_noop_transition`, `test_set_status_idempotent_same_canonical` |
| **§4 (c) guards** | §4 guard bullets | **Not** in helper | Encode when status PATCH / hire services exist |
| **Repeat apply / new cycle** | §5 | `application_cycle` nullable; no dedicated “second apply” writer | **C2b** gap |
| **Idempotency `lead_id`** | §10 | `ensure_recruitment_application_for_lead_intent` upsert by `(tenant, candidate_id, lead_id)` | MVP API tests |
| **Idempotency no-lead** | §10 subset | `(tenant, candidate_id, vacancy_id, source)` when `lead_id` IS NULL | MVP API tests |
| **Pool → vacancy** | §6 | Same row + `meta["pool_to_vacancy_audit_v1"]` | `test_pool_to_vacancy_updates_row_and_audit_meta` |
| **Vacancy switch** | §7 default new Application | No policy layer / API | **I1** gap |
| **HR return / reactivation** | §§8–9 | Spec-only until handoff writers | — |
| **Candidate.stage coupling** | §2 | `ensure_*` does not change stage | `test_ensure_does_not_change_candidate_stage` (**C4**) |
| **`hired` → Employee** | §8 | No implicit Employee on status alone | **C3** — test when status PATCH exists |

---

## 3. Conflict & gap register (explicit)

### C1 — MVP `active` vs lifecycle §3 — **RESOLVED**

- **Was:** Older MVP text used `active` as initial status.
- **Resolution:** Storage and API canon = lifecycle §3. **`active` → `applied`** (migration + `normalize_application_status`). New writes use `applied` only.

### C2a — Idempotent replay vs §5 “new row for true second apply” — **CLARIFIED (no silent merge)**

- **§10:** Same `lead_id` + replay → **same row** (idempotent).
- **§5:** A **genuine** second application episode → **new** row / **new** `application_cycle`, not silent update of history.
- **Declared rule for current ingestion:** Replay of the **same** conversion event is keyed by **`lead_id`** (when present) → same row. A **different** `lead_id` (new intake row) → **new** Application row after attach/create, even if same Candidate + vacancy.

### C2b — Second apply **without** a new Lead (portal / same channel) — **OPEN**

- **Gap:** No stable **`external_id`** (or equivalent) on `recruitment_applications` yet; `application_cycle` not auto-set on “second apply.”
- **Next:** Product + schema: either `external_id` idempotency per §10, or explicit API “new intent” that sets `application_cycle`.

### C3 — `hired` must not materialize Employee by itself — **OPEN until PATCH**

- **Rule:** Transition to `hired` must not create `WorkforceEmployee` without the handoff path.
- **Next:** Add regression test when a public PATCH or internal status setter exists.

### C4 — Candidate pipeline vs Application — **RULE DOCUMENTED; TEST EXISTS FOR `ensure_*`**

- **Rule:** No automatic `Candidate.stage` updates from `RecruitmentApplication.status` unless a **named** integration rule exists.
- **Evidence:** `test_ensure_does_not_change_candidate_stage`.

### I1 — Vacancy switch (§7) — **IMPLEMENTATION GAP (not a moral conflict)**

- **Spec default:** new Application for vacancy B when switching off evaluated A.
- **Code:** No dedicated “switch vacancy” operation; operators must not rely on helper until product defines API.

---

## 4. Next code PRs (after reconciliation)

Order is suggestive; do not bundle unrelated concerns.

1. **Status writers:** Any service that sets `RecruitmentApplication.status` → **must** call **`set_recruitment_application_status`** (wraps normalize + `validate_application_status_transition`). Do not assign ``row.status`` directly except in Alembic.
2. **C2b:** Schema + API for second apply without new Lead (optional: `external_id`, cycle assignment).
3. **C3:** Regression test when hire transition is exposed.
4. **I1:** Vacancy switch policy (new row vs audited same-row exception per §7).
5. **§4 (c) guards:** Hire binding, reopen policy in domain layer — not only matrix membership.

**Still explicitly out of scope:** workflow engine, orchestration saga, reports migration, removal of `candidate.vacancy_id` (see lifecycle §11).

---

## 5. Document history

- **v1:** Sync note; branch diff checklist; gap table; C1–C4.
- **v2:** Reconciliation pass — single canon statement, contract table §2, C1 resolved / C2 split / I1, lifecycle §12 cross-reference, next PRs refreshed.
- **v3:** Helper enforcement — `set_recruitment_application_status` as mandatory service write path; §2 / §4 next-step wording.
