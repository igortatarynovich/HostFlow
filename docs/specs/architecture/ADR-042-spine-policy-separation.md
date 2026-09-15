# ADR-042: Spine / Policy Separation (platform workflow kernel)

**Status:** **Accepted**  
**Accepted:** 2026-09-15  
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

### 2a. Module publishes process contract — not policy internals

A module **exposes** the process result and allowed actions. A neighbour **must not** know which rules produced that result.

| Module | Outward process contract | Hidden inside |
|--------|--------------------------|---------------|
| Recruitment | Ready / not ready; Transfer package (`ready_for_employment.v1` decisions) | Scoring, packs, Code95, language, recruiter exceptions |
| Employment | Process state; admit/start verdicts + allowed actions | Contract/Medical/BHP rule machinery, formalize depth |
| Workforce | Active-employee state + allowed ops | Internal workforce policies |

**Consequence:** Full Spine can be stabilized **once**. Recruitment, Employment, Legalization, Posting deepen independently without rebuilding the person path.

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

Walks 1–4 remain **useful evidence** of past kernel/policy/evidence conflation. They are **not** criteria for Spine existence.

### 4a. Neutral policy ≠ bypass (hard lock)

Baseline Full Spine proves **existence and composition** of the каркас. It does **not** prove that production policy can be switched off.

**Allowed:** a normal **policy contract** whose configuration may contain **no additional requirements**. Then `allowed` is returned **by the same policy engine** — штатно, not around it.

**Forbidden for kernel proof:**

| Bypass form | Why rejected |
|-------------|--------------|
| `if test` / env / CI-only short-circuit of production policy | Not the product path |
| Special tenant flag that disables admit/Ready engines | Shadow spine |
| Direct call of internal APIs that skip evaluate → verdict | Not a process contract |
| Operator-set `start_allowed` / forged Ready | False continuity |
| Seed helpers that mint Started without hosts | Not three-host composition |

Neutral/minimal = **empty or zero-requirement ruleset on the real policy surface**. Same hosts, same evaluate path, same verdict shape (`allowed|blocked|missing|unsupported_context` + `next_action`).

### 5. Hard bans

| Ban | Meaning |
|-----|---------|
| **No policy-specific spine** | Pack / document / citizenship / A1 / ZUS / client checklist must not mint a second life path |
| **No condition-as-route-infrastructure** | Missing Hub type/evidence ≠ “spine cannot exist” |
| **No bottom-up architecture** | Do not start from documents/rules and invent the person route |
| **No Walk-as-kernel** | Continuous Started under PEM-1 document load ≠ Full Spine PASS |
| **No neutral-as-bypass** | Kernel proof must not disable or skip the policy engine |

### 6. Defect classification (before any fix)

Every later STOP / defect is classified **before** remediation:

| Class | Means | Example |
|-------|-------|---------|
| **kernel defect** | Transition, ownership, handoff, identity, or host composition broken | Transfer does not create Employment case; IDs diverge |
| **policy / rule defect** | Wrong or incomplete ruleset for a context | PEM-1 admit missing BHP rule |
| **evidence / authority defect** | Proof exists but wrong SoT / Hub identity / alias | approved `code95` not seen as DQC |
| **integration defect** | Boundary/API/host wiring wrong while process and policy are sound | wrong host path; ACL scope miss |

A Code95 hole is **not** “Full Spine broken” unless classified as kernel.

### 7. Ordered program (after Accept)

| Step | Work | Proves / produces | Status |
|------|------|-------------------|--------|
| **1** | **Accept ADR-042** | Design rule: life path → processes → modules → policies/rules | **DONE** 2026-09-15 |
| **2** | Finish inventory I/O | Six-field cards P1–P6 | **DONE** |
| **3a** | Baseline Kernel proof attempt | Preflight: zero-requirement expressible? | **STOP** — Admit not a composable policy engine ([brief](../tasks/baseline-full-spine-kernel-proof.md)) |
| **3b** | **Admit policy / ruleset separation** | `employment_start_allowed.v1` = process-policy + pluggable ruleset (PEM-1 = one ruleset; `[]` → allowed штатно) | **OPEN** — [`admit-policy-ruleset-separation.md`](../tasks/admit-policy-ruleset-separation.md) |
| **3c** | Dual zero-policy preflight | Full Ready evaluator + Admit evaluator each → `allowed` under `[]` | After 3b PASS |
| **3d** | **Baseline Full Spine Kernel proof** (new person P1→P6) | Continuity, ownership, handoffs, identity; neutral ≠ bypass | After 3c |
| **4** | **PEM-1 Policy Composition proof** | Same каркас + PEM-1 ruleset may block | After kernel PASS |
| **5** | Ongoing defects | Classify per §6 before fix | Ongoing |

