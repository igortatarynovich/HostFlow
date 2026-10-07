# HRappka live session audit — product brief

**Status:** research draft  
**Date:** 2026-09-10  
**Method:** authorized test session on entities `HOSTFLOW20260910` / related test workers; no real people, SMS/email, publications, or external filings  
**Path exercised:** Vacancy → Questionnaire → Matching → Candidate → Accepted → Hire → Client → Contract → Position → Permits (+ later UX walk: forms, calendar, work time, home, signup modules)  
**SoT strategy:** Cursor Strategy Lock canvas (`hostflow-strategy-lock`) · RSO / ESO spines  
**Companion canvas:** `hrappka-live-session-audit.canvas.tsx` (session detail + parked table)  
**Inventory:** [vacancy-requirements-facts-inventory.md](vacancy-requirements-facts-inventory.md)  
**Requirements SoT:** [vacancy-recruitment-requirements-sot.md](../specs/tasks/vacancy-recruitment-requirements-sot.md)  
**Canonical Facts Completeness:** [canonical-facts-completeness.md](../specs/tasks/canonical-facts-completeness.md)

> L3 research / product brief. Does **not** amend L0. Does **not** schedule payroll/CRM/ERP. Does **not** reopen Full Spine Gate. Does **not** wait on HR operator host.

---

## 1. One-line verdict

HRappka shows **where** HostFlow differentiates — not a backlog of modules to clone.

HRappka is a strong **administrative** HRIS: many options and functions, but the operator constantly sees the internal model (candidate, contract, position, permits, rates, BHP…). HostFlow lock remains:

**Options yes · Functions yes · Complexity no**  
**Intent → minimum necessary data → system decision → one next action → result**

---

## 2. What the session validated (already built)

Primary “missing” claims from the first Work write-up are **outdated** relative to ESO-1…5:

| Claim | HostFlow reality |
|---|---|
| Automatic legal pathway | **ESO-2** — deterministic pathway + `employable` / `blocked` / `insufficient_facts` |
| Evidence-based employability | **ESO-2 + ESO-3** — active missing → minimal resolution → re-eval |
| Automatic document selection | **ESO-4** — context/pathway formal requirements → `ready_to_create_employee` |
| Separate Started confirmation | **ESO-5** — Employee ≠ Started → explicit physical-start confirm |

Competitive audit **validates** Employment Decision Engine direction. Do not treat these as greenfield P0.

---

## 3. Highest-value anti-pattern (do not copy)

HRappka splits:

1. Vacancy **rich text** requirements (“C+E, Code 95, karta kierowcy, 1 rok UE”)
2. Separate **Profiling / matching parameters** the operator must build by hand

Control example we must never ship: a strong Employment Engine while a manager still creates five matching parameters to answer “does this driver fit the vacancy?”

**HostFlow contract (near-term SoT):**

```text
Vacancy Recruitment Requirements
  × Canonical Candidate Facts
  → Fits / Not fits / Missing (+ explanation)
```

Source-independent: Meta · Form · manual · CSV · job board → same facts.  
Live signal: `citizenship=PL` must not remain only in `field_answers` if needed downstream.

---

## 4. Locked corrections from this audit

| Topic | Decision |
|---|---|
| Spine topology | **Unchanged:** Source → Recruitment → Handoff → Employment → Employability → Formalize → Employee → Started |
| Fits ≠ Transfer | **Keep** human boundary: Fits → Ready for employment → **Передать на трудоустройство**. Do **not** auto-create Employment case from Fits alone |
| Accepted | Recruitment status ≠ employment / employability decision |
| Zero-choice | Removes pointless system choices; **does not** remove real business decisions |
| Configuration | **Configuration defines policy. Configuration primitives must not become operator workflow.** Live HostFlow FAIL: handoff blocked on missing `ready_for_handoff` stage while state is already ready |

---

## 5. Near-term work (after Recruitment-side cutover)

HR operator host is **NOT READY**. Full Spine operator test is **BLOCKED BY HR UI**. That does **not** block this track.

Not payroll, CRM, or HRappka module breadth. Three architectural questions — **#1 before declaring Recruitment closed:**

### 5.1 Vacancy Recruitment Requirements SoT (P0)

- Where Fits reads requirements; how they stay source-independent  
- UI principle liked in HRappka: at vacancy/position create, pick required documents (+ role classification) from a list; short guided steps so the operator states what must be stated  
- HostFlow already has packs / `CandidateRequirementsTab` / vacancy overlay — bind into **one** Requirements SoT that feeds Fits, not a second Profiling layer  
- **Do not** fold rates/contract subtype into that create path as runtime blockers  

