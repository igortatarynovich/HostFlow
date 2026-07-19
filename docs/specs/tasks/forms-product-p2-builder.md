# Forms Product Layer P2 — Builder

**Status:** **ACTIVE** (design · after merge `a142bd0c` / [PR #55](https://github.com/igortatarynovich/HostFlow/pull/55))  
**Prerequisite:** P1 Product Layer Foundation **CLOSED** (merge `97aac4e3` / [PR #54](https://github.com/igortatarynovich/HostFlow/pull/54) · status `a142bd0c` / #55)  
**Catalog:** Field Catalog public contracts v1 **FROZEN** ([`forms-field-catalog-v1-freeze.md`](../architecture/forms-field-catalog-v1-freeze.md))  
**Canon:** [`forms-product-layer-epic.md`](forms-product-layer-epic.md)  
**Next sprint:** [`forms-product-p2-1-builder-read-model.md`](forms-product-p2-1-builder-read-model.md) · **READY FOR IMPLEMENTATION**

---

## Closed / active gates (after PR #55)

| Gate | Status |
|------|--------|
| P2 Builder Design | ✅ **ACTIVE** |
| **P2.1 Builder Read Model** | **READY FOR IMPLEMENTATION** |
| Field Catalog v1 | **FROZEN** |
| P1 Foundation | **CLOSED** |
| P3 Publish UI | **LOCKED** |
| P4 Themes | **LOCKED** |
| P5 Analytics | **LOCKED** |

---

## Hard boundary (normative)

Builder is a **thin client of frozen Field Catalog v1**. It may only:

1. **Read** the unified Catalog (existing find / get / descriptors APIs).  
2. **Assemble** form composition (instances, order, config).  
3. **Persist** draft composition for the existing publish path.

Builder **must not**:

- create or invent component types;  
- duplicate validation or normalization;  
- know or branch on Basic vs module extension;  
- reopen Field Catalog architecture;  
- own storage / domain mapping / second intake.

```text
Catalog (frozen v1) → Builder reads unified list
                    → places instances + config
                    → saves draft composition
                    → Publish / Public / validate / normalize unchanged
```

---

## Decomposition

| Sprint | Name | Goal | UI? |
|--------|------|------|-----|
| **P2.1** | Builder Read Model | Stable read model over Catalog | no |
| **P2.2** | Composition Model | Canonical draft structure | no |
| **P2.3** | Composition Commands | add/remove/reorder/config/draft ops | no |
| **P2.4** | Draft Persistence | Persist composition for existing publish | no |
| **P2.5** | Minimal Builder UI | Palette · canvas · config · save | **yes** (after gate) |

### P2.1 — Builder Read Model (**READY FOR IMPLEMENTATION**)

See [`forms-product-p2-1-builder-read-model.md`](forms-product-p2-1-builder-read-model.md).

- Load unified component list  
- Search / filter  
- Get descriptor by `component_id` + version  
- Map Catalog descriptor → Builder-facing read model  
- **No** own component-type database  

**Result:** palette data only from Catalog; Basic and extension visually equal; origin does not affect Builder behavior.

### P2.2 — Composition Model

Canonical draft instance (minimum):

| Field | Role |
|-------|------|
| `instance_id` | Stable instance identity |
| `component_id` | Catalog component |
| `component_version` | Exact pinned version |
| `config` | Instance config |
| position | Order in composition |

**Invariants:** same component may appear many times; order lives in composition (not descriptor); `config` limited to Builder Descriptor `config_fields`; unknown component/version cannot be saved; Builder does **not** interpret validation/normalization.

### P2.3 — Composition Commands

Operate on the composition model (not raw UI state):

- add / remove / reorder instance  
- update config  
- duplicate instance  
- load draft / save draft  

Same command layer usable from web, tests, and future clients.

### P2.4 — Draft Persistence

Persist **only** composition suitable for the existing publish path.

**Forbidden:** separate Builder publication schema; alternate schema contract; second storage pipeline; separate intake mapping.

Saved draft must compose into the existing publish contract without manual type transforms.

### P2.5 — Minimal Builder UI

Only after P2.1–P2.4 + UI gate:

- Catalog palette · search · canvas  
- add / remove / reorder  
- config panel from `config_fields`  
- save draft  

**Out:** themes · deep Publish UI · analytics · conditional logic · layout designer · custom CSS · full public-form preview if it needs a separate runtime.

---

## Additional mandatory invariants

1. Builder **never** imports stdlib components directly.  
2. Builder has **no** checks like `component_id == "email"`.  
3. Component version is always **pinned** in composition.  
4. **No** automatic version bump of an existing instance.  
5. Missing / incompatible component → draft is **diagnosably invalid**, never silently replaced.  
6. Builder Descriptor defines available config — **not** public field appearance.  
7. **Save draft** and **publish** are different actions.  
8. Builder **never** auto-publishes.

---

## UI start gate

UI (**P2.5**) must not start until ready:

- [ ] Builder Read Model  
- [ ] Composition Contract  
- [ ] Draft commands  
- [ ] Persistence adapter  
- [ ] Contract tests: no hardcode · no Catalog mutation  

---

## History

- 2026-07-19: Opened READY after P1.4 (`97aac4e3` / #54); client-only boundary.  
- 2026-07-19: Design **ACTIVE** after #55 (`a142bd0c`); P2.1–P2.5 decomposition + UI gate; P3–P5 LOCKED.
