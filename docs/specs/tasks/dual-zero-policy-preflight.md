# Dual zero-policy preflight (P1 Ready + P4 Admit)

**Status:** **PASS** (retry 2026-09-17) — P1 Ready **PASS** · P4 Admit **PASS**  
**Layer:** L3 preflight — **not** Kernel walk · **not** new-person witness · **not** PEM-1 composition  
**Phase class:** platform  
**Opened:** 2026-09-15  
**Closed (prior):** 2026-09-15 (**STOP** — P4 PASS · P1 STOP)  
**Closed (this retry):** 2026-09-17 (**PASS**)  
**Architecture:** [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) §7 step **3c**  
**Depends on:** [`admit-policy-ruleset-separation.md`](admit-policy-ruleset-separation.md) **PASS** · [`recruitment-ready-policy-composition-separation.md`](recruitment-ready-policy-composition-separation.md) **PASS** · [`post-pmi-kernel-public-contract-preflight.md`](post-pmi-kernel-public-contract-preflight.md) **PASS**  
**Named gate:** `dual-zero-policy-preflight-gate`  
**Next:** [`three-host-full-spine-gate-pem1.md`](three-host-full-spine-gate-pem1.md) — PEM-1 Policy Composition (**OPEN** after Kernel **PASS** 2026-09-18)  
**Does not open:** PEM-1 composition · candidate mint as dual proof · five Ready layer gap-fixes · re-litigation of Ready composition internals

> Answers two questions only.  
> **No** new person. **No** Kernel walk in this artifact.  
> Green by stuffing documents / confirmations / ops facts is **forbidden**.  
> Ready composition authority is already **PASS** — this retry is **consumer-level** only.

---

## Original Goal → Completion Proof

**Problem this preflight must permanently remove (before Kernel):**  
Uncertainty whether **both** process-policy surfaces can return штатный `allowed` under a **zero-requirement composition** on the **real** evaluate path (neutral ≠ bypass).

**Completion proof (named consumer — retry):**

```text
P1 Recruitment
  → ready_composition_id=empty  (штатная registered composition)
  → recruitment.public.ready.evaluate_ready_transfer
  → decision=allowed / transfer_allowed=true
  → policy capabilities NOT invoked (minimal fixture)

P4 Employment
  → admit_ruleset_id=empty  (штатный registered ruleset)
  → employment.public.commands.evaluate_start_allowed_for_handoff
  → decision=start_allowed / start_allowed=true
  → no contract/medical/bhp stuffing

Negative: no test/env bypass, forged Ready/start_allowed, seed helpers, kernel branches

BOTH green → preflight PASS → may open Baseline Kernel witness (separate artifact)
EITHER red → preflight STOP → classify; do not open Kernel
```

---

## Results (prior 2026-09-15 — STOP)

| Policy point | Result | Evidence |
|--------------|--------|----------|
| **P4 Admit** | **PASS** | `admit_ruleset_id=empty` → resolve → evaluate → `start_allowed=true` |
| **P1 Ready** | **STOP** | No empty-composition authority on full Ready; non-R5 layers still gated `transfer_allowed` |
| **Dual preflight** | **STOP** | Admit fixed; Ready not composable |

**Kernel walk:** **NOT opened.**

---

## Results (retry 2026-09-17 — PASS)

| Policy point | Result | Evidence |
|--------------|--------|----------|
| **P1 Ready** | **PASS** | `recruitment.public.ready` + `ready_composition_id=empty` → `decision=allowed` / `transfer_allowed=true` on minimal candidate; package/fields/ops/eligibility **not** invoked |
| **P4 Admit** | **PASS** | `employment.public.commands.evaluate_start_allowed_for_handoff` + `admit_ruleset_id=empty` → `decision=start_allowed` / `start_allowed=true`; evidence views `None` (no stuffing) |
| **Dual preflight** | **PASS** | Both independent zero-policy configurations green on production pipelines via `*.public.*` |

**Evidence:** `backend/tests/platform/test_dual_zero_policy_preflight_gate.py`.

**Not re-proved here:** Ready composition resolver internals / capability table (closed by Ready composition separation **PASS**).

**Kernel walk:** still **NOT opened** by this PASS — opens only via separate Baseline Kernel witness artifact.

---

## P1 Ready — PASS detail (retry)

| Check | Result |
|-------|--------|
| Public contract | `recruitment.public.ready.evaluate_ready_transfer` |
| Composition | `ready_composition_id=empty` (registered; same pipeline as driver) |
| Fixture | Minimal candidate (no phone/email/docs/confirmations) |
| Non-invocation | document_packs / package / fields / ops **not** called under `[]` |
| Verdict | `decision=allowed`, `transfer_allowed=true` |
| Bypass flags | Absent (`kernel_mode` / `skip_requirements` / `neutral`) |

---

## P4 Admit — PASS detail (retry)

| Check | Result |
|-------|--------|
| Public contract | `employment.public.commands.evaluate_start_allowed_for_handoff` |
| Composition | `admit_ruleset_id=empty` → host → resolve → evaluate → aggregate |
| Fixture | Minimal handoff + employee identity; evidence views empty |
| Verdict | `decision=start_allowed`, `start_allowed=true`, `ruleset_id=empty` |
| Resolve failure still distinct | third-country pathway → `unsupported_context` (unchanged Admit property) |

---

## Negative proof (both points)

| Banned | Held |
|--------|------|
| `neutral=true` / `kernel_mode` / `skip_requirements` | Absent |
| Forged `transfer_allowed` / `start_allowed` | Not used |
| Seed helpers minting Ready/Started | Not used |
| Test-only / env short-circuit evaluators | Not used |
| Stuffing docs / confirmations / ops to green empty | Forbidden; P1 spies enforce non-invocation |
| New person / Kernel walk | **Not opened** |
| Re-opening Ready composition internals proof | Out of scope (already PASS) |

---

## PASS / STOP

| Outcome | When |
|---------|------|
| **PASS** | P1 and P4 both штатный `allowed` under empty composition via `*.public.*` on real pipelines |
| **STOP** | Named hole + module owner — do not open Kernel |

**Current:** **PASS** (2026-09-17 retry).

---

## Next

1. Open [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md) — **new** P1→P6 Baseline Kernel witness on a new person/application (continuous path across isolated modules).  
2. PEM-1 composition only after Kernel witness **PASS**.  
3. Do **not** treat this dual PASS as Kernel PASS.
