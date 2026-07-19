# Forms Product Layer P2.3 — Composition Commands

**Status:** **COMPLETE**  
**Epic / P2:** [`forms-product-p2-builder.md`](forms-product-p2-builder.md) · Catalog Consumption **ACTIVE**  
**Prerequisite:** P2.2 Composition Model **COMPLETE** (`fea96deb` / #58)  
**Unlocks:** P2.4 Draft Persistence — **READY FOR IMPLEMENTATION**  
**Out of scope:** UI · persistence · publish · drag-and-drop semantics  

---

## Goal

Immutable domain commands over `forms.builder.composition.v1` — operable from web, tests, and future clients without UI state.

```text
FormDraftComposition → command → new FormDraftComposition
Catalog / build_instance validate preconditions
```

**Contract:** `forms.builder.composition_commands.v1`  
**Package:** `backend/app/forms_platform/builder/commands.py`

---

## Command surface

| Command | Effect |
|---------|--------|
| `add_instance` | Insert/append Catalog-backed instance |
| `remove_instance` | Drop by `instance_id` |
| `reorder_instance` | Move by index; content unchanged |
| `update_config` | Replace config only; identity/version pinned |
| `duplicate_instance` | Clone with new `instance_id` |
| `replace_component_version` | Explicit version pin change only |

**Not in P2.3:** `save` / `load` / `publish` (P2.4+).

---

## Invariants (held)

1. Commands return a **new** composition; input is never mutated.  
2. `instance_id` unique within a draft.  
3. `duplicate` creates a new `instance_id`.  
4. `reorder` does not change instance content.  
5. `update_config` does not change component identity/version.  
6. Unknown component/version → typed error.  
7. Automatic version upgrade forbidden.  
8. No save/load/publish operations.  
9. No UI events / DnD semantics inside domain commands.

---

## DoD

- [x] Minimal command surface implemented  
- [x] Immutability + uniqueness + pin invariants tested  
- [x] Catalog-backed preconditions (via `build_instance`)  
- [x] Explicit `replace_component_version` only  
- [x] No persistence / UI / publish  
- [x] Contract + gate tests green  

---

## History

- 2026-07-19: Opened READY after P2.2 COMPLETE (`fea96deb` / #58).  
- 2026-07-19: **COMPLETE** — `forms.builder.composition_commands.v1`; P2.4 READY.
