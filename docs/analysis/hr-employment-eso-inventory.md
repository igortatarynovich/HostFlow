# HR / Employment vs ESO-1…5 — inventory

**Status:** research draft (L3)  
**Date:** 2026-09-13  
**Trusted base:** `feat/eso5-started-hr-binding` (from `feat/eso4-formalize-hr-binding` @ `754c1bd2` / Formalize PASS `68762f13`)  
**Parent brief:** [`../specs/tasks/employment-spine-orchestrator-v1.md`](../specs/tasks/employment-spine-orchestrator-v1.md)  
**Does not amend:** L0 · ADR-042 decision · Recruitment Architecture CLOSED · Full Spine Gate STOP  
**Not SoT:** this file is L3 implementation context. Contracts remain `docs/specs/architecture/employment-*.md` + `early-employability.md`.

> Inventory of **what already exists** after Recruitment Architecture CLOSED.  
> Does **not** claim Full Spine PASS. Does **not** reopen Recruitment.

---

## Verdict

| Layer | ESO-1…5 |
|-------|---------|
| Contracts (SoT) | **PASS / Accepted** for all five |
| Backend reference + orchestrator + named CI gate + HTTP | **PASS** (machine complete; ESO-5 merged [#357](https://github.com/igortatarynovich/HostFlow/pull/357) / `0d256ba8`, ancestor of tip) |
| Operator UI on HR host | **ESO-1 PASS** @ `b6735b9b` / `04f31a74`; **ESO-2+3 Decision Surface PASS** @ `fb61a7b1`; **ESO-4 Formalize HR Binding PASS** @ `68762f13`; **ESO-5 Started HR Binding** — **in progress** on `feat/eso5-started-hr-binding` (not PASS-stamped yet) |
| Existing HR UI | Legacy review collapsed secondary only — **not** the Employment happy path |

Product implication: Accept + Decision Surface + Formalize + Started (binding) are hosted on `/app/hr/handoffs/:id`. Full product spine remains **NOT PASS** until ESO-5 UI gate + Full Spine Gate.

---

## Gap matrix

| Slice | SoT | Backend | HTTP | Named CI | FE surface | Class |
|-------|-----|---------|------|----------|------------|-------|
| **ESO-1** Accept Policy | `employment-accept-policy.md` · `employment_accept_policy.v1` | `employment_accept_policy.py` · `employment_accept_orchestrator.py` | `POST /handoffs/{id}/employment-accept-policy` | `eso1-accept-policy-gate` | **PASS** — `HrEmploymentAcceptPanel` on `/app/hr/handoffs/:id` | contract PASS / UI PASS |
| **ESO-2** Early Employability | `early-employability.md` · `early_employability.v1` | `early_employability.py` · orchestrator | `POST /handoffs/{id}/early-employability` | `eso2-early-employability-gate` | **PASS** — shared `HrEmploymentDecisionSurface` (with ESO-3) | contract PASS / UI PASS |
| **ESO-3** Missing Resolution | `employment-missing-resolution.md` · `employment_missing_resolution.v1` | reference + orchestrator | `POST /handoffs/{id}/employment-missing-resolution` | `eso3-missing-resolution-gate` | **PASS** — same Decision Surface; resolve → auto re-eval | contract PASS / UI PASS |
| **ESO-4** Formalize | `employment-formalize.md` · `employment_formalize.v1` | reference + orchestrator | `POST /handoffs/{id}/employment-formalize` | `eso4-formalize-gate` | **PASS** — `HrEmploymentFormalizePanel` @ `68762f13` (ready_to_create_employee; no Employee mint) | contract PASS / UI PASS |
| **ESO-5** Started | `employment-started.md` · `employment_started.v1` | reference + orchestrator | `POST /handoffs/{id}/employment-started` | `eso5-started-gate` | **IN PROGRESS** — `HrEmploymentStartedPanel` on `/app/hr/handoffs/:id` (`feat/eso5-started-hr-binding`; not PASS-stamped) | contract PASS / UI binding |

Frontend clients: ESO-1…5 endpoints wired from `hrWorkspace.ts` on the handoff case. ESO-5 UI not PASS-stamped.

---

## Package receive → Started (operator path today)

| Step | Machine | Operator UI today |
|------|---------|-------------------|
| Transfer / package receive | RSO create handoff `destination=internal_hr` | Candidate Transfer; toast; no auto-open prepared HR case |
| Accept / init | ESO-1 `employment-accept-policy` | **PASS** — auto policy on `/app/hr/handoffs/:id` (no ritual Accept) |
| Employability | ESO-2 | **PASS** — Decision Surface (`employable` / `blocked` / `insufficient_facts`) |
| Employment missing | ESO-3 | **PASS** — one current gap → resolve → auto re-eval on same surface |
| Formalize | ESO-4 → `ready_to_create_employee` | **PASS** @ `68762f13` — context formal action → complete; no Employee / Started CTA |
| Employee / Started | ESO-5 may mint + confirm start | **IN PROGRESS** — Started surface on same host after `ready_to_create_employee=true`; terminal on handoff (no employee-card redirect) |

---

## Existing HR host (keep; do not replace)

| Surface | Route / API | Note |
|---------|-------------|------|
| HR Inbox | `/app/hr/inbox` · `GET /hr/handoffs/*` | Package inbox — valid host entry |
| HR Handoff case | `/app/hr/handoffs/:id` | **Host** for ESO-1…5 |
| HR Review / approve | `…/hr-review/*` | Legacy parallel — must not become ESO happy path |
| Employees / dossier | `/app/hr/employees/:id` | Post-employee chrome |
| `workspace.module.hr.employment` | Registry → `modules/hr/contributions/employment` | Renderer **missing** (`src/modules/hr` absent) — do not invent a third host |

---

## Recommended sequence (after this inventory)

1. **ESO-1 HR host binding** — **PASS** @ `b6735b9b` / `04f31a74`.  
2. **ESO-2 + ESO-3 Employment Decision Surface** — **PASS** @ `fb61a7b1`.  
3. **ESO-4 Formalize HR Binding** — **PASS** @ `68762f13` / [#371](https://github.com/igortatarynovich/HostFlow/pull/371).  
4. **ESO-5 Started** HR binding on the same host — **in progress** (`feat/eso5-started-hr-binding`).  
5. New Full Spine Gate (three-host) — **only after** ESO-5 PASS; **not** a retune of the withdrawn one-card gate.

Hard locks: no Recruitment reopen; no Application-hosted Formalize/Started; no Full Spine PASS claim from inventory alone.

---

## Provenance note — #370 `qa-static` (2026-09-13)

`frontend-static-qa` / `qa-static` on [#370](https://github.com/igortatarynovich/HostFlow/pull/370) fails on SPA path literals:

`backend/app/reference/requirement_policy_parallel_authority_retirement.py` → `'/app/settings/requirement-policy'`

**Provenance:** file exists on base `feat/eso4-formalize` @ `04f31a74`; **not** in #370 diff (`fb61a7b1` / `87070907` only touch Decision Surface FE + stamps). Same failure observed on `feat/eso4-formalize` CI and closed [#369](https://github.com/igortatarynovich/HostFlow/pull/369).

**Decision:** treat as **baseline noise on ESO machine stack base** — do **not** pull a spa-path fix into ESO-4 Formalize HR binding. Repair remains a separate concern on the ESO base / RPM path if product wants green `qa-static` before merge.
