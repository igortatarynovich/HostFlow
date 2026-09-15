# Gap-fix: DOCUMENT_REQUIRED ↔ Hub storage aliases (transfer-readiness)

**Status:** **PASS** (2026-09-15)  
**Layer:** L3 proof / gap-fix — **not** Full Spine reopen · **not** Documents catalog retouch  
**Phase class:** product  
**Opened:** 2026-09-15  
**Closed:** 2026-09-15  
**Parent STOP:** [`three-host-full-spine-gate-pem1.md`](three-host-full-spine-gate-pem1.md) Walk journal 2 — candidate `f5841c06-f2ff-4b3c-a376-6a7c4834e6f3`  
**Depends on:** [`dqc-catalog-pack-bridge-gap.md`](dqc-catalog-pack-bridge-gap.md) **PASS** (inbound DQC → Hub `code95`)  
**Does not open:** Full Spine PASS · second Hub type · `driver_license_with_code95` product work · pack rename

> Catalog write path already stores `driver_qualification_card` as Hub **`code95`**.  
> This gap is the **requirement evaluation / transfer-readiness consumer** that still exact-matched the pack code.  
> Fix uses existing **canonical/legacy mapping authority** — no DQC-specific `if`.

---

## Original Goal → Completion Proof

**Problem this gap must permanently remove:**  
Approved Hub `code95` does not satisfy DOCUMENT_REQUIRED(`driver_qualification_card`) because `evaluate_requirement_rules` looks up `doc_index[doc_code]` literally — so transfer-readiness stays blocked after a correct Documents create.

**Completion proof (named consumer):**

```text
DOCUMENT_REQUIRED(driver_qualification_card)
  → resolve via document_type_canonical_bridge (ref ↔ Hub storage keys)
  → find approved Hub code95
  → requirement satisfied / no document_missing for DQC
  → machine gate green
  → then new Full Spine Walk 3 (new person; not f5841c06-…)
```

**Decision:** **PASS** — machine gate `document-required-hub-alias-gate` green  
(`backend/tests/platform/test_document_required_hub_alias_gate.py`; CI job wired).

---

## Expected semantics (locked)

```text
DOCUMENT_REQUIRED receives requirement code
  → resolves through existing canonical document bridge
  → searches corresponding Hub documents
  → approved code95 satisfies driver_qualification_card
```

| Forbidden | Required |
|-----------|----------|
| `if doc_code == "driver_qualification_card": check code95` | Reuse `hub_storage_keys_for_requirement_code` / `normalize_legacy_doc_type` / `legacy_codes_for_ref_canonical` |
| New per-consumer alias tables in requirement_engine | One shared lookup helper on the canonical bridge |
| Weakening the requirement when no Hub evidence | Missing storage aliases still → `document_missing: driver_qualification_card` |

---

## Implementation (closed)

| Surface | Change |
|---------|--------|
| `document_type_canonical_bridge.hub_storage_keys_for_requirement_code` | Shared ordered keys (exact + ref + legacy aliases) |
| `requirement_rules.evaluator._lookup_document_for_requirement` | DOCUMENT_REQUIRED uses shared authority |
| `document_runtime.delivery_contract.resolve_required_type_runtime_via_contract` | Same shared keys (no private alias table) |

---

## Machine proof (named gate) — PASS

**Gate id:** `document-required-hub-alias-gate`

1. **Exact-code regression:** Hub document typed as the requirement code still satisfies.  
2. **Canonical alias:** requirement `driver_qualification_card` + approved Hub `code95` → **satisfied** (no `document_missing` for DQC).  
3. **Negative regression:** no `code95` (and no exact DQC row) → still `document_missing: driver_qualification_card`.

---

## Next after PASS

Restart backend → **Walk 3** new person from scratch → Full Spine PASS only if continuous walk completes. Do **not** resume `f5841c06-…`. Full Spine remains **NOT PASS** until composition PASS.
