# Recruitment Spine Orchestrator v1

**Status:** **RSO-1 Contract Gate PASS** (feat locked) — runtime = RSO-2; see [ready-for-employment-contract.md](../architecture/ready-for-employment-contract.md).  
**Phase class:** product  
**Module owner:** **Recruitment** (independent of Employment / HR)  
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) · [Hiring workflow E2E](hiring-workflow-e2e.md) · [Recruitment → HR minimal handoff](recruitment-hr-minimal-handoff.md) · Architecture Rule 2 (no cross-module internal access — handoff via delivery contract only) · Strategy Lock (Operator Test / Zero-choice / Happy path short)  
**Sibling (Employment):** [Employment Spine Orchestrator v1](employment-spine-orchestrator-v1.md) — owns employability/legalization, formalize, Employee, Started  
**Contract SoT:** [Ready for employment contract](../architecture/ready-for-employment-contract.md) (`ready_for_employment.v1`)  
**Estimate:** 1 docs contract slice + feat slices for Recruitment rail only  

> Not Mapping Authority. Not Forms Publish. Not Employment / HR creating Employee from Recruitment.  
> Not “Recruitment continues until Started”. Not auto-accept handoff as a Recruitment side-effect.  
> Mapping Connect→Ready stays **parallel** and must not block this brief.  
> **Host (ADR-042):** Fits on **Application** enters **Candidate**. Transfer is **not** the next verb after Fits. Ready for employment + **Передать** live on the Candidate. Employment after handoff is **HR**, not Application Workspace.

---

## Acceptance gates (every subsequent change)

1. **RSO does not know how to employ.** Terminal result = valid Ready for employment **handoff package** (`ready_for_employment.v1`).  
2. **ESO does not re-ask Recruitment.** Package facts/evidence are reused; only **employment missing** may be requested. *(Owned/enforced on Employment side — Recruitment must not emit employment doc shopping lists.)*  
3. **Operator does not service the boundary.** **Передать на трудоустройство** (on the Candidate, after Ready for employment) continues the same person into a prepared HR case; package emit, audit, owner switch, Employment init are internal.

Gate 2 failure mode to watch forever: citizenship twice, employer re-picked, documents re-uploaded. Domain boundary splits **responsibility**, not user-visible data.

Machine gate: `backend/tests/platform/test_ready_for_employment_contract_gate.py`.

---

## Critical boundary (do not blur)

**Recruitment** and **Employment / Hiring** are **two independent modules** and two processes.

| | Recruitment | Employment |
|---|-------------|------------|
| Ends when | **Ready for employment contract** is fulfilled on the **Candidate** (handoff package emitted). **Fits on an Application only enters Candidates** — it is not Recruitment complete | Person is **Started** (and economics later) |
| Owns | Application (inbound + Fits), Candidate recruitment process, Person resolution, duplicates, qualification, **recruitment missing**, **handoff package** | Accept handoff, **employment missing**, employability/legalization, contract/formalize, **Employee**, Start — **hosted in HR** |
| Must not | Create Employee; collect “docs just in case” for Employment; own legalization SoT; auto-accept its own handoff | Re-ask recruitment qualification; invent a second intake workflow |

**Ready for employment is a contract between modules — not merely a candidate stage/status.**  
A status may *reflect* that the contract was emitted; the SoT is the **handoff package** + audit event that Recruitment completed and Employment started.

**User journey** may look continuous.  
**Ownership** stays separate: seamless handoff, not a merged orchestrator.

```text
Source → Application (Fits) → Candidate (Recruitment process)
                    ↓
     Ready for employment  ← CONTRACT (handoff package), not “a status”
                    ↓
     Передать на трудоустройство
                    ↓
HR / Employment case → employability → missing → formalize → Employee → Started
```

Operator may see: **Подходит** on the Application, then Recruitment on the Candidate, then **Передать на трудоустройство**, then an already-prepared case in **HR**.  
Inside: Recruitment emits package → Employment accepts under **Employment policy**. Do not keep Formalize / Started on the Application card ([`ADR-042`](../architecture/ADR-042-operator-host-boundary.md)).

### Universal HostFlow principle

**Seamless UX does not mean shared ownership.**  
Recruitment, Employment, HR, Legalization, Fleet, Finance may keep hard domain boundaries. Simplicity comes from the next module receiving all known context — never from forcing the operator to manually carry work across the boundary.

---

## Handoff package (Ready for employment contract)

Recruitment **guarantees** a concrete package. After emit, Recruitment’s job for this **person / vacancy** is **done**. Fits on the Application is earlier: it only enters Candidates.

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
After **Подходит**, the operator is forced through entity steps (Create candidate, vacancy bind, stage menus), or Recruitment is treated as finished at Fits so Employment verbs land on the Application — or Recruitment never emits a clear **Ready for employment contract**, only a fuzzy stage.

**Completion proof (named consumer):**  
Untrained operator: Meta **Application** → **Подходит** → person is a **Candidate** → Recruitment process on that Candidate (Zero-choice inside it) → Ready for employment package → **Передать на трудоустройство**. No Create candidate / vacancy bind / stage picker rituals. Exact duplicate attaches silently. Audit: Recruitment completed. Operator does **not** Formalize, confirm start, or create Employee from the Application card.