**Corollary (from Kernel preflight STOP):** zero-requirement is **not** a kernel special-case. It is a **mandatory property** of a composable policy engine. If empty composition cannot be evaluated correctly, rules are still embedded in topology.

Do **not** change architecture or write runtime for spine topology between steps 1–3. Do **not** open Contract/BHP/Code95 fixes **as Full Spine topology**.

---

## Consequences

### Positive

- Top-down platform that scales contexts without N spines.  
- Clear Full Spine vs PEM-1 proof split; neutral ≠ bypass.  
- Modules publish process contracts; neighbours stay ignorant of rule internals.  
- STOP diagnosis: kernel / policy-rule / evidence-authority / integration.

### Negative / cost

- Reclassify recent walks/gates.  
- Inventory I/O before kernel proof.  
- Resist “add Hub type to green Walk N” and “disable policy for kernel” as architecture.

### Compatibility

- Does not void RSO-2 / ESO-4 / ESA / ESO-5 PASSes.  
- Hub identity fixes remain valid **inside Employment/Recruitment policy evidence**, not as kernel substitutes.  
- Walks 1–4 retained as historical evidence — not Spine existence criteria.

---

## Alternatives considered

| Alternative | Reject |
|-------------|--------|
| Continue PEM-1 walks by fixing each document STOP | Bottom-up; conditions as route infrastructure |
| Per-vacancy / per-nationality spines | Forks life path; INV-07 |
| Equate Full Spine with PEM-1 | Confuses kernel with one policy composition |
| Treat Walk 4 Started as Full Spine PASS | Policy-laden ≠ kernel |
| Kernel proof via tenant flag / `if test` / internal skip | Neutral-as-bypass |

---

## Accept criteria

| # | Criterion | Status |
|---|-----------|--------|
| A1 | Accepted by Architecture canon owner | **MET** 2026-09-15 |
| A2 | Full Spine brief **NOT PASS** until baseline kernel proof; PEM-1 named separately | **MET** (hold) |
| A3 | Inventory holds life-path → process → module map + leak overlay; I/O excludes document types as topology | **MET** (P1–P6 cards CLOSED 2026-09-15) |
| A4 | Catalog / domain-map cross-refs | **MET** |
| A5 | Neutral ≠ bypass lock (§4a); defect classes (§6) are the remediation taxonomy | **MET** |

**Runtime / migrations:** not required for Accept. Not opened by Accept.

---

## Cross-references

| Doc | Role |
|-----|------|
| [`admit-policy-ruleset-separation.md`](../tasks/admit-policy-ruleset-separation.md) | Classified **policy/rule** fix — Admit process-policy vs PEM-1 ruleset |
| [`baseline-full-spine-kernel-proof.md`](../tasks/baseline-full-spine-kernel-proof.md) | Kernel proof **NOT PASS** (preflight STOP) |
| [`spine-policy-separation-inventory.md`](../tasks/spine-policy-separation-inventory.md) | P1–P6 six-field map **CLOSED** |
| [`three-host-full-spine-gate-pem1.md`](../tasks/three-host-full-spine-gate-pem1.md) | PEM-1-laden walks — historical |
| [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) | ADR index |
| [`hostflow-core-domain-map-v1.md`](hostflow-core-domain-map-v1.md) | Domain linkage |

---

## Changelog

- 2026-09-15: Proposed — Spine/Policy Separation.  
- 2026-09-15: Amended — top-down **path → process → module → policy**; explicit **Full Spine ≠ PEM-1**.  
- 2026-09-15: Amended — **neutral ≠ bypass**; module process contracts; ordered Accept→inventory→kernel→PEM-1; defect classes.  
- 2026-09-15: **Accepted** — no architecture/runtime change on Accept; next = inventory six-field I/O.  
- 2026-09-15: Inventory P1–P6 cards **CLOSED**; Baseline Kernel proof opened — [`../tasks/baseline-full-spine-kernel-proof.md`](../tasks/baseline-full-spine-kernel-proof.md).  
- 2026-09-15: Kernel preflight STOP → Admit is PEM-1 composition as evaluator; program inserts **Admit policy/ruleset separation** before retry — [`../tasks/admit-policy-ruleset-separation.md`](../tasks/admit-policy-ruleset-separation.md).
