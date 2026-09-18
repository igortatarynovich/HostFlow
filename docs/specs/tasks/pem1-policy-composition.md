# PEM-1 Policy Composition Proof

**Status:** **PASS** (2026-09-18 — dual-boundary blocking + satisfied on one continuous identity)  
**Layer:** L3 proof context — **not** L2 redesign · **not** a release gate · **not** a new Kernel / Full Spine proof  
**Phase class:** platform  
**Opened:** 2026-09-18  
**Closed:** 2026-09-18  
**Named gate:** `pem1-policy-composition-gate` (`test_pem1_policy_composition_gate.py` — 4 passed)  
**Architecture parent:** [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) (**Accepted**) §4 / §7 step 4 — **program closed through this stamp**  
**Kernel prerequisite (PASS):** [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md) — continuous P1→P6 under empty Ready + empty Admit (**do not mix with this stamp**)  
**Historical walks (not this proof):** [`three-host-full-spine-gate-pem1.md`](three-host-full-spine-gate-pem1.md) — Walks 1–4 **HISTORICAL**; not an open Full Spine gate  
**Inventory:** [`spine-policy-separation-inventory.md`](spine-policy-separation-inventory.md) step 4  
**Composition ids:** Ready `driver` · Admit `PEM-1` (Contract / Medical / BHP)  
**Evidence:** `backend/tests/platform/test_pem1_policy_composition_gate.py`

> **Claim authorized:** The same proved P1→P6 Kernel exists **without** PEM-1.  
> PEM-1 only selects **which** Ready / Admit rules apply — it changes **permission**, not **topology**.

---

## Hard boundary (locked)

| This proof **is** | This proof **is not** |
|-------------------|------------------------|
| First **production policy composition** on a proved Kernel | A new Full Spine / Kernel witness |
| Proof that PEM-1 Ready + PEM-1 Admit wire correctly on the **same** P1→P6 process | Continuation of Walks 1–4 |
| Blocking + satisfied semantics under ADR-042 | “Fix the next document and walk further” |
| Classification of every red before any fix | Auto-remediation mid-walk |
| Consumer of Kernel / public contracts | License to change Kernel topology for PEM-1 |

**Kernel remained closed for this slice.** No Kernel edits.

---

## Original Goal → Completion Proof — MET

```text
Proved Kernel (empty Ready + empty Admit already PASSed)
  → Recruitment selects PEM-1 Ready composition (driver)
  → existing Recruitment capabilities apply per that composition
  → Ready verdict (missing/blocked with next_action when unsatisfied;
                   allowed when satisfied)
  → Boundary / RFE unchanged topology
  → Employment selects PEM-1 Admit composition (Contract / Medical / BHP)
  → Admit verdict (same missing/blocked vs allowed discipline)
  → when composition is satisfied, the same Kernel reaches
       Confirm → employment_started.v1 → Workforce public
```

---

## Dual-boundary lock (mandatory) — held

Part A and Part B proved at **both** policy boundaries on the **same** continuous witness.

### Locked witness sequence (executed)

```text
Recruitment boundary
  driver + missing → missing/blocked + next_action
  → provide exactly the required Ready evidence/facts
  → same person/application
  → driver + satisfied → allowed
  → RFE

Employment boundary
  PEM-1 Admit + missing Contract/Medical/BHP → missing/blocked + next_action
  → provide exactly the required Admit evidence/facts
  → same person/application/handoff/employee
  → PEM-1 + satisfied → allowed / start_allowed=true
  → Confirm → Started → Workforce
```

**`next_action` criterion (held):** consequence of active composition; after satisfying Contract, re-eval named the next outstanding PEM-1 requirement (not Contract again); after all Admit evidence → `allowed`.

---

## Witness journal — 2026-09-18 (PASS)

| Step | Boundary | Result | Classification |
|------|----------|--------|----------------|
| Ready A | `driver` + missing dossier | `missing` + `next_action` (`document_packs` / composition-driven); `transfer_allowed=false`; route intact | **expected policy block** |
| Ready B | same person; satisfy Ready layers | `allowed` / `transfer_allowed=true`; composition still `driver` | Part B |
| RFE | Boundary validate | `ready_for_employment.v1` valid | topology unchanged |
| Accept / Formalize / ensure | Employment public | accepted + Employee | Kernel path |
| Admit A | `PEM-1` + no evidence | `missing` + primary Contract; `start_allowed=false` | **expected policy block** |
| Admit progression | Contract only | still `missing`; primary ≠ Contract (next composition req) | composition-driven `next_action` |
| Admit B | Contract + Medical + BHP | `start_allowed=true` | Part B |
| Confirm → Started → Workforce | public | `started=true`; Workforce public accepts | Kernel continuity |

No unexpected red. No Kernel topology change.

---

## STOP classification (normative — used)

| Class | When | Effect |
|-------|------|--------|
| **expected policy block** | Composition correctly returns `missing`/`blocked` + composition-driven `next_action` | Part A evidence |
| **policy / rule** | Wrong / incomplete / unexpected composition behavior | STOP |
| **evidence / authority** | Evidence exists but authority does not see it | STOP |
| **kernel / integration regression** | Transition/identity/public contract broken vs Kernel PASS | STOP — not PEM-1 feature |

### Kernel immutability lock — held

PEM-1 did **not** change Kernel topology.

---

## False close (reject) — none applied

| Reject | Why |
|--------|-----|
| Walks 1–4 continuous Started | Historical only |
| Kernel empty-composition PASS alone | Not PEM-1 wiring |
| Part A only on Admit | Violates dual-boundary lock |
| `next_action` unrelated to composition | Rejected by criterion |
| PEM-2 / universal DSL mid-slice | Out of scope |

---

## PASS / STOP

| Outcome | When |
|---------|------|
| **PASS** | Dual-boundary Part A + Part B; composition-driven `next_action`; Kernel untouched |
| **STOP** | Named break + class + module owner |

**Current:** **PASS**.

---

## Out of scope (unchanged)

- Re-proving Kernel · Walks 1–4 · PEM-2 / DSL / all professions  
- Hiring E2E / Release Readiness  
- ZUS / Insurance pre-Start · A1 / legalization in this composition  

---

## Next

1. **ADR-042 ordered program closed** through step 4 (Kernel + PEM-1). Do **not** auto-open PEM-2 / further compositions / policy DSL.  
2. **Engineering track returns to product-driven scheduling:** next Engineering item only by queue amendment from the **next HostFlow product goal** — not “another composition as pretext for foundational refactoring.”  
3. Walks 1–4 stay [`three-host-full-spine-gate-pem1.md`](three-host-full-spine-gate-pem1.md) **HISTORICAL** — not an open Full Spine gate.  
4. Classified residual debt only via new work items. Do **not** reopen Kernel or re-run PEM-1 “for confidence.”
