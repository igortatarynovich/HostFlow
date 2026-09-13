# Employment start_allowed — runtime inventory (PEM-1)

**Status:** research draft (L3) — **inventory only**; not a build plan; runtime **not opened**  
**Date:** 2026-09-13  
**Depends on:** [`../specs/architecture/employment-start-allowed.md`](../specs/architecture/employment-start-allowed.md) (**Accepted**) · [`production-employment-minimum.md`](production-employment-minimum.md) (**PEM-1 Accepted**) · [`employment-formalization-coverage-audit.md`](employment-formalization-coverage-audit.md) @ `b88a6168`  
**Observation base:** current tree `integration/release-product-a-b` + ESO feat tips (`feat/eso4-formalize*`, `feat/eso5-started*`) via `git show`  
**Does not amend:** L0 · Accepted contracts · Full Spine Gate  
**Code:** closed — this file does **not** authorize `employment_start_allowed.v1` runtime.

> Criterion: **do not create a new authority** until an existing one is proven unusable.  
> Output: per-domain **reuse as-is / adapt / missing authority** — not an implementation backlog.

---

## Short verdict (five areas)

| Area | Verdict | One line |
|------|---------|----------|
| **Employee mint** | **adapt** | Canonical primitive = `handoff_from_candidate`; call after ESO-4, **before** `start_allowed`; retire ESO-5 mint-on-confirm as PEM-1 legacy |
| **Contract proof** | **adapt** | Reuse Documents `employment_contract` / `umowa_o_prace` + structured meta; **not** draft preview; **not** ESO-4 basis ack |
| **Medical** | **adapt** | Reuse `medical_certificate` + expiry / verified dates; still lack fit-for-**post/conditions** structured SoT |
| **BHP** | **adapt** | Reuse `bhp` / `szkolenia_BHP` + `training_date`; lack introductory/applicability semantics |
| **Exception resolution** | **missing authority** | No typed `requirement_code`+`exception_code`+facts Employee store; only free-text waive/override **patterns** to adapt |

**No area is reuse as-is** for PEM-1 `start_allowed` evaluator rules (`document exists ≠ satisfied`).  
**No new parallel mint primitive** required — compose existing `handoff_from_candidate`.  
**One missing authority:** typed audited exception resolution for allowlisted codes (esp. `bhp_successive_same_employer_same_post`).

Full Spine remains **NOT PASS**. Runtime `employment_start_allowed.v1` stays **closed** until a post-inventory slice is explicitly opened.

---

## Inventory matrix

