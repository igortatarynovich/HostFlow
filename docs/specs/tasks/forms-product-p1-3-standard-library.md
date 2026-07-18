# Forms Product Layer P1.3 — Standard Library

**Status:** **READY FOR IMPLEMENTATION**  
**Prerequisite:** P1.2 Descriptors **COMPLETE** ([`forms-product-p1-2-descriptors.md`](forms-product-p1-2-descriptors.md) · `1f7b4aba` / #50)  
**Unlocks:** Product Layer P2 (Builder) after this DoD  
**Builder:** **LOCKED** until P1.3 complete  
**Canon:** [`forms-product-p1-field-catalog.md`](forms-product-p1-field-catalog.md)

---

## Goal

Register the **Basic HostFlow Forms component pack** exclusively through the public **Registry** and **Descriptors** contracts.

No special-case branches, hard-coded Email/Phone paths, or exceptions inside Catalog core.

```text
stdlib components
  → build_component_record(... descriptors ...)
  → registry.register(...)
  → same get / find / resolve_compatible / get_descriptors APIs as any component
```

---

## Normative rule

**Standard Library is a Catalog client, not a Catalog privilege.**

Every Basic component is a normal registered component with complete declarative descriptors. Core registry/descriptor code must not grow `if component_id == "forms.field.email"` (etc.) shortcuts.

---

## Minimal component set

| Component | Suggested `component_id` |
|-----------|--------------------------|
| Text | `forms.field.text` |
| TextArea | `forms.field.textarea` |
| Number | `forms.field.number` |
| Email | `forms.field.email` |
| Phone | `forms.field.phone` |
| Date | `forms.field.date` |
| Checkbox | `forms.field.checkbox` |
| Radio | `forms.field.radio` |
| Select | `forms.field.select` |
| MultiSelect | `forms.field.multiselect` |
| File | `forms.field.file` |
| Hidden | `forms.field.hidden` |

Each entry ships with **complete** Builder / Public / Validation / Normalization descriptors (`require_complete_descriptors=True`).

---

## Scope

### In

- Stdlib registration module that uses only public Catalog APIs  
- Seed platform registry (or explicit `register_standard_library(registry)`)  
- Contract tests: all 12 present, complete descriptors, resolve via public APIs  
- Gate: no special-case branches in `registry.py` / `descriptors.py` for stdlib ids  

### Out

- Builder UI (P2) — unlocked **after** this DoD  
- Themes (P4) · Analytics (P5)  
- Module Extension API (P1.4)  
- Migrations (unless strictly required; prefer code registration)  
- Domain components (Recruitment/HR/Fleet — P1.4)  

---

## DoD (implementation gate)

- [ ] All 12 Basic components registered via public Registry + Descriptors  
- [ ] Each has complete four-descriptor set  
- [ ] No Catalog-core special cases for stdlib ids  
- [ ] Contract + gate tests green  
- [ ] Builder unlock documented as allowed after merge  
- [ ] P1.4 remains next for module-owned components  

---

## History

- 2026-07-18: Opened **READY FOR IMPLEMENTATION** after P1.2 merge `1f7b4aba` (#50).
