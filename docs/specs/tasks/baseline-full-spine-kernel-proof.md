# Baseline Full Spine Kernel Proof

**Status:** **OPEN** (proof brief — **NOT PASS**; STOP at preflight 2026-09-15)  
**Layer:** L3 proof context — **not** L2 design · **not** a release gate · **not** PEM-1  
**Phase class:** platform  
**Opened:** 2026-09-15  
**Architecture parent:** [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) (**Accepted**)  
**Map prerequisite:** [`spine-policy-separation-inventory.md`](spine-policy-separation-inventory.md) — P1–P6 cards **CLOSED**  
**Distinct from:** [`three-host-full-spine-gate-pem1.md`](three-host-full-spine-gate-pem1.md) (PEM-1-laden walks — historical evidence only)

> **Meaning of this proof:** HostFlow’s **каркас exists independently** of any particular HR policy.  
> **Not** “driver docs green.” **Not** Walk 4 continued.  
> **No code** from this brief. No seed / bypass / operator-set verdicts.

---

## Original Goal → Completion Proof

**Problem this proof must permanently remove:**  
Inability to claim a stable person path P1→P6 without loading a production policy composition (PEM-1).

**Completion proof (named consumer):**

```text
One new person on real product hosts
  → walks process contracts P1 → P6
  → every policy point uses the real evaluator with minimal/zero-requirement ruleset
  → allowed is штатно (neutral ≠ bypass)
  → one identity + traceability across all next contracts
  → including Started Employee contract → Workforce Input (P5→P6)
```

Only **PASS** here authorizes: “каркас HostFlow exists independently of a specific кадровой политики.”  
Only after that may PEM-1 be the **first production policy composition** on a proved kernel.

---

## Locked walk

```text
P1 Recruitment Ready     (zero-requirement Ready ruleset → evaluate → allowed)
  → P2 Handoff / RFE     (ready_for_employment.v1 emit + accept)
  → P3 Formalize/ensure  (Employee exists; not Started)
  → P4 Admit-to-work     (zero-requirement admit ruleset → evaluate → allowed)
  → P5 Start Confirm     (employment_started.v1 → started=true)
  → P6 Workforce Input   (Started Employee contract accepted on Workforce product surface)
```

### Must hold on the witness

| Invariant | Meaning |
|-----------|---------|
| Process contracts only | Each step consumes prior **Output / next contract** — not prior rule internals |
| Neutral ≠ bypass | Same evaluators as production; **zero-requirement ruleset**; no `if test`, tenant disable-policy, internal skip, operator-set `start_allowed`, seed Started |
| Single identity | Same person: candidate / application / handoff / employee ids recoverable end-to-end |
| P5 → P6 explicit | Not “Employee row exists” — Workforce **Input** = Started Employee contract from P5 Output |
| Three hosts | Recruitment · Boundary · Employment; Workforce surface for P6 |

### False close (reject)

| Reject | Why |
|--------|-----|
| PEM-1 / Walks 1–4 continuous Started | Different proof; policy-laden |
| Sum of RSO/ESO/ESA PASSes | Piecewise ≠ composition |
| Bypass / seed / forged verdicts | Violates ADR-042 §4a |
| Employee exists without Workforce accepting Started contract | Masks P5→P6 |
| Fixing Code95/BHP mid-walk “to green kernel” | Wrong class; kernel uses zero-requirement ruleset |

---

## STOP classification (mandatory before any fix)

| Class | Use when |
|-------|----------|
| **kernel** | Transition / ownership / handoff / identity / host composition broken |
| **policy / rule** | Ruleset wrong (should not appear under zero-requirement; if it blocks, misconfiguration) |
| **evidence / authority** | Proof/SoT identity wrong (should not be required under zero-requirement) |
| **integration** | Product host/API wiring fails while contracts are sound |

**P1 Ready leak** (inventory): if zero-requirement still cannot yield штатный `allowed` via evaluate, classify carefully — may be **kernel** or **integration** on the Ready surface, not “add Code95.” Do **not** auto-open document gap-fixes.

**P5→P6:** if Started succeeds but Workforce product surface cannot accept Started Employee as Input → **kernel** or **integration** proof gap — blocks PASS.

---

## PASS / STOP

| Outcome | When |
|---------|------|
| **PASS** | One continuous P1→P6 witness; invariants held; P5→P6 shown; neutral ≠ bypass held |
| **STOP** | Named break + **defect class**; kernel remains **NOT PASS** |

**Current:** **NOT PASS** — Admit separation **PASS**; dual preflight **STOP**; Ready composition **PARKED**; Kernel walk **blocked** until [`platform-modularization-isolation-cutover.md`](platform-modularization-isolation-cutover.md) **PASS**.

---

## Preflight journal (2026-09-15) — before walk

**Criterion checked:** can existing Recruitment and Admit evaluators express a **normal configuration with zero requirements** and return штатный `allowed` the same way as with a non-empty policy — **without** a special kernel/test/neutral mode?

### P1 / Recruitment (transfer-readiness / R5)

| Check | Result |
|-------|--------|
| Empty owner context → `r5_required_set({})` | **Non-empty** default: `passport`, `driver_license`, `driver_qualification_card`, `tachograph_card` |
| Штатный overlay `candidate.overrides[].remove` of those four (+ residency) | **`r5_required_set` → ∅** — empty required-set **is expressible** on the R5 merge contract |
| Full Ready zero-composition | **Not expressible** — no Ready analog of `admit_ruleset_id=empty`; `recruitment_package` / confirmations / fields / slots / ops still gate `transfer_allowed` |

### P4 / Admit (`employment_start_allowed.v1`)

| Check | Result |
|-------|--------|
| Empty composition | **PASS** — `admit_ruleset_id=empty` → `[]` → `allowed` |
| Pipeline | resolve → evaluate → aggregate |

### Dual preflight (§3c)

| Field | Value |
|-------|--------|
| Outcome | **STOP** — [`dual-zero-policy-preflight.md`](dual-zero-policy-preflight.md) |
| P4 | **PASS** |
| P1 | **STOP** — policy→topology / non-composition layers inside Recruitment |
| Kernel | **Not opened** |

---

## Out of scope

- PEM-1 composition (separate proof after PASS)  
- Auto-fixing inventory P1 Ready leak without classified Ready composability work  
- Inventing kernel/test/neutral evaluator mode to green this proof  
- Hiring E2E / Release Readiness  

---

## Next

1. [`platform-modularization-isolation-cutover.md`](platform-modularization-isolation-cutover.md) — **OPEN**.  
2. After PMI **PASS**, unpark [`recruitment-ready-policy-composition-separation.md`](recruitment-ready-policy-composition-separation.md).  
3. Re-run dual zero-policy preflight until **PASS**.  
4. Then new-person P1→P6 on **this** brief.  
5. PEM-1 composition only after kernel PASS.

Banned still: `neutral=true` · `skip_requirements` · `kernel_mode` · test-only evaluator · evaluator-chooses-ruleset · stuffing candidate data to green Ready.

## Next after PASS

1. Open **PEM-1 Policy Composition** proof on the **same** kernel (driver Recruitment + admit Contract/Medical/BHP may block).  
2. Walks 1–4 remain historical evidence only.
