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
| `ready_to_create_employee` | ESO-4 allow-create (or equivalent formalize complete). Required to **mint** Employee if none exists. |
| Existing `employee_id` | If already materialized (legacy accept path, delayed-HR approve, prior apply). **Does not** imply Started. |
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
| `not_started` | Employee exists or may be minted; start not confirmed. |
| `blocked` | Not allowed to create Employee and none exists; or start-date/context **conflict** with an existing start. |
| `rejected_confirm` | Confirm required but missing/invalid when facts were not yet known. |

Every decision MUST include:

- `employee_created` — Employee exists (input) or this apply **mints** (when allowed). **Never** implies `started`.  
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

### Employee mint (distinct fact)

If no Employee exists and `ready_to_create_employee=true`, apply **may mint** Employee (`mint_employee=true`). That write **must leave `started=false`** unless the same apply also carries an explicit start confirmation. Mint is not Started.

---

## Write authority

| May | Must not |
|-----|----------|
| Mint Employee when ESO-4 allows and none exists | Treat mint / formalize complete as Started |
| Confirm physical start with date + context | Auto-start because Employee exists |
| Reuse known date/context; skip re-ask | Re-ask package `target_work` / known start date |
| Emit one `employee_physical_start` audit | Emit a second start event on re-confirm |
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

**PASS** when this document + `employment_started.v1` + gate tests exist, the ESO brief names Started, and HostFlow can answer **started / already_started / not_started / blocked** with an explicit confirmable start date + employment context — **without** auto-start from Employee create or formalize, **without** a second start event on replay, and with the spine closed as **Employee → Started**.
