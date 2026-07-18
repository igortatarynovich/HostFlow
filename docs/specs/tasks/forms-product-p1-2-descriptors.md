# Forms Product Layer P1.2 — Component Descriptors

**Status:** **READY** (design · implementation not started)  
**Prerequisite:** P1.1 Registry **COMPLETE** ([`forms-product-p1-1-registry.md`](forms-product-p1-1-registry.md) · `644b102a` / #47)  
**Unlocks:** P1.3 Standard library (consumes descriptors)  
**Builder:** **LOCKED**  
**Canon:** [`forms-product-p1-field-catalog.md`](forms-product-p1-field-catalog.md)

---

## Goal

Standardize **four descriptor surfaces** per Catalog component so clients stop hardcoding Email/Phone specifics and only ask:

> “Give me the descriptor.”

| Descriptor | Consumer | Purpose |
|------------|----------|---------|
| **Builder** | Builder (P2) | Palette / property editors / preview contract |
| **Public** | Public Form runtime | Render contract for published forms |
| **Validation** | Sprint 4/5 validation | How values are validated |
| **Normalization** | Sprint 5 answers | How values are normalized |

```text
Registry.get(id, version)
  → descriptors.builder | .public | .validation | .normalization
```

---

## Scope

### In

- Stable descriptor contract ids / shapes for the four surfaces  
- Attach descriptors to registered `ComponentRecord` (or adjacent Catalog API)  
- Resolve descriptors via registry (exact + compatible resolution from P1.1)  
- Contract tests: every registered component can expose all four descriptors (may be minimal stubs)  
- Compose existing Sprint 4/5 validation & normalization hooks — do not fork them  

### Out

- **UI renderers** (actual React/widgets) — descriptors only; UI in P2/P4  
- **Standard library** components (P1.3)  
- Extension API (P1.4)  
- Builder unlock  
- Migrations (unless strictly required; prefer code registry)  

---

## DoD (implementation gate)

- [ ] Four descriptor surfaces defined and documented  
- [ ] Registry/API returns descriptors for a component version  
- [ ] Clients can fetch without knowing Email/Phone internals  
- [ ] Validation/Normalization descriptors compose Sprint 4/5 contracts  
- [ ] Contract + gate tests green  
- [ ] No Builder UI · no stdlib pack · Builder remains LOCKED  

---

## History

- 2026-07-18: Opened as READY after P1.1 merge `644b102a` (#47).
