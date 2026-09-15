# Inventory: Life path → Processes → Modules → Leaks

**Status:** **OPEN** (map seeded; leak overlay in progress) — Accept of [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) still required to promote remediation  
**Layer:** L3 inventory — not Full Spine PASS · not a document catalog gap-fix  
**Phase class:** platform  
**Opened:** 2026-09-15  
**Parent:** [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) (**Proposed**)  
**Does not open:** Walk 4 Continuations · Contract/BHP as spine topology · Hiring E2E · Release Readiness

> **Layer 1:** restore the map — life path → processes → modules → boundaries → process I/O.  
> **Layer 2:** overlay RSO/ESO/ESA / requirements / documents / policies — mark where internals leaked into the каркас.  
> That leak list **is** the remediation plan.

---

## Original Goal → Completion Proof

**Problem this inventory must permanently remove:**  
Ambiguity between “platform каркас broken” and “policy correctly blocks an action,” plus bottom-up document fixes mistaken for Full Spine architecture.

**Completion proof (named consumer):**

```text
Published map: life path → process → module → I/O / boundary
  → overlay classifies each major transition (clean | leak | unclear)
  → remediation queue = leaks only
  → Full Spine kernel proof brief can open (minimal/neutral policy)
  → PEM-1 remains a separate policy-composition proof
```

---

## Layer 1 — Life path (person)

```text
Отклик → Отбор → Передача → Трудоустройство → Выход на работу → Работа → завершение / изменение
Lead/Apply → Recruitment → Handoff → Employment → Start → Workforce → …
```

Designed **without** Code95, BHP, citizenship, vacancy packs.

---

## Layer 1 — Processes → Modules → I/O

| # | Life-path segment | Process | Module | In (expects) | Out (produces) | Must not own |
|---|-------------------|---------|--------|--------------|----------------|--------------|
| 1 | Отклик → решение / отбор | **Recruitment** | Recruitment | Lead/Candidate, vacancy target, recruiter actions | Ready / not ready for Transfer; Fits + requirement verdicts as Recruitment SoT | Employee lifecycle; admit Medical/BHP sufficiency; ZUS |
| 2 | Передача | **Handoff / boundary** | Boundary (RSO transport) | Recruitment Ready package / RFE | Immutable manifest + scope transition; Employment case init trigger | Copying Person/Docs; inventing Employment admit decisions |
| 3 | Подготовка к найму | **Employment formalize** | HR / Employment | Live Person/Docs + manifest decisions | `ready_to_create_employee` / Employee ensure | Recruitment qualification packs as Employment topology |
| 4 | Проверка допуска | **Admit-to-work** | Employment | Employee + evidence views | `start_allowed` verdict + next_action | New person spine; Recruitment Ready rules |
| 5 | Фактический выход | **Start** | Employment | `start_allowed` + human Confirm | Started | Mint-on-confirm; auto-start from documents alone |
| 6 | Работа | **Workforce** | Workforce | Employee Started | Post-start ops | Re-opening Recruitment topology |
| 7 | Легализация* | **Legalization** | Separate (later) | Employment context | Legalization outcomes | Second Full Spine |
| 8 | Командирование* | **Posting / Delegation** | Separate (later) | Employment/Workforce context | Posting outcomes | Second Full Spine |

\* Applicable processes — attach by policy/context, not by forking the life path.

### Boundary canon already on tree (reuse)

| Boundary | Canon |
|----------|--------|
| Recruitment ↛ Employee lifecycle | [`ADR-002`](../architecture/ADR-002-modular-recruitment-hr-boundary.md) · [`ADR-037`](../architecture/ADR-037-lifecycle-identity-canon.md) |
| Transfer dual model (live + frozen) | [`recruitment-employment-boundary-ownership.md`](../architecture/recruitment-employment-boundary-ownership.md) |
| RFE package | [`ready-for-employment-contract.md`](../architecture/ready-for-employment-contract.md) |
| Admit-to-work | [`employment-start-allowed.md`](../architecture/employment-start-allowed.md) |
| Employment Accept policy | [`employment-accept-policy.md`](../architecture/employment-accept-policy.md) |

### Process I/O detail (seeded from Accepted boundary)

