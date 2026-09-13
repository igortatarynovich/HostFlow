# Employment start_allowed — adaptation design (PEM-1)

**Status:** research draft (L3) — **Accepted** (adaptation design); runtime foundation = separate slice  
**Accepted:** 2026-09-13  
**Depends on:**  
- Contract: [`../specs/architecture/employment-start-allowed.md`](../specs/architecture/employment-start-allowed.md) (**Accepted**)  
- Inventory: [`employment-start-allowed-runtime-inventory.md`](employment-start-allowed-runtime-inventory.md) @ `466016b6`  
- PEM-1: [`production-employment-minimum.md`](production-employment-minimum.md)  
**Runtime foundation slice:** [`../specs/tasks/employment-start-allowed-runtime-foundation.md`](../specs/tasks/employment-start-allowed-runtime-foundation.md) (**OPEN**)  
**Does not amend:** Accepted `employment_start_allowed.v1` operator question · ESO-4/5 PASS stamps · Full Spine Gate  

> SoT for **how** inventory adapt/missing close without a parallel evidence layer.  
> **Not** Full Spine. Slice sequencing below — do not collapse into one PR.

---

## Hard locks

### Evaluator does not own evidence

```text
start_allowed evaluator READS existing Contract / Medical / BHP authorities
via normalized evidence views.
It does NOT own their data and does NOT create a parallel evidence layer.
```

| Owns | Does not own |
|------|----------------|
| Admit-to-work **derived** decision | Contract/Medical/BHP document rows, meta, merge drafts |
| Typed exception resolutions (§5) | Free-text HR waives as admit bypass |
| Satisfaction **predicates** on normalized views | Interpreting raw Hub subtype schemas ad hoc |

### Derived state (mandatory)

```text
start_allowed is derived state, not operator-set state.
```

- **Forbidden:** `PATCH employee.start_allowed = true` (or any operator-writable boolean that *is* the authority).  
- **Allowed:** persist evaluate/apply **decision snapshots** for audit/UI — truth MUST be reproducible by `employment_start_allowed.v1` from current context + evidence views + exceptions.  
- Snapshot stale vs re-eval → re-eval wins.

Write paths for Contract/Medical/BHP stay on existing Documents / HR surfaces. Operator supplies missing evidence **there**; evaluator only re-reads.

---

## 1. Employee mint — adapt (no new service)

| Decision | Choice |
|----------|--------|
| **Canonical primitive** | `handoff_from_candidate` only for Employment-spine mint after ESO-4 |
| **Order (frozen)** | `ESO-4 allow-create → mint Employee → start_allowed → ESO-5 confirm` |
| **New mint service** | **Forbidden** |
| **Manual `create_employee`** | HR-only sibling; **out of** Employment spine happy path |
| **ESO-5 mint-on-confirm** | **Legacy** — retire only in **slice 4** (ESO-5 enforcement cutover), not in foundation |

Compose existing helpers (`ensure_hr_operational_context` preferred for parity). Do not fork mint.

---

## 2. Contract proof — adapt (normalized view)

**Authority:** Documents Hub (Contract domain).  
**Not proof:** `contract_draft_preview` · ESO-4 `confirm_employment_contract_basis`.

### Lock

```text
start_allowed reads a normalized Contract evidence view.
It does NOT interpret different contract-document schemas itself.
```

Documents authority projects Hub artifacts into:

| View field | Meaning |
|------------|---------|
| `written_instrument_confirmed` | **true** iff written employment contract **OR** written confirmation of employment terms (PEM-1) |
| `instrument_kind` | `signed_employment_contract` \| `written_confirmation_of_terms` (Documents-owned mapping) |
| `employer_ref` / `start_at` | When available from Documents projection |
| `evidence_document_id` | Link for audit |

### Satisfaction predicate

`written_employment_contract_or_confirmation` satisfied iff:

1. Normalized view present for this Employee.  
2. `written_instrument_confirmed === true`.  
3. Projection rejects draft-only / rejected / soft-deleted Hub rows.

How Documents derives `written_instrument_confirmed` (Documents SoT, not evaluator):

- signed employment contract path, **or**  
- written confirmation of employment terms path  

Exact meta/flags stay in Documents schema errata. Evaluator never hard-codes `signed_at`-only.

---

## 3. Medical — adapt (fit-for-post; start-date validity)

**Authority:** existing `medical_certificate` (+ aliases). **No second medical store.**

### Admit / start reference date

```text
medical_valid_until >= planned_start_date
```

- **`planned_start_date`** = canonical start fact shared with ESO-5 (`start_date` / planned start on package or stored start fact) — **one** date, not a second layer-local date.  
- If `planned_start_date` is **unknown** → requirement is **`missing`** with primary toward that start fact (e.g. `planned_start_date`) — **never** treat “valid today” as satisfied.  
- **Forbidden fallback:** evaluation “today”.

### Satisfaction predicate

`occupational_medical_fit_for_post` satisfied iff **all** hold:

1. Employee-linked medical certificate (or alias) via medical evidence view.  
2. `planned_start_date` known.  
3. `medical_valid_until` (from meta `expires_at` and/or verified `exam_valid_until`, Documents/HR projection) **≥** `planned_start_date`.  
4. Fitness facts on **same** document meta (Documents errata):  
   - `fit_for_work` = true / `fit` (PEM-1 default: no restrictions enum unless later allowlisted)  
   - `applies_to_post` matches employment context post  
   - `working_conditions_ref` or `conditions_match=true` for current post context  
5. No PEM-1 medical exception codes.

---

