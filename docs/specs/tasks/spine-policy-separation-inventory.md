# Inventory: Life path → Processes → Modules → Six-field cards

**Status:** **CLOSED** (P1–P6 six-field architectural map) — 2026-09-15  
**Layer:** L3 inventory — not Full Spine PASS · not a gap-fix · **no runtime**  
**Phase class:** platform  
**Opened:** 2026-09-15 · **Cards closed:** 2026-09-15  
**Parent:** [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) (**Accepted**)  
**Unlocks:** [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md)  
**Does not open:** Feature/gap-fix · architecture rewrite · PEM-1 as Spine · Hiring E2E · Release Readiness

> Cards define the **kernel map**. They do **not** prove the kernel.  
> Walks 1–4 = conflation evidence only — **not** Spine existence criteria.  
> Classified leaks stay **classified**; no automatic fix from this close.

---

## Original Goal → Completion Proof

**Problem removed by closing cards:**  
Ambiguous process boundaries that let document lists masquerade as topology.

**Completion proof (this file):**

```text
P1–P6 each have locked six fields (process contracts, not document lists)
  → P1 Ready leak classified (do not auto-fix)
  → P5→P6 contract stated; continuity proof deferred to kernel brief
  → Baseline Full Spine Kernel proof may open
```

---

## Program status (ADR-042 §7)

| Step | Item | Status |
|------|------|--------|
| 1 | Accept ADR-042 | **DONE** |
| 2 | Six-field I/O cards P1–P6 | **CLOSED** (this file) |
| 3a | Baseline Kernel preflight | **STOP** — Admit embeds PEM-1 as evaluator |
| 3b | Admit policy / ruleset separation | **PASS** — [`admit-policy-ruleset-separation.md`](admit-policy-ruleset-separation.md) (resolver ≠ evaluator; `[]` → allowed) |
| 3c | Dual zero-policy preflight (full Ready + Admit) | **STOP** — [`dual-zero-policy-preflight.md`](dual-zero-policy-preflight.md) (P4 PASS · P1 STOP) |
| 3c2 | Recruitment Ready policy / composition separation | **PARKED** — [`recruitment-ready-policy-composition-separation.md`](recruitment-ready-policy-composition-separation.md) until PMI **PASS** |
| PMI | Platform Modularization & Isolation Cutover | **OPEN** — [`platform-modularization-isolation-cutover.md`](platform-modularization-isolation-cutover.md) |
| 3c3 | Dual zero-policy preflight retry | **PASS** 2026-09-17 |
| 3d | Baseline Kernel P1→P6 witness | **PASS** 2026-09-18 — [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md) |
| 4 | PEM-1 Policy Composition proof | **OPEN** — Active Engineering ([`three-host-full-spine-gate-pem1.md`](three-host-full-spine-gate-pem1.md)) |
| 5 | Classified fixes only | Ongoing — no auto-fix from inventory |

**Corollary:** zero-requirement = property of composable policy engine, not a kernel special-case. `r5_required_set=∅` alone ≠ neutral Recruitment Ready.

---

## Field semantics (locked — every card)

| # | Field | Means | Must not mean |
|---|-------|-------|----------------|
| 1 | **Input** | Which **process contract** this module accepts | Which documents / requirements it demands |
| 2 | **State / work** | What the process **does with the person** | Checklist of evidence types |
| 3 | **Output** | Stable result **published outward** | Internal scoring / rule trace |
| 4 | **Transition owner** | **Single** owner of the transition into/out of this process step | Shared / ambiguous ownership |
| 5 | **Policy point** | Where policy/evaluator is invoked + **standard verdict shape** | Ruleset contents (Code95, BHP, …) |
| 6 | **Next contract** | What the **next** process receives **without** knowing prior rules | Copy of prior internals |

**Verdict shape (all policy points):** `allowed` | `blocked` | `missing` | `unsupported_context` (+ `next_action` where applicable). Neutral kernel uses the **same** shape with a **zero-requirement ruleset** (ADR-042 §4a — neutral ≠ bypass).

---

## Life path (каркас)

```text
Lead/Apply → Recruitment (P1) → Handoff (P2) → Employment formalize (P3)
  → Admit-to-work (P4) → Start (P5) → Workforce (P6) → …
```

---

## P1 — Recruitment

| Field | Locked value |
|-------|----------------|
| **Input** | Process contract: **person entered Recruitment** (Lead/Application/Candidate bound to a role/vacancy target). Not a document pack. |
| **State / work** | Selects and qualifies the person for Transfer: Fits decision, recruitment-missing resolution, Ready eligibility. |
| **Output** | Stable outward result: **Ready** or **not Ready** for Transfer (eligibility to leave Recruitment). |
| **Transition owner** | **Recruitment** alone. |
| **Policy point** | Transfer-readiness **evaluate** → standard verdict. Active **composition** selected by Ready resolver (not AND of every capability). Ruleset contents are **not** topology. |
| **Next contract** | Handoff (P2) receives: **Ready person + authority to emit** `ready_for_employment.v1` decisions. Handoff does not see Recruitment scoring/packs/rules. |

