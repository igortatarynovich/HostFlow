# Platform Modularization & Isolation Cutover

**Status:** **OPEN** (PMI-0 map **PASS** 2026-09-16; Active Engineering waits for **PMI-1** start in its own PR)  
**Layer:** L2 operating program — **not** an ADR · **not** Full Spine PASS · **not** Module Independence recertification  
**Phase class:** platform  
**Opened:** 2026-09-16  
**Named gate:** [`platform-modularization-isolation-cutover-gate.md`](../gates/platform-modularization-isolation-cutover-gate.md)  
**Architecture parents:** [`ADR-002`](../architecture/ADR-002-modular-recruitment-hr-boundary.md) · [`ADR-023`](../architecture/ADR-023-recruitment-sales-module-separation.md) · [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) · AGENTS Rules 2, 3, 6, 7 · [`module-ownership-coverage.md`](../gates/module-ownership-coverage.md)  
**Does not supersede:** `MODULE_INDEPENDENCE_PROGRAM_PASS` (2026-05-29) — that closeout certified **documents**, not runtime isolation  
**Does not open:** Recruitment Ready composition · Kernel walk · PEM-1 · Hiring E2E · new ADR for “modules should be isolated”

> Result is measured by **ISOLATED cards + CI**, not by the number of markdown files.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**

Product work (Ready, Admit, Full Spine, new vacancy kinds, new screens) is forced to reconstruct domain decisions from mixed authorities, cross-module internals, and per-screen UI. Module Independence, ADR-042, ownership cards, and facade allowlists exist; **runtime still does not obey them**. Adding a warehouse worker still requires touching global lifecycle slots. Each E2E walk surfaces another generation of the same leak.

**Completion proof (named consumer):**

```text
Warehouse worker is added by changing Recruitment policy composition only.
Admit-to-work requirement is added by changing Employment policy only.
New evidence type is added inside Documents only.
New screen is composed from the platform design system + module-owned composition.
Spine walk Recruitment → Handoff → Employment → Start → Workforce
  calls only public process contracts
  (Recruitment Ready, Ready for Employment, Employment Admit, Started Employee).
CI rejects a new Recruitment → Documents internal import.
A closed ISOLATED card exists for Recruitment, Boundary, Employment, Documents, Workforce.
Only then Full Spine / Kernel may unpark.
```

---

## Why this, not Ready composition

Admit ruleset separation **PASS** fixed one Employment evaluator. Dual preflight then proved P1 Ready is still several machines AND-ed as topology. Opening Ready composition now is the same class of local repair: it does not create module isolation, authority uniqueness, or UI composition.

