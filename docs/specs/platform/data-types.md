# Data Types — platform inventory

**Hierarchy:** L2 — semantic DataType catalog + observed fragment map; **not** a runtime SoT yet  
**Decision record:** [`ADR-041`](../architecture/ADR-041-data-types.md)  
**Parent model:** [`ADR-038`](../architecture/ADR-038-platform-standardization-model.md) · [`platform-standardization-model.md`](platform-standardization-model.md) (area `data_types`)  
**Related:** [`field-registry-card-configuration.md`](field-registry-card-configuration.md) §4 · [`ADR-040`](../architecture/ADR-040-naming-identifiers.md) · [`naming-identifiers.md`](naming-identifiers.md)  
**Owner:** Platform Reference (target) + Architecture canon  
**Slice:** Semantic value types used by Field Registry, Forms, and UI binders

---

## 1. Row contract

| Field | Meaning |
|-------|---------|
| `data_type` | Semantic `stable_code` |
| `purpose` | What values mean |
| `observed_field_types` | Today’s Field Registry / Forms / custom strings that map here |
| `owner` | Catalog owner |
| `consumers` | Who should bind |
| `notes` | Multiplicity, unknown, forbidden mixes |

---

## 2. Rules summary (from ADR-041)

1. **Field ≠ DataType** — field has `qualified_code`; it **uses** a `data_type`.
2. DataType codes are flat `stable_code` (no module prefix).
3. Formatters / validators / serializers / filters / UI bind primarily to **DataType** (target).
4. Forms schema `type` / stdlib `value_type` are adapters — not a second SoT.
5. Multiplicity and option lists belong to the **field** (or form config), not new DataTypes.
6. Extending the v1 closed set requires a dedicated platform PR.
7. This document does **not** migrate runtime manifests.

---

## 3. v1 semantic inventory

| data_type | purpose | observed_field_types (descriptive) | owner | consumers | notes |
|-----------|---------|--------------------------------------|-------|-----------|-------|
| `text` | Single-line string | `text`, `string` (Forms normalize→text) | Platform Reference (target) | Field Registry, Forms, UI | — |
| `multiline_text` | Multi-line string | `textarea` | Platform Reference (target) | Field Registry, Forms | — |
| `boolean` | Strict bool | `boolean`, `checkbox` (custom) | Platform Reference (target) | Field Registry, Forms | — |
| `integer` | Whole number | `integer` | Platform Reference (target) | Field Registry, Forms | — |
| `decimal` | Non-currency decimal | `decimal`, `number` (Forms/custom) | Platform Reference (target) | Field Registry, Forms | Not money |
| `money` | Monetary amount | *(rarely distinct today — often `decimal`)* | Platform Reference (target) | Field Registry, UI | Currency SoT out of scope |
| `date` | Calendar date | `date` | Platform Reference (target) | Field Registry, Forms | — |
| `datetime` | Instant / datetime | `datetime` | Platform Reference (target) | Field Registry, Forms | — |
| `email` | Email address | `email` | Platform Reference (target) | Field Registry, Forms | — |
| `phone` | Phone number | `phone`, `phone_e164` | Platform Reference (target) | Field Registry, Forms | E.164 = normalization profile of `phone` |
| `url` | URL | `url` | Platform Reference (target) | Forms | — |
| `country` | Country code | `code_alpha2` | Platform Reference (target) | Field Registry | Often paired with reference domain |
| `code` | Opaque slug / identifier | `code` | Platform Reference (target) | Field Registry | Not DocumentType / permission codes |
| `reference_code` | Code in a named reference domain | `reference_code`, `reference_code[]` | Platform Reference (target) | Field Registry, Forms | `[]` = multiplicity on field; require `reference_domain` |
| `enum` | Closed choice set | `single_select`, `select`, `multi_select` / `multiselect`, Forms `enum` | Platform Reference (target) | Field Registry, Forms, custom fields | Options owned by field/config |
| `json` | Structured blob | `json_object`, Forms `json` | Platform Reference (target) | Field Registry, Forms | Schema validation is field-owned |
| `file` | File / upload | `file` | Platform Reference (target) | Forms | Not DocumentType |
| `unknown` | Unmapped / extension bridge | `custom_field`, `computed` (until modeled), other free strings | Platform Reference (target) | Migration / lint | Must not grow as a dumping ground without follow-up |

---

## 4. Fragment → DataType map (observed)

| Observed string | Maps to `data_type` | Source (typical) |
|-----------------|---------------------|------------------|
| `text` / `string` | `text` | Field Registry / Forms |
| `textarea` | `multiline_text` | Field Registry / Forms |
| `phone` / `phone_e164` | `phone` | Field Registry / Forms |
| `email` | `email` | Field Registry / Forms |
| `date` | `date` | Field Registry / Forms |
| `datetime` | `datetime` | Field Registry / Forms |
| `boolean` / `checkbox` | `boolean` | Field Registry / custom |
| `integer` | `integer` | Field Registry / Forms |
| `decimal` / `number` | `decimal` | Field Registry / Forms / custom |
| `code` | `code` | Field Registry |
| `code_alpha2` | `country` | Field Registry |
| `reference_code` / `reference_code[]` | `reference_code` | Field Registry / Forms |
| `json_object` / `json` | `json` | Field Registry / Forms |
| `single_select` / `select` / `enum` | `enum` | Field Registry / Forms / custom |
| `multi_select` / `multiselect` | `enum` | + multiplicity on field |
| `url` | `url` | Forms |
| `file` | `file` | Forms |
| `custom_field` | `unknown` | Field Registry indirection |
| `computed` | `unknown` | Until computed-value model is typed |

---

## 5. Not a DataType (forbidden mixes)

| Thing | Correct area |
|-------|----------------|
| `national_identity_card` / `id_card` | DocumentType / Naming (ADR-040) |
| `users.roles_access` | Permission (ADR-036) |
| `draft` / `active` / `pending_review` | States & Transitions (ADR-039) — dimension-specific |
| `recruitment.candidate.contacts.phone` | Field (`qualified_code`) |
| `forms.field.phone` | FormComponent (Library) |

---

## 6. Fields linkage — target shape

```yaml
qualified_code: recruitment.candidate.contacts.phone
data_type: phone                    # ADR-041 catalog
# field_type: phone_e164            # legacy fragment during transition
normalization: phone_e164           # profile / strategy, not a second DataType
reference_domain: null
```

Until an adoption PR lands, Field Registry §4 remains the **operating description of fragments**; this file is the **semantic target**. Do not invent a third parallel type table in modules.

---

## 7. Adoption backlog (not executed in ADR-041)

1. Add/alias `data_type` on Field Registry manifests and docs §3/§4.
2. Map Forms `ALLOWED_FIELD_TYPES` / stdlib `value_type` → this catalog.
3. Bind shared formatters/validators primarily to DataType.
4. Narrow `unknown` via follow-up types or explicit extension policy.
5. Optional: currency SoT for `money`.

---

## 8. History

- 2026-08-13: Initial L2 DataType inventory under ADR-041; area `data_types` → exists (runtime adoption deferred).