**Surfaces:** RSO-1 · transfer-readiness · Evidence as **inputs to policy only**.

### P1 Ready — classified leak (do not auto-fix)

| Item | Value |
|------|--------|
| **Observation** | Absence of a requirement (e.g. Code95 / any pack item) historically behaved as if **Recruitment topology could not be walked**, instead of штатный policy returning `blocked`/`missing` + `next_action` while the Ready **transition still exists**. |
| **Class** | **policy → topology leak** (evidence/authority defects on Walks 1–2 aggravated the symptom) |
| **Inventory action** | **Classify only** from inventory close. Dual preflight STOP classified Ready composition; that item is **PARKED** behind [`platform-modularization-isolation-cutover.md`](platform-modularization-isolation-cutover.md). |
| **Kernel implication** | Baseline Kernel proof must use **zero-requirement** Ready ruleset on the **real** evaluator so `allowed` is штатно — proving topology without curing the leak by bypass. Leak remediation remains a later **classified** fix if still present under non-zero rulesets. |

---

## P2 — Handoff / boundary

| Field | Locked value |
|-------|----------------|
| **Input** | Process contract from P1: **Ready + emit authority** for Transfer package decisions. |
| **State / work** | Moves ownership across the Recruitment→Employment boundary: immutable manifest, scope/write transition, Employment auto-init trigger. |
| **Output** | Stable outward result: **accepted boundary** — Employment may proceed on live Person/Docs + frozen decisions (no dossier copy). |
| **Transition owner** | **Split by axis (Accepted boundary):** Recruitment **owns emit**; Employment **owns accept**. No third owner. |
| **Policy point** | `employment_accept_policy.v1` (ESO-1) evaluate → standard verdict. Admit packs are **not** this policy. |
| **Next contract** | Employment formalize (P3) receives: **live authorities + manifest decisions + accepted case**. Does not receive Recruitment rule internals. |

**Surfaces:** RSO-2 / RSO-2C · boundary E2E **PASS** (piecewise).

---

## P3 — Employment formalize / ensure

| Field | Locked value |
|-------|----------------|
| **Input** | Process contract from P2: **accepted Employment case** on live Person/Docs + frozen Transfer decisions. |
| **State / work** | Prepares the person for employment identity: early employability → employment-missing resolution → formalize → Employee ensure. |
| **Output** | Stable outward result: **Employee exists** (employment identity), **not** Started. |
| **Transition owner** | **Employment** alone. |
| **Policy point** | `early_employability.v1` · `employment_missing_resolution.v1` · `employment_formalize.v1` (ESO-2…4) → standard verdicts. Thin formalize depth = policy/product depth, **not** a second spine. |
| **Next contract** | Admit-to-work (P4) receives: **Employee identity** available for admit evaluate. Does not receive Recruitment packs. |

**Surfaces:** ESO-2…4 machine **PASS**.

---

## P4 — Admit-to-work

| Field | Locked value |
|-------|----------------|
| **Input** | Process contract from P3: **Employee identity** (+ evidence views as **policy inputs**, not as Input contract). |
| **State / work** | Decides whether physical start is permitted **now**. |
| **Output** | Stable outward result: admit **verdict** (`allowed` / `blocked` / `missing` / `unsupported_context` + `next_action`). |
| **Transition owner** | **Employment** alone. |
| **Policy point** | `employment_start_allowed.v1` (ESA) evaluate → standard verdict. PEM-1 Contract/Medical/BHP = **ruleset**, not topology. |
| **Next contract** | Start (P5) receives: **admit `allowed`** (or must not Confirm). Start does not see admit rule internals. |

**Surfaces:** ESA · evidence authority (Walk 3 = evidence class, not topology).

---

## P5 — Start

| Field | Locked value |
|-------|----------------|
| **Input** | Process contract from P4: **admit `allowed`** + explicit human Confirm intent. |
| **State / work** | Records physical first day: Confirm → Started; **no** mint-on-confirm. |
| **Output** | Stable outward result: **`employment_started.v1` decision** with `started=true` (or `already_started`), `employee_id`, start fact/audit (`employee_physical_start`), continuous person linkage. |
| **Transition owner** | **Employment** alone (Confirm / Started). |
| **Policy point** | `employment_started.v1` evaluate/apply; first Confirm requires admit `allowed` (ESO-5 / slice 4) → standard decisions (`started` / `already_started` / `not_started` / `blocked` / …). |
| **Next contract** | Workforce (P6) receives the **Started Employee process contract** defined below — **not** “Employee somewhere exists.” |

