# Recruitment Spine Orchestrator v1

**Status:** **RSO-2 in progress** (Fits → Handoff Gate) — RSO-1 Contract Gate **PASS**; see [ready-for-employment-contract.md](../architecture/ready-for-employment-contract.md).  
**Phase class:** product  
**Module owner:** **Recruitment** (independent of Employment / HR)  
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) · [Hiring workflow E2E](hiring-workflow-e2e.md) · [Recruitment → HR minimal handoff](recruitment-hr-minimal-handoff.md) · Architecture Rule 2 (no cross-module internal access — handoff via delivery contract only) · Strategy Lock (Operator Test / Zero-choice / Happy path short)  
**Sibling (Employment):** [Employment Spine Orchestrator v1](employment-spine-orchestrator-v1.md) — owns employability/legalization, formalize, Employee, Started  
**Contract SoT:** [Ready for employment contract](../architecture/ready-for-employment-contract.md) (`ready_for_employment.v1`)  
**Runtime:** `backend/app/modules/recruitment/services/ready_for_employment_orchestrator.py` · gate `backend/tests/platform/test_rso2_fits_handoff_gate.py` · CI `rso2-fits-handoff-gate`  
**Estimate:** 1 docs contract slice + feat slices for Recruitment rail only  

> Not Mapping Authority. Not Forms Publish. Not Employment / HR creating Employee from Recruitment.  
> Not “Recruitment continues until Started”. Not auto-accept handoff as a Recruitment side-effect.  
> Mapping Connect→Ready stays **parallel** and must not block this brief.

---

## Acceptance gates (every subsequent change)

1. **RSO does not know how to employ.** Terminal result = valid Ready for employment **handoff package** (`ready_for_employment.v1`).  
2. **ESO does not re-ask Recruitment.** Package facts/evidence are reused; only **employment missing** may be requested. *(Owned/enforced on Employment side — Recruitment must not emit employment doc shopping lists.)*  
3. **Operator does not service the boundary.** **Передать на трудоустройство** continues the same person; package emit, audit, owner switch, Employment init are internal.

Gate 2 failure mode to watch forever: citizenship twice, employer re-picked, documents re-uploaded. Domain boundary splits **responsibility**, not user-visible data.

Machine gate: `backend/tests/platform/test_ready_for_employment_contract_gate.py`.

---

## Critical boundary (do not blur)

**Recruitment** and **Employment / Hiring** are **two independent modules** and two processes.

| | Recruitment | Employment |
|---|-------------|------------|
| Ends when | Candidate **fits** and **Ready for employment contract** is fulfilled (handoff package emitted) | Person is **Started** (and economics later) |
| Owns | Application/context, Person resolution, duplicates, qualification, **recruitment missing** only, fits / not fits, **handoff package** | Accept handoff, **employment missing**, employability/legalization, contract/formalize, **Employee**, Start |
| Must not | Create Employee; collect “docs just in case” for Employment; own legalization SoT; auto-accept its own handoff | Re-ask recruitment qualification; invent a second intake workflow |

**Ready for employment is a contract between modules — not merely a candidate stage/status.**  
A status may *reflect* that the contract was emitted; the SoT is the **handoff package** + audit event that Recruitment completed and Employment started.

**User journey** may look continuous.  
**Ownership** stays separate: seamless handoff, not a merged orchestrator.

```text
Source → Application → Qualification → Recruitment decision
                    ↓
     Ready for employment  ← CONTRACT (handoff package), not “a status”
                    ↓
Employment case → requirements → legalization → contract → Employee → Started
```

Operator may see: **Передать на трудоустройство**.  
Inside: Recruitment emits package → Employment accepts under **Employment policy**.

### Universal HostFlow principle

**Seamless UX does not mean shared ownership.**  
Recruitment, Employment, HR, Legalization, Fleet, Finance may keep hard domain boundaries. Simplicity comes from the next module receiving all known context — never from forcing the operator to manually carry work across the boundary.

---

## Handoff package (Ready for employment contract)

Recruitment **guarantees** a concrete package. After emit, Recruitment’s job for this application is **done**.

| Field (logical) | Meaning |
|-----------------|--------|
| Person identity | Who (stable Person/Candidate id + identity facts used) |
| Target work | Which vacancy / employer / role they were selected for |
| Recruitment facts | Facts confirmed for **fit / qualification** only |
| Evidence / source | Provenance (Meta submission, docs, call outcomes, etc.) |
| Fits decision | Why Fits was accepted (decision + timestamp + actor) |
| Context refs | Application id, source id, tenant, recruiter as needed by delivery contract |

Employment treats this package as **input** and answers a **different** question:  
*What is required to lawfully and actually employ this person in this context?*

### Missing data split (hard)

| Kind | Owned by | Allowed contents |
|------|----------|------------------|
| **Recruitment missing** | Recruitment | Only what is required to decide Fits and assemble a **correct handoff package** |
| **Employment missing** | Employment | Everything required for employability, legalization, contract, formalize |

**Forbidden:** Recruitment collecting the full employment/legalization document set “just in case”. That is Employment leaking into the ATS.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After **Подходит**, the operator is forced through entity steps (Create candidate, vacancy bind, stage menus) and may be pulled into Employment/HR mechanics that Recruitment does not own — or Recruitment never emits a clear **Ready for employment contract**, only a fuzzy stage.

**Completion proof (named consumer):**  
Untrained operator on a Meta application with known vacancy: Call → **Подходит** → (only **recruitment missing** if needed) → **Передать на трудоустройство** — without Create candidate, vacancy bind, or stage picker. Exact duplicate attaches silently. A **handoff package** meeting the contract above is emitted; audit trail records **Recruitment completed**. Operator does **not** create Employee from Recruitment UI. Operator Test PASS on the **Recruitment** rail.

