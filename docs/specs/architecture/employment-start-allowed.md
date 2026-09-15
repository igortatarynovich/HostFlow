# Employment start_allowed

**Status:** **Accepted** (L2 contract — Employment Start Allowed / admit-to-work)  
**Accepted:** 2026-09-13  
**Policy id:** `employment_start_allowed.v1`  
**Parent product decision:** [`../../analysis/production-employment-minimum.md`](../../analysis/production-employment-minimum.md) — **PEM-1 Accepted** (as a **ruleset composition**, not as evaluator topology — see ADR-042)  
**Open amend (policy/rule):** [`../tasks/admit-policy-ruleset-separation.md`](../tasks/admit-policy-ruleset-separation.md) — separate process-policy contract from PEM-1 ruleset  
**Baseline inventory:** [`../../analysis/employment-formalization-coverage-audit.md`](../../analysis/employment-formalization-coverage-audit.md) @ `b88a6168`  
**Adjacent contracts:** ESO-4 `employment_formalize.v1` (allow-create) · ESO-5 `employment_started.v1` (physical start) · [`ADR-042`](ADR-042-spine-policy-separation.md)  
**Named gate (required before runtime PASS):** `employment-start-allowed-gate`  
**Does not amend:** L0 · ESO-1…5 PASS stamps · Full Spine Gate  

> Seals the **pre-Start admit-to-work** authority.  
> **2026-09-15 note:** Kernel preflight proved the runtime evaluator currently **embeds PEM-1 requirements as topology**. Target (open work item): `start_allowed = active Admit policy evaluated to allowed`; PEM-1 = one ruleset. Empty ruleset `[]` must yield `allowed` on the **same** pipeline — not via kernel/neutral bypass.  
> **ESO-4 stays thin.** Employee mint happens **before** this policy. ESO-5 Confirm requires `start_allowed=true`.  
> **Do not** open Full Spine from this Accept. **No** “Allow anyway” override.

---

## Operator question (one)

Given an **Employee** already created (after ESO-4 `ready_to_create_employee`), for a **PEM-1** employment context, **may this person be admitted to work** — i.e. is `start_allowed=true` — based only on proven Contract + applicable Medical\* + applicable BHP\* (or a **policy-listed** typed exception), before any human Confirm physical start?

No second question is this contract. Physical start remains ESO-5. ZUS/Insurance remain post-Started lifecycle.

---

## Hard locks

| Lock | Meaning |
|------|---------|
| **ESO-4 stays thin** | Allow-create only. Do **not** add written-umowa proof, medical, or BHP to `employment_formalize.v1`. |
| **Employee exists first** | `start_allowed` evaluates an existing `employee_id`. Mint is **not** this policy’s job. |
| **Employee ≠ admit-to-work** | Minting Employee does not imply `start_allowed`. |
| **`start_allowed` ≠ Started** | `start_allowed=true` does not emit physical start or auto-confirm ESO-5. |
| **ESO-5 requires `start_allowed`** | Confirm physical start is impossible unless `start_allowed=true` (PEM-1). |
| **No manual override** | Operator may supply missing evidence or select a **supported** policy exception with auditable facts. **No** “Allow anyway” / force-admit control. |
| **Document ≠ satisfied** | Uploaded PDF / document row existence alone **never** satisfies a requirement; evaluator needs structured facts (type, validity, relation to Employee/post/context where applicable). |
| **No new evidence store** | Bind to existing Documents / contract artifacts / medical / BHP authorities + typed exception facts. |
| **Typed exceptions only** | `requirement_code` + `exception_code` + facts/evidence + actor + timestamp. Unknown exception → not operator-inventable. |
| **ZUS not in this gate** | 7-day registration is lifecycle after Started. |
| **Context not checklist** | Medical\* / BHP\* = requirement vs listed exception — no universal dump. |
| **LLM-OFF** | Admit-to-work decision is deterministic. |
| **PEM-1 scope** | A1 / delegacja / legalization / ZUS / Insurance **MUST NOT** appear in PEM-1 `required_actions`. |
| **Ownership ≠ UI host** | Policy authority = Employee; orchestration surface = existing HR handoff. No new UI workflow. |

---

## Placement in spine

```text
ESO-4 ready_to_create_employee
  → mint Employee
  → employment_start_allowed.v1  (THIS CONTRACT)
  → start_allowed=true
  → ESO-5 human confirm_physical_start
  → Started
  → ZUS / Insurance deadline lifecycle
```

Entity path:

```text
Candidate → Employment case → Employee → eligible to start (start_allowed) → Started
```

| Contract | Owns |
|----------|------|
| ESO-4 Formalize | Employee **creatable** |
| Employee mint | Materialize `workforce_employees` (**before** start_allowed) |
| **start_allowed** | **Admit-to-work** (pre-Start) |
| ESO-5 Started | **Physical start** confirm |

