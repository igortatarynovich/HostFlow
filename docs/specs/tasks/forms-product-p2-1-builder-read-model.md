# Forms Product Layer P2.1 — Builder Read Model

**Status:** **COMPLETE** (`ae767201` / #57)  
**Epic / P2:** [`forms-product-p2-builder.md`](forms-product-p2-builder.md) · Catalog Consumption **ACTIVE**  
**Prerequisite:** P1 Foundation **CLOSED** · Field Catalog v1 **FROZEN**  
**Unlocks:** P2.2 Composition Model — ✅ COMPLETE · P2.3 Commands READY  
**UI:** **FORBIDDEN** until P2.1–P2.4 + UI gate  

---

## Goal

Give Builder a stable **read model** over the existing unified Field Catalog — without a private type database and without reopening Catalog architecture.

```text
Catalog.find / get / get_descriptors
  → BuilderReadModel (palette · search · category groups · descriptor view)
  → no register · no stdlib import · no Basic vs Extension branch
```

**Existing asset checked (no sequence change):** P1.4 `list_catalog_for_builder` remains a thin Catalog audit list; P2.1 adds the Builder-facing projection (`forms.builder.read_model.v1`) on the same public `find` / `get` / descriptor APIs.

---

## Delivered

| Surface | Role |
|---------|------|
| `forms.builder.read_model.v1` | Contract id |
| `BuilderReadModel.list_palette` | Unified Catalog → palette rows |
| `BuilderReadModel.search` | Query / filter projection |
| `BuilderReadModel.group_by_category` | Category grouping for palette |
| `BuilderReadModel.get_component` | Exact `component_id` + version view + `config_fields` |
| `BuilderReadModel.get_builder_descriptor_payload` | Builder descriptor payload only |

**Package:** `backend/app/forms_platform/builder/`  
**Tests:** `test_forms_p2_1_read_model_contract.py` · `test_forms_p2_1_read_model_gates.py`

---

## Boundaries (held)

- Reads Catalog only through frozen public APIs  
- No component registration · no Catalog mutation · no Field Catalog v1 edits  
- No direct stdlib import · no `component_id == …` hardcode  
- No Basic vs extension branch in the working model (no `source` on DTOs)  
- No composition / commands / persistence / UI (P2.2–P2.5)

---

## DoD

- [x] Read model loads unified Catalog list  
- [x] Search / filter work without private type store  
- [x] Descriptor fetch by id + version  
- [x] Basic and extension treated equally  
- [x] No `component_id == ...` hardcode; no Catalog writes  
- [x] Contract + gate tests green  

---

## History

- 2026-07-19: Opened READY FOR IMPLEMENTATION after P2 design ACTIVE (`a142bd0c` / #55; status `33011872` / #56).  
- 2026-07-19: **COMPLETE** — `forms.builder.read_model.v1`; P2.2 READY.