**Inventory:** [vacancy-requirements-facts-inventory.md](vacancy-requirements-facts-inventory.md). **SoT (sealed, runtime later):** [vacancy-recruitment-requirements-sot.md](../specs/tasks/vacancy-recruitment-requirements-sot.md). System result ≠ three buttons; **Подходит** stays the human boundary.

### 5.2 Canonical Facts completeness (P0)

- Why known facts (e.g. citizenship) leak into form-local `field_answers`  
- Inventory which qualification / employment facts drop between intake and canonical layer  
- Aligns with HRappka’s citizenship gate on legalization — HostFlow goes further: **facts → pathway**, not “pick permit type first”  

Leak / storage rows are in the same inventory (§ Facts). Completeness contract (consumers-first occupancy matrix): [canonical-facts-completeness.md](../specs/tasks/canonical-facts-completeness.md). Order: facts occupancy cutover → Vacancy Requirements evaluator.

### 5.3 Configuration runtime dependency audit (P1)

- Cases like `ready_for_handoff` stage, `campaign_flight`, mapping config  
- Classify each: true domain prerequisite vs internal HostFlow entity the operator should never service  
- Preflight where config is mandatory; never surprise-block mid-person handling  

Not this inventory.

---

## 6. Parked observations (liked · not scheduled)

Captured during the walk. Posture: **useful capabilities are not dismissed**; **not everything is copied**; **no implementation brief yet** except §5.

| Theme | Like | HostFlow posture |
|---|---|---|
| Vacancy create: docs + classification + short steps | Focused policy capture | Feed Vacancy Requirements SoT; reuse packs/catalog |
| Rates / remuneration step | Employee vs client, types, periods | Park for economics / invoiceable; not Fits/Employment P0 |
| Vacancy → recruitment + questionnaire + preview | Context-preserving | Park; skip dense WWW/after-apply settings as entry complexity |
| Employee facts → ZUS / contract / permit / A1 / print / e-submit | Facts feed filings | Formalize/export depth; pathway-driven generate/print; PUE later |
| Legalization from citizenship | Citizenship required before permits | Canonical fact → pathway (ESO); missing-fact UX |
| Module enablement at signup | Narrow surface | Tenant capability onboarding; spine always on; optional modules off by default |
| Candidate card | Sections, tags, recruitment bind, attachments | Person workspace parity+; create stays short |
| Form builder | Clear field names/types; pick → add → configure → save | Forms UX target; canonical fields → facts |
| Work time summary calendar | Demand vs workers, cell actions | Later workforce / Started proof; not full T&A/RFID now |
| Ops calendar | Hours, absence, availability, transport… | Entity-context calendar; not Outlook clone |
| Start dashboard | Universal + personalizable | My Work / home; core = attention queue, not second ERP |

**Product formula for parked items:** options and functions may grow **inside** the system; operator surface stays short. A feature that adds choice without removing work is complexity, not strength.

---

## 7. Explicit non-goals (from this audit)

- Becoming another HRappka (full payroll, invoices, ERP, universal CRM, rare certificate taxonomies)  
- Permit-first legalization UI with long legal radio trees as the happy path  
- Auto Transfer / auto Employment case from Fits  
- Closing Recruitment without Vacancy Requirements SoT (§5.1)  
- Treating ESO pathway / Started as still “missing”

---

## 8. Friction snapshot (session metrics)

Approximate operator load on the hire path (HRappka):

- Operator Friction ~**72/100**  
- Candidate → Employee seamlessness ~**3/10**  
- Highest friction areas: Legalization, Recruit→Employ, Formalization  

Use as **competitive evidence**, not as HostFlow scorecard. HostFlow scorecard = Operator Test + Zero-choice + Happy path short on our spine.

---

## 9. References

- [Recruitment Spine Orchestrator v1](../specs/tasks/recruitment-spine-orchestrator-v1.md)  
- [Employment Spine Orchestrator v1](../specs/tasks/employment-spine-orchestrator-v1.md)  
- [Ready for employment contract](../specs/architecture/ready-for-employment-contract.md)  
- [Vacancy Requirements / Facts inventory](vacancy-requirements-facts-inventory.md)  
- Strategy Lock / live audit canvases (Cursor project canvases; not repo SoT)

---

## 10. Suggested next artifacts

1. Inventory — [vacancy-requirements-facts-inventory.md](vacancy-requirements-facts-inventory.md).  
2. **Vacancy Recruitment Requirements SoT** — sealed: [vacancy-recruitment-requirements-sot.md](../specs/tasks/vacancy-recruitment-requirements-sot.md). Runtime not started.  
3. **Canonical Facts Completeness** — sealed: [canonical-facts-completeness.md](../specs/tasks/canonical-facts-completeness.md). Next: occupancy cutover, then evaluator.  
4. Audit table: **Configuration runtime dependencies** (P1; not this track).
