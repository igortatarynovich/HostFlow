# Forms Product Layer P1.1 — Field Catalog Registry

**Status:** READY FOR REVIEW  
**Epic / P1:** [`forms-product-p1-field-catalog.md`](forms-product-p1-field-catalog.md)  
**Prerequisite:** P1 decomposition **ACTIVE** (`51063d1c` / #45)  
**Unlocks:** P1.2 Descriptors  
**Builder:** **LOCKED** (unlock only after P1.3)

---

## Goal

Stable **platform-wide** Field Catalog registry core — no UI, no Builder, no descriptors, no module extension API, no DB migration (code registry).

```text
register(component_id, component_version)
  → get exact · find · resolve_compatible · compatibility check
```

---

## DoD

- [x] Register by `component_id` + `component_version`  
- [x] Reject duplicate same version  
- [x] Get exact version  
- [x] Find available components (deterministic: id ASC, version DESC)  
- [x] Resolve latest compatible version (same major, `>=` requested)  
- [x] Compatibility check API  
- [x] Typed errors: duplicate · not found · incompatible · invalid semver  
- [x] Tenant-independent platform registry  
- [x] Contract + gate tests  
- [x] No Builder / renderers / module extensions / migrations  

---

## Compatibility model

| Segment | Meaning |
|---------|---------|
| **major** | breaking — clients never auto-jump majors |
| **minor** | backward-compatible within major |
| **patch** | fixes without contract change |

`resolve_compatible(id, requested)` → latest registered version with same major and version `>=` requested.

---

## Surface

| Artifact | Path |
|----------|------|
| Contract id | `forms.field_catalog.registry.v1` |
| Package | `backend/app/forms_platform/field_catalog/` |
| Tests | `test_forms_p1_1_registry_contract.py` · `test_forms_p1_1_registry_gates.py` |

---

## Out of scope

Builder · Public/Builder renderers · Validation/Normalization descriptors (P1.2) · Standard library (P1.3) · Extension API (P1.4) · Alembic

---

## History

- 2026-07-18: Opened for implementation after status `5c831e6d` (#46).
