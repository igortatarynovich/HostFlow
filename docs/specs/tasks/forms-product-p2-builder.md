# Forms Product Layer P2 — Builder

**Status:** **ACTIVE** (design · Catalog Consumption **ACTIVE**)  
**Prerequisite:** P1 Product Layer Foundation **CLOSED** · Field Catalog v1 **FROZEN**  
**Canon:** [`forms-product-layer-epic.md`](forms-product-layer-epic.md)  
**Last complete:** [`forms-product-p2-2-composition-model.md`](forms-product-p2-2-composition-model.md) · **COMPLETE**  
**Next sprint:** P2.3 Composition Commands — **READY FOR IMPLEMENTATION**

---

## Closed / active gates

| Gate | Status |
|------|--------|
| P2 Builder Design | ✅ **ACTIVE** |
| **P2.1 Builder Read Model** | ✅ **COMPLETE** (`ae767201` / #57) |
| **Builder Catalog Consumption** | ✅ **ACTIVE** |
| **P2.2 Composition Model** | ✅ **COMPLETE** |
| **P2.3 Composition Commands** | **READY FOR IMPLEMENTATION** |
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
3. **Persist** draft composition for the existing publish path (P2.4 — not yet).

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
| **P2.1** | Builder Read Model | Stable read model over Catalog | no — ✅ COMPLETE |
| **P2.2** | Composition Model | Canonical draft structure | no — ✅ COMPLETE |
| **P2.3** | Composition Commands | add/remove/reorder/config/draft ops | no — **READY** |
| **P2.4** | Draft Persistence | Persist composition for existing publish | no |
| **P2.5** | Minimal Builder UI | Palette · canvas · config · save | **yes** (after gate) |

### Process rule (normative)

Before opening a large new implementation: **check existing assets** in the current step. Do **not** invent an unplanned gate or reorder the approved sequence unless a **blocking conflict** is found.

### P2.1 — Builder Read Model (**COMPLETE**)

See [`forms-product-p2-1-builder-read-model.md`](forms-product-p2-1-builder-read-model.md).

### P2.2 — Composition Model (**COMPLETE**)

See [`forms-product-p2-2-composition-model.md`](forms-product-p2-2-composition-model.md).

| Field | Role |
|-------|------|
| `draft_id` | Stable form draft identity |
| `instance_id` | Stable instance identity |
| `component_id` | Catalog component |
| `component_version` | Exact pinned version |
| `config` | Instance config (`config_fields` only) |
| order | Sequence of instances |

**Invariants:** multi-use of one component; version pin; no `source`; no validation/normalization storage; unknown id/version → diagnosable error; no UI layout; no persistence/publish in P2.2.

### P2.3 — Composition Commands (**READY FOR IMPLEMENTATION**)

Operate on the composition model (not raw UI state):

- add / remove / reorder instance  
- update config  
- duplicate instance  
- load draft / save draft *(command shapes only — persistence adapter is P2.4)*  

Same command layer usable from web, tests, and future clients.

### P2.4 — Draft Persistence

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
- [ ] Draft commands  
- [ ] Persistence adapter  
- [ ] Contract tests: no hardcode · no Catalog mutation  

---

## History

- 2026-07-19: Design **ACTIVE** after #55; P2.1–P2.5 decomposition; P3–P5 LOCKED.  
- 2026-07-19: P2.1 COMPLETE (`ae767201` / #57); Builder Catalog Consumption **ACTIVE**; P2.2 opened.  
- 2026-07-19: **P2.2 COMPLETE** — `forms.builder.composition.v1`; P2.3 READY.
