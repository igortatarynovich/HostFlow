# Dual zero-policy preflight (P1 Ready + P4 Admit)

**Status:** **STOP** (2026-09-15) — P4 Admit **PASS**; P1 full Ready **STOP** (policy→topology / non-composition layers)  
**Layer:** L3 preflight — **not** Kernel walk · **not** new-person witness · **not** PEM-1 composition  
**Phase class:** platform  
**Opened:** 2026-09-15  
**Closed:** 2026-09-15 (STOP — do not open P1→P6)  
**Architecture:** [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) §7 step **3c**  
**Depends on:** [`admit-policy-ruleset-separation.md`](admit-policy-ruleset-separation.md) **PASS**  
**Named gate:** `dual-zero-policy-preflight-gate`  
**Does not open:** Baseline Kernel P1→P6 · PEM-1 composition · candidate mint · evidence upload · Ready architecture rewrite

> Answers two questions only.  
> **No** new person. **No** Kernel walk.  
> Green `transfer_allowed` by stuffing a candidate with data/docs is **forbidden**.

---

## Original Goal → Completion Proof

**Problem this preflight must permanently remove (before Kernel):**  
Uncertainty whether **both** process-policy surfaces can return штатный `allowed` under a **zero-requirement composition** on the **real** evaluate path (neutral ≠ bypass).

**Completion proof (named consumer):**

```text
P1 Recruitment — FULL Ready surface (all layers)
  → zero-requirement composition selected штатно
  → ordinary evaluate → allowed / transfer_allowed=true

P4 Admit
  → resolve_admit_ruleset_v1 selects empty (admit_ruleset_id=empty)
  → same resolve → evaluate → aggregate → allowed / start_allowed=true

Negative: no test/env bypass, forged Ready/start_allowed, seed helpers, kernel branches

BOTH green → preflight PASS → may open Baseline Kernel witness
EITHER red → preflight STOP → classify; do not open Kernel
```

---

## Results (2026-09-15)

| Policy point | Result | Evidence |
|--------------|--------|----------|
| **P4 Admit** | **PASS** | `admit_ruleset_id=empty` → resolver `rules=[]` → evaluate → `start_allowed=true` (same pipeline as PEM-1) |
| **P1 Ready** | **STOP** | `r5_required_set=∅` expressible; **full** Ready has **no** empty-composition authority; layers outside R5 still participate in `transfer_allowed` |
| **Dual preflight** | **STOP** | Admit fixed; Ready still embeds non-composition requirements as process topology |

**Kernel walk:** **NOT opened.**

---

## P4 Admit — PASS detail

| Check | Result |
|-------|--------|
| Resolver authority | `resolve_admit_ruleset_v1` |
| Composition | `admit_ruleset_id=empty` → `ruleset_id=empty`, `rules=[]` |
| Pipeline | resolve → evaluate → aggregate (no short-circuit) |
| Verdict | `decision=start_allowed`, `start_allowed=true` |
| Resolve failure still distinct | third-country pathway → `unsupported_context` (not empty) |

---

## P1 Ready — STOP classification

**Critical criterion:** after R5 requirements are removed, any remaining obligation must be classified — **why that layer does not obey the chosen Recruitment policy composition**. Do **not** add candidate data/docs to green the preflight.

### What R5∅ proves

| Fact | Status |
|------|--------|
| Full remove overlay → `r5_required_set(preview_context(), delta) == ∅` | **Expressible** (штатный overlay) |
| R5∅ alone = neutral Recruitment Ready | **False** (inventory corollary) |

### What still participates in `transfer_allowed` (outside R5 composition)

From `TransferPolicyResolver.resolve` (`transfer_policy_v1`):

```text
transfer_allowed =
    handoff_allowed          # workforce eligibility / document_packs ops
  ∧ readiness_ok             # eligibility profiles
  ∧ docs_ready               # missing/pending docs (R5-linked — emptiable)
  ∧ pkg.ready                # recruitment_package (PR16 dossier / slots)
  ∧ ¬required_confirmations  # recruiter_confirmation
  ∧ ops_ready                # operational_requirements (e.g. first_contact)
```

Plus PE transition gate / field_requirements / requirement_engine pack slots when `target_stage=ready_for_handoff`.

| Layer (`source_layer`) | Obeys R5∅ / Ready empty composition? | Class | Notes |
|------------------------|--------------------------------------|-------|-------|
| `document_packs` / R5 | **Yes** (emptiable via overlay) | **policy / rule** | Necessary but not sufficient |
| `recruitment_package` | **No** — hardcoded `VERIFICATION_SLOT_DEFS` + Contacts block | **policy → topology leak** | Dossier topology not a pluggable ruleset |
| `recruiter_confirmation` | **No** — hardwired confirmation machine | **policy → topology leak** | After R5∅, blocks flip to `ready` → *more* unconfirmed_block pressure |
| `field_requirements` | **No** — PE seeded phone/email/address | **policy / rule** | No Ready `ruleset_id=empty` lever |
| `requirement_engine` pack slots | **No** — pack manifests / slots not emptied by R5∅ | **policy / rule** | Composition incomplete |
| `operational_requirements` | **No** — catalog (`first_contact_completed`) | **policy / rule** | Not under R5 overlay |
| `process_engine_handoff_rules` / destinations | Routing | routing | `require_destination=False` → warning only for `transfer_allowed` |

**No** Ready analog of Admit `admit_ruleset_id=empty` exists on `TransferPolicyResolver` / PE adapter.

**Why STOP (not a candidate defect):** zero-requirement was selected only for **R5 membership**. Remaining layers are **not subordinate** to that composition — they still act as route infrastructure for Ready. Stuffing contacts/docs/confirmations would **mask** the leak, not prove composition.

---

## Negative proof (both points)

| Banned | Held |
|--------|------|
| `neutral=true` / `kernel_mode` / `skip_requirements` | Absent on Admit path; Ready has no such green path either |
| Forged `transfer_allowed` / `start_allowed` | Not used |
| Seed helpers minting Ready/Started | Not used |
| Test-only / env short-circuit evaluators | Not used |
| New person / Kernel walk | **Not opened** |

---

## PASS / STOP

| Outcome | When |
|---------|------|
| **PASS** | P1 full Ready **and** P4 Admit both штатный `allowed` under zero-composition on real evaluators |
| **STOP** | Named hole + class — **this close** |

**Current:** **STOP** (P4 PASS · P1 STOP).

---

## Next

1. **Classified Ready work** (separate item): make full Recruitment Ready a composable policy engine — empty composition → `transfer_allowed=true` without topology leaks (`recruitment_package` / confirmations / slots / fields / ops).  
2. Re-run **this** dual preflight until **PASS**.  
3. Only then: [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md) new-person P1→P6.  
4. PEM-1 composition only after kernel PASS.

**Do not** open Kernel walk from this STOP.
