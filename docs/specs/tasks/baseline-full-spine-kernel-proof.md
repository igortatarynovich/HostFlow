# Baseline Full Spine Kernel Proof

**Status:** **PASS** (2026-09-18 — single continuous new-person P1→P6 witness)  
**Layer:** L3 proof context — **not** L2 design · **not** a release gate · **not** PEM-1  
**Phase class:** platform  
**Opened:** 2026-09-15  
**Authorized:** 2026-09-18  
**Closed:** 2026-09-18  
**Named gate:** `baseline-full-spine-kernel-proof-gate`  
**Architecture parent:** [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) (**Accepted**)  
**Map prerequisite:** [`spine-policy-separation-inventory.md`](spine-policy-separation-inventory.md) — P1–P6 cards **CLOSED**  
**Authorization parents:** [`platform-modularization-isolation-cutover.md`](platform-modularization-isolation-cutover.md) **PASS** (PMI-X) · [`post-pmi-kernel-public-contract-preflight.md`](post-pmi-kernel-public-contract-preflight.md) **PASS** · [`recruitment-ready-policy-composition-separation.md`](recruitment-ready-policy-composition-separation.md) **PASS** · [`dual-zero-policy-preflight.md`](dual-zero-policy-preflight.md) **PASS** (retry)  
**Distinct from:** [`three-host-full-spine-gate-pem1.md`](three-host-full-spine-gate-pem1.md) (PEM-1-laden walks — historical evidence only)  
**Evidence:** `backend/tests/platform/test_baseline_full_spine_kernel_proof_gate.py`

> **Meaning of this proof:** HostFlow’s **каркас exists independently** of any particular HR policy.  
> One continuous witness under zero-requirement Ready + empty Admit.  
> Public-contract continuity held. PEM-1 may now open as the first production composition.

---

## Current authorization — 2026-09-18

| Prerequisite | Status |
|--------------|--------|
| PMI-X | **PASS** |
| Post-PMI public-contract preflight (Recruitment → Employment → Boundary → Documents → Workforce) | **PASS** |
| Recruitment Ready composition separation | **PASS** |
| Dual zero-policy retry (P1 `[]` → allowed · P4 `[]` → allowed via `*.public.*`) | **PASS** |

**Therefore:** P1→P6 Baseline Kernel witness was **AUTHORIZED**. Witness executed the same day → **PASS** below.

The preflight **STOP** of 2026-09-15 is **superseded for authorization purposes**. It remains **historical evidence** in the journal below — do not erase or rewrite that journal into a competing SoT.

---

## Original Goal → Completion Proof

**Problem this proof must permanently remove:**  
Inability to claim a stable person path P1→P6 without loading a production policy composition (PEM-1).

**Completion proof (named consumer) — MET:**

```text
One new person / application on real product hosts
  → walks process contracts P1 → P6
  → every policy point uses the real evaluator with minimal/zero-requirement composition
  → transitions execute through published module contracts (*.public.*)
  → allowed is штатно (neutral ≠ bypass)
  → one identity + traceability across all next contracts
  → including Started Employee contract → Workforce Input (P5→P6)
```

**Claim now authorized:** “каркас HostFlow exists independently of a specific кадровой политики.”  
PEM-1 may be the **first production policy composition** on this proved kernel.

**One continuous witness was enough.** No second confidence walk. Production variability → PEM-1.

---

## Witness journal — 2026-09-18 (PASS)

| Step | Transition | Public surface | Result |
|------|------------|----------------|--------|
| P1 | empty Ready → `allowed` / `transfer_allowed=true` | `recruitment.public.ready` | **PASS** |
| P2 | RFE validate + Employment accept | `boundary.public.ready` + `employment.public.commands.apply_employment_accept_policy` | **PASS** |
| P3 | Formalize + ensure Employee (not Started) | `employment.public.commands.formalize_employment_for_handoff` | **PASS** |
| P4 | empty Admit → `start_allowed=true` | `employment.public.commands.evaluate_start_allowed_for_handoff` | **PASS** |
| P5 | human Confirm → `employment_started.v1` / `started=true` | `employment.public.commands.confirm_employment_started_for_handoff` | **PASS** |
| P6 | Workforce public accepts Started Employee | `workforce.public.started` (`find_employee_by_candidate` + `ensure_hr_profiles_bundle`; Started fact present) | **PASS** |

