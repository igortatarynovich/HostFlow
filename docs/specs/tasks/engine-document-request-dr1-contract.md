# Engine → Document Request DR1-contract

**Status:** **PASS** [#302](https://github.com/igortatarynovich/HostFlow/pull/302)  
**Phase class:** platform  
**Branch:** `feat/engine-document-request-dr1-contract`  
**Parents:** [Entity Field Composition CL0](entity-field-composition-cl0-contract-seal.md) · [CL1](entity-field-composition-cl1-candidate-inventory.md) · [LI-1](lifecycle-identity-li1-existence-guard.md) · [Documents Platform E7](documents-platform-e7-document-requests.md) · [Sequential queue](sales-to-comms-sequential-queue.md)

> DR1-contract seals the **read/projection** chain from Requirement Engine evaluation to Hub ``outstanding_asks`` on ``documents.hub_adapter_v1``. E7 owns Hub consume; this slice owns Engine→ask mapping. **No mass generation.** Runtime creation of asks is **[DR1-runtime](engine-document-request-dr1-runtime.md)** (after Overlay Gate ∧ Reference R5).

---

## Original Goal → Completion Proof

**Problem:** E7 sealed Hub outstanding ask as required type + entity via Document Link, but Engine evaluation still had no named contract for projecting blockers / required documents into that Hub shape. Without DR1-contract, the next PR risks ad-hoc mapping or premature write paths.

**Completion proof:** ``engine_to_hub_outstanding_ask.v1`` maps ``requirement_engine`` evaluation → E7 ``outstanding_asks`` rows with canonical ``document_type_code`` values only. Boundary guard blocks competing projection producers. Named **DR1 Contract Gate** in CI.

**False close:** mass document generation; Hub request table; Catalog ``document.requested``; Candidate stage as Documents SoT; DR1-runtime write path inside this slice.

---

## Scope (contract only)

| In scope | Out of scope |
|----------|--------------|
| Contract module ``engine_to_hub_outstanding_ask_contract.py`` | Persisting / creating Hub asks ([DR1-runtime](engine-document-request-dr1-runtime.md)) |
| Projection from ``document_hub_bridge`` → ``{doc_type, state}`` | CL2+ Field Composition runtime |
| Canonical type ids via Document Type Registry (R3/R4) | E8-bind / E8-eval |
| Gate test + boundary guard | Mass D3–D9 bind |
| CI named **DR1 Contract Gate** | Activity / HR JSON as Documents SoT |

---

## Contract shape

```text
evaluate_requirement_rules(...)
  → map_requirement_evaluation_to_document_hub(...)
  → hub_section_to_outstanding_asks(...)
  → [{doc_type: <canonical>, state: missing|requested|problem}]
```

Hub adapter id: ``documents.hub_adapter_v1`` (E7). Contract id: ``engine_to_hub_outstanding_ask.v1``.

---

## Artifacts

| Artifact | Path |
|----------|------|
| Brief | this file |
| Contract | `backend/app/requirement_rules/engine_to_hub_outstanding_ask_contract.py` |
| Boundary guard | `scripts/architecture/check_engine_outstanding_ask_boundary.py` |
| Gate test | `backend/tests/requirement_rules/test_dr1_contract_gate.py` |

---

## DR1 Contract Gate (named)

PASS when:

1. Brief + contract module committed.  
2. Driver CE evaluation projects canonical ``outstanding_asks`` aligned with Hub required buckets.  
3. Boundary guard reports exactly one projection producer.  
4. No persistence / mass-generation helpers in the contract module.  
5. Named CI job runs ``test_dr1_contract_gate.py``.

---

## Queue position

**Depends on:** CL1 Gate ✅ · LI-1 Gate ✅ · Reference R3/R4 when contract names canonical type ids ✅  
**Unlocks:** CL2; [DR1-runtime](engine-document-request-dr1-runtime.md) ✅ [#313](https://github.com/igortatarynovich/HostFlow/pull/313) (join Reference R5 ∧ Overlay Gate)  
**Does not block:** later Product on Reference R5 (only DR1-runtime parked there; now unblocked)