**False close (reject):** one mega-orchestrator that creates Employee from Recruitment; Fits treated as Recruitment complete; Formalize / Started hosted on the Application; treating Ready for employment as only `stage=ready_for_handoff` without package contract; Recruitment gathering employment/legalization docs “на всякий случай”; treating `create_handoff + accept` as Recruitment logic; requiring the operator to re-enter known facts after handoff; no audit boundary between modules.

---

## Product language (two Recruitment hosts)

[`ADR-042`](../architecture/ADR-042-operator-host-boundary.md): **Отклики** and **Кандидаты** are both Recruitment-owned. They are not one card forever.

**Application (Отклики)** — inbound + first qualification:

`Source · Vacancy (if known) · Person`

→ **Позвонить** (when needed)  
→ **Подходит / Перезвонить / Не подходит**  
→ recruitment facts required to decide take / reject  

**Подходит** = enter **Candidates**. Not Transfer. Not Formalize.

**Candidate (Кандидаты)** — Recruitment process (Zero-choice inside this process; not a 15-stage ritual if the vacancy does not need it):

→ contact / qualification / recruitment-scope data as the vacancy requires  
→ **Ready for employment** (package)  
→ **Передать на трудоустройство**

After Transfer the operator opens an already-prepared **HR / Employment** case. Same person, no re-entry of known facts. Employment verbs are not Application chrome.

Internal call-result codes remain backend-only.

---

## Recruitment orchestrator contract

**Input intent (Application):** `fits` (Подходит) on a recruitment application / intake work item — enter Candidate.

**Input intent (Candidate):** Recruitment complete for this vacancy → emit `ready_for_employment.v1` → **offer_handoff**.

**Pipeline (Recruitment-owned only):**

1. **resolve_context** — vacancy, employer, source, recruiter (zero-choice when known).  
2. **attach_or_create_person** — without “Create candidate” UI.  
3. **resolve_duplicate** — exact → silent attach; probable → minimal confirm; HR-lock policy as today.  
4. **qualify (Application)** — enough to decide take / reject. Fits here **does not** emit the handoff.  
5. **recruit on Candidate** — vacancy/company process until Ready for employment (still Zero-choice: one blocker or one next action).  
6. **evaluate_recruitment_missing** — facts to decide Fits **or** to assemble a **correct handoff package** (never the full employment/legalization set).  
7. **build_handoff_package** — fulfills the **Ready for employment contract** (see table above). Only when Recruitment on the Candidate is complete.  
8. **emit + return next_action** — ask recruitment missing · confirm probable duplicate · **offer_handoff** (`Передать на трудоустройство`) · not_fits. Emit writes audit: Recruitment completed for this person/vacancy. Not an Application `next_action` of Formalize / Started.

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
| **RSO-2** | Runtime re-host ([`ADR-042`](../architecture/ADR-042-operator-host-boundary.md)): Application `fits` → Candidate; Candidate Ready for employment → `offer_handoff` | **Application Fits / Candidate Transfer Gate** — no Create candidate / vacancy bind / stage menu; Employment verbs not on Application | RSO-1 |
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

1. Meta work item, vacancy known — **Application**.  
2. **Подходит** → person is a **Candidate** (not Transfer, not Formalize).  
3. On the Candidate: Recruitment process (Zero-choice inside that process) until Ready for employment.  
4. **Передать на трудоустройство** on the Candidate.  
5. Never Create candidate / Bind / stage picker as rituals; never Formalize / Started on the Application.

FAIL if Recruitment UI creates Employee, asks for zezwolenie type, or hosts Employment verbs on the Application.

---

## Non-goals

- Employment / Legalization Decision Engine implementation (Employment program).  
- Merging Recruitment + HR into one module orchestrator.  
- Mapping Authority UX.  
- Work Surface mail/calendar.

---

## Next

1. **RSO-1 PASS** — package contract + three acceptance gates frozen.  
2. **RSO-2** runtime: re-host per [`ADR-042`](../architecture/ADR-042-operator-host-boundary.md) — Application Fits enters Candidate; emit `ready_for_employment.v1` + **Передать** only after Recruitment on that Candidate is complete. Do not pursue [#359](https://github.com/igortatarynovich/HostFlow/pull/359) one-card PASS.  
3. **Intake Readiness Gate** — [`intake-readiness-gate.md`](../gates/intake-readiness-gate.md) (`intake_readiness.v1`): Meta-like `POST /leads/meta` must become an actionable Application (`next_action = fits`) without hand-written canonical facts. Not Transfer / Formalize / Started.  
4. **Vacancy Recruitment Requirements SoT** — [vacancy-recruitment-requirements-sot.md](vacancy-recruitment-requirements-sot.md). System result fit / missing / not_fit chooses one next action; **Подходит** stays the human boundary into Candidates. Runtime not started. Unlock ≠ sequential-queue Active Product.  
5. **Canonical Facts Completeness** — [canonical-facts-completeness.md](canonical-facts-completeness.md). Occupancy cutover before Vacancy Requirements evaluator.  
6. ESO-1 accept policy on [Employment Spine Orchestrator v1](employment-spine-orchestrator-v1.md) — must enforce gate 2 (no re-ask).

Canvas: `meta-to-started-target-journey` (visual; not L2 canon).
