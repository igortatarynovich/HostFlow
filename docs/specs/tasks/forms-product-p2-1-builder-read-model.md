# Forms Product Layer P2.1 — Builder Read Model

**Status:** **READY FOR IMPLEMENTATION**  
**Epic / P2:** [`forms-product-p2-builder.md`](forms-product-p2-builder.md) · design ACTIVE (`a142bd0c` / #55)  
**Prerequisite:** P1 Foundation **CLOSED** · Field Catalog v1 **FROZEN**  
**Unlocks:** P2.2 Composition Model  
**UI:** **FORBIDDEN** until P2.1–P2.4 + UI gate  

---

## Goal

Give Builder a stable **read model** over the existing unified Field Catalog — without a private type database and without reopening Catalog architecture.

```text
Catalog.find / get / get_descriptors
  → BuilderReadModel (palette · search · descriptor view)
  → no register · no stdlib import · no Basic vs Extension branch
```

---

## Scope

### In

- Load unified component list via public Catalog APIs  
- Search and filter (Catalog `find` / read-model projection)  
- Fetch descriptor by `component_id` + `component_version`  
- Project Catalog descriptors into Builder-facing read DTOs  
- Contract tests: palette source = Catalog only; origin does not change behavior  

### Out

- Composition / draft commands (P2.2–P2.3)  
- Persistence (P2.4) · UI (P2.5)  
- Catalog mutation · component registration  
- Direct stdlib / extension imports  
- Validation / normalization execution  

---

## DoD

- [ ] Read model loads unified Catalog list  
- [ ] Search / filter work without private type store  
- [ ] Descriptor fetch by id + version  
- [ ] Basic and extension treated equally  
- [ ] No `component_id == ...` hardcode; no Catalog writes  
- [ ] Contract + gate tests green  

---

## History

- 2026-07-19: Opened READY FOR IMPLEMENTATION after P2 design ACTIVE (`a142bd0c` / #55).
