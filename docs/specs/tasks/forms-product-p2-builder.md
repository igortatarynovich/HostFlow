# Forms Product Layer P2 — Builder

**Status:** **ACTIVE** · Builder MVP **COMPLETE** (P2.1–P2.5)  
**Prerequisite:** P1 CLOSED · Field Catalog v1 **FROZEN**  
**Canon:** [`forms-product-layer-epic.md`](forms-product-layer-epic.md)  
**Last complete:** [`forms-product-p2-5-minimal-builder-ui.md`](forms-product-p2-5-minimal-builder-ui.md) · **COMPLETE**

---

## Closed / active gates

| Gate | Status |
|------|--------|
| P2.1–P2.5 | ✅ **COMPLETE** |
| Builder Catalog Consumption | ✅ **ACTIVE** |
| Builder MVP | ✅ **COMPLETE** |
| Field Catalog v1 | **FROZEN** |
| P1 Foundation | **CLOSED** |
| P3 Publish UI | **LOCKED** |
| P4 Themes | **LOCKED** |
| P5 Analytics | **LOCKED** |

---

## Decomposition

| Sprint | Status |
|--------|--------|
| P2.1 Read Model | ✅ |
| P2.2 Composition | ✅ |
| P2.3 Commands | ✅ |
| P2.4 Persistence | ✅ |
| P2.5 Minimal UI | ✅ COMPLETE |

### P2.5 — Minimal Builder UI (**COMPLETE**)

See [`forms-product-p2-5-minimal-builder-ui.md`](forms-product-p2-5-minimal-builder-ui.md).

Palette · search · canvas · add/reorder/remove · properties from `config_fields` · save/load draft · dirty + revision conflict. No themes/preview/publish wizard.

---

## UI start gate

- [x] Builder Read Model  
- [x] Composition Contract  
- [x] Draft commands  
- [x] Persistence adapter  
- [x] Contract tests: no hardcode · no Catalog mutation  
- [x] Minimal UI delivered  

---

## Next (outside P2 Builder MVP)

- **P3 Publish UI** remains LOCKED until explicitly opened.  
- **Next platform focus:** [`intake-canonical-input-matrix.md`](intake-canonical-input-matrix.md) · **ACTIVE** — freeze Source profile → Provider → Published form → `route_intent` → `intake_handoff` → Destination **before** Flights / Intake Routing runtime.  
  Matrix SoT: [`../architecture/intake-canonical-input-matrix.md`](../architecture/intake-canonical-input-matrix.md) (**READY**).

---

## History

- 2026-07-19: P2.4 COMPLETE (`7164a66d` / #60); UI gate OPEN.  
- 2026-07-19: **P2.5 COMPLETE** — Builder MVP closed.  
- 2026-07-19: Next epic opened — Intake Canonical Input Matrix ACTIVE / matrix READY.
