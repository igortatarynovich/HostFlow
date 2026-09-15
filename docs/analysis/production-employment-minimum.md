# Production Employment Minimum / Blocking Boundary

**Status:** research draft (L3) — **Accepted** for scenario **PEM-1** (product decision; not a Full Spine / ESO gate stamp)  
**Accepted:** 2026-09-13  
**Scenario id:** `PEM-1` — Polish domestic employee, EU/EEA pathway  
**Depends on (baseline):** [`employment-formalization-coverage-audit.md`](employment-formalization-coverage-audit.md) @ `b88a6168`  
**Parent brief:** [`../specs/tasks/employment-spine-orchestrator-v1.md`](../specs/tasks/employment-spine-orchestrator-v1.md)  
**Next artifact:** [`../specs/architecture/employment-start-allowed.md`](../specs/architecture/employment-start-allowed.md) — **`employment_start_allowed.v1` Accepted** (runtime not started; inventory next)  
**Does not amend:** L0 · ESO-1…5 PASS stamps · Formalize thin table runtime · Full Spine Gate  
**Code:** closed until post-Accept **inventory** of mint path + evidence authorities, then thin runtime slice.

> **Product decision**, not inventory.  
> **PEM-1 Accepted.** Do **not** expand ESO-4 into Contract + Medical + BHP.  
> **Do not** write code. **Do not** open Full Spine Gate from this Accept.  
> **Do not** generalize PEM-1 into third-country, posting, or full legalization suite.

---

## Purpose

For **one** named HostFlow production scenario, decide:

1. Which of the eight formalization domains are **REQUIRED / NOT REQUIRED / deferred**?  
2. What must be true **before Employee create**?  
3. What must be true **before physical Started** (`start_allowed`)?  
4. What is a **later lifecycle** obligation (after Started)?  
5. Which gaps are **blocking** for claiming Formalize semantics / Full Spine for this scenario?

Coverage Audit baseline (unchanged):

- `ready_to_create_employee=true` = **allow-create threshold**, not completed formalization.  
- **0 / 8 BUILT** end-to-end (decision ≠ internal task ≠ evidence ≠ external execution).  
- Full Spine remains **NOT PASS**.

---

## Scenario PEM-1 (Accepted)

**Title:** Polish domestic employee, EU/EEA pathway  

| Axis | PEM-1 |
|------|-------|
| Employer | Polish employer (PL payroll employer) |
| Contract type | `umowa o pracę` |
| Pathway | Citizen of PL / EU / EEA with free access to the labour market (`pl_eu_eea_free_movement`) |
| Geography | Work in Poland only |
| Start jurisdiction | Poland |
| HostFlow role | Owns process from handoff → proven **admit-to-work** decision; may record evidence of external acts; **not** required to be the government API (ZUS/PUE/urząd) in v1 |
| Posting / delegation | Absent |
| A1 | **NOT REQUIRED** |
| Zgłoszenie delegacji | **NOT REQUIRED** |
| Work-permit legalization | **NOT REQUIRED** |

### Why this scenario first

Proves core Employment Formalize / admit-to-work semantics **without** migration or cross-border execution. A1 / delegacja / work-permit legalization stay out of the first Minimum.

---

## Spine model for PEM-1 (Accepted)

**Employee create ≠ admit-to-work.** Canonical order:

```text
ESO-4 allow-create (ready_to_create_employee)
  → Employee exists
  → Contract + Medical* + BHP* proof / exception
  → start_allowed=true
  → human Confirm physical start (ESO-5)
  → Started
  → ZUS / Insurance deadline-bound lifecycle
```

| Phase | Meaning for PEM-1 |
|-------|-------------------|
| ESO-4 allow-create | Pathway + identity + contract **basis** sufficient to **materialize Employee** — not proof of written umowa, BHP, or medical |
| Employee exists | Internal workforce row; enables post-Employee tools (Contract Preview, ZUS workspace) |
| Pre-Start (`start_allowed`) | Separate authority **immediately before ESO-5**: written contract / written confirmation of terms; introductory BHP (unless lawful exception); valid occupational medical certificate for the post and conditions of work (unless lawful exception) |
| Started | Explicit physical start (ESO-5) — only when `start_allowed` |
| Later lifecycle | ZUS registration / insurance within **7 days** from insurance obligation / employment start — **not** a pre-Start blocker |

**Do not expand ESO-4** to Contract + Medical + BHP. ESO-4 stays the Employee-create gate. **`start_allowed` is a new pre-Start authority** between Employee and ESO-5.

**Legal posture (product intent, not HostFlow legal advice; re-checked 2026-09-13 against official sources):**

- For `umowa o pracę`, employer must have a written contract **or** written confirmation of parties, type, and terms **before admit-to-work**.  
- Introductory BHP is conducted **before admit-to-work**, with a statutory exception for an immediately successive contract with the **same employer** in the **same post**.  
- Medical rule is stricter: the worker **must not** be admitted without a current medical conclusion of no contraindications for the **specific post and working conditions**.  
- ZUS registration filing deadline is **7 days** from the insurance obligation arising (e.g. employment start under `umowa o pracę`) — deadline-bound lifecycle, not a ban on first-day Started.

---

## Decision table — PEM-1 (Accepted)