**False close (reject):** one mega-orchestrator that creates Employee from Recruitment; treating Ready for employment as only `stage=ready_for_handoff` without package contract; Recruitment gathering employment/legalization docs “на всякий случай”; treating `create_handoff + accept` as Recruitment logic; requiring the operator to re-enter known facts after handoff; no audit boundary between modules.

---

## Product language (Recruitment segment of the card)

One workspace card (shared surface is OK; **module context** must change at the boundary):

`Person · Employer/Vacancy · Role`

→ **Позвонить**  
→ **Подходит / Перезвонить / Не подходит** (one step; no-answer = Перезвонить)  
→ recruitment missing facts only (if needed)  
→ **Передать на трудоустройство**  

After the click: user is in **Employment** context (same person, no re-entry of known facts) — owned by Employment orchestrator, not by continuing Recruitment.

Internal call-result codes remain backend-only.

---

## Recruitment orchestrator contract

**Input intent:** `fits` (Подходит) on a recruitment application / intake work item.

**Pipeline (Recruitment-owned only):**

1. **resolve_context** — vacancy, employer, source, recruiter (zero-choice when known).  
2. **attach_or_create_person** — without “Create candidate” UI.  
3. **resolve_duplicate** — exact → silent attach; probable → minimal confirm; HR-lock policy as today.  
4. **qualify** — recruitment qualification for this vacancy/client.  
5. **evaluate_recruitment_missing** — only facts needed to **decide Fits and assemble the handoff package** (never the full employment/legalization set).  
6. **build_handoff_package** — fulfills the **Ready for employment contract** (see table above).  
7. **emit + return next_action** — e.g. ask recruitment missing · confirm probable duplicate · **offer_handoff** (`Передать на трудоустройство`) · not_fits. Emit must write an audit event: Recruitment completed for this application.

**Explicitly out of Recruitment return / ownership:**

- employability / legalization decision SoT  
- creating Employee  
- accepting handoff  
- Started confirm  
- payroll  

Employment may **expose a read facade** (e.g. preview blockers) that Recruitment UI can display **without** owning the SoT (Rule 2: facade/contract only). Recruitment must not write Employment internals.

### Handoff button

**Передать на трудоустройство** = Recruitment completes and emits handoff.  

Same-tenant auto-accept, if any, is **Employment module policy** after receiving the package — never “Recruitment creates Employee”.

---

## Ladder (Recruitment program only)

| Slice | Name | Gate | Depends |
|-------|------|------|---------|
| **RSO-1** | Recruitment orchestrator **contract** (this brief + package SoT) | **Recruitment Orchestrator Contract Gate** — **PASS** (`ready_for_employment.v1` + `test_ready_for_employment_contract_gate.py`) | — |
| **RSO-2** | Runtime `fits` → package → `offer_handoff` | **Fits → Handoff Gate** — no Create candidate / vacancy bind / stage menu on happy path | RSO-1 |
| **RSO-3** | Call triad + My Work (Recruitment card states) | **Call / My Work Gate** | RSO-2 (or FE parallel after contract types stable) |

**Not in this program (Employment brief):** early employability SoT, formalize gate, Employee create, Started. See [employment-spine-orchestrator-v1.md](employment-spine-orchestrator-v1.md).

Mapping Connect→Ready: **parallel**.

---

## Existing primitives (Recruitment consume)

| Step | Existing |
|------|----------|
| Context / vacancy | Meta ingest ads map / campaign target / `resolve_vacancy_for_lead_processing` |
| Person convert | `POST …/applications/{id}/process` |
| Duplicate | `resolve_lead_duplicate_match` / `duplicate_decision` |
| Call store | `POST …/call-result` |
| Handoff create | `create_handoff` — Recruitment may **create** pending handoff; **accept** is Employment |
| Package / missing | recruitment-package / RPM — narrow to **recruitment** missing for handoff readiness |

**DELETE_UI (Recruitment):** Create candidate, vacancy bind when known, assign UUID ritual, call enum, stage rail as primary path after Fits.  
**AUTO:** process/qualify/confirm vacancy when context known; exact duplicate attach.  
**BUILD:** Recruitment orchestrator + handoff package contract + card states through **offer_handoff**.

---

## Operator Test (RSO-2)

1. Meta work item, vacancy known.  
2. **Позвонить** → **Подходит**.  
3. Next: recruitment missing only if needed, then **Передать на трудоустройство**.  
4. Never Create candidate / Bind / stage picker.  
5. After handoff action, Employment context continues the person — Recruitment rail is done.

FAIL if Recruitment UI creates Employee or asks for zezwolenie type.

---

## Non-goals

- Employment / Legalization Decision Engine implementation (Employment program).  
- Merging Recruitment + HR into one module orchestrator.  
- Mapping Authority UX.  
- Work Surface mail/calendar.

---

## Next

1. **RSO-1 PASS** — package contract + three acceptance gates frozen.  
2. **RSO-2 in progress** — Fits auto-runs recruitment prep (`POST …/fits`); Transfer is explicit (`POST …/transfer-to-employment`); machine gate `test_rso2_fits_handoff_gate.py`.  
3. ESO-1 accept policy on [Employment Spine Orchestrator v1](employment-spine-orchestrator-v1.md) — must enforce gate 2 (no re-ask).

### RSO-2 runtime invariants (machine)

- **Fits** never creates handoff / Employee / Recruitment completed audit.  
- **Transfer** revalidates `ready_for_employment.v1` from current facts (no stale snapshot).  
- Successful Transfer → exactly one pending handoff (idempotent) + audit **Recruitment completed**.  
- Recruitment missing never includes employment/legalization shopping lists.

Canvas: `meta-to-started-target-journey` (visual; not L2 canon).
