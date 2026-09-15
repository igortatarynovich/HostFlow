# ADR-042: Spine / Policy Separation (platform workflow kernel)

**Status:** **Proposed** (Awaiting Accept)  
**Date:** 2026-09-15  
**Trusted base:** `integration/release-product-a-b`  
**Does not supersede:** [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md) · [`ADR-016`](ADR-016-requirement-evidence-document-separation.md) · [`ADR-018`](ADR-018-requirement-policy-evaluation-model.md) · [`ADR-037`](ADR-037-lifecycle-identity-canon.md) · RSO/ESO/ESA named gate PASSes · [`recruitment-employment-boundary-ownership.md`](recruitment-employment-boundary-ownership.md)  
**Related:** [`employment-start-allowed.md`](employment-start-allowed.md) · [`three-host-full-spine-gate-pem1.md`](../tasks/three-host-full-spine-gate-pem1.md) · inventory [`spine-policy-separation-inventory.md`](../tasks/spine-policy-separation-inventory.md) · [`architecture-invariants.md`](architecture-invariants.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (one owner per concern), **INV-01** (one SoT), **INV-07** (compose, do not fork engines), **INV-16** (decision priority). Clarifies composition of lifecycle topology with requirement/policy evaluation (ADR-016/018/037) — does **not** rewrite L0.

**(1)** Life path → process → module ownership (top-down); transition **Policy** owns permission; Facts/Evidence/Actions own proof inputs. **(2)** No new Catalog capability. **(3)** Existing module facades + RSO/ESO/ESA as process/policy surfaces. **(4)** No Recruitment/HR checklists into System Layer. **(5)** No new settings dump. **(6)** SoT: path ≠ process ≠ module ≠ policy ≠ evidence. **(7)** No new security event types for Accept. **(8)** Requires existing PE / requirements / employment policies. **(9)** No new licence. **(10)** Additive: transition verdicts `allowed|blocked|missing|unsupported_context` (+ `next_action`).

---

## Context

PEM-1 “Full Spine” walks treated missing documents / Hub identities as if the **person route** did not exist. That inverts platform construction: conditions were acting as **route infrastructure**.

HostFlow must scale to warehouse, office, EU driver, third-country driver, B2B, posting — **without** six spines. Documents, Code95, BHP, citizenship, A1, ZUS are **not** design-time inputs to topology.

ADR-016 / ADR-018 / ADR-037 already separate evidence, evaluation, and stage identity. This ADR seals the **top-down construction order** and the split **Full Spine (kernel) ≠ PEM-1 (policy composition)**.

---

## Decision

### 0. Construction order (mandatory, top-down)

```text
1. Life path of the person          (stages of the journey — no documents yet)
2. Business processes               (what work happens between stages)
3. Modules                          (who owns each process)
4. Boundaries / I/O of each process (what enters / exits; ownership handoff)
5. Policies & rules inside modules  (may this action run now? why not?)
6. Facts / Evidence / Actions       (inputs to rules)
```

**Principle (frozen wording):**

> **Путь определяет процессы. Процессы определяют модули. Политики и правила определяют поведение внутри модулей.**  
> **Не наоборот.**

A document, rule, or policy **must not** create a new person route. It only decides whether a concrete action inside an existing process is allowed and what blocks it.

Example: missing BHP → “Start now forbidden — BHP required.”  
Not: “Candidate → Employment → Employee → Started only exists when the system already knew BHP.”

Same for Recruitment: driver Ready may need C+E + Code95; warehouse another set; office a third — **one Recruitment process**, many policy sets.

### 1. Life path (каркас человека)

Illustrative person journey (product language; stage **identities** remain ADR-037 / module registries):

```text
Отклик → Отбор → Передача → Трудоустройство → Выход на работу → Работа → завершение / изменение отношений
```

English working labels for proofs:

```text
Lead / Apply → Recruitment → Handoff → Employment → Start → Workforce → …
```

This path is designed **without** thinking about Code95, BHP, citizenship, or vacancy packs.

### 2. Processes and modules (from the path)

| Life-path segment | Process | Module / owner |
|-------------------|---------|----------------|
| Отклик → решение / отбор | Recruitment | Recruitment |
| Передача между функциями | Handoff / boundary | Boundary coordination (RSO transport; ownership per boundary card) |
| Подготовка к найму | Employment (formalize / ensure) | HR / Employment |
| Проверка допуска | Admit-to-work | Employment (`start_allowed`) |
| Фактический выход | Start (Confirm → Started) | Employment (ESO-5) |
| Работа с действующим сотрудником | Workforce | Workforce |
| Легализация (when applicable) | Legalization | Separate module (later; not a second spine) |
| Командирование (when applicable) | Posting / Delegation | Separate module (later; not a second spine) |

After this table, the **platform skeleton is largely defined**. Each process then deepens **independently**.

| Process outward contract (example) | Must remain true |
|------------------------------------|------------------|
| Recruitment | Person **ready / not ready** for Transfer — Recruitment internals (scoring, packs, language) stay inside |
| Employment | Employment case progresses; admit and start decisions Employment-owned — Recruitment must not know Contract/Medical/BHP machinery |
| Workforce | Post-start lifecycle — not a Recruitment/Employment topology fork |

### 3. Layers inside a process

| Layer | Owns | Must not own |
|-------|------|----------------|
| **Process / Spine topology** | States, transitions, module ownership, handoff, audit | Vacancy packs, nationality, document-type lists, A1/ZUS/BHP |
| **Policy** | May this transition/action run **now**? `allowed` / `blocked` / `missing` / `unsupported_context` + `next_action` | Alternate person routes |
| **Rules** | Context config of a policy (PEM-1 `start_allowed` = Contract+Medical+BHP) | Which transitions exist |
| **Facts / Evidence / Actions** | Proof inputs | Driving topology |

Dependency **only** one way:

```text
Facts / Evidence / Actions → Rules → Policy → Transition permission → Stable process on the life path
```

**Forbidden reverse:** Document type / pack / nationality → runtime → life path exists or not.

### 4. Full Spine ≠ PEM-1

| Proof | Proves | Does not prove |
|-------|--------|----------------|
| **Full Spine (kernel)** | Platform каркас works: Lead → Recruitment → Handoff → Employment → Start → Workforce under **minimal/neutral** policy | Driver/warehouse/office document sets |
| **PEM-1 (policy composition)** | For that worker context, the **right policies** are wired (e.g. Recruitment qualification + admit Contract/Medical/BHP) | That the каркас only exists for PEM-1 |
| **Named RSO/ESO/ESA gates** | Slice of process/policy machinery | Full Spine kernel alone |

Warehouse, office, EU driver, third-country, B2B, posted worker → **one каркас**, different process policies — not six spines.

### 5. Hard bans

| Ban | Meaning |
|-----|---------|
| **No policy-specific spine** | Pack / document / citizenship / A1 / ZUS / client checklist must not mint a second life path |
| **No condition-as-route-infrastructure** | Missing Hub type/evidence ≠ “spine cannot exist” |
| **No bottom-up architecture** | Do not start from documents/rules and invent the person route |
| **No Walk-as-kernel** | Continuous Started under PEM-1 document load ≠ Full Spine PASS |

### 6. Remediation posture (after Accept)

1. **Map restore** ([inventory](../tasks/spine-policy-separation-inventory.md)): life path → processes → modules → boundaries → process I/O.  
2. **Second layer:** overlay RSO/ESO/ESA, requirements, documents, policies — mark **leaks** (process logic into каркас).  
3. Remediate **only** leaks. Keep working RSO/ESO/ESA; re-bind as process/policy surfaces where needed.  
4. **Do not** open further Contract/BHP/Code95 fixes **as Full Spine topology**.  
5. Baseline lifecycle proof, then PEM-1 policy composition separately.

---

## Consequences

### Positive

- Top-down platform that scales contexts without N spines.  
- Clear Full Spine vs PEM-1 proof split.  
- STOP diagnosis: kernel vs process policy vs evidence.

### Negative / cost

- Reclassify recent walks/gates.  
- Inventory before Full Spine PASS.  
- Resist “add Hub type to green Walk N” as architecture.

### Compatibility

- Does not void RSO-2 / ESO-4 / ESA / ESO-5 PASSes.  
- Hub identity fixes remain valid **inside Employment/Recruitment policy evidence**, not as kernel substitutes.

---

## Alternatives considered

| Alternative | Reject |
|-------------|--------|
| Continue PEM-1 walks by fixing each document STOP | Bottom-up; conditions as route infrastructure |
| Per-vacancy / per-nationality spines | Forks life path; INV-07 |
| Equate Full Spine with PEM-1 | Confuses kernel with one policy composition |
| Treat Walk 4 Started as Full Spine PASS | Policy-laden ≠ kernel |

---

## Accept criteria

| # | Criterion |
|---|-----------|
| A1 | Accepted by Architecture canon owner |
| A2 | Full Spine brief **NOT PASS** until baseline kernel proof; PEM-1 named separately |
| A3 | Inventory holds life-path → process → module map + leak overlay |
| A4 | Catalog / domain-map cross-refs |

**Runtime / migrations:** not required for Accept.

---

## Cross-references

| Doc | Role |
|-----|------|
| [`spine-policy-separation-inventory.md`](../tasks/spine-policy-separation-inventory.md) | Map + leak overlay |
| [`three-host-full-spine-gate-pem1.md`](../tasks/three-host-full-spine-gate-pem1.md) | NOT PASS; Full Spine ≠ PEM-1 |
| [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) | ADR index |
| [`hostflow-core-domain-map-v1.md`](hostflow-core-domain-map-v1.md) | Domain linkage |

---

## Changelog

- 2026-09-15: Proposed — Spine/Policy Separation.  
- 2026-09-15: Amended — top-down **path → process → module → policy**; explicit **Full Spine ≠ PEM-1**.
