# Forms Product Layer P1.4 — Extension API

**Status:** **READY FOR IMPLEMENTATION**  
**Prerequisite:** P1.3 Standard Library **COMPLETE** ([`forms-product-p1-3-standard-library.md`](forms-product-p1-3-standard-library.md) · `0cf7fc00` / #52)  
**Closes:** Forms Product Layer **P1** (after this DoD)  
**Then:** P2 Builder — without returning to Field Catalog architecture  
**Canon:** [`forms-product-p1-field-catalog.md`](forms-product-p1-field-catalog.md)

---

## Goal

Modules register their own Catalog components through a **separate public extension surface**. Extension components use the **same** Registry + Descriptor validations as Basic. Builder sees one unified catalog via existing read APIs — it does **not** distinguish Basic vs extension.

```text
module → Extension API
       → same Registry.register + Descriptor validation
       → source = platform | module:<id>
       → Builder/Public clients: find / get / get_descriptors (unchanged)
```

---

## Preferred boundaries (normative)

1. **Separate public surface** for module registration (not Registry internals).  
2. Extension components pass the **same** Registry + Descriptor validations as stdlib.  
3. **Forbidden:** overriding Basic (`forms.field.*` stdlib) components.  
4. **Forbidden:** silent replacement of an already-registered `(component_id, version)`.  
5. **Source** recorded as `platform` or a concrete **module identifier**.  
6. Failure of one module’s registration **must not** corrupt the whole Catalog.  
7. **No tenant-level extensions** in P1.4 (platform/module scope only).  
8. Builder does **not** know Basic vs extension — unified read surface after bootstrap.  

---

## Scope

### In

- Public extension registration API (e.g. `register_module_component` / pack bootstrap)  
- `source` / ownership metadata on component records  
- Reject Basic id override + reject silent version replace (typed errors)  
- Isolated per-module registration errors (partial success OK)  
- Contract tests: module components visible via public find/get/descriptors  
- Gate: no Catalog-core `if module == ...` special cases; no tenant extensions  

### Out

- Builder UI (P2)  
- Themes / Analytics  
- Tenant-scoped component packs  
- Rewriting Registry / Descriptors / Stdlib contracts  

---

## DoD (implementation gate)

- [ ] Public extension registration surface  
- [ ] Same Registry + Descriptor validation path as Basic  
- [ ] Basic override blocked; silent version replace blocked  
- [ ] `source` = `platform` | `module:<id>`  
- [ ] One module failure does not wipe Catalog  
- [ ] No tenant-level extensions  
- [ ] Builder/read APIs unchanged (unified catalog)  
- [ ] Contract + gate tests green  
- [ ] P1 marked COMPLETE; P2 Builder may start  

---

## History

- 2026-07-18: Stub opened with P1.3.  
- 2026-07-19: **READY FOR IMPLEMENTATION** after P1.3 merge `0cf7fc00` (#52); boundaries fixed.