[`recruitment-ready-policy-composition-separation.md`](recruitment-ready-policy-composition-separation.md) is **PARKED**.  
[`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md) stays **blocked** until this program **PASS**.

Module Independence closeout remains historically true of five **document packs**. [`module-ownership-coverage.md`](../gates/module-ownership-coverage.md) §5 already records the Rule 7 gap: no CI that a domain is isolated. This program **closes that gap in runtime**, starting with the spine.

---

## Architecture review (ten questions)

| # | Answer |
|---|--------|
| 1 Owner | Architecture canon owner (program) + module owner on each ISOLATED card |
| 2 Existing? | Yes: Rules 2/7, MIP cards, ADR-002/023/042, allowlist scanners. **Not done:** physical isolation + deny-new-leak CI + one write authority per fact |
| 3 Adapter | Public process contracts only (facade / delivery / event / DTO). No new Catalog capability |
| 4 Boundary | Does not rewrite L0. Does not mint Compliance/Payroll domains. Does not move Ready/Kernel into this PR |
| 5 Settings | No new settings dump |
| 6 SoT | One write owner per state/fact/decision/policy; readers consume contracts |
| 7 Events | Module-owned; no new security event types for program open |
| 8 Requires | PMI-0 fact map before any module cutover. Enforcement freeze (PMI-1) before reducing leaks |
| 9 Licence | None |
| 10 Public contract | Additive publication of existing spine contracts; internals hidden. Breaking only via named exception retirement |

---

## Definition of Done — module ISOLATED

A module is **ISOLATED** only when its [`module_isolation_card.md`](../../modules/_template/module_isolation_card.md) is **CLOSED** with **machine evidence** for every row:

| # | Row | Closed means |
|---|-----|----------------|
| 1 | Owner | Named owner; card not “baseline-established” without a runtime package |
| 2 | Public contract | Versioned inbound/outbound process contracts (commands, events, verdicts). Neighbours name **only** these |
| 3 | Policy authorities | Each policy engine (requirements, packs, confirmations, eligibility, admit, …) has one write owner; spine **calls** the module and receives a verdict |
| 4 | Internal state hidden | Foreign modules do not read ORM/internal helpers/rulesets/exceptions of this module |
| 5 | Cross-module dependencies | Allowed edges enumerated. Everything else is a leak |
| 6 | UI surface | Module compositions listed; they use design-system primitives; no parallel kit |
| 7 | Legacy leaks | Each remaining leak is in the exception registry with owner + expiry, **or** deleted |
| 8 | Enforcement | CI fails a **new** forbidden import / authority write. Allowlist may only shrink |

**CERTIFIED** (MIP 2026-05-29) ≠ **ISOLATED**. HR/Workforce having no `backend/app/modules/<name>` package is a PMI finding, not a footnote.

---

## In-scope modules (finite)

Spine first, one module at a time after the map and freeze:

| Order | Module | Public contracts (targets, not today’s internals) |
|-------|--------|-----------------------------------------------------|
| 1 | **Recruitment** | Recruitment Ready (leave Recruitment / Transfer permission) |
| 2 | **Boundary** | Ready for Employment (`ready_for_employment.v1` emit + accept) |
| 3 | **Employment** (HR) | Employment Admit (`employment_start_allowed.v1`); Started Employee (`employment_started.v1`) |
| 4 | **Documents** | Evidence / Hub delivery — facts, not lifecycle verdicts |
| 5 | **Workforce** | Workforce Input (accepts Started Employee; does not reconstruct Admit) |

Out of this program’s **PASS** (owned elsewhere, must not grow new spine leaks): Sales, Forms, Acquisition, Communication, Integrations. They remain subject to PMI-1 freeze (no **new** edges into spine internals).

Not created here: Legalization, Posting, Compliance-as-domain, Billing, Fleet.

---

## Locked sequence

```text
PMI-0  Fact map (code + imports + UNASSIGNED paths)     ← PASS 2026-09-16
PMI-1  Enforcement freeze (new leaks illegal)           ← next (own PR)
PMI-R  Recruitment → ISOLATED
PMI-B  Boundary → ISOLATED
PMI-E  Employment → ISOLATED
PMI-D  Documents → ISOLATED
PMI-W  Workforce → ISOLATED
PMI-UI Design system v1 + forbid parallel primitives
PMI-X  Program exit gate
```

Unlock ≠ schedule. Do not start PMI-R in the PMI-0 PR. Do not start PMI-B before Recruitment ISOLATED. **PMI-UI** is not a component library drop: it locks platform primitives (layout, nav, entity card, status/verdict, actions, forms, evidence) **and** CI/architecture enforcement that **rejects new parallel primitives** where a platform primitive already exists. Module compositions consume those primitives. Without that forbid rule, backend isolation still leaves product reinvented on the frontend. ADR-011 remains the UI standard; the gap is **runtime kit + parallel-primitive enforcement** ([`PRIMITIVES_AUDIT.md`](../frontend/PRIMITIVES_AUDIT.md)).

### PMI-0 — complete map (PASS criteria)

**Not** “scanner printed large numbers.” Large UNASSIGNED / edge counts are a **baseline**, not a close.

| # | Property | Evidence |
|---|----------|----------|
| 1 | Every `backend/app/**/*.py` is classified **deterministically** as exactly one owner **or** explicit `UNASSIGNED` | Scanner exit 0; `backend_file_count == sum(file_counts)`; ambiguous longest-prefix collision → STOP |
| 2 | Every spine owner has **declared package/prefix boundaries** that match ≥1 file each (`required_prefixes`) | `module_isolation_owners.json` + scanner validate |
| 3 | The **same scanner** reproducibly emits the leak set that becomes PMI-1 input | Committed `module_isolation_pmi0_baseline.json`; `check_module_isolation_map.py --check` |

**Hard rules for PMI-0:**

- Leak set = **all** cross-owner import edges. No manual “these look public” exclusions before freeze.
- `public_name_markers` / informal allowlists are **forbidden** in PMI-0.
- UNASSIGNED is valid debt; inventing owners to shrink the number is STOP.

| Deliverable | Path |
|-------------|------|
| Owner map | `scripts/architecture/module_isolation_owners.json` |
| Scanner | `scripts/architecture/check_module_isolation_map.py` |
| Baseline (PMI-1 input) | `scripts/architecture/module_isolation_pmi0_baseline.json` |
| Gate | `backend/tests/platform/test_module_isolation_pmi0_map_gate.py` |

**PMI-0 PASS:** three properties above green; CI `--check` green; **no ISOLATED claim**; Ready/Kernel still parked.  
**PMI-0 STOP:** incomplete classification, missing spine roots, baseline drift, or hand-curated leak exceptions.

### PMI-1 — freeze (separate slice; not this commit)

Freeze **exactly** the PMI-0 baseline leak set:

- current cross-owner edges = technical debt  
- **new** cross-owner edge = CI failure  
- **allowlist growth** = CI failure  

Do not remediate the 2000+ edges in PMI-1. Do not mix PMI-1 into the PMI-0 stamp commit.

---

## STOP / park list (normative)

Do **not** start while this program is OPEN:

1. [`recruitment-ready-policy-composition-separation.md`](recruitment-ready-policy-composition-separation.md) — **PARKED**
2. Dual-preflight retry as a substitute for isolation
3. [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md) Kernel walk
4. PEM-1 composition proof
5. Another ADR restating Rule 2 / ADR-042
6. Another conceptual audit in place of PMI-0
7. Per-screen product design outside PMI-UI primitives

MA-3 (Mapping Operator) is a **different write-set**. It must not add a third UI kit and must not import spine internals. It is **not** this program and does **not** unpark Full Spine.

---

## False close (reject)

| Claim | Why reject |
|-------|------------|
| Scanner printed large UNASSIGNED / edge counts | Baseline ≠ complete map; need the three PMI-0 properties |
| All MIP cards exist | Documentation only (Rule 7 gap) |
| Admit / RSO / ESO named gates PASS | Piecewise spine ≠ isolated modules |
| Ready composition PASS | Local evaluator fix; not program DoD |
| Allowlist grew | PMI-1 forbids growth |
| Hand-curated “public” import exceptions in PMI-0 | Freeze would cement wrong classification |
| “Logical isolation” without package/facade cut | Physical isolation is row 4+8 |
| Kernel green via bypass / empty special-case | Neutral ≠ bypass (ADR-042) |
| Component library without parallel-primitive CI | PMI-UI false close |

---

## Program PASS / STOP

| Outcome | When |
|---------|------|
| **PASS** | PMI-X: five spine ISOLATED cards CLOSED; PMI-UI v1 locked; PMI-1 allowlist did not grow vs PMI-1 freeze (only shrink); named gate green |
| **STOP** | Missing card, unknown import, dual write authority, UI parallel kit, or Kernel/Ready started before PASS |

After **PASS**, Full Spine unparks as: each transition calls the owning module’s public contract. Code95, BHP, contract, nationality, posting, A1 stay inside owners.

---

## История

- **2026-09-16** — Program opened. Ready composition **PARKED**. Kernel remains blocked.
- **2026-09-16** — PMI-0 map **PASS**: deterministic owner|UNASSIGNED for all `backend/app/**/*.py`; spine `required_prefixes`; committed reproducible `module_isolation_pmi0_baseline.json` (1275 files; 574 UNASSIGNED; 2006 cross-owner edges = full leak set, no manual public filter). PMI-1 not started.