## 4. BHP — adapt (introductory + applicability)

**Authority:** existing `bhp` / `szkolenia_BHP`.  

### Evidence path predicate

Satisfied iff all hold:

1. Employee-linked BHP document.  
2. `training_date` present.  
3. Introductory intent: `training_kind=introductory` (or equivalent Documents-normalized field).  
4. Applicability: employer + `post_key` match start context.  
5. If `expires_at` present: `expires_at >= planned_start_date` (same canonical start date rule as medical; if start date unknown → `missing` planned_start_date, not “today”).

Periodic-only training does **not** satisfy.

### Exception path

Allowlisted `bhp_successive_same_employer_same_post` (§5) — not free-text waive.

---

## 5. Exceptions — narrow new authority

**Only** new authority justified by inventory (**missing**).

### Record shape

```text
employee_id
requirement_code
exception_code            # allowlisted only
facts_json
evidence_refs[]           # optional links to existing docs
actor_user_id
created_at
(revoked_at / revoked_by optional)
```

### PEM-1 allowlist — BHP successive

| `exception_code` | `requirement_code` | Required `facts_json` |
|------------------|--------------------|------------------------|
| `bhp_successive_same_employer_same_post` | `introductory_bhp_before_admit` | `employer_id`, `post_key`, `prior_contract_ref`, `prior_contract_end_date`, `current_contract_start_date`, `successive=true` |

**Not required:** `prior_employee_id` (legal/business link is prior **employment relationship / contract**, not a HostFlow Employee id).

### Evaluator proof of succession (mandatory)

Do **not** trust `successive=true` alone.

Evaluator MUST verify, using facts (+ optional evidence_refs):

1. `employer_id` and `post_key` match current PEM-1 start context.  
2. `prior_contract_end_date` and `current_contract_start_date` are present and parseable.  
3. **Immediate succession:** no gap beyond policy-allowed zero/next-day succession rule (PEM-1: current start is the calendar day after prior end, or same-day succession if Documents/facts assert contiguous — exact calendar rule frozen in reference module; must be deterministic).  
4. `prior_contract_ref` non-empty and distinct from current instrument ref when both known.

If facts incomplete or succession not proven → exception does **not** satisfy; `rejected_patch` or remain `missing`.

Medical: **no** exception codes at PEM-1.

---

## Cross-cutting consume loop

```text
if planned_start_date unknown and any date-bounded predicate needs it → missing(planned_start_date)
for each applicable required_action:
  if allowlisted exception resolves (with succession proof where required) → satisfied
  else if normalized evidence view passes predicate → satisfied
  else → active_missing
document.exists alone → never satisfied
start_allowed boolean is always derived from evaluate()
```

| Input | Source |
|-------|--------|
| Employee + context | Workforce + package/handoff |
| `planned_start_date` | Canonical ESO-5-aligned start fact |
| Contract/Medical/BHP | **Normalized evidence views** from Documents/HR authorities |
| Exceptions | New typed store only |
| Decision | `employment_start_allowed.v1` evaluate/apply |

---

## Runtime sequencing (Accepted)

Do **not** bind UI to mint cutover in one step.

| Slice | Scope | Out of scope |
|-------|-------|--------------|
| **1. Machine foundation** | Normalized evidence views + predicates; typed exception authority; reference evaluator; `employment-start-allowed-gate` | HR UI; mint cutover; ESO-5 enforcement |
| **2. Employee mint timing cutover** | ESO-4 allow-create → `handoff_from_candidate` → Employee | ESO-5 mint delete; Full Spine |
| **3. HR host binding** | `/app/hr/handoffs/:id`: missing evidence / supported exception → re-eval → `start_allowed` | Expanding Formalize |
| **4. ESO-5 enforcement cutover** | PEM-1 Confirm requires `start_allowed=true`; remove PEM-1 mint-on-confirm | Full Spine declare |

Full Spine remains **NOT PASS** until slices prove PEM-1 admit-to-work in product.

---

## Non-goals

- Parallel Contract/Medical/BHP stores  
- Operator-set `start_allowed` field as authority  
- Validity fallback to “today”  
- Evaluator parsing raw contract subtype schemas  
- Trusting `successive=true` without date proof  
- Expanding ESO-4 thin Formalize  
- Full Spine Gate from this Accept  

---

## Acceptance record

| Criterion | Result |
|-----------|--------|
| Medical validity vs `planned_start_date` only; unknown start → missing | **PASS** |
| Contract via normalized `written_instrument_confirmed` | **PASS** |
| BHP exception facts without `prior_employee_id`; succession proven | **PASS** |
| Derived state lock | **PASS** |
| Four-slice sequencing | **PASS** |
| Evaluator does not own evidence | **PASS** |

**Accepted** 2026-09-13 as adaptation design for PEM-1 `start_allowed`.

---

## Next

1. **Slice 1 PASS** @ `d5767488`.  
2. **Slice 2 PASS (machine/portable seam) + Formalize→ensure integration parity PASS:** [`../specs/tasks/employment-start-allowed-mint-cutover.md`](../specs/tasks/employment-start-allowed-mint-cutover.md) @ `322d0148` under test for wire; portable ESA2 @ `0c8b337f` (mixed SHA — candidate-missing excluded).
3. **Slice 3 OPEN:** [`../specs/tasks/employment-start-allowed-hr-host-binding.md`](../specs/tasks/employment-start-allowed-hr-host-binding.md) — `/app/hr/handoffs/:id` bind; one active missing → evidence/exception → re-eval → `start_allowed`. **STOP** before slice 4. Full Spine closed.
