# HR / Employment vs ESO-1…5 — inventory

**Status:** research draft (L3)  
**Date:** 2026-09-13  
**Trusted base:** `feat/eso2-eso3-employment-decision-surface` @ `fb61a7b1`  
**Parent brief:** [`../specs/tasks/employment-spine-orchestrator-v1.md`](../specs/tasks/employment-spine-orchestrator-v1.md)  
**Does not amend:** L0 · ADR-042 decision · Recruitment Architecture CLOSED · Full Spine Gate STOP  
**Not SoT:** this file is L3 implementation context. Contracts remain `docs/specs/architecture/employment-*.md` + `early-employability.md`.

> Inventory of **what already exists** after Recruitment Architecture CLOSED.  
> Does **not** claim Full Spine PASS. Does **not** schedule Formalize/Started UI. Does **not** reopen Recruitment.

---

## Verdict

| Layer | ESO-1…5 |
|-------|---------|
| Contracts (SoT) | **PASS / Accepted** for all five |
| Backend reference + orchestrator + named CI gate + HTTP | **PASS** (machine complete; ESO-5 merged [#357](https://github.com/igortatarynovich/HostFlow/pull/357) / `0d256ba8`, ancestor of tip) |
| Operator UI on HR host | **ESO-1 PASS** @ `b6735b9b` / `04f31a74`; **ESO-2+3 Decision Surface PASS** @ `fb61a7b1`; ESO-4…5 still **MISSING** |
| Existing HR UI | Legacy review collapsed secondary only — **not** the Employment happy path |

Product implication: Employment accept + Decision Surface are hosted on `/app/hr/handoffs/:id`. Full product spine remains **NOT PASS / BLOCKED BY HR UI** until Formalize + Started operator surfaces land.

---

## Gap matrix

| Slice | SoT | Backend | HTTP | Named CI | FE surface | Class |
|-------|-----|---------|------|----------|------------|-------|
| **ESO-1** Accept Policy | `employment-accept-policy.md` · `employment_accept_policy.v1` | `employment_accept_policy.py` · `employment_accept_orchestrator.py` | `POST /handoffs/{id}/employment-accept-policy` | `eso1-accept-policy-gate` | **PASS** — `HrEmploymentAcceptPanel` on `/app/hr/handoffs/:id` | contract PASS / UI PASS |
| **ESO-2** Early Employability | `early-employability.md` · `early_employability.v1` | `early_employability.py` · orchestrator | `POST /handoffs/{id}/early-employability` | `eso2-early-employability-gate` | **PASS** — shared `HrEmploymentDecisionSurface` (with ESO-3) | contract PASS / UI PASS |
| **ESO-3** Missing Resolution | `employment-missing-resolution.md` · `employment_missing_resolution.v1` | reference + orchestrator | `POST /handoffs/{id}/employment-missing-resolution` | `eso3-missing-resolution-gate` | **PASS** — same Decision Surface; resolve → auto re-eval | contract PASS / UI PASS |
| **ESO-4** Formalize | `employment-formalize.md` · `employment_formalize.v1` | reference + orchestrator | `POST /handoffs/{id}/employment-formalize` | `eso4-formalize-gate` | **MISSING** (correctly off Application per ADR-042) | contract PASS / UI MISSING |
| **ESO-5** Started | `employment-started.md` · `employment_started.v1` | reference + orchestrator | `POST /handoffs/{id}/employment-started` | `eso5-started-gate` | **MISSING** | contract PASS / UI MISSING |

Frontend clients: ESO-1…3 endpoints wired from `hrWorkspace.ts` on the handoff case. ESO-4…5 still unbound in UI.

---

## Package receive → Started (operator path today)

| Step | Machine | Operator UI today |
|------|---------|-------------------|
| Transfer / package receive | RSO create handoff `destination=internal_hr` | Candidate Transfer; toast; no auto-open prepared HR case |
| Accept / init | ESO-1 `employment-accept-policy` | **PASS** — auto policy on `/app/hr/handoffs/:id` (no ritual Accept) |
| Employability | ESO-2 | **PASS** — Decision Surface (`employable` / `blocked` / `insufficient_facts`) |
| Employment missing | ESO-3 | **PASS** — one current gap → resolve → auto re-eval on same surface |
| Formalize | ESO-4 → `ready_to_create_employee` | **MISSING** (employable stops at ready-for-Formalize) |
| Employee / Started | ESO-5 may mint + confirm start | Employee dossier after workforce id; physical start **MISSING** |

---

## Existing HR host (keep; do not replace)

| Surface | Route / API | Note |
|---------|-------------|------|
| HR Inbox | `/app/hr/inbox` · `GET /hr/handoffs/*` | Package inbox — valid host entry |
| HR Handoff case | `/app/hr/handoffs/:id` | **Host** for ESO-1 accept + ESO-2+3 Decision Surface |
| HR Review / approve | `…/hr-review/*` | Legacy parallel — must not become ESO happy path |
| Employees / dossier | `/app/hr/employees/:id` | Post-employee chrome |
| `workspace.module.hr.employment` | Registry → `modules/hr/contributions/employment` | Renderer **missing** (`src/modules/hr` absent) — do not invent a third host |

---

## Recommended sequence (after this inventory)

1. **ESO-1 HR host binding** — **PASS** @ `b6735b9b` / `04f31a74`.  
2. **ESO-2 + ESO-3 Employment Decision Surface** — **PASS** @ `fb61a7b1`.  
3. **ESO-4 Formalize** → **ESO-5 Started** HR bindings on the same host.  
4. New Full Spine Gate (three-host) — **not** a retune of the withdrawn one-card gate.

Hard locks: no Recruitment reopen; no Application-hosted Formalize/Started; no Full Spine PASS claim from inventory alone.