| Domain | Existing authority | Write path | Read path | Structured facts | Audit | Reusable? | Gap |
|--------|-------------------|------------|-----------|------------------|-------|-----------|-----|
| **Employee mint** | `handoff_from_candidate` (+ sibling `create_employee` for manual HR) in `workforce_employees.py` | Accept → `accept_internal_hr_handoff`; delayed approve → `approve_employment_for_handoff`; API `POST …/from-candidate/{id}`; manual `POST /workforce/employees`; **[feat]** ESO-5 `confirm_employment_started_for_handoff` may call `handoff_from_candidate` | Employee by id / by `candidate_id` (idempotent) | Employee row + HR profile bundle + optional `meta.internal_hr_handoff_id` | Accept: `handoff_accepted`; from-candidate API: `workforce.handoff_from_candidate` activity; manual: lifecycle `employee_hired`; ESO-5 Started: `employee_physical_start` (not mint-specific). **No** `emit_security_event*` on mint | **adapt** (reuse primitive; change **when** called) | Multiple callers; ESO-5 mint-on-confirm conflicts with PEM-1 order; ESO-5 mint skips `ensure_hr_operational_context` / checklist that accept path runs |
| **Contract proof** | Documents Hub `employment_contract` / `umowa_o_prace`; employee `DocumentEntityLink` | Hub upload/meta; HR doc links via `ensure_hr_document_links`; draft-only `contract_generation.generate_contract_draft_preview` | Platform documents API; expected-doc `contract` (`blocks_employment=true`) | Meta `umowa_o_prace.json`: `employer_name`, `signed_at`, `start_at`, optional number/position/end; merge log = `draft_preview` only | Merge log + `workforce.contract_draft_preview`; ESO-4 `confirm_employment_contract_basis` is ack in formalize payload — **not** written-umowa SoT | **adapt** | No first-class “written confirmation of terms” type; draft ≠ proof; evaluator must require structured signed/confirmation facts, not row existence |
| **Medical** | Hub `medical_certificate` (+ aliases); HR verified field `exam_valid_until`; expiry engine | Hub create/meta; HR verification / verified-fields upsert; handoff activity stub `medical_examination` (title only) | Docs + expiry projection; expected-doc `medical_exam` (`blocks_employment=true`); eligibility packs | Meta: exam/issue date, `expires_at`, clinic/doctor/number; verified `exam_valid_until`; **no** fit/unfit + post/conditions binding | Doc verification / verified-field activities; waive is free-text | **adapt** | Missing occupational fit-for-**post + working conditions** structured fact; free-text waive ≠ PEM-1 medical exception (none allowlisted) |
| **BHP** | Hub `bhp` / `bhp_instruction` / `szkolenia_BHP` meta | Hub upload + `szkolenia_BHP.json` meta; scanner preset | Expected-doc `bhp` with **`blocks_employment=false`**; not in HR `CHECKLIST_ITEM_CODES`; weak/absent in platform registry vs config aliases | Meta: `training_date` (required), optional `training_type` / `provider` / `expires_at` | Document row only; no dedicated BHP completion event | **adapt** | No introductory-vs-periodic; no applicability to employer/post; not employment-blocking in expected-doc today |
| **Exception resolution** | **No** PEM-1 typed exception SoT. Closest: HR `waive_document_requirement` (`reason`+actor+time); verified-field `overridden`; recruitment `candidate_pipeline_overrides` / `candidate_evidence` variants; tenant requirement overrides | Waive/override APIs above | Review JSON / override tables | Free-text reason or recruitment-scoped codes — **not** `exception_code` allowlist + required facts for Employee admit | Activity / pipeline audit events (recruitment) | **missing authority** (patterns **adapt**) | Need Employee-scoped audited record: `requirement_code` + allowlisted `exception_code` + facts + actor + timestamp; `bhp_successive_same_employer_same_post` **absent** |

---

## 1. Employee mint path (detail)

### Canonical primitives (only two)

| Primitive | File | Role |
|-----------|------|------|
| `handoff_from_candidate` | `backend/app/services/workforce_employees.py` | **Idempotent** Candidate→Employee; seeds HR bundle + ZUS auto-task; asserts recruitment/HR module access |
| `create_employee` | same | Manual HR create (no candidate required); same bundle/ZUS seed |

Stage-driven mint is **dead** (`should_workforce_handoff_on_stage_change` → always `False`).

### Who calls mint today

| Caller | When | Before ESO-5 physical start? |
|--------|------|------------------------------|
| `accept_internal_hr_handoff` (unless `delayed_hr_workforce_creation`) | Handoff accept | **Yes** |
| `approve_employment_for_handoff` | Delayed HR approve | **Yes** |
| `POST /workforce/employees/from-candidate/{id}` | Direct API | **Yes** |
| `POST /workforce/employees` | Manual HR UI | **Yes** |
| **[feat]** `confirm_employment_started_for_handoff` | ESO-5 confirm / `ensure_employee` | **At confirm** (or ensure without Started) |

ESO-4 Formalize (**feat**): emits `ready_to_create_employee` — **never** mints.

### Preconditions (summary)

- `handoff_from_candidate`: module asserts + idempotent existing employee.  
- Accept path: handoff `pending_review` + internal_hr.  
- Approve path: HR review / can-approve.  
- Manual create: trust write + HR module — **no** ESO-4 gate.  
- ESO-5 mint: `ready_to_create_employee` (or existing employee) + start facts for Started.

### ESO-5 mint → legacy for PEM-1

Accepted spine: `ESO-4 → mint Employee → start_allowed → ESO-5`.

Therefore ESO-5 `handoff_from_candidate` on confirm is **transitional legacy composition**. Safe retirement shape (product, not this inventory’s implementation):