**Transitional note:** ESO-5 mint-on-confirm is **retired** for PEM-1 (Slice 4 **PASS**). Mint remains on/after ESO-4 allow-create via Formalize→ensure, **before** start_allowed evaluation.

---

## Closed decisions (former open questions)

### 1. Host / API authority

| Concern | Decision |
|---------|----------|
| **Policy authority** | **Employee** — evaluate/apply for a concrete `employee_id` |
| **Orchestration surface** | Existing **HR handoff** host `/app/hr/handoffs/:id` |
| **UI** | **No** new UI/workflow — bind panels on the current handoff case |
| **API** | Endpoint shape **not frozen** in this Accept; design after inventory of existing employee/handoff APIs |

Rationale: `start_allowed` is semantically about the Employee; handoff remains the process host (**ownership ≠ UI host**).

### 2. Evidence binding

**Do not** create a new evidence store.

| Requirement | Evidence authority |
|-------------|-------------------|
| Contract | Existing Documents / contract artifacts — proof of written contract **or** written confirmation of parties / type / terms |
| Medical | Existing `medical_certificate` (and peers) + **structured** validity + post/conditions applicability |
| BHP | Existing BHP document / training evidence + **structured** completion + applicability |
| Exception | Separate **audited structured fact** — not a stub document |

**Critical rule:** `document exists ≠ requirement satisfied.`  
Evaluator MUST check required structured facts (type, validity, relation to Employee / post / context where applicable). Otherwise the allow-create defect repeats as `PDF uploaded = start_allowed`.

### 3. Exceptions

**Forbidden:** generic `exception=true`.

**Required shape:**

```text
requirement_code + exception_code + facts/evidence + actor + timestamp
```

| Rule | Meaning |
|------|---------|
| Allowlist only | PEM-1 may apply **only** explicitly listed `exception_code` values in policy |
| No invent-via-UI | If policy does not know the exception, operator cannot invent it |
| Unsupported ≠ bypass | Unknown legal edge → `unsupported_context` or missing evidence path — **not** manual override |
| Medical caution | HostFlow-supported exception ≠ every statutory exception. Do not enumerate all law; unsupported medical cases stay non-bypassable |

**PEM-1 listed exception (initial allowlist):**

| `exception_code` | Applies to | Facts (minimum) |
|------------------|------------|-----------------|
| `bhp_successive_same_employer_same_post` | `introductory_bhp_before_admit` | same employer id, same post, immediately successive contract linkage, actor, timestamp |

Medical: **no** PEM-1 medical exception codes at Accept unless later errata adds a concrete allowlisted code with facts. Default = evidence of valid fit-for-post certificate.

### 4. Employee mint timing

**Frozen:**

```text
ESO-4 allow-create → mint Employee → start_allowed → ESO-5
```

- Employee **must exist** before `start_allowed` evaluation.  
- **Do not** mint inside `start_allowed`.  
- ESO-5 mint-on-confirm = **retired** (Slice 4 PASS); Confirm requires `start_allowed=true` and an existing Employee.

### 5. Named gate / CI

**Required:** `employment-start-allowed-gate` (machine gate before runtime PASS).

Minimum proofs:

1. Cannot reach `start_allowed=true` without Contract + applicable Medical + applicable BHP (or allowlisted exception).  
2. Exception works only for an allowlisted `requirement_code` + `exception_code`.  
3. `missing` emits exactly one `primary_item`.  
4. Known/satisfied evidence is not re-asked.  
5. ZUS / Insurance / A1 / Delegation / Legalization never appear in PEM-1 `required_actions`.  
6. `start_allowed` never creates Started / never emits physical-start event.  
7. ESO-5 physical confirm is impossible without `start_allowed=true`.  
8. Replay / idempotency of evaluate/apply.  
9. Non-PEM-1 context does not silently pass as PEM-1 (`unsupported_context`).  
10. No override path yields `start_allowed=true` without evidence/exception satisfaction.

### 6. Non-PEM-1 → `unsupported_context`

Do **not** reuse ordinary business `blocked` for “this policy does not apply.”

| Decision | Meaning |
|----------|---------|
| `unsupported_context` | `employment_start_allowed.v1` has **no authority** for this employment context (e.g. third-country international driver). Person may still be employable under a future PEM-N contract. |
| `blocked` | PEM-1 context applies, but hard preconditions fail (e.g. no Employee, reuse/gate violation inside PEM-1). |
| `missing` | PEM-1 applies; required pre-Start items outstanding. |

Future PEM-2 / PEM-3 route via **policy selection**, not operator bypasses.

---

## Input / output (frozen)

### Input

