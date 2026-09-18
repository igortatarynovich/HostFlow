# Platform Modularization & Isolation Cutover

**Status:** **PASS** (PMI-0…**PMI-X PASS** 2026-09-16; program exit CLOSED)
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
PMI-1  Enforcement freeze (new leaks illegal)           ← PASS 2026-09-16
PMI-R  Recruitment → ISOLATED                           ← PASS 2026-09-16
PMI-B  Boundary → ISOLATED                              ← PASS 2026-09-16
PMI-E  Employment → ISOLATED                            ← PASS 2026-09-16
PMI-D  Documents → ISOLATED                             ← PASS 2026-09-16
PMI-W  Workforce → ISOLATED                             ← PASS 2026-09-16
PMI-UI Design system v1 + forbid parallel primitives   ← PASS 2026-09-16
PMI-X  Program exit                                      ← PASS 2026-09-16
```

Unlock ≠ schedule. Do not start PMI-R in the PMI-0 PR. Do not start PMI-B before Recruitment ISOLATED. **PMI-UI** is not a component library drop: it locks platform primitives (layout, nav, entity card, status/verdict, actions, forms, evidence) **and** CI/architecture enforcement that **rejects new parallel primitives** where a platform primitive already exists. Module compositions consume those primitives. Without that forbid rule, backend isolation still leaves product reinvented on the frontend. ADR-011 remains the UI standard; the gap is **runtime kit + parallel-primitive enforcement** ([`PRIMITIVES_AUDIT.md`](../frontend/PRIMITIVES_AUDIT.md)).

### PMI-1 — enforcement freeze (PASS criteria)

**Narrow contract.** PMI-1 remediates nothing and moves no code between modules. It installs a ratchet.

| Rule | Machine meaning |
|------|-----------------|
| Baseline authority | `module_isolation_pmi0_baseline.json` content from commit **`844900d6`** (sha256 pinned in `module_isolation_pmi1_freeze.json`) |
| Frozen debt | All **2006** structural cross-owner edges `(from_file, import, to_file)` — debt, not architectural permission |
| New cross-owner edge vs debt | **FAIL** |
| Edge removal (import gone) | **PASS**; debt may shrink via `--shrink-debt` |
| Add edge to debt/authority | **FAIL** (not “update snapshot”) |
| Ownership/prefix remap that hides a still-present debt import | **FAIL** |
| Move code to `UNASSIGNED` to drop a forbidden edge from the cross-owner set while import remains | **FAIL** (hide rule) |
| PMI-0 `--write` after freeze | **FAIL** — authority immutable |

| Deliverable | Path |
|-------------|------|
| Freeze lock | `scripts/architecture/module_isolation_pmi1_freeze.json` |
| Debt allowlist (shrink-only) | `scripts/architecture/module_isolation_pmi1_debt.json` |
| Checker | `scripts/architecture/check_module_isolation_freeze.py` |
| Gate | `backend/tests/platform/test_module_isolation_pmi1_freeze_gate.py` |

**Platform invariant after PMI-1 PASS:**

> Architectural debt may only shrink. New cross-module coupling is rejected.

**PMI-1 PASS:** freeze checker green; authority sha matches `844900d6`; debt ⊆ authority; current ⊆ debt; no hide; no Ready/Kernel/policy work in the freeze PR.  
**PMI-X PASS.** Program exit CLOSED. **Ready is not auto-unfrozen.** Post-PMI cycle: public-contract Kernel preflight → classified fix only on STOP → dual zero-policy → P1→P6 → PEM-1. Preflight **STOP** 2026-09-17 (Recruitment). Active: [`recruitment-ready-policy-composition-separation.md`](recruitment-ready-policy-composition-separation.md).

### PMI-R — Recruitment ISOLATED (PASS 2026-09-16)

Eight-row card CLOSED. Published surface = `backend/app/modules/recruitment/public/`. Ready = Recruitment policy authority (parked rewrite). Debt **2006→1799**. CI: `check_recruitment_isolation.py` (new foreign→Recruitment internals FAIL; allowlist shrink-only).

### PMI-B — Boundary ISOLATED (PASS 2026-09-16)

Eight-row card CLOSED. Narrow charter: RFE package + handoff/trace only — not Ready, not Admit, not Documents, not Workforce. Published surface = `backend/app/modules/boundary/public/`. Named foreign→Boundary internals = **0**. Debt **1799→1746**. EXC-PMI-R-FUNNEL preserved for PMI-E. CI: `check_boundary_isolation.py`.

### PMI-E — Employment ISOLATED (PASS 2026-09-16)

Eight-row card CLOSED. Owns Formalize/Admit/Start; Admit rulesets + ESO-5 internals private; `employment.public.*` only. EXC-PMI-B-EMP closed; EXC-PMI-R-FUNNEL×6 closed (not renamed). EXC-PMI-B-DOC deferred to PMI-D. Debt **1746→1705**. CI: `check_employment_isolation.py`.

### PMI-D — Documents ISOLATED (PASS 2026-09-16)

Eight-row card CLOSED. Evidence facts only via `documents.public.*` — not Ready/Admit/Workforce lifecycle. EXC-PMI-B-DOC closed. DQC/Contract/BHP semantics not rewritten. Debt **1705→1612**. CI: `check_documents_isolation.py`.

### PMI-W — Workforce ISOLATED (PASS 2026-09-16)

Eight-row card CLOSED. Accepts Started Employee continuity via `workforce.public.*`; does not reconstruct Ready/RFE/Admit/evidence. Employment writes only through public. Debt **1612→1557**. Not Kernel witness. CI: `check_workforce_isolation.py`.

### PMI-UI — Design system ISOLATED (PASS 2026-09-16)

Four DoD levels CLOSED on spine surfaces. Authority via `platform/design-system` + `ui_primitive_authority.json`. Decision ownership prefers backend verdicts. UI debt allowlist **8** (shrink-only). Not a full frontend rewrite. CI: `check_ui_isolation.py`. Kernel remains parked.

### PMI-X — Program exit (PASS 2026-09-16)

Joint **verification only** (not remediation; **fixes nothing**). PASS is **HEAD-simultaneous**: historical PMI-R/B/E/D/W/UI stamps alone are insufficient — full suite green together on one revision. Five spine cards ISOLATED; B/E/D/W foreign internals = 0; Recruitment spine foreign internals = 0 (non-spine residual ≤63 shrink-only); backend debt **2006→1557 (−449)**; UI debt **8**; Ready/Kernel/PEM-1 not smuggled. **Ready is not auto-unfrozen.** Debt need not reach zero. Defect at exit → STOP + separate work item. CI: `check_pmi_x_program_exit.py`.

Program boundary closed: `PMI-0 → PMI-1 → R → B → E → D → W → UI → PMI-X`.

### After PMI-X (different proof cycle)

Order: **Public-contract Kernel preflight** ([`post-pmi-kernel-public-contract-preflight.md`](post-pmi-kernel-public-contract-preflight.md)) → classified module-local fix **only if that preflight STOPs** → dual zero-policy PASS → new P1→P6 witness → PEM-1.

**External chain (Recruitment):** `policy composition → recruitment.public.* → verdict / transition permission` (incl. zero-requirement). Symmetric for Boundary / Employment / Documents / Workforce via their `*.public.*`. Forbidden external probes include `recruitment_package`, `VERIFICATION_SLOT_DEFS`, `requirement_engine`, or any facade bypass. Outward = contracts/verdicts; inward = owner only after classified STOP. Old dual-preflight STOP remains a fact about the old runtime — not an auto-resume of Ready composition.

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

### PMI-1 — freeze (CLOSED — do not reopen as remediation)

See **PMI-1 — enforcement freeze** above. Do not mix remediation into the freeze PR.

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
- **2026-09-16** — PMI-X Program exit **PASS**: joint machine gate green; five ISOLATED + UI; debt 2006→1557; UI debt 8; spine public contracts enforced. Post-X = Kernel preflight on public contracts (not auto-resume pre-PMI plan).
- **2026-09-16** — PMI-UI Design system **ISOLATED PASS**: four DoD levels; `platform/design-system`; UI debt **8**; `check_ui_isolation.py`. PMI-X queued. Ready/Kernel remain parked.
- **2026-09-16** — PMI-W Workforce **ISOLATED PASS**: `workforce.public.*`; foreign internals = 0; Started Employee intake sealed; debt **1612→1557**; card `docs/modules/workforce/module_isolation_card.md`. PMI-UI queued. Ready/Kernel remain parked.
- **2026-09-16** — PMI-D Documents **ISOLATED PASS**: `documents.public.*` evidence contracts; foreign internals = 0; EXC-PMI-B-DOC closed; debt **1705→1612**; card `docs/modules/documents/module_isolation_card.md`. PMI-W queued. Ready/Kernel remain parked.
- **2026-09-16** — PMI-E Employment **ISOLATED PASS**: `employment.public.*`; foreign internals = 0; EXC-PMI-B-EMP + EXC-PMI-R-FUNNEL closed; debt **1746→1705**; EXC-PMI-B-DOC → PMI-D; card `docs/modules/employment/module_isolation_card.md`. PMI-D queued. Ready/Kernel remain parked.
- **2026-09-16** — PMI-B Boundary **ISOLATED PASS**: `boundary.public.*` (`ready`/`handoff`/`models`/`emit`/`dto`); named foreign internals = 0; debt **1799→1746**; EXC-PMI-R-FUNNEL left for PMI-E; card `docs/modules/boundary/module_isolation_card.md`. PMI-E queued. Ready/Kernel remain parked.
- **2026-09-16** — PMI-R Recruitment **ISOLATED PASS**: public package `backend/app/modules/recruitment/public/`; Ready classified as Recruitment policy (not rewritten); spine helpers/ORM via public; debt **2006→1799**; `check_recruitment_isolation.py` + allowlist shrink-only; card `docs/modules/recruitment/module_isolation_card.md`. PMI-B queued. Ready/Kernel remain parked.
- **2026-09-16** — PMI-0 map **PASS**: deterministic owner|UNASSIGNED for all `backend/app/**/*.py`; spine `required_prefixes`; committed reproducible `module_isolation_pmi0_baseline.json` (1275 files; 574 UNASSIGNED; 2006 cross-owner edges = full leak set, no manual public filter).
- **2026-09-16** — PMI-1 freeze **PASS**: authority `844900d6` pinned; debt = 2006 structural edges; new edge / debt growth / ownership hide / UNASSIGNED hide / authority mutate → FAIL. No remediation. PMI-R not started.
