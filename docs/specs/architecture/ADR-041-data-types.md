# ADR-041: Data Types (+ Fields linkage)

**Status:** Accepted  
**Date:** 2026-08-13  
**Layer of change:** Vocabulary (Data Types) | Meta-canon + inventory  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-038`](ADR-038-platform-standardization-model.md) · [`ADR-040`](ADR-040-naming-identifiers.md) · [`ADR-037`](ADR-037-platform-object-kind-catalog.md) · [`../platform/field-registry-card-configuration.md`](../platform/field-registry-card-configuration.md) · L2 [`../platform/data-types.md`](../platform/data-types.md)

**L0 checklist:** No new L0 P-rule; does not rewrite Passport/Manifest; fills ADR-038 area `data_types` with a **semantic DataType canon + Fields linkage contract**, not a runtime `field_type` migration.

---

## Context

ADR-038 hard rule **Field ≠ DataType**: semantic datatypes (`phone`, `money`, `country`, `date`) are shared; fields (`recruitment.candidate.contacts.phone`) **use** a datatype. Formatters, validators, serializers, filters, and UI renderers bind primarily to DataType.

Today HostFlow only has **fragments**: Field Registry `field_type` strings, Forms schema `type`, and stdlib `value_type` — overlapping but not a closed Platform Reference SoT. Without a DataType canon, modules keep inventing parallel type strings and binding UI to field codes instead of shared value semantics.

---

## Decision

### 1. DataType is a vocabulary object

A **DataType** is a platform semantic for *what a value means and how it is normalized/rendered*. It is **not**:

| Not a DataType | Why |
|----------------|-----|
| Field / FieldDefinition | Field identity = `qualified_code` (ADR-040); Field **uses** a DataType |
| FormComponent | Presentation/control library entry; may bind to a DataType |
| DocumentType | Evaluation / reference document kind codes (ADR-018 / ADR-040) |
| Permission / Capability | Authz / entitlement (ADR-036 / Catalog) |
| Status / state dimension | Lifecycle / outcome axes (ADR-039) |

### 2. Identifier kind

DataType codes are flat `stable_code` (ADR-040). No dotted module prefixes (`recruitment.phone` is a **field**, not a datatype).

### 3. Ownership

| Concern | Owner |
|---------|-------|
| DataType catalog (semantic codes) | Platform Reference (target) — this ADR + L2 inventory |
| Field identity + storage binding | Platform Field Registry |
| Form controls / schema adapters | Forms Platform |
| Formatters / validators / serializers | Prefer bind to DataType (target); today often bound to `field_type` fragments |

### 4. Closed v1 semantic set

| data_type | Answers |
|-----------|---------|
| `text` | Single-line string |
| `multiline_text` | Multi-line string |
| `boolean` | Strict bool |
| `integer` | Whole number |
| `decimal` | Non-currency decimal |
| `money` | Monetary amount (currency SoT **out of scope**) |
| `date` | Calendar date (timezone-safe) |
| `datetime` | Instant / datetime |
| `email` | Email address |
| `phone` | Phone number (E.164 normalization is a profile of `phone`) |
| `url` | URL |
| `country` | Country code (typically ISO alpha-2) |
| `code` | Opaque slug / identifier |
| `reference_code` | Code that must exist in a named reference domain |
| `enum` | Closed choice set (options owned by field/config, not by DataType catalog) |
| `json` | Structured object/blob |
| `file` | File / upload reference |
| `unknown` | Bridge only — unmapped legacy / `custom_field` indirection |

Extending the closed set requires a dedicated PR (Platform-first), not a module-local string.

### 5. Fields / Forms linkage (contract only)

```text
Field (qualified_code) → uses → DataType (stable_code)
FormComponent / schema type → maps or adapts → DataType
```

- Field Registry today stores `field_type` fragments; **target** shape adds/aliases an explicit `data_type` referencing this catalog.
- Forms `ALLOWED_FIELD_TYPES` / stdlib `value_type` are **consumers/adapters**, not a second SoT.
- Multiplicity (`reference_code[]`, multiselect) is a **field/cardinality** concern, not a separate DataType.
- This ADR does **not** migrate manifests, DB columns, or Forms allow-lists.

### 6. Observed fragments are descriptive

L2 inventory maps today’s `phone_e164`, `textarea`, `code_alpha2`, `number`, `single_select`, etc. onto v1 DataTypes. Those maps are **descriptive inventory**, not a claim that runtime already uses the canonical codes.

---

## Out of scope (explicit)

- Runtime / ORM / `field_type` column migration
- Forms `ALLOWED_FIELD_TYPES` rewrite
- Currency registry / ISO money model for `money`
- Reference-domain SoT expansion
- Relationships, Actions, Events, Design SVL
- DocumentType seed alignment
- Shared status enums

---

## Explicit next

1. Relationships: **done** ([`ADR-042`](ADR-042-relationships.md)). UI composition rule: **done** ([`ADR-043`](ADR-043-ui-component-composition-canon.md)). ADR-038 *vocabulary* sequence continues with **Actions** / **Events**.
2. Optional later: Field Registry / Forms adoption PR that stores `data_type` and binds validators/UI primarily to DataType.

---

## Architecture Review Checklist (L0)

- [x] P-01…P-05 respected — no new capability Passport
- [x] Does not collapse Field and DataType
- [x] Aligns with ADR-038 Field ≠ DataType and ADR-040 naming
- [x] Platform-first — closed set; extensions via PR
- [x] L0 freeze untouched

---

## Consequences

- Positive: Data Types area becomes `exists`; Field Registry and Forms have a shared semantic target; UI/validation binding has a clear primary key (DataType).
- Negative: runtime still uses fragments until an adoption PR; `money` lacks currency SoT.
- Follow-on: ~~Relationships~~ (ADR-042); ~~UI composition~~ (ADR-043); Actions / Events (ADR-038 vocabulary); optional Field/Forms `data_type` adoption.

---

## Alternatives considered

1. **Treat Field Registry §4 as the DataType SoT** — rejected; mixes field identity concerns and leaves Forms with a parallel list.
2. **Migrate all manifests in this PR** — rejected; one concern — canon first.
3. **Open-ended free strings forever** — rejected; recreates the gap ADR-038 named.

---

## Cross-references (updated in same change set)

- [`../platform/data-types.md`](../platform/data-types.md) — L2 inventory + fragment map
- [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md) — area `data_types` → `exists`
- [`ADR-038-platform-standardization-model.md`](ADR-038-platform-standardization-model.md) — next-pointer update
- [`../platform/field-registry-card-configuration.md`](../platform/field-registry-card-configuration.md) · [`architecture-guide.md`](architecture-guide.md) · [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)
