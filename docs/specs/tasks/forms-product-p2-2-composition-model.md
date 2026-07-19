# Forms Product Layer P2.2 — Composition Model

**Status:** **COMPLETE**  
**Epic / P2:** [`forms-product-p2-builder.md`](forms-product-p2-builder.md)  
**Prerequisite:** P2.1 Builder Read Model **COMPLETE** (`ae767201` / #57)  
**Unlocks:** P2.3 Composition Commands — **READY FOR IMPLEMENTATION**  
**Out of scope:** UI · draft persistence · publish side effects  

---

## Goal

Define the canonical **in-memory** form draft composition for Builder — stable identity, pinned instances, ordered placement, config bounded by Builder Descriptor.

```text
FormDraftComposition
  draft_id
  instances[] → instance_id · component_id · component_version (pin) · config
  order = list sequence
```

---

## Minimal model (normative)

| Field | Role |
|-------|------|
| `draft_id` | Stable form draft identity |
| `instance_id` | Stable instance identity |
| `component_id` | Catalog component |
| `component_version` | Exact pinned version |
| `config` | Instance config (builder `config_fields` only) |
| order | Sequence of `instances` (no UI x/y/layout) |

**Contract:** `forms.builder.composition.v1`  
**Package:** `backend/app/forms_platform/builder/composition.py`

---

## Invariants (held)

1. One `component_id` may appear many times (distinct `instance_id`).  
2. Version pin is mandatory; no auto-upgrade.  
3. Composition does **not** store `source`.  
4. Composition does **not** store validation / normalization logic.  
5. Unknown component/version → explicit / diagnosable error (never silent replace).  
6. No UI-specific coordinates or layout model.  
7. No draft persistence and no publish side effects in P2.2.  
8. `config` keys limited to Builder Descriptor `config_fields`.

---

## DoD

- [x] Minimal composition model + draft identity  
- [x] Ordered instances with pinned versions  
- [x] Catalog-backed diagnose / assert_valid  
- [x] Reject origin / layout / validation leakage  
- [x] No persistence / publish / UI  
- [x] Contract + gate tests green  

---

## History

- 2026-07-19: Opened READY after P2.1 COMPLETE (`ae767201` / #57).  
- 2026-07-19: **COMPLETE** — `forms.builder.composition.v1`; P2.3 READY.