| Input | Role |
|-------|------|
| `employee_id` | **Required** — Employee already minted |
| Employment context | Must match PEM-1 axes or → `unsupported_context` |
| Contract / Medical / BHP evidence views | From existing authorities + structured facts |
| Exception resolutions | Allowlisted typed facts only |
| Resolution patch | Minimal evidence bind / exception for **current** `primary_item` only |

### Output

`policy_id` MUST be `employment_start_allowed.v1`.

| Decision | Meaning |
|----------|---------|
| `start_allowed` | All applicable PEM-1 pre-Start items satisfied → ESO-5 may accept confirm |
| `missing` | Applicable items outstanding (`active_missing` / one `primary_item`) |
| `blocked` | PEM-1 applies but hard preconditions fail |
| `unsupported_context` | Policy has no authority for this context (not a business “cannot employ” verdict) |
| `rejected_patch` | Empty/invalid patch when input required, or non-allowlisted exception |

Every decision MUST include:

- `start_allowed` — `true` only when decision is `start_allowed`  
- `required_actions` — PEM-1 applicable set only  
- `active_missing` — unsatisfied applicable items only  
- `primary_item` — one next step when `missing`  
- `started=false`  
- `employee_id` present  
- `employee_minted_by_this_policy=false`  
- `zus_required_for_start=false`  
- `manual_override=false` (always)  
- `context_policy` — e.g. `PEM-1` or null when unsupported  

### Checklist ban

MUST NOT emit A1, delegacja, legalization, ZUS registration, or insurance filing as `start_allowed` requirements for PEM-1.

---

## PEM-1 required-actions table (frozen)

| Code | Kind | Satisfied when |
|------|------|----------------|
| `written_employment_contract_or_confirmation` | evidence | Structured proof of written `umowa o pracę` **or** written confirmation of parties, type, and terms (document row alone insufficient) |
| `occupational_medical_fit_for_post` | evidence | Structured valid medical conclusion for **this post + working conditions** bound to Employee (no PEM-1 medical exception codes at Accept) |
| `introductory_bhp_before_admit` | evidence / exception | Structured completion of introductory BHP, **or** allowlisted `bhp_successive_same_employer_same_post` with required facts |

Applicability: derive from employment/post context — not a static dump on every Employee.

---

## Write authority

| May | Must not |
|-----|----------|
| Evaluate/apply for `employee_id` on HR handoff host | Create a parallel admit-to-work UI/workflow |
| Bind existing document/training authorities + structured facts | Create a new evidence store |
| Accept only allowlisted typed exceptions | Generic `exception=true` or “Allow anyway” |
| Emit `start_allowed=true` when complete | Mint Employee; set Started; auto Confirm ESO-5 |
| Return `unsupported_context` for non-PEM-1 | Pretend non-PEM-1 is business-`blocked` employability failure |
| Stay LLM-OFF | Let AI decide admit-to-work |

---

## Non-goals

- Runtime / HTTP / UI in this Accept (inventory next).  
- Freezing concrete API paths before employee/handoff API inventory.  
- Expanding ESO-4 Formalize thin table.  
- ZUS / Insurance inside `start_allowed`.  
- A1 / posting / third-country PEM-N (separate contracts).  
- Full Spine Gate.  
- Replacing ESO-5 human confirm.  
- ePUAP / Płatnik integrations.  
- Encoding every statutory medical/BHP exception.

---

## Acceptance record

| Criterion | Result |
|-----------|--------|
| Operator question frozen | **PASS** |
| Hard locks frozen (incl. no override, document≠satisfied, Employee-first) | **PASS** |
| Host = handoff / authority = Employee | **PASS** |
| Evidence binding to existing authorities | **PASS** |
| Typed exception model + initial BHP allowlist | **PASS** |
| Mint timing frozen; ESO-5 mint = legacy | **PASS** |
| `employment-start-allowed-gate` proofs listed | **PASS** |
| `unsupported_context` for non-PEM-1 | **PASS** |
| I/O + required-actions frozen | **PASS** |
| Runtime required for this Accept | **NO** |

**Accepted** 2026-09-13 as L2 contract for PEM-1 admit-to-work.

---

## Next (after this Accept)

1. **Inventory (done as L3):** [`../../analysis/employment-start-allowed-runtime-inventory.md`](../../analysis/employment-start-allowed-runtime-inventory.md) @ `466016b6`.  
2. **Adaptation design (Accepted):** [`../../analysis/employment-start-allowed-adaptation-design.md`](../../analysis/employment-start-allowed-adaptation-design.md) — normalized views; derived `start_allowed`; narrow exceptions.  
3. **Runtime slice 1 OPEN:** [`../tasks/employment-start-allowed-runtime-foundation.md`](../tasks/employment-start-allowed-runtime-foundation.md) — machine foundation only. Full Spine **NOT PASS**.
