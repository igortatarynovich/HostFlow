# Forms Product Layer P1.2 — Component Descriptors

**Status:** READY FOR REVIEW  
**Prerequisite:** P1.1 Registry **COMPLETE** ([`forms-product-p1-1-registry.md`](forms-product-p1-1-registry.md) · `644b102a` / #47)  
**Unlocks:** P1.3 Standard library — **READY** after this merge  
**Builder:** **LOCKED** (until P1.3)  
**Canon:** [`forms-product-p1-field-catalog.md`](forms-product-p1-field-catalog.md)

---

## DoD delivered

- [x] Four declarative descriptors: Builder, Public, Validation, Normalization  
- [x] Unified contract `forms.field_catalog.descriptors.v1`  
- [x] Strict per-descriptor schema  
- [x] Ban executable logic / callbacks / eval-exec / framework-specific keys  
- [x] Bound to `component_id` + `component_version`  
- [x] Registry `get_descriptors` / `get_descriptor` / `get_descriptors_compatible`  
- [x] Validate descriptors at registration / `build_component_record`  
- [x] Typed errors: missing · invalid · unsupported  
- [x] JSON-serializable, deterministic output  
- [x] Contract + gate tests  
- [x] No UI-renderers · no Standard Library · no module extensions · no migrations  

---

## Normative rule

**Descriptors must be declarative and must not contain executable logic.**

Runtimes interpret descriptors; descriptors never run code. Same contract for web, mobile, and future clients.

---

## Surface

| Artifact | Path |
|----------|------|
| Contract | `forms.field_catalog.descriptors.v1` |
| Module | `backend/app/forms_platform/field_catalog/descriptors.py` |
| Registry API | `get_descriptors` · `get_descriptor` · `get_descriptors_compatible` |
| Tests | `test_forms_p1_2_descriptors_contract.py` · `test_forms_p1_2_descriptors_gates.py` |

---

## History

- 2026-07-18: Opened as READY after P1.1 merge `644b102a` (#47).  
- 2026-07-18: Design **ACTIVE** after #48 / #49; declarative-only rule.  
- 2026-07-18: Implementation READY FOR REVIEW.
