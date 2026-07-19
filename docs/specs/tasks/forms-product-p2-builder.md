# Forms Product Layer P2 — Builder

**Status:** **READY FOR IMPLEMENTATION**  
**Prerequisite:** P1 Product Layer Foundation **COMPLETE** (merge `97aac4e3` / [PR #54](https://github.com/igortatarynovich/HostFlow/pull/54))  
**Catalog:** Field Catalog public contracts v1 **FROZEN** ([`forms-field-catalog-v1-freeze.md`](../architecture/forms-field-catalog-v1-freeze.md))  
**Canon:** [`forms-product-layer-epic.md`](forms-product-layer-epic.md)

---

## Hard boundary (normative)

Builder is a **thin Field Catalog client**. It may only:

1. **Read** the unified Catalog (existing find / get / descriptors APIs).  
2. **Assemble** form composition (which components, order, instance config).  
3. **Persist** form configuration for publish (compose existing publish / schema contracts).

Builder **must not**:

- create or invent component types;  
- duplicate validation or normalization logic;  
- distinguish Basic vs module extension components;  
- rewrite or bypass frozen Catalog v1 contracts;  
- own storage / domain mapping / second intake.

```text
Catalog (frozen v1) → Builder reads unified list
                    → places instances + config
                    → saves composition
                    → Publish / Public / validate / normalize unchanged
```

Origin (`platform` | `module:<id>`) may exist for audit tooling; Builder composition UX treats all components the same.

---

## Goal

Visual form constructor on top of the completed P1 platform — without returning to Field Catalog architecture.

---

## Scope (preview)

### In

- Catalog palette / search via public read APIs  
- Canvas: add / reorder / configure instances within descriptor `config_fields`  
- Persist draft composition → existing publish path  
- Contract tests: Builder never registers components; never hardcodes Email/Phone  

### Out

- New field types (use Extension API / Stdlib)  
- Themes (P4) · Analytics (P5) · Publish UI depth (P3) beyond compose  
- Breaking Catalog v1 changes  

---

## DoD (implementation gate)

- [ ] Builder reads only unified Catalog surface  
- [ ] Composition save uses published schema contracts (component_id + version + config)  
- [ ] No type invention; no validation/normalization fork  
- [ ] No Basic vs Extension branching in Builder  
- [ ] Gates assert frozen v1 contracts unchanged  
- [ ] Contract + UI smoke tests  

---

## History

- 2026-07-19: Opened READY after P1.4 merge `97aac4e3` (#54); hard client-only boundary fixed.
