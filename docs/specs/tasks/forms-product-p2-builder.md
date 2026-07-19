# Forms Product Layer P2 — Builder

**Status:** **ACTIVE** (Catalog Consumption **ACTIVE**)  
**Prerequisite:** P1 Product Layer Foundation **CLOSED** · Field Catalog v1 **FROZEN**  
**Canon:** [`forms-product-layer-epic.md`](forms-product-layer-epic.md)  
**Last complete:** [`forms-product-p2-4-draft-persistence.md`](forms-product-p2-4-draft-persistence.md) · **COMPLETE**  
**Next sprint:** P2.5 Minimal Builder UI — **READY FOR IMPLEMENTATION** (UI gate **OPEN**)

---

## Closed / active gates

| Gate | Status |
|------|--------|
| P2 Builder Design | ✅ **ACTIVE** |
| **P2.1 Builder Read Model** | ✅ **COMPLETE** (`ae767201` / #57) |
| **Builder Catalog Consumption** | ✅ **ACTIVE** |
| **P2.2 Composition Model** | ✅ **COMPLETE** (`fea96deb` / #58) |
| **P2.3 Composition Commands** | ✅ **COMPLETE** (`e1de9e3e` / #59) |
| **P2.4 Draft Persistence** | ✅ **COMPLETE** |
| **P2.5 Minimal Builder UI** | **READY FOR IMPLEMENTATION** (UI gate **OPEN**) |
| Field Catalog v1 | **FROZEN** |
| P1 Foundation | **CLOSED** |
| P3 Publish UI | **LOCKED** |
| P4 Themes | **LOCKED** |
| P5 Analytics | **LOCKED** |

---

## Hard boundary (normative)

Builder is a **thin client of frozen Field Catalog v1**. It may only:

1. **Read** the unified Catalog.  
2. **Assemble** form composition (instances, order, config).  
3. **Persist** draft composition for the existing publish path.

Builder **must not** invent types, fork validation/normalization, branch on Basic vs extension, or own a second publication/intake pipeline.

---

## Decomposition

| Sprint | Name | Status |
|--------|------|--------|
| **P2.1** | Builder Read Model | ✅ COMPLETE |
| **P2.2** | Composition Model | ✅ COMPLETE |
| **P2.3** | Composition Commands | ✅ COMPLETE |
| **P2.4** | Draft Persistence | ✅ COMPLETE |
| **P2.5** | Minimal Builder UI | **READY** (gate open) |

### Process rule (normative)

Before opening a large new implementation: **check existing assets** in the current step. Do **not** invent an unplanned gate or reorder the approved sequence unless a **blocking conflict** is found.

### P2.4 — Draft Persistence (**COMPLETE**)

See [`forms-product-p2-4-draft-persistence.md`](forms-product-p2-4-draft-persistence.md).

Stores only composition drafts with tenant isolation + revision CAS; immutable payload per revision; no publish side effects.

### P2.5 — Minimal Builder UI (**READY FOR IMPLEMENTATION**)

UI gate prerequisites satisfied:

- [x] Builder Read Model  
- [x] Composition Contract  
- [x] Draft commands  
- [x] Persistence adapter  
- [x] Contract tests: no hardcode · no Catalog mutation  

In scope: Catalog palette · search · canvas · add/remove/reorder · config panel from `config_fields` · save draft.

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

## History

- 2026-07-19: P2.1–P2.3 COMPLETE through #59 (`e1de9e3e`).  
- 2026-07-19: **P2.4 COMPLETE** — `forms.builder.draft_persistence.v1`; **P2.5 UI gate OPEN**.
