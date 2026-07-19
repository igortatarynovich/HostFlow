# Forms Product Layer P2 — Builder

**Status:** **ACTIVE** (Catalog Consumption **ACTIVE**)  
**Prerequisite:** P1 Product Layer Foundation **CLOSED** · Field Catalog v1 **FROZEN**  
**Canon:** [`forms-product-layer-epic.md`](forms-product-layer-epic.md)  
**Last complete:** [`forms-product-p2-3-composition-commands.md`](forms-product-p2-3-composition-commands.md) · **COMPLETE**  
**Next sprint:** P2.4 Draft Persistence — **READY FOR IMPLEMENTATION**

---

## Closed / active gates

| Gate | Status |
|------|--------|
| P2 Builder Design | ✅ **ACTIVE** |
| **P2.1 Builder Read Model** | ✅ **COMPLETE** (`ae767201` / #57) |
| **Builder Catalog Consumption** | ✅ **ACTIVE** |
| **P2.2 Composition Model** | ✅ **COMPLETE** (`fea96deb` / #58) |
| **P2.3 Composition Commands** | ✅ **COMPLETE** |
| **P2.4 Draft Persistence** | **READY FOR IMPLEMENTATION** |
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
3. **Persist** draft composition for the existing publish path (P2.4).

Builder **must not**:

- create or invent component types;  
- duplicate validation or normalization;  
- know or branch on Basic vs module extension;  
- reopen Field Catalog architecture;  
- own storage / domain mapping / second intake.

---

## Decomposition

| Sprint | Name | Goal | UI? |
|--------|------|------|-----|
| **P2.1** | Builder Read Model | Stable read model over Catalog | no — ✅ COMPLETE |
| **P2.2** | Composition Model | Canonical draft structure | no — ✅ COMPLETE |
| **P2.3** | Composition Commands | add/remove/reorder/config/duplicate/replace version | no — ✅ COMPLETE |
| **P2.4** | Draft Persistence | Persist composition for existing publish | no — **READY** |
| **P2.5** | Minimal Builder UI | Palette · canvas · config · save | **yes** (after gate) |

### Process rule (normative)

Before opening a large new implementation: **check existing assets** in the current step. Do **not** invent an unplanned gate or reorder the approved sequence unless a **blocking conflict** is found.

### P2.1 — Builder Read Model (**COMPLETE**)

See [`forms-product-p2-1-builder-read-model.md`](forms-product-p2-1-builder-read-model.md).

### P2.2 — Composition Model (**COMPLETE**)

See [`forms-product-p2-2-composition-model.md`](forms-product-p2-2-composition-model.md).

### P2.3 — Composition Commands (**COMPLETE**)

See [`forms-product-p2-3-composition-commands.md`](forms-product-p2-3-composition-commands.md).

Immutable commands: `add_instance` · `remove_instance` · `reorder_instance` · `update_config` · `duplicate_instance` · `replace_component_version` (explicit only). No save/load/publish in P2.3.

### P2.4 — Draft Persistence (**READY FOR IMPLEMENTATION**)

Persist **only** composition suitable for the existing publish path.

**Forbidden:** separate Builder publication schema; alternate schema contract; second storage pipeline; separate intake mapping.

### P2.5 — Minimal Builder UI

Only after P2.1–P2.4 + UI gate.

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

- [x] Builder Read Model  
- [x] Composition Contract  
- [x] Draft commands  
- [ ] Persistence adapter  
- [ ] Contract tests: no hardcode · no Catalog mutation  

---

## History

- 2026-07-19: Design ACTIVE; P2.1–P2.5 decomposition; P3–P5 LOCKED.  
- 2026-07-19: P2.1 COMPLETE (`ae767201` / #57); Catalog Consumption ACTIVE.  
- 2026-07-19: P2.2 COMPLETE (`fea96deb` / #58).  
- 2026-07-19: **P2.3 COMPLETE** — `forms.builder.composition_commands.v1`; P2.4 READY.
