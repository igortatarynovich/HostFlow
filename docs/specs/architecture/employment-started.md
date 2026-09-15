# Employment started

**Status:** **Accepted** (L2 contract — Employment Started Gate / ESO-5)  
**Date:** 2026-09-09  
**Trusted base:** `feat/eso4-formalize` @ `3dc8735b` (stacks on ESO-4 → ESO-3 → ESO-2 → ESO-1)  
**Related:** [`employment-formalize.md`](employment-formalize.md) · [`employment-missing-resolution.md`](employment-missing-resolution.md) · [`../tasks/employment-spine-orchestrator-v1.md`](../tasks/employment-spine-orchestrator-v1.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02**. Does not rewrite L0. Does not treat `workforce_employee_created` or ESO-1 case-accept `employment_started` as physical start.

> This file is the **SoT** for confirming **physical first day at work** after Employee is allowed / exists.  
> Machine copy: `employment_started.v1` in `backend/app/reference/employment_started.py`.  
> Runtime: `backend/app/services/employment_started_orchestrator.py`.  
> Gate tests: `backend/tests/platform/test_employment_started_gate.py`.  
> Closes the Employment spine: **Employee → Started**. Not an HR employee card. Not Formalize.

---

## Operator question (one)

Given a handoff that may already have an **Employee** (or `ready_to_create_employee`), plus employment context, **has this person actually started work** — and if confirming, with which **start date + employment context** — without treating Employee create or formalization complete as Started?

No second question is this contract. ESO-1 audit `employment_started` means Employment **accepted the case**, not that the person walked in.

---

## Three acceptance gates (bind every change)

1. **RSO does not know how to employ.** Started is Employment-owned. Recruitment Transfer must not confirm start.  
2. **ESO does not re-ask Recruitment.** Package `target_work` / identity already on the handoff is reused. Known start date and employment context are **not** re-collected.  
3. **Operator does not service the boundary.** Confirming start is one explicit fact (`Подтвердить выход`), not a second onboarding form. If date/context are already known reliably, confirm without re-asking.

---

## Hard locks

| Lock | Meaning |
|------|---------|
| **Employee created ≠ Started** | `workforce_employees` row (or `employee_created=true`) is **not** physical start. |
| **Formalize complete ≠ Started** | `ready_to_create_employee` / `formalization_complete` **must not** auto-set Started. |
| **Explicit confirmable fact** | Started requires **start date + employment context**, then an explicit confirm. |
| **Audit-able** | First successful Started emits **one** audit event (`employee_physical_start`). Distinct from ESO-1 `employment_started` (case accept). |
| **Idempotent** | Re-confirm with the same date/context returns `already_started` and **must not** emit a second start event. |
| **Known facts** | If start date and/or context are already known reliably, omit them from `active_missing`. |
| **Spine close** | A successful Started result has **Employee present** and **`started=true`**. |

---

## Input / output (frozen)

### Input

| Input | Role |
|-------|------|
| `ready_to_create_employee` | ESO-4 allow-create diagnostic. **PEM-1 Slice 4:** Confirm does **not** mint from this flag. |
| Existing `employee_id` | Required for Confirm. Materialized via Formalize→ensure (ESA2). **Does not** imply Started. |
| Employment context | Country + employer and/or vacancy (reuse package `target_work`). |
| Known start date | Package `target_work.start_date` / planned start / prior stored fact — reuse, do not re-ask. |
| Start confirmation (apply) | Explicit confirm. May omit date/context when those facts are already known. |
| Prior start event | Stored physical-start fact for idempotency / conflict. |

### Output

`policy_id` MUST be `employment_started.v1`.

| Decision | Meaning |
|----------|---------|
| `started` | First explicit physical-start confirm; **`start_event_emitted=true`**. |
| `already_started` | Same start date + context already recorded; **`start_event_emitted=false`**, `idempotent_replay=true`. |
| `not_started` | Employee exists; start not confirmed (or admit-to-work still missing). |
| `blocked` | Not allowed to create Employee and none exists; or start-date/context **conflict** with an existing start. |
| `rejected_confirm` | Confirm required but missing/invalid when facts were not yet known. |

Every decision MUST include:

- `employee_created` — Employee exists (input). **Never** implies `started`. Confirm must not mint.  
- `start_allowed` — admit-to-work from `employment_start_allowed.v1` (Slice 4). First Confirm requires `true`.  
- `started` — physical start confirmed (`true` only for `started` / `already_started`).  
- `start_date` — ISO date when known.  
- `employment_context` — normalized country + employer/vacancy.  
- `active_missing` — only unknown date, incomplete context, or the confirm action itself.  
- `start_event_emitted` — `true` **only** on the first Started transition.  
- `idempotent_replay` — `true` only on `already_started`.  
- `formalization_complete_implies_started=false`  
- `employee_created_implies_started=false`  

### Known-fact reuse

ESO-5 **MUST NOT** re-ask:

- start date already on package `target_work` (`start_date` / `planned_start_date` / `first_work_date`) or on a prior stored physical-start fact;  
- employment country / employer_id / vacancy_id already on package `target_work` or provided context.

When those facts are present, `active_missing` contains at most `confirm_physical_start` (until confirmed). After Started, `active_missing` is empty.

### Determinism

Start decision is **LLM-OFF**. AI must not decide `started`.

### Employee mint (retired on Confirm — Slice 4)

Confirm **must not** mint Employee. If no Employee exists → `blocked` / `employee_required`.  
Mint path for PEM-1 = Formalize authoritative apply → `ensure_employee_after_formalize_apply` only.

### Admit-to-work (Slice 4)

First physical Confirm requires `start_allowed=true` from `employment_start_allowed.v1`.  
Idempotent `already_started` does **not** re-require admit. `start_allowed=true` does **not** auto-Confirm Started.

Forbidden:

```text
Confirm → handoff_from_candidate (mint-on-confirm)
Confirm when start_allowed=false
```

---

## Write authority

| May | Must not |
|-----|----------|
| Confirm physical start when Employee exists and `start_allowed=true` | Mint Employee inside Confirm |
| Reuse known date/context; skip re-ask | Confirm when `start_allowed=false` |
| Emit one `employee_physical_start` audit | Auto-start because Employee exists or Formalize complete |
| Return `already_started` on identical replay | Overwrite an existing start with a different date silently |

---

## Non-goals

- HR employee card / workforce profile chrome.  
- Replacing ESO-1 case-accept audit `employment_started`.  
- ADR-017 ZUS / post-hire satellites.  
- Full Legalization Engine.  
- Mapping Authority.  
- Recruitment Transfer calling this API.

---

## Completion of ESO-5

**PASS** when this document + `employment_started.v1` + gate tests exist, the ESO brief names Started, and HostFlow can answer **started / already_started / not_started / blocked** with an explicit confirmable start date + employment context — **without** auto-start from Employee create or formalize, **without** a second start event on replay, with first Confirm requiring `start_allowed=true` (Slice 4), and with the spine closed as **Employee → Started**. Slice 4 enforcement brief: [`../tasks/employment-start-allowed-eso5-enforcement.md`](../tasks/employment-start-allowed-eso5-enforcement.md) (**PASS**). Full Spine remains a separate gate.