| Domain | PEM-1 | Before Employee | Before Started | Later lifecycle | Blocking? |
|--------|-------|-----------------|----------------|-----------------|-----------|
| **Contract** | **REQUIRED** | **basis sufficient to materialize Employee** (not written umowa yet) | **yes** — proof of written contract / written confirmation of terms | archive / amendments | **yes** (Start) |
| **Medical** | **REQUIRED\*** | no | **yes** — valid certificate for post + conditions, or documented exception | renewals / expiry | **yes** (Start) |
| **BHP** | **REQUIRED\*** | no | **yes** — introductory BHP before admit, or documented exception | periodic training | **yes** (Start) |
| **ZUS** | **REQUIRED** | no | **no** | **yes**, deadline-bound (≤ 7 days from insurance obligation / employment start) | **no** for Start |
| **Insurance** | **REQUIRED** via ZUS context | no | **no** | **yes** (with ZUS registration lifecycle) | **no** for Start |
| **A1** | **NOT REQUIRED** | — | — | — | **no** |
| **Delegation** | **NOT REQUIRED** | — | — | — | **no** |
| **Legalization** | **NOT REQUIRED** (this pathway) | — | — | — | **no** |

\* **Context, not universal checkbox.** Model requirement vs lawful exception (e.g. introductory BHP when continuing same post / same employer under an immediately successive contract).

### Contract row — Accept clarification

| Gate | Requirement |
|------|-------------|
| Before Employee | Employment **basis** sufficient to mint Employee (aligns with ESO-4 `confirm_employment_contract_basis` + pathway/identity). Written umowa is **not** required before create — Contract Preview remains post-Employee. |
| Before Started | **Evidence** of written contract **or** written confirmation of terms (legal admit-to-work boundary). |
| Blocking Start | **YES** |

### Layer interpretation (PEM-1)

| Domain | Minimum layer for “done enough” in HostFlow v1 |
|--------|--------------------------------------------------|
| Contract (pre-Start) | **Evidence** of written contract / written confirmation (sign/ePUAP may stay external) |
| Medical | **Evidence** of valid occupational medical conclusion for the post (or recorded exception) |
| BHP | **Evidence** of completed introductory BHP before admit (or recorded exception) |
| ZUS / Insurance | **Internal task** (+ optional filing evidence) with **deadline** after Started |
| A1 / Delegation / Legalization | Out of PEM-1 |

---

## Blocking gap read (Accepted implication)

| Gap class | Domains | Implication |
|-----------|---------|-------------|
| **Primary** | Contract + Medical + BHP as **`start_allowed`** | First blocking gap = absence of a proven **pre-Start authority** — **not** A1, **not** ZUS-as-Start-blocker, **not** expanding ESO-4 |
| Out of PEM-1 Start | A1 / Delegation / Legalization | **NOT REQUIRED** |
| Lifecycle | ZUS + Insurance | REQUIRED after Started with 7-day deadline; not `start_allowed` |

---

## Production Employment Minimum (one paragraph — Accepted)

For **PEM-1** (PL employer, `umowa o pracę`, EU/EEA free-movement worker, domestic work in Poland, no posting), HostFlow must: (1) allow Employee create when employment **basis** is sufficient (ESO-4); (2) before physical start — prove written contract / written confirmation of terms, introductory BHP, and valid medical fitness for the post and conditions (each with modeled exceptions) via a separate **`start_allowed`** authority; (3) after Started — run ZUS/insurance as a deadline-bound lifecycle (≤ 7 days). A1, zgłoszenie delegacji, and work-permit legalization are out of scope. Employee create is not admit-to-work; ESO-5 Confirm start requires `start_allowed` first.

---

## Acceptance record

| Criterion | Result |
|-----------|--------|
| Scenario axes concrete (not “driver in Poland”) | **PASS** |
| Decision table filled; Contract Before Employee = basis only | **PASS** |
| `Employee ≠ start_allowed ≠ Started` | **PASS** |
| Blocking limited to PEM-1 Start domains | **PASS** |
| ESO-4 not expanded to Medical/BHP/written umowa | **PASS** |
| Next work = `start_allowed` architecture only | **PASS** |
| Full Spine PASS claimed | **NO** (explicitly forbidden) |

**Accepted** as product decision for PEM-1 on 2026-09-13.

---

## Locked sequence

1. ESO-5 [#372](https://github.com/igortatarynovich/HostFlow/pull/372) — Started HR binding (separate).  
2. Coverage Audit — committed `b88a6168`.  
3. **PEM-1 Accepted** (this file).  
4. **`start_allowed` architecture** — [`employment-start-allowed.md`](../specs/architecture/employment-start-allowed.md) **Accepted**; next = **inventory** (mint path + evidence authorities), then thin runtime.  
5. Only then: implement Minimum-blocking gaps for PEM-1.  
6. Three-host Full Spine Gate — [`../specs/tasks/three-host-full-spine-gate-pem1.md`](../specs/tasks/three-host-full-spine-gate-pem1.md) **STOP** 2026-09-15 (proof walk; **NOT PASS**; Ready / DQC hole).

---

## Non-goals

- Expanding ESO-4 Formalize thin table to Contract proof + Medical + BHP.  
- Third-country / posting / A1 scenarios (later PEM-N).  
- Making ZUS a pre-Start blocker for PEM-1.  
- Equating Employee create with admit-to-work.  
- ZUS API / Płatnik / ePUAP as PEM-1 requirement.  
- Code, migrations, or UI before mint/evidence **inventory** + thin runtime plan.  
- Full Spine Gate from this Accept.

---

## Next action

1. **Inventory** before any runtime: Employee mint path + Documents/contract/medical/BHP evidence authorities (no parallel stores).  
2. Then thin `employment_start_allowed.v1` runtime + `employment-start-allowed-gate`.  
3. Keep ZUS/Insurance on post-Start lifecycle; do not open A1/delegation under PEM-1.
