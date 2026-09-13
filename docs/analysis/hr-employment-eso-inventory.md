# HR / Employment vs ESO-1…5 — inventory

**Status:** research draft  
**Date:** 2026-09-12  
**Trusted base:** `feat/eso4-formalize` @ `f4b81641`  
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
| Operator UI on HR host | **ESO-1 PASS**; **ESO-2+3 Decision Surface (this slice)**; ESO-4…5 still **MISSING** |
| Existing HR UI | Legacy review collapsed secondary only — **not** the Employment happy path |

Product implication: backend Employment spine is ready; HR chrome does not host it. Full product spine remains **NOT PASS / BLOCKED BY HR UI**.

---

## Gap matrix

| Slice | SoT | Backend | HTTP | Named CI | FE surface | Class |
|-------|-----|---------|------|----------|------------|-------|
| **ESO-1** Accept Policy | `employment-accept-policy.md` · `employment_accept_policy.v1` | `employment_accept_policy.py` · `employment_accept_orchestrator.py` | `POST /handoffs/{id}/employment-accept-policy` | `eso1-accept-policy-gate` | **MISSING** — ritual «Take into HR review» / raw `accept` | contract PASS / UI MISSING |
| **ESO-2** Early Employability | `early-employability.md` · `early_employability.v1` | `early_employability.py` · orchestrator | `POST /handoffs/{id}/early-employability` | `eso2-early-employability-gate` | **MISSING** | contract PASS / UI MISSING |
| **ESO-3** Missing Resolution | `employment-missing-resolution.md` · `employment_missing_resolution.v1` | reference + orchestrator | `POST /handoffs/{id}/employment-missing-resolution` | `eso3-missing-resolution-gate` | **MISSING** | contract PASS / UI MISSING |
| **ESO-4** Formalize | `employment-formalize.md` · `employment_formalize.v1` | reference + orchestrator | `POST /handoffs/{id}/employment-formalize` | `eso4-formalize-gate` | **MISSING** (correctly off Application per ADR-042) | contract PASS / UI MISSING |
| **ESO-5** Started | `employment-started.md` · `employment_started.v1` | reference + orchestrator | `POST /handoffs/{id}/employment-started` | `eso5-started-gate` | **MISSING** | contract PASS / UI MISSING |

Zero frontend clients call the five ESO endpoints (inventory date).

---

## Package receive → Started (operator path today)

| Step | Machine | Operator UI today |
|------|---------|-------------------|
| Transfer / package receive | RSO create handoff `destination=internal_hr` | Candidate Transfer; toast; no auto-open prepared HR case |
| Accept / init | ESO-1 `employment-accept-policy` | Ritual **Take into HR review** → `acceptHandoff` |
| Employability | ESO-2 | **MISSING** (legacy doc verification / eligibility chrome) |
| Employment missing | ESO-3 | **MISSING** (hr-review checklist / missing-docs queues) |
| Formalize | ESO-4 → `ready_to_create_employee` | **MISSING** |
| Employee / Started | ESO-5 may mint + confirm start | Employee dossier after workforce id; physical start **MISSING** |

---

## Existing HR host (keep; do not replace)

| Surface | Route / API | Note |
|---------|-------------|------|
| HR Inbox | `/app/hr/inbox` · `GET /hr/handoffs/*` | Package inbox — valid host entry |
| HR Handoff case | `/app/hr/handoffs/:id` | **Chosen host** for ESO-1 binding |
| HR Review / approve | `…/hr-review/*` | Legacy parallel — must not become ESO happy path |
| Employees / dossier | `/app/hr/employees/:id` | Post-employee chrome |
| `workspace.module.hr.employment` | Registry → `modules/hr/contributions/employment` | Renderer **missing** (`src/modules/hr` absent) — do not invent a third host |

---

## Recommended sequence (after this inventory)

1. **ESO-1 HR host binding** on existing `/app/hr/handoffs/:id` — policy auto_accept or concrete blocker; no ritual Accept.  
2. **ESO-2 + ESO-3** as one Employment decision surface (avoid an extra UI step between employability and missing resolve).  
3. **ESO-4 Formalize** → **ESO-5 Started**.  
4. New Full Spine Gate (three-host) — **not** a retune of the withdrawn one-card gate.

Hard locks: no Recruitment reopen; no Application-hosted Formalize/Started; no Full Spine PASS claim from inventory alone.