**Identity continuity:** same `candidate_id` / `application_id` / `handoff_id` / `employee_id` recovered end-to-end.  
**Public-contract continuity:** transitions via `*.public.*` only; gate forbids private Workforce / handoff-create imports for performing the next step.  
**Neutral ≠ bypass:** empty Ready composition + `admit_ruleset_id=empty`; no `kernel_mode` / `neutral=true` / stuffing.  
**First-red discipline:** single continuous witness; no remaining-step shopping.

---

## Locked walk (executed)

```text
P1  new person/application
      → empty Ready composition → recruitment.public.* → verdict allowed / transfer_allowed=true
  → P2  RFE / handoff via Boundary (boundary.public.*) + Employment accept
  → P3  Formalize / ensure Employee (employment.public.*; Employee exists; not Started)
  → P4  empty Admit → employment.public.* → start_allowed=true
  → P5  human Confirm → employment_started.v1 → started=true
  → P6  Workforce public surface accepts the Started Employee contract
        (workforce.public.*; continuity — not Ready/Admit/evidence re-eval)
```

### Invariants held

| Invariant | Meaning |
|-----------|---------|
| **Public-contract continuity** | P1→P6 **executed** transitions through published module contracts (`*.public.*`). Persistence/audit inspected for identity/traceability. Private module machinery not used to perform the next transition |
| Process contracts only | Each step consumed prior **Output / next contract** |
| Neutral ≠ bypass | Same evaluators; zero-requirement composition |
| Single identity | Same person ids end-to-end |
| P5 → P6 explicit | Workforce **public** accepted Started Employee (not private helper merely because `employment_started.v1` exists) |
| First-red STOP | Applied (no defect catalog from skipped steps) |

---

## PASS / STOP

| Outcome | When |
|---------|------|
| **PASS** | One continuous new-person P1→P6 witness; invariants held (incl. public-contract continuity); P5→P6 via Workforce public; neutral ≠ bypass held |
| **STOP** | Named break + **defect class** + module owner; kernel remains **NOT PASS**; remaining steps not executed |

**Current:** **PASS** — see Witness journal.

---

## Preflight journal (2026-09-15) — historical evidence

> Superseded for **authorization**. Kept as historical evidence of the pre-PMI Ready composition gap. Do not treat as competing current SoT.

**Criterion checked:** can existing Recruitment and Admit evaluators express a **normal configuration with zero requirements** and return штатный `allowed` the same way as with a non-empty policy — **without** a special kernel/test/neutral mode?

### P1 / Recruitment (transfer-readiness / R5)

| Check | Result |
|-------|--------|
| Empty owner context → `r5_required_set({})` | **Non-empty** default: `passport`, `driver_license`, `driver_qualification_card`, `tachograph_card` |
| Штатный overlay `candidate.overrides[].remove` of those four (+ residency) | **`r5_required_set` → ∅** — empty required-set **is expressible** on the R5 merge contract |
| Full Ready zero-composition | **Not expressible** (as of 2026-09-15) — no Ready analog of `admit_ruleset_id=empty`; `recruitment_package` / confirmations / fields / slots / ops still gate `transfer_allowed` |

### P4 / Admit (`employment_start_allowed.v1`)

| Check | Result |
|-------|--------|
| Empty composition | **PASS** — `admit_ruleset_id=empty` → `[]` → `allowed` |
| Pipeline | resolve → evaluate → aggregate |

### Dual preflight (§3c) — 2026-09-15

| Field | Value |
|-------|--------|
| Outcome | **STOP** — [`dual-zero-policy-preflight.md`](dual-zero-policy-preflight.md) |
| P4 | **PASS** |
| P1 | **STOP** — policy→topology / non-composition layers inside Recruitment |
| Kernel | **Not opened** |

### Authorization path after PMI (summary — see Current authorization)

PMI-X **PASS** → public-contract preflight **PASS** → Ready composition separation **PASS** → dual zero-policy retry **PASS** → this witness **AUTHORIZED** → **PASS** 2026-09-18.

---

## Out of scope

- PEM-1 composition contents (opens **now** as next proof — separate artifact)  
- Second kernel walk after this PASS  
- Continuing Walks 1–4  
- Inventing kernel/test/neutral evaluator mode  
- Hiring E2E / Release Readiness  

---

## Next

1. Open **PEM-1 Policy Composition** proof on this proved kernel.  
2. Walks 1–4 remain historical evidence only.  
3. Do **not** re-run Kernel “for confidence.”

Banned still: `neutral=true` · `skip_requirements` · `kernel_mode` · test-only evaluator · evaluator-chooses-ruleset · stuffing to green Ready · private helpers to skip `*.public.*` transitions.