1. After ESO-4 allow-create, mint via **`handoff_from_candidate`** (same primitive as accept/approve) **before** `start_allowed` evaluate.  
2. Prefer also `ensure_hr_operational_context` when minting from Employment spine (parity with accept path) — currently **missing** on ESO-5 mint.  
3. ESO-5 only confirms physical start when `start_allowed=true` and Employee already exists.  
4. Keep idempotency: if accept/approve already minted, ESO-5 must no-op mint.

### Mint side effects

| Effect | Present |
|--------|---------|
| HR profiles bundle (employment/payroll/ZUS/tax/insurance/compliance/eligibility) | Yes on both primitives |
| ZUS registration auto-task | Yes |
| HR operational context + checklist | Accept/approve wrappers **yes**; ESO-5 mint **no**; raw from-candidate API **no** |
| Security events on mint | **None found** |
| Physical-start audit | ESO-5 Started only — not mint |

### Mint verdict: **adapt**

Reuse `handoff_from_candidate` as the **single** Employment-spine mint authority after ESO-4. Do not invent a third create API. Adapt call timing + operational-context parity; mark ESO-5 mint-on-confirm legacy for PEM-1.

---

## 2. Evidence authorities (detail)

### Contract — **adapt**

- **SoT candidate:** Employee-linked hub document with type `employment_contract` / meta `umowa_o_prace` (`signed_at`, employer, dates).  
- **Not SoT:** `contract_draft_preview` merge log; ESO-4 `confirm_employment_contract_basis`.  
- **Gap:** structured “written confirmation of terms” path; evaluator rules that ignore bare uploads.

### Medical — **adapt**

- **SoT candidate:** Employee-linked `medical_certificate` + non-expired validity (`expires_at` / `exam_valid_until`).  
- **Gap:** conclusion of fitness for **specific post + working conditions**; no PEM-1 medical exception codes (correct per Accept).

### BHP — **adapt**

- **SoT candidate:** Employee-linked `bhp` / `szkolenia_BHP` with `training_date`.  
- **Gap:** introductory semantics, applicability, employment-blocking policy today is false in expected-docs; exception code absent.

### Exception — **missing authority**

- Closest patterns: HR requirement waive (`reason` only); verified-field override; recruitment pipeline overrides / `candidate_evidence` variants.  
- **None** store Employee admit allowlist `exception_code` + required facts for `bhp_successive_same_employer_same_post`.  
- Generic waive **must not** satisfy `start_allowed` (Accepted hard lock).  
- Creating typed exception resolution is justified **only** because no existing Employee-scoped authority meets the Accepted shape — still prefer extending an audited pattern over a greenfield “exceptions module” if inventory later finds a tighter fit during design.

---

## What this inventory does **not** do

- Open `employment_start_allowed.v1` runtime / HTTP / UI  
- Freeze API paths  
- Expand ESO-4 thin Formalize table  
- Schedule Full Spine Gate  
- Choose between “new exception table” vs “extend waive JSON” (that is post-inventory design, with **missing authority** already established)

---

## Next (after this inventory)

1. Keep runtime **closed**.  
2. Product/architecture choice only where verdict = **adapt** / **missing**:  
   - mint call site after ESO-4;  
   - Contract/Medical/BHP structured satisfaction rules on existing docs;  
   - minimal typed exception authority for allowlisted codes.  
3. Only then open a thin runtime slice + `employment-start-allowed-gate`.

---

## References

- Mint: `backend/app/services/workforce_employees.py`, `hr_acceptance_orchestrator.py`, `handoff.py`  
- ZUS seed: `workforce_zus_task_autocreate.sync_auto_tasks_after_employee_created`  
- Contract: `contract_generation.py`, `meta_schemas/umowa_o_prace.json`, `HrContractPreviewPanel.tsx`  
- Medical: `meta_schemas/medical_cert.json`, `hr_verified_field_catalog.py`, `hr_expected_documents.json`  
- BHP: `meta_schemas/szkolenia_BHP.json`, `hr_expected_documents.json` (`bhp`)  
- Waive pattern: `hr_document_verification.waive_document_requirement`  
- ESO-5 mint (feat): `employment_started_orchestrator.confirm_employment_started_for_handoff`