**Surfaces:** ESO-5 slice 4 **PASS** (Employment spine closes Employee→Started). **P5→P6 continuity is not thereby proved.**

---

## P6 — Workforce

| Field | Locked value |
|-------|----------------|
| **Input** | Process contract from P5: **Started Employee** — see P5→P6 contract. |
| **State / work** | Operates the **active** employee after physical start (eligibility, assignments, post-start lifecycle). |
| **Output** | Stable outward result: **active-employee state + allowed Workforce ops**. |
| **Transition owner** | **Workforce** alone for post-start process transitions. |
| **Policy point** | Workforce process / operational-eligibility policies → standard verdict shape. Post-Start rules (e.g. ZUS timing) are **policy**, not pre-Start topology. |
| **Next contract** | Applicable later processes (Legalization / Posting) attach by context on the **same** person path — no second spine. |

### P5 → P6 — contract (must not be masked)

Kernel may **not** treat “`workforce_employees` row exists” as proof of Started→Workforce.

| Question | Architectural answer (card) | Kernel proof must show |
|----------|----------------------------|-------------------------|
| **What P5 Output is P6 Input?** | `employment_started.v1` **Started** result: `employee_id` + `started=true` (+ start fact/audit), same person continuity (candidate/handoff/employee ids recoverable). | One continuous witness: Confirm → Started → **Workforce product surface** accepts that same `employee_id` / person as **active** input |
| **Who owns identity after Start?** | **Employment identity materialization** remains the Employee record; **Workforce owns** post-start **operational** lifecycle/status for that Employee ([ownership card](../../modules/workforce/module_ownership_card.md)). | Owner of the **transition into Workforce work** is Workforce; Employment does not keep owning post-start ops |
| **What transition proves Started → Workforce?** | Process edge: **Started Employee contract published → Workforce accepts it as Input** (product host, not DB row peek). | Named step on real Workforce host/API in kernel proof — **until then: proof gap** |

| Item | Status |
|------|--------|
| Card definition | **CLOSED** (above) |
| Continuity proof | **OPEN** — required for Baseline Kernel **PASS**; absence blocks “kernel proved” |
| Auto gap-fix | **Forbidden** from this inventory close |

---

## Chain (process contracts only)

```text
P1 Output (Ready)                    → P2 Input
P2 Output (accepted boundary)        → P3 Input
P3 Output (Employee exists)          → P4 Input
P4 Output (admit allowed)            → P5 Input
P5 Output (Started Employee contract)→ P6 Input
```

---

## Layer 2 — Overlay summary

| Edge | Class | Action now |
|------|-------|------------|
| P4 Admit zero-requirement | **policy / rule** — **PASS** 2026-09-15 | Admit ruleset separation; `[]` → allowed; PEM-1 = ruleset |
| P1 Ready (requirement miss → route absent) | **policy → topology leak** | Dual preflight **STOP**; Ready composition **PARKED** behind PMI — [`platform-modularization-isolation-cutover.md`](platform-modularization-isolation-cutover.md) |
| P1 R5 empty via overlay remove | **note** | Empty R5 **expressible**; full Ready surface **not** zero-composable until 3c2 |
| P1 → P2 → P3 → P4 → P5 (named RSO/ESO/ESA) | **clean** (piecewise) | Compose in kernel proof |
| P3 → P4 evidence holes (Walk 3) | **evidence / authority** | Not topology; not auto-fix as spine |
| P5 → P6 | **proof gap** (contract defined; continuity unproved) | Must be witnessed in kernel proof |
| Walks 1–4 as Spine criteria | **framing leak** | Retained as evidence only |

**Composition verdict:** Process cards **compose one intended kernel**. Piecewise gates exist through P5. **Kernel is not proved** until Baseline proof walks P1→P6 under neutral ≠ bypass, including P5→P6.

---

## Explicit non-goals

- New feature / gap-fix from this close  
- Fixing P1 Ready leak automatically  
- Declaring kernel PASS because Employee exists  
- PEM-1 as Spine existence proof  
- Runtime / architecture change  

---

## Next

1. [`platform-modularization-isolation-cutover.md`](platform-modularization-isolation-cutover.md) — isolate spine modules before another evaluator fix.  
2. After PMI **PASS**, unpark [`recruitment-ready-policy-composition-separation.md`](recruitment-ready-policy-composition-separation.md).  
3. Re-run [`dual-zero-policy-preflight.md`](dual-zero-policy-preflight.md) until **PASS**.  
4. [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md) new-person P1→P6 — after 3c3 PASS.  
5. PEM-1 composition after kernel PASS.

Admit separation **PASS:** [`admit-policy-ruleset-separation.md`](admit-policy-ruleset-separation.md).  
Dual preflight **STOP:** [`dual-zero-policy-preflight.md`](dual-zero-policy-preflight.md).