**Handoff / Transfer (process #2)** — from boundary ownership:

| Axis | Rule |
|------|------|
| Manifest | `ready_for_employment.v1` = immutable boundary proof + decision basis — **not** live Person/Docs SoT |
| Live after Transfer | Same Person / Documents Hub / Vacancy authorities |
| Write after Transfer | Scope transition reuses existing access; Employment collects only Employment-owned missing |
| Forbidden | Candidate copy → handoff copy → Employee copy → HR verifies copies |

**Recruitment Ready outward (process #1):**

| Outward signal | Meaning |
|----------------|---------|
| Ready / Transfer allowed | Person may leave Recruitment process |
| Not ready + blockers / next_action | Policy verdict — **path still exists** |
| Fits / requirement packs | Internal Recruitment policy sets (driver_ce ≠ warehouse ≠ office) — **one process** |

**Employment admit outward (process #4):**

| Outward signal | Meaning |
|----------------|---------|
| `start_allowed=true` | Admit policy satisfied for this context |
| `missing` / `blocked` + next_action | Evidence/policy gap — **Start transition still exists** |
| PEM-1 pack (Contract+Medical+BHP) | One ruleset under admit policy — not a second Employment spine |

---

## Layer 2 — Overlay (RSO / ESO / ESA / requirements / documents)

**Rubric**

| Class | Meaning |
|-------|---------|
| **clean** | Process transition exists; policy returns allowed/blocked/missing/unsupported + next_action; evidence is input only |
| **leak** | Missing document/type/pack/nationality prevents the **route** from existing, or process internals dictate каркас topology |
| **unclear** | Needs Architecture owner call |

### Transition overlay (seeded 2026-09-15)

| Transition | Surfaces today | Class | Leak / note |
|------------|----------------|-------|-------------|
| → Recruitment Ready | `transfer-readiness`, requirement_engine, document packs, Candidate Evidence | **leak** (observed Walks 1–2) | Pack/R5 codes + Hub storage identity acted as **route existence** (DQC / `doc_index` exact match). Should be: Ready transition exists; policy says missing/blocked + next_action |
| Ready → Transfer / RFE | RSO-2 emit / create handoff | **clean** (boundary E2E PASS) | Transport + manifest; not document topology |
| Transfer → Employment auto-init | RSO-2C / ESO accept-after-transfer | **clean** | Employment owns accept; no ritual Accept happy path |
| → Formalize / Employee ensure | ESO-4 | **clean** (thin table) | Pathway actions; not pack-driven spine |
| Employee → `start_allowed` | ESA / `employment_start_allowed.v1` | **leak→remediated as evidence** (Walk 3) | Hub missing `employment_contract`/`bhp` types collapsed storage → picker could not see evidence. **Policy surface itself is correct**; leak was evidence identity, framed wrongly as Full Spine topology. Do not reopen as spine work |
| Confirm → Started | ESO-5 | **clean** (slice 4 PASS) | Confirm requires `start_allowed`; mint-on-confirm retired |
| Full Spine Gate brief | PEM-1 walks 1–4 | **leak (framing)** | Equated PEM-1 document composition with platform каркас; Walk 4 Started reclassified — not kernel PASS |

### Known non-leaks (keep)

- RSO-2 cutover / boundary E2E — boundary process, not vacancy-pack spine.  
- ESO-4 / ESA / ESO-5 named gates — Employment process policies.  
- ADR-016/018 — evidence vs requirement evaluation (aligns with this inventory).

---

## Remediation plan (derived from leaks only)

| Priority | Item | Kind | Not |
|----------|------|------|-----|
| P0 | Accept ADR-042 | Architecture | Runtime rewrite |
| P1 | Finish this map (I/O columns, Legalization/Posting stubs) | Inventory | New Hub types “for Walk” |
| P2 | **Baseline Full Spine kernel proof** brief — minimal/neutral policy | Proof | PEM-1 packs as topology |
| P3 | Re-bind Recruitment Ready evaluate so missing docs = policy `missing` + next_action, not “path absent” | Process policy hygiene | Second Recruitment spine |
| P4 | PEM-1 **policy composition** proof (separate from kernel) | Proof | Equating with Full Spine |
| — | Contract/BHP Hub identity PASS | Done as **evidence** | Further Walk-4 document chasing as spine |

---

## Explicit non-goals

- Continuing Walk 4 / opening Contract/BHP gap-fixes as Full Spine topology  
- Six spines for warehouse / office / EU / third-country / B2B / posting  
- Claiming Release Readiness or Hiring E2E  

---

## Next

1. **Accept** ADR-042.  
2. Complete Layer 1 I/O detail from module-scope / ownership cards.  
3. Open baseline **Full Spine kernel** proof (minimal policy).  
4. Keep PEM-1 as separate policy-composition proof.
